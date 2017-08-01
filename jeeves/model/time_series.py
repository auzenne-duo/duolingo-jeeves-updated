import operator
import pandas as pd

from jeeves.dal.config.metadata import STATS_FIELD_TITLES
from jeeves.dal.support_tickets import SupportTicketDAL

class TimeSeries(object):

    def __init__(self):
        self.__df = None
        self.JAN_FIRST = pd.Timestamp('2017-01-01', tz='UTC')

    @property
    def df(self):
        if self.__df is None:
            self.__init_df()
        return self.__df

    def __init_df(self):
        _df = pd.DataFrame()

        _df['tickets'] = pd.Series(
            st
            for st in SupportTicketDAL.get_labeled_support_tickets()
            if pd.Timestamp(st.date_time) > self.JAN_FIRST
        )
        print('predrop', _df.shape)
        _df['id'] = _df['tickets'].map(operator.attrgetter('ticket_id'))
        _df.drop_duplicates(subset='id', inplace=True)
        del _df['id']

        print('main', _df.shape)

        _df.set_index(
            _df['tickets'].map(lambda tk: pd.Timestamp(tk.date_time)),
            inplace=True
        )
        _df.sort_index(inplace=True)

        print('set and sorted index')

        for field in STATS_FIELD_TITLES:
            # pylint: disable=W0640
            _df[field] = _df['tickets'].map(lambda tk: getattr(tk.metadata, field)).astype('category', copy=False)

        print('loaded metadata cols')

        self.__df = _df

TS = TimeSeries()
