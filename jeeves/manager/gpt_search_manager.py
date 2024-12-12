"""
A manager for the Jeeves GPT Search functionality.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from asyncio import create_task, gather
from dataclasses import asdict, dataclass
from datetime import datetime
from json import JSONDecodeError
from threading import Thread
from typing import Any, List, Optional

import tiktoken
from opensearchpy import OpenSearchException
from requests import RequestException

from jeeves import registry as app_registry
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.memcached_client import get_memcached_client
from jeeves.manager.query_helper import DSLQueryResponse, QueryHelper
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.matching_document import MatchingDocument
from jeeves.model.search_result import DocumentContent
from jeeves.util.date_util import get_date_prefix_for_system_prompt

LOG = logging.getLogger(__name__)

# CACHE SETTINGS
# The number of seconds to cache the results
CACHE_TTL_SECONDS = 3600

# k-NN SETTINGS
# The max number of results to return from the k-NN search
MAX_KNN_RESULTS = 1000
# The minimum confidence score for a document to be considered a hit
MIN_CONF_THRESHOLD = 0.7

# TOKEN LIMITS
# The maximum number of tokens for the request *and* response. This is fixed by GPT and cannot be increased.
CONTEXT_LENGTH = 4096
# The maximum number of tokens we are requesting to be returned in the response from GPT.
#   NB: The number of tokens in the request and in the response must be less than or equal to CONTEXT_LENGTH.
MAX_RESPONSE_TOKENS = 1024

# CHARACTER LIMITS
# The maximum allowed length (in characters) for the text fields for a JeevesDocument for sending to OpenAI,
#   above which we will truncate the string and send only the first part up to this limit.
# This is to prevent a single document from taking up the whole user prompt
MAX_BODY_CHARS = 1000
MAX_TITLE_CHARS = 250

# DISPLAY LIMITS
# The maximum number of spans of words to highlight in the display of the documents shown to the user
MAX_BOLDED_SPANS = 3
# The maximum number of documents to show to the user
NUM_RESULTS = 5

# PROMPT TEMPLATES
# These are used to construct the chat completions requests.
REQ_DOCUMENTS = "Documents"
REQ_QUESTION = "Question"

# KEYS TO THE REQUEST YAML
# These are the keys to the fields found in the request YAML object sent as context information to GPT.
REQ_ID = "id"
REQ_TITLE = "title"
REQ_BODY = "body"

# KEYS TO THE RESPONSE JSON
# These are the keys to the fields found in the response JSON object returned by GPT.
RESP_ANSWER = "answer"
RESP_DOC_BODY_BOLDED = "doc_body_bolded"
RESP_DOC_LANG = "doc_language"
RESP_ID = REQ_ID
RESP_MATCHES = "matches"
RESP_TRANSL_BODY_BOLDED = "translation_body_bolded"
RESP_TRANSL_LANG = "translation_language"
RESP_TRANSL_TITLE = "translation_title"

SYSTEM_PROMPT = f"""
You are a web application that summarizes data from across the internet and helps employees of the company Duolingo
to gain insight into what users are saying about Duolingo's products across the internet from various sources.

Given the "{REQ_DOCUMENTS}" provided and no prior knowledge, answer the "{REQ_QUESTION}" asked by the user in the same
language as the question. If "{REQ_QUESTION}" is not a question, provide a short summary in English about the documents
in "{REQ_DOCUMENTS}", in particular the ones that relate to the words the user typed in "{REQ_QUESTION}".

Give your response in JSON format and store the answer to the question as the value to the key "{RESP_ANSWER}".
In the value for the key "{RESP_MATCHES}", give an list of at most {NUM_RESULTS} JSON objects representing the
documents that best support the answer in "{RESP_ANSWER}", with the most relevant documents sorted first in the list,
and with key words and phrases bolded with <b/> tags to draw attention to the relevant parts.
Furthermore, if the document is not written in the same language as "{REQ_QUESTION}", translate the document into
the language of "{REQ_QUESTION}" and put it in the field "{RESP_TRANSL_BODY_BOLDED}" of the JSON object.
Keep the bolding consistent between the original text and the translation. The "language of '{REQ_QUESTION}'" is
the language the question is WRITTEN in, not the language it is ABOUT. For example, "What do Polish users think
about the English course?" is written in English, so all Polish documents should have an English translation populated
in the field "{RESP_TRANSL_BODY_BOLDED}".

Each item in the list is a JSON object containing the fields (all required):
- "{RESP_ID}": The document ID (taken directly from the field "{REQ_ID}" of "{REQ_DOCUMENTS}")
- "{RESP_DOC_BODY_BOLDED}": A sample of the text from the document (taken from the field "{REQ_BODY}" of
  "{REQ_DOCUMENTS}"), but with <b></b> tags added around between 0 and {MAX_BOLDED_SPANS} words or phrases that best
  match the query in "{REQ_QUESTION}" or which support the answer in "{RESP_ANSWER}".
- "{RESP_DOC_LANG}": The English name of the language of the document's title and body text
- "{RESP_TRANSL_BODY_BOLDED}": The text of the document translated into the language of the question, with <b></b>
  tags added that exactly match the ones in "{RESP_DOC_BODY_BOLDED}". If the document language already matches, use
  the null value.
- "{RESP_TRANSL_LANG}": The language of the translated document in "{RESP_TRANSL_BODY_BOLDED}" and
  "{RESP_TRANSL_TITLE}", which should exactly match the language of the question. If the document language already
  matches, use the null value.
- "{RESP_TRANSL_TITLE}" The title of the document translated into the language of the question. If the document
  language already matches, use the null value.

For example, if the "{REQ_QUESTION}" is "What do users think about the Friends feature?", your answer may be:
{{
  "{RESP_ANSWER}": "Users like the friends feature, but some reported difficulty adding friends.",
  "{RESP_MATCHES}": [ {{
    "{RESP_ID}": "AppFigures_5513570",
    "{RESP_DOC_BODY_BOLDED}": "Uwielbiam to, że mogę zobaczyć moich <b>znajomych</b> w aplikacji!",
    "{RESP_DOC_LANG}": "Polish",
    "{RESP_TRANSL_BODY_BOLDED}": "I love that I can see my <b>friends</b> on the app!",
    "{RESP_TRANSL_LANG}": "English",
    "{RESP_TRANSL_TITLE}": "Nice app!"
  }}, {{
    "{RESP_ID}": "JIRA_247210",
    "{RESP_DOC_BODY_BOLDED}": "<b>Add friends</b> button is broken",
    "{RESP_DOC_LANG}": "English",
    "{RESP_TRANSL_BODY_BOLDED}": null,
    "{RESP_TRANSL_LANG}": null,
    "{RESP_TRANSL_TITLE}": null
  }}, {{
    "{RESP_ID}": "Zendesk_324721",
    "{RESP_DOC_BODY_BOLDED}": "J'aime donner des <b>félicitations</b> à mes <b>amis</b>",
    "{RESP_DOC_LANG}": "French",
    "{RESP_TRANSL_BODY_BOLDED}": "I love giving <b>kudos</b> to my <b>friends</b>",
    "{RESP_TRANSL_LANG}": "English",
    "{RESP_TRANSL_TITLE}": "This is fun!"
  }} ]
}}
"""


@dataclass
class JeevesException(Exception):
    exc_info: Optional[Exception]
    message: Optional[str]

    def log_error(self, request_id: str) -> None:
        LOG.error(f"{self.message} (Request ID: {request_id})", exc_info=self.exc_info)


@dataclass
class GPTResponseDocument:
    """
    A single document returned by GPT, which it thinks supports its answer to the question
    """

    id: str
    doc_body_bolded: str
    doc_language: str
    translation_body_bolded: Optional[str]
    translation_language: Optional[str]
    translation_title: Optional[str]

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> GPTResponseDocument:
        return cls(
            id=d[RESP_ID],
            doc_body_bolded=d[RESP_DOC_BODY_BOLDED],
            doc_language=d[RESP_DOC_LANG],
            translation_body_bolded=d.get(RESP_TRANSL_BODY_BOLDED),
            translation_language=d.get(RESP_TRANSL_LANG),
            translation_title=d.get(RESP_TRANSL_TITLE),
        )


@dataclass
class GPTResponse:
    """
    The response from GPT in the format we defined in the system prompt
    """

    answer: str
    matches: list[GPTResponseDocument]

    @classmethod
    def from_json(cls, json_str: str) -> GPTResponse:
        # Sanitize all control characters from JSON string before parsing
        json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", json_str)
        data = json.loads(json_str)
        matches = [
            GPTResponseDocument.from_dict(match)
            for match in data[RESP_MATCHES]
            if match is not None
        ]
        return cls(answer=data[RESP_ANSWER], matches=matches)


@dataclass
class LanguageContent(DocumentContent):
    """
    The localized content of a JeevesDocument to display in a table cell in the frontend
    """

    body_orig: Optional[str]  # The original body text before we asked GPT to bold keywords in it
    language: str


@dataclass
class GPTSearchResult:
    """
    A JSON of a JeevesDocument that GPT suggested as supporting evidence for the answer it gave to the user
    with the translated text and cosine similarity
    """

    bolded_body: str
    translated_text: Optional[LanguageContent]
    score: float
    doc: dict[str, Any]

    @classmethod
    def from_jeeves_document(
        cls, doc: JeevesDocument, match: GPTResponseDocument, score: float
    ) -> GPTSearchResult:
        translated_text = None
        if match.translation_body_bolded is not None:
            translated_text = LanguageContent(
                body=match.translation_body_bolded,
                body_orig=None,
                language=match.translation_language if match.translation_language else "",
                title=match.translation_title if match.translation_title else "",
            )
        return cls(
            bolded_body=match.doc_body_bolded,
            score=score,
            translated_text=translated_text,
            doc=JeevesDocument.serialize_to_json(doc),
        )


@dataclass
class GPTSearchStartedResponse:
    """
    The initial acknowledgement of the request to start a GPT Search, which includes a request ID and a set of
    OpenSearch filters parsed from the request string.
    """

    lucene_filters: dict[str, str]
    request_id: str
    error: Optional[str] = None


@dataclass
class GPTSearchResults:
    """
    The object we will return to the user from /api/3/gpt_search
    """

    answer: str
    supporting_docs: list[GPTSearchResult]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass()
class KNNSearchResponse:
    """
    Our internal API response for /api/3/gpt_search_get_knn_results, containing the matching documents and any errors.
    """

    docs: list[JeevesDocument]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> dict[str, Any]:
        response_dict = self.to_dict()
        docs_json = [JeevesDocument.serialize_to_json(d) for d in self.docs]
        response_dict["docs"] = docs_json
        return response_dict


@dataclass
class KNNSearchResult:
    """
    The result of a k-NN search, containing the document IDs and the scores for each (and the error if there was one)
    """

    id_to_score: dict[str, float]
    error: Optional[str] = None


def get_system_prompt() -> str:
    return get_date_prefix_for_system_prompt() + SYSTEM_PROMPT


def format_for_user_prompt(md: MatchingDocument) -> str:
    """
    Extract the relevant text fields of a JeevesDocument to send to ai-completions-backend during the user prompt.
    """
    doc = md.doc
    header_stripped = re.sub(r"\s+", " ", doc.header_text).strip()
    title = header_stripped[:MAX_TITLE_CHARS]

    body_stripped = doc.body_text.replace("\n", " ")
    body = body_stripped[:MAX_BODY_CHARS]

    return f"{REQ_ID}: {doc.jeeves_uid}\n{REQ_TITLE}: {title}\n{REQ_BODY}: {body}"


def get_embedding(
    query: str,
) -> list[float]:
    """
    Request a text embedding vector from OpenAI for the user's query.
    """
    try:
        embedding = app_registry(AICompletionsDAL).request_embedding(query, raise_exceptions=True)
    except RequestException as e:
        raise JeevesException(
            e, "An exception was returned from OpenAI while requesting a text embedding."
        )

    if embedding is None or len(embedding) == 0:
        raise JeevesException(None, "Could not retrieve the text embedding from OpenAI.")

    return embedding


def get_dsl_query(
    query: str,
) -> DSLQueryResponse:
    """
    Extract an OpenSearch DSL query and a matching lucene query from GPT
    """
    try:
        dsl_response = app_registry(QueryHelper).get_dsl_query_and_topics(
            query, raise_exceptions=True
        )
    except RequestException as e:
        raise JeevesException(e, "Did not receive a DSL query in the response from OpenAI.")
    except JSONDecodeError as e:
        raise JeevesException(e, "Invalid DSL query returned from OpenAI.")
    except KeyError as e:
        raise JeevesException(e, "The DSL query returned by OpenAI is in the incorrect format.")

    if dsl_response is None:
        raise JeevesException(
            None, "Could not get an OpenSearch DSL query from OpenAI from this query."
        )

    LOG.debug(f"DSL query: {dsl_response.dsl_query}")
    LOG.debug(f"Lucene filters: {dsl_response.lucene_filters}")
    LOG.debug(f"Topic: {dsl_response.target_topic}")

    return dsl_response


def extract_supporting_docs(
    gpt_matches: list[GPTResponseDocument],
    hits: list[MatchingDocument],
) -> list[GPTSearchResult]:
    """
    Given a list of documents selected by GPT, return a list of GPTSearchResult objects to return to the user.

    Params:
        gpt_matches (List[GPTResponseDocument]): The list of documents that GPT selected
        hits (List[MatchingDocument]): The list of documents that were returned by OpenSearch

    Returns:
        A list of GPTSearchResult objects to return to the user
    """
    # Construct a map of ID to MatchingDocument for the documents that GPT selected
    id_to_doc: dict[str, MatchingDocument] = {doc.doc.jeeves_uid: doc for doc in hits}

    supporting_docs: list[GPTSearchResult] = []
    for gpt_match in gpt_matches:
        _id = gpt_match.id
        _id = _id.strip()
        if _id not in id_to_doc:
            LOG.warning(f"GPT selected the document ID {_id} which does not exist in our dict")
            continue

        matching_doc = id_to_doc[_id]
        result = GPTSearchResult.from_jeeves_document(
            matching_doc.doc, gpt_match, matching_doc.score
        )
        supporting_docs.append(result)

    return supporting_docs


class GPTSearchManager:
    def __init__(self) -> None:
        LOG.debug("Initializing GPTSearchManager...")
        self.opensearch = app_registry(OpenSearchDAL)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

        # A map of the hash to the text embedding of the user's query
        self.emb_cache = get_memcached_client("emb", expiration=CACHE_TTL_SECONDS)
        # A map of the hash to the OpenSearch filters extracted from the request string
        self.dsl_cache = get_memcached_client("dsl", expiration=CACHE_TTL_SECONDS)
        # A map of the hash to the results of the k-NN search (IDs only)
        self.knn_cache = get_memcached_client("knn", expiration=CACHE_TTL_SECONDS)
        # A map of the hash to the results of the GPT search
        self.gpt_cache = get_memcached_client("gpt", expiration=CACHE_TTL_SECONDS)

    def token_len(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def get_max_docs_under_content_length_limit(
        self, docs: list[MatchingDocument], max_response_tokens: int, prompts: list[str]
    ) -> list[str]:
        """
        Given the CONTEXT_LENGTH for our GPT model, return as many documents as possible
        while still staying under the total token limit (tokens in request + response combined).
        """
        prompts_token_sum = sum(self.token_len(p) for p in prompts)
        LOG.debug(f"Total tokens used in prompts: {prompts_token_sum}")
        # Less ten as a buffer in case the token calculation is off
        max_remaining_tokens = CONTEXT_LENGTH - prompts_token_sum - max_response_tokens - 10
        LOG.debug(f"Remaining number of tokens to fill with documents: {max_remaining_tokens}")

        docs_token_sum = 0
        final_docs = []
        for doc in docs:
            formatted = format_for_user_prompt(doc)
            n = self.token_len(formatted)
            if docs_token_sum + n > max_remaining_tokens:
                break

            docs_token_sum += n
            final_docs.append(formatted)

        LOG.debug(f"Total number of tokens used in documents: {docs_token_sum}")
        LOG.debug(f"Unused token balance: {max_remaining_tokens - docs_token_sum}")
        LOG.debug(f"Total number of docs being checked: {len(docs)}")
        LOG.debug(f"Number of docs being sent to GPT: {len(final_docs)}")
        return final_docs

    async def get_embedding_cached(
        self,
        hash_key: str,
        query: str,
    ) -> list[float]:
        """
        Return the text embedding vector for the user's query, either from the cache or by requesting it from OpenAI.

        Params:
            hash_key (str): The key to use for the memcached cache
            query (str): The user's query

        Returns:
            The text embedding vector from OpenAI
        """
        cached_embedding: list[float] = self.emb_cache.get(hash_key)
        if cached_embedding and len(cached_embedding) > 0:
            LOG.debug(
                f"Found cached text embedding vector for query '{query}', reusing cached embedding."
            )
            self.emb_cache.set(hash_key, cached_embedding)
            return cached_embedding

        LOG.debug(
            f"Did not find a cached text embedding vector for query '{query}'. Requesting an embedding..."
        )

        # Will raise a JeevesException if this is not successful
        result = get_embedding(query)
        self.emb_cache.set(hash_key, result)
        return result

    async def get_dsl_query_cached(
        self,
        hash_key: str,
        query: str,
    ) -> DSLQueryResponse:
        """
        Extract an OpenSearch DSL query and a matching lucene query from GPT, either from the cache or by requesting
          it from OpenAI.

        Params:
            hash_key (str): The key to use for the memcached cache
            query (str): The user's query

        Returns:
            The DSLQueryResponse object containing the DSL query and the lucene filters
        """
        cached_dsl_response: DSLQueryResponse = self.dsl_cache.get(hash_key)
        if cached_dsl_response and cached_dsl_response.dsl_query:
            LOG.debug(f"Found cached DSL Query for query '{query}', reusing cached response.")
            self.dsl_cache.set(hash_key, cached_dsl_response)
            return cached_dsl_response

        LOG.debug(f"Did not find a cached DSL Query for query '{query}'. Requesting one...")

        # Will raise a JeevesException if this is not successful
        dsl_response = get_dsl_query(query)
        self.dsl_cache.set(hash_key, dsl_response)
        return dsl_response

    def knn_search(
        self,
        filters: dict[str, Any],
        max_search_depth: int,
        query_embedding: list[float],
    ) -> KNNSearchResult:
        """
        Given a set of OpenSearch filters and a text embedding, perform a k-NN search against our Jeeves document index
          to find the most relevant documents.

        Params:
            filters (Dict[str, Any]): The OpenSearch filters to use for the search
            max_search_depth (int): The maximum number of documents to search through
            query_embedding (List[float]): The text embedding of the user's query

        Returns:
            A KNNSearchResult object containing the document IDs and their scores.
        """
        # Even though we search through max_search_depth items to find the approximate k-NN results, fewer may be
        #   returned because of the post_filter steps. Request 1000 results, then we'll get back fewer than 1000,
        #   and ultimately we'll only send to GPT-4 the top matches that fit in the token limit.
        num_knn_results = min(MAX_KNN_RESULTS, max_search_depth)

        # Measure the time it takes to perform the search
        start_time = datetime.now()
        try:
            hits = self.opensearch.perform_knn_search(
                filters,
                query_embedding,
                ids_only=True,  # Return the document IDs only, not the full documents
                max_search_depth=max_search_depth,
                num_results=num_knn_results,
                threshold=MIN_CONF_THRESHOLD,
            )
        except OpenSearchException as e:
            raise JeevesException(
                e, "Got an exception from OpenSearch while executing k-NN search."
            )
        except KeyError as e:
            raise JeevesException(e, "Could not parse the response from OpenSearch.")
        finally:
            end_time = datetime.now()
            LOG.debug(f"Response time for k-NN search: {end_time - start_time}")

        if not hits:
            raise JeevesException(
                None,
                "No Jeeves documents found that match the document IDs provided. The k-NN results cache may be stale.",
            )

        # The hits contain only the document IDs. Extract the IDs into a list.
        id_to_score = {doc_id: matching_doc.score for doc_id, matching_doc in hits.items()}
        LOG.debug(f"Saving {len(id_to_score)} hit IDs to memcached: {id_to_score}")

        return KNNSearchResult(id_to_score)

    def knn_search_cached(
        self,
        filters: dict[str, Any],
        hash_key: str,
        max_search_depth: int,
        query: str,
        query_embedding: list[float],
    ) -> KNNSearchResult:
        """
        Given a set of OpenSearch filters and a text embedding, perform a k-NN search against our Jeeves document
          index, but first return the cache and return that if a successful result exists. Cache the result.

        Params:
            filters (Dict[str, Any]): The OpenSearch filters to use for the search
            hash_key (str): The key to use for the memcached cache
            max_search_depth (int): The maximum number of documents to search through
            query (str): The user's query
            query_embedding (List[float]): The text embedding of the user's query

        Returns:
            A KNNSearchResult object containing the document IDs and their scores.
        """
        cached_result: KNNSearchResult = self.knn_cache.get(hash_key)
        if cached_result and cached_result.id_to_score and not cached_result.error:
            LOG.debug(f"Found cached k-NN results for query '{query}', reusing cached results.")
            self.knn_cache.set(hash_key, cached_result)
            return cached_result

        LOG.debug(
            f"Did not find any cached k-NN results for query '{query}'. Starting a new search..."
        )

        try:
            result = self.knn_search(filters, max_search_depth, query_embedding)
        except JeevesException as e:
            e.log_error(hash_key)
            result = KNNSearchResult({}, error=e.message)

        self.knn_cache.set(hash_key, result)
        return result

    def run_mget(self, id_to_score: dict[str, float]) -> list[MatchingDocument]:
        # Measure the time it takes to perform the search
        start_time = datetime.now()
        try:
            hits = self.opensearch.multi_get_with_score(id_to_score)
        except OpenSearchException as e:
            raise JeevesException(
                e, "Encountered an error retrieving documents from OpenSearch by ID."
            )
        finally:
            end_time = datetime.now()
            LOG.debug(f"Response time for mget: {end_time - start_time}")

        if not hits or len(hits) == 0:
            raise JeevesException(None, "No Jeeves documents found that match the IDs provided.")

        return hits

    def gpt_chat_completion(
        self,
        hits: list[MatchingDocument],
        num_results: int,
        query: str,
    ) -> GPTSearchResults:
        """
        Given a list of MatchingDocuments, determine the maximum number that can be sent while staying under the
          token limit, and send them to GPT to answer the user's `query` or summarize.

        Params:
            hits (List[MatchingDocument]): The list of MatchingDocuments to send to GPT
            num_results (int): The maximum number of results to return to the user
            query (str): The user's query

        Returns:
            A GPTSearchResults object containing the answer and the list of supporting documents.
        """
        sys_prompt = get_system_prompt()
        prompts = [sys_prompt, REQ_DOCUMENTS, REQ_QUESTION, query]
        max_docs_formatted = self.get_max_docs_under_content_length_limit(
            hits, MAX_RESPONSE_TOKENS, prompts
        )
        docs_combined: str = "\n".join(max_docs_formatted)

        user_prompt = (
            f"{REQ_QUESTION}: {query}\n"
            f"{REQ_DOCUMENTS}:\n"
            "---------------------\n"
            f"{docs_combined}\n"
            "---------------------\n"
        )

        # Measure the time it takes to perform the search
        start_time = datetime.now()
        try:
            openai_resp = app_registry(AICompletionsDAL).ask(
                max_tokens=MAX_RESPONSE_TOKENS,
                raise_exceptions=True,
                system_prompt=sys_prompt,
                use_json_mode=True,
                user_prompt=user_prompt,
            )
        except RequestException as e:
            raise JeevesException(
                e, "An exception was returned from OpenAI while requesting a GPT summary."
            )
        finally:
            end_time = datetime.now()
            LOG.debug(f"Response time for OpenAI /chat/completions: {end_time - start_time}")

        if openai_resp is None:
            raise JeevesException(
                None, "Invalid response from OpenAI while requesting a GPT summary."
            )

        try:
            # Parse the response from GPT as a GPTResponse object
            gpt_response = GPTResponse.from_json(openai_resp)
            answer = gpt_response.answer
            gpt_matches = gpt_response.matches
        except JSONDecodeError as decode_error:
            raise JeevesException(decode_error, "Could not deserialize response from GPT.")

        if not gpt_response:
            raise JeevesException(None, "Invalid response from GPT.")
        if not answer:
            raise JeevesException(None, "Could not find an answer in the response from GPT.")
        if not gpt_matches:
            # This is a possible and valid response from GPT
            LOG.debug(f"Could not find field '{RESP_MATCHES}' in response {openai_resp}.")
            gpt_matches = []

        if len(gpt_matches) > num_results:
            LOG.warning(
                f"GPT returned {len(gpt_matches)} documents in its response; "
                f"truncating to the requested {num_results}"
            )
            gpt_matches = gpt_matches[:num_results]

        supporting_docs = extract_supporting_docs(gpt_matches, hits)

        LOG.debug(f"Sending response to user: {answer}")
        return GPTSearchResults(answer, supporting_docs)

    def gpt_chat_completion_cached(
        self,
        hash_key: str,
        hits: list[MatchingDocument],
        num_results: int,
        query: str,
    ) -> None:
        """
        Given a list of MatchingDocuments, determine the maximum number that can be sent while staying under the
          token limit, and send them to GPT to answer the user's `query` or summarize. Cache the results so that they
          can be retrieved asynchronously when requested by the browser.

        Params:
            hash_key (str): The key to use for the memcached cache
            hits (List[MatchingDocument]): The list of MatchingDocuments to send to GPT
            num_results (int): The maximum number of results to return to the user
            query (str): The user's query
        """
        cached_result: GPTSearchResults = self.gpt_cache.get(hash_key)
        if cached_result and cached_result.answer and not cached_result.error:
            LOG.debug(
                f"Found a cached GPT chat completion for query '{query}'. Refreshing cache expiration timestamp."
            )
            self.gpt_cache.set(hash_key, cached_result)
            return

        LOG.debug(
            f"Did not find a cached GPT chat completion for query '{query}'. Sending a new request..."
        )
        try:
            result = self.gpt_chat_completion(hits, num_results, query)
        except JeevesException as e:
            e.log_error(hash_key)
            result = GPTSearchResults(answer="", supporting_docs=[], error=e.message)

        self.gpt_cache.set(hash_key, result)

    def init_search(
        self,
        filters: dict[str, Any],
        hash_key: str,
        max_search_depth: int,
        num_results: int,
        query: str,
        query_embedding: list[float],
    ) -> None:
        knn_result = self.knn_search_cached(
            filters, hash_key, max_search_depth, query, query_embedding
        )
        if not knn_result or not knn_result.id_to_score:
            # Error handling and logging already happened inside knn_search_cached()
            return

        # Get the full documents from OpenSearch using these IDs
        hits: list[MatchingDocument] = []
        try:
            hits = self.run_mget(knn_result.id_to_score)
        except JeevesException as e:
            e.log_error(hash_key)

        if not hits:
            # Error handling already happened
            return

        # Ask GPT to summarize as many documents as will fit in the context length limit
        # Error handling happens inside gpt_chat_completion()
        self.gpt_chat_completion_cached(hash_key, hits, num_results, query)

    async def gpt_search(
        self, query: str, max_search_depth: int, num_results: int
    ) -> GPTSearchStartedResponse:
        """
        Given a query string, initialize the GPT Search process:
        [Steps 1 and 2 are run simultaneously:]
        1. Get the text embedding of the query from OpenAI
        2. Get the DSL query and topics with GPT /chat/completions
        [Return the DSL query to the browser here. Start a background thread which does the following:]
        3. Perform a k-NN search against the OpenSearch index using the DSL query and the text embedding;
             save the results to memcached using the hash of the query string as the key
        4. Make a request to GPT /chat/completions using the documents returned by the k-NN search as context;
             save the results to memcached using the hash of the query string as the key

        Params:
            query (str): The query string to search for
            max_search_depth (int): The maximum number of documents to search through in OpenSearch
            num_results (int): The maximum number of documents to return to the user

        Returns:
            GPTSearchStartedResponse: An object containing the OpenSearch filters in Lucene syntax and an error string
              if there is one, along with a request ID to track the request. This response serves as an acknowledgement
              to the user that the search is starting.
        """
        # Create an MD5 hash of the query string to use as the key for the memcached entry
        hash_key = hashlib.md5(query.encode("utf-8")).hexdigest()
        LOG.info(f"Processing request with hash {hash_key}...")

        try:
            embedding_task = create_task(self.get_embedding_cached(hash_key, query))
            dsl_task = create_task(self.get_dsl_query_cached(hash_key, query))
            embedding_response, dsl_response = await gather(
                embedding_task, dsl_task, return_exceptions=True
            )

            if isinstance(embedding_response, Exception):
                raise embedding_response
            if not isinstance(embedding_response, List):
                raise JeevesException(None, "Could not parse the embeddings response.")
            query_embedding: list[float] = embedding_response

            if isinstance(dsl_response, Exception):
                raise dsl_response
            if not isinstance(dsl_response, DSLQueryResponse):
                raise JeevesException(None, "Could not parse the DSL query response.")
            parsed_queries: DSLQueryResponse = dsl_response

        except JeevesException as e:
            e.log_error(hash_key)
            return GPTSearchStartedResponse({}, hash_key, error=e.message)

        if isinstance(embedding_response, List):
            query_embedding = embedding_response
        if isinstance(dsl_response, DSLQueryResponse):
            parsed_queries = dsl_response

        knn_thread = Thread(
            target=self.init_search,
            args=(
                parsed_queries.dsl_query,
                hash_key,
                max_search_depth,
                num_results,
                query,
                query_embedding,
            ),
        )
        knn_thread.start()

        return GPTSearchStartedResponse(parsed_queries.lucene_filters, hash_key)

    def wait_for_knn_results(self, hash_key: str, timeout: int = 45) -> KNNSearchResponse:
        """
        Wait for the k-NN search to finish and return the results.

        Params:
            hash_key (str): The request ID of the browser's initial request to the server
            timeout (int): The number of seconds to wait for the results before timing out
        """
        knn_result: Optional[KNNSearchResult] = None
        start_time = datetime.now()
        # While the timeout is not reached, check the cache for the results, sleep for 1 second, and try again
        while (datetime.now() - start_time).seconds < timeout:
            knn_result = self.knn_cache.get(hash_key)
            if knn_result:
                break
            time.sleep(1)

        if not knn_result:
            error = JeevesException(None, "Timed out waiting for the k-NN search to finish.")
            error.log_error(hash_key)
            return KNNSearchResponse([], error.message)

        if not knn_result.id_to_score:
            # This is a valid outcome, so we log that there were no results and return an empty list
            LOG.info(f"No results found for the k-NN search for hash key {hash_key}.")
            return KNNSearchResponse([], None)

        # Get the full documents from OpenSearch using these IDs
        try:
            hits = self.run_mget(knn_result.id_to_score)
        except JeevesException as e:
            e.log_error(hash_key)
            return KNNSearchResponse([], e.message)

        if not hits:
            return KNNSearchResponse([], "Did not find any matches to the cached IDs.")

        return KNNSearchResponse([d.doc for d in hits], None)

    def wait_for_gpt_answer(self, hash_key: str, timeout: int = 45) -> GPTSearchResults:
        """
        Wait for the OpenAI /chat/completions results to be set to the cache and return the results.

        Params:
            hash_key (str): The request ID of the browser's initial request to the server
            timeout (int): The number of seconds to wait for the results before timing out
        """
        gpt_result: Optional[GPTSearchResults] = None
        start_time = datetime.now()
        # While the timeout is not reached, check the cache for the results, sleep for 1 second, and try again
        while (datetime.now() - start_time).seconds < timeout:
            gpt_result = self.gpt_cache.get(hash_key)
            if gpt_result:
                break
            time.sleep(1)

        if not gpt_result:
            error = JeevesException(None, "Timed out waiting for the k-NN search to finish.")
            error.log_error(hash_key)
            return GPTSearchResults("", [], error.message)

        if not gpt_result.answer:
            error = JeevesException(None, "GPT did not provide an answer to the request.")
            error.log_error(hash_key)
            return GPTSearchResults("", [], error.message)

        return gpt_result
