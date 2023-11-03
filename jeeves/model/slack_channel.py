from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SlackChannel(namedtuple("SlackChannel", "name channel_id"), Enum):
    DESIGN_QUALITY = "#design-quality", "C01867ZCY7J"
    DESIGN_QUALITY_MONETIZATION = "#area-monetization-design-quality", "C062U3TE1K4"
    DESIGN_QUALITY_GROWTH = "#area-growth-design-quality", "C0636NYT4MP"
    DESIGN_QUALITY_LEARNING = "#area-learning-design-quality", "C062U48RJEN"
    DESIGN_QUALITY_NEW_SUBJECTS = "#area-new-subjects-design-quality", "C063H47D140"
    FEEDBACK_LANGUAGE = "#feedback-language", "C0KHQRPDZ"
    FEEDBACK_PRODUCT = "#feedback-product", "C013VGDCU5R"
    FEEDBACK_TTS = "#feedback-tts", "C01FWHDCLP4"
    TEAM_QA = "#team-qa", "C01HWDJK60P"

    BUG_TRIAGE = "#bug-triage", "C91UF7WAZ"
    JEEVES = "#jeeves", "C6A1F2CNA"
    POST_TEST_RESULTS = "#post-test-results", "CJNN7RJBD"

    LITERACY_TESTING = "#team-literacy-testing", "CMCTM4UN4"

    @classmethod
    def from_name_or_id(cls, name_or_id: str) -> Optional["SlackChannel"]:
        for channel in list(cls):
            if channel.name == name_or_id or channel.channel_id == name_or_id:
                return channel
        return None

    def url(self):
        return f"https://duolingo.slack.com/archives/{self.channel_id}"


AREA_NAME_TO_SLACK_CHANNEL = {
    "Monetization": SlackChannel.DESIGN_QUALITY_MONETIZATION,
    "Growth": SlackChannel.DESIGN_QUALITY_GROWTH,
    "Learning R&D": SlackChannel.DESIGN_QUALITY_LEARNING,
    "Learning Scaling": SlackChannel.DESIGN_QUALITY_LEARNING,
    "New Subjects": SlackChannel.DESIGN_QUALITY_NEW_SUBJECTS,
}


@dataclass
class ForwardedSlackChannel:
    """Contains a primary slack channel with secondary forwarded channels."""

    primary: SlackChannel
    forwarded: List[SlackChannel] = field(default_factory=list)


def area_design_quality_channel(area: str) -> Optional[SlackChannel]:
    return AREA_NAME_TO_SLACK_CHANNEL.get(area)
