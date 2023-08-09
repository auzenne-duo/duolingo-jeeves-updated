"""
Functions related to making duplicate issues have a maximum degree of separation
of one. This code is in its own file because putting it anywhere else wouldn't
make sense or would cause a circular dependency.
"""

import asyncio
from collections import Counter
from typing import Dict, List, Optional, Tuple

import rollbar
from duolingo_base.util import registry

from jeeves.dal.jira_dal import JiraApiDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.lib.profiling import traced_function
from jeeves.manager.parent_summary_manager import ParentSummaryManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph
from jeeves.util.async_util import get_asyncio_loop
from jeeves.util.cleanup import extract_duolingo_metadata
from jeeves.util.parent_jira_issue_util import (
    generate_parent_body_text_from_data,
    parse_parent_description,
    strip_parent_description,
    update_parent_data_from_child,
)


@registry.bind(
    es_dal=registry.reference(OpenSearchDAL),
    jira_dal=registry.reference(JiraApiDAL),
    parent_summary_manager=registry.reference(ParentSummaryManager),
)
class DuplicateGraphResolver:
    def __init__(
        self,
        es_dal: OpenSearchDAL,
        jira_dal: JiraApiDAL,
        parent_summary_manager: ParentSummaryManager,
    ):
        self._es_dal = es_dal
        self._jira_dal = jira_dal
        self._jira_manager = IDManagerMap.get_manager_for_identifier("JIRA")
        self._parent_summary_manager = parent_summary_manager

    @traced_function()
    def get_duplicate_graph(
        self, issue_keys: List[str], key_to_doc: Dict[str, JiraDocument] = None
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

        existing_links = set()
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
            if not target_key in key_to_doc:
                docs = self._jira_manager.download_bulk_issues_with_features(list(docs_to_fetch))
                key_to_doc.update({doc.issue_key: doc for doc in docs})
                not_fetched = [
                    issue_key for issue_key in docs_to_fetch if issue_key not in key_to_doc
                ]
                for issue_key in not_fetched:
                    unvisited.discard(issue_key)
                    missing_issues.add(issue_key)
                    rollbar.report_message(f"Couldn't fetch Jira issue {issue_key}", "warning")

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

        parent_doc = duplicate_graph.issue_keys_to_documents[parent_key]
        parent_data = parse_parent_description(parent_doc.body_text)

        # The set visited should now contain all issues we want to fully connect
        # The set existing_links should now contain all existing links
        all_possible_links = set()
        keys_list = sorted(list(duplicate_graph.issue_keys_to_documents.keys()))
        for i in range(0, len(keys_list) - 1):
            for j in range(i + 1, len(keys_list)):
                all_possible_links.add((keys_list[i], keys_list[j]))

        remaining_links = all_possible_links - duplicate_graph.existing_issue_links
        any_success = False
        any_failure = False
        result_list = []

        loop = get_asyncio_loop()
        future = asyncio.ensure_future(self._jira_dal.mark_duplicates_async(remaining_links))
        results = loop.run_until_complete(future)

        for (outward_end, inward_end, link_created) in results:
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
            doc
            for doc in duplicate_graph.issue_keys_to_documents.values()
            if not JiraDocument.is_group_parent(doc)
        ]
        headers = [doc.header_text for doc in children_docs]
        # Remove shake-to-report metadata and parent issue description from the descriptions
        # before sending to AI.
        descriptions = [
            strip_parent_description(extract_duolingo_metadata(doc.body_text)[0])
            for doc in children_docs
        ]
        (
            ai_summary,
            ai_description,
        ) = self._parent_summary_manager.generate_summary_and_description(headers, descriptions)
        # Prepend [Parent] to the summary so that it's clear that this is a parent issue.
        # and [Parent] not already in the summary
        if "[Parent]" not in ai_summary:
            ai_summary = f"[Parent] {ai_summary}"

        self._try_set_remote_parent(
            parent_key, ai_summary, ai_description, parent_data, most_common_feature, priority
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

        return f"{result_status}\n{result_manifest}"

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

    def populate_parent_child_issue_fields(self, issues: List[JeevesDocument]):
        """
        Sets the parent_issue and child_issues fields of JiraDocuments by getting the duplicate graph
        to determine duplicate parent or children.

        Parameters:
            issues: list of Jeeves documents
        """
        filtered_issues = [
            issue
            for issue in issues
            if JiraDocument.get_data_source_identifier() == issue.get_data_source_identifier()
            and issue.linked_duplicate_keys != []
        ]

        if not filtered_issues:
            return
        docs_to_fetch = {
            key
            for issue in filtered_issues
            for key in issue.linked_duplicate_keys + [issue.issue_key]
        }

        docs = self._jira_manager.download_bulk_issues_with_features(list(docs_to_fetch))
        key_to_doc = {doc.issue_key: doc for doc in docs}
        for issue in filtered_issues:
            duplicate_graph = self.get_duplicate_graph(
                [issue.issue_key] + issue.linked_duplicate_keys, key_to_doc=key_to_doc
            )

            if JiraDocument.is_group_parent(issue):
                issue.child_issues = sorted(
                    list(set(duplicate_graph.issue_keys_to_documents) - {issue.issue_key})
                )
            else:
                parent_issues = [
                    issue
                    for key, issue in duplicate_graph.issue_keys_to_documents.items()
                    if JiraDocument.is_group_parent(issue)
                ]
                if len(parent_issues) == 1:
                    issue.parent_issue = parent_issues[0].issue_key
                elif len(parent_issues) > 1:
                    issue.parent_issue, _ = self.resolve_multiple_parent_issues(parent_issues)
