"""
Makes sure that all features in the jira_features.py config exist in the necessary projects on JIRA.

Requires the env vars SHAKIRA_JIRA_USERNAME_WEB and SHAKIRA_JIRA_API_TOKEN_WEB to be set.
"""

import sys

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.manager.shakira_jira import ShakiraJiraApiClient

_PROJECTS = ["DLAA", "DLAI", "DLAW"]


if __name__ == "__main__":
    apply_registry()
    try:
        jira_client = app_registry(ShakiraJiraApiClient)

        required_features = set()
        for teams_to_features in JIRA_FEATURES.values():
            for features_to_synonyms in teams_to_features.values():
                required_features.update(features_to_synonyms.keys())

        features_on_jira = jira_client.get_features(_PROJECTS)
        features_to_add = [
            required_feature
            for required_feature in required_features
            if required_feature not in features_on_jira
        ]

        if len(features_to_add) == 0:
            sys.exit()

        print("Identified features to create")
        print(features_to_add)

        issuetypes = jira_client.get_issuetype_metadata(_PROJECTS)
        feature_field_keys = {
            issuetype.feature_field_key()
            for issuetype in issuetypes
            if issuetype.feature_field_key() is not None
        }

        for field_key in feature_field_keys:
            context_ids = jira_client.get_contexts(field_key)

            for context_id in context_ids:
                jira_client.create_options_for_field(field_key, context_id, features_to_add)
    finally:
        close_registry()
