import unittest

from jeeves.model.slack_bot import SlackBot
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.scripts.index_pipeline_and_spike_detector.slack import (
    generate_slack_message,
    get_jeeves_analysis_query_params,
    get_yesterdays_date,
    spike_sorter,
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
                            "text": "*<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duo>*",
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
                            "text": "*<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duo>*",
                        },
                        {"type": "plain_text", "text": "10.0"},
                        {
                            "type": "mrkdwn",
                            "text": "*<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duolingo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duolingo>*",
                        },
                        {"type": "plain_text", "text": "9.1"},
                    ],
                },
            ],
        )

    def test_generate_slack_message_for_spike_words_with_summary(self):
        testObj1 = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        result = generate_slack_message(SpikeCategory.EXTERNAL_NON_STR_SPIKES, [testObj1])
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
                            "text": "*<https://jeeves.duolingo.com/en/analysis?filter=NON_STR_EXTERNAL&q=duo&use-lemmas=true&spike-category=EXTERNAL_NON_STR_SPIKES|duo>*\ntest summary",
                        },
                        {"type": "plain_text", "text": "10.0"},
                    ],
                },
            ],
        )

    def test_spike_sorter_for_customer_feedback(self):
        """
        Tests that when given a batch of customer feedback spikes the spike sorter correctly
        divides spikes into bug spikes and social trend spikes and doesn't give any spikes
        to the beta spike reporter
        """
        testObj1 = SpikeWord(
            word="duo1",
            score=1,
            date="2022-01-01",
            lang="en",
            is_bug=True,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        testObj2 = SpikeWord(
            word="duo2",
            score=2,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        testObj3 = SpikeWord(
            word="duo3",
            score=3,
            date="2022-01-01",
            lang="en",
            is_bug=True,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        testObj4 = SpikeWord(
            word="duo4",
            score=4,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=True,
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        testObj5 = SpikeWord(
            word="duo5",
            score=5,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=True,
            spike_group=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
            summary="test summary",
        )

        result = spike_sorter(
            spikes=[testObj1, testObj2, testObj3, testObj4, testObj5],
            curr_spike_category=SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )

        self.assertEqual(
            set(result.keys()),
            {
                SlackBot.SPIKE_REPORTER.slack_name,
                SlackBot.BUG_SPIKE_REPORTER.slack_name,
                SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name,
                SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name,
            },
        )

        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SPIKE_REPORTER.slack_name],
                    [testObj5, testObj4, testObj3, testObj2],
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BUG_SPIKE_REPORTER.slack_name], [testObj3, testObj1]
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name], [testObj5, testObj4]
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name], []
                )
            )
        )

    def test_spike_sorter_for_beta_feedback(self):
        """
        Tests that when given a batch of beta feedback spikes the spike sorter correctly
        gives all the spikes to the beta spike reporter and doesn't give any spikes to
        the bug spike reporter or social trend spike reporter
        """
        testObj1 = SpikeWord(
            word="duo1",
            score=1,
            date="2022-01-01",
            lang="en",
            is_bug=True,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_STR_SPIKES,
            summary="test summary",
        )

        testObj2 = SpikeWord(
            word="duo2",
            score=2,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_STR_SPIKES,
            summary="test summary",
        )

        testObj3 = SpikeWord(
            word="duo3",
            score=3,
            date="2022-01-01",
            lang="en",
            is_bug=True,
            is_social_trend=False,
            spike_group=SpikeCategory.EXTERNAL_STR_SPIKES,
            summary="test summary",
        )

        testObj4 = SpikeWord(
            word="duo4",
            score=4,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=True,
            spike_group=SpikeCategory.EXTERNAL_STR_SPIKES,
            summary="test summary",
        )

        testObj5 = SpikeWord(
            word="duo5",
            score=5,
            date="2022-01-01",
            lang="en",
            is_bug=False,
            is_social_trend=True,
            spike_group=SpikeCategory.EXTERNAL_STR_SPIKES,
            summary="test summary",
        )

        result = spike_sorter(
            spikes=[testObj1, testObj2, testObj3, testObj4, testObj5],
            curr_spike_category=SpikeCategory.EXTERNAL_STR_SPIKES,
        )

        self.assertEqual(
            set(result.keys()),
            {
                SlackBot.SPIKE_REPORTER.slack_name,
                SlackBot.BUG_SPIKE_REPORTER.slack_name,
                SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name,
                SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name,
            },
        )

        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SPIKE_REPORTER.slack_name],
                    [testObj5, testObj4, testObj3, testObj2],
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BUG_SPIKE_REPORTER.slack_name], []
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name], []
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name],
                    [testObj5, testObj4, testObj3, testObj2],
                )
            )
        )

    def test_spike_sorter_for_no_spikes(self):
        """
        Tests that the spike sorter doesn't throw an error when there are no spikes
        """
        result = spike_sorter(spikes=[], curr_spike_category=SpikeCategory.EXTERNAL_NON_STR_SPIKES)

        self.assertEqual(
            set(result.keys()),
            {
                SlackBot.SPIKE_REPORTER.slack_name,
                SlackBot.BUG_SPIKE_REPORTER.slack_name,
                SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name,
                SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name,
            },
        )

        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SPIKE_REPORTER.slack_name], []
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BUG_SPIKE_REPORTER.slack_name], []
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name], []
                )
            )
        )
        self.assertTrue(
            all(
                resultSpike == expectedSpike
                for resultSpike, expectedSpike in zip(
                    result[SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name], []
                )
            )
        )
