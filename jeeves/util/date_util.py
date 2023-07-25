"""
A utility that offers date-related functions.
"""
import datetime
from typing import Iterator, Optional

import pytz
from dateutil.parser import parse

_DATE_FORMAT = "%Y-%m-%d"
_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # ISO Format https://www.w3.org/TR/NOTE-datetime
_OPENSEARCH_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def get_eastern_today():
    """Get datetime object representing right now in US/Eastern (Not UTC!)"""
    time = datetime.datetime.utcnow()
    return convert_timezone(time)


def get_utc_today():
    return datetime.datetime.now(pytz.utc)


def convert_timezone(time, tz_from=None, tz_to=None):
    if tz_from is None:
        tz_from = pytz.timezone("UTC")
    if tz_to is None:
        tz_to = pytz.timezone("US/Eastern")
    return time.replace(tzinfo=tz_from).astimezone(tz=tz_to)


def get_n_days_ago(date_obj, n):
    """
    Returns a date object that represents `n` days before the given date.

    Parameters:
        date_obj: A datetime.date object.
        n: An integer.

    Returns:
        A datetime.date object.
    """
    return date_obj - datetime.timedelta(days=n)


def date_to_str(date_obj: datetime.date) -> str:
    """
    Converts a date object to string.

    Parameters:
        date_obj: A datetime.date object.

    Returns:
        A date string (YYYY-MM-DD).
    """
    assert isinstance(date_obj, datetime.date), f"invalid type: {type(date_obj)}"
    return date_obj.strftime(_DATE_FORMAT)


def datetime_to_str(datetime_obj):
    """
    Converts a date object to string.

    Parameters:
        date_obj: A datetime object.

    Returns:
        A date string (YYYY-MM-DD hh:mm:ss).
    """
    assert isinstance(datetime_obj, datetime.date)
    datetime_str = datetime_obj.strftime(_DATETIME_FORMAT)
    return datetime_str


def str_to_date(date_str):
    """
    Converts a string date to object.

    Parameters:
        date_str: A date string (YYYY-MM-DD).

    Returns:
        A datetime.date object
    """
    _date_str = date_str.split("-")
    return datetime.date(int(_date_str[0]), int(_date_str[1]), int(_date_str[2]))


def time_series_str_to_datetime(date_str) -> Optional[datetime.datetime]:
    if date_str is None or date_str == "":
        return None
    else:
        if "T" in date_str:
            # Remove colon since python <3.6 can't parse it
            if date_str[-3] == ":":
                date_str = date_str[:-3] + date_str[-2:]
            return datetime.datetime.strptime(date_str, _OPENSEARCH_FORMAT)
        return datetime.datetime.strptime(date_str, _DATE_FORMAT)


def parse_external_datetime(datetime_str: str) -> datetime.datetime:
    """
    Parse dates received from external APIs.

    Parameters:
        datetime_str: String representation of a date and time, received
                      from an external API.

    Returns:
        datetime.datetime object corresponding to given string

    """

    parsed_datetime = parse(datetime_str)
    if parsed_datetime.tzinfo is None:
        parsed_datetime = parsed_datetime.replace(tzinfo=pytz.utc)
    return parsed_datetime


def yield_intermediate_dates(
    start_date: datetime.date, end_date: datetime.date
) -> Iterator[datetime.date]:
    """
    Given two dates that represent the endpoints of a range of dates, yield all
    dates between and including the two provided dates.

    If start_date comes after end_date, a ValueError is raised.

    Parameters:
        start_date: Start of date range, first value yielded
        end_date: End of date range, last value yielded

    Yields:
        datetime.date objects representing dates between start_date and end_date
        in chronological order.
    """

    if end_date < start_date:
        raise ValueError(
            f"Inappropriate dates, start_date given as {start_date}, end_date given as {end_date}."
        )

    rover_date = start_date
    while rover_date <= end_date:
        yield rover_date
        rover_date = get_n_days_ago(rover_date, -1)
