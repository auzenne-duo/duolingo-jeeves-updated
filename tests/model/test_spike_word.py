import unittest

from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord


class TestSpikeWord(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSpikeWord, self).__init__(*args, **kwargs)
        self.testObj = SpikeWord(
            word="duo",
            score=10,
            date="2022-01-01",
            lang="en",
            spike_group=SpikeCategory.ALL_SPIKES,
            confirmed=False,
            confirmed_user_id=10,
            summary="summary",
            is_bug=True,
            is_social_trend=False,
            experiment_spikes={},
        )

    def test_from_dict(self):
        testDict = {
            "word": "duo",
            "score": 10,
            "date": "2022-01-01",
            "lang": "en",
            "spike_group": "ALL_SPIKES",
            "confirmed": True,
            "confirmed_user_id": 10,
            "fixed": True,
            "email_sent_date": "2022-01-02",
            "email_user_id": 11,
            "fixed_user_id": 19,
            "summary": "summary",
            "is_bug": True,
            "is_social_trend": False,
        }

        result = SpikeWord.from_dict(testDict)

        self.assertEqual(result.word, "duo")
        self.assertEqual(result.score, 10)
        self.assertEqual(result.date, "2022-01-01")
        self.assertEqual(result.lang, "en")
        self.assertEqual(result.spike_group, SpikeCategory.ALL_SPIKES)
        self.assertEqual(result.confirmed, True)
        self.assertEqual(result.confirmed_user_id, 10)
        self.assertEqual(result.email_sent_date, "2022-01-02")
        self.assertEqual(result.email_user_id, 11)
        self.assertEqual(result.fixed, True)
        self.assertEqual(result.fixed_user_id, 19)
        self.assertEqual(result.summary, "summary")
        self.assertEqual(result.is_bug, True)
        self.assertEqual(result.is_social_trend, False)

    def test_from_dict_no_confirmed(self):
        testDict = {
            "word": "duo",
            "score": 10,
            "date": "2022-01-01",
            "lang": "en",
            "spike_group": "ALL_SPIKES",
        }

        result = SpikeWord.from_dict(testDict)

        self.assertEqual(result.word, "duo")
        self.assertEqual(result.score, 10)
        self.assertEqual(result.date, "2022-01-01")
        self.assertEqual(result.lang, "en")
        self.assertEqual(result.spike_group, SpikeCategory.ALL_SPIKES)
        self.assertEqual(result.confirmed, False)
        self.assertEqual(result.confirmed_user_id, None)
        self.assertEqual(result.summary, None)
        self.assertEqual(result.is_bug, True)
        self.assertEqual(result.experiment_spikes, {})

    def test_from_dict_deprecated_category(self):
        testDict = {
            "word": "duo",
            "score": 10,
            "date": "2022-01-01",
            "lang": "en",
            "spike_group": "INVALID_CATEGORY",
        }

        result = SpikeWord.from_dict(testDict)

        self.assertEqual(result.word, "duo")
        self.assertEqual(result.score, 10)
        self.assertEqual(result.date, "2022-01-01")
        self.assertEqual(result.lang, "en")
        self.assertEqual(result.spike_group, None)
        self.assertEqual(result.confirmed, False)
        self.assertEqual(result.confirmed_user_id, None)
        self.assertEqual(result.summary, None)
        self.assertEqual(result.is_bug, True)
        self.assertEqual(result.experiment_spikes, {})

    def test_to_dict(self):
        result = self.testObj.to_dict()

        self.assertDictEqual(
            result,
            {
                "word": "duo",
                "score": 10,
                "date": "2022-01-01",
                "lang": "en",
                "spike_group": "ALL_SPIKES",
                "confirmed": False,
                "confirmed_user_id": 10,
                "email_user_id": None,
                "email_sent_date": None,
                "fixed": False,
                "fixed_user_id": None,
                "summary": "summary",
                "is_bug": True,
                "is_social_trend": False,
                "experiment_spikes": {},
                "status": "UNCONFIRMED",
                "status_user_id": None,
            },
        )

    def test_get_spike_id(self):
        result = self.testObj.get_spike_id()

        self.assertEqual(result, "SPIKE_duo_en_2022-01-01_ALL_SPIKES")
