"""
Unit tests for the metrics crawler.
"""
import unittest
from datetime import datetime

from jeeves.util.date_util import date_to_str, get_n_days_ago, str_to_date


class Test(unittest.TestCase):
    def test_date_conversions(self):
        date_str = "2015-07-17"
        self.assertEqual(date_to_str(str_to_date(date_str)), date_str)

    def test_get_n_days_ago(self):
        day = datetime(2010, 11, 22)
        self.assertEqual(date_to_str(get_n_days_ago(day, 2)), "2010-11-20")


if __name__ == "__main__":
    unittest.main()
