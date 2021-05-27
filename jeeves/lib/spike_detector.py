"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
from collections import defaultdict
from datetime import date, datetime, time
from typing import List

import numpy as np

from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import (
    date_to_str,
    get_eastern_today,
    get_n_days_ago,
    time_series_str_to_datetime,
)


def split_beta_batches_and_run_detector(doc_mix: List[JeevesDocument]) -> None:
    """
    Given a mix of documents from checkpointing, split them into groups
    according to what their shake-to-report categorization is, and run spike
    detection on each of those groups.

    Parameters:
        doc_mix: A mix of documents, which can contain documents with various
                 values for shake_to_report_category.
    """

    split_batches = defaultdict(list)
    for document in doc_mix:
        split_batches[document.shake_to_report_category].append(document)

    for spike_group in SpikeCategory:
        group_to_run = []
        for shake_category in SpikeCategory.inter_category_mapping(spike_group):
            if shake_category in split_batches:
                group_to_run += split_batches[shake_category]

        if group_to_run:
            run_spike_detector_for_batch(group_to_run, spike_group)


def split_beta_batches_and_run_for_date(target_date: date) -> None:
    """
    Essentially a wrapper around split_beta_batches_and_run_detector that
    calculates a list of documents on a particular date and uses
    that list as the list of documents to be considered.

    Parameters:
        target_date: Date that we want to perform spike detection on. All
                     documents from this date will be considered in spike
                     detection.
    """
    target_start = datetime.combine(target_date, time.min)
    target_end = datetime.combine(target_date, time.max)

    doc_batch = []
    _BATCH_TARGET_SIZE = 1000

    _PAGE_SIZE = 10
    for lang in SUPPORTED_LANGUAGES.__members__:
        more_pages = True
        page_number = 0
        while more_pages:
            paginated_info = ElasticDAL.get_recent_paginated_tickets(
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
                split_beta_batches_and_run_detector(doc_batch)
                doc_batch = []

    split_beta_batches_and_run_detector(doc_batch)


def run_spike_detector_for_batch(
    new_ticket_batch: List[JeevesDocument], spike_group: SpikeCategory
) -> None:
    """
    Given a new batch of tickets from checkpointing, runs spike detection on
    each of the words in the new tickets, for the date that ticket was opened.
    That is, if a ticket in this batch contains word X and was submitted on
    date Y, run spike detection for word X on date Y. Repeat for all words in
    that ticket, and repeat for all tickets in the batch.

    Parameters:
        new_ticket_batch (List[JeevesDocument]): Batch of new tickets used to
                                                direct spike detection
        spike_group (SpikeCategory): Indicator for which types of documents
                                     are in the current batch.
    """
    # Since spike detection is split up by language, we need to separate tickets
    # and dates into different language buckets
    new_ticket_dates_per_lang = dict.fromkeys(SUPPORTED_LANGUAGES.__members__, set())
    new_ticket_ids_per_lang = dict.fromkeys(SUPPORTED_LANGUAGES.__members__, [])

    for ticket in new_ticket_batch:
        new_ticket_dates_per_lang[ticket.language].add(ticket.date_time.date())
        new_ticket_ids_per_lang[ticket.language].append(
            ticket.generate_elasticsearch_internal_id(ticket)
        )

    batch_spike_list = []

    for lang in SUPPORTED_LANGUAGES.__members__:
        if new_ticket_ids_per_lang[lang]:
            word_to_date_to_count = _get_word_to_date_to_count(lang, new_ticket_ids_per_lang[lang])
            for target_dt in new_ticket_dates_per_lang[lang]:
                batch_spike_list += _find_spiked_words(lang, word_to_date_to_count, target_dt)

    for spike in batch_spike_list:
        spike.update({"spike_group": spike_group.name})

    if batch_spike_list:
        ElasticDAL.bulk_index_spikes(batch_spike_list)


def run_spike_detector(language, update_start_time):
    """
    Runs the spike detector algorithm for a specified language

    Parameters:
        language(SUPPORTED_LANGUAGES): A language enum; which language to run
            spike detection on.
    """

    today = get_eastern_today()  # Shouldn't be UTC

    # We don't want to recalculate existing spikes,
    # so only consider terms from recent tickets.
    new_ticket_ids = ElasticDAL.acquire_ticket_ids_since(update_start_time, language.name)
    word_to_date_to_count = _get_word_to_date_to_count(language.name, new_ticket_ids)
    recent_spikes = []
    for i in range(3):
        target_dt = get_n_days_ago(today, i)
        recent_spikes += _find_spiked_words(language.name, word_to_date_to_count, target_dt)
    ElasticDAL.bulk_index_spikes(recent_spikes)


def _bucket_to_value(bucket):
    date_val = time_series_str_to_datetime(bucket["key_as_string"])
    return {date_to_str(date_val): bucket["doc_count"]}


def _get_word_to_date_to_count(lang, new_ticket_ids):
    """
    Compute a data structure that represents how many times a word appeared
    in our stored tickets, bucketed by date, for each of several words. The
    'several words' are the applicable words extracted as tokens from the
    provided ticket IDs.

    Parameters:
        lang (str): Restrict search to this language
        new_ticket_ids (List[str]): IDs of tickets to tokenize for words.
                                    Those words will be mapped to date-bucketed
                                    counts of instances in stored tickets.

    Returns:
        A data structure that contains a mapping from each word in the provided
        tickets to a mapping from dates to how many times that word appeared on
        that date.
    """
    # Elasticsearch can take care of tokenization on top of everything else
    terms = ElasticDAL.get_terms_from_docs(new_ticket_ids, lang)

    word_date_count = {}
    for t in terms:
        word_date_count[t] = {}
        buckets = ElasticDAL.aggregate_time_series(lang, t)
        if "ERROR" in buckets:
            continue
        for val in [_bucket_to_value(b) for b in buckets]:
            word_date_count[t].update(val)

    return word_date_count


def _find_spiked_words(lang, word_to_date_to_count, target_dt):
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

    score_word_pairs = [
        (_calculate_spike_score(date_to_count, target_dt), word)
        for word, date_to_count in word_to_date_to_count.items()
    ]
    score_word_pairs = sorted(score_word_pairs, key=lambda x: x[0], reverse=True)
    result = [
        {"word": word, "score": score, "date": target_date_str, "lang": lang}
        for score, word in score_word_pairs
        if (not np.isnan(score) and not np.isinf(score) and score > SPIKE_THRESHOLD)
    ]
    return result


def _calculate_spike_score(date_to_count, target_datetime):
    """
    Given a word, returns a score that represents spikiness where spikiness is a z-score
    computed based on word occurrences in the previous `moving_avg_window_size` days.

    https://stackoverflow.com/questions/22583391/peak-signal-detection-in-realtime-timeseries-data
    """
    date_str = date_to_str(target_datetime)
    target_count = date_to_count.get(date_str, 0)
    if target_count < COUNT_THRESHOLD:
        return -1
    valid_range = set(
        date_to_str(get_n_days_ago(target_datetime, i + 1)) for i in range(HISTORY_WINDOW_SIZE)
    )
    count_history = [count for date, count in date_to_count.items() if date in valid_range]
    mean = np.mean(count_history)
    std = np.std(count_history)
    zscore = (target_count - mean) / std if std != 0 else np.inf
    return zscore
