import unittest
from unittest.mock import MagicMock, patch

import pytest

from jeeves.dal.employees import EmployeesDAL
from jeeves.manager.jira_feature_manager import JiraFeatureManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient

mock_jira_client = ShakiraJiraApiClient(EmployeesDAL())
mock_jira_client.get_features = MagicMock(
    return_value=[
        "Leaderboard",
        "Streak",
        "Stories",
        "Kudos",
        "Skill tree",
        "Shake-to-report",
        "Music - Instrument Mode",
        "Music - Practice Tab",
    ]
)

mock_jira_leaderboard_keywords = ["League", "*current_screen*: ldrbrd"]
mock_jira_kudos_keywords = ["Congrats", "High five", "High-five", "Highfive"]
mock_jira_features = {
    "Pillal A": {
        "Area A": {
            "Team 1": {
                "Leaderboard": mock_jira_leaderboard_keywords,
                "Streak": [],
                "Stories": ["Story"],
            },
        },
    },
    "Pillar B": {
        "Area B": {
            "Team 2": {
                "Kudos": mock_jira_kudos_keywords,
            },
            "Team 3": {
                "Skill tree": ["Home"],
            },
        },
    },
    "Pillar C": {
        "Area C": {
            "Team 4": {
                "Shake-to-report": [],
            },
        },
    },
    "Pillar D": {
        "Area D": {
            "Team 5": {
                "Music - Instrument Mode": ["pitch"],
                "Music - Practice Tab": ["music library"],
            },
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

mock_debug_type_to_features = {"Max features": []}


def test_get_features_v1():
    feature_manager = JiraFeatureManager(
        mock_jira_client, mock_jira_features, {}, {}, mock_debug_type_to_features
    )
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
            "Design quality",
            "Lesson content / accepted translations",
            "Feature request / feedback",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
        actual_result,
    )


def test_get_features_by_team_and_area():
    feature_manager = JiraFeatureManager(
        mock_jira_client, mock_jira_features, {}, {}, mock_debug_type_to_features
    )
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
        {
            "area_name": "Area D",
            "teams": [
                {
                    "team_name": "Team 5",
                    "features": ["Music - Instrument Mode", "Music - Practice Tab"],
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
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # works with feature that has a space and different capitalization in the description.
    (
        "Bug",
        "Please fix the skill tree.",
        "",
        ["Skill tree"],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # synonym is detected in part of a word in description; case-insensitive.
    (
        "Bug",
        "Please fix leagues.",
        "",
        ["Leaderboard"],
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # synonym with colon, underscore, and markdown is detected in generated_description.
    (
        "Bug",
        "Please fix.",
        "*current_screen*: ldrbrd",
        ["Leaderboard"],
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # terms that appear in the "substrings to ignore" should be ignored.
    (
        "Bug",
        "Please fix\n-\nReported with shake-to-report",
        "Reported with shake-to-report",
        [],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # terms that appear in ways other than the "substrings to ignore" should be detected.
    (
        "Bug with shake-to-report",
        "Please fix\n-\nReported with shake-to-report",
        "Reported with shake-to-report",
        ["Shake-to-report"],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # multiple features are detected, no tie.
    (
        "League leaderboard and skill tree are broken",
        "Please fix.",
        "",
        ["Leaderboard", "Skill tree"],
        [
            "Streak",
            "Stories",
            "Kudos",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # more than three features are detected, no tie.
    (
        "Broken",
        "Leaderboard, League, League, League. Skill tree, home, home. Streak, streak. Kudos.",
        "",
        ["Leaderboard", "Skill tree", "Streak", "Kudos"],
        ["Stories", "Shake-to-report", "Music - Instrument Mode", "Music - Practice Tab"],
    ),
    # empty strings.
    (
        "",
        "",
        "",
        [],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # session end screen is detected.
    (
        "",
        "",
        "some lines of text\nSession End Screen Name: sessionComplete\n\nother stuff: things",
        ["Lesson complete session end"],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # no generated description.
    (
        "",
        "",
        None,
        [],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # math feature is detected.
    (
        "",
        "Test",
        "some lines of text\nMEGA Information:\n- Mega course: math\n\nother stuff: things",
        ["Math - Generated Sessions", "Math - Localization", "Math"],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # math feature is detected with iOS generated description.
    (
        "",
        "Test",
        "*System Information*:\n*app version*: 6.213.0.4\n*MEGA Information*:\n- *Mega course*: math\n\nother stuff: things",
        ["Math - Generated Sessions", "Math - Localization", "Math"],
        [
            "Leaderboard",
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
    ),
    # prioritize user input over generated description.
    (
        "Pitch",
        "music library home streak stories",
        "*System Information*:\n*app version*: 6.213.0.4\n*MEGA Information*:\n- *Mega course*: music\n\nother stuff: "
        + "".join(mock_jira_leaderboard_keywords)
        + "".join(mock_jira_kudos_keywords),
        ["Music - Instrument Mode", "Music - Practice Tab", "Streak", "Skill tree", "Stories"],
        ["Leaderboard", "Kudos", "Shake-to-report"],
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
    "jeeves.manager.jira_feature_manager._MATH_FEATURES",
    [
        "Math - Generated Sessions",
        "Math - Localization",
        "Math",
    ],
)
def test_get_suggested_features(
    summary, description, generated_description, expected_suggestions, expected_others
):
    feature_manager = JiraFeatureManager(
        mock_jira_client,
        mock_jira_features,
        mock_jira_features_descriptions,
        mock_session_end_screen_to_feature,
        mock_debug_type_to_features,
    )
    actual_result = feature_manager.get_suggested_features(
        ["DLAA", "DLAI", "DLAW"], summary, description, generated_description
    )

    case = unittest.TestCase()
    case.assertEqual(sorted(expected_suggestions), sorted(actual_result["suggested_features"]))
    case.assertCountEqual(sorted(expected_others), sorted(actual_result["other_features"]))
    case.assertEqual(mock_jira_features_descriptions, actual_result["feature_to_description"])


def test_feature_filtering():
    mock_filtered_jira_client = ShakiraJiraApiClient(EmployeesDAL())
    mock_filtered_jira_client.get_features = MagicMock(
        return_value=[
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Shake-to-report",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ]
    )
    mock_filtered_jira_features = {
        "Pillar A": {
            "Area A": {
                "Team 1": {"Leaderboard": ["League"], "Streak": [], "Stories": ["Story"]},
            },
        },
        "Pillar B": {
            "Area B": {
                "Team 2": {
                    "Kudos": ["Congrats", "High five", "High-five", "Highfive"],
                },
                "Team 3": {
                    "Skill tree": ["Home"],
                },
            },
        },
        "Pillar C": {
            "Area D": {
                "Team 5": {
                    "Music - Instrument Mode": ["pitch"],
                    "Music - Practice Tab": ["music library"],
                },
            },
        },
    }

    feature_manager = JiraFeatureManager(
        mock_filtered_jira_client, mock_filtered_jira_features, {}, {}, mock_debug_type_to_features
    )
    case = unittest.TestCase()

    actual_result_features = feature_manager.get_features_v1(["DLAA", "DLAI", "DLAW"])
    case.assertCountEqual(
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Design quality",
            "Lesson content / accepted translations",
            "Feature request / feedback",
            "Music - Instrument Mode",
            "Music - Practice Tab",
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
        {
            "area_name": "Area D",
            "teams": [
                {
                    "team_name": "Team 5",
                    "features": ["Music - Instrument Mode", "Music - Practice Tab"],
                },
            ],
        },
    ]

    actual_result_suggested_features = feature_manager.get_suggested_features(
        ["DLAA", "DLAI", "DLAW"], "", "", ""
    )
    case.assertCountEqual(
        [
            "Streak",
            "Stories",
            "Kudos",
            "Skill tree",
            "Music - Instrument Mode",
            "Music - Practice Tab",
        ],
        actual_result_suggested_features["other_features"],
    )
