"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
from collections import Counter, defaultdict
import time

import numpy as np
from tqdm import tqdm

from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.spikes import SpikeDAL
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.util.date_util import convert_timezone, date_to_str, get_eastern_today, get_n_days_ago


def run_spike_detector(language):
    """
    Runs the spike detector algorithm for a specified language

    Parameters:
        language(SUPPORTED_LANGUAGES): A language enum; which language to run
            spike detection on.
    """
    today = get_eastern_today()  # Shouldn't be UTC
    word_to_date_to_count = _get_word_to_date_to_count(language)
    new_spikes = {}
    for i in range(3):
        target_dt = get_n_days_ago(today, i)
        new_spikes.update(_find_spiked_words(word_to_date_to_count, target_dt))
    SpikeDAL.add_spikes(new_spikes, language.name)


def _get_word_to_date_to_count(language):
    date_to_counter = defaultdict(Counter)
    tickets = SupportTicketDAL.get_labeled_support_tickets(language)

    # We use set for tickets -- multiple word occurrences within a ticket doesn't increase counts.
    # If multiple tickets were created by the same user on a given day, text got concatenated.
    unique_tickets = defaultdict(list)
    for ticket in tickets:
        date = date_to_str(convert_timezone(ticket.date_time))
        if ticket.tokens:
            unique_tickets[(date, ticket.requester_id)] += ticket.tokens

    for (date, _), ticket_tokens in unique_tickets.items():
        words = set(ticket_tokens)
        date_to_counter[date].update(words)
    word_to_date_to_count = {}
    for date, counter in date_to_counter.items():
        for word, count in counter.items():
            if word not in word_to_date_to_count:
                word_to_date_to_count[word] = {_date: 0 for _date in date_to_counter.keys()}
            word_to_date_to_count[word][date] = count
    print(f"num words = {len(word_to_date_to_count)}")
    return word_to_date_to_count


def _find_spiked_words(word_to_date_to_count, target_dt):
    target_date_str = date_to_str(target_dt)
    print("Spike detection started for", target_date_str)
    start = time.time()

    score_word_pairs = [
        (_calculate_spike_score(date_to_count, target_dt), word)
        for word, date_to_count in tqdm(
            word_to_date_to_count.items(), desc="Calculate spikiness scores"
        )
    ]
    score_word_pairs = sorted(score_word_pairs, key=lambda x: x[0], reverse=True)
    result = {
        "spike": [
            (score, word)
            for score, word in score_word_pairs
            if (not np.isnan(score) and not np.isinf(score) and score > SPIKE_THRESHOLD)
        ],
        "new": [word for score, word in score_word_pairs if np.isinf(score)],
    }
    print(f"{len(result['spike'])} spiked words found on {target_date_str}:")
    for score, word in result["spike"]:
        print(f"{score:.2f} {word_to_date_to_count[word][target_date_str]:2d} {word}")
    print(f"{len(result['new'])} new words found on {target_date_str}:")
    for pair in result["new"]:
        print(pair)
    print(f"Done in {(time.time() - start):.3f} sec.")
    return {target_date_str: result}


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
