import unittest

from jeeves.model.products import Products
from jeeves.util.classify import detect_language, detect_product


class Test(unittest.TestCase):

    def test_detect_language(self):
        self.assertEqual(detect_language('Hello world!'), 'en')
        self.assertEqual(detect_language('¡Hola Mundo!'), 'es')
        self.assertEqual(detect_language('Bonjour le monde!'), 'fr')

    def detect_product(self):
        self.assertEqual(detect_product(['tinycards_feedback'], None), Products.TINYCARDS)
        self.assertEqual(detect_product(['test_center'], None), Products.DET)
        self.assertEqual(detect_product([], None), Products.LA)
