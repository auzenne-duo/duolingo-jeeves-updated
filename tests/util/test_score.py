"""
Unit test for scoring functions util.
"""
from functools import reduce
import numpy as np
import operator
import unittest

from jeeves.util.score import pearsons_coefficient, cosine_similarity

first = dict(a=15, b=6, c=2)
second = dict(a=1, b=5, d=1)

np_first = np.array([15, 6, 2, 0])
np_second = np.array([1, 5, 0, 1])


def center(x):
    return x - np.average(x)


def norm_prod(it):
    return reduce(operator.mul, map(np.linalg.norm, it), 1)


def cosine(a, b):
    return a.dot(b) / norm_prod((a, b))


def pearsons(a, b):
    return cosine(center(a), center(b))


class Test(unittest.TestCase):
    def test_pearsons_coefficient(self):
        expected = pearsons(np_first, np_second)
        result = pearsons_coefficient(first, second)
        self.assertAlmostEqual(result, expected)

    def test_cosine_similarity(self):
        expected = cosine(np_first, np_second)
        result = cosine_similarity(first, second)
        self.assertAlmostEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
