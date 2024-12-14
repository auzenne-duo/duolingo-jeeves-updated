"""
A script for finding spikes of word occurrences in all Jeeves documents.
Candidate words are batched together by date, language, and spike category.
"""

import json
import timeit
from collections import defaultdict
from datetime import date, datetime, time
from random import shuffle
from typing import Dict, List, Optional, Tuple, Union

import duo_logging  # type: ignore[import]
import numpy as np

from jeeves import registry as app_registry
from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.metrics_dal import MetricsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.reporter_identity import ReporterIdentity
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import (
    date_to_str,
    get_n_days_ago,
    str_to_date,
    time_series_str_to_datetime,
)
from jeeves.util.error_util import SpikeDetectorException

SPIKE_EXCLUDE_WORDS_REGISTRY_KEY = "spike_exclude_words"
SPIKE_LEMMA_STATS_REGISTRY_KEY = "spike_lemma_stats"
STR_SPIKE_LEMMA_STATS_REGISTRY_KEY = "spike_lemma_stats"

# Components of the request format (in YAML)
REQ_SPIKE_WORD = "SPIKE WORD"
REQ_TITLE = "TITLE"
REQ_BODY = "BODY"

# Components of the response format (in JSON)
RESP_SUMMARY = "summary"
RESP_IS_BUG = "is_bug"
RESP_IS_SOCIAL_TREND = "is_social_trend"

SPIKE_SUMMARIZER_SYSTEM_PROMPT = f"""
You are part of a quality analytics pipeline at Duolingo that monitors internal Jira reports, Reddit, app store reviews
from AppFigures, and Zendesk reports coming from email, Twitter, and our Shake-to-Report feature for beta users.
First, you will be given a "spike word" in the format:
{REQ_SPIKE_WORD}: <word>

Next will be a list of reports from Duolingo users in any language (which may contain bug reports, feature requests,
service requests, or something else, each of which should have that spike word in its text), in the format:
{REQ_TITLE}: <title>
{REQ_BODY}: <body>

Your task is:
In 50 words or fewer, write a short summary (IN ENGLISH) of these reports that helps employees at Duolingo to quickly
understand the reason this word is spiking. If the spike is due to multiple users experiencing a bug, explain what
the issue is. Otherwise, summarize what the tickets have in common in relation to the spike word. Your response
should make it clear how the spike word relates to the issue described. If the spike word happens to be the name of
people reporting an issue by coincidence, or happens to be part of an email signature, explain that and do not classify
it as a bug. If the spike word is not in English, be sure to explain what it means in English as part of the summary.

Write your response in English (no matter what language the original documents were in) in the following JSON format:
{{
  "{RESP_SUMMARY}": "<summary>",
  "{RESP_IS_BUG}": <true/false>,
  "{RESP_IS_SOCIAL_TREND}": <true/false>
}}

Consider an issue to be a "bug" if it has to do with the app not working as expected, such as:
- Daily quests aren't being counted correctly
- Users can't log in
- Users are stuck on a green screen

Spike words that are NOT a "bug" involve a feature request, something external, or a coincidence, such as:
- Users want to be able to change their username
- Compliments, general complaints, refund requests, or help repairing their streak
- Retweets or gibberish
- Names of people or rare words that happen to be found in multiple unrelated documents

Consider a spike word to be related to a social trend the reports are about something fun trending on social media, such as:
- A new feature is trending on a social media platform
- Discussing a Duolingo meme or viral tiktok video
- Bugs are not social trends

For example, if you are given the following input:
{REQ_SPIKE_WORD}: accéder
{REQ_TITLE}: Erreur d'authentification
{REQ_BODY}: impossible d'accéder à mon compte

{REQ_TITLE}: Page bloqué
{REQ_BODY}: Bonjour, impossible hier accéder à mon compte

Your response could be:
{{
  "{RESP_SUMMARY}": "Users are reporting that they are unable to access (accéder) or log in to their accounts.",
  "{RESP_IS_BUG}": true,
  "{RESP_IS_SOCIAL_TREND}": false
}}

For example, if you are given the following input:
{REQ_SPIKE_WORD}: party
{REQ_TITLE}: Celebrating 365 Days of Keeping My Streak Alive
{REQ_BODY}: Join my Duolingo Streak Party! #LanguageJourney #DuolingoStreak

{REQ_TITLE}: Get Ready for a Feathered Fiesta!
{REQ_BODY}: I'm throwing a streak party, and it's going to be 'owl'-t of this world!

Your response could be:
{{
  "{RESP_SUMMARY}": "Users are posting about their streak parties to celebrate their streak milestones.",
  "{RESP_IS_BUG}": false,
  "{RESP_IS_SOCIAL_TREND}": true
}}
""".strip()
# if the number of unique users in a spike is less than this, we don't consider it a spike
UNIQUE_USER_THRESHOLD = 3

# We will get automated summaries for the top 5 spikes of each lang/category
MAX_SPIKE_SUMMARIES = 5

# The maximum number of random documents to send to GPT for summarization that contain the spikeword
MAX_DOCS_PER_GPT_REQUEST = 20


def detect_spikes(dry_run: bool, target_date: Optional[date] = None) -> None:
    """
    Essentially a wrapper around _split_beta_batches_and_run_detector that
    calculates a list of documents on a particular date and uses
    that list as the list of documents to be considered.

    Parameters:
        target_date: Date that we want to perform spike detection on. All
                     documents from this date will be considered in spike
                     detection.
                     If no target_date is provided, spikes will be recalculated for all dates.
    """
    target_start = datetime.combine(target_date, time.min) if target_date is not None else None
    target_end = datetime.combine(target_date, time.max) if target_date is not None else None

    _BATCH_TARGET_SIZE = 1000
    _PAGE_SIZE = 10 if target_date is not None else 100

    for lang in SUPPORTED_LANGUAGES.__members__:
        if SUPPORTED_LANGUAGES.is_all(lang):
            continue

        doc_batch = []
        sort_id = None
        count = 0
        while True:
            paginated_info = app_registry(OpenSearchDAL).get_recent_paginated_tickets(
                lang,
                "",
                sort_id=sort_id,
                limit=_PAGE_SIZE,
                start_time=target_start,
                end_time=target_end,
                filter_jiras_from_jeeves=True,
            )

            doc_batch += paginated_info["data"]
            if len(doc_batch) > _BATCH_TARGET_SIZE:
                _split_beta_batches_and_run_detector(doc_batch, lang, dry_run)
                doc_batch = []
            count += len(paginated_info["data"])
            if count >= paginated_info["total_records"]:
                break
            if "sort_id" not in paginated_info:
                break
            sort_id = paginated_info["sort_id"]

        _split_beta_batches_and_run_detector(doc_batch, lang, dry_run)


def _split_beta_batches_and_run_detector(
    documents: List[JeevesDocument], lang: str, dry_run: bool
) -> None:
    """
    Given a mix of documents from checkpointing, run spike detection for each spike category.

    Parameters:
        documents: Jeeves documents, all of which should be in the same language.
    """
    spike_category_to_doc_list = defaultdict(list)
    for document in documents:
        for spike_category in SpikeCategory:
            if SpikeCategory.get_predicate_for_category(spike_category)(document):
                spike_category_to_doc_list[spike_category].append(document)
    print(
        f"Split a batch of {len(documents)} tickets in language {lang}",
        flush=True,
    )
    for spike_category, doc_list in spike_category_to_doc_list.items():
        if doc_list:
            run_spike_detector_for_batch(doc_list, spike_category, lang, dry_run)


def run_spike_detector_for_batch(
    new_ticket_batch: List[JeevesDocument], spike_group: SpikeCategory, lang: str, dry_run: bool
) -> None:
    """
    Given a new batch of tickets from checkpointing, runs spike detection on
    each of the words in the new tickets, for the date that ticket was opened.
    That is, if a ticket in this batch contains word X and was submitted on
    date Y, run spike detection for word X on date Y. Repeat for all words in
    that ticket, and repeat for all tickets in the batch.

    Parameters:
        new_ticket_batch (List[JeevesDocument]): Batch of new tickets used to direct spike
                                            detection. All tickets should be in the same language.
        spike_group (SpikeCategory): Indicator for which types of documents
                                     are in the current batch.
    """
    print(
        f"Running spike detection for a batch of {spike_group.name} tickets in language {lang}",
        flush=True,
    )
    different_languages = [
        ticket.language for ticket in new_ticket_batch if ticket.language != lang
    ]
    if any(different_languages):
        raise SpikeDetectorException(
            f"Batch of {lang} tickets contains ticket(s) in {different_languages}"
        )

    new_ticket_dates = {ticket.date_time.date() for ticket in new_ticket_batch}
    new_ticket_ids = [ticket.generate_opensearch_internal_id(ticket) for ticket in new_ticket_batch]

    batch_spike_list: List[SpikeWord] = []
    batch_prompt_list: List[str] = []

    word_to_date_to_count = _get_word_to_date_to_count(
        lang, spike_group, new_ticket_ids, min(new_ticket_dates)
    )
    filtered_word_to_date_to_count = {
        word: date_to_count
        for word, date_to_count in word_to_date_to_count.items()
        # pylint: disable-next=unsupported-membership-test
        if word not in app_registry(SPIKE_EXCLUDE_WORDS_REGISTRY_KEY)
    }
    for target_date in new_ticket_dates:
        spikes, prompts = _find_spiked_words(
            lang, filtered_word_to_date_to_count, target_date, spike_group
        )
        batch_spike_list += spikes
        batch_prompt_list += prompts

    # 2024-01-18: Changed from bulk chat completion request to synchronous,
    # because ai-completions-backend has been at capacity recently.
    # The Max Engine team gave us the go-ahead to do this.
    top_spikes = batch_prompt_list[:MAX_SPIKE_SUMMARIES]
    if top_spikes:
        print(f"Asking GPT to summarize {len(top_spikes)} spikes...", flush=True)

    for i, prompt in enumerate(top_spikes):
        try:
            user_prompt = f"{REQ_SPIKE_WORD}: {batch_spike_list[i].word}\n\n{prompt}"
            response = app_registry(AICompletionsDAL).ask(
                max_tokens=1024,
                system_prompt=SPIKE_SUMMARIZER_SYSTEM_PROMPT,
                top_p=0.8,
                use_json_mode=True,
                user_prompt=user_prompt,
            )
            # Parse the response as a JSON object
            response_json = json.loads(response)
            batch_spike_list[i].summary = response_json[RESP_SUMMARY]
            batch_spike_list[i].is_bug = response_json[RESP_IS_BUG]
            batch_spike_list[i].is_social_trend = response_json[RESP_IS_SOCIAL_TREND]
        except TimeoutError as e:
            duo_logging.capture_message(f"Spike summary request timed out: {e}", "warning")
        except Exception as e:
            duo_logging.capture_message(f"Spike summary request failed: {e}", "warning")

    if batch_spike_list:
        if not dry_run:
            app_registry(SpikeIndexDAL).bulk_index_spikes(batch_spike_list)
        else:
            print(f"{[spike.to_dict() for spike in batch_spike_list]}")


def _bucket_to_value(bucket: Dict[str, Union[str, int]]) -> Dict[str, int]:
    date_val = time_series_str_to_datetime(bucket["key_as_string"])
    return {date_to_str(date_val): bucket["doc_count"]}


def _get_word_to_date_to_count(
    lang: str,
    spike_category: SpikeCategory,
    new_ticket_ids: List[str],
    min_target_date: date,
) -> Dict[str, Dict[str, int]]:
    """
    Compute a data structure that represents how many times a word appeared
    in our stored tickets, bucketed by date, for each of several words. The
    'several words' are the applicable words extracted as tokens from the
    provided ticket IDs.

    Parameters:
        lang: Restrict search to this language.
        spike_category: Restrict search to documents that belong to this spike category.
        new_ticket_ids: IDs of tickets to tokenize for words. Those words will be mapped to
            date-bucketed counts of instances in stored tickets.

    Returns:
        A data structure that contains a mapping from each word in the provided
        tickets to a mapping from dates to how many times that word appeared on
        that date.
    """
    # OpenSearch can take care of tokenization on top of everything else
    terms = app_registry(OpenSearchDAL).get_terms_from_docs(new_ticket_ids, lang)

    start_time = timeit.default_timer()
    word_date_count = {}
    for t in terms:
        word_date_count[t] = {}
        buckets = app_registry(OpenSearchDAL).aggregate_time_series(
            lang, spike_category, t, get_n_days_ago(min_target_date, HISTORY_WINDOW_SIZE)
        )
        if "ERROR" in buckets:
            continue
        for val in [_bucket_to_value(b) for b in buckets]:
            word_date_count[t].update(val)
    print(
        f"getting word_date_count took {round(timeit.default_timer() - start_time, 2)} seconds for {len(terms)} terms",
        flush=True,
    )

    return word_date_count


def _find_spiked_words(
    lang: str,
    word_to_date_to_count: Dict[str, Dict[str, int]],
    target_date: date,
    spike_group: SpikeCategory,
) -> Tuple[List[SpikeWord], List[str]]:
    """
    Calculates spike words on a particular date.

    Parameters:
        lang (str): Language to restrict search to
        word_to_date_to_count: See _get_word_to_date_to_count, this should be
                               the direct output of that function.
        target_date (date): The date to perform spike calculation on.
        spike_group (SpikeCategory): The SpikeCategory to calculate

    Returns:
        A list of spikes, where each spike consists of:
        - word (str): The spike word
        - score (float): Generally, how big the spike is
        - date (str): The date the spike occurred on
        - lang (str): Language of tickets used in spike calculation

        A list of prompt strings which are concatenated body text of tickets
    """
    target_date_str = date_to_str(target_date)

    min_max_datetimes = app_registry(OpenSearchDAL).get_min_and_max_document_dates(
        lang, spike_group
    )
    window_start_date = max(
        str_to_date(min_max_datetimes["min"]),
        get_n_days_ago(target_date, HISTORY_WINDOW_SIZE),
    )
    data_window_size = (target_date - window_start_date).days

    num_tickets_by_day = app_registry(OpenSearchDAL).get_num_tickets_by_day(
        target_date, spike_group, lang
    )
    average_num_tickets = np.mean(list(num_tickets_by_day.values()))

    # currently we use a baseline generated from solely str tickets
    baseline_stats = app_registry(STR_SPIKE_LEMMA_STATS_REGISTRY_KEY)

    score_word_pairs = [
        (
            _calculate_spike_score(
                date_to_count,
                target_date,
                data_window_size,
                word,
                average_num_tickets,
                lang,
                baseline_stats,
                spike_group,
            ),
            word,
        )
        for word, date_to_count in word_to_date_to_count.items()
    ]
    print(
        f"Calculated spike scores from {target_date_str} for {len(score_word_pairs)} words",
        flush=True,
    )
    score_word_pairs = sorted(score_word_pairs, key=lambda x: x[0], reverse=True)

    result = []
    prompts = []
    for score, word in score_word_pairs:
        if not np.isnan(score) and not np.isinf(score) and score > SPIKE_THRESHOLD:
            target_datetime = datetime(target_date.year, target_date.month, target_date.day)
            search_result = app_registry(OpenSearchDAL).get_recent_paginated_tickets(
                lang,
                word,
                target_datetime,
                target_datetime,
                spike_category=spike_group,
                use_lemmas=True,
            )
            docs = search_result["data"]

            # if we don't have enough unique reporters, skip this spike
            if _get_num_unique_users(docs) < UNIQUE_USER_THRESHOLD:
                continue

            # we will then pass the text of up to 20 random documents to chatgpt to get a summary of the issue
            shuffle(docs)
            random_sample = docs[:MAX_DOCS_PER_GPT_REQUEST]
            prompt = "\n".join(
                [
                    f"{REQ_TITLE}: {doc.header_text}\n{REQ_BODY}: {doc.body_text}\n"
                    for doc in random_sample
                ]
            )
            prompts.append(prompt)

            experiment_spikes = {}
            if lang == "en":
                experiment_spikes = app_registry(MetricsDAL).get_shared_conditions(
                    [doc.user_id for doc in docs]
                )

            spike_word = SpikeWord(
                word=word,
                score=score,
                date=target_date_str,
                lang=lang,
                spike_group=spike_group,
                confirmed=False,
                experiment_spikes=experiment_spikes,
            )
            # if a previous spike exists, persist everything except the score
            prev_spike = app_registry(SpikeIndexDAL).get_spike_by_id(spike_word.get_spike_id())
            if prev_spike:
                prev_spike.score = spike_word.score
                result.append(prev_spike)
            else:
                result.append(spike_word)
    return result, prompts


def _get_num_unique_users(docs: List[JeevesDocument]) -> int:
    """
    Returns the number of unique users in a list of documents.
    """
    return len({ReporterIdentity.from_doc(doc) for doc in docs})


def _calculate_spike_score(
    date_to_count: Dict[str, int],
    target_datetime: date,
    data_window_size: int,
    word: str,
    average_num_tickets: int,
    lang: str,
    baseline_stats: Dict,
    spike_group: SpikeCategory,
):
    """
    Given a word, returns a score that represents spikiness where spikiness is a z-score
    computed based on word occurrences in the previous `moving_avg_window_size` days.

    https://stackoverflow.com/questions/22583391/peak-signal-detection-in-realtime-timeseries-data

    If there are less than HISTORY_WINDOW_SIZE days of data for the spike category:
        For days within HISTORY_WINDOW_SIZE that have no count, we take a weighted mean and std using
        the baseline stats for that term. We normalize by number of docs per day using the ratio of
        average_num_tickets for a dataset to the baseline avg_docs_per_day. If a word is not in the baseline
        dataset, then it is treated normally.
    """
    date_str = date_to_str(target_datetime)
    target_count = date_to_count.get(date_str, 0)
    if target_count < COUNT_THRESHOLD:
        return -1
    word_stats = baseline_stats["words"]

    count_history = [
        date_to_count.get(date_to_str(get_n_days_ago(target_datetime, i)), 0)
        for i in reversed(range(data_window_size))
    ]
    day_count = len(count_history)

    # if there are no previous instances of this term in the past HISTORY_WINDOW_SIZE days, return -1
    if sum(count_history[:-1]) == 0 and data_window_size > 1:
        return -1
    mean = np.mean(count_history)
    std = np.std(count_history)

    if word in word_stats and lang == "en" and day_count < HISTORY_WINDOW_SIZE:
        baseline_mean = word_stats[word]["mean"]
        baseline_std = word_stats[word]["std"]

        # adjust based on average number of tickets
        if average_num_tickets:
            baseline_mean = average_num_tickets * baseline_mean / baseline_stats["avg_docs_per_day"]
            baseline_std = average_num_tickets * baseline_std / baseline_stats["avg_docs_per_day"]

        # take weighted mean and std based on number of real samples in the HISTORY_WINDOW_SIZE
        baseline_count = HISTORY_WINDOW_SIZE - day_count
        mean, std = _calculate_combined_mean_std(
            day_count, mean, std, baseline_count, baseline_mean, baseline_std
        )

    zscore = (target_count - mean) / std if std != 0 else np.inf
    return zscore


def _calculate_combined_mean_std(n_x, mean_x, std_x, n_y, mean_y, std_y):
    """
    Given two distributions (x,y) with size (n), std, and mean, calculates the combined mean and std
    """
    mean = (mean_x * n_x + mean_y * n_y) / (n_x + n_y)
    std = (
        ((n_x) * std_x**2 + (n_y) * std_y**2) / (n_x + n_y)
        + (n_x * n_y * (mean_x - mean_y) ** 2) / ((n_x + n_y) * (n_x + n_y))
    ) ** 0.5
    return mean, std
