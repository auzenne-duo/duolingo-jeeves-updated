import operator
import pandas as pd

from jeeves.dal.config.metadata import STATS_FIELD_TITLES
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.util.date_util import datetime_to_str, get_eastern_today, get_n_days_ago

# Jeeves shows tickets for the past `MOST_RECENT_N_DAYS` days
MOST_RECENT_N_DAYS = 60


class TimeSeries(object):

    def __init__(self):
        self.__df = None
        self.ORIGIN_DATE = get_n_days_ago(get_eastern_today(), MOST_RECENT_N_DAYS)

    @property
    def df(self):
        if self.__df is None:
            self.__init_df()
        return self.__df

    def reload_cache(self):
        self.__init_df()

    def __init_df(self):
        _df = pd.DataFrame()

        # Slow! Load tickets.
        support_tickets = SupportTicketDAL.get_labeled_support_tickets()

        # Obtain recent tickets only
        _df['tickets'] = pd.Series(st for st in support_tickets if st.date_time > self.ORIGIN_DATE)
        print('predrop', _df.shape)
        _df['id'] = _df['tickets'].map(operator.attrgetter('ticket_id'))
        _df.drop_duplicates(subset='id', inplace=True)
        del _df['id']

        print('main', _df.shape)

        _df.set_index(
            _df['tickets'].map(lambda tk: pd.Timestamp(datetime_to_str(tk.date_time), tz='UTC')),
            inplace=True
        )
        _df.sort_index(inplace=True)

        print('set and sorted index')

        for field in STATS_FIELD_TITLES:
            # pylint: disable=W0640
            _df[field] = (
                _df['tickets'].map(lambda tk: getattr(tk.metadata, field))
                .astype('category', copy=False)
            )

        print('loaded metadata cols')

        self.__df = _df


TS = TimeSeries()
