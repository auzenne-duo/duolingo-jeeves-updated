"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
import time
import timeit
from collections import defaultdict
from datetime import date, datetime, time
from typing import Dict, List, Optional, Union

import numpy as np

from jeeves import registry as app_registry
from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import date_to_str, get_n_days_ago, time_series_str_to_datetime
from jeeves.util.error_util import SpikeDetectorException

SPIKE_EXCLUDE_WORDS_REGISTRY_KEY = "spike_exclude_words"
SPIKE_TERM_STATS_REGISTRY_KEY = "spike_term_stats"


def detect_spikes(target_date: Optional[date] = None) -> None:
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
        doc_batch = []
        more_pages = True
        page_number = 0
        while more_pages:
            paginated_info = app_registry(ElasticsearchDAL).get_recent_paginated_tickets(
                lang,
                "",
                page=page_number,
                limit=_PAGE_SIZE,
                start_time=target_start,
                end_time=target_end,
            )
            more_pages = paginated_info["deepest_index"] < paginated_info["total_records"]
            doc_batch += paginated_info["data"]
            page_number += 1
            if len(doc_batch) > _BATCH_TARGET_SIZE:
                _split_beta_batches_and_run_detector(doc_batch, lang)
                doc_batch = []

        _split_beta_batches_and_run_detector(doc_batch, lang)


def _split_beta_batches_and_run_detector(documents: List[JeevesDocument], lang: str) -> None:
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
        run_spike_detector_for_batch(doc_list, spike_category, lang)


def run_spike_detector_for_batch(
    new_ticket_batch: List[JeevesDocument], spike_group: SpikeCategory, lang: str
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
            f"Batch of {lang} tickets contains a tickets in {different_languages}"
        )

    new_ticket_dates = {ticket.date_time.date() for ticket in new_ticket_batch}
    new_ticket_ids = [
        ticket.generate_elasticsearch_internal_id(ticket) for ticket in new_ticket_batch
    ]

    batch_spike_list: List[SpikeWord] = []

    word_to_date_to_count = _get_word_to_date_to_count(lang, spike_group, new_ticket_ids)
    filtered_word_to_date_to_count = {
        word: date_to_count
        for word, date_to_count in word_to_date_to_count.items()
        if word not in app_registry(SPIKE_EXCLUDE_WORDS_REGISTRY_KEY)
    }
    for target_dt in new_ticket_dates:
        batch_spike_list += _find_spiked_words(
            lang, filtered_word_to_date_to_count, target_dt, spike_group
        )

    if batch_spike_list:
        app_registry(SpikeIndexDAL).bulk_index_spikes(batch_spike_list)


def _bucket_to_value(bucket: Dict[str, Union[str, int]]) -> Dict[str, int]:
    date_val = time_series_str_to_datetime(bucket["key_as_string"])
    return {date_to_str(date_val): bucket["doc_count"]}


def _get_word_to_date_to_count(
    lang: str, spike_category: SpikeCategory, new_ticket_ids: List[str]
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
    # Elasticsearch can take care of tokenization on top of everything else
    terms = app_registry(ElasticsearchDAL).get_terms_from_docs(new_ticket_ids, lang)

    start_time = timeit.default_timer()
    word_date_count = {}
    for t in terms:
        word_date_count[t] = {}
        buckets = app_registry(ElasticsearchDAL).aggregate_time_series(lang, spike_category, t)
        if "ERROR" in buckets:
            continue
        for val in [_bucket_to_value(b) for b in buckets]:
            word_date_count[t].update(val)
    print(
        f"getting word_date_count took {timeit.default_timer() - start_time} for {len(terms)} terms",
        flush=True,
    )

    return word_date_count


def _find_spiked_words(
    lang: str,
    word_to_date_to_count: Dict[str, Dict[str, int]],
    target_dt: datetime.date,
    spike_group: SpikeCategory,
) -> List[SpikeWord]:
    """
    Calculates spike words on a particular date.

    Parameters:
        lang (str): Language to restrict search to
        word_to_date_to_count: See _get_word_to_date_to_count, this should be
                               the direct output of that function.
        target_dt (datetime.date): The date to perform spike calculation on.

    Returns:
        A list of spikes, where each spike consists of:
        - word (str): The spike word
        - score (float): Generally, how big the spike is
        - date (str): The date the spike occured on
        - lang (str): Language of tickets used in spike calculation
    """
    target_date_str = date_to_str(target_dt)

    average_num_tickets = app_registry(ElasticsearchDAL).get_average_num_tickets_per_day(
        spike_group, lang
    )

    score_word_pairs = [
        (
            _calculate_spike_score(
                date_to_count, target_dt, word, spike_group, average_num_tickets, lang
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
    result = [
        SpikeWord(
            word=word,
            score=score,
            date=target_date_str,
            lang=lang,
            spike_group=spike_group,
            confirmed=False,
        )
        for score, word in score_word_pairs
        if (not np.isnan(score) and not np.isinf(score) and score > SPIKE_THRESHOLD)
    ]
    return result


def _calculate_spike_score(
    date_to_count: Dict[str, int],
    target_datetime: datetime.date,
    word: str,
    spike_group: SpikeCategory,
    average_num_tickets: int,
    lang: str,
):
    """
    Given a word, returns a score that represents spikiness where spikiness is a z-score
    computed based on word occurrences in the previous `moving_avg_window_size` days.

    https://stackoverflow.com/questions/22583391/peak-signal-detection-in-realtime-timeseries-data

    If the spike group is BASELINE_FREQ_COLD_START_SPIKES:
        For days within HISTORY_WINDOW_SIZE that have no count, we take a weighted mean and std using
        the baseline stats for that term. We normalize by number of docs per day using the ratio of
        average_num_tickets for a dataset to the baseline avg_docs_per_day. If a word is not in the baseline
        dataset, then it is treated normally.
    """
    date_str = date_to_str(target_datetime)
    target_count = date_to_count.get(date_str, 0)
    if target_count < COUNT_THRESHOLD:
        return -1
    valid_range = [
        date_to_str(get_n_days_ago(target_datetime, i + 1)) for i in range(HISTORY_WINDOW_SIZE)
    ]
    baseline_stats = app_registry(SPIKE_TERM_STATS_REGISTRY_KEY)
    word_stats = baseline_stats["words"]

    count_history = [count for date, count in date_to_count.items() if date in valid_range]
    if not count_history:
        return -1
    mean = np.mean(count_history)
    std = np.std(count_history)

    if (
        spike_group == SpikeCategory.BASELINE_FREQ_COLD_START_SPIKES
        and word in word_stats
        and lang == "en"
    ):
        day_count = len(count_history)
        # adjust based on average number of tickets
        baseline_mean = (
            average_num_tickets * word_stats[word]["mean"] / baseline_stats["avg_docs_per_day"]
        )
        baseline_std = (
            average_num_tickets * word_stats[word]["std"] / baseline_stats["avg_docs_per_day"]
        )

        # take weighted mean and std based on number of real samples in the HISTORY_WINDOW_SIZE
        mean = (
            day_count * mean + (HISTORY_WINDOW_SIZE - day_count) * baseline_mean
        ) / HISTORY_WINDOW_SIZE
        std = (
            (day_count * std**2 + (HISTORY_WINDOW_SIZE - day_count) * baseline_std**2)
            / HISTORY_WINDOW_SIZE
        ) ** 0.5

    zscore = (target_count - mean) / std if std != 0 else np.inf
    return zscore
