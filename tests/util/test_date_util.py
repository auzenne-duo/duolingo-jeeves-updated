import datetime
import unittest

import pytz

from jeeves.util.date_util import (
    convert_timezone,
    date_to_str,
    get_eastern_today,
    get_n_days_ago,
    get_utc_today,
    str_to_date,
    yield_intermediate_dates,
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

    def test_intermediate_dates(self):
        week_dates = [str_to_date(f"2000-01-0{i+1}") for i in range(7)]

        # Check that giving dates out of order causes an exception
        self.assertRaises(ValueError, next, yield_intermediate_dates(week_dates[5], week_dates[2]))

        # Check that giving start and end as the same date returns that date
        single_date_list = list(yield_intermediate_dates(week_dates[3], week_dates[3]))
        self.assertEqual(len(single_date_list), 1)
        self.assertEqual(week_dates[3], single_date_list[0])

        # Check that giving two endpoints of a range gives all dates inbetween
        self.assertEqual(week_dates, list(yield_intermediate_dates(week_dates[0], week_dates[6])))
