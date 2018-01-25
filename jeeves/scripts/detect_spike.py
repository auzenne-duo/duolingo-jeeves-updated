"""
A script for finding spikes of word occurrences in Zendesk tickets.
Candidate words are from Zendesk tickets on a target date.
"""
from collections import Counter
import json
import os
import re
import string
import time

import numpy as np
from tqdm import tqdm

from jeeves.lib.time_series_generator import get_recent_tickets_by_word, get_time_series
from jeeves.util.date_util import date_to_str, get_eastern_today, get_n_days_ago, str_to_date
from jeeves.util.s3 import S3, S3_BUCKET_ID, S3_SPIKE_DIR

_CONTENT_TYPE = 'text/plain; charset=utf-8'

# On the target day, the word has to occur at least this many times to be considered as a candidate.
_COUNT_THRESHOLD = 5

# We compare word occurrences in the past these days.
_HISTORY_WINDOW_SIZE = 50

# For spikes, occurrences should be at least five-sigma away from historical values.
_SPIKE_THRESHOLD = 5


def find_spiked_words(target_date_str, debug=False):
    """
    Parameters:
        target_date_str: The target date to detect spike (YYYY-MM-DD).
        debug: Whether to debug this function (runs faster on a small sample).
    """
    start = time.time()
    words = _find_candidate_words(target_date_str)
    print('%s candidate words found.' % len(words))
    if debug:
        words = words[:10]
    score_word_pairs = [(_calculate_spike_score(word, target_date_str=target_date_str), word)
                        for word in tqdm(words, desc='Calculate spikiness scores')]
#     score_word_pairs = [(score, word) for (score, word) in score_word_pairs
#                         if not np.isnan(score) and score > _SPIKE_THRESHOLD]
    score_word_pairs = sorted(score_word_pairs, key=lambda x: x[0], reverse=True)
    result = {}
    result['spike'] = [(score, word) for score, word in score_word_pairs
                       if (not np.isnan(score)
                           and not np.isinf(score)
                           and score > _SPIKE_THRESHOLD)]
    result['new'] = [word for score, word in score_word_pairs if np.isinf(score)]
    print('%s spiked words found on %s:' % (len(result['spike']), target_date_str))
    for pair in result['spike']:
        print(pair)
    print('%s new words found on %s:' % (len(result['new']), target_date_str))
    for pair in result['new']:
        print(pair)
    if not debug:
        S3.upload(S3_BUCKET_ID, os.path.join(S3_SPIKE_DIR, target_date_str),
                  json.dumps(result), _CONTENT_TYPE)
    print('Done in %s sec.' % (time.time() - start))


_TABLE = str.maketrans({ch: None for ch in string.punctuation})


def _find_candidate_words(target_date_str):
    """
    Returns a list of words occurred more than `count_threshold` times in tickets on the target
    date.
    """
    end_time = get_n_days_ago(str_to_date(target_date_str), -1)
    tickets = get_recent_tickets_by_word('', start_time=target_date_str, end_time=end_time)

    def ticket_to_words(ticket):
        return set(word for attr in ('subject', 'description')
                   for word in getattr(ticket, attr).translate(_TABLE).lower().split())

    # A dict from word to number of ticket this word appears during the time span.
    word_counts = Counter(w for ticket in tickets for w in ticket_to_words(ticket))
    # Filter by threshold
    words = [word for word, count in word_counts.items()
             if count >= _COUNT_THRESHOLD and _valid_word(word)]
    return words


def _calculate_spike_score(word, target_date_str='2017-07-16'):
    """
    Given a word, returns a score that represents spikiness where spikiness is a z-score
    computed based on word occurrences in the previous `moving_avg_window_size` days.

    https://stackoverflow.com/questions/22583391/peak-signal-detection-in-realtime-timeseries-data
    """
    end_date_obj = str_to_date(target_date_str)
    start_date_obj = date_to_str(get_n_days_ago(end_date_obj, _HISTORY_WINDOW_SIZE))

    date_to_count = get_time_series(re.escape(word),
                                    start_time=start_date_obj,
                                    end_time=get_n_days_ago(end_date_obj, -1))['values']
    count_history = [date_to_count.get(date_to_str(get_n_days_ago(end_date_obj, i+1)), 0)
                     for i in range(_HISTORY_WINDOW_SIZE)]
    mean = np.mean(count_history)
    std = np.std(count_history)
    target_count = date_to_count.get(date_to_str(end_date_obj), 0)
    zscore = (target_count - mean) / std if std != 0 else np.inf
    return zscore


def _valid_word(word):
    return not bool(re.search(r'^\d+$', word))


if __name__ == '__main__':
    today = get_eastern_today()
    for i in range(7):
        date_str = date_to_str(get_n_days_ago(today, i))
        find_spiked_words(date_str)
