"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
from collections import defaultdict
from datetime import date, datetime, time
from typing import List, Optional

import numpy as np

from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.dal.spike_index_interface import SpikeDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import date_to_str, get_n_days_ago, time_series_str_to_datetime
from jeeves.util.error_util import SpikeDetectorException


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
                _split_beta_batches_and_run_detector(doc_batch, lang)
                doc_batch = []

        _split_beta_batches_and_run_detector(doc_batch, lang)


def _split_beta_batches_and_run_detector(doc_mix: List[JeevesDocument], lang: str) -> None:
    """
    Given a mix of documents from checkpointing, split them into groups
    according to what their shake-to-report categorization is, and run spike
    detection on each of those groups.

    Parameters:
        doc_mix: A mix of documents, which can contain documents with various values for
        shake_to_report_category. All of these documents should be in the same language.
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
            run_spike_detector_for_batch(group_to_run, spike_group, lang)


# TODO require batch to only contain one language and maybe one date?
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
    print(f"Running spike detection for a batch of {spike_group.name} tickets in language {lang}")
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

    word_to_date_to_count = _get_word_to_date_to_count(lang, new_ticket_ids)
    for target_dt in new_ticket_dates:
        batch_spike_list += _find_spiked_words(lang, word_to_date_to_count, target_dt)

    for spike in batch_spike_list:
        spike.spike_group = spike_group

    if batch_spike_list:
        SpikeDAL.bulk_index_spikes(batch_spike_list)


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


def _find_spiked_words(lang, word_to_date_to_count, target_dt) -> List[SpikeWord]:
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
    print(
        f"Calculated spike scores from {target_date_str} for {len(score_word_pairs)} words",
        flush=True,
    )
    score_word_pairs = sorted(score_word_pairs, key=lambda x: x[0], reverse=True)
    result = [
        SpikeWord(word=word, score=score, date=target_date_str, lang=lang, spike_group=None)
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
