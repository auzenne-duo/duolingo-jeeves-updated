"""
Unit tests for polarity calculator util
"""

import unittest

from jeeves.util.polarity_calculator import calc_cosine_similarity, calc_polarity


class Test(unittest.TestCase):
    def test_calc_polarity(self):
        self.assertAlmostEqual(calc_polarity([1, 0], [1, 0], [0, 1]), 1)
        self.assertAlmostEqual(calc_polarity([0.5, 0.5, 0.5], [1, 0, 1], [0, 1, 0]), 0.23914631)
        self.assertAlmostEqual(
            calc_polarity([0.25, 0.5, 0.75], [0, 0, 1], [0.5, 0.75, 1]), -0.19079961
        )

    def test_calc_cosine_similarity(self):
        self.assertAlmostEqual(calc_cosine_similarity([0, 1], [1, 0]), 0)
        self.assertAlmostEqual(calc_cosine_similarity([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]), 1)
        self.assertAlmostEqual(
            calc_cosine_similarity([0.5, 0.25, 0.75], [0.75, 0.15, 0.35]), 0.85789971
        )
