import unittest
from unittest.mock import MagicMock, patch

import pytest

from jeeves.manager.jira_feature_manager import JiraFeatureManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient

mock_jira_client = ShakiraJiraApiClient()
mock_jira_client.get_features = MagicMock(
    return_value=["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"]
)

mock_jira_features = {
    "Area A": {
        "Team 1": {
            "Leaderboard": ["League", "*current_screen*: ldrbrd"],
            "Streak": [],
            "Stories": ["Story"],
        },
    },
    "Area B": {
        "Team 2": {
            "Kudos": ["Congrats", "High five", "High-five", "Highfive"],
        },
        "Team 3": {
            "Skill tree": ["Home"],
        },
    },
    "Area C": {
        "Team 4": {
            "Shake-to-report": [],
        },
    },
}

mock_jira_features_descriptions = {
    "Leaderboard": "Description 1",
    "Streak": "Description 2",
    "Home": "Description 3",
}

mock_substrings_to_ignore_by_term = {
    "SHAKE-TO-REPORT": ["REPORTED WITH SHAKE-TO-REPORT"],
}

mock_session_end_screen_to_feature = {
    "sessionComplete": "Lesson complete session end",
}


def test_get_features_v1():
    feature_manager = JiraFeatureManager(mock_jira_client, mock_jira_features, {}, {})
    actual_result = feature_manager.get_features_v1(["DLAA", "DLAI", "DLAW"])

    case = unittest.TestCase()
    case.assertCountEqual(
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Visual polish",
            "Lesson content / accepted translations",
            "TTS: mispronunciation",
            "TTS: missing",
            "Feature request / feedback",
            "Visemes / Mouth movements",
        ],
        actual_result,
    )


def test_get_features_by_team_and_area():
    feature_manager = JiraFeatureManager(mock_jira_client, mock_jira_features, {}, {})
    actual_result = feature_manager.get_features_by_team_and_area()

    assert actual_result == [
        {
            "area_name": "Area A",
            "teams": [
                {
                    "team_name": "Team 1",
                    "features": ["Leaderboard", "Streak", "Stories"],
                },
            ],
        },
        {
            "area_name": "Area B",
            "teams": [
                {
                    "team_name": "Team 2",
                    "features": ["Kudos"],
                },
                {
                    "team_name": "Team 3",
                    "features": ["Skill tree"],
                },
            ],
        },
        {
            "area_name": "Area C",
            "teams": [
                {
                    "team_name": "Team 4",
                    "features": ["Shake-to-report"],
                },
            ],
        },
    ]


# Feature name capitalization should match capitalization in mock_jira_features.
test_cases = [
    # feature name in summary is detected.
    (
        "Leaderboard is broken",
        "Please fix.",
        "",
        ["Leaderboard"],
        ["Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # works with feature that has a space and different capitalization in the description.
    (
        "Bug",
        "Please fix the skill tree.",
        "",
        ["Skill tree"],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Shake-to-report"],
    ),
    # synonym is detected in part of a word in description; case-insensitive.
    (
        "Bug",
        "Please fix leagues.",
        "",
        ["Leaderboard"],
        ["Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # synonym with colon, underscore, and markdown is detected in generated_description.
    (
        "Bug",
        "Please fix.",
        "*current_screen*: ldrbrd",
        ["Leaderboard"],
        ["Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # terms that appear in the "substrings to ignore" should be ignored.
    (
        "Bug",
        "Please fix\n-\nReported with shake-to-report",
        "Reported with shake-to-report",
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # terms that appear in ways other than the "substrings to ignore" should be detected.
    (
        "Bug with shake-to-report",
        "Please fix\n-\nReported with shake-to-report",
        "Reported with shake-to-report",
        ["Shake-to-report"],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree"],
    ),
    # multiple features are detected, no tie.
    (
        "League leaderboard and skill tree are broken",
        "Please fix.",
        "",
        ["Leaderboard", "Skill tree"],
        ["Streak", "Stories", "Kudos", "Shake-to-report"],
    ),
    # more than three features are detected, no tie.
    (
        "Broken",
        "Leaderboard, League, League, League. Skill tree, home, home. Streak, streak. Kudos.",
        "",
        ["Leaderboard", "Skill tree", "Streak"],
        ["Stories", "Kudos", "Shake-to-report"],
    ),
    # empty strings.
    (
        "",
        "",
        "",
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # session end screen is detected.
    (
        "",
        "",
        "some lines of text\nSession End Screen Name: sessionComplete\n\nother stuff: things",
        ["Lesson complete session end"],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # no generated description.
    (
        "",
        "",
        None,
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # mega feature is detected.
    (
        "",
        "Test",
        "some lines of text\nMEGA Information:\n- Mega course: math\n\nother stuff: things",
        ["Mega", "Music", "Math"],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # mega feature is detected with iOS generated description.
    (
        "",
        "Test",
        "*System Information*:\n*app version*: 6.213.0.4\n*MEGA Information*:\n- *Mega course*: math\n\nother stuff: things",
        ["Mega", "Music", "Math"],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
]


@pytest.mark.parametrize(
    "summary,description,generated_description,expected_suggestions,expected_others", test_cases
)
@patch(
    "jeeves.manager.jira_feature_manager._SUBSTRINGS_TO_IGNORE_BY_TERM",
    mock_substrings_to_ignore_by_term,
)
@patch(
    "jeeves.manager.jira_feature_manager._MEGA_FEATURES",
    ["Mega", "Music", "Math"],
)
def test_get_suggested_features(
    summary, description, generated_description, expected_suggestions, expected_others
):
    feature_manager = JiraFeatureManager(
        mock_jira_client,
        mock_jira_features,
        mock_jira_features_descriptions,
        mock_session_end_screen_to_feature,
    )
    actual_result = feature_manager.get_suggested_features(
        ["DLAA", "DLAI", "DLAW"], summary, description, generated_description
    )

    case = unittest.TestCase()
    case.assertEqual(expected_suggestions, actual_result["suggested_features"])
    case.assertCountEqual(expected_others, actual_result["other_features"])
    case.assertEqual(mock_jira_features_descriptions, actual_result["feature_to_description"])


def test_feature_filtering():
    mock_filtered_jira_client = ShakiraJiraApiClient()
    mock_filtered_jira_client.get_features = MagicMock(
        return_value=["Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"]
    )
    mock_filtered_jira_features = {
        "Area A": {
            "Team 1": {"Leaderboard": ["League"], "Streak": [], "Stories": ["Story"]},
        },
        "Area B": {
            "Team 2": {
                "Kudos": ["Congrats", "High five", "High-five", "Highfive"],
            },
            "Team 3": {
                "Skill tree": ["Home"],
            },
        },
    }

    feature_manager = JiraFeatureManager(
        mock_filtered_jira_client, mock_filtered_jira_features, {}, {}
    )
    case = unittest.TestCase()

    actual_result_features = feature_manager.get_features_v1(["DLAA", "DLAI", "DLAW"])
    case.assertCountEqual(
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Visual polish",
            "Lesson content / accepted translations",
            "TTS: mispronunciation",
            "TTS: missing",
            "Feature request / feedback",
            "Visemes / Mouth movements",
        ],
        actual_result_features,
    )

    actual_result_features_by_area_and_team = feature_manager.get_features_by_team_and_area()
    assert actual_result_features_by_area_and_team == [
        {
            "area_name": "Area A",
            "teams": [
                {
                    "team_name": "Team 1",
                    "features": ["Streak", "Stories"],
                },
            ],
        },
        {
            "area_name": "Area B",
            "teams": [
                {
                    "team_name": "Team 2",
                    "features": ["Kudos"],
                },
                {
                    "team_name": "Team 3",
                    "features": ["Skill tree"],
                },
            ],
        },
    ]

    actual_result_suggested_features = feature_manager.get_suggested_features(
        ["DLAA", "DLAI", "DLAW"], "", "", ""
    )
    case.assertCountEqual(
        ["Streak", "Stories", "Kudos", "Skill tree"],
        actual_result_suggested_features["other_features"],
    )
