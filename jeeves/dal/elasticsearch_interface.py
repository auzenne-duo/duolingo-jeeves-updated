import sys
from datetime import date, datetime
from typing import Dict, Iterator, List, Optional, Set, Union

import rollbar
from duolingo_base.config import Config
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Mapping, Q, Search
from elasticsearch_dsl.query import MoreLikeThis

from jeeves.config.config import DATA_VERSION_IDENTIFIER
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.util.date_util import date_to_str, datetime_to_str

_config = Config.load_config()

# If we ever change the duplicate detection model, make sure this value is
# updated appropriately
_SENTENCE_TRANSFORMERS_VECTOR_SIZE = 768


class ElasticsearchDAL:
    def __init__(self) -> None:
        host = _config.get_nested(["elasticsearch", "host"])
        port = int(_config.get_nested(["elasticsearch", "port"]))

        self._es = Elasticsearch([host], port=port)

        self._indexname = f"jeeves_tickets_v_{DATA_VERSION_IDENTIFIER}"

    def initialize_index(self) -> None:
        """
        Initialize Elasticsearch index
        Should only be called once, during server startup
        """

        if not self._es.indices.exists(index=self._indexname):

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

            # We now need to pivot into a different structure to add the
            # mapping for the duplicate detector's embedding vector. This format
            # is more annoying to work with so it is only being used here
            # because I couldn't get it to work in the above format.
            mapping_dict = m.to_dict()
            mapping_dict["properties"]["embedding_vector"] = {
                "type": "knn_vector",
                "dimension": _SENTENCE_TRANSFORMERS_VECTOR_SIZE,
            }

            settings_dict = {
                "index": {
                    "knn": True,
                    "knn.space_type": "cosinesimil",
                }
            }

            index_creation_structure = {
                "mappings": mapping_dict,
                "settings": settings_dict,
            }

            self._es.indices.create(index=self._indexname, body=index_creation_structure)
            rollbar.report_message("Created index {self._indexname} with new mappings", "info")

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

    def aggregate_time_series(
        self, lang: str, spike_category: SpikeCategory, word: str
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Calculates per-day counts of how many tickets contain a particular word

        Parameters:
            lang: Language to search tickets in.
            spike_category: The spike category whose documents we should search within.
            word: Term to search against. Supports regular expressions.

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

        s = SpikeCategory.get_elasticsearch_transformer_for_category(spike_category)(s)

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

    def ensure_specific_jira_issue(
        self, issue_key: str, force_download: bool = False
    ) -> Optional[JeevesDocument]:
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
                            if we already have a copy in Elasticsearch.

        Returns:
            A JeevesDocument object representing the requested document as it
            exists in Elasticsearch, or None if we can't find the document.
        """

        # First, determine if we already have the requested document.
        # We could do a call to count_by_arbitrary_keywords here but if we have
        # the document then we'll need to call this anyway.
        filter_results = list(self.filter_by_arbitrary_keywords({"issue_key.keyword": issue_key}))

        base_document = None

        # If Python had switch statements I would use one but here we are.
        # I'm explicitly checking the length of the list against 0 to emulate a
        # switch statement structure.
        if force_download or len(filter_results) == 0:
            jira_manager = IDManagerMap.get_manager_for_identifier("JIRA")
            base_document = jira_manager.download_specific_issue(issue_key)
            self.bulk_index_tickets([base_document])

        elif len(filter_results) == 1:
            base_document = filter_results[0]

        else:
            # There is no way we should ever get here and if we do something
            # very broken has happened.
            raise Exception(
                f"Filtering to find issue {issue_key} somehow returned {len(filter_results)} results. Please investigate."
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
                             Elasticsearch, we attempt to download it.
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

        target_doc = self.ensure_specific_jira_issue(issue_key)

        if not target_doc:
            print(f"Requested issue with key {issue_key} could not be found.")
            return []

        query_body = {
            "size": max_search_depth,
            "query": {
                "knn": {
                    "embedding_vector": {
                        "k": max_search_depth,
                        "vector": target_doc.embedding_vector,
                    }
                }
            },
        }

        response = self._es.search(index=self._indexname, body=query_body)
        result_docs = [
            IDManagerMap.get_manager_for_identifier(hit["_source"]["data_source"])
            .get_managed_document_type()
            .deserialize_from_internal_json(hit["_source"])
            for hit in response["hits"]["hits"]
            if hit["_score"] >= 0.8
        ]
        result_docs = list(
            filter(lambda doc: (target_doc.date_time - doc.date_time).days < 60, result_docs)
        )
        if should_filter_project:
            result_docs = [doc for doc in result_docs if doc.project == target_doc.project]
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

    def find_jira_by_key(self, issue_key: str) -> Optional[JeevesDocument]:
        """
        Queries for a particular Jira issue using an issue key.

        If found, returns an object representation of the document,
        otherwise returns None.

        Parameters:
            issue_key: The issue key of the document we want to query.

        Returns:
            An object representation of the queried document, or None.
        """

        s = Search(using=self._es, index=self._indexname).filter(
            "term", issue_key__keyword=issue_key
        )
        results = self.execute_arbitrary_query(s.to_dict())
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            raise Exception(
                f"Found two documents with identical issue_key value {issue_key}, please investigate."
            )

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
            family_member = self.ensure_specific_jira_issue(family_member_key)
            if family_member.is_group_parent(family_member):
                return family_member
        return None


ElasticDAL = ElasticsearchDAL()
