import langid

from jeeves.exception.model import UnsupportedLanguageError
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.model.products import Products

_TINYCARDS_TAGS = frozenset(('tinycards_feedback', 'tinycardsat'))
_DET_TAGS = frozenset(('examity', 'mettl', 'testcenter', 'test_center', 'det'))

def classifyLang(text):
    lid = langid.classify(text)[0]
    try:
        return SUPPORTED_LANGUAGES[lid]
    except KeyError:
        raise UnsupportedLanguageError(lid)

def classifyProd(ticket_json):
    tags = frozenset(ticket_json['tags'])
    if _TINYCARDS_TAGS & tags:
        return Products.TINYCARDS
    elif (
        _DET_TAGS & tags
        or ticket_json['subject'].startswith(
            ('[internal-review]', '[web-survey-results]')
        )
    ):
        return Products.DET
    else:
        return Products.LA
