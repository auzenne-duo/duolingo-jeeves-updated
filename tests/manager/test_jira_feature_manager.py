import unittest

import pytest

from jeeves.manager.jira_feature_manager import JiraFeatureManager

mock_jira_features = {
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
    "Area C": {
        "Team 4": {
            "Shake-to-report": [],
        },
    },
}

feature_manager = JiraFeatureManager(mock_jira_features)


def test_get_features_by_team_and_area():
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
    # terms that appear in the field keys of the generated_description should be ignored.
    (
        "",
        "",
        "Session information:\nSkill tree id: 1234abcd",
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # terms that appear in the field values of the generated_description should be detected.
    (
        "",
        "",
        "Session information:\nField name: Leaderboard",
        ["Leaderboard"],
        ["Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # auto-generated "Reported with shake-to-report" message is not detected.
    (
        "Bug",
        "Please fix\n-\nReported with shake-to-report",
        "Reported with shake-to-report",
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
    ),
    # FullStory does not get detected as "story".
    (
        "",
        "",
        "FullStory:\n- session url: https://app.fullstory.com/asdf",
        [],
        ["Leaderboard", "Streak", "Stories", "Kudos", "Skill tree", "Shake-to-report"],
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
]


@pytest.mark.parametrize(
    "summary,description,generated_description,expected_suggestions,expected_others", test_cases
)
def test_get_suggested_features(
    summary, description, generated_description, expected_suggestions, expected_others
):
    actual_result = feature_manager.get_suggested_features(
        summary, description, generated_description
    )

    case = unittest.TestCase()
    case.assertEqual(expected_suggestions, actual_result["suggested_features"])
    case.assertCountEqual(expected_others, actual_result["other_features"])
