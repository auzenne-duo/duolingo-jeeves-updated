from datetime import date, datetime
import sys
from typing import Dict, Iterator, List, Optional, Set, Union

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Mapping, Q, Search
from elasticsearch_dsl.query import MoreLikeThis

from duolingo_base.config import Config
from jeeves.config.config import DATA_VERSION_IDENTIFIER

from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.util.date_util import date_to_str, datetime_to_str


_config = Config.load_config()


class ElasticsearchDAL:
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

            # We need to explicitly set these types because Elasticsearch will
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
            m.save(self._indexname, using=self._es)

        if not self._es.indices.exists(index=self._spikename):
            self._es.indices.create(index=self._spikename)

            m = Mapping()
            m.field("lang", "keyword")
            m.field("spike_group", "keyword")
            m.save(self._spikename, using=self._es)

    def _execute_search_for_documents(self, s: Search) -> List[JeevesDocument]:
        """
        Given an Elasticsearch_DSL Search object, performs the necessary logic
        to execute that search and convert the results into a list of document
        objects.

        Parameters:
            s: An Elasticsearch_DSL Search object to execute.

        Returns:
            The results of the input search as a list of JeevesDocument objects.
        """

        response = s.execute()
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
        Given JSON representing an arbitrary Elasticsearch query, execute that
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
        Elasticsearch. Currently this is only expected to happen for malformed
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
            "ERROR": "Elasticsearch encountered an unknown error. Please report this behavior to the repo owner."
        }

    def get_recent_paginated_tickets(
        self,
        lang: str,
        word: str,
        page: int = 0,
        limit: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        beta_filter_category: Optional[str] = False,
        jeeves_id: Optional[str] = None,
    ) -> Dict[str, Union[int, List[JeevesDocument]]]:
        """
        Returns stored user tickets from Elasticsearch in a paginated manner.
        To obtain multiple pages of tickets, call this function multiple times.
        If an empty string is passed to the `word` parameter, replace the normal
        `match against this word` query with a `match all` query.

        Parameters:
            lang (str): Language to search for tickets in.
            word (str): Query to search against in Elasticsearch. An empty string
                        will match to all documents. Uses regular expressions.
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
            beta_filter_category (str): How we should filter results to
                                        have specific values related to release
                                        candidates, if at all. Optional value.
            jeeves_id (str): Unique ID of a specific document. A unique ID is
                             assigned to every document at index time, in
                             bulk_index_tickets. Providing this value overrides
                             all other arguments because no additional filtering
                             should be performed if the user already knows which
                             document they want. Optional value.

        Returns:
            A dictionary containing the following:
            - data: A list of support ticket objects, representing the requested
              page of results. Results are sorted, larger timestamps first.
            - total_records: An integer representing the total number of hits
              for the search criteria
            - deepest_index: An integer representing the index in the search
              of the last expected element
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
                s = s.query("query_string", default_field="body_text", query=word, lenient=True)
            else:
                s = s.query("match_all")

            if beta_filter_category:
                s = s.filter("term", shake_to_report_category=beta_filter_category)

        try:
            total_records = s.count()

            retval = {"total_records": total_records}

            lower_limit = limit * page
            upper_limit = lower_limit + limit
            s = s[lower_limit:upper_limit]

            retval.update({"deepest_index": upper_limit})

            retval.update({"data": self._execute_search_for_documents(s)})

            return retval

        except RequestError as e:
            return self._handle_es_request_errors(e)

    def aggregate_time_series(self, lang: str, word: str) -> List[Dict[str, Union[str, int]]]:
        """
        Calculates per-day counts of how many tickets contain a particular word

        Parameters:
            lang (str): Language to search tickets in.
            word (str): Term to search against. Supports regular expressions.

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
            .query("query_string", default_field="body_text", query=word, lenient=True)
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

        try:
            response = s.execute()
            if not response.success():
                print("Attempt to aggregate time series failed.", file=sys.stderr)
                print("Here's what the call to execute() returned:", file=sys.stderr)
                print(response.to_dict(), file=sys.stderr)
            response_buckets = response.aggregations.replacementtimeseries.buckets
            return response_buckets

        except RequestError as e:
            return self._handle_es_request_errors(e)

    def bulk_index_tickets(self, tickets: List[JeevesDocument]) -> None:
        """
        Store multiple tickets into Elasticsearch.

        Parameters:
            tickets: Object representation of tickets to store.
        """
        bulk_actions = [
            {
                "_index": self._indexname,
                "_source": ticket.serialize_to_json(ticket),
                "_id": ticket.generate_elasticsearch_internal_id(ticket),
            }
            for ticket in tickets
        ]
        bulk(self._es, bulk_actions)

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
            there were no tickets in Elasticsearch.
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

    def get_min_and_max_document_dates(self) -> Dict[str, str]:
        """
        Returns the earliest and latest dates among all documents in our data.
        Return value is a dict with keys `min` and `max` and string
        representations of dates as values.
        """

        s = Search(using=self._es, index=self._indexname)
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
                    - spike_group (str): Name of spike category the spike belongs
                                         to (see SpikeCategories.py).
        """
        bulk_actions = [
            {
                "_index": self._spikename,
                "_source": spike,
                "_id": f"SPIKE_{spike['word']}_{spike['lang']}_{spike['date']}_{spike['spike_group']}",
            }
            for spike in spikes
        ]
        bulk(self._es, bulk_actions)

    def get_min_and_max_spike_dates(self) -> Dict[str, str]:
        """
        Returns the earliest and latest dates among all spikes in our data.
        Return value is a dict with keys `min` and `max` and string
        representations of dates as values.

        This is just the same method as get_min_and_max_document_dates, but for
        spikes instead of documents.
        """

        s = Search(using=self._es, index=self._spikename)
        s.aggs.metric("min_date", "min", field="date", format="yyyy-MM-dd")
        s.aggs.metric("max_date", "max", field="date", format="yyyy-MM-dd")

        response = s.execute()

        min_date = response.aggregations.min_date.value
        max_date = response.aggregations.max_date.value

        # We need to divide the return values by 1000 because they will be in
        # milliseconds instead of seconds.
        return {
            "min": date_to_str(date.fromtimestamp(min_date / 1000)) if min_date else None,
            "max": date_to_str(date.fromtimestamp(max_date / 1000)) if max_date else None,
        }

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
        self, lang: str, date_str: str, num_spikes: int, spike_group: SpikeCategory
    ) -> Iterator[Dict[str, Union[str, float]]]:
        """
        Yields all spikes for a given language, from a particular date.

        Parameters:
            lang (str): Language to yield spikes for.
            date (str): Date to search on, as a string.
            num_spikes (int): How many spikes we should yield.
            spike_group: Which group we want spikes from
                         (see jeeves/model/spike_categories.py)

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
            .filter("term", spike_group=spike_group.name)
            .sort("-score")
        )
        s = s[0:num_spikes]
        for hit in s.execute():
            yield hit

    def yield_spikes_in_date_range(
        self, lang: str, start_date: str, end_date: str, spike_group: Optional[str] = "ALL_SPIKES"
    ) -> Iterator[Dict[str, Union[str, float]]]:
        """
        Yields all spikes for a given language, between two dates

        Parameters:
            lang (str): Language to yield spikes for.
            start_date (str): Date to start search on, as a string.
            end_date (str): Date to end search on, as a string.
            spike_group (str): Spike group to restrict search to. Optional,
                               defaults to returning spikes from all documents.

        Yields:
            Spikes from the requested language between requested dates.
            See documentation for bulk_index_spikes for a description of spike
            format. Results are unsorted.
        """

        s = (
            Search(using=self._es, index=self._spikename)
            .filter("term", lang=lang)
            .filter("term", spike_group=spike_group)
            .sort("-score")
        )

        timestamp_dict = {}
        if start_date:
            timestamp_dict["gte"] = start_date
        if end_date:
            timestamp_dict["lte"] = end_date
        if timestamp_dict:
            s = s.filter("range", date=timestamp_dict)

        yield from s.scan()

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

        yield from [
            IDManagerMap.get_manager_for_identifier(hit.data_source)
            .get_managed_document_type()
            .deserialize_from_internal_json(hit.to_dict())
            for hit in s.scan()
        ]

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
        # I'm not aware of a way to do this purely in Elasticsearch but if
        # anyone reading this has any ideas please let me know.
        results_page_start = 0
        results_page_size = 10
        running_known_duplicates = set(base_document.linked_duplicate_keys)
        output_list = []
        while True:
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


ElasticDAL = ElasticsearchDAL()
