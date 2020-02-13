"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
from collections import Counter, defaultdict
import re
import time

import numpy as np
from tqdm import tqdm

from jeeves.config.config import COUNT_THRESHOLD, HISTORY_WINDOW_SIZE, SPIKE_THRESHOLD
from jeeves.dal.spikes import SpikeDAL
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.util.date_util import convert_timezone, date_to_str, get_eastern_today, get_n_days_ago
from jeeves.util.email_preprocessor import cleanup_email
from jeeves.util.tokenizer import Tokenizer


def run_spike_detector():
    today = get_eastern_today()  # Shouldn't be UTC
    word_to_date_to_count = _get_word_to_date_to_count()
    new_spikes = {}
    for i in range(3):
        target_dt = get_n_days_ago(today, i)
        new_spikes.update(_find_spiked_words(word_to_date_to_count, target_dt))
    SpikeDAL.add_spikes(new_spikes)


def _get_word_to_date_to_count():
    tokenizer = Tokenizer()
    date_to_counter = defaultdict(Counter)
    tickets = SupportTicketDAL.get_labeled_support_tickets()

    # We use set for tickets -- multiple word occurrences within a ticket doesn't increase counts.
    # If multiple tickets were created by the same user on a given day, text got concatenated.
    unique_tickets = defaultdict(list)
    for ticket in tickets:
        date = date_to_str(convert_timezone(ticket.date_time))
        unique_tickets[(date, ticket.requester_id)] += [
            ticket.subject,
            cleanup_email(ticket.description),
        ]

    for (date, _), ticket_texts in unique_tickets.items():
        # Has to convert to Eastern from UTC before indexing data by date string
        words = set(
            word for word in tokenizer.tokenize(" ".join(ticket_texts)) if _valid_word(word)
        )
        date_to_counter[date].update(words)
    word_to_date_to_count = {}
    for date, counter in date_to_counter.items():
        for word, count in counter.items():
            if word not in word_to_date_to_count:
                word_to_date_to_count[word] = {_date: 0 for _date in date_to_counter.keys()}
            word_to_date_to_count[word][date] = count
    print("num words = %s" % len(word_to_date_to_count))
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
    print("%s spiked words found on %s:" % (len(result["spike"]), target_date_str))
    for score, word in result["spike"]:
        print("%.2f %2d %s" % (score, word_to_date_to_count[word][target_date_str], word))
    print("%s new words found on %s:" % (len(result["new"]), target_date_str))
    for pair in result["new"]:
        print(pair)
    print("Done in %.3f sec." % (time.time() - start))
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


def _valid_word(word):
    # Word should be at least 3 words and can have chars [a-zA-Z] only.
    return bool(re.search(r"^[a-zA-Z]{3,}$", word))
