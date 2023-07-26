"""
A manager for filtering documents based on similarity to a target topic for sentiment analysis
"""

import random
import re
from enum import Enum
from typing import Dict, List

import numpy as np
import tiktoken
from duolingo_base.util import registry
from sklearn.svm import SVC
from sklearn.utils import shuffle

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.manager.topic_definition_manager import TopicDefinitionManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.matching_document import MatchingDocument

STRONGLY_SIMILAR_TOPIC_THRESHOLD = 0.82
SIMILAR_TOPIC_THRESHOLD = 0.80
DISSIMILAR_TOPIC_THRESHOLD = 0.79
STRONGLY_DISSIMILAR_TOPIC_THRESHOLD = 0.77

CONTEXT_LENGTH = 4096
MAX_RESPONSE_TOKENS = 512
MAX_HEADER_CHARS = 200
MAX_BODY_CHARS = 1000

REQ_ID = "id"
REQ_HEADER = "header"
REQ_BODY = "body"
REQ_RESP_TOPIC = "topic"
REQ_DOCUMENTS = "documents"
RESP_ID = "ids"
DOCUMENT_SEPARATOR = (
    "=|*|=|*|="  # GPT document delimiter. Must be unique and not in the documents themselves.
)

# The system prompts for finding related and not unrelated documents are nearly identical. The only difference is "are relevant to" vs "are not about"
SIMILARITY_SYSTEM_PROMPT_PART_1 = f"""
You will be given a topic and a list of documents containing an id, header, and body.
Each document will be separated by the following delimiter: {DOCUMENT_SEPARATOR}.
Identify which documents
"""

SIMILARITY_SYSTEM_PROMPT_RELATED = f"""
 are relevant to
"""

SIMILARITY_SYSTEM_PROMPT_UNRELATED = f"""
 are not about
"""

SIMILARITY_SYSTEM_PROMPT_PART_2 = f"""
the target topic and return only the document ids in a comma separated list.
For example you could output: {RESP_ID}: AppFigures_1698, AppFigures_189, AppFigures_980

Document format:
{REQ_ID}: <document_id> {REQ_HEADER}: <document_header> {REQ_BODY}: <document_body>

Input format:
{REQ_RESP_TOPIC}: <target topic>
{REQ_HEADER}: <document 1> {DOCUMENT_SEPARATOR} <document 2> {DOCUMENT_SEPARATOR} <document 3> {DOCUMENT_SEPARATOR} ...

Output format:
{RESP_ID}: <id>, <id>, <id>, ...

Always include {RESP_ID} at the start of the output
"""


class SimilarityCategory(Enum):
    SIMILAR = "similar"
    STRONGLY_SIMILAR = "strongly_similar"
    DISSIMILAR = "dissimilar"
    STRONGLY_DISSIMILAR = "strongly_dissimilar"
    RELATED = "related"  # Documents that are either similar or strongly similar
    UNRELATED = "unrelated"  # Documents that are either dissimilar or strongly dissimilar


def format_for_user_prompt(document: JeevesDocument) -> str:
    """
    Truncate a document as needed and format it for GPT
    """
    header = document.header_text.replace("\n", " ")[:MAX_HEADER_CHARS]
    body = document.body_text.replace("\n", " ")[:MAX_BODY_CHARS]
    return f"{REQ_ID}:{document.jeeves_uid} {REQ_HEADER}:{header} {REQ_BODY}:{body}"


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
    topic_definition_manager=registry.reference(TopicDefinitionManager),
)
class TopicSimilarityManager:
    def __init__(
        self,
        ai_completions_dal: AICompletionsDAL,
        topic_definition_manager: TopicDefinitionManager,
    ):
        self.ai_completions_dal = ai_completions_dal
        self.topic_definition_manager = topic_definition_manager
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

    def filter_documents_using_topic(
        self, documents_list: List[MatchingDocument], target_topic: str
    ) -> List[JeevesDocument]:
        """
        Use cosine similarity to sort the documents by similarity. Then double check the results by sending the two lists of
        related and not related documents to GPT. The training data will contain all the strongly similar and strongly dissimilar documents.
        A subset of the related and not related documents will be labeled by gpt and included in the training data as well.
        Construct a SVM model and use it to predict which documents are related to the target topic.
        """

        # Remove documents that don't have an embedding
        documents_list = [
            document
            for document in documents_list
            if GPT_EMBEDDING_MODEL in document.doc.embeddings.keys()
        ]
        sorted_docs = self.sort_documents_using_cosine_similarity(documents_list)

        label_to_num = {SimilarityCategory.RELATED: 1, SimilarityCategory.UNRELATED: 0}
        num_to_label = {1: SimilarityCategory.RELATED, 0: SimilarityCategory.UNRELATED}

        topic_description = self.topic_definition_manager.get_topic_description(target_topic)
        svm_classifier = self.construct_svm_for_filtering(
            sorted_docs, topic_description, label_to_num
        )

        documents_list = [document.doc for document in documents_list]
        test_embeddings = np.array(
            [document.embeddings[GPT_EMBEDDING_MODEL] for document in documents_list]
        )
        test_labels = svm_classifier.predict(test_embeddings)

        related_docs = [
            documents_list[i]
            for i in range(len(documents_list))
            if num_to_label[test_labels[i]] == SimilarityCategory.RELATED
        ]

        return related_docs

    def construct_svm_for_filtering(
        self,
        sorted_docs: Dict[str, List[JeevesDocument]],
        topic_description: str,
        label_to_num: Dict[SimilarityCategory, int],
    ) -> SVC:
        """
        Construct a dataset for training a SVM model to filter documents based on similarity to a target topic. Then fit a SVM model to the dataset.
        """

        related_embedding = self.ai_completions_dal.request_embedding(topic_description)
        unrelated_embedding = self.ai_completions_dal.request_embedding(
            SimilarityCategory.UNRELATED.value
        )

        # Construct related examples for our training dataset
        related_docs = sorted_docs[
            SimilarityCategory.STRONGLY_SIMILAR
        ] + self.verify_topic_using_gpt(
            sorted_docs[SimilarityCategory.SIMILAR]
            + sorted_docs[SimilarityCategory.STRONGLY_SIMILAR],
            topic_description,
            True,
        )

        # Construct unrelated examples for our training dataset
        unrelated_docs = sorted_docs[
            SimilarityCategory.STRONGLY_DISSIMILAR
        ] + self.verify_topic_using_gpt(
            sorted_docs[SimilarityCategory.DISSIMILAR]
            + sorted_docs[SimilarityCategory.STRONGLY_DISSIMILAR],
            topic_description,
            False,
        )

        training_embeddings = np.array(
            [doc.embeddings[GPT_EMBEDDING_MODEL] for doc in related_docs + unrelated_docs]
            + [related_embedding, unrelated_embedding]
        )
        labels = np.concatenate(
            (
                np.full((len(related_docs),), label_to_num[SimilarityCategory.RELATED]),
                np.full((len(unrelated_docs),), label_to_num[SimilarityCategory.UNRELATED]),
                np.array(
                    [
                        label_to_num[SimilarityCategory.RELATED],
                        label_to_num[SimilarityCategory.UNRELATED],
                    ]
                ),
            ),
            axis=None,
        )
        training_embeddings, labels = shuffle(training_embeddings, labels, random_state=0)

        svm_classifier = SVC(kernel="rbf", probability=True)
        svm_classifier.fit(training_embeddings, labels)

        return svm_classifier

    def sort_documents_using_cosine_similarity(
        self, documents_list: List[MatchingDocument]
    ) -> Dict[str, List[JeevesDocument]]:
        """
        Sort documents into four lists: similar, strongly similar, dissimilar, and strongly dissimilar.
        Not all documents will be returned. We want documents that would be good to train our classifier on.
        """
        sorted_docs = {
            SimilarityCategory.SIMILAR: [],
            SimilarityCategory.DISSIMILAR: [],
            SimilarityCategory.STRONGLY_SIMILAR: [],
            SimilarityCategory.STRONGLY_DISSIMILAR: [],
        }
        for document in documents_list:
            if document.score > STRONGLY_SIMILAR_TOPIC_THRESHOLD:
                sorted_docs[SimilarityCategory.STRONGLY_SIMILAR].append(document.doc)
            elif document.score > SIMILAR_TOPIC_THRESHOLD:
                sorted_docs[SimilarityCategory.SIMILAR].append(document.doc)
            elif document.score < STRONGLY_DISSIMILAR_TOPIC_THRESHOLD:
                sorted_docs[SimilarityCategory.STRONGLY_DISSIMILAR].append(document.doc)
            elif document.score < DISSIMILAR_TOPIC_THRESHOLD:
                sorted_docs[SimilarityCategory.DISSIMILAR].append(document.doc)
        return sorted_docs

    def verify_topic_using_gpt(
        self, documents_list: List[JeevesDocument], topic_description: str, get_similar: bool
    ) -> List[JeevesDocument]:
        """
        Use GPT to determine which documents are related to the target topic when the get_similar boolean is true.
        Otherwise use GPT to determine which documents are unrelated to the target topic.
        """
        user_prompt = f"{REQ_RESP_TOPIC}: {topic_description}\n{REQ_DOCUMENTS}: "
        random.shuffle(documents_list)
        user_prompt += f"\n {DOCUMENT_SEPARATOR} \n".join(
            self.get_max_docs_under_content_length_limit(documents_list)
        )
        similarity_prompt = (
            SIMILARITY_SYSTEM_PROMPT_RELATED if get_similar else SIMILARITY_SYSTEM_PROMPT_UNRELATED
        )
        system_prompt = (
            SIMILARITY_SYSTEM_PROMPT_PART_1 + similarity_prompt + SIMILARITY_SYSTEM_PROMPT_PART_2
        )
        response_text = self.ai_completions_dal.ask(system_prompt, user_prompt)
        pattern = rf"^{RESP_ID}:"
        doc_ids = set([id.strip(" ") for id in set(re.split(pattern, response_text)[1].split(","))])

        filtered_docs = []
        for doc in documents_list:
            if doc.jeeves_uid in doc_ids:
                filtered_docs.append(doc)

        return filtered_docs

    def get_max_docs_under_content_length_limit(self, docs: List[JeevesDocument]) -> List[str]:
        """
        Given the CONTEXT_LENGTH for our GPT model, return the greatest number of documents possible
        while still staying under the total token limit.
        """
        system_prompt_token_sum = self.token_len(
            SIMILARITY_SYSTEM_PROMPT_PART_1
            + SIMILARITY_SYSTEM_PROMPT_RELATED
            + SIMILARITY_SYSTEM_PROMPT_PART_2
        )
        # Leave ten as a buffer in case the token calculation is off
        max_remaining_tokens = CONTEXT_LENGTH - system_prompt_token_sum - MAX_RESPONSE_TOKENS - 10

        docs_token_sum = 0
        final_docs = []
        for doc in docs:
            formatted = format_for_user_prompt(doc)
            n = self.token_len(formatted)
            docs_token_sum += n
            if docs_token_sum > max_remaining_tokens:
                break
            final_docs.append(formatted)

        return final_docs

    def token_len(self, text: str):
        return len(self.tokenizer.encode(text))
