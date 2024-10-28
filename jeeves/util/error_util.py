import logging
import sys
from typing import Optional

import duo_logging
from opensearch_dsl.response import Response
from requests.exceptions import RequestException

LOG = logging.getLogger(__name__)


def print_request_exception(e: RequestException, log_level: Optional[str] = None) -> None:
    """Print information about a RequestException.

    Parameters:
        e: The RequestException, probably raised by .raise_for_status()
        log_level: "critical", "error", "warning", "info", "debug", or None. (Only "critical" and "error"
            will be reported to Sentry.)
    """
    method = e.request.method if e.request is not None else None
    url = e.request.url if e.request is not None else None
    status_code = e.response.status_code if e.response is not None else None
    reason = e.response.reason if e.response is not None else None
    headers = e.response.headers if e.response is not None else None
    body = e.response.text if e.response is not None else None
    error_str = f"""
        An exception occurred for the following request:
        {method} {url}
        The above request generated the following response:
        {status_code}: {reason}
        Returned headers: {headers}
        Returned body: {body}
        """
    if log_level == "error" or log_level == "critical":
        LOG.error(error_str)
        duo_logging.capture_exception(
            sys.exc_info(),
            extra_data={
                "headers": headers,
                "body": body,
            },
        )
    elif log_level == "warning":
        LOG.warning(error_str)
    else:
        LOG.info(error_str)


class SearchUnsuccessfulException(Exception):
    """Exception raised for unsuccessful OpenSearch searches

    Attributes:
        response -- the response returned from the execute() call.
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
