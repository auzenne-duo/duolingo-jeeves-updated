"""
Decompose text into a list of words.

TODO: Support non-English languages.
TODO: Use existing 3rd party tokenizers.
"""
import json

import requests

_NLP_URL = "https://nlp.duolingo.com/v1/udep"


class Tokenizer:
    def tokenize(self, text, lang):

        if not text:
            return []

        nlp_required_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "duolingo-jeeves (DuolingoService)",
        }
        nlp_params = {"language": lang}
        nlp_data = {"document": text}

        r = requests.post(
            _NLP_URL, headers=nlp_required_headers, params=nlp_params, data=json.dumps(nlp_data)
        )

        # TODO: Add more informative exception handling
        try:
            detailedTokenLists = json.loads(r.text)["results"]
            combinedDetailedList = sum(detailedTokenLists, [])
        except:
            return []

        tokens = [
            detailedToken["text"].lower()
            for detailedToken in combinedDetailedList
            if (detailedToken["upos"] != "PUNCT")
        ]

        return tokens
