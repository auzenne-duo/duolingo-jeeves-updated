"""
A library for generating ticket volume over time.
"""

from dateutil.parser import parse
import numpy as np
import pandas as pd
import re

from jeeves.dal.config.metadata import SEMANTIC_FIELD_TITLES, STATS_FIELD_TITLES
from jeeves.model.metadata import Metadata
from jeeves.model.time_series import TS
from jeeves.util.cache import CacheHandler
from jeeves.util.date_util import convert_timezone, datetime_to_str, get_n_days_ago

_SEARCH_REGEX = r'\b(?:{0})\b'


def _compile_search_regex(word):
    return re.compile(_SEARCH_REGEX.format(word), flags=re.I | re.U)


@CacheHandler.cache(maxsize=32, typed=False)
def match_description(word, start_time=None, end_time=None, meta_filter=Metadata({})):
    # end_time doesn't have to be incremented for 1 day

    ser = TS.df.loc[start_time:end_time]['tickets']
    meta_match = lambda tk: all(getattr(tk.metadata, field) == val
                                for field, val in meta_filter.items() if val != '')
    if word:
        match = _compile_search_regex(word)
        desc_match = lambda tk: bool(match.search(tk.description))
        if meta_filter:
            return ser.map(lambda tk: meta_match(tk) and desc_match(tk))
        else:
            return ser.map(desc_match)
    else:
        if meta_filter:
            return ser.map(meta_match)
        else:
            return pd.Series(np.full(len(ser), True, dtype=np.bool8), index=ser.index)


@CacheHandler.cache(maxsize=32, typed=False)
def get_time_series(word, start_time=None, end_time=None, meta_filter=Metadata({})):
    """
    Returns time series of, on a daily basis, number of tickets that match a particular keyword

    Arguments:
        word {str} -- A regular expression to search descriptions for

    Keyword Arguments:
        start_time {pd.Timestamp} -- Datetime to start recording data from (default: {None})
        end_time {pd.Timestamp} -- Datetime to end recording data from (default: {None})
        meta_filter {dict} -- mapping from metadata field names to acceptable value (default: {None})
    """
    assert isinstance(word, str) and word
    if end_time:
        # end_time has to be incremented for 1 day!!
        end_time = get_n_days_ago(end_time, -1)
    counts = (
        match_description(word, start_time, end_time, meta_filter).astype(int, copy=False)
        .resample('D').sum().transform(lambda i: 0 if np.isnan(i) else i)
    )
    vals = dict(zip(map(lambda dt: dt.strftime('%Y-%m-%d'), counts.index), counts))
    return {'values': vals}


@CacheHandler.cache(maxsize=32, typed=False)
def get_recent_tickets_by_word(word, start_time=None, end_time=None, meta_filter=Metadata({})):
    assert isinstance(word, str)
    if end_time:
        # end_time has to be incremented for 1 day!!
        end_time = get_n_days_ago(end_time, -1)
    if word:
        matched_mask = match_description(word, start_time, end_time, meta_filter)
        try:
            return TS.df.loc[start_time:end_time][matched_mask]['tickets']
        except KeyError:
            print('Data missing for the timespan (%s, %s). Please update.' % (start_time, end_time))
            raise
    else:
        return TS.df.loc[start_time:end_time]['tickets']


def get_most_recent_ticket_timestamp():
    """ Returns the timestamp (YYYY:MM:DD hh:mm:ss in US/Eastern) of most recent ticket. """
    dt_str = TS.df.ix[-1]['tickets'].date_time
    dt = parse(dt_str)
    return datetime_to_str(convert_timezone(dt))


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
def get_viable_categories_in_metadata_distribution(start_time, end_time, min_prob=0.001):
    # end_time doesn't have to be incremented for 1 day

    matched_mask = match_description('', start_time, end_time)
    matched_meta = TS.df.loc[start_time:end_time][matched_mask][SEMANTIC_FIELD_TITLES]
    return {
        col: set(matched_meta[col].value_counts(normalize=True)[lambda p: p > min_prob].index)
        for col in matched_meta.columns
    }


@CacheHandler.cache(maxsize=32, typed=False)
def get_metadata_distribution(word, start_time=None, end_time=None, meta_filter=Metadata({})):
    if end_time:
        # end_time has to be incremented for 1 day!!
        end_time = get_n_days_ago(end_time, -1)
    matched_mask = match_description(word, start_time, end_time, meta_filter)
    matched_meta = TS.df.loc[start_time:end_time][matched_mask][STATS_FIELD_TITLES]
    viable_categories = get_viable_categories_in_metadata_distribution(start_time, end_time)
    freq_dict = {
        col: {
            k: v
            for k, v in matched_meta[col].value_counts(normalize=True).iteritems()
            if k != ''  # not counting the unpopulated fields
            and k in viable_categories[col
                                      ]  # as long as k is a mildly plausible (non-noise) category
        }
        for col in viable_categories
    }
    return freq_dict
