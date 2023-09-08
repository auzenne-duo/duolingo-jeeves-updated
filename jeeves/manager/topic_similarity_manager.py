"""
A manager for filtering documents based on similarity to a target topic for sentiment analysis
"""

import json
import logging
import random
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np
import tiktoken
from duolingo_base.util import registry
from sklearn.svm import SVC
from sklearn.utils import shuffle

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.matching_document import MatchingDocument

LOG = logging.getLogger(__name__)

STRONGLY_SIMILAR_TOPIC_THRESHOLD = 0.82
SIMILAR_TOPIC_THRESHOLD = 0.80
DISSIMILAR_TOPIC_THRESHOLD = 0.79
STRONGLY_DISSIMILAR_TOPIC_THRESHOLD = 0.77

CONTEXT_LENGTH = 4096
MAX_RESPONSE_TOKENS = 700
MAX_HEADER_CHARS = 200
MAX_BODY_CHARS = 1000

REQ_ID = "id"
REQ_HEADER = "header"
REQ_BODY = "body"
REQ_RESP_TOPIC = "topic"
REQ_DOCUMENTS = "documents"
RELATED_RESP_IDS = "related ids"
UNRELATED_RESP_IDS = "unrelated ids"
RESP_ID = REQ_ID
DOCUMENT_SEPARATOR = (
    "=|*|=|*|="  # GPT document delimiter. Must be unique and not in the documents themselves.
)

# The system prompts for finding related and not unrelated documents are nearly identical. The only difference is "are relevant to" vs "are not about"
SIMILARITY_SYSTEM_PROMPT = f"""
You will be given a topic and a list of documents containing an id, header, and body.
Each document will be separated by the following delimiter: {DOCUMENT_SEPARATOR}.
Some documents are about the topic and some are not.

List any documents that ARE about the target topic in a JSON array as the value of the key "{RELATED_RESP_IDS}" in your response. Documents that
are about the target topic either contain the keywords of the topic or keywords related to
the topic.

List any documents that ARE NOT about the target topic in a JSON array as the value of the key "{UNRELATED_RESP_IDS}" in your response.

Return a JSON document with the ids of the related and unrelated documents.

Document format:
{REQ_ID}: <document_id> {REQ_HEADER}: <document_header> {REQ_BODY}: <document_body>

Input format:
{REQ_RESP_TOPIC}: <target topic>
{REQ_HEADER}: <document 1> {DOCUMENT_SEPARATOR} <document 2> {DOCUMENT_SEPARATOR} <document 3> {DOCUMENT_SEPARATOR} ...

The output must be a valid JSON object like the following:
{{
  "{RELATED_RESP_IDS}": [
    "<document_id>",
    "<document_id>",
    "<document_id>",
  ],
  "{UNRELATED_RESP_IDS}": [
    "<document_id>",
    "<document_id>",
  ]
}}
"""


class SimilarityCategory(Enum):
    SIMILAR = "similar"
    STRONGLY_SIMILAR = "strongly_similar"
    DISSIMILAR = "dissimilar"
    STRONGLY_DISSIMILAR = "strongly_dissimilar"
    RELATED = "related"  # Documents that are either similar or strongly similar
    UNRELATED = "unrelated"  # Documents that are either dissimilar or strongly dissimilar


def format_for_user_prompt(document: JeevesDocument, doc_id: str) -> str:
    """
    Truncate a document as needed and format it for GPT
    """
    translation_table = str.maketrans({"\n": " ", "\r": " ", ":": " "})

    header = document.header_text.translate(translation_table)[:MAX_HEADER_CHARS]
    body = document.body_text.translate(translation_table)[:MAX_BODY_CHARS]
    return f"{REQ_ID}:{doc_id} {REQ_HEADER}:{header} {REQ_BODY}:{body}"


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class TopicSimilarityManager:
    def __init__(
        self,
        ai_completions_dal: AICompletionsDAL,
    ):
        self.ai_completions_dal = ai_completions_dal
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

        LOG.debug(f"Filtering out documents unrelated to {target_topic}")

        # Remove documents that don't have an embedding
        documents_list = [
            document
            for document in documents_list
            if document.doc.embeddings and GPT_EMBEDDING_MODEL in document.doc.embeddings.keys()
        ]
        sorted_docs = self.sort_documents_using_cosine_similarity(documents_list)

        label_to_num = {SimilarityCategory.RELATED: 1, SimilarityCategory.UNRELATED: 0}
        num_to_label = {1: SimilarityCategory.RELATED, 0: SimilarityCategory.UNRELATED}

        svm_classifier = self.construct_svm_for_filtering(sorted_docs, target_topic, label_to_num)

        documents_list = (
            sorted_docs[SimilarityCategory.SIMILAR]
            + sorted_docs[SimilarityCategory.STRONGLY_SIMILAR]
            + sorted_docs[SimilarityCategory.DISSIMILAR]
        )
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
        target_topic: str,
        label_to_num: Dict[SimilarityCategory, int],
    ) -> SVC:
        """
        Construct a dataset for training a SVM model to filter documents based on similarity to a target topic. Then fit a SVM model to the dataset.
        """

        related_embedding = self.ai_completions_dal.request_embedding(target_topic)
        unrelated_embedding = self.ai_completions_dal.request_embedding(
            SimilarityCategory.UNRELATED.value
        )
        docs = (
            sorted_docs[SimilarityCategory.STRONGLY_SIMILAR]
            + sorted_docs[SimilarityCategory.SIMILAR]
            + sorted_docs[SimilarityCategory.DISSIMILAR]
            + sorted_docs[SimilarityCategory.STRONGLY_DISSIMILAR]
        )
        gpt_docs = self.verify_topic_using_gpt(
            likely_related_docs=docs[0 : min(75, len(docs) // 2)],
            likely_unrelated_docs=docs[max(len(docs) - 50, min(75, len(docs) // 2)) : len(docs)],
            target_topic=target_topic,
        )
        # Construct related examples for our training dataset
        related_docs = gpt_docs[SimilarityCategory.RELATED]

        # Construct unrelated examples for our training dataset
        unrelated_docs = gpt_docs[SimilarityCategory.UNRELATED]

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
        self,
        likely_related_docs: List[JeevesDocument],
        likely_unrelated_docs: List[JeevesDocument],
        target_topic: str,
    ) -> Dict[str, List[JeevesDocument]]:
        """
        Use GPT to determine which documents are related to the target topic and which are not
        related to the target topic. Return two lists where one is a list of related documents
        and one is a list of unrelated documents

        Likely related docs and likely unrelated docs should both be sorted from highest to lowest cosine similarity
        """
        relevant_docs = {SimilarityCategory.RELATED: [], SimilarityCategory.UNRELATED: []}
        user_prompt = f"{REQ_RESP_TOPIC}: {target_topic}\n{REQ_DOCUMENTS}: "
        LOG.debug(
            f"Likely Potential Documents to send to GPT-4 {[doc.jeeves_uid for doc in likely_related_docs]}"
        )
        LOG.debug(
            f"Unlikely Potential Documents to send to GPT-4 {[doc.jeeves_uid for doc in likely_unrelated_docs]}"
        )
        # We want to send the documents that are most likely to be related/unrelated to GPT
        likely_unrelated_docs.reverse()
        document_list = (
            [x for pair in zip(likely_related_docs, likely_unrelated_docs) for x in pair]
            + likely_related_docs[len(likely_unrelated_docs) :]
            + likely_unrelated_docs[len(likely_related_docs) :]
        )
        formatted_docs, id_mapper = self.get_max_docs_under_content_length_limit(document_list)
        random.shuffle(formatted_docs)  # Improves GPT results
        user_prompt += f"\n {DOCUMENT_SEPARATOR} \n".join(formatted_docs)
        response_text = self.ai_completions_dal.ask(
            system_prompt=SIMILARITY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=MAX_RESPONSE_TOKENS,
        )
        response_data = json.loads(response_text)

        if RELATED_RESP_IDS in response_data:
            related_id_set = set(response_data[RELATED_RESP_IDS])
            relevant_docs[SimilarityCategory.RELATED] = [
                doc
                for doc in document_list
                if (doc.jeeves_uid in id_mapper and id_mapper[doc.jeeves_uid] in related_id_set)
            ]
        if UNRELATED_RESP_IDS in response_data:
            unrelated_id_set = set(response_data[UNRELATED_RESP_IDS])
            relevant_docs[SimilarityCategory.UNRELATED] = [
                doc
                for doc in document_list
                if (doc.jeeves_uid in id_mapper and id_mapper[doc.jeeves_uid] in unrelated_id_set)
            ]
        LOG.debug(
            f"GPT found these documents to be about {target_topic}: {[doc.jeeves_uid for doc in relevant_docs[SimilarityCategory.RELATED]]}"
        )
        LOG.debug(
            f"GPT found these documents to not be about {target_topic}: {[doc.jeeves_uid for doc in relevant_docs[SimilarityCategory.UNRELATED]]}"
        )
        return relevant_docs

    def get_max_docs_under_content_length_limit(
        self, docs: List[JeevesDocument]
    ) -> Tuple[List[str], Dict[int, str]]:
        """
        Given the CONTEXT_LENGTH for our GPT model, return the greatest number of documents possible
        while still staying under the total token limit.
        """
        system_prompt_token_sum = self.token_len(SIMILARITY_SYSTEM_PROMPT)
        # Leave ten as a buffer in case the token calculation is off
        max_remaining_tokens = CONTEXT_LENGTH - system_prompt_token_sum - MAX_RESPONSE_TOKENS - 10

        docs_token_sum = 0
        final_docs = []
        curr_id = 0
        id_mapper = {}
        for doc in docs:
            formatted = format_for_user_prompt(doc, str(curr_id))
            n = self.token_len(formatted)
            docs_token_sum += n
            if docs_token_sum > max_remaining_tokens:
                break
            final_docs.append(formatted)
            id_mapper[doc.jeeves_uid] = str(curr_id)
            curr_id += 1

        return final_docs, id_mapper

    def token_len(self, text: str):
        return len(self.tokenizer.encode(text))
