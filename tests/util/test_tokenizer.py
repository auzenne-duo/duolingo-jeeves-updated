import unittest

from jeeves.util.tokenizer import Tokenizer


class Test(unittest.TestCase):

    def test_(self):
        tokenizer = Tokenizer()
        self.assertEqual(
            tokenizer.tokenize('hello, world! I\'m Duo.'), ['hello', 'world', 'i', 'm', 'duo']
        )
