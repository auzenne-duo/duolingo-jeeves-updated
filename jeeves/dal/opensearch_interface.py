import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Union, cast

import numpy as np
import rollbar
from duolingo_base.config import Config
from duolingo_nlp.annotations import AnnotationKind, Language, Text
from duolingo_nlp.annotators.text.nlp_client import TextNLPBackendClient
from duolingo_nlp.models.annotations.text.word import WordProperty
from opensearch_dsl import A, Mapping, Q, Search
from opensearch_dsl.query import MoreLikeThis
from opensearch_dsl.response import Response
from opensearchpy import OpenSearch
from opensearchpy.exceptions import RequestError
from opensearchpy.helpers import bulk

from jeeves import registry as app_registry
from jeeves.config.config import (
    GPT_EMBEDDING_MODEL,
    HISTORY_WINDOW_SIZE,
    MIN_SAMPLES_THRESHOLD,
    SENTENCE_TRANSFORMER_MODEL,
)
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.matching_document import MatchingDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory as STRC
from jeeves.model.spike_categories import SpikeCategory
from jeeves.util.date_util import date_to_str, datetime_to_str, parse_external_datetime
from jeeves.util.error_util import SearchUnsuccessfulException
from jeeves.util.shakira import JIRA_VIA_JEEVES_LABEL
from jeeves.util.sleep_check import sleep_check

_config = Config.load_config()

# Default limit of 1000 must be increased to provide enough space for ~500 experiment conditions
_MAX_FIELDS_LIMIT = 3000
# If we ever change the duplicate detection model, make sure this value is
# updated appropriately
_SENTENCE_TRANSFORMERS_VECTOR_SIZE = 768
_GPT_EMBEDDING_VECTOR_SIZE = 1536


class OpenSearchDAL:
    def __init__(self) -> None:
        host = _config.get_nested(["opensearch", "host"])
        port = int(_config.get_nested(["opensearch", "port"]))

        self._es = OpenSearch([host], port=port)

        self._indexname = (
            f"jeeves_tickets_v_{_config.get_nested(['opensearch', 'data_version_identifier'])}"
        )
        self.language = Language.ENGLISH
        self.annotator = TextNLPBackendClient.load(
            language=self.language,
            annotation_kinds=(AnnotationKind.SYNTACTIC_TOKEN_LEMMAS,),
        )

    def initialize_index(self) -> None:
        """
        Initialize OpenSearch index
        Should only be called once, during server startup
        """
        if not self._es.indices.exists(index=self._indexname):

            print(f"Creating index {self._indexname}...", flush=True)

            # We need to explicitly set these types because OpenSearch will
            # otherwise misinterpret them. In the future we may want to set more
            # types explicitly like this.
            m = Mapping()
            m.field("data_source", "keyword")
            m.field("document_id", "keyword")
            m.field("jeeves_uid", "keyword")
            m.field("shake_to_report_category", "keyword")
            m.field("app_version", "keyword")
            m.field("course", "keyword")
            m.field("os_version", "keyword")
            m.field("platform", "keyword")
            m.field("screen_size", "keyword")
            m.field("screen_content", "keyword")
            m.field("ui_language", "keyword")
            m.field("username", "keyword")

            # We now need to pivot into a different structure to add the
            # mapping for the duplicate detector's embedding vector. This format
            # is more annoying to work with so it is only being used here
            # because I couldn't get it to work in the above format.
            mapping_dict = m.to_dict()
            mapping_dict["properties"][f"embeddings.{SENTENCE_TRANSFORMER_MODEL}"] = {
                "type": "knn_vector",
                "dimension": _SENTENCE_TRANSFORMERS_VECTOR_SIZE,
            }
            mapping_dict["properties"][f"embeddings.{GPT_EMBEDDING_MODEL}"] = {
                "type": "knn_vector",
                "dimension": _GPT_EMBEDDING_VECTOR_SIZE,
            }

            settings_dict = {
                "index": {
                    "knn": True,
                    "knn.space_type": "cosinesimil",
                    "mapping.total_fields.limit": _MAX_FIELDS_LIMIT,
                }
            }

            index_creation_structure = {
                "mappings": mapping_dict,
                "settings": settings_dict,
            }

            self._es.indices.create(index=self._indexname, body=index_creation_structure)
            message = f"Created index {self._indexname} with new mappings"
            print(message, flush=True)
            rollbar.report_message(message, "info")

    def _execute_search_for_documents(self, s: Search) -> List[JeevesDocument]:
        """
        Given an OpenSearch_DSL Search object, performs the necessary logic
        to execute that search and convert the results into a list of document
        objects.

        Parameters:
            s: An OpenSearch_DSL Search object to execute.

        Returns:
            The results of the input search as a list of JeevesDocument objects.
        """

        response = s.execute()
        return self._parse_response_to_docs(response)

    def _parse_response_to_docs(self, response: Response) -> List[JeevesDocument]:
        """
        Given an OpenSearch_DSL Response object, performs the necessary logic
        to convert the results into a list of document
        objects.

        Parameters:
            response (dict): An OpenSearch_DSL Response object

        Returns:
            The response hits as a list of JeevesDocument objects.
        """
        if not response.success():
            raise Exception(
                f"""
            Attempt to get a page of documents failed.
            Here's what the call to execute() returned:
            {response.to_dict()}
            """
            )

        result_docs = [
            IDManagerMap.get_manager_for_identifier(hit["_source"]["data_source"])
            .get_managed_document_type()
            .deserialize_from_internal_json(hit["_source"])
            for hit in response.to_dict()["hits"]["hits"]
        ]

        return result_docs

    def execute_arbitrary_query(self, jsn: JSON) -> List[JeevesDocument]:
        """
        Given JSON representing an arbitrary OpenSearch query, execute that
        query and return the results.

        Parameters:
            jsn: JSON object representing the query to execute

        Returns:
            A list of documents that match the query criteria
        """
        s = Search(using=self._es, index=self._indexname)
        s = s.update_from_dict(jsn)
        return self._execute_search_for_documents(s)

    def _handle_es_request_errors(self, e: RequestError) -> JSON:
        """
        Interprets and gives response values for RequestErrors returned by
        OpenSearch. Currently this is only expected to happen for malformed
        query_string inputs, but we can extend this function in the future as
        necessary.

        For reference, request errors appear to be of the form:
        RequestError(<status code>, <error cause>, <error details>)

        Returns:
            A JSON object containing information about the error. This object
            should be returned in place of the normal return value of the
            calling function, since if a RequestError occured, obtaining a
            proper return value is likely not possible. This also lets us
            communicate with the user about the nature of the error.
        """

        if e.args[1] == "search_phase_execution_exception":
            # Splitting this conditional from the outer one is cleaner in case
            # we want to add more cases later
            if (
                e.args[2]
                .get("error", {})
                .get("root_cause", [{}])[0]
                .get("reason", "")
                .startswith("Failed to parse")
            ):
                return {
                    "ERROR": "Your query appears to be malformed. Please check your query and try resubmitting."
                }

        return {
            "ERROR": "OpenSearch encountered an unknown error. Please report this behavior to the repo owner."
        }

    def get_recent_paginated_tickets(
        self,
        lang: str,
        word: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        beta_filter_category: Optional[str] = False,
        jeeves_id: Optional[str] = None,
        limit: int = 10,
        sort_id: int = None,
        prev_sort_id: int = None,
        offset: int = 0,
        spike_category: Optional[SpikeCategory] = SpikeCategory.ALL_SPIKES,
        use_lemmas: bool = False,
        filter_jiras_from_jeeves: bool = False,
    ) -> Dict[str, Union[int, List[JeevesDocument]]]:
        """
        Returns stored user tickets from OpenSearch in a paginated manner.
        To obtain multiple pages of tickets, call this function multiple times.
        If an empty string is passed to the `word` parameter, replace the normal
        `match against this word` query with a `match all` query.

        Parameters:
            lang (str): Language to search for tickets in.
            word (str): Query to search against in OpenSearch. An empty string
                        will match to all documents. Uses regular expressions.
            start_time (datetime): The beginning of a date range to search for tickets in.
                                   Results will not have timestamps before this value.
                                   Optional value.
            end_time (datetime):  The end of a date range to search for tickets in,
                                  Results will not have timestamps after this value.
                                  Optional value.
            beta_filter_category (str): How we should filter results to
                                        have specific values related to release
                                        candidates, if at all. Optional value.
            jeeves_id (str): Unique ID of a specific document. A unique ID is
                             assigned to every document at index time, in
                             bulk_index_tickets. Providing this value overrides
                             all other arguments because no additional filtering
                             should be performed if the user already knows which
                             document they want. Optional value.
            limit (int): Number of docs to return
            sort_id (int): ID number of doc at the start of the range
            prev_sort_id (int): ID number of doc at the start of the range, but now the range extends backwards
                                Only one of sort_id or prev_sort_id should be present
            offset (int): if neither sort_id nor prev_sort_id are provided, query returns the docs at positions offset
                         to offset+limit. Note this only works up to 10,000.
            spike_category: The spike category whose documents we should search within. Optional value.
            use_lemmas (bool): Flag determining if lemmatized terms should be used over searching for word in body_text.
            filter_jiras_from_jeeves (bool): If true, Jira issues that were posted from Jeeves will be excluded from results.

        Returns:
            A dictionary containing the following:
            - data (list[hits]): A list of support ticket objects, representing the requested
              page of results. Results are sorted, larger timestamps first.
            - total_records (int): An integer representing the total number of hits
              for the search criteria
            - sort_id (str): sort_id of the last doc in the batch
            - prev_sort_id (str): sort_id of the first doc in the batch
        """

        s = Search(using=self._es, index=self._indexname)

        if jeeves_id:
            s = s.filter("term", jeeves_uid=jeeves_id)

        else:
            timestamp_dict = {"time_zone": "America/New_York"}
            if start_time:
                timestamp_dict.update({"gte": start_time.date()})
            if end_time:
                timestamp_dict.update({"lte": end_time.date()})

            s = (
                s.filter("range", date_time=timestamp_dict)
                .filter("term", language=lang)
                .sort("-date_time")
            )

            if word:
                if lang == "en" and use_lemmas:
                    s = s.filter("term", lemmatized_terms=word)
                else:
                    s = s.query("query_string", default_field="body_text", query=word, lenient=True)
            else:
                s = s.query("match_all")

            if beta_filter_category:
                s = s.filter("term", shake_to_report_category=beta_filter_category)
            s = SpikeCategory.get_opensearch_transformer_for_category(spike_category)(s)

            if filter_jiras_from_jeeves:
                s = s.query("bool", must_not=[Q({"match": {"labels": JIRA_VIA_JEEVES_LABEL}})])

            s = s.extra(size=limit)
            if sort_id:
                s = s.extra(search_after=[sort_id])
            elif prev_sort_id:
                # reverse the sort to get the tickets before the previous sort id
                s = s.sort("date_time").extra(search_after=[prev_sort_id])
            else:
                s = s[offset : offset + limit]

        try:
            total_records = s.count()
            response = s.execute()
            if prev_sort_id:
                # correct the order of the tickets caused by the reverse sort
                response.hits.hits.reverse()

            retval = {
                "total_records": total_records,
                "data": self._parse_response_to_docs(response),
            }
            if response.to_dict()["hits"]["hits"]:
                retval["sort_id"] = str(
                    response.to_dict()["hits"]["hits"][-1].get("sort", [None])[0]
                )
                retval["prev_sort_id"] = str(
                    response.to_dict()["hits"]["hits"][0].get("sort", [None])[0]
                )
            return retval

        except RequestError as e:
            return self._handle_es_request_errors(e)

    def aggregate_time_series(
        self,
        lang: str,
        spike_category: SpikeCategory,
        word: str,
        start_date: datetime.date = None,
        use_lemmas: bool = True,
        beta_filter_category: Optional[STRC] = None,
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Calculates per-day counts of how many tickets contain a particular word. For English, we use lemmatized terms

        Parameters:
            lang: Language to search tickets in.
            spike_category: The spike category whose documents we should search within.
            word: Term to search against. Supports regular expressions.
            start_date (datetime): The beginning of a date range to search for tickets in.
                                   Results will not have timestamps before this value.
                                   Optional value.
            use_lemmas (bool): Flag determining if lemmatized terms should be used over searching for word in body_text
            beta_filter_category (str): How we should filter results to
                                        have specific values related to release
                                        candidates, if at all. Optional value.

        Returns:
            A list of dicts, where each dict contains a string representing a
            date and an int representing a count of how many times the input
            term appeared on that date.
        """

        s = (
            Search(using=self._es, index=self._indexname)
            .filter("term", language=lang)
            .query("bool", must_not=[Q({"match": {"labels": JIRA_VIA_JEEVES_LABEL}})])
        )

        if lang == "en" and use_lemmas:
            s = s.filter("term", lemmatized_terms=word)
        else:
            s = s.query("query_string", default_field="body_text", query=word, lenient=True)

        if start_date:
            s = s.filter("range", date_time={"gte": start_date})

        if beta_filter_category:
            s = s.filter("term", shake_to_report_category=beta_filter_category.value)
        s = SpikeCategory.get_opensearch_transformer_for_category(spike_category)(s)

        # OpenSearch just so happens to have functionality for making a date
        # histogram of data, that is, a list of counts of instances of something
        # bucketed by time intervals.
        s.aggs.bucket(
            "replacementtimeseries",
            "date_histogram",
            field="date_time",
            calendar_interval="day",
            time_zone="America/New_York",
            format="yyyy-MM-dd'T'HH:mm:ssxx",
        )

        try:
            response = s.execute()
            if not response.success():
                raise SearchUnsuccessfulException(
                    response, search_description="aggregate time series"
                )
            response_buckets = response.aggregations.replacementtimeseries.buckets
            return response_buckets

        except RequestError as e:
            return self._handle_es_request_errors(e)

    def filter_text(self, text: str) -> str:
        """
        Returns filtered text

        Parameters:
            text (str): body of text
        """
        stop_punctuation = '!\n\r"‘’“”#$%&()*+,.…:;<=>?@[/\\]^`{|}~'
        join_punctuation = "-_'‘’"
        email_pattern = "[\w0-9-._]*@[\w0-9-._]+"  # also handles handles like @duolingo
        emote_pattern = ":[\w_]+:"
        url_pattern = "https?://[\w./0-9-?=_]+"
        filter_pattern = re.compile(
            f"{email_pattern}|{emote_pattern}|{url_pattern}|["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U0001F1F2-\U0001F1F4"  # Macau flag
            "\U0001F1E6-\U0001F1FF"  # flags
            "\U0001F600-\U0001F64F"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001f926-\U0001f937"
            "\U0001F1F2"
            "\U0001F1F4"
            "\U0001F620"
            "\u200d"
            "\u2640-\u2642"
            "]+",
            flags=re.UNICODE,
        )

        no_emoji_text = filter_pattern.sub(r"", text)

        clean_text = no_emoji_text.translate(
            str.maketrans(stop_punctuation, " " * len(stop_punctuation), join_punctuation)
        )

        # remove extra white spaces
        return re.sub(" +", " ", clean_text).strip()

    def lemmatize_texts(self, raw_texts: List[str]) -> List[List[str]]:
        """
        Tokenizes and annotates texts and returns a list of list of unique lemmas per text

        Parameters:
            List of texts to lemmatize

        Returns:
            List of list of unique lemmas per text
        """
        texts = Text.make_batch(
            languages=self.language,
            raw_texts=[self.filter_text(raw_text) for raw_text in raw_texts],
        )
        anno_texts = texts.annotate_with(self.annotator)

        lemmatized_texts = []
        for anno_text in anno_texts:
            lemmatized_texts.append(
                self._filter_terms(
                    {
                        lemma.lower()
                        for lemma in anno_text.syntactic_tokens_property(WordProperty.LEMMA)
                    }
                )
            )
        return lemmatized_texts

    def lemmatize_tickets(self, tickets: List[JeevesDocument]) -> None:
        """
        Populates each tickets' lemmatized_terms field by lemmatizing the body text

        Parameters:
            tickets: Object representation of tickets.
        """
        tickets_to_lemmatize = [ticket for ticket in tickets if ticket.language == "en"]
        lemmatized_terms = self.lemmatize_texts(
            [ticket.body_text for ticket in tickets_to_lemmatize]
        )

        for ticket, lemmas in zip(tickets_to_lemmatize, lemmatized_terms):
            ticket.lemmatized_terms = lemmas

    def populate_embedding_vectors(self, tickets: List[JeevesDocument]) -> None:
        """
        Populates each ticket's embedding vector

        Parameters:
            tickets: Object representation of tickets.
        """
        for ticket in tickets:
            # Delay for a bit to avoid rate limiting
            time.sleep(0.1)
            embeddings = {}

            ai_embedding = app_registry(AICompletionsDAL).request_embedding(
                f"Title: {ticket.header_text}\n Description: {ticket.body_text}"
            )

            # TODO (caleb): If the returned embedding is None, we should put the ticket back in the sqs queue
            # and try again later.
            if ai_embedding is not None:
                embeddings[GPT_EMBEDDING_MODEL] = ai_embedding

            if ticket.data_source == JiraDocument.get_data_source_identifier():
                embeddings[SENTENCE_TRANSFORMER_MODEL] = JiraDocument.calculate_embedding(ticket)

            ticket.embeddings = embeddings

    def bulk_index_tickets(self, tickets: List[JeevesDocument]) -> None:
        """
        Store multiple tickets into OpenSearch.

        Parameters:
            tickets: Object representation of tickets to store.
        """
        self.lemmatize_tickets(tickets)
        self.populate_embedding_vectors(tickets)

        bulk_actions = [
            {
                "_index": self._indexname,
                "_source": ticket.serialize_to_json(ticket),
                "_id": ticket.generate_opensearch_internal_id(ticket),
            }
            for ticket in tickets
        ]
        (_, errors) = bulk(self._es, bulk_actions, raise_on_error=False, raise_on_exception=False)
        if errors:
            error_message = (
                f"Encountered {len(errors)} error{'' if len(errors) == 1 else 's'} "
                + f"when bulk indexing tickets: {errors}"
            )
            rollbar.report_exc_info(sys.exc_info())
            raise Exception(error_message)

    def get_most_recent_timestamp(
        self, lang: Optional[str] = None, data_source: Optional[str] = None
    ) -> Optional[float]:
        """
        Acquire submission timestamp of most recent stored ticket.

        Parameters:
            lang (str): Optional, filter ticket search to only this language.
            data_source (str): Optional, filter document search to only check
                               results from this data source

        Returns:
            Most recent UNIX timestamp across all searched tickets, or None if
            there were no tickets in OpenSearch.
        """
        s = Search(using=self._es, index=self._indexname).query("match_all")
        if lang:
            s = s.filter("term", language=lang)
        if data_source:
            s = s.filter("term", data_source=data_source)
        s.aggs.metric("most_recent_timestamp", "max", field="date_time")

        response = s.execute()
        if not response.success():
            print("Attempt to get most recent timestamp failed.", file=sys.stderr)
            print("Here's what the call to execute() returned:", file=sys.stderr)
            print(response.to_dict(), file=sys.stderr)
        agg_result = response.aggregations.most_recent_timestamp
        if not agg_result["value"]:
            return None
        time_float = agg_result["value"] / 1000
        return time_float

    def acquire_ticket_ids_since(self, timestamp: float, lang: str) -> List[str]:
        """
        Queries for all IDs of tickets with timestamps later than a given value.

        Parameters:
            timestamp (float): Cutoff time. Only tickets with timestamps
                               later than this value will be considered.
            lang (str): Filter ticket search to only this language.

        Returns:
            List of ticket IDs of tickets in the given language with timestamps
            greater than the given timestamp.
        """
        date_str = datetime_to_str(datetime.fromtimestamp(timestamp))

        s = (
            Search(using=self._es, index=self._indexname)
            .filter("range", date_time={"gt": date_str})
            .filter("term", language=lang)
        )
        doc_ids = [h.meta.id for h in s.scan()]

        return doc_ids

    def get_num_tickets_by_day(
        self,
        end_date: datetime,
        spike_category: SpikeCategory,
        lang: str,
        start_date: Optional[datetime] = None,
    ) -> List[Dict[str, int]]:
        """
        Calculates the number of tickets by day up to HISTORY_WINDOW_SIZE days in the past

        Parameters:
            end_date (datetime): Retrieves data up until and including end_date
            spike_category: The spike category whose documents we should search within.
            lang (str): Filter ticket search to only this language.

        Returns:
            (dict date (str): count (int)) mapping of date strings to count of documents for that date
        """
        end_date = end_date + timedelta(days=1)
        if start_date:
            start_date_str = datetime_to_str(start_date)
        else:
            range_start = end_date - timedelta(days=HISTORY_WINDOW_SIZE)
            start_date_str = datetime_to_str(range_start)
        end_date_str = datetime_to_str(end_date)

        s = Search(using=self._es, index=self._indexname).filter("term", language=lang)
        s = s.filter("range", date_time={"gte": start_date_str, "lte": end_date_str})
        s = SpikeCategory.get_opensearch_transformer_for_category(spike_category)(s)

        # OpenSearch just so happens to have functionality for making a date
        # histogram of data, that is, a list of counts of instances of something
        # bucketed by time intervals.
        s.aggs.bucket(
            "doc_count_by_day",
            "date_histogram",
            field="date_time",
            calendar_interval="day",
            time_zone="America/New_York",
            format="yyyy-MM-dd",
        )

        try:
            response = s.execute()
            if not response.success():
                raise SearchUnsuccessfulException(
                    response, search_description="aggregate doc count by day"
                )
            response_buckets = response.aggregations.doc_count_by_day.buckets
            return {sample["key_as_string"]: sample["doc_count"] for sample in response_buckets}

        except RequestError as e:
            return self._handle_es_request_errors(e)

    def generate_term_stats(self, start_date: datetime, only_shake_to_report: bool = False):
        """
        Scrolls through all documents of a specific language and counts the number of occurences.
        Then saves the mean (occurences per day) and std for terms that appear at least MIN_SAMPLES_THRESHOLD times
        To conform with the spike_detector algorithm, the mean is only taken over days that have at least 1 occurence.

        Currently only supports English

        Parameters:
            start_date (DateTime): Earliest date after which to sample tickets
            only_shake_to_report (boolean): if true, filters only for Jira tickets or Zendesk beta users

        Returns:
            (dict {str: {"mean": float, "std": float}}) mapping from each word to its mean and std of daily count over the sample window
        """
        date_str = datetime_to_str(start_date)
        query = {
            "size": 1000,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"date_time": {"gt": date_str}}},
                        {"term": {"language": "en"}},
                    ]
                }
            },
        }
        if only_shake_to_report:
            query["query"]["bool"]["filter"].append(
                {"terms": {"shake_to_report_category": [STRC.EXTERNAL.name, STRC.INTERNAL.name]}}
            )

        resp = self._es.search(  # pylint: disable=unexpected-keyword-arg
            index=self._indexname,
            body=query,
            scroll="2s",
        )

        old_scroll_id = resp["_scroll_id"]
        doc_count = 0
        word_to_day_to_count = defaultdict(Counter)
        date_to_doc_count = Counter()

        while len(resp["hits"]["hits"]):
            for doc in resp["hits"]["hits"]:
                if len(doc["_source"]["lemmatized_terms"]) == 0:
                    continue

                doc_count += 1
                terms = doc["_source"]["lemmatized_terms"]

                date_str = doc["_source"]["date_time"]
                date = parse_external_datetime(date_str)
                date_key = date_to_str(date)
                date_to_doc_count[date_key] += 1

                for term in terms:
                    word_to_day_to_count[term][date_key] += 1

                if doc_count % 5000 == 0:
                    print("doc count", doc_count)

            resp = self._es.scroll(  # pylint: disable=unexpected-keyword-arg
                scroll_id=old_scroll_id, scroll="2s"
            )
            old_scroll_id = resp["_scroll_id"]

        stats = {}

        num_days = (datetime.today() - start_date).days + 1
        for word, day_to_count in word_to_day_to_count.items():
            samples = [count for _, count in day_to_count.items()]
            if len(samples) < MIN_SAMPLES_THRESHOLD:
                continue
            # add zeros for all the days missing data
            samples = samples + [0] * (num_days - len(samples))
            mean = np.mean(samples)
            std = np.std(samples)
            stats[word] = {"mean": mean, "std": std}

        return {
            "avg_docs_per_day": np.mean(list(date_to_doc_count.values())),
            "words": stats,
        }

    def scroll_arbitrary_query(self, jsn: JSON) -> Generator[JeevesDocument, None, None]:
        """
        Given JSON representing an arbitrary OpenSearch query, executes a scroll for that
        query and yields the results.

        Parameters:
            jsn: JSON object representing the query to execute

        Returns:
            A generator of documents that match the query criteria
        """
        resp = self._es.search(  # pylint: disable=unexpected-keyword-arg
            index=self._indexname,
            body=jsn,
            scroll="2s",
        )

        old_scroll_id = resp["_scroll_id"]

        while len(resp["hits"]["hits"]):
            yield from resp["hits"]["hits"]
            resp = self._es.scroll(  # pylint: disable=unexpected-keyword-arg
                scroll_id=old_scroll_id, scroll="2s"
            )
            old_scroll_id = resp["_scroll_id"]

    def generate_sentiment_docs_from_filters(self, filters: Dict[str, str]) -> List[JeevesDocument]:
        """
        Takes in a dictionary of filters from /query_params and uses them to query the OpenSearch database
        and returns a list of Jeeves documents.
        Scroll is used since these queries may exceed the 10,000 document maximum.
        """
        twitter_only = False
        if "data_source" in filters.keys() and filters["data_source"].lower() == "twitter":
            filters["data_source"] = "Zendesk"
            twitter_only = True
        fields_list = [f'{{"term": {{"{"language"}": "{"en"}"}}}}']
        for filter_name, filter_value in filters.items():
            if filter_name == "data_source" and filter_value.lower() == "all":
                continue
            elif filter_name in ("header_text", "body_text"):
                continue
            elif filter_name == "date_time":
                gte, lte = filter_value.split("[")[1].split("]")[0].split(" TO ")
                fields_list.append(
                    f'{{"range": {{"{filter_name}": {{"gte": "{gte}","lte": "{lte}"}}}}}}'
                )
            else:
                fields_list.append(f'{{"term": {{"{filter_name}": "{filter_value}"}}}}')
        query_string = (
            f'{{"query": {{"bool": {{"must": [{", ".join(fields_list)}]}}}}, "size": {1000}}}'
        )
        print(f"query string: {query_string}")
        query_jsn = json.loads(query_string)
        resp = self._es.search(  # pylint: disable=unexpected-keyword-arg
            index=self._indexname,
            body=query_jsn,
            scroll="10s",
        )

        old_scroll_id = resp["_scroll_id"]
        document_list = []

        while len(resp["hits"]["hits"]):
            for hit in resp["hits"]["hits"]:
                document_list.append(
                    IDManagerMap.get_manager_for_identifier(hit["_source"]["data_source"])
                    .get_managed_document_type()
                    .deserialize_from_internal_json(hit["_source"])
                )
            resp = self._es.scroll(  # pylint: disable=unexpected-keyword-arg
                scroll_id=old_scroll_id, scroll="2s"
            )
            old_scroll_id = resp["_scroll_id"]
        if twitter_only:
            document_list = [
                doc for doc in document_list if doc.via["channel"].lower() == "twitter"
            ]
        return document_list

    def _filter_terms(self, terms):
        """
        Quick and dirty way of filtering out any terms containing
        digits. If a term contains digits its probably either a user
        describing an amount of something or system information
        we've attached. In the former case, the digit is probably not
        a useful spike word, and in the latter case, the output tends
        to get flooded by versions of iOS, which is also not useful.

        Parameters:
            terms ({str}): set of words

        Return:
            terms ({str}): set of filtered words with any term containing digits removed
        """
        return {s for s in terms if not any(i.isdigit() for i in s)}

    def _get_terms_from_slice(self, doc_ids_slice: List[str], lang: str) -> Set[str]:
        """
        Helper function for get_terms_from_docs, below.
        Given a list of document IDs, determine all terms used in the
        corresponding documents, using OpenSearch's mtermvectors functionality

        Parameters:
            doc_ids_slice (List[str]): A list of document IDs for which we want to collect terms.
            lang (str): Two-letter language code that the given documents are expected to have.

        Returns:
            Set of strings, representing terms from the requested documents.
        """
        if lang == "en":
            response = self._es.search(
                index=self._indexname,
                body={"query": {"ids": {"values": doc_ids_slice}}, "size": len(doc_ids_slice)},
            )
            return set(
                [
                    lemma
                    for doc in response["hits"]["hits"]
                    for lemma in doc["_source"]["lemmatized_terms"]
                ]
            )

        request_body_params = {"fields": ["body_text"]}
        if lang == "ja":
            request_body_params["per_field_analyzer"] = {"body_text": "kuromoji"}
        if lang == "zh":
            request_body_params["per_field_analyzer"] = {"body_text": "smartcn"}
        request_body = {"ids": doc_ids_slice, "parameters": request_body_params}

        m_term_vec_out = self._es.mtermvectors(body=request_body, index=self._indexname)
        try:
            terms_lists = [
                list(d["term_vectors"]["body_text"]["terms"]) for d in m_term_vec_out["docs"]
            ]
            # Flatten terms_lists into single list
            terms = set([item for sublist in terms_lists for item in sublist])
            return self._filter_terms(terms)
        except:
            return set()

    def get_terms_from_docs(self, doc_ids: List[str], lang: str) -> Set[str]:
        """
        Given document IDs, determine all terms used in the corresponding documents.

        Parameters:
            doc_ids (List[str]): Document IDs to get terms for.
            lang (str): Specify which OpenSearch analyzer should be used
                        for term tokenization.

        Returns:
            Set of terms from the specified documents. Since this is a Set,
            if a term appears more than once (in the same document or across
            different documents), it is only counted once.
        """

        terms = set()
        # Do the term collection in chunks to avoid massive network packets
        slice_size = 20
        for i in range(0, len(doc_ids), slice_size):
            doc_ids_slice = doc_ids[i : i + slice_size]
            terms_batch = self._get_terms_from_slice(doc_ids_slice, lang)
            terms.update(terms_batch)

        return terms

    def get_min_and_max_document_dates(
        self, lang: str = None, spike_category: SpikeCategory = SpikeCategory.ALL_SPIKES
    ) -> Dict[str, str]:
        """
        Returns the earliest and latest dates among all documents in our data.
        Return value is a dict with keys `min` and `max` and string
        representations of dates as values.
        Optionally can be filtered by spike category and language.

        Parameters:
            lang: Language to search tickets in.
            spike_category: The spike category whose documents we should search within.
        """

        s = Search(using=self._es, index=self._indexname)
        if lang:
            s = s.filter("term", language=lang)
        s = SpikeCategory.get_opensearch_transformer_for_category(spike_category)(s)

        s.aggs.metric("min_date", "min", field="date_time", format="yyyy-MM-dd")
        s.aggs.metric("max_date", "max", field="date_time", format="yyyy-MM-dd")

        response = s.execute()

        min_date = response.aggregations.min_date.value
        max_date = response.aggregations.max_date.value
        # We need to divide the return values by 1000 because they will be in
        # milliseconds instead of seconds.
        return {
            "min": date_to_str(date.fromtimestamp(min_date / 1000)) if min_date else None,
            "max": date_to_str(date.fromtimestamp(max_date / 1000)) if max_date else None,
        }

    def filter_by_arbitrary_keywords(
        self, field_value_pairs: Dict[str, str]
    ) -> Iterator[JeevesDocument]:
        """
        Utility method. Constructs and executes a chain of filter()s to search
        according to arbitrary criteria.

        Parameters:
            field_value_pairs: A dictionary of filter criteria, where keys are
                               field names and values are the values those fields
                               should have.

        Yields:
            JeevesDocument objects that represent records matching the
            specified criteria. Results are unordered due to the use of scan().
        """

        s = Search(using=self._es, index=self._indexname)

        for field, value in field_value_pairs.items():
            filter_params = {"term": {f"{field}": {"value": f"{value}"}}}
            s = s.query("bool", filter=[Q(filter_params)])

        try:
            yield from [
                IDManagerMap.get_manager_for_identifier(hit.data_source)
                .get_managed_document_type()
                .deserialize_from_internal_json(hit.to_dict())
                for hit in s.scan()
            ]
        except RequestError as e:
            return self._handle_es_request_errors(e)

    def count_by_arbitrary_keywords(self, field_value_pairs: Dict[str, str]) -> int:
        """
        Utility method. Constructs and executes a chain of filter()s to search
        according to arbitrary criteria, and return only a count of matches.

        Parameters:
            field_value_pairs: A dictionary of filter criteria, where keys are
                               field names and values are the values those fields
                               should have.

        Returns:
            A count of how many records match the specified criteria.
        """

        s = Search(using=self._es, index=self._indexname)

        for field, value in field_value_pairs.items():
            filter_params = {"term": {f"{field}": {"value": f"{value}"}}}
            s = s.query("bool", filter=[Q(filter_params)])

        return s.count()

    def check_if_duplicate_tweet(self, base_document: JeevesDocument) -> bool:
        """
        This is intended to be used for duplicate tweet detection.

        Parameters:
            base_document: A document for which we would like to find similar documents.
        Returns:
            True if a duplicate is found, False otherwise.
        """

        s = Search(using=self._es, index=self._indexname)
        s = s.filter("term", via__channel="twitter")
        # Restrict results to have the same twitter_id as the base document.
        s = s.filter(
            "term", via__source__from__twitter_id=base_document.via["source"]["from"]["twitter_id"]
        )
        # Restrict results to be from within one day of the base document.
        s = s.filter(
            "range",
            date_time={
                "gte": base_document.date_time - timedelta(minutes=30),
                "lte": base_document.date_time + timedelta(minutes=30),
            },
        )
        # Exclude the base document from the results.
        s = s.exclude("term", document_id=base_document.document_id)

        # Check if any of the hits are similar to the base document.
        hits = s.execute()
        if len(hits) > 0:
            return SequenceMatcher(a=hits[0].body_text, b=base_document.body_text).ratio() > 0.8
        return False

    def run_more_like_this_for_duplicates(
        self,
        base_document: JeevesDocument,
        should_filter_project: bool = False,
        num_desired_results: int = 5,
    ) -> List[JeevesDocument]:
        """
        Executes a More Like This query based on the provided document.
        This is intended to be used for duplicate detection, and so the query
        includes some additional features. It will restrict results to be from the
        same data source as the base document. Results will only be selected from
        records with an issue type of Bug. Results are also filtered manually to
        remove results that are known duplicates of earlier results or known
        duplicates of the base document. Parameters are provided to control
        the number of results, and select if we should further restrict results
        to be from the same JIRA project as the base document.
        If the base document is not a JIRA document, an exeption will be thrown.

        Parameters:
            base_document: A document for which we would like to find similar documents.
            should_filter_project: Optional, if True will restrict results to
                                   only be from the same JIRA project as
                                   base_document.
            num_desired_results: Optional, the number of desired results.


        Returns:
            A list of documents similar to the input document, in the context
            of duplicate issue detection, as determined by MLT.
        """

        if base_document.data_source != "JIRA":
            raise Exception("Duplicate detection is currently only supported for JIRA issues!")

        s = Search(using=self._es, index=self._indexname)
        s = s.filter("term", data_source=base_document.data_source)
        s = s.filter("term", issue_type__keyword="Bug")
        if should_filter_project:
            s = s.filter("term", project__keyword=base_document.project)

        base_doc_id_str = f"{base_document.data_source}_{base_document.document_id}"
        s = s.query(
            MoreLikeThis(
                like=[{"_id": base_doc_id_str}],
                fields=["body_text", "header_text"],
                min_term_freq=0,
                min_doc_freq=0,
            )
        )

        # Now that we have the query set up, we must address the possibly
        # painful operation of filtering the results down to disjoint sets.
        # I'm not aware of a way to do this purely in OpenSearch but if
        # anyone reading this has any ideas please let me know.
        results_page_start = 0
        results_page_size = 10
        running_known_duplicates = set(base_document.linked_duplicate_keys)
        output_list = []
        while True:
            sleep_check()
            s = s[results_page_start : results_page_start + results_page_size]
            results_page = self._execute_search_for_documents(s)

            for result in results_page:
                if result.issue_key not in running_known_duplicates:
                    running_known_duplicates.update(result.linked_duplicate_keys)
                    output_list.append(result)
                    if len(output_list) >= num_desired_results:
                        return output_list

            # If the results page has fewer results than requested I believe
            # that's an indicator we've run out of results to check and we
            # should just return what we have.
            if not results_page:
                return output_list

            results_page_start += results_page_size

    def _ensure_specific_jira_issue(
        self, issue_key: str, force_download: bool = False
    ) -> Optional[JiraDocument]:
        """
        Determines if we have a particular JIRA issue indexed already.

        If we don't have it, an attempt will be made to download and index it.
        If this attempt succeeds or if we have the issue indexed initially,
        return a JeevesDocument representation of the issue. If we can't find
        the requested issue even after a download attempt, return None.

        Parameters:
            issue_key: A string representing the issue key that we wish to
                       ensure the presence of.
            force_download: Optional parameter, defaults to False. When True,
                            forces a re-download of the requested issue, even
                            if we already have a copy in OpenSearch.

        Returns:
            A JeevesDocument object representing the requested document as it
            exists in OpenSearch, or None if we can't find the document.
        """

        # First, determine if we already have the requested document.
        # We could do a call to count_by_arbitrary_keywords here but if we have
        # the document then we'll need to call this anyway.
        filter_results: List[JeevesDocument] = list(
            self.filter_by_arbitrary_keywords({"issue_key.keyword": issue_key})
        )

        base_document: Optional[JiraDocument]

        n_results = len(filter_results)
        # If Python had switch statements I would use one but here we are.
        # I'm explicitly checking the length of the list against 0 to emulate a
        # switch statement structure.
        if force_download or n_results == 0:
            jira_manager = IDManagerMap.get_manager_for_identifier("JIRA")
            base_document = jira_manager.download_specific_issue(issue_key)
            self.bulk_index_tickets([base_document])

        elif n_results == 1:
            base_document = cast(filter_results[0], JiraDocument)

        else:
            # There is no way we should ever get here and if we do something
            # very broken has happened.
            raise Exception(
                f"Filtering to find issue {issue_key} somehow returned {n_results} results. Please investigate."
            )

        return base_document

    def find_potential_jira_duplicates(
        self,
        issue_key: str,
        num_results: int = 5,
        should_filter_project: bool = True,
        max_search_depth: int = 50,
        use_parent_issues: bool = False,
    ) -> List[JeevesDocument]:
        """
        Given a JIRA issue key, ensure we have the corresponding document, and
        identify other documents that represent potential duplicates of the
        provided document.

        If requested document is not found, return an empty list.

        Parameters:
            issue_key (str): The issue key of the JIRA issue we wish to find
                             duplicates of. If this issue is not already in
                             OpenSearch, we attempt to download it.
            num_results (int): Optional, upper bound of how many results we
                               should return
            should_filter_project (bool): Optional. If True, results will be
                                          filtered to only those with the same
                                          project as the requested document.
            max_search_depth (int): Optional. Maximum number of documents to
                                    search through to find num_results results
            use_parent_issues (bool): Optional. If True, then issues that have
                                      parent issues will be substituted with
                                      their parents, and additional filtering
                                      will be performed to ensure that a given
                                      parent does not appear twice in the list
                                      of results. If False, parents will be
                                      excluded, and no additional filtering will
                                      be applied.

        Returns:
            A list of suspected duplicate issues.
        """

        target_doc: JiraDocument = self._ensure_specific_jira_issue(issue_key)

        if not target_doc:
            print(f"Requested issue with key {issue_key} could not be found.")
            return []

        datetime_bound = target_doc.date_time - timedelta(days=30)

        query_body = {
            "size": max_search_depth,
            "query": {
                "bool": {
                    "filter": {
                        "bool": {"must": [{"range": {"date_time": {"gte": datetime_bound}}}]}
                    },
                    "must": [
                        {
                            "knn": {
                                f"embeddings.{SENTENCE_TRANSFORMER_MODEL}": {
                                    "k": max_search_depth,
                                    "vector": target_doc.embeddings[SENTENCE_TRANSFORMER_MODEL],
                                }
                            }
                        }
                    ],
                }
            },
        }

        response = self._es.search(index=self._indexname, body=query_body)
        result_docs = [
            MatchingDocument.from_response_hit(hit)
            for hit in response["hits"]["hits"]
            if hit["_score"] >= 0.8
        ]
        if should_filter_project:
            result_docs = [d.doc for d in result_docs if d.doc.project == target_doc.project]
        # Filter out issue from its own duplicate list
        result_docs = [doc for doc in result_docs if doc.issue_key != target_doc.issue_key]
        # Filter out known duplicates and clones from duplicate list
        known_duplicates = target_doc.linked_duplicate_keys
        for link in target_doc.issue_links:
            if "Clone" in link["type"]["name"]:
                if "inwardIssue" in link:
                    known_duplicates.append(link["inwardIssue"]["key"])
                if "outwardIssue" in link:
                    known_duplicates.append(link["outwardIssue"]["key"])
        non_parent_result = [
            doc
            for doc in result_docs
            if (doc.issue_key not in known_duplicates) and (not doc.is_group_parent(doc))
        ]
        if not use_parent_issues:
            return non_parent_result[:num_results]

        excluded_keys = set()
        result_docs = []
        roving_index = 0
        while len(result_docs) < num_results and roving_index < len(non_parent_result):
            doc = non_parent_result[roving_index]
            roving_index += 1
            if doc.issue_key in excluded_keys:
                continue
            possible_parent = self.get_parent_for_jira(doc)
            if possible_parent:
                doc = possible_parent
            result_docs.append(doc)
            excluded_keys.add(doc.issue_key)
            excluded_keys.update(doc.linked_duplicate_keys)

        return result_docs

    def perform_knn_search(
        self,
        filters: Dict[str, Any],
        query_embedding: List[float],
        max_search_depth: int = 50,
        num_results: int = 5,
        threshold: float = 0.8,
    ) -> Dict[str, MatchingDocument]:
        """
        Perform a k-NN search on the OpenSearch index against an embeddings vector as well
        as a set of Query DSL filters extracted by GPT.

        Parameters:
            filters (Dict[str, Any]): A set of Query DSL filters extracted by GPT
            query_embedding (List[float]): The embeddings vector to search against
            max_search_depth (int): Optional. Maximum number of documents to search through
                                    in order to find num_results hits (default 50).
            num_results (int): Optional. Number of results to display to user (default 5)
            threshold (float): Optional. Minimum score for a result to be returned (default 0.8)
        """

        query_body = {
            "size": max_search_depth,
            "query": {
                "bool": {
                    "filter": filters,
                    "must": [
                        {
                            "knn": {
                                f"embeddings.{GPT_EMBEDDING_MODEL}": {
                                    "k": max_search_depth,
                                    "vector": query_embedding,
                                }
                            }
                        }
                    ],
                }
            },
        }

        response = self._es.search(index=self._indexname, body=query_body)
        result_docs = {
            hit["_source"]["jeeves_uid"]: MatchingDocument.from_response_hit(hit)
            for hit in response["hits"]["hits"]
            if hit["_score"] >= threshold
        }

        # Get first num_results items from result_docs dict
        return {k: result_docs[k] for k in list(result_docs.keys())[:num_results]}

    def get_parent_for_jira(self, target_doc: JeevesDocument) -> Optional[JeevesDocument]:
        """
        Given a document, determines if it is a Jira document that has a parent
        and returns that parent if possible.

        Parameters:
            target_doc: The document whose parent we wish to return.

        Returns:
            A JeevesDocument representing the parent issue of the input if it
            was found, otherwise None.
        """

        # This seems very roundabout but if we ever change the Jira identifier
        # then we'll remember to change this line because it will start erroring
        if (
            target_doc.data_source
            != IDManagerMap.get_manager_for_identifier("JIRA")
            .get_managed_document_type()
            .get_data_source_identifier()
        ):
            return None

        for family_member_key in target_doc.linked_duplicate_keys:
            family_member = self._ensure_specific_jira_issue(family_member_key)
            if family_member.is_group_parent(family_member):
                return family_member
        return None

    def get_bugs_count_per_reporter_email(
        self,
        min_doc_count: int = 1,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resolution_filter: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Counts the number of internal/admin beta bug reports per person.

        Parameters:
            min_doc_count: If a reporter has reported fewer than this number of bugs, they will not
                appear in the results.
            start_time: Limit the search to bugs created (or resolved) after this time. Specified in
                Eastern time.
            end_time: Limit the search to bugs created (or resolved) before this time. Specified in
                Eastern time.
            resolution_filter: Limit the search to bugs with any of the listed resolutions.

        Returns:
            A Dict of reporter_email to document count.
        """
        # TODO use filters aggregation to get all of these stats at once!
        s = (
            Search(using=self._es, index=self._indexname)
            .query("match_all")
            .filter("term", shake_to_report_category="INTERNAL")
            .filter("term", language="en")
        )

        timestamp_dict = {"time_zone": "America/New_York"}
        if start_time:
            timestamp_dict.update({"gte": start_time})
        if end_time:
            timestamp_dict.update({"lt": end_time})
        if resolution_filter:
            s = s.filter("range", resolution_date=timestamp_dict)
        else:
            s = s.filter("range", creation_date=timestamp_dict)

        if resolution_filter:
            # TODO check status of all duplicates as well
            s = s.filter("terms", resolution__keyword=resolution_filter)

        # size=65536 is the default search.max_buckets setting
        s.aggs.bucket(
            "reporters",
            "terms",
            field="reporter_email.keyword",
            size=65536,
            min_doc_count=min_doc_count,
        )
        response = s.execute()

        if not response.success():
            raise SearchUnsuccessfulException(response, search_description="get bugs count")
        reporters = response.aggregations.reporters
        if (
            reporters.doc_count_error_upper_bound > 0
            or reporters.sum_other_doc_count > 0
            or not reporters.buckets
        ):
            raise SearchUnsuccessfulException(
                response, search_description="aggregate bugs count per reporter"
            )
        else:
            return {reporter.key: reporter.doc_count for reporter in reporters.buckets}

    def get_most_recent_resolved_bugs_per_reporter_email(
        self,
        resolution_filter: List[str],
        start_time: Optional[datetime] = None,
        max_doc_count: int = 5,
    ) -> Dict[str, List[JeevesDocument]]:
        """
        Returns the admin/internal beta bugs that were most recently resolved for each reporter.

        Parameters:
            resolution_filter: Limit the search to bugs with any of the listed resolutions.
            start_time: Limit the search to bugs created (or resolved) after this time. Specified in
                Eastern time.
            max_doc_count: The maximum number of bugs to return for each person.

        Returns:
            A Dict of reporter_email to a list of JeevesDocuments.
        """
        s = (
            Search(using=self._es, index=self._indexname)
            .query("match_all")
            .filter("term", shake_to_report_category="INTERNAL")
            .filter("term", language="en")
            .filter("terms", resolution__keyword=resolution_filter)
        )

        if start_time:
            timestamp_dict = {"time_zone": "America/New_York", "gte": start_time}
            s = s.filter("range", resolution_date=timestamp_dict)

        top_hits_aggregate = {
            "most_recent_bugs": A(
                "top_hits", sort=[{"resolution_date": {"order": "desc"}}], size=max_doc_count
            )
        }
        # size=65536 is the default search.max_buckets setting
        reporter_buckets_aggregate = A(
            "terms", field="reporter_email.keyword", size=65536, aggs=top_hits_aggregate
        )
        s.aggs.bucket("reporters", reporter_buckets_aggregate)

        response = s.execute()

        if not response.success():
            raise SearchUnsuccessfulException(
                response, search_description="get most recent resolved bugs"
            )
        reporters = response.aggregations.reporters
        if (
            reporters.doc_count_error_upper_bound > 0
            or reporters.sum_other_doc_count > 0
            or not reporters.buckets
        ):
            raise SearchUnsuccessfulException(
                response, search_description="aggregate recent resolved bugs per reporter"
            )
        else:
            return {
                reporter.key: [
                    IDManagerMap.get_manager_for_identifier(hit["data_source"])
                    .get_managed_document_type()
                    .deserialize_from_internal_json(hit.to_dict())
                    for hit in reporter.most_recent_bugs
                ]
                for reporter in reporters.buckets
            }
