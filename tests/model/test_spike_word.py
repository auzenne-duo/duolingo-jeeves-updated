import unittest

from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord


class TestSpikeWord(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSpikeWord, self).__init__(*args, **kwargs)
        self.testObj = SpikeWord(
            word="duo", score=10, date="2022-01-01", lang="en", spike_group=SpikeCategory.ALL_SPIKES
        )

    def test_from_dict(self):
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
        self.assertEqual(result.spike_group, "ALL_SPIKES")

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
            },
        )

    def test_get_spike_id(self):
        result = self.testObj.get_spike_id()

        self.assertEqual(result, "SPIKE_duo_en_2022-01-01_ALL_SPIKES")

    def test_get_jeeves_analysis_url(self):
        result = self.testObj.get_jeeves_analysis_url()

        self.assertEqual(result, "https://jeeves.duolingo.com/en/analysis?q=duo")
