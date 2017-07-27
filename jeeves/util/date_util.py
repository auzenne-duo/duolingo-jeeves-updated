"""
A utility that offers date-related functions.
"""
import datetime


_DATE_FORMAT = '%Y-%m-%d'

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

def date_to_str(date_obj):
    """
    Converts a date object to string.

    Parameters:
        date_obj: A datetime.date object.

    Returns:
        A date string (YYYY-MM-DD).
    """
    assert isinstance(date_obj, datetime.date)
    return date_obj.strftime(_DATE_FORMAT)


def str_to_date(date_str):
    """
    Converts a string date to object.

    Parameters:
        date_str: A date string (YYYY-MM-DD).

    Returns:
        A datetime.date object
    """
    _date_str = date_str.split('-')
    return datetime.date(int(_date_str[0]), int(_date_str[1]), int(_date_str[2]))
