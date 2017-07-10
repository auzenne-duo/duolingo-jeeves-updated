"""
A library for generating ticket volume over time.
"""

import numpy as np
import pandas as pd
import re

from jeeves.dal.support_tickets import FileSystemSupportTicketDAL

# TODO: Make this more effective. Currently preprocessed all Zendesk data
# and stored it to disk. Loading it takes about 2~3 seconds, but then all
# `get_time_series` calls are basically instantaneous
df = pd.DataFrame()
df['tickets'] = list(FileSystemSupportTicketDAL('tickets-{lang}-{prod}.txt').get_labeled_support_tickets())
df.index = df['tickets'].apply(lambda tk: pd.Timestamp(tk.date_time))
df.index.name = 'datetime'
df = df.sort_index()

_SEARCH_REGEX = r'\b(?:{0})\b'

def _compile_search_regex(word):
    return re.compile(_SEARCH_REGEX.format(word), flags=re.I | re.U)

def get_time_series(word):
    # TODO: support start_date & end_date arguments
    assert isinstance(word, str) and word
    match = _compile_search_regex(word)
    counts = df['tickets'].apply(lambda tk: bool(match.search(tk.description))).resample('D').sum().transform(lambda i: 0 if np.isnan(i) else i)
    vals = dict(zip(map(lambda dt: dt.strftime('%Y-%m-%d'), counts.index), counts))
    return {'values': vals}


def get_recent_tickets_by_word(word, start_time=None, end_time=None):
    assert isinstance(word, str) and word
    match = _compile_search_regex(word)
    matched_tickets = filter(lambda tk: bool(match.search(tk.description)), df[start_time:end_time]['tickets'])
    return matched_tickets

def get_paginated_tickets(page, limit):
    start = -(page * limit) - 1
    end = start - page
    return df.ix[start:end:-1]['tickets']
