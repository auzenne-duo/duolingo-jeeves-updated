from collections import namedtuple
from enum import Enum
from typing import Optional


class SlackChannel(namedtuple("SlackChannel", "name channel_id"), Enum):
    VISUAL_POLISH = "#visual-polish", "C01867ZCY7J"
    FEEDBACK_LANGUAGE = "#feedback-language", "C0KHQRPDZ"
    FEEDBACK_PRODUCT = "#feedback-product", "C013VGDCU5R"
    FEEDBACK_TTS = "#feedback-tts", "C01FWHDCLP4"
    FEEDBACK_LOCALIZATION = "#feedback-localization", "C8BAQPLN4"
    FEEDBACK_VISEMES = "#feedback-visemes", "C041F3G50EA"
    PROJ_MISSING_TTS = "#proj-missing-tts", "C03N2CK8KL1"
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
