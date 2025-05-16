"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple, Union

from duolingo_base.user_agent import DuolingoUserAgent, DuoPlatform
from duolingo_base.util import registry
from requests.exceptions import RequestException
from werkzeug.datastructures import FileStorage

from jeeves import registry as app_registry
from jeeves.config.jira_features import JIRA_FEATURE_TO_TEAM, JIRA_TEAM_TO_AREA
from jeeves.lib.profiling import traced_function
from jeeves.manager.gpt_duplicate_detector import GPTDuplicateDetector
from jeeves.manager.gpt_log_summarizer import GPTLogSummarizer, JiraLogSummarizationTicket
from jeeves.manager.gpt_priority_estimator import GPTPriorityEstimator
from jeeves.manager.gpt_screenshot_summarizer import GPTScreenshotSummarizer
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_loki import ShakiraLokiApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import JiraTicketText
from jeeves.model.slack_channel import (
    ForwardedSlackChannel,
    SlackChannel,
    area_design_quality_channel,
)
from jeeves.util.s3_client_and_bucket import upload_to_jeeves_s3
from jeeves.util.shakira import (
    JIRA_PROJ_TO_PLATFORM,
    JIRA_RELEASE_BLOCKER_LABEL,
    JIRA_VIA_JEEVES_LABEL,
    SHAKE_TO_REPORT_LABEL,
)

LOG = logging.getLogger(__name__)
_VIA_JEEVES_MARKER = "[via Jeeves]"

_SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Design quality": SlackChannel.DESIGN_QUALITY,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_REPORT_TYPE_TO_SLACK_CHANNEL = {
    "Lesson content issue": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS / Visemes / Mouth animations": SlackChannel.FEEDBACK_TTS,
    "Design quality": SlackChannel.DESIGN_QUALITY,
    "Feature request": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_CHANNELS_TO_JIRA_LABELS = {
    SlackChannel.DESIGN_QUALITY: "design-quality",
    SlackChannel.DESIGN_QUALITY_MONETIZATION: "design-quality",
    SlackChannel.DESIGN_QUALITY_GROWTH: "design-quality",
    SlackChannel.DESIGN_QUALITY_LEARNING: "design-quality",
    SlackChannel.DESIGN_QUALITY_NEW_SUBJECTS: "design-quality",
    SlackChannel.LITERACY_TESTING: "shakira",
}

PRIORITIZED_BY_GPT_LABEL = "prioritized-by-gpt"
SLACK_CHANNEL_NAME = "#proj-jeeves"
SLACK_CHANNEL_URL = "https://duolingo.slack.com/archives/C01DFNRES8Y"
SLACK_CHANNEL_MD = f"[{SLACK_CHANNEL_NAME}|{SLACK_CHANNEL_URL}]"

_IOS_LOG_FILENAME = "logs.txt"
ANDROID_LOG_FILE_PATTERN = re.compile(r"^log\d+\.txt$")

DEFAULT_DESCRIPTION = "(no description)"
DEFAULT_ISSUE_SUMMARY = "(no issue summary)"

_SCREENSHOT_FILE_KEY = "screenshot"


@registry.bind(
    gpt_duplicate_detector=registry.reference(GPTDuplicateDetector),
    gpt_log_summarizer=registry.reference(GPTLogSummarizer),
    gpt_priority_estimator=registry.reference(GPTPriorityEstimator),
    gpt_screenshot_summarizer=registry.reference(GPTScreenshotSummarizer),
    jira_client=registry.reference(ShakiraJiraApiClient),
    slack_client=registry.reference(ShakiraSlackApiClient),
)
class ShakiraManager:
    def __init__(
        self,
        gpt_log_summarizer: GPTLogSummarizer,
        gpt_priority_estimator: GPTPriorityEstimator,
        gpt_screenshot_summarizer: GPTScreenshotSummarizer,
        jira_client: ShakiraJiraApiClient,
        slack_client: ShakiraSlackApiClient,
        gpt_duplicate_detector: GPTDuplicateDetector,
        upload_to_s3: Callable[[str, bytes], None] = upload_to_jeeves_s3,
    ):
        self._gpt_log_summarizer = gpt_log_summarizer
        self._gpt_priority_estimator = gpt_priority_estimator
        self._gpt_screenshot_summarizer = gpt_screenshot_summarizer
        self._jira_client = jira_client
        self._slack_client = slack_client
        self._gpt_duplicate_detector = gpt_duplicate_detector
        self._upload_to_s3 = upload_to_s3

    def get_shake_to_report_tokens(self, project: Optional[str]) -> Dict[str, str]:
        """
        Gets API tokens for Jira and Slack depending on the project.

        Parameters:
             project: Platform (e.g., DLAA, DLAI, DLAW)

        Returns:
            Dictionary of API tokens for Jira and Slack.
        """
        jira_token = self._jira_client.get_jira_api_token(project)
        slack_token = self._slack_client.get_slack_api_token()

        return {"jira": jira_token, "slack": slack_token}

    def get_project_error_message(self, project: str) -> Optional[str]:
        """
        If the project is invalid, return an error message. Otherwise return None.
        """
        return (
            f"Invalid project - must be one of {list(JIRA_PROJ_TO_PLATFORM)}"
            if project not in JIRA_PROJ_TO_PLATFORM
            else None
        )

    def get_features(self, projects: Union[str, List[str]]) -> List[str]:
        """
        Get possible values for the "Feature" issue field in a project.

        parameters
            projects: e.g. DLAA, DLAI, DLAW
        """
        return self._jira_client.get_features(projects)

    def get_slack_report_types(self) -> List[Dict[str, Union[str, bool]]]:
        """
        Returns a list of report types that go to Slack.

        returns: a List[Dict[str, Union[str, bool]]], each dict containing the following fields:
            - "name": the name of the Slack report type.
            - "alsoPostsToJira": whether this Slack report type will also create a Jira issue.
        """
        return [
            {
                "name": channel_name,
                "alsoPostsToJira": channel in _SLACK_CHANNELS_TO_JIRA_LABELS,
            }
            for channel_name, channel in _SLACK_REPORT_TYPE_TO_SLACK_CHANNEL.items()
        ]

    def _get_slack_channels(
        self,
        client_specified_channel: Optional[SlackChannel],
        slack_report_type: Optional[str],
        feature: Optional[str],
    ) -> Optional[ForwardedSlackChannel]:
        """
        Get the Slack channel(s) to post to based on user input.

        parameters:
            client_specified_channel: e.g. SlackChannel.DESIGN_QUALITY
            slack_report_type: e.g. "Lesson content / accepted translations" or "Design Quality".
            feature: e.g. Achievements

        returns: A `ForwardedSlackChannel`, which contains all the channels we should post to.
        """
        # If the client gave us a proper channel, just use it
        if client_specified_channel is not None:
            return ForwardedSlackChannel(primary=client_specified_channel)

        # Next check the slack_report_type
        slack_channel_from_slack_report_type = (
            SlackChannel.LITERACY_TESTING
            if slack_report_type == "literacy"
            else _SLACK_REPORT_TYPE_TO_SLACK_CHANNEL.get(slack_report_type)
        )

        slack_channel_from_feature = _SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        channel = slack_channel_from_slack_report_type or slack_channel_from_feature
        channels = ForwardedSlackChannel(primary=channel) if channel else None

        team = JIRA_FEATURE_TO_TEAM.get(feature)
        area = JIRA_TEAM_TO_AREA.get(team)

        # Add forwarding to Design Quality area channel if applicable
        if (
            channels is not None
            and channels.primary == SlackChannel.DESIGN_QUALITY
            and area is not None
            and (area_channel := area_design_quality_channel(area)) is not None
        ):
            channels.forwarded.append(area_channel)

        return channels

    def _set_priority(
        self,
        issue_key: str,
        project: str,
        ticket_text: JiraTicketText,
    ) -> None:
        """
        Set the priority of the Jira issue based on the textual content of the ticket

        parameters:
            issue_key (str): The Jira key for which we want to set the priority (e.g. "DLAA-1234")
            project (str): The project of the Jira issue ("DLAA", "DLAI" or "DLAW")
            ticket_text (JiraTicketText): The text content provided by the user in the bug report
                (summary and description).
        """
        comment = "Could not estimate the priority with GPT. Please set the priority manually."
        try:
            priority_resp = self._gpt_priority_estimator.estimate_priority(ticket_text)
            priority = priority_resp.priority
            reason = priority_resp.reason
            reason = reason.strip().strip(".!?") if reason else ""

            if priority == JiraPriority.UNPRIORITIZED and not reason:
                raise ValueError("Invalid response from GPT")

            if priority != JiraPriority.UNPRIORITIZED:
                LOG.info(f"{issue_key}: Setting priority {priority} for the reason: {reason}")
                self._jira_client.set_priority(project, issue_key, priority)

            # Jira API expects "{{...}}" for fixed-width text in markdown, but with an f-string we need to escape each;
            # Five curly braces for one string is a little crazy, though, so I'm avoiding an f-string here.
            priority_md = "{{" + priority + "}}"
            reason_md = "{{" + reason + "}}"
            comment = (
                f"The priority was automatically set to {priority_md} by GPT for the reason: {reason_md}.\n\n"
                f"Please change any incorrect priorities and report any major issues to {SLACK_CHANNEL_MD}."
            )

            # Adds a label to the issue to indicate that the priority was estimated by GPT.
            # There are automation rules in place to remove this label if the priority is manually changed.
            self._jira_client.add_label(
                issue_key=issue_key, label=PRIORITIZED_BY_GPT_LABEL, project=project
            )
        except Exception as e:
            LOG.error(f"{issue_key}: Error estimating priority: {e}")
            self._jira_client.add_comment(project, issue_key, comment)
            return

        self._jira_client.add_comment(project, issue_key, comment)

    def _find_duplicates_gpt(self, issue_key: str):
        issue = self._jira_client.get_issue_details(issue_key)
        if issue is None:
            LOG.warning(f"{issue_key}: Could not get issue details, skipping duplicate detection")
            return
        try:
            duplicates = self._gpt_duplicate_detector.find_duplicates(issue)
        except Exception as e:
            LOG.warning(f"{issue_key}: Error finding duplicates: {e}")
            return

        if not duplicates:
            LOG.info(f"{issue_key}: No potential duplicates detected")
            return

        dup_str = ", ".join(dup for dup, _ in duplicates)
        LOG.info(f"{issue_key}: Potential duplicates detected: {dup_str}")

        dups_file = ""
        for dup, reasoning in duplicates:
            dups_file += f"{dup}\nReasoning: {reasoning}\n\n"

        try:
            self._upload_to_s3(
                f"gpt_detected_duplicates/{issue_key}.txt", dups_file.strip().encode("utf-8")
            )
            LOG.info(f"{issue_key}: Potential duplicates stored to S3")
        except Exception as e:
            LOG.error(f"{issue_key}: Error uploading potential duplicates to S3: {e}")

        try:
            rich_text = self._gpt_duplicate_detector.generate_duplicates_rich_text(
                issue_key, duplicates
            )
            self._jira_client.insert_rich_text_into_description(issue_key, rich_text)
            LOG.info(f"{issue_key}: Updated description with potential duplicates")
        except Exception as e:
            LOG.error(f"{issue_key}: Error inserting rich text into description: {e}")

    def _generate_and_upload_screenshot_summary(
        self,
        issue_key: str,
        screenshot: bytes,
        extension: str,
        issue_summary: str,
    ):
        LOG.info(f"{issue_key}: Generating screenshot summary")
        try:
            summary = self._gpt_screenshot_summarizer.generate_description(
                screenshot, extension, issue_summary
            )
        except Exception as e:
            LOG.warning(f"{issue_key}: Failed to generate screenshot summary: {e}")
            return
        try:
            self._upload_to_s3(f"screenshot_summaries/{issue_key}.txt", summary.encode("utf-8"))
            LOG.info(f"{issue_key}: Summary uploaded to S3")
        except Exception as e:
            LOG.warning(f"{issue_key}: Error uploading screenshot summary to S3: {e}")

    def _summarize_logs(
        self,
        issue_key: str,
        summary: str,
        description: str,
        files: Dict[str, List[str]],
    ):
        """
        Summarize logs using GPTLogSummarizer and log the result.
        Returns the LogSummaryResponse or None if no logs or error.
        """
        if not files:
            LOG.warning(f"{issue_key}: No logs found to summarize")
            return None
        if (description is None or description == DEFAULT_DESCRIPTION) and (
            summary is None or summary == DEFAULT_ISSUE_SUMMARY
        ):
            LOG.warning(f"{issue_key}: No description or summary, skipping log summarization")
            return None
        try:
            ticket = JiraLogSummarizationTicket(
                description=description or "", title=summary or "", files=files, ticket_id=issue_key
            )
            summary_response = self._gpt_log_summarizer.summarize_logs(ticket)
            LOG.info(f"{issue_key}: GPT log summary: {summary_response.format(max_lines=5)}")
        except Exception as e:
            LOG.error(f"{issue_key}: Error summarizing logs with GPT: {e}")
            return
        try:
            self._upload_to_s3(
                f"log_summaries/{issue_key}.txt",
                summary_response.format(max_lines=5).encode("utf-8"),
            )
            LOG.info(f"{issue_key}: Log summary uploaded to S3")
        except Exception as e:
            LOG.warning(f"{issue_key}: Error uploading log summary to S3: {e}")

    def _parse_log_files(self, files: Dict[str, FileStorage]) -> Dict[str, List[str]]:
        """Parse log files from FileStorage objects into a dictionary of filename to list of log lines.
        Args:
            files: Dictionary mapping file names to FileStorage objects
        Returns:
            Dictionary mapping filenames to lists of log lines
        """
        parsed_log_files: Dict[str, List[str]] = {}
        for file_name, file_storage in files.items():
            if file_name == _SCREENSHOT_FILE_KEY:
                # We don't want to parse the screenshot file
                continue

            try:
                file_storage.stream.seek(0)
                log_text = file_storage.stream.read().decode("utf-8")
                file_storage.stream.seek(0)
                if log_text:
                    LOG.info(
                        f"Log text exists for {file_storage.filename}. Length: {len(log_text)}"
                    )
                    parsed_log_files[file_storage.filename] = log_text.splitlines()
            except UnicodeDecodeError as e:
                LOG.warning(
                    f"Could not decode file {getattr(file_storage, 'filename', '<unknown>')} as UTF-8, skipping: {e}"
                )
            except Exception as e:
                LOG.warning(
                    f"Error reading log file {getattr(file_storage, 'filename', '<unknown>')}, skipping: {e}"
                )
        return parsed_log_files

    @traced_function()
    def report_issue(
        self,
        project: str,
        feature: Optional[str],
        slack_report_type: Optional[str],
        client_specified_slack_channel_name: Optional[str],
        related_issue_key: Optional[str],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        release_blocker: bool,
        files: Dict[str, FileStorage],
        localization_contractor: bool = False,
    ) -> Dict[str, Union[str, Tuple[str, int]]]:
        """
        Create an issue in JIRA and/or post the issue to Slack, depending on the client_specified_slack_channel_name, feature, and slack_report_type fields.

        parameters:
            project: e.g. DLAA, DLAI, DLAW, LIT, DETBUG
            feature: e.g. Achievements
            slack_report_type: e.g. "Lesson content / accepted translations" or "Design Quality".
            client_specified_slack_channel_name: e.g. #design-quality. If this is set, override the other parameters and post in this channel.
            related_issue_key: e.g. "DEL-1773". If this is set the related issue will be linked to the new issue.
            summary: Roughly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_email: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
            release_blocker: Whether the ticket should have a release blocker label
            files: MultiDict of form name to file. The screenshot file should have the form name "screenshot".

        returns: Dict[str, ?] containing one or more of the following fields:
            - "issueKey": str if an issue was created in JIRA.
            - "slackChannel": str if it was posted to Slack.
            - "url": (DEPRECATED) str URL to view the created issue, the Slack channel, or None.
            - "jiraUrl": str if an issue was created in JIRA.
            - "slackUrl": str if it was posted to Slack.
            - "error": Tuple[message: str, code: int] if there was an error creating the issue.

        """
        # JIRA summary cannot be longer than be longer than 255 characters, truncate if necessary.
        if len(summary) > 255:
            summary = summary[:252] + "..."

        project_error_message = self.get_project_error_message(project)
        if project_error_message:
            return {
                "error": (
                    project_error_message,
                    400,
                )
            }

        client_specified_slack_channel = (
            SlackChannel.from_name_or_id(client_specified_slack_channel_name)
            if client_specified_slack_channel_name
            else None
        )
        if client_specified_slack_channel_name and not client_specified_slack_channel:
            return {
                "error": (
                    f"Invalid slack channel - must be one of {[c.name for c in list(SlackChannel)]}",
                    400,
                )
            }

        channels = self._get_slack_channels(
            client_specified_channel=client_specified_slack_channel,
            slack_report_type=slack_report_type,
            feature=feature,
        )
        jira_label_from_channel = (
            _SLACK_CHANNELS_TO_JIRA_LABELS.get(channels.primary) if channels else None
        )
        jeeves_label = JIRA_VIA_JEEVES_LABEL if summary.startswith(_VIA_JEEVES_MARKER) else None
        rc_blocker_label = JIRA_RELEASE_BLOCKER_LABEL if release_blocker else None

        screenshot = files.get(_SCREENSHOT_FILE_KEY)

        post_to_slack_only = channels is not None and jira_label_from_channel is None
        if related_issue_key and not post_to_slack_only:
            related_issue_details = self._jira_client.get_issue_details(issue_key=related_issue_key)
            related_issue_exists = (
                related_issue_details is not None and related_issue_details.get("id") is not None
            )
        else:
            related_issue_exists = False

        related_issue_invalid = related_issue_key is not None and not related_issue_exists

        should_post_to_slack = (
            channels is not None and not related_issue_invalid
        ) or post_to_slack_only
        should_post_to_jira = jira_label_from_channel is not None or not should_post_to_slack
        issue_key = None
        issue_url = None
        if should_post_to_jira:
            LOG.info(
                f"Creating JIRA issue for project {project}, feature {feature}, summary {summary}"
            )

            issue_key = self._jira_client.create_issue(
                project=project,
                feature=feature,
                labels=[
                    label
                    for label in [
                        jira_label_from_channel,
                        jeeves_label,
                        rc_blocker_label,
                        SHAKE_TO_REPORT_LABEL,
                    ]
                    if label is not None
                ],
                summary=summary,
                description=description,
                generated_description=generated_description,
                reporter_email=reporter_email,
                pre_release=pre_release,
                will_post_to_slack=should_post_to_slack,
                related_issue_exists=related_issue_exists,
                localization_contractor=localization_contractor,
            )

            if issue_key:
                issue_url = self._jira_client.issue_url(issue_key)
                self.upload_artifacts(issue_key, files, issue_summary=summary)
                if related_issue_exists:
                    self._jira_client.link_issues(
                        outward_issue_key=related_issue_key,
                        inward_issue_key=issue_key,
                    )

                # Set priority based on summary and feature in a background task.
                ticket_text = JiraTicketText(title=summary, description=f"{description}")
                executor = app_registry(ThreadPoolExecutor)
                executor.submit(self._set_priority, issue_key, project, ticket_text)
                executor.submit(self._find_duplicates_gpt, issue_key)

            if not should_post_to_slack:
                return (
                    {"issueKey": issue_key, "url": issue_url, "jiraUrl": issue_url}
                    if issue_key
                    else {"error": ("There was an issue posting to Jira.", 500)}
                )

        # We technically know that `channels` is not `None`, but we add this for mypy
        if should_post_to_slack and channels is not None:
            post_info_in_reply = (
                issue_url is None and (description or generated_description) is not None
            )
            # Keep track of the posts that succeeded
            post_ids = {}

            for channel in [channels.primary, *channels.forwarded]:
                post_id = self._slack_client.post_issue(
                    project=project,
                    slack_channel=channel,
                    summary=summary,
                    reporter_email=reporter_email,
                    jira_issue_url=issue_url,
                    post_info_in_reply=post_info_in_reply,
                    screenshot=screenshot,
                )
                post_ids[channel] = post_id

                if post_info_in_reply and post_id:
                    self._slack_client.post_info_in_reply(
                        slack_channel=channel,
                        original_post_id=post_id,
                        summary=summary,
                        description=description,
                        generated_description=generated_description,
                    )

            optional_channel_url = (
                channels.primary.url() if post_ids.get(channels.primary) else None
            )
            primary_post_id = post_ids.get(channels.primary)
            return (
                {
                    "slackChannel": channels.primary.name if primary_post_id else None,
                    "forwardedSlackChannels": [
                        channel.name for channel in channels.forwarded if post_ids.get(channel)
                    ],
                    "url": issue_url or optional_channel_url,
                    "issueKey": issue_key,
                    "slackUrl": optional_channel_url,
                    "jiraUrl": issue_url,
                }
                if primary_post_id is not None or issue_key is not None
                else {"error": ("There was a problem reporting the issue.", 500)}
            )

    def _upload_to_loki_ios(self, jira_issue_key: str, text_stream: io.TextIOWrapper):
        loki_client = ShakiraLokiApiClient()
        try:
            loki_client.integrate_ios_info_to_loki(self._jira_client, jira_issue_key, text_stream)
        except Exception as e:
            LOG.error(f"{jira_issue_key}: Error uploading to Loki: {type(e).__name__}: {e}")

    def _upload_to_loki_android(self, jira_issue_key: str, text_stream: io.TextIOWrapper):
        loki_client = ShakiraLokiApiClient()
        try:
            loki_client.integrate_android_info_to_loki(
                self._jira_client, jira_issue_key, text_stream
            )
        except Exception as e:
            LOG.error(f"{jira_issue_key}: Error uploading to Loki: {type(e).__name__}: {e}")

    @traced_function()
    def upload_artifacts(
        self,
        jira_issue_key: str,
        files: Dict[str, "FileStorage"],
        issue_summary: Optional[str] = None,
        user_agent: Optional["DuolingoUserAgent"] = None,
    ) -> Dict[str, Union[str, Tuple[str, int]]]:
        """
        Attach files to a Jira issue.

        parameters:
            jira_issue_key: Jira issue ID in string (E.g DLAA-2508)
            files: MultiDict of form name to file. The screenshot file should have the form name "screenshot".

        returns: Dict[str, ?] containing one or more of the following fields:
            - "issueKey": str if an issue was created in JIRA.
            - "jiraUrl": str if an issue was created in JIRA.
            - "error": Tuple[message: str, code: int] if there was an error creating the issue.
        """
        issue_url = self._jira_client.issue_url(jira_issue_key)
        if not files:
            LOG.info(f"{jira_issue_key}: No files to upload")
            return {"issueKey": jira_issue_key, "jiraUrl": issue_url}

        project = jira_issue_key.split("-")[0]
        text_stream = None
        if user_agent:
            for f in files.values():
                if hasattr(f, "filename") and (
                    f.filename == _IOS_LOG_FILENAME or ANDROID_LOG_FILE_PATTERN.match(f.filename)
                ):
                    file_contents = f.read()
                    # Move the pointer back to the beginning since we're going to read it again later
                    f.seek(0)
                    file_stream = io.BytesIO(file_contents)
                    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8")
                    # Assume we will either have one `logs.txt` file or one `log${random_number}.txt`
                    break

        executor = app_registry(ThreadPoolExecutor)

        if text_stream:
            if user_agent.platform == DuoPlatform.IOS:
                executor.submit(self._upload_to_loki_ios, jira_issue_key, text_stream)
            elif user_agent.platform == DuoPlatform.ANDROID:
                executor.submit(self._upload_to_loki_android, jira_issue_key, text_stream)

        issue_details = self._jira_client.get_issue_details(jira_issue_key)
        if issue_summary is None:
            if issue_details is None:
                LOG.warning(f"{jira_issue_key}: Could not get issue details, using empty summary")
                issue_summary = DEFAULT_ISSUE_SUMMARY
            else:
                issue_summary = issue_details["fields"]["summary"]
                assert isinstance(issue_summary, str)

        if issue_details is None:
            LOG.warning(f"{jira_issue_key}: Could not get issue details, using empty description")
            description = DEFAULT_DESCRIPTION
        else:
            description_field = issue_details["fields"]["description"]
            content = description_field["content"]

            # Only take the first paragraph of the description for now.
            # TODO(cainan): Clean up how we pull this data, and get other relevant fields
            if (
                len(content) > 0
                and content[0]["type"] == "paragraph"
                and len(content[0]["content"]) > 0
            ):
                description = content[0]["content"][0]["text"]
            else:
                LOG.warning(f"{jira_issue_key}: Invalid description field, using empty description")
                description = DEFAULT_DESCRIPTION

            assert isinstance(
                description, str
            ), f"description should be str but got {type(description)} with value: {description}"

        # Parse the log files first to avoid race conditions in stream consumption
        parsed_log_files = self._parse_log_files(files)

        if _SCREENSHOT_FILE_KEY in files:
            screenshot = files[_SCREENSHOT_FILE_KEY]

            # Read the screenshot in single threaded context to avoid race
            # conditions in stream consumption
            screenshot.stream.seek(0)
            screenshot_data = screenshot.stream.read()
            screenshot.stream.seek(0)

            if screenshot.filename:
                extension = screenshot.filename.split(".")[-1]
            elif screenshot.mimetype:
                extension = screenshot.mimetype.split("/")[-1]
            else:
                LOG.warning(f"{jira_issue_key}: Could not determine extension for screenshot")
                extension = "jpeg"

            executor.submit(
                self._generate_and_upload_screenshot_summary,
                jira_issue_key,
                screenshot_data,
                extension,
                issue_summary,
            )

        executor.submit(
            self._summarize_logs,
            jira_issue_key,
            issue_summary,
            description,
            parsed_log_files,
        )

        try:
            self._jira_client.upload_attachments(project, jira_issue_key, files)
        except RequestException as e:
            return {
                "error": (
                    f"{jira_issue_key}: Error uploading attachments to JIRA: {e}",
                    e.response.status_code if e.response else 500,
                )
            }
        except Exception as e:
            return {
                "error": (
                    f"{jira_issue_key}: Error uploading attachments to JIRA: {e}",
                    500,
                )
            }

        return {"issueKey": jira_issue_key, "jiraUrl": issue_url}
