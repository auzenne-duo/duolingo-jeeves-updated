import operator
import random
from collections import Counter
from typing import Dict, List, Optional, Union

from duolingo_base.util import registry

from jeeves.config.jira_features import (
    DEBUG_TYPE_TO_FEATURES_REGISTRY_KEY,
    JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY,
    JIRA_FEATURES_REGISTRY_KEY,
    SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY,
)
from jeeves.manager.shakira import _SHAKIRA_FEATURES_TO_SLACK_CHANNEL
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.model.custom_types import AreaWithTeamList
from jeeves.util.cleanup import extract_duolingo_metadata_and_body

_SUBSTRINGS_TO_IGNORE_BY_TERM = {
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


# Note math and music will have more than 5 features because we include the math and music features as well as the
# top suggested features for each. We limit the number of extra features to 2.
SUGGESTED_FEATURES_LIMIT = 5
EXTRA_SUGGESTED_FEATURES_LIMIT = 2

_MATH_FEATURES = [
    "Math - Generated Sessions",
    "Math - Localization",
    "Math - Match Madness",
    "Math - Puzzles & Games",
    "Math - Word Problems",
    "Math - Life Skills",
    "Math",
]
_MUSIC_FEATURES = ["Music"]


@registry.bind(
    jira_client=registry.reference(ShakiraJiraApiClient),
    features_config=registry.reference(JIRA_FEATURES_REGISTRY_KEY),
    descriptions_config=registry.reference(JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY),
    session_end_screen_to_feature=registry.reference(SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY),
    debug_type_to_features=registry.reference(DEBUG_TYPE_TO_FEATURES_REGISTRY_KEY),
)
class JiraFeatureManager:
    def __init__(
        self,
        jira_client: ShakiraJiraApiClient,
        features_config: Dict[str, Dict[str, Dict[str, List[str]]]],
        descriptions_config: Dict[str, str],
        session_end_screen_to_feature: Dict[str, str],
        debug_type_to_features: Dict[str, List[str]],
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
        self._debug_type_to_features = debug_type_to_features
        self._session_end_screen_to_feature = session_end_screen_to_feature

    def _get_feature_to_synonyms_mapping(self) -> Dict[str, List[str]]:
        """
        Based on self.jira_features_and_synonyms, which contains features and synonyms organized
        by area and team, this method returns a mapping that contains all features mapped to a list
        of their respective synonyms.
        """
        all_features_to_synonyms = {}

        for pillar in self.jira_features_and_synonyms:
            for teams_to_features in self.jira_features_and_synonyms[pillar].values():
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
                            for feature, synonyms in features_dict.items()
                            if feature in valid_features
                        ],
                    }
                    for team_name, features_dict in teams_dict.items()
                ],
            }
            for pillar_name, areas_dict in self.jira_features_and_synonyms.items()
            for area_name, teams_dict in areas_dict.items()
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

    def _get_text_suggested_features(
        self, search_text: str, valid_features: List[str]
    ) -> List[str]:
        """
        Counts the mentions of a feature in a given body of text.
        Returns a sorted and filtered list of features based on their counts.
        """
        search_text_uppercase = search_text.upper()
        feature_count = Counter()

        # Note: this counts substrings that are parts of words
        for term, feature in self._uppercase_term_to_feature.items():
            search_text_uppercase_clean = search_text_uppercase
            substrings_to_ignore = _SUBSTRINGS_TO_IGNORE_BY_TERM.get(term)
            if substrings_to_ignore is not None and len(substrings_to_ignore) > 0:
                for substring in substrings_to_ignore:
                    search_text_uppercase_clean = search_text_uppercase_clean.replace(substring, "")

            feature_count[feature] += search_text_uppercase_clean.count(term)

        sorted_features_to_counts = sorted(
            feature_count.items(), key=operator.itemgetter(1), reverse=True
        )

        return [
            feature
            for (feature, count) in sorted_features_to_counts
            if count > 0 and feature in valid_features
        ]

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
        if generated_description:
            # Remove asterisks from generated description. iOS STR includes them, but they interfere with extracting metadata
            _, duolingo_metadata = extract_duolingo_metadata_and_body(
                generated_description.replace("*", "")
            )
            mega_course = duolingo_metadata.get("mega_information", {}).get("mega_course", None)
            if mega_course == "math":
                suggested_features.extend(_MATH_FEATURES)
            elif mega_course == "music":
                suggested_features.extend(_MUSIC_FEATURES)

        for session_end_screen_label in ["Session end screen name: ", "Session End Screen Name: "]:
            if generated_description and session_end_screen_label in generated_description:
                screen_name = (
                    generated_description.split(session_end_screen_label)[1]
                    .split("\n")[0]
                    .split(" ")[0]
                )
                if screen_name in self._session_end_screen_to_feature:
                    suggested_features.append(self._session_end_screen_to_feature[screen_name])

        text_suggested_features = []

        # parse and process user input
        search_text_user_input = summary.upper()
        if description:
            search_text_user_input = search_text_user_input + "\n" + description.upper()
        feature_list_user_input = self._get_text_suggested_features(
            search_text_user_input, valid_features
        )

        # parse and process generated description
        search_text_generated_description = ""
        if generated_description:
            search_text_generated_description = generated_description.upper()
        feature_list_generated_description = self._get_text_suggested_features(
            search_text_generated_description, valid_features
        )

        # prioritize feature matches from user inputted text, then add suggestions from generated description if there is space
        text_suggested_features = feature_list_user_input[:SUGGESTED_FEATURES_LIMIT]
        available_feature_slots = SUGGESTED_FEATURES_LIMIT - len(feature_list_user_input)
        if available_feature_slots > 0:
            text_suggested_features.extend(
                feature_list_generated_description[:available_feature_slots]
            )

        if len(suggested_features) == 0:
            suggested_features = text_suggested_features
        else:
            suggested_features.extend(text_suggested_features[:EXTRA_SUGGESTED_FEATURES_LIMIT])
        suggested_features = list(set(suggested_features))  # Remove duplicates
        random.shuffle(suggested_features)

        other_features = [
            feature for feature in valid_features if feature not in suggested_features
        ]

        return {
            "suggested_features": suggested_features,
            "other_features": other_features,
            "debug_type_to_features": self._debug_type_to_features,
            "feature_to_description": self._feature_to_description,
        }
