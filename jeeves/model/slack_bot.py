import os
from collections import namedtuple
from enum import Enum


class SlackBot(namedtuple("SlackBot", "slack_name api_token spike_type_insert"), Enum):
    """
    Contains the name, API token, a specific message insert for each spike reporter slack bot
    """

    SPIKE_REPORTER = "spike_reporter", os.environ.get("SPIKE_REPORTER_SLACK_API_TOKEN"), ""
    BUG_SPIKE_REPORTER = (
        "bug_spike_reporter",
        os.environ.get("BUG_SPIKE_REPORTER_SLACK_API_TOKEN"),
        "related to bugs ",
    )
    SOCIAL_TRENDS_SPIKE_REPORTER = (
        "social_trends_spike_reporter",
        os.environ.get("SOCIAL_TRENDS_SPIKE_REPORTER_SLACK_API_TOKEN"),
        "related to social media trends ",
    )
