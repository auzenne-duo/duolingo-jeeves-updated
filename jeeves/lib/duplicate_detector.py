"""
Functions related to duplicate detection.
Currently only applies to JIRA issues.
"""

from typing import List


from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap


def calculate_duplicates_for_JIRA_issue(
    issue_key: str, num_results: int = 5, should_filter_project: bool = False
) -> List[str]:
    """
    Given a JIRA issue key, ensure we have the corresponding document, and
    identify other documents that represent potential duplicates of the
    provided document. If requested document is not found, return an empty list.

    Parameters:
        issue_key (str): The issue key of the JIRA issue we wish to find
                         duplicates of. If this issue is not already in
                         Elasticsearch, we attempt to download it.
        num_results (int): Optional, how many results we should return
        should_filter_project (bool): Optional. If True, results will be filtered
                                      to only those with the same project as
                                      the requested document.

    Returns:
        A list of issue keys of suspected duplicate issues.
    """

    # First, determine if we already have the requested document.
    # We could do a call to count_by_arbitrary_keywords here but if we have
    # the document then we'll need to call this anyway.
    filter_results = list(ElasticDAL.filter_by_arbitrary_keywords({"issue_key.keyword": issue_key}))

    base_document = None

    # If Python had switch statements I would use one but here we are.
    # I'm explicitly checking the length of the list against 0 to emulate a
    # switch statement structure.
    if len(filter_results) == 0:
        jira_manager = IDManagerMap.get_manager_for_identifier("JIRA")
        base_document = jira_manager.download_specific_issue(issue_key)
        ElasticDAL.bulk_index_tickets([base_document.serialize_to_json(base_document)])

    elif len(filter_results) == 1:
        base_document = filter_results[0]

    else:
        # There is no way we should ever get here and if we do something
        # very broken has happened.
        raise Exception(
            f"Filtering to find issue {issue_key} somehow returned {len(filter_results)} results. Please investigate."
        )

    if not base_document:
        print(f"Requested issue with key {issue_key} could not be found.")
        return []

    return ElasticDAL.run_more_like_this_for_duplicates(
        base_document, num_desired_results=num_results, should_filter_project=should_filter_project
    )
