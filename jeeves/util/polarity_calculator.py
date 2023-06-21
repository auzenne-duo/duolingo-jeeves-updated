"""
A utility for calculating vector functions related to polarity
"""
from typing import List

import numpy as np


def calc_cosine_similarity(target_embedding: List[float], doc_embedding: List[float]) -> float:
    """
    Returns the cosine similarity between two embeddings
    """
    return np.dot(target_embedding, doc_embedding) / (
        np.linalg.norm(target_embedding) * np.linalg.norm(doc_embedding)
    )


def calc_polarity(
    doc_embedding: List[float], pos_embedding: List[float], neg_embedding: List[float]
) -> float:
    """
    Returns the polarity of a document compared to the positive and negative embeddings
    """
    return calc_cosine_similarity(doc_embedding, pos_embedding) - calc_cosine_similarity(
        doc_embedding, neg_embedding
    )
