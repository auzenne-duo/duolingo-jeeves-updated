"""
A library for generating ticket volume over time.
"""

import numpy as np
import pandas as pd
import re

from jeeves.dal.config.metadata import STATS_FIELD_TITLES
from jeeves.model.time_series import TS
from jeeves.util.cache import CacheHandler

_SEARCH_REGEX = r'\b(?:{0})\b'

def _compile_search_regex(word):
    return re.compile(_SEARCH_REGEX.format(word), flags=re.I | re.U)

@CacheHandler.cache(maxsize=32, typed=False)
def _match_description(word, start_time=None, end_time=None):
    match = _compile_search_regex(word)
    return TS.df.loc[start_time:end_time]['tickets'].apply(lambda tk: bool(match.search(tk.description)))

@CacheHandler.cache(maxsize=32, typed=False)
def get_time_series(word, start_time=None, end_time=None):
    """
    Returns time series of, on a daily basis, number of tickets that match a particular keyword

    Arguments:
        word {str} -- A regular expression to search descriptions for

    Keyword Arguments:
        start_time {pd.Timestamp} -- Datetime to start recording data from (default: {None})
        end_time {pd.Timestamp} -- Datetime to end recording data from (default: {None})
    """
    assert isinstance(word, str) and word
    counts = (_match_description(word, start_time, end_time)
              .resample('D').sum().transform(lambda i: 0 if np.isnan(i) else i))
    vals = dict(zip(map(lambda dt: dt.strftime('%Y-%m-%d'), counts.index), counts))
    return {'values': vals}

@CacheHandler.cache(maxsize=32, typed=False)
def get_recent_tickets_by_word(word, start_time=None, end_time=None):
    assert isinstance(word, str)
    if word:
        matched_mask = _match_description(word, start_time, end_time)
        return TS.df.loc[start_time:end_time][matched_mask]['tickets']
    else:
        return TS.df.loc[start_time:end_time]['tickets']

def get_paginated_tickets(page, limit, dataframe=None):
    if dataframe is None:
        dataframe = TS.df
    start = -(page * limit + 1)
    end = start - limit
    paginated = dataframe.ix[start:end:-1]
    if isinstance(paginated, pd.DataFrame):
        paginated = paginated['tickets']
    return paginated

@CacheHandler.cache(maxsize=32, typed=False)
def get_metadata_distribution(word, start_time=None, end_time=None):
    matched_mask = _match_description(word, start_time, end_time)
    matched_meta = TS.df.loc[start_time:end_time][matched_mask][STATS_FIELD_TITLES]
    freq_dict = {
        col: {
            k: v
            for k, v in matched_meta[col].value_counts().iteritems()
            if k != ''  # not counting the unpopulated fields
        } for col in matched_meta
    }
    return freq_dict
