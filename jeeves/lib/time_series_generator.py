"""
A library for generating ticket volume over time.
"""

import numpy as np
import pandas as pd

from jeeves.dal.support_tickets import ZendeskFileSystemSupportTicketDAL

# TODO: Make this more effective. Currently processing all Zendesk data and putting
# it into memory at once, which takes about 2~3 minutes (and is clearly
# problematic), but then all `get_time_series` calls are basically instantaneous
df = pd.DataFrame()
df['tickets'] = list(ZendeskFileSystemSupportTicketDAL().get_labeled_support_tickets())
df.index = df['tickets'].apply(lambda tk: pd.Timestamp(tk.date_time))
df.index.name = 'datetime'

def get_time_series(word):
    # TODO: support start_date & end_date arguments
    assert isinstance(word, str) and word
    counts = df['tickets'].apply(lambda tk: word in tk.description).resample('D').sum().transform(lambda i: 0 if np.isnan(i) else i)
    vals = dict(zip(map(lambda dt: dt.strftime('%Y-%m-%d'), counts.index), counts))
    return {'values': vals}
