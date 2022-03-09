import sys

from elasticsearch_dsl.response import Response
from requests.exceptions import RequestException


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


class SearchUnsuccessfulException(Exception):
    """Exception raised for unsuccessful Elasticsearch searches

    Attributes:
        response -- the response returned from the call the execute().
        search_description -- a short description of what we were trying to search for.
    """

    def __init__(self, response: Response, search_description: str):
        self.response = response
        self.search_description = search_description
        super().__init__()

    def __str__(self):
        return f"""Search '{self.search_description}' failed.
Here's what the call to execute() returned:
{self.response.to_dict()}"""


class SpikeDetectorException(Exception):
    """Exception raised while performing spike detection"""

    def __init__(self, message: str):
        super().__init__(message)
