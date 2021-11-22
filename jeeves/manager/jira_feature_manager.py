import operator
from typing import Dict, List, Optional

from jeeves.model.custom_types import JSON
from jeeves.util.cleanup import extract_duolingo_metadata


class JiraFeatureManager:
    def __init__(self, features_config: Dict[str, Dict[str, Dict[str, List[str]]]]):
        """
        Note: the features and synonyms provided in features_config are assumed to be unique, ie
        no synonym or feature name is associated with more than one feature.

        features_config should be of the form:
        {
            "Area": {
                "Team": {
                    "Feature": ["Synonym"],
                },
            },
        }
        """
        self.jira_features_and_synonyms = features_config
        self._feature_to_synonyms = self._get_feature_to_synonyms_mapping()
        self._uppercase_term_to_feature = self._get_uppercase_term_to_feature_mapping()

    def _get_feature_to_synonyms_mapping(self) -> Dict[str, List[str]]:
        """
        Based on self.jira_features_and_synonyms, which contains features and synonyms organized
        by area and team, this method returns a mapping that contains all features mapped to a list
        of their respective synonyms.
        """
        all_features_to_synonyms = {}

        for teams_to_features in self.jira_features_and_synonyms.values():
            for features_to_synonyms in teams_to_features.values():
                all_features_to_synonyms.update(features_to_synonyms)

        return all_features_to_synonyms

    def _get_uppercase_term_to_feature_mapping(self) -> Dict[str, str]:
        """
        Based on self._feature_to_synonyms, which contains all features mapped to a list of their
        respective synonyms, this method returns a mapping from search terms (all uppercase) to the
        feature that each search term is associated with.
        """
        uppercase_term_to_feature = {}

        for feature, synonyms in self._feature_to_synonyms.items():
            uppercase_term_to_feature[feature.upper()] = feature
            for synonym in synonyms:
                uppercase_term_to_feature[synonym.upper()] = feature

        return uppercase_term_to_feature

    @staticmethod
    def _get_leaf_values(json: JSON) -> str:
        if isinstance(json, str):
            return json
        if isinstance(json, list):
            return ",".join(json)
        if isinstance(json, dict):
            res = ""
            for value in json.values():
                res = res + JiraFeatureManager._get_leaf_values(value) + "\n"
            return res

    def get_suggested_features(
        self,
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
    ) -> Dict[str, List[str]]:
        """
        Suggests features that could be attached to an issue.

        parameters:
            summary: Rougly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.

        returns: Dict[str, List[str]] containing the following fields:
            - "suggested_features": a list of up to three suggested features for the issue.
            - "other_features": a list of other features (i.e. ones not included in the suggested_features list).
        """
        # Implement fingerprint if we need better performance

        search_text_uppercase = summary.upper()
        if description:
            search_text_uppercase = search_text_uppercase + "\n" + description.upper()
        if generated_description:
            _, metadata = extract_duolingo_metadata(generated_description)
            if metadata:
                metadata.pop("raw")
            search_text_uppercase = (
                search_text_uppercase + "\n" + JiraFeatureManager._get_leaf_values(metadata).upper()
            )

        search_text_uppercase = search_text_uppercase.replace("REPORTED WITH SHAKE-TO-REPORT", "")
        search_text_uppercase = search_text_uppercase.replace("FULLSTORY", "")

        feature_count = {}
        # Note: this counts substrings that are parts of words
        for term, feature in self._uppercase_term_to_feature.items():
            if feature in feature_count:
                feature_count[feature] = feature_count[feature] + search_text_uppercase.count(term)
            else:
                feature_count[feature] = search_text_uppercase.count(term)

        sorted_features_to_counts = sorted(
            feature_count.items(), key=operator.itemgetter(1), reverse=True
        )
        sorted_features = [feature for (feature, count) in sorted_features_to_counts if count > 0]
        suggested_features = sorted_features[:3]
        other_features = [
            feature
            for feature in self._feature_to_synonyms.keys()  # pylint: disable=consider-iterating-dictionary
            if feature not in suggested_features
        ]

        return {
            "suggested_features": suggested_features,
            "other_features": other_features,
        }
