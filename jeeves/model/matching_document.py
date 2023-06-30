from dataclasses import asdict, dataclass
from typing import Any, Dict

from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.model.jeeves_document import JeevesDocument


@dataclass
class MatchingDocument:
    """
    A container to store a JeevesDocument and the score from our approximate k-NN search (cosine similarity)
    """

    def __init__(self, doc: JeevesDocument, score: float):
        self.doc = doc
        self.score = score

    @classmethod
    def from_response_hit(cls, hit: Dict[str, Any]):
        """
        Translate a hit (from response["hits"]["hits"]) into a MatchingDocument
        """
        doc = (
            IDManagerMap.get_manager_for_identifier(hit["_source"]["data_source"])
            .get_managed_document_type()
            .deserialize_from_internal_json(hit["_source"])
        )

        return cls(doc, hit["_score"])

    def to_dict(self):
        return asdict(self)
