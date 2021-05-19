"""
Functions related to making duplicate issues have a maximum degree of separation
of one. This code is in its own file because putting it anywhere else wouldn't
make sense or would cause a circular dependency.
"""

from typing import List

from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.manager.jira_manager import JiraManager


class DuplicateGraphResolver:
    @staticmethod
    def connect_duplicates_remote(issue_keys: List[str]) -> str:
        """
        Marks a new issue as a duplicate of each of several existing issues on
        Jira, and ensures that any issues with a finite degree of separation
        via duplicate relation from any of the provided issues become marked
        as duplicates such that the maximum degree of separation via duplicate
        relation is 1.

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

        Parameters:
            existing_keys: A list of issue keys of issues that we want to
                           include in our fully duplicate graph. All duplicates
                           of these issues will also be included in the graph,
                           as well as all duplicates of those issues, and so on.

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
            we consider the operation a success.
        """

        # I'm writing this from scratch but this is probably just Dijkstra's?
        existing_links = set()
        visited = set()
        unvisited = set(issue_keys)
        while unvisited:
            target_key = unvisited.pop()
            target_issue = ElasticDAL.ensure_specific_jira_issue(target_key)
            for existing_duplicate in target_issue.linked_duplicate_keys:
                if existing_duplicate not in visited:
                    unvisited.add(existing_duplicate)
                existing_pair = tuple(sorted([target_key, existing_duplicate]))
                existing_links.add(existing_pair)
            visited.add(target_key)

        # The set visited should now contain all issues we want to fully connect
        # The set existing_links should now contain all existing links
        all_possible_links = set()
        keys_list = sorted(list(visited))
        for i in range(0, len(keys_list) - 1):
            for j in range(i + 1, len(keys_list)):
                all_possible_links.add((keys_list[i], keys_list[j]))

        remaining_links = all_possible_links - existing_links
        any_success = False
        any_failure = False
        result_list = []
        for (outward_end, inward_end) in remaining_links:
            link_created = JiraManager.mark_duplicate_remote(outward_end, inward_end)
            if link_created:
                any_success = True
                result_list.append(f"S {outward_end} {inward_end}\n")
            else:
                any_failure = True
                result_list.append(f"F {outward_end} {inward_end}\n")

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
