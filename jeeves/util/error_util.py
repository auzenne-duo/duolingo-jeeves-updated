import sys

import rollbar
from elasticsearch_dsl.response import Response
from requests.exceptions import RequestException


def print_request_exception(e: RequestException):
    status_code = e.response.status_code if e.response is not None else None
    reason = e.response.reason if e.response is not None else None
    print(
        f"""
        An exception occurred for the following request:
        {e.request}
        The above request generated the following response:
        {status_code}: {reason}
        """,
        file=sys.stderr,
    )
    rollbar.report_exc_info(sys.exc_info())


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


class SpikeReporterException(Exception):
    """Exception raised while running the spike reporter bot"""

    def __init__(self, message: str):
        super().__init__(message)
