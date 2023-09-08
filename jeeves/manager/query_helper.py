"""
A manager for handling natural language tasks related to querying OpenSearch
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from duolingo_base.util import registry

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.sentiment_classifier_dal import SentimentClassifierDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import get_date_prefix_for_system_prompt
from jeeves.util.polarity_calculator import calc_cosine_similarity

RESP_LUCENE_FILTERS = "lucene_filters"
RESP_QUERY = "query"
RESP_TARGET_TOPIC = "topic"

SYSTEM_PROMPT = f"""
You are a tool that helps employees of the company Duolingo to find documents in an OpenSearch database by taking the
user's natural language query and returning a JSON object representing the OpenSearch Query DSL syntax that can be used
to retrieve the documents that the user wants, as well as the "target topic" which can be used in whatever way the
application needs.

The index contains a collection of documents with the following properties which can be queried:
- app_version (keyword): The version of the Duolingo app being used when the document was created, ex. "6.216.0.3"
- data_source (keyword): The data source. The only values for this are: {{AppFigures, JIRA, Reddit, Zendesk}}.
- date_time (date): The datetime that the document was written. Represented as an ISO datetime string in UTC time.
- platform (keyword): The only possible values are "Android", "Web", or "iOS" (or an empty string)
- username (keyword): The username of the user who reported the ticket
- user_id (text or keyword multifield): The ID of the user who reported the ticket (a number with 1-10 digits)

If the user requests documents from the data source "twitter", search instead for documents with
{{"data_source": "Zendesk"}} and {{"via.channel": "twitter"}} (with "via.channel" syntax; do NOT return a nested query)

If the user specifically requests documents from AppFigures, Reddit, or Twitter, the only valid filters are
  "data_source" and "date_time". The other filters are not applicable to these data sources. For those requests,
  the other filters must be left blank.

Given the user's request, return a JSON object with the target topic that the document is interested in in the field
"{RESP_TARGET_TOPIC}", and in the field "{RESP_QUERY}" put a JSON object that can be directly used as the "{RESP_QUERY}"
in an OpenSearch Query in DSL syntax to retrieve relevant documents using ONLY the properties of the documents above.
Do not add any free-text search queries. Only extract parts of the user's query that can be converted to filters
for the parameters listed. Inside the field "{RESP_LUCENE_FILTERS}", put a JSON object with equivalent representations
of the filters in "{RESP_QUERY}" as though key-value pairs for a Lucene search. If there is no topic in the user's
query, return a null value in "{RESP_TARGET_TOPIC}".

If there are no filters found in the user's query and they explicitly request results from the entire history of the
OpenSearch index (ex. "from all time"), return the following in "{RESP_QUERY}": {{ "match_all": {{}} }}, and in
"{RESP_LUCENE_FILTERS}" return an empty object. Otherwise, if there is no date range specified in their request,
default to a date range of the past month. Always round the end date to the end of the current day in UTC.

For instance, if the user's query is: "What crashes have been found on iOS for the app version 6.213.0.4 in May 2023?"
you should return:

{{
  "{RESP_LUCENE_FILTERS}": {{
    "platform": "iOS",
    "app_version": "6.213.0.4",
    "date_time": "[2023-05-01T00:00:00 TO 2023-05-31T23:59:59]"
  }},
  "{RESP_QUERY}": {{
    "bool": {{
      "must": [
        {{
          "match": {{
            "platform": "iOS"
          }}
        }},
        {{
          "match": {{
            "app_version": "6.213.0.4"
          }}
        }},
        {{
          "range": {{
            "date_time": {{
              "gte": "2023-05-01T00:00:00",
              "lte": "2023-05-31T23:59:59"
            }}
          }}
        }}
      ]
    }}
  }},
  "{RESP_TARGET_TOPIC}": "crashes"
}}

If the user's query is: "What are people saying about Leaderboards on Twitter?" and if the current date were
'2023-09-03T01:23:45Z', you should return:

{{
  "{RESP_LUCENE_FILTERS}": {{
    "data_source": "Zendesk",
    "via.channel": "twitter",
    "date_time": "[2023-08-03T00:00:00 TO 2023-09-03T23:59:59]"
  }},
  "{RESP_QUERY}": {{
    "bool": {{
      "must": [
        {{
          "match": {{
            "data_source": "Zendesk"
          }}
        }},
        {{
          "match": {{
            "via.channel": "twitter"
          }}
        }},
        {{
          "range": {{
            "date_time": {{
              "gte": "2023-08-03T00:00:00",
              "lte": "2023-09-03T23:59:59"
            }}
          }}
        }}
      ]
    }}
  }},
  "{RESP_TARGET_TOPIC}": "leaderboards"
}}
"""

TARGET_TOPIC_THRESHOLD = 0.79


@dataclass
class DSLQueryResponse:
    dsl_query: Dict[str, Any]
    lucene_filters: Dict[str, str]
    target_topic: Optional[str]


def get_system_prompt() -> str:
    return get_date_prefix_for_system_prompt() + SYSTEM_PROMPT


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
    opensearch_dal=registry.reference(OpenSearchDAL),
    sentiment_classifier_dal=registry.reference(SentimentClassifierDAL),
)
class QueryHelper:
    def __init__(
        self,
        ai_completions_dal: AICompletionsDAL,
        opensearch_dal: OpenSearchDAL,
        sentiment_classifier_dal: SentimentClassifierDAL,
    ):
        self.ai_completions_dal = ai_completions_dal
        self.opensearch_dal = opensearch_dal
        self.sentiment_classifier_dal = sentiment_classifier_dal

    def get_dsl_query_and_topics(
        self, query: str, raise_exceptions: bool = False
    ) -> DSLQueryResponse:
        """
        Given a user request, return a DSL "query" that can be used to retrieve relevant documents,
        along with a list of "topics" extracted from the request.
        """
        sys_prompt = get_system_prompt()
        gpt_response: str = self.ai_completions_dal.ask(
            sys_prompt, query, raise_exceptions=raise_exceptions
        )
        gpt_response_json = json.loads(gpt_response)

        # Account for a couple inconsistencies in the GPT response
        dsl_query = gpt_response_json[RESP_QUERY]
        if dsl_query is None:
            dsl_query = {"match_all": {}}
        elif "query" in dsl_query:
            dsl_query = dsl_query["query"]

        return DSLQueryResponse(
            dsl_query,
            lucene_filters=gpt_response_json[RESP_LUCENE_FILTERS],
            target_topic=gpt_response_json[RESP_TARGET_TOPIC],
        )

    def filter_documents_using_topic(
        self, documents_list: List[JeevesDocument], target_topic: str
    ) -> List[JeevesDocument]:
        """
        Use cosine similarity to determine which documents match the target topic
        """
        target_embedding = self.ai_completions_dal.request_embedding(target_topic)
        docs_on_topic = []
        for document in documents_list:
            # Skip a document if it doesn't have an embedding
            # (Could also consider creating an embedding on the fly, but this could get expensive)
            if GPT_EMBEDDING_MODEL not in document.embeddings.keys():
                continue
            doc_embedding = document.embeddings[GPT_EMBEDDING_MODEL]
            similarity = calc_cosine_similarity(target_embedding, doc_embedding)
            if similarity > TARGET_TOPIC_THRESHOLD:
                docs_on_topic.append(document)
        return docs_on_topic
