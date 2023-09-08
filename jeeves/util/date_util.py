"""
A utility that offers date-related functions.
"""
from datetime import date, datetime, timedelta
from typing import Any, Iterator, Optional

import pytz
from dateutil.parser import parse

_DATE_FORMAT = "%Y-%m-%d"
_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # ISO Format https://www.w3.org/TR/NOTE-datetime
_OPENSEARCH_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
_SYSTEM_PROMPT_PREFIX = "The current date and time is {}.\n"


def get_eastern_today() -> datetime:
    """Get datetime object representing right now in US/Eastern (Not UTC!)"""
    time = datetime.utcnow()
    return convert_timezone(time)


def get_utc_today() -> datetime:
    return datetime.now(pytz.utc)


# Set types to Any because pytz package is not typed and it's not clean to work around it
def convert_timezone(
    time: datetime,
    tz_from: Any = None,
    tz_to: Any = None,
) -> datetime:
    if tz_from is None:
        tz_from = pytz.timezone("UTC")
    if tz_to is None:
        tz_to = pytz.timezone("US/Eastern")
    return time.replace(tzinfo=tz_from).astimezone(tz=tz_to)


def get_n_days_ago(date_obj: date, n: int) -> date:
    """
    Returns a date object that represents `n` days before the given date.

    Parameters:
        date_obj (date): The relative date
        n (int): Number of days to go back

    Returns:
        A new date object that is `n` days in the past
    """
    return date_obj - timedelta(days=n)


def date_to_str(date_obj: date) -> str:
    """
    Converts a date object to string.

    Parameters:
        date_obj (date): A date object.

    Returns:
        A date string (YYYY-MM-DD).
    """
    assert isinstance(date_obj, date), f"invalid type: {type(date_obj)}"
    return date_obj.strftime(_DATE_FORMAT)


def datetime_to_str(datetime_obj: datetime) -> str:
    """
    Converts a datetime object to string.

    Parameters:
        datetime_obj (datetime): A datetime object

    Returns:
        A date string (YYYY-MM-DD hh:mm:ss).
    """
    assert isinstance(datetime_obj, datetime)
    datetime_str = datetime_obj.strftime(_DATETIME_FORMAT)
    return datetime_str


def str_to_date(date_str: str) -> date:
    """
    Converts an ISO date string to a date object.

    Parameters:
        date_str: An ISO date string (YYYY-MM-DD).

    Returns:
        A date object
    """
    _date_str = date_str.split("-")
    return date(int(_date_str[0]), int(_date_str[1]), int(_date_str[2]))


def time_series_str_to_datetime(date_str: str) -> Optional[datetime]:
    if date_str is None or date_str == "":
        return None
    else:
        if "T" in date_str:
            # Remove colon since python <3.6 can't parse it
            if date_str[-3] == ":":
                date_str = date_str[:-3] + date_str[-2:]
            return datetime.strptime(date_str, _OPENSEARCH_FORMAT)
        return datetime.strptime(date_str, _DATE_FORMAT)


def parse_external_datetime(datetime_str: str) -> datetime:
    """
    Parse dates received from external APIs.

    Parameters:
        datetime_str: String representation of a date and time, received
                      from an external API.

    Returns:
        datetime object corresponding to given string

    """

    parsed_datetime = parse(datetime_str)
    if parsed_datetime.tzinfo is None:
        parsed_datetime = parsed_datetime.replace(tzinfo=pytz.utc)
    return parsed_datetime


def yield_intermediate_dates(start_date: date, end_date: date) -> Iterator[date]:
    """
    Given two dates that represent the endpoints of a range of dates, yield all
    dates between and including the two provided dates.

    If start_date comes after end_date, a ValueError is raised.

    Parameters:
        start_date (date): Start of date range, first value yielded
        end_date (date): End of date range, last value yielded

    Yields:
        date objects representing dates between start_date and end_date in chronological order.
    """

    if end_date < start_date:
        raise ValueError(
            f"Inappropriate dates, start_date given as {start_date}, end_date given as {end_date}."
        )

    rover_date = start_date
    while rover_date <= end_date:
        yield rover_date
        rover_date = get_n_days_ago(rover_date, -1)


def get_date_prefix_for_system_prompt() -> str:
    """
    Returns a string that can be prepended to system prompts to give GPT information about the current date.
    """
    date_str = datetime_to_str(datetime.utcnow())
    return _SYSTEM_PROMPT_PREFIX.format(date_str)


def get_datetime_from_date(date_obj: date) -> datetime:
    """
    Converts a date object to a datetime object (using the time at UTC midnight).

    Parameters:
        date_obj (date): A date object.

    Returns:
        A datetime object at midnight UTC..
    """
    return datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=pytz.utc)
