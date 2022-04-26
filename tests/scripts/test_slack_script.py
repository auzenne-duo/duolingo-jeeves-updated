import unittest

from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.scripts.slack import generate_slack_message, get_yesterdays_date


class TestSlackScript(unittest.TestCase):
    def test_generate_slack_message_for_one_spike_word(self):
        testObj = SpikeWord(
            word="duo", score=10, date="2022-01-01", lang="en", spike_group=SpikeCategory.ALL_SPIKES
        )
        result = generate_slack_message([testObj])
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
                            "text": "<https://jeeves.duolingo.com/en/analysis?q=duo|duo>",
                        },
                        {"type": "plain_text", "text": "10.0"},
                    ],
                },
            ],
        )

    def test_generate_slack_message_for_many_spike_words(self):
        testObj1 = SpikeWord(
            word="duo", score=10, date="2022-01-01", lang="en", spike_group=SpikeCategory.ALL_SPIKES
        )
        testObj2 = SpikeWord(
            word="duolingo",
            score=9.1234,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.ALL_SPIKES,
        )

        result = generate_slack_message([testObj1, testObj2])
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
                            "text": "<https://jeeves.duolingo.com/en/analysis?q=duo|duo>",
                        },
                        {"type": "plain_text", "text": "10.0"},
                        {
                            "type": "mrkdwn",
                            "text": "<https://jeeves.duolingo.com/en/analysis?q=duolingo|duolingo>",
                        },
                        {"type": "plain_text", "text": "9.1"},
                    ],
                },
            ],
        )
