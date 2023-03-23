import operator
from collections import Counter
from typing import Dict, List, Optional, Union

from duolingo_base.util import registry

from jeeves.config.jira_features import (
    JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY,
    JIRA_FEATURES_REGISTRY_KEY,
    SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY,
)
from jeeves.manager.shakira import _SHAKIRA_FEATURES_TO_SLACK_CHANNEL
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.model.custom_types import AreaWithTeamList

SUBSTRINGS_TO_IGNORE_BY_TERM = {
    "ADS": ["READS"],
    "COURSE": ["COURSE: "],
    "EDDY": ["FREDDY"],
    "LEVEL": ["API LEVEL: ", "LEVEL NUMBER: "],
    "LIN": ["DUOLINGO", "LINE", "LINK"],
    "MAX": [
        "IPHONE 11 PRO MAX",
        "IPHONE 12 PRO MAX",
        "IPHONE 13 PRO MAX",
        "IPHONE 14 PRO MAX",
        "IPHONE 15 PRO MAX",
        "IPHONE XS MAX",
        "MAXIMUM",
        "MAXTOWER",
    ],
    "PLUS": ["ONEPLUS"],
    "SKILL TREE": ["SKILL TREE ID: "],
    "SHAKE-TO-REPORT": [
        "REPORTED WITH SHAKE-TO-REPORT",
        "REPORTED VIA BIRD'S EYE, SHAKE-TO-REPORT",
    ],
    "STORY": ["FULLSTORY"],
    "TREE": ["SKILL TREE ID: "],
    "USERNAME": ["USERNAME: "],
}

SUBSTRINGS_TO_IGNORE_REGISTRY_KEY = "substrings_to_ignore_by_term"


@registry.bind(
    jira_client=registry.reference(ShakiraJiraApiClient),
    features_config=registry.reference(JIRA_FEATURES_REGISTRY_KEY),
    descriptions_config=registry.reference(JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY),
    session_end_screen_to_feature=registry.reference(SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY),
    substrings_to_ignore_by_term=registry.reference(SUBSTRINGS_TO_IGNORE_REGISTRY_KEY),
)
class JiraFeatureManager:
    def __init__(
        self,
        jira_client: ShakiraJiraApiClient,
        features_config: Dict[str, Dict[str, Dict[str, List[str]]]],
        descriptions_config: Dict[str, str],
        session_end_screen_to_feature: Dict[str, str],
        substrings_to_ignore_by_term: Dict[str, List[str]],
    ):
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

        descriptions_config should be of the form:
        {
            "Feature": "Description",
        }
        """
        self._jira_client = jira_client
        self.jira_features_and_synonyms = features_config
        self._feature_to_synonyms = self._get_feature_to_synonyms_mapping()
        self._uppercase_term_to_feature = self._get_uppercase_term_to_feature_mapping()
        self._feature_to_description = descriptions_config
        self._session_end_screen_to_feature = session_end_screen_to_feature
        self._substrings_to_ignore_by_term = substrings_to_ignore_by_term

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

    def _get_valid_features(self, projects: Union[str, List[str]]) -> List[str]:
        """
        Returns a list of features that exist in both the specific Jira project and in the config.
        """
        features_on_jira = self._jira_client.get_features(projects) or []
        features_in_config = self._feature_to_synonyms.keys()
        return list(set(features_on_jira) & set(features_in_config))

    def get_features_v1(self, projects: Union[str, List[str]]) -> List[str]:
        valid_jira_features = self._get_valid_features(projects)
        slack_report_features = _SHAKIRA_FEATURES_TO_SLACK_CHANNEL.keys()
        return list(set(valid_jira_features).union(set(slack_report_features)))

    def get_features_by_team_and_area(
        self,
    ) -> List[AreaWithTeamList]:
        """
        Returns a list of features organized by area and team.
        """
        valid_features = self._get_valid_features(["DLAA", "DLAI", "DLAW"])
        areasWithTeams = [
            {
                "area_name": area_name,
                "teams": [
                    {
                        "team_name": team_name,
                        "features": [
                            feature
                            for (feature, synonyms) in features_dict.items()
                            if feature in valid_features
                        ],
                    }
                    for (team_name, features_dict) in teams_dict.items()
                ],
            }
            for (area_name, teams_dict) in self.jira_features_and_synonyms.items()
        ]

        areasWithTeams = [
            {
                "area_name": areaWithTeams["area_name"],
                "teams": list(
                    filter(
                        lambda teamWithFeatures: len(teamWithFeatures["features"]) > 0,
                        areaWithTeams["teams"],
                    )
                ),
            }
            for areaWithTeams in areasWithTeams
        ]

        areasWithTeams = list(
            filter(lambda areaWithTeams: len(areaWithTeams["teams"]) > 0, areasWithTeams)
        )

        return areasWithTeams

    def get_suggested_features(
        self,
        projects: Union[str, List[str]],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
    ) -> Dict[str, List[str]]:
        """
        Suggests features that could be attached to an issue.

        parameters:
            projects: e.g. DLAA, DLAI, DLAW
            summary: Rougly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.

        returns: Dict[str, List[str]] containing the following fields:
            - "suggested_features": a list of up to three suggested features for the issue.
            - "other_features": a list of other features (i.e. ones not included in the suggested_features list).
        """
        # Implement fingerprint if we need better performance

        valid_features = self._get_valid_features(projects)

        suggested_features = []
        for session_end_screen_label in ["Session end screen name: ", "Session End Screen Name: "]:
            if generated_description and session_end_screen_label in generated_description:
                screen_name = (
                    generated_description.split(session_end_screen_label)[1]
                    .split("\n")[0]
                    .split(" ")[0]
                )
                if screen_name in self._session_end_screen_to_feature:
                    suggested_features.append(self._session_end_screen_to_feature[screen_name])

        if not suggested_features:
            search_text_uppercase = summary.upper()
            if description:
                search_text_uppercase = search_text_uppercase + "\n" + description.upper()
            if generated_description:
                search_text_uppercase = search_text_uppercase + "\n" + generated_description.upper()

            feature_count = Counter()
            # Note: this counts substrings that are parts of words
            for term, feature in self._uppercase_term_to_feature.items():
                search_text_uppercase_clean = search_text_uppercase
                substrings_to_ignore = self._substrings_to_ignore_by_term.get(term)
                if substrings_to_ignore is not None and len(substrings_to_ignore) > 0:
                    for substring in substrings_to_ignore:
                        search_text_uppercase_clean = search_text_uppercase_clean.replace(
                            substring, ""
                        )

                feature_count[feature] += search_text_uppercase_clean.count(term)

            sorted_features_to_counts = sorted(
                feature_count.items(), key=operator.itemgetter(1), reverse=True
            )

            sorted_and_filtered_features = [
                feature
                for (feature, count) in sorted_features_to_counts
                if count > 0 and feature in valid_features
            ]
            suggested_features = sorted_and_filtered_features[:3]
        other_features = [
            feature for feature in valid_features if feature not in suggested_features
        ]

        return {
            "suggested_features": suggested_features,
            "other_features": other_features,
            "feature_to_description": self._feature_to_description,
        }
