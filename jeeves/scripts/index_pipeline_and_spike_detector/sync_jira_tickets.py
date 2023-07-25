import os
import sys
import time
from typing import Dict, List

import rollbar
from duolingo_base.config import Config

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, JIRA_PROJECTS
from jeeves.dal.jira_dal import JiraDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.util.quality_report_util import is_jira_issue_resolved

_DEFAULT_REFRESH_WINDOW_HOURS = 1
_REFRESH_HOURS = os.environ.get("REFRESH_HOURS", _DEFAULT_REFRESH_WINDOW_HOURS)
_INWARD_ISSUE_LINK_KEY = "inwardIssue"
_OUTWARD_ISSUE_LINK_KEY = "outwardIssue"

config = Config.load_config()
config.apply_logging()
config.apply_rollbar()


def search_for_issues() -> List[JiraDocument]:
    """
    Yields bugs that have been updated in the last _REFRESH_HOURS

    Returns:
        List of JiraDocuments
    """
    # Need to get the feature field key so that field is set in Jira documents
    JiraManager.get_feature_field()

    max_results_per_page = 100
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND updated >= -{_REFRESH_HOURS}h "
        + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
        + f"ORDER BY updated asc"
    )

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
    }

    issues = []
    for i, issue in enumerate(JiraDAL.paginate_search_issues(url_params)):
        jira_doc = JiraDocument.deserialize_from_external_json(issue)
        issues.append(jira_doc)
        if i % 500 == 0:
            print(f"Paginating jira issues; at {i}")
    print("finished paginating")
    return issues


def resolve_duplicate_graphs(
    jira_issues: List[JiraDocument],
) -> Dict[str, JiraDocument]:
    """
    Params:
        jira_issues: list of JiraDocuments

    Returns:
        a mapping from issue key to Jira document

    For each jira issue we resolve the duplicate graph and determine a representative of each dupe graph
    The rep will be the parent of the graph if it exists. If there is only one issue, then that issue is
    the rep. Otherwise, if there is at least one open issue, some open issue is used as the rep. Finally
    if all issues are done, then any issue that was not closed as a Duplicate is used.

    Assigns parent_issue and child_issue attributes for jira documents
    """

    # Fetch all directly linked duplicates in batch and compile a mapping from issue key to issue
    key_to_issue_map = {issue.issue_key: issue for issue in jira_issues}
    issues_to_fetch = {
        key
        for issue in jira_issues
        for key in issue.linked_duplicate_keys
        if not key in key_to_issue_map
    }

    downloaded_issues = IDManagerMap.get_manager_for_identifier(
        "JIRA"
    ).download_bulk_issues_with_features(list(issues_to_fetch))
    key_to_issue_map.update({issue.issue_key: issue for issue in downloaded_issues})

    # For each issue determine the duplicate graph and choose a representative.
    visited_issues = set()
    for issue in jira_issues:
        if issue.issue_key in visited_issues:
            continue
        duplicate_graph = app_registry(DuplicateGraphResolver).get_duplicate_graph(
            [issue.issue_key], key_to_doc=key_to_issue_map
        )
        duplicate_graph_issues = list(duplicate_graph.issue_keys_to_documents.values())
        visited_issues.update(duplicate_graph.issue_keys_to_documents.keys())
        parent_issues = [
            issue for issue in duplicate_graph_issues if JiraDocument.is_group_parent(issue)
        ]

        if len(parent_issues) == 1:
            # use the parent issue as the representative
            parent_issue = parent_issues[0]
        elif len(parent_issues) > 1:
            # check to see if any parent issue is unresolved, and if so use that as the representative
            for potential_parent_issue in parent_issues:
                if not is_jira_issue_resolved(potential_parent_issue):
                    parent_issue = potential_parent_issue
                    break
            else:
                # if all parent issues are resolved, use an arbitrary parent issue as the representative
                parent_issue = potential_parent_issue
        elif len(duplicate_graph_issues) == 1:
            # if there is only one issue in the graph, use that as the representative
            parent_issue = issue
        else:
            # if there are no parent issues, use an open issue as the representative
            open_issues = [
                issue for issue in duplicate_graph_issues if not is_jira_issue_resolved(issue)
            ]
            if len(open_issues) > 0:
                parent_issue = open_issues[0]
            else:
                # if all issues are closed, use any issue that was not closed as a duplicate
                non_dupes = [
                    issue for issue in duplicate_graph_issues if issue.resolution != "Duplicate"
                ]
                parent_issue = duplicate_graph_issues[0] if non_dupes == [] else non_dupes[0]

        # set parent and child issues attributes
        parent_issue.child_issues = [
            i.issue_key for i in duplicate_graph_issues if i.issue_key != parent_issue.issue_key
        ]
        for child_issue in duplicate_graph_issues:
            if child_issue == parent_issue:
                continue
            child_issue.parent_issue = parent_issue.issue_key

    return key_to_issue_map


def update_dev_related_issues(
    jira_docs: List[JiraDocument], key_to_issue_map: Dict[str, JiraDocument]
) -> None:
    """
    Updates is_dev_related property for issues that are related to a development ticket,
    where a dev ticket is a non-bug ticket.

    Params:
        issue_keys: list of issue keys
        key_to_issue_map: mapping from issue key to JiraDocument
    """
    issues_to_fetch = set()
    for jira_doc in jira_docs:
        for link in jira_doc.issue_links:
            if "Relates" in link["type"]["name"]:
                if _INWARD_ISSUE_LINK_KEY in link:
                    issues_to_fetch.add(link[_INWARD_ISSUE_LINK_KEY]["key"])
                if _OUTWARD_ISSUE_LINK_KEY in link:
                    issues_to_fetch.add(link[_OUTWARD_ISSUE_LINK_KEY]["key"])

    downloaded_issues = IDManagerMap.get_manager_for_identifier(
        "JIRA"
    ).download_bulk_issues_with_features(list(issues_to_fetch))
    key_to_issue_map.update({issue.issue_key: issue for issue in downloaded_issues})

    for jira_doc in jira_docs:
        is_dev_related = False
        for link in jira_doc.issue_links:
            if "Relates" in link["type"]["name"]:
                issue = None
                if _INWARD_ISSUE_LINK_KEY in link:
                    issue = key_to_issue_map.get(link[_INWARD_ISSUE_LINK_KEY]["key"])
                if _OUTWARD_ISSUE_LINK_KEY in link:
                    issue = key_to_issue_map.get(link[_OUTWARD_ISSUE_LINK_KEY]["key"])
                if issue is None:
                    print("missing linked issue", link)
                    continue
                if issue.issue_type != "Bug":
                    is_dev_related = True
                    break
        jira_doc.is_dev_related = is_dev_related


def refresh_updated_jira_tickets() -> None:
    """
    This task fetches Jira tickets that have been updated since the last checkpoint
    and re-indexes them into opensearch

    For tickets we determine
    - the duplicate graph and store the child/parent issue keys.
    - if a ticket is related to a dev (non-Bug) ticket
    """
    print("starting sync of jira tickets")
    jira_issues = search_for_issues()
    print(f"refreshing {len(jira_issues)} tickets")
    key_to_issue_map = resolve_duplicate_graphs(jira_issues)
    update_dev_related_issues(jira_issues, key_to_issue_map)

    # if embeddings already exist, we don't want to overwrite them
    # so we will check if the tickets already have embeddings in opensearch
    print("checking if tickets already have embeddings")
    opensearch_query_batch_size = 100
    for index in range(0, len(jira_issues), opensearch_query_batch_size):
        issues = jira_issues[index : index + opensearch_query_batch_size]
        query = {
            "size": len(issues),
            "query": {"terms": {"issue_key.keyword": [issue.issue_key for issue in issues]}},
        }

        indexed_issues = app_registry(OpenSearchDAL).execute_arbitrary_query(query)

        if not indexed_issues:
            continue
        indexed_key_to_issue_map = {i.issue_key: i for i in indexed_issues}
        for issue in issues:
            if issue.issue_key in indexed_key_to_issue_map:
                issue.embeddings = indexed_key_to_issue_map[issue.issue_key].embeddings
    print("indexing synced jira tickets")
    app_registry(OpenSearchDAL).bulk_index_tickets(jira_issues, populate_embeddings=False)


if __name__ == "__main__":
    apply_registry()
    try:
        start = time.time()
        refresh_updated_jira_tickets()
        print("=" * 100)
        print(f"Jira sync done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()
