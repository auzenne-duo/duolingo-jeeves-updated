"""
A manager for the Jeeves GPT Search functionality.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

import tiktoken

from jeeves import registry as app_registry
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.manager.query_helper import DSLQueryResponse, QueryHelper
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.matching_document import MatchingDocument
from jeeves.model.search_result import DocumentContent, SearchResults

LOG = logging.getLogger(__name__)

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
    def from_dict(cls, d: Dict[str, str]) -> GPTResponseDocument:
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
    matches: List[GPTResponseDocument]

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
    doc: Dict[str, Any]

    @classmethod
    def from_jeeves_document(
        cls, doc: JeevesDocument, match: GPTResponseDocument, score: float
    ) -> GPTSearchResult:

        translated_text = None
        if match.translation_body_bolded is not None:
            translated_text = LanguageContent(
                body=match.translation_body_bolded,
                body_orig=None,
                language=match.translation_language,
                title=match.translation_title,
            )
        return cls(
            bolded_body=match.doc_body_bolded,
            score=score,
            translated_text=translated_text,
            doc=doc.serialize_to_json(doc),
        )


@dataclass
class GPTSearchResults(SearchResults):
    """
    The object we will return to the user from /api/3/gpt_search
    """

    answer: str


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


class GPTSearchManager:
    def __init__(self) -> None:
        LOG.debug("Initializing GPTSearchManager...")
        self.opensearch = app_registry(OpenSearchDAL)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        return

    def token_len(self, text: str):
        return len(self.tokenizer.encode(text))

    def get_max_docs_under_content_length_limit(
        self, docs: Dict[str, MatchingDocument], max_response_tokens: int, prompts: List[str]
    ) -> List[str]:
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
        for _id, doc in docs.items():
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

    def gpt_search(self, query: str, num_results: int, max_search_depth: int) -> GPTSearchResults:
        # TODO: Should we ask GPT to give us a slimmed-down version of the query without the filters?
        #   Does this help with the k-NN search accuracy?
        query_embedding = app_registry(AICompletionsDAL).request_embedding(query)

        dsl_response: DSLQueryResponse = app_registry(QueryHelper).get_dsl_query_and_topics(query)
        lucene_query: List[str] = dsl_response.lucene_query
        LOG.debug(f"DSL query: {dsl_response.dsl_query}")
        LOG.debug(f"Lucene query: {lucene_query}")
        LOG.debug(f"Topic: {dsl_response.target_topic}")

        # Even though we search through max_search_depth items to find the approximate k-NN results, fewer may be
        #   returned because of the post_filter steps. Request 1000 results, then we'll get back fewer than 1000,
        #   and ultimately we'll only send to GPT-4 the top matches that fit in the token limit.
        num_knn_results = min(1000, max_search_depth)
        hits = self.opensearch.perform_knn_search(
            dsl_response.dsl_query,
            query_embedding,
            max_search_depth=max_search_depth,
            num_results=num_knn_results,
            threshold=0.7,
        )
        # TODO: If there are no hits BUT we have results when we remove the filters, give an error message
        #   with an button to reset the filters
        if not hits:
            return GPTSearchResults(
                answer="No Jeeves documents found that match the query.",
                lucene_query=[],
                query=query,
                results=[],
            )

        prompts = [SYSTEM_PROMPT, REQ_DOCUMENTS, REQ_QUESTION, query]
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
        LOG.debug(f"SYSTEM PROMPT: {SYSTEM_PROMPT.encode('ascii', errors='replace')}")
        LOG.debug(f"USER PROMPT: {user_prompt.encode('ascii', errors='replace')}")

        gpt_resp = app_registry(AICompletionsDAL).ask(
            SYSTEM_PROMPT, user_prompt, max_tokens=MAX_RESPONSE_TOKENS
        )
        # TODO: Catch exceptions and give an appropriate response to the user
        if not gpt_resp:
            return GPTSearchResults(
                answer="Could not answer the question.", lucene_query=[], query=query, results=[]
            )

        LOG.debug(f"GPT response: {gpt_resp.encode('ascii', errors='replace')}")
        answer: str
        gpt_matches: List[GPTResponseDocument]
        try:
            # Parse the response from GPT as a GPTResponse object
            gpt_response = GPTResponse.from_json(gpt_resp)
            answer = gpt_response.answer
            gpt_matches = gpt_response.matches
        except JSONDecodeError as decode_error:
            LOG.error("Could not deserialize response from GPT", exc_info=decode_error)
            return GPTSearchResults(
                answer="Could not parse the response from GPT.",
                lucene_query=[],
                query=query,
                results=[],
            )

        if not answer:
            LOG.warning(f"Could not find field '{RESP_ANSWER}' in response {gpt_resp}")

        if not gpt_matches:
            LOG.warning(
                f"Could not find field '{RESP_MATCHES}' in response {gpt_resp}, or else it is empty"
            )

        if len(gpt_matches) > num_results:
            LOG.warning(
                f"GPT returned {len(gpt_matches)} documents in its response; "
                f"truncating to the requested {num_results}"
            )
            gpt_matches = gpt_matches[:num_results]

        print(f"Number of tokens in answer: {self.token_len(answer)}", flush=True)

        supporting_docs: List[GPTSearchResult] = []
        for gpt_match in gpt_matches:
            _id = gpt_match.id
            _id = _id.strip()
            if _id not in hits:
                LOG.warning(f"GPT selected the document {_id} which does not exist in our dict")
                continue

            hit = hits[_id]
            result = GPTSearchResult.from_jeeves_document(hit.doc, gpt_match, hit.score)
            supporting_docs.append(result)

        results = GPTSearchResults(
            answer=answer, lucene_query=lucene_query, query=query, results=supporting_docs
        )
        response_str = json.dumps(results.to_dict(), indent=2, default=str).encode(
            "ascii", errors="replace"
        )
        LOG.debug(f"Sending response to user: {response_str}")
        return results
