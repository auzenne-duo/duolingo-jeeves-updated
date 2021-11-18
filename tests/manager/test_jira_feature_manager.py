import unittest

import pytest

from jeeves.manager.jira_feature_manager import JiraFeatureManager

mock_jira_features = {
    "Area A": {
        "Team 1": {"Leaderboard": ["League"], "Streak": []},
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

feature_manager = JiraFeatureManager(mock_jira_features)

# Feature name capitalization should match capitalization in mock_jira_features
test_cases = [
    # feature name in summary is detected.
    (
        "Leaderboard is broken",
        "Please fix.",
        "",
        ["Leaderboard"],
        ["Streak", "Kudos", "Skill tree"],
    ),
    # works with feature that has a space and different capitalization in the description.
    (
        "Bug",
        "Please fix the skill tree.",
        "",
        ["Skill tree"],
        ["Leaderboard", "Streak", "Kudos"],
    ),
    # synonym is detected in part of a word in generated_description; case-insensitive.
    (
        "Bug",
        "Please fix.",
        "leagues",
        ["Leaderboard"],
        ["Streak", "Kudos", "Skill tree"],
    ),
    # multiple features are detected, no tie.
    (
        "League leaderboard and skill tree are broken",
        "Please fix.",
        "",
        ["Leaderboard", "Skill tree"],
        ["Streak", "Kudos"],
    ),
    # more than three features are detected, no tie.
    (
        "Broken",
        "Leaderboard, League, League, League. Skill tree, home, home. Streak, streak. Kudos.",
        "",
        ["Leaderboard", "Skill tree", "Streak"],
        ["Kudos"],
    ),
    # empty strings.
    (
        "",
        "",
        "",
        [],
        ["Leaderboard", "Streak", "Kudos", "Skill tree"],
    ),
]


@pytest.mark.parametrize(
    "summary,description,generated_description,expected_suggestions,expected_others", test_cases
)
def test_dedup_document_batch(
    summary, description, generated_description, expected_suggestions, expected_others
):
    actual_result = feature_manager.get_suggested_features(
        summary, description, generated_description
    )

    case = unittest.TestCase()
    case.assertEqual(expected_suggestions, actual_result["suggested_features"])
    case.assertCountEqual(expected_others, actual_result["other_features"])
