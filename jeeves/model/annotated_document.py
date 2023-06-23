"""
Model for a JeevesDocument annotated with its sentiment and potentially a sentiment score as well
"""
from typing import List

import attr

from jeeves.model.jeeves_document import JeevesDocument


@attr.s(kw_only=True)
class AnnotatedDocument:
    """
    Model for a JeevesDocument annotated with its sentiment
    """

    jeeves_document: JeevesDocument = attr.ib()
    label: str = attr.ib()

    def get_summary_string(self) -> str:
        """
        Returns a summary of the jeeves document and its label
        """
        return f"(document id: {self.jeeves_document.document_id}. label: {self.label}. header text: {self.jeeves_document.header_text}. body text: {self.jeeves_document.body_text})"

    @classmethod
    def convert_to_jeeves_doc(
        cls, labeled_documents: List["AnnotatedDocument"]
    ) -> List[JeevesDocument]:
        """
        This function converts a list of AnnotatedDocuments into a list of JeevesDocuments since we often need to
        convert between the two
        """
        return [labeled_doc.jeeves_document for labeled_doc in labeled_documents]


@attr.s(kw_only=True)
class SentimentScoredDocument(AnnotatedDocument):
    """
    Model for a JeevesDocument annotated with its sentiment and a sentiment score
    """

    sentiment_score: float = attr.ib()
