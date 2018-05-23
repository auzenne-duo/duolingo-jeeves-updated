import langid

from jeeves.model.products import Products

_TINYCARDS_TAGS = frozenset(('tinycards_feedback', 'tinycardsat'))
_DET_TAGS = frozenset(('examity', 'mettl', 'testcenter', 'test_center', 'det'))


def detect_language(text):
    return langid.classify(text)[0]


def detect_product(tags, subject):
    tags = frozenset(tags)
    if _TINYCARDS_TAGS & tags:
        return Products.TINYCARDS
    elif (_DET_TAGS & tags or subject.startswith(('[internal-review]', '[web-survey-results]'))):
        return Products.DET
    else:
        return Products.LA
