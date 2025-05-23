"""
Functions related to making duplicate issues have a maximum degree of separation
of one. This code is in its own file because putting it anywhere else wouldn't
make sense or would cause a circular dependency.
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, TypedDict

import duo_logging  # type: ignore[import]
from duolingo_base.util import registry

from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, JIRA_ISSUE_TYPE_EPIC
from jeeves.dal.jira_dal import JiraApiDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.profiling import traced_function
from jeeves.manager.jira_manager import JiraManager
from jeeves.manager.parent_summary_manager import JiraTicketText, ParentSummaryManager
from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph, JiraDuplicateGraphOperationStatus
from jeeves.util.async_util import get_asyncio_loop
from jeeves.util.parent_jira_issue_util import (
    generate_parent_body_text_from_data,
    parse_parent_description,
    update_parent_data_from_child,
)
from jeeves.util.quality_report_util import is_jira_issue_resolved
from jeeves.util.s3_client_and_bucket import upload_to_jeeves_s3

LOG = logging.getLogger(__name__)
MAX_LOG_LINES = 10

PARENT_PREFIX = "[Parent]"
DUPLICATE_ISSUE_LINK_TYPE = "Duplicate"


class DuplicateGraphOperationResults(TypedDict):
    status: JiraDuplicateGraphOperationStatus
    edge_failures: List[Tuple[str, str]]
    edge_successes: List[Tuple[str, str]]


@registry.bind(
    es_dal=registry.reference(OpenSearchDAL),
    jira_dal=registry.reference(JiraApiDAL),
    jira_manager=registry.reference(JiraManager),
    parent_summary_manager=registry.reference(ParentSummaryManager),
)
class DuplicateGraphResolver:
    def __init__(
        self,
        es_dal: OpenSearchDAL,
        jira_dal: JiraApiDAL,
        jira_manager: JiraManager,
        parent_summary_manager: ParentSummaryManager,
        upload_to_s3: Callable[[str, bytes], None] = upload_to_jeeves_s3,
    ):
        self._es_dal = es_dal
        self._jira_dal = jira_dal
        self._jira_manager = jira_manager
        self._parent_summary_manager = parent_summary_manager
        self._upload_to_s3 = upload_to_s3

    @traced_function()
    def get_duplicate_graph(
        self, issue_keys: List[str], key_to_doc: Optional[Dict[str, JiraDocument]] = None
    ) -> JiraDuplicateGraph:
        """
        Takes issue key(s) and returns information about the set of reachable issues in the graph
        of duplicates.

        key_to_doc memoizes keys that we have fetched the doc for from JiraAPI

        Returns a dict with the following keys:
        - issue_keys_to_documents: a Dict[str, JiraDocument] of issue keys in the duplicate graph
            mapped to their document representations.
        - existing_links: a Set[Tuple[str]] of links that already exist between issues in the graph.
        """
        if key_to_doc is None:
            key_to_doc = {}

        existing_links: Set[Tuple[str, str]] = set()
        visited = {}
        unvisited = set(issue_keys)
        missing_issues = set()
        docs_to_fetch = {issue_key for issue_key in issue_keys if issue_key not in key_to_doc}
        while unvisited:
            # prioritize visiting loaded issues
            unvisited_loaded_issues = [issue for issue in unvisited if issue in key_to_doc]
            if unvisited_loaded_issues:
                target_key = unvisited_loaded_issues[0]
                unvisited.remove(target_key)
            else:
                target_key = unvisited.pop()
            # download issues in bulk as needed
            if target_key not in key_to_doc:
                docs = self._jira_manager.download_bulk_issues_with_features(list(docs_to_fetch))
                key_to_doc.update({doc.issue_key: doc for doc in docs})
                not_fetched = [
                    issue_key for issue_key in docs_to_fetch if issue_key not in key_to_doc
                ]
                for issue_key in not_fetched:
                    unvisited.discard(issue_key)
                    missing_issues.add(issue_key)
                    duo_logging.capture_message(f"Couldn't fetch Jira issue {issue_key}", "warning")

                docs_to_fetch = set()
                if target_key in not_fetched:
                    continue
            target_issue = key_to_doc[target_key]
            for existing_duplicate in target_issue.linked_duplicate_keys:
                if existing_duplicate not in visited and existing_duplicate not in missing_issues:
                    unvisited.add(existing_duplicate)
                    if existing_duplicate not in key_to_doc:
                        docs_to_fetch.add(existing_duplicate)
                existing_pair = tuple(sorted([target_key, existing_duplicate]))
                existing_links.add(existing_pair)
            visited[target_key] = target_issue
        return JiraDuplicateGraph(
            issue_keys_to_documents=visited, existing_issue_links=existing_links
        )

    def _get_duplicate_issue_link(
        self, duplicate_graph: JiraDuplicateGraph, outward_key: str, inward_key: str
    ):
        doc = duplicate_graph.issue_keys_to_documents.get(outward_key)
        if doc is None:
            return None
        try:
            for issue_link in doc.issue_links:
                if (
                    DUPLICATE_ISSUE_LINK_TYPE in issue_link["type"]["name"]
                    and "inwardIssue" in issue_link
                    and issue_link["inwardIssue"]["key"] == inward_key
                ):
                    return issue_link
        except:
            return None
        return None

    def _get_deletion_results(self, link_ids: Iterable[str]):
        loop = get_asyncio_loop()
        future = asyncio.ensure_future(self._jira_dal.delete_links_async(link_ids))
        return loop.run_until_complete(future)

    def disconnect_duplicates_remote(self, issue_key: str) -> DuplicateGraphOperationResults:
        duplicate_graph = self.get_duplicate_graph([issue_key])
        edges_to_ids: Dict[Tuple[str, str], str] = {}
        for outward_key, inward_key in duplicate_graph.existing_issue_links:
            for permutation in ((outward_key, inward_key), (inward_key, outward_key)):
                issue_link = self._get_duplicate_issue_link(duplicate_graph, *permutation)
                if issue_link is not None:
                    edges_to_ids[permutation] = issue_link["id"]

        deletion_results = self._get_deletion_results(edges_to_ids.values())
        ids_to_edges = {link_id: edge for edge, link_id in edges_to_ids.items()}
        failed_edges = [
            ids_to_edges[link_id] for link_id, success in deletion_results if not success
        ]
        status = JiraDuplicateGraphOperationStatus.FAILURE
        if len(failed_edges) == 0:
            status = JiraDuplicateGraphOperationStatus.SUCCESS
        elif len(failed_edges) < len(edges_to_ids):
            status = JiraDuplicateGraphOperationStatus.PARTIAL
        return DuplicateGraphOperationResults(
            status=status,
            edge_failures=failed_edges,
            edge_successes=[edge for edge in edges_to_ids if edge not in failed_edges],
        )

    def connect_duplicates_remote(self, issue_keys: List[str]) -> str:
        """
        Marks a new issue as a duplicate of each of several existing issues on
        Jira, and ensures that any issues with a finite degree of separation
        via duplicate relation from any of the provided issues become marked
        as duplicates such that the maximum degree of separation via duplicate
        relation is 1. Also enforces the presence of exactly one parent issue in
        the resulting group.

        For example, say we have the following situation, where letters
        represent issues and hyphens represent that two issues are duplicates:
        A-B-C
        D-E-F
        And then we want to mark issue G as a duplicate of both A and D. This
        function will perform that operation, as well as marking any pair of
        letters from [A, G] as duplicates of each other.

        We perform the above operation by constructing a graph of the existing
        duplicate relationships, according to what we have stored in
        OpenSearch to minimize how many potentially expensive network calls
        we need to make. We then determine what edges need to be added to this
        graph to make it fully connected. Finally, we call mark_duplicate_remote
        for every edge we need to add. If any edge addition fails, we continue
        attempting to add all other edges. The return value of this function
        indicates which edge additions succeeded and which did not.

        Enforcement of exactly one parent issue is performed by checking all
        documents that will become part of the group for the parent property.
        If exactly 0 such documents are found, a new document is created and
        added to the existing set of documents. If exactly 1 document is found,
        it will be used as the parent issue for the whole group. If 2 or more
        documents are found, one parent will be chosen and the rest deprecated.

        Parameters:
            existing_keys: A list of issue keys of issues that we want to
                           include in our fully duplicate graph. All duplicates
                           of these issues will also be included in the graph,
                           as well as all duplicates of those issues, and so on.
                           If no parent issue is found in any of these duplicates,
                           a new issue will be created as the parent issue.

        Returns:
            A string, indicating which edge additions succeeded and which
            failed. The first line of the string is one of SUCCESS, PARTIAL,
            or FAILURE. SUCCESS indicates that all edges were successfully
            added, FAILURE indicates that no edges were successfully added, and
            PARTIAL indicates that some edges were successfully added and some
            were not. This first line is followed by several other lines, each
            of which starts with the character S (for success) or F (for
            failure), followed by two issue keys; each line indicates whether
            its two issue keys were successfully marked as duplicates. We
            attach a trailing newline at the end of the final line so that every
            line is parsed identically. If no new duplicate links were added,
            we consider the operation a success. If we attempt to merge two or
            more parent issues into the same group, an exception will be thrown.
        """
        # Log the issue keys we're connecting duplicates for.
        displayed_keys = issue_keys[:MAX_LOG_LINES]
        msg = f"Connecting {len(issue_keys)} duplicate(s) for {displayed_keys}"
        if len(issue_keys) > MAX_LOG_LINES:
            msg += "...truncated"
        LOG.info(msg)

        # Get the duplicate graph for the issue keys.
        duplicate_graph = self.get_duplicate_graph(issue_keys)
        doc_reps = [doc for doc in duplicate_graph.issue_keys_to_documents.values()]
        group_parents = [doc for doc in doc_reps if doc and JiraDocument.is_group_parent(doc)]
        features = [doc.feature for doc in doc_reps if doc.feature]
        most_common_feature = max(set(features), key=features.count) if features else None
        priority = Counter([doc.priority for doc in doc_reps]).most_common(1)[0][0]

        parent_key = None
        deprecated_parent_issue_keys = []
        if len(group_parents) == 1:
            parent_key = group_parents[0].issue_key
        elif len(group_parents) == 0:
            parent_project = doc_reps[0].project
            combined_headers = "|".join([doc.header_text for doc in doc_reps])
            # Jira issue titles have a hard 255 character limit
            parent_header_text = f"PARENT FOR [{combined_headers}]"[:255]
            parent_key = self._upload_template_parent_issue(parent_project, parent_header_text)
            duplicate_graph.issue_keys_to_documents[parent_key] = self._jira_dal.get_issue(
                parent_key
            )
        else:
            parent_key, deprecated_parent_issue_keys = self.resolve_multiple_parent_issues(
                group_parents
            )
        # Log the parent key and deprecated parent issue keys.
        LOG.info(f"Parent key chosen: {parent_key}")
        LOG.info(f"Deprecated parent issue keys: {deprecated_parent_issue_keys}")

        parent_doc = duplicate_graph.issue_keys_to_documents[parent_key]
        parent_data = parse_parent_description(parent_doc.body_text)

        # Only link the parent to each child (not between children)
        all_possible_links = set()
        for key in duplicate_graph.issue_keys_to_documents.keys():
            if key != parent_key and key not in deprecated_parent_issue_keys:
                all_possible_links.add((key, parent_key))

        # Log the links we're marking as duplicates.
        displayed_links = list(all_possible_links)[:MAX_LOG_LINES]
        msg = f"Marking {len(all_possible_links)} duplicate(s) for {parent_key}: {displayed_links}"
        if len(all_possible_links) > MAX_LOG_LINES:
            msg += "...truncated"
        LOG.info(msg)

        remaining_links = all_possible_links - duplicate_graph.existing_issue_links
        any_success = False
        any_failure = False
        result_list = []

        loop = get_asyncio_loop()
        future = asyncio.ensure_future(self._jira_dal.mark_duplicates_async(remaining_links))
        results = loop.run_until_complete(future)

        for outward_end, inward_end, link_created in results:
            # We don't need to edit our documents here because the changes will
            # get pulled in from Jira later anyway.
            if link_created:
                any_success = True
                result_list.append(f"S {outward_end} {inward_end}\n")
                if outward_end == parent_key and inward_end not in deprecated_parent_issue_keys:
                    child_issue = duplicate_graph.issue_keys_to_documents[inward_end]
                    update_parent_data_from_child(parent_data, child_issue)
                elif inward_end == parent_key and outward_end not in deprecated_parent_issue_keys:
                    child_issue = duplicate_graph.issue_keys_to_documents[outward_end]
                    update_parent_data_from_child(parent_data, child_issue)
            else:
                any_failure = True
                result_list.append(f"F {outward_end} {inward_end}\n")

        children_docs = [
            JiraTicketText.from_jira_doc(doc)
            for doc in duplicate_graph.issue_keys_to_documents.values()
            if not JiraDocument.is_group_parent(doc)
        ]
        aic_summary = self._parent_summary_manager.generate_summary_and_description(children_docs)
        aic_title = aic_summary.title
        aic_description = aic_summary.description

        # Prepend [Parent] to the summary so that it's clear that this is a parent issue.
        # (Only if [Parent] is not already in the summary)
        if PARENT_PREFIX not in aic_title:
            aic_title = f"{PARENT_PREFIX} {aic_title}"

        self._try_set_remote_parent(
            parent_key, aic_title, aic_description, parent_data, most_common_feature, priority
        )

        result_manifest = "".join(result_list)
        # If we had no successes and no failures, then we didn't create any new
        # links. This turns out to be identical to the case where we had only
        # successes.
        result_status = "UNSET, THIS IS AN ERROR"
        if not any_failure:
            result_status = "SUCCESS"
        elif any_success:
            result_status = "PARTIAL"
        else:
            result_status = "FAILURE"

        result = f"{result_status}\n{result_manifest}"
        # Upload the result status and manifest to S3
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            s3_key = f"duplicate_connect_results/{parent_key}_{timestamp}.txt"
            self._upload_to_s3(s3_key, result.encode("utf-8"))
            LOG.info(f"Uploaded duplicate connect results to S3: {s3_key}")
        except Exception as e:
            LOG.error(f"Error uploading duplicate connect results to S3: {e}")

        return result

    def _upload_template_parent_issue(self, project: str, header_text: str) -> str:
        """
        Uploads a template parent issue to the specified project with the
        specified header text.

        The template issue contains paragraph blocks that each consist of one of
        the parent categories defined in get_parent_category_mappings() in the
        JiraDocument class. The resulting body text is appropriate for adding
        data to, sourced from individual Jira documents.

        Parameters:
            project: The project this parent issue should live in.
            header_text: The header text this parent issue should have.

        Returns:
            The issue key of the new parent issue, as returned by Jira.
        """
        category_names = JiraDocument.get_parent_category_mappings().values()
        body_json = generate_parent_body_text_from_data(
            "", {category: {} for category in category_names}
        )
        return self._jira_dal.create_bug_issue(project, header_text, body_json)

    def try_mark_duplicate_remote(self, outward_key: str, inward_key: str) -> bool:
        """
        Given two issue keys, one outward and one inward, marks them as
        duplicates of each other on JIRA. We distinguish between outward and
        inward here because JIRA's architecture does not consider the relation
        to be symmetric. To my knowledge, all other parts of Jeeves discard
        this directionality information and treat the relationship as though
        it were symmetric, so flipping the order of the parameters here should
        not matter.

        Parameters:
            outward_key: Issue key on the "outward" side of the duplicate link.
            inward_key: Issue key on the "inward" side of the duplicate link.

        Returns:
            True if the link is created, otherwise False.
        """
        try:
            self._jira_dal.mark_duplicate(outward_key, inward_key)
            return True
        except:
            return False

    def _try_set_remote_parent(
        self,
        parent_key: str,
        summary: str,
        description: str,
        data: Dict[str, Dict[str, int]],
        feature: Optional[str],
        priority: Optional[str],
    ) -> bool:
        """
        Sets the body text of the issue specified by parent_key to content
        specified by the provided data, and saves this change to Jira.

        Parameters:
            parent_key: The issue key of the parent issue we want to edit
            summary: The summary of the parent issue.
            description: The text-based description of all the issues captured
                  by the parent.
            data: The data we will use to generate the new parent body. See
                  parse_parent_description for format.
            feature: The string to be used for the issue's feature field
            priority: The string to be used for the issue's priority field

        Returns:
            True if the Jira API indicates that the operation completed
            successfully, otherwise False.
        """
        try:
            self._jira_dal.update_issue(
                parent_key,
                summary=summary,
                description=generate_parent_body_text_from_data(description, data),
                feature=feature,
                priority=priority,
            )
            return True
        except:
            return False

    def resolve_multiple_parent_issues(
        self, group_parents: List[JiraDocument]
    ) -> Tuple[str, List[str]]:
        (parent_key, deprecated_parent_issues) = self.choose_parent_issue(group_parents)
        deprecated_parent_issue_keys = [issue.issue_key for issue in deprecated_parent_issues]
        self._deprecate_parent_issues(deprecated_parent_issues)
        return parent_key, deprecated_parent_issue_keys

    def choose_parent_issue(
        self, parent_issues: List[JiraDocument]
    ) -> Tuple[str, List[JiraDocument]]:
        def _choose_parent_issue_from_filtered_list(filtered_list: List[JiraDocument]):
            sorted_filtered_list = sorted(
                filtered_list, key=lambda issue: issue.updated_date, reverse=True
            )
            new_parent = sorted_filtered_list[0]
            return (
                new_parent.issue_key,
                [issue for issue in parent_issues if issue.issue_key != new_parent.issue_key],
            )

        issues_in_progress = [issue for issue in parent_issues if issue.status == "In Progress"]
        if len(issues_in_progress) > 0:
            return _choose_parent_issue_from_filtered_list(issues_in_progress)

        issues_not_resolved = [issue for issue in parent_issues if issue.resolution != ""]
        if len(issues_not_resolved) > 0:
            return _choose_parent_issue_from_filtered_list(issues_not_resolved)

        return _choose_parent_issue_from_filtered_list(parent_issues)

    def _deprecate_parent_issues(self, parent_issues: List[JiraDocument]):
        for issue in parent_issues:
            self._jira_dal.update_issue(
                issue.issue_key,
                summary=f"(deprecated) {issue.header_text}"[:255],
                remove_parent_bug_label=True,
            )
            self._jira_dal.close_issue_as_duplicate(issue.issue_key)

    def resolve_duplicate_graphs(
        self,
        jira_issues: List[JiraDocument],
    ) -> Tuple[List[JiraDocument], Dict[str, JiraDocument]]:
        """
        Params:
            jira_issues: list of JiraDocuments

        Returns:
            A tuple of
                a set of jira issue keys with only one representative issue from each duplicate graph.
                a mapping from issue key to Jira document

        For each jira issue we resolve the duplicate graph and determine a representative of each dupe graph
        The rep will be the parent of the graph if it exists. If there is only one issue, then that issue is
        the rep. Otherwise, if there is at least one open issue, some open issue is used as the rep. Finally
        if all issues are done, then any issue that was not closed as a Duplicate is used.

        Assigns parent issue and child_issue attributes for jira documents
        """
        # Fetch all directly linked duplicates in batch and compile a mapping from issue key to issue
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        issues_to_fetch = {
            key
            for issue in jira_issues
            for key in issue.linked_duplicate_keys
            if key not in key_to_issue
        }

        downloaded_issues = self._jira_manager.download_bulk_issues_with_features(
            list(issues_to_fetch)
        )
        key_to_issue.update({issue.issue_key: issue for issue in downloaded_issues})
        # For each issue determine the duplicate graph and choose a representative.
        parent_representatives = []
        visited_issues = set()
        for issue in jira_issues:
            if issue.issue_key in visited_issues:
                continue
            duplicate_graph = self.get_duplicate_graph([issue.issue_key], key_to_doc=key_to_issue)
            duplicate_graph_issues = list(duplicate_graph.issue_keys_to_documents.values())
            visited_issues.update(duplicate_graph.issue_keys_to_documents.keys())
            parent_issues = []
            for issue in duplicate_graph_issues:
                if JiraDocument.is_group_parent(issue) and issue.issue_type == JIRA_ISSUE_TYPE_BUG:
                    parent_issues.append(issue)

            if len(parent_issues) == 1:
                parent_issue = parent_issues[0]
            elif len(parent_issues) > 1:
                # check to see if any issue is open
                for potential_parent_issue in parent_issues:
                    if not is_jira_issue_resolved(potential_parent_issue.resolution):
                        parent_issue = potential_parent_issue
                        break
                else:
                    parent_issue = potential_parent_issue
            elif len(duplicate_graph_issues) == 1:
                parent_issue = issue
            else:
                open_issues = [
                    issue
                    for issue in duplicate_graph_issues
                    if not is_jira_issue_resolved(issue.resolution)
                ]
                if len(open_issues) > 0:
                    parent_issue = open_issues[0]
                else:
                    non_dupes = [
                        issue for issue in duplicate_graph_issues if issue.resolution != "Duplicate"
                    ]
                    parent_issue = duplicate_graph_issues[0] if non_dupes == [] else non_dupes[0]

            parent_issue.child_issues = [
                i.issue_key for i in duplicate_graph_issues if i.issue_key != parent_issue.issue_key
            ]
            for child_issue in duplicate_graph_issues:
                if child_issue == parent_issue:
                    continue
                child_issue.parent_issue = parent_issue.issue_key

            if parent_issue.issue_type != JIRA_ISSUE_TYPE_EPIC:
                parent_representatives.append(parent_issue)

        return parent_representatives, key_to_issue
