"""
Functions related to making duplicate issues have a maximum degree of separation
of one. This code is in its own file because putting it anywhere else wouldn't
make sense or would cause a circular dependency.
"""

from collections import defaultdict
from typing import List

from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph


class DuplicateGraphResolver:
    @staticmethod
    def _update_local_links_from_manifest(manifest: List[str]) -> None:
        """
        Given a list of manifest results (see connect_duplicates_remote),
        modify our locally stored information to include the links successfully
        created according to the manifest.

        Parameters:
            manifest: A results manifest generated in connect_duplicates_remote
        """

        issues_to_link = defaultdict(list)
        for line in manifest:
            line_items = line.strip().split(" ")
            if line_items[0] != "S":
                continue
            # Add 1 to 2 and 2 to 1
            for i in range(2):
                issues_to_link[line_items[i + 1]].append(line_items[2 - i])

        updated_docs = []
        docs = [ElasticDAL.find_jira_by_key(key) for key in issues_to_link]
        for target_doc in docs:
            target_json = target_doc.serialize_to_json(target_doc)
            for key in issues_to_link[target_doc.issue_key]:
                target_json["linked_duplicate_keys"].append(key)
            updated_docs.append(JiraDocument.deserialize_from_internal_json(target_json))
        ElasticDAL.bulk_index_tickets(updated_docs)

    @staticmethod
    def get_duplicate_graph(issue_keys: List[str]) -> JiraDuplicateGraph:
        """
        Takes issue key(s) and returns information about the set of reachable issues in the graph
        of duplicates.

        Returns a dict with the following keys:
        - keys: a Set[str] of issue keys in the duplicate graph.
        - existing_links: a Set[Tuple[str]] of links that already exist between issues in the graph.
        """

        existing_links = set()
        visited = set()
        unvisited = set(issue_keys)
        while unvisited:
            target_key = unvisited.pop()
            target_issue = ElasticDAL.ensure_specific_jira_issue(target_key, force_download=True)
            for existing_duplicate in target_issue.linked_duplicate_keys:
                if existing_duplicate not in visited:
                    unvisited.add(existing_duplicate)
                existing_pair = tuple(sorted([target_key, existing_duplicate]))
                existing_links.add(existing_pair)
            visited.add(target_key)
        return JiraDuplicateGraph(issue_keys=visited, existing_issue_links=existing_links)

    @staticmethod
    def connect_duplicates_remote(issue_keys: List[str]) -> str:
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
        Elasticsearch to minimize how many potentially expensive network calls
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
        documents are found, an exception will be thrown.

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
        duplicate_graph = DuplicateGraphResolver.get_duplicate_graph(issue_keys)

        doc_reps = [
            ElasticDAL.ensure_specific_jira_issue(key) for key in duplicate_graph.issue_keys
        ]
        group_parents = [doc for doc in doc_reps if doc and JiraDocument.is_group_parent(doc)]

        parent_key = None
        if len(group_parents) == 1:
            parent_key = group_parents[0].issue_key
        elif len(group_parents) == 0:
            parent_project = doc_reps[0].project
            combined_headers = "|".join([doc.header_text for doc in doc_reps])
            # Jira issue titles have a hard 255 character limit
            parent_header_text = f"PARENT FOR [{combined_headers}]"[:255]
            parent_key = JiraManager.upload_template_parent_issue(
                parent_project, parent_header_text
            )
            duplicate_graph.issue_keys.add(parent_key)
        else:
            raise Exception(
                f"Attempting to fully connect keys [{', '.join(issue_keys)}] into a single group found returned {len(group_parents)} parent issues; please investigate."
            )

        parent_doc = ElasticDAL.ensure_specific_jira_issue(parent_key)
        parent_data = JiraManager.parse_parent_description(parent_doc.body_text)

        # The set visited should now contain all issues we want to fully connect
        # The set existing_links should now contain all existing links
        all_possible_links = set()
        keys_list = sorted(list(duplicate_graph.issue_keys))
        for i in range(0, len(keys_list) - 1):
            for j in range(i + 1, len(keys_list)):
                all_possible_links.add((keys_list[i], keys_list[j]))

        remaining_links = all_possible_links - duplicate_graph.existing_issue_links
        any_success = False
        any_failure = False
        result_list = []
        for (outward_end, inward_end) in remaining_links:
            # We don't need to edit our documents here because the changes will
            # get pulled in from Jira later anyway.
            link_created = JiraManager.try_mark_duplicate_remote(outward_end, inward_end)
            if link_created:
                any_success = True
                result_list.append(f"S {outward_end} {inward_end}\n")
                if outward_end == parent_key:
                    child_issue = ElasticDAL.find_jira_by_key(inward_end)
                    JiraManager.update_parent_data_from_child(parent_data, child_issue)
                elif inward_end == parent_key:
                    child_issue = ElasticDAL.find_jira_by_key(outward_end)
                    JiraManager.update_parent_data_from_child(parent_data, child_issue)
            else:
                any_failure = True
                result_list.append(f"F {outward_end} {inward_end}\n")

        JiraManager.try_set_remote_parent_body(parent_key, parent_data)
        ElasticDAL.ensure_specific_jira_issue(parent_key, force_download=True)
        DuplicateGraphResolver._update_local_links_from_manifest(result_list)

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
