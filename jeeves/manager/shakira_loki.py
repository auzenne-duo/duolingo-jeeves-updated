import io
import logging
import re
from datetime import datetime
from typing import List

import pytz
from requests import post

from jeeves.lib.profiling import traced_function
from jeeves.manager.shakira_jira import ShakiraJiraApiClient

LOG = logging.getLogger(__name__)

_HOST = "https://loki-prod.duolingo.com"
_API = f"{_HOST}/loki/api/v1/push"
_EXPECTED_IOS_TIMESTAMP_FORMAT = r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}:\d{3}$"
_IOS_DATE_FORMAT = "%Y/%m/%d %H:%M:%S:%f"
_CATEGORY_LABEL_MAPPING = {
    "id": "user_id",
    "time zone": "time_zone",
    "device model": "device_model",
    "app version": "app_version",
}
_BILLION = 1_000_000_000


class ShakiraLokiApiClient:
    """
    This class handles the logic to upload a client-submitted log into Loki for
    easier querying and debugging. It only supports parsing iOS logs for now, but
    if enough people use it, let's expand it to support Android.
    """

    def parse_logs_ios(self, text_file: io.TextIOWrapper) -> List[List[str]]:
        """
        Parses logs from iOS into a stream that Loki can ingest.

        This relies on the iOS logs being a certain format. To see what it might look like,
        see `jira_api_response_ios.json` in the tests directory. To see the expected output,
        see `test_shakira_loki_client.py`.
        """
        lines = []
        current_line = ""
        current_date = ""

        for line in text_file:
            line = line.strip()
            parts = line.split("  ")
            date_string = parts[0]
            if re.match(_EXPECTED_IOS_TIMESTAMP_FORMAT, date_string):
                # The timestamp is in UTC as far as I can tell
                datetime_object = datetime.strptime(date_string + "000", _IOS_DATE_FORMAT).replace(
                    tzinfo=pytz.utc
                )
                # Loki expects the timestamp in nanoseconds
                nanoseconds = int(datetime_object.timestamp() * _BILLION)
                if current_line and current_date:
                    lines.append([current_date, current_line])
                current_date = str(nanoseconds)
                current_line = "".join(parts[1:])
            else:
                current_line += line

        if current_line and current_date:
            lines.append([current_date, current_line])
        return lines

    def extract_iOS_reporter_information(self, ticket_content):
        """
        This extracts information about the original reporter in a Jira ticket.
        This is used to add information to the labels when we submit to Loki.
        For more detailed information about the expected input and output, see
        `test_shakira_loki_client.py`.
        """
        mappings = []

        for section in ticket_content:
            if section["type"] == "bulletList":
                for item in section["content"]:
                    if item["type"] == "listItem":
                        bulleted_item = item["content"][0]["content"]
                        mappings.append(
                            [obj.get("text", "").replace(": ", "") for obj in bulleted_item]
                        )

        return mappings

    @traced_function()
    def upload_to_loki(
        self, jira_client: ShakiraJiraApiClient, jira_issue_key: str, text_file: io.TextIOWrapper
    ):
        details = jira_client.get_issue_details(jira_issue_key)
        mappings = self.extract_iOS_reporter_information(
            details["fields"]["description"]["content"]
        )

        stream_labels = {"service": "ios_app"}
        stream_labels["jira_issue_key"] = jira_issue_key
        stream_labels["jira_ticket_title"] = details["fields"]["summary"]
        for mapping in mappings:
            if mapping[0] in _CATEGORY_LABEL_MAPPING:
                stream_labels[_CATEGORY_LABEL_MAPPING[mapping[0]]] = mapping[1]

        log_values = self.parse_logs_ios(text_file)

        if not log_values:
            raise Exception(f"unable to upload any logs for jira ticket: {jira_issue_key}")

        body = {"streams": [{"stream": stream_labels, "values": log_values}]}

        response = post(_API, headers={"Content-Type": "application/json"}, json=body)
        response.raise_for_status()
