from datetime import datetime
import sys
from typing import Dict, Iterator, List, Optional, Set, Union

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Search

from duolingo_base.config import Config
from jeeves.config.config import DATA_VERSION_IDENTIFIER
from jeeves.lib.identifier_document_mapping import IDENTIFIER_DOCUMENT_MAPPING
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import datetime_to_str


_config = Config.load_config()


class ElasticsearchDAL(object):
    def __init__(self) -> None:
        host = _config.get_nested(["elasticsearch", "host"])
        port = int(_config.get_nested(["elasticsearch", "port"]))

        self._es = Elasticsearch([host], port=port)

        self._indexname = f"jeeves_tickets_v_{DATA_VERSION_IDENTIFIER}"
        self._spikename = f"jeeves_spikes_v_{DATA_VERSION_IDENTIFIER}"

    def initialize_indices(self) -> None:
        """
        Initialize Elasticsearch indices
        Should only be called once, during server startup
        """

        if not self._es.indices.exists(index=self._indexname):
            self._es.indices.create(index=self._indexname)

        if not self._es.indices.exists(index=self._spikename):
            self._es.indices.create(index=self._spikename)

    def get_recent_paginated_tickets(
        self,
        lang: str,
        word: str,
        page: int = 0,
        limit: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[JeevesDocument]:
        """
        Returns stored user tickets from Elasticsearch in a paginated manner.
        To obtain multiple pages of tickets, call this function multiple times.

        Parameters:
            lang (str): Language to search for tickets in.
            word (str): Query to search against in Elasticsearch.
            page (int): Desired page number of results.
                        Used when multiple pages of results are needed.
            limit (int): The maximum number of results per page.
                         The final page of results may have fewer than this many.
            start_time (datetime): The beginning of a date range to search for tickets in.
                                   Results will not have timestamps before this value.
                                   Optional value.
            end_time (datetime):  The end of a date range to search for tickets in,
                                  Results will not have timestamps after this value.
                                  Optional value.

        Returns:
            A list of support ticket objects, representing the requested page of results.
            Results are sorted, larger timestamps first.
        """
        timestamp_dict = {"time_zone": "America/New_York"}
        if start_time:
            timestamp_dict.update({"gte": start_time.date()})
        if end_time:
            timestamp_dict.update({"lte": end_time.date()})

        s = (
            Search(using=self._es, index=self._indexname)
            .query("match", body_text=word)
            .filter("range", date_time=timestamp_dict)
            .filter("term", language=lang)
            .sort("-date_time")
        )

        lower_limit = limit * page
        upper_limit = lower_limit + limit
        s = s[lower_limit:upper_limit]

        response = s.execute()
        if not response.success():
            print("Attempt to get recent paginated tickets failed.", file=sys.stderr)
            print("Here's what the call to execute() returned:", file=sys.stderr)
            print(response.to_dict(), file=sys.stderr)

        tickets = [
            IDENTIFIER_DOCUMENT_MAPPING[
                hit["_source"]["data_source"]
            ].deserialize_from_internal_json(hit["_source"])
            for hit in response.to_dict()["hits"]["hits"]
        ]

        return tickets

    def aggregate_time_series(self, lang: str, word: str) -> List[Dict[str, Union[str, int]]]:
        """
        Calculates per-day counts of how many tickets contain a particular word

        Parameters:
            lang (str): Language to search tickets in.
            word (str): Term to search against.

        Returns:
            A list of dicts, where each dict contains a string reprseneting a
            date and an int representing a count of how many times the input
            term appeared on that date.

        TODO:
            Currently, there is no ability to restrict the query by date.
            It might be nice to implement that filter here instead of needing
            to possibly discard data later.
        """

        s = (
            Search(using=self._es, index=self._indexname)
            .query("match", body_text=word)
            .filter("term", language=lang)
        )

        # Elasticsearch just so happens to have functionality for making a date
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

        response = s.execute()
        if not response.success():
            print("Attempt to aggregate time series failed.", file=sys.stderr)
            print("Here's what the call to execute() returned:", file=sys.stderr)
            print(response.to_dict(), file=sys.stderr)
        response_buckets = response.aggregations.replacementtimeseries.buckets

        return response_buckets

    def bulk_index_tickets(self, json_tickets: List[JSON]) -> None:
        """
        Store multiple tickets into Elasticsearch.

        Parameters:
            json_tickets: JSON representation of tickets to store.
        """
        bulk_actions = [
            {
                "_index": self._indexname,
                "_source": ticket,
                "_id": f"{ticket['data_source']}_{ticket['document_id']}",
            }
            for ticket in json_tickets
        ]
        bulk(self._es, bulk_actions)

    def get_most_recent_timestamp(self, lang: Optional[str] = None) -> Optional[float]:
        """
        Acquire submission timestamp of most recent stored ticket.

        Parameters:
            lang (str): Optional, filter ticket search to only this language.

        Returns:
            Most recent UNIX timestamp across all searched tickets, or None if
            there were no tickets in Elasticsearch.
        """
        s = Search(using=self._es, index=self._indexname).query("match_all")
        if lang:
            s = s.filter("term", language=lang)
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

    def _get_terms_from_slice(self, doc_ids_slice: List[str], lang: str) -> Set[str]:
        """
        Helper function for get_terms_from_docs, below.
        Given a list of document IDs, determine all terms used in the
        corresponding documents, using Elasticsearch's mtermvectors functionality

        Parameters:
            doc_ids_slice (List[str]): A list of document IDs for which we want to collect terms.
            lang (str): Two-letter language code that the given documents are expected to have.

        Returns:
            Set of strings, representing terms from the requested documents.
        """
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
            # Quick and dirty way of filtering out any terms containing
            # digits. If a term contains digits its probably either a user
            # describing an amount of something or system information
            # we've attached. In the former case, the digit is probably not
            # a useful spike word, and in the latter case, the output tends
            # to get flooded by versions of iOS, which is also not useful.
            terms = set([s for s in terms if not any(i.isdigit() for i in s)])
            return terms
        except:
            return set()

    def get_terms_from_docs(self, doc_ids: List[str], lang: str) -> Set[str]:
        """
        Given document IDs, determine all terms used in the corresponding documents.

        Parameters:
            doc_ids (List[str]): Document IDs to get terms for.
            lang (str): Specify which Elasticsearch analyzer should be used
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

    def bulk_index_spikes(self, spikes: List[JSON]) -> None:
        """
        Stores multiple spikes into Elasticsearch

        Parameters:
            spikes: List of spikes to store. Each spike is a dictionary that
                    should contain:
                    - word (str): The term the spike represents.
                    - lang (str): The language that the above word is from.
                    - date (str): The date the above word spiked on.
                    - score (float): How sharp the spike was.
        """
        bulk_actions = [
            {
                "_index": self._spikename,
                "_source": spike,
                "_id": f"SPIKE_{spike['word']}_{spike['lang']}_{spike['date']}",
            }
            for spike in spikes
        ]
        bulk(self._es, bulk_actions)

    def yield_all_spikes(self, lang: str) -> Iterator[Dict[str, Union[str, float]]]:
        """
        Yields all spikes for a given language.

        Parameters:
            lang (str): Language to yield spikes for.

        Yields:
            Spikes from the requested language. See documentation for
            bulk_index_spikes for a description of spike format.
        """
        s = Search(using=self._es, index=self._spikename).filter("term", lang=lang).sort("-score")
        for hit in s.scan():
            yield hit

    def yield_spikes_on_date(
        self, lang: str, date_str: str, num_spikes: int
    ) -> Iterator[Dict[str, Union[str, float]]]:
        """
        Yields all spikes for a given language, from a particular date.

        Parameters:
            lang (str): Language to yield spikes for.
            date (str): Date to search on, as a string.
            num_spikes (int): How many spikes we should yield.

        Yields:
            Spikes from the requested language on the requested date.
            Results are sorted, higher values of score first.
            See documentation for bulk_index_spikes for a description of spike
            format.
        """
        # If x <= y and x >= y, then we must have x == y
        timestamp_dict = {"gte": date_str, "lte": date_str}
        s = (
            Search(using=self._es, index=self._spikename)
            .filter("range", date=timestamp_dict)
            .filter("term", lang=lang)
            .sort("-score")
        )
        s = s[0:num_spikes]
        for hit in s.execute():
            yield hit


ElasticDAL = ElasticsearchDAL()
