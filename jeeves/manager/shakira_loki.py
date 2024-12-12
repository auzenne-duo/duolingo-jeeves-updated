import io
import logging
import re
import string
import time
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
_EXPECTED_ANDROID_TIMESTAMP_FORMAT = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{4}"
_EXPECTED_ANDROID_ZULU_TIMESTAMP_FORMAT = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}Z"
_IOS_DATE_FORMAT = "%Y/%m/%d %H:%M:%S:%f"
_CATEGORY_LABEL_MAPPING = {
    "id": "user_id",
    "time zone": "time_zone",
    "device model": "device_model",
    "app version": "app_version",
    "App version code": "app_version_code",
    "User ID": "user_id",
    "Model (Product)": "device_model",
}
_BILLION = 1_000_000_000
_BATCH_SIZE = 200
_BATCH_SLEEP_TIME = 1


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
    def integrate_ios_info_to_loki(
        self, jira_client: ShakiraJiraApiClient, jira_issue_key: str, text_file: io.TextIOWrapper
    ):
        """
        This integrate labels and logs from IOS Json and Logs file. Compose the request body.
        And call Loki API to upload labels and logs.
        """
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

    @traced_function()
    def parse_logs_android(self, text_file: io.TextIOWrapper) -> List[List[str]]:
        """
        Parses logs from Android into a stream that Loki can ingest.

        This relies on the Android logs being a certain format. To see what it might look like,
        for input and output, see `test_shakira_loki_client.py`.
        """
        lines = []
        current_line = ""
        current_date = ""
        for line in text_file:
            parts = line.split(" ")

            if len(parts) < 2:
                continue

            date_string = parts[0] + " " + parts[1]
            if re.match(_EXPECTED_ANDROID_TIMESTAMP_FORMAT, date_string):
                # Define the format of the timestamp string
                format_str = "%Y-%m-%d %H:%M:%S.%f%z"
                date_string = date_string.strip()
                date_string = date_string[:-5] + "000" + date_string[-5:]
                # Parse the string into a datetime object
                dt = datetime.strptime(date_string, format_str)

                # Get the timestamp in seconds and convert to nanoseconds
                nanoseconds = int(dt.timestamp() * _BILLION)
                current_date = str(nanoseconds)

                current_line = " ".join(parts[2:]).strip()
                if any(char not in string.printable for char in current_line):
                    current_line = ""
            elif re.match(_EXPECTED_ANDROID_ZULU_TIMESTAMP_FORMAT, date_string):
                # ZULU time format is special, we need to handle it separately
                format_str = "%Y-%m-%d %H:%M:%S.%fZ"
                date_string = date_string.strip()
                date_string = date_string[:-1] + "000" + date_string[-1:]
                # Parse the string into a datetime object
                dt = datetime.strptime(date_string, format_str)

                # Get the timestamp in seconds and convert to nanoseconds
                nanoseconds = int(dt.timestamp() * _BILLION)
                current_date = str(nanoseconds)

                current_line = " ".join(parts[2:]).strip()
                if any(char not in string.printable for char in current_line):
                    current_line = ""
            else:
                current_line = ""

            if current_line and current_date:
                if len(current_date) == 19:
                    lines.append([current_date, current_line])
                else:
                    LOG.error(f"Invalid date format: {current_date}")
        return lines

    @traced_function()
    def extract_android_reporter_information(self, ticket_content):
        """
        This extracts information about the original reporter in a Jira ticket.
        This is used to add information to the labels when we submit to Loki.
        To see what it might look like, see `jira_api_response_android.json` in the tests directory. To see the expected output,
        see `test_shakira_loki_client.py`.
        """
        mappings = []

        for section in ticket_content:
            if "content" in section:
                content_list = section["content"]
                for item in content_list:
                    if (
                        "marks" not in item
                        and item["type"] == "text"
                        and item["text"]
                        and ":" in item["text"]
                    ):
                        bulleted_item = item["text"].split(":")
                        if len(bulleted_item) > 1 and bulleted_item[1]:
                            mappings.append([bulleted_item[0], "".join(bulleted_item[1:])])
                    elif "marks" in item:
                        mappings.append(["url", item["text"]])

        return mappings

    @traced_function()
    def integrate_android_info_to_loki(
        self, jira_client: ShakiraJiraApiClient, jira_issue_key: str, text_file: io.TextIOWrapper
    ):
        """
        This integrate labels and logs from Andoid Json and Logs file. Compose the request body.
        And batch calling Loki API to upload labels and logs.
        """
        details = jira_client.get_issue_details(jira_issue_key)
        mappings = self.extract_android_reporter_information(
            details["fields"]["description"]["content"]
        )
        stream_labels = {"service": "android_app"}
        stream_labels["jira_issue_key"] = jira_issue_key
        stream_labels["jira_ticket_title"] = details["fields"]["summary"]
        for mapping in mappings:
            if mapping[0] in _CATEGORY_LABEL_MAPPING:
                stream_labels[_CATEGORY_LABEL_MAPPING[mapping[0]]] = mapping[1]

        log_values = self.parse_logs_android(text_file)
        if not log_values:
            raise Exception(f"unable to upload any logs for jira ticket: {jira_issue_key}")

        patched_logs = []
        subbody = {}
        for i, log_value in enumerate(log_values):
            patched_logs.append(log_value)
            # The URL parse to loki have maximum character limit, so batch the logs
            if i % _BATCH_SIZE == 0 and i != 0:
                try:
                    subbody = {"streams": [{"stream": stream_labels, "values": patched_logs}]}
                    response = post(
                        _API, headers={"Content-Type": "application/json"}, json=subbody
                    )
                    response.raise_for_status()
                except Exception as e:
                    LOG.error(f"Error uploading logs to Loki: {e}")
                patched_logs = []
                time.sleep(_BATCH_SLEEP_TIME)

        subbody = {"streams": [{"stream": stream_labels, "values": patched_logs}]}
        response = post(_API, headers={"Content-Type": "application/json"}, json=subbody)
        response.raise_for_status()
