"""
Model for a JeevesDocument annotated with its sentiment
"""

import attr

from jeeves.model.jeeves_document import JeevesDocument


@attr.s(kw_only=True)
class AnnotatedDocument:

    jeeves_document: JeevesDocument = attr.ib()
    label: str = attr.ib()

    def get_summary_string(self) -> str:
        """
        Returns a summary of the jeeves document and its label
        """
        return f"(document id: {self.jeeves_document.document_id}. label: {self.label}. header text: {self.jeeves_document.header_text}. body text: {self.jeeves_document.body_text})"
