"""
Model for a JeevesDocument annotated with its sentiment
"""

import attr

from jeeves.model.jeeves_document import JeevesDocument


@attr.s(kw_only=True)
class AnnotatedDocument:

    jeeves_document: JeevesDocument = attr.ib()
    label: str = attr.ib()
