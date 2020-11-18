from requests.exceptions import RequestException
import sys


def print_request_exception(e: RequestException):
    print(
        f"""
        An exception occurred for the following request:
        {e.request}
        The above request generated the following response:
        {e.response}
        """,
        file=sys.stderr,
    )
