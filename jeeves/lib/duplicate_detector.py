"""
Functions related to duplicate detection.
Currently only applies to JIRA issues.
"""

import os
from typing import List

from sentence_transformers import SentenceTransformer

_DUPLICATE_DETECTOR_MODEL_PATH = os.environ.get("DUPLICATE_DETECTOR_MODEL")


class DuplicateIssueDetector:
    def __init__(self) -> None:
        self.sentence_transformer_model = SentenceTransformer(_DUPLICATE_DETECTOR_MODEL_PATH)

    def calculate_embedding_vector(self, target: str) -> List[float]:
        """
        Using a SentenceTransformers model, calculate an embedding vector for
        the given text.

        An embedding vector is a fixed-length numerical vector
        that can be compared to other similar vectors to determine similarity
        in meaning between corresponding pieces of text.

        Parameters:
            target (str): String to calculate an embedding vector for

        Returns:
            A list of floats representing an embedding vector for the
            provided text.
        """
        raw_model_output = self.sentence_transformer_model.encode([target])
        embedding_vector = raw_model_output[0].tolist()
        return embedding_vector


DuplicateDetector = DuplicateIssueDetector()
