"""
A library for generating ticket volume over time.
"""

import numpy as np
import pandas as pd

from jeeves.dal.support_tickets import FileSystemSupportTicketDAL

# TODO: Make this more effective. Currently processing all Zendesk data and putting
# it into memory at once, which takes about 2~3 minutes (and is clearly
# problematic), but then all `get_time_series` calls are basically instantaneous
df = pd.DataFrame()
df['tickets'] = list(FileSystemSupportTicketDAL('englishTicketDump.txt').get_labeled_support_tickets())
df.index = df['tickets'].apply(lambda tk: pd.Timestamp(tk.date_time))
df.index.name = 'datetime'

def get_time_series(word, debug=False):
    if debug:
        return _DEBUG_DATA
    # TODO: support start_date & end_date arguments
    assert isinstance(word, str) and word
    counts = df['tickets'].apply(lambda tk: word in tk.description).resample('D').sum().transform(lambda i: 0 if np.isnan(i) else i)
    vals = dict(zip(map(lambda dt: dt.strftime('%Y-%m-%d'), counts.index), counts))
    return {'values': vals}

_DEBUG_DATA = {'values': {'2017-06-01': 10,
                          '2017-06-02': 11,
                          '2017-06-03': 15,
                          '2017-06-04': 34,
                          '2017-06-05': 65,
                          '2017-06-06': 64,
                          '2017-06-07': 39,
                          '2017-06-08': 20,
                          '2017-06-09': 12,
                          '2017-06-10': 10,
                          '2017-06-11': 3,
                          '2017-06-12': 2,
                          '2017-06-13': 1,
                          '2017-06-14': 0,
                          '2017-06-15': 2,
                          '2017-06-16': 55,
                          '2017-06-17': 40,
                          '2017-06-18': 32,
                          '2017-06-19': 21,
                          '2017-06-20': 19,
                          '2017-06-21': 15,
                          '2017-06-22': 15,
                          '2017-06-23': 13,
                          '2017-06-24': 12,
                          '2017-06-25': 19,
                          '2017-06-26': 15,
                          '2017-06-27': 8,
                          '2017-06-28': 3,
                          '2017-06-29': 1,
                          '2017-06-30': 1
                          }
               }
