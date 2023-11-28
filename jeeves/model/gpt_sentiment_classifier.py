"""
Model for sentiment classifier using GPT
"""
from typing import List, Tuple

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import (
    NEGATIVE_CLASS,
    POSITIVE_CLASS,
    SentimentAnalysisClassifier,
)

SYSTEM_PROMPT = """
You are a tool which helps to classify documents. Give output in the format requested by the user.
"""


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTSentimentClassifier(SentimentAnalysisClassifier):
    def __init__(self, ai_completions_dal: AICompletionsDAL):
        self.ai_completions_dal = ai_completions_dal
        self.positive_class = POSITIVE_CLASS
        self.negative_class = NEGATIVE_CLASS

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        user_prompt_prefix = """Your job is to determine whether a document is "positive" or "negative".

        Return "positive" for a positive document and "negative" for a negative document.
        Return a number on a scale of -5 to 5 to determine how positive or negative a document is.

        Return the label and the number separated by a comma. For example, "positive, 5" or "negative, -3".
        """
        body = document.body_text.replace("\n", " ")
        header = document.header_text.replace("\n", " ")
        label, value = self.ai_completions_dal.ask(
            SYSTEM_PROMPT, f"{user_prompt_prefix} \nDocument: {body} {header}"
        ).split(", ")
        return label, int(value)

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        # TODO : Make this an actual batch request to the AI Completions DAL
        return [
            SentimentScoredDocument(jeeves_document=document, label=label, sentiment_score=polarity)
            for document in document_list
            for label, polarity in [self.classify(document)]
        ]
