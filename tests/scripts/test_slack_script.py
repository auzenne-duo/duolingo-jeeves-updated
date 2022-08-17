import unittest

from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.scripts.slack import (
    generate_slack_message,
    get_jeeves_analysis_query_params,
    get_yesterdays_date,
)
from jeeves.util.error_util import SpikeReporterException


class TestSlackScript(unittest.TestCase):
    def test_get_jeeves_analysis_query_params(self):
        testObj = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )
        result = get_jeeves_analysis_query_params(testObj)
        self.assertEqual(
            result,
            {
                "q": "duo",
                "filter": "NON_STR_EXTERNAL",
                "use-lemmas": "true",
                "spike-category": "EXTERNAL_NON_STR_SPIKES",
            },
        )

        testObj = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.INTERNAL_V2_IOS_SPIKES,
        )
        result = get_jeeves_analysis_query_params(testObj)
        self.assertEqual(
            result,
            {
                "q": "duo",
                "filter": "INTERNAL",
                "spike-category": "INTERNAL_V2_IOS_SPIKES",
                "use-lemmas": "true",
            },
        )

    def test_generate_slack_message_exception(self):
        testObj = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )
        self.assertRaises(
            SpikeReporterException,
            lambda: generate_slack_message(SpikeCategory.ALL_SPIKES, [testObj]),
        )

    def test_generate_slack_message_for_one_spike_word(self):
        testObj = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )
        result = generate_slack_message(SpikeCategory.EXTERNAL_NON_STR_SPIKES, [testObj])
        self.assertEqual(
            result,
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Here is the top 1 trending word we saw in customer feedback for {get_yesterdays_date()}:*",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*Word*"},
                        {"type": "mrkdwn", "text": "*Spikiness*"},
                        {
                            "type": "mrkdwn",
                            "text": "<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duo>",
                        },
                        {"type": "plain_text", "text": "10.0"},
                    ],
                },
            ],
        )

    def test_generate_slack_message_for_many_spike_words(self):
        testObj1 = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )
        testObj2 = SpikeWord(
            word="duolingo",
            score=9.1234,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )

        result = generate_slack_message(SpikeCategory.EXTERNAL_NON_STR_SPIKES, [testObj1, testObj2])
        self.assertEqual(
            result,
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Here are the top 2 trending words we saw in customer feedback for {get_yesterdays_date()}:*",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*Word*"},
                        {"type": "mrkdwn", "text": "*Spikiness*"},
                        {
                            "type": "mrkdwn",
                            "text": "<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duo>",
                        },
                        {"type": "plain_text", "text": "10.0"},
                        {
                            "type": "mrkdwn",
                            "text": "<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duolingo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duolingo>",
                        },
                        {"type": "plain_text", "text": "9.1"},
                    ],
                },
            ],
        )
