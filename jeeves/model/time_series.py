import operator
import pandas as pd

from jeeves.dal.config.metadata import STATS_FIELD_TITLES
from jeeves.dal.support_tickets import SupportTicketDAL

class TimeSeries(object):

    def __init__(self):
        self.__df = None

    @property
    def df(self):
        if self.__df is None:
            self.__init_df()
        return self.__df

    def __init_df(self):
        _df = pd.DataFrame()
        _df['tickets'] = pd.Series(st for st in SupportTicketDAL.get_labeled_support_tickets())
        _df['id'] = _df['tickets'].map(operator.attrgetter('ticket_id'))
        _df.drop_duplicates(subset='id', inplace=True)
        del _df['id']

        print('main', _df.shape)

        _metadf = pd.DataFrame.from_records(dict(zip(STATS_FIELD_TITLES, operator.attrgetter(*STATS_FIELD_TITLES)(tk.metadata))) for tk in _df['tickets'])
        _metadf = _metadf.apply(pd.Categorical)

        print('meta', _metadf.shape)

        _df = _df.join(_metadf)

        print('joined', _metadf.shape)

        _df.set_index(
            _df['tickets'].apply(lambda tk: pd.Timestamp(tk.date_time)),
            inplace=True
        )
        _df.sort_index(inplace=True)
        self.__df = _df

TS = TimeSeries()
