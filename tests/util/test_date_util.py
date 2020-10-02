import datetime
import pytz
import unittest

from jeeves.util.date_util import (
    convert_timezone,
    date_to_str,
    get_eastern_today,
    get_n_days_ago,
    get_utc_today,
    str_to_date,
)


class Test(unittest.TestCase):
    def test_conversion(self):
        eastern_dt = get_eastern_today()
        utc_dt = get_utc_today()
        converted_dt = convert_timezone(
            utc_dt, tz_from=pytz.timezone("UTC"), tz_to=pytz.timezone("US/Eastern")
        )
        self.assertTrue(converted_dt - eastern_dt < datetime.timedelta(milliseconds=100))

    def test_get_n_days_ago(self):
        utc_dt = get_utc_today()
        self.assertEqual(get_n_days_ago(utc_dt, 1) - utc_dt, datetime.timedelta(days=-1))
        self.assertEqual(get_n_days_ago(utc_dt, -1) - utc_dt, datetime.timedelta(days=1))

    def test_str_conversion(self):
        self.assertEqual(date_to_str(str_to_date("2018-01-01")), "2018-01-01")
