import os
import sys
import time

import duo_logging.legacy as rollbar

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.jira_manager import JiraManager

_DEFAULT_REFRESH_WINDOW_HOURS = 1
_REFRESH_HOURS = os.environ.get("REFRESH_HOURS", _DEFAULT_REFRESH_WINDOW_HOURS)


def refresh_updated_jira_tickets() -> None:
    """
    This task fetches Jira tickets that have been updated since the last checkpoint
    and re-indexes them into opensearch

    For tickets we determine
    - the duplicate graph and store the child/parent issue keys.
    - if a ticket is related to a dev (non-Bug) ticket
    """
    print("starting sync of jira tickets")
    jira_issues = JiraManager.get_jira_issues_since(f"-{_REFRESH_HOURS}h")
    print(f"refreshing {len(jira_issues)} tickets")
    # assign parent and child fields
    app_registry(DuplicateGraphResolver).resolve_duplicate_graphs(jira_issues)

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
