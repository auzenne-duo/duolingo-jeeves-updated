# TO USE:
# Export the following env vars:
# - JIRA_USERNAME: @duolingo email address.
# - JIRA_API_TOKEN: A Jira API token for your account. Can be generated from https://id.atlassian.com/manage-profile/security/api-tokens
#
# Follow the usual README steps to set up your Python environment.
#
# Example: print the keys of all Jira tickets that are reachable from DLAA-10000 or DLAA-10001:
# python3 jeeves/script/get_duplicate_graph.py DLAA-10000 DLAA-10001
#
# Uncomment lines or add to the script at the bottom to print other information

import sys

from jeeves import registry as app_registry
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver

duplicate_graph = app_registry(DuplicateGraphResolver).get_duplicate_graph(sys.argv[1:])

# prints all issue keys
print(duplicate_graph.issue_keys_to_documents.keys())

# to print keys and summaries, for example
# print([
#   f"{doc.issue_key}: {doc.header_text}" # doc is a JiraDocument object
#   for doc in duplicate_graph.issue_keys_to_documents.values()
#   ])

# to print all resolutions
# print([
#   doc.resolution # doc is a JiraDocument object
#   for doc in duplicate_graph.issue_keys_to_documents.values()
# ])
