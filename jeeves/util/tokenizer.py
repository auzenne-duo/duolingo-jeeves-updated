"""
Decompose text into a list of words.

TODO: Support non-English languages.
TODO: Use existing 3rd party tokenizers.
"""
import sys
import unicodedata


class Tokenizer(object):

    table = {i: " " for i in range(sys.maxunicode) if unicodedata.category(chr(i)).startswith("P")}

    def tokenize(self, text):
        return text.translate(self.table).lower().split()
