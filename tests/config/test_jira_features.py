from jeeves.config.jira_features import (
    JIRA_FEATURES,
    JIRA_FEATURES_DESCRIPTIONS,
    LOG_SUMMARIZATION_ENABLED_FEATURES,
)


def test_terms_are_disjoint():
    terms = set()

    for pillar in JIRA_FEATURES:
        for teams_to_features in JIRA_FEATURES[pillar].values():
            for features_to_synonyms in teams_to_features.values():
                for feature, _ in features_to_synonyms.items():
                    assert feature.upper() not in terms
                    terms.add(feature.upper())


def test_descriptions_is_subset():
    features = {
        feature.upper()
        for pillar_features in JIRA_FEATURES.values()
        for area_features in pillar_features.values()
        for team_features in area_features.values()
        for feature in team_features
    }

    for description_feature in JIRA_FEATURES_DESCRIPTIONS:
        assert description_feature.upper() in features


def test_log_summarization_enabled_features_is_subset():
    all_features = {
        feature
        for pillar_features in JIRA_FEATURES.values()
        for area_features in pillar_features.values()
        for team_features in area_features.values()
        for feature in team_features
    }
    # All enabled features should be in the set of all features
    assert LOG_SUMMARIZATION_ENABLED_FEATURES.issubset(all_features)
    # Should not be empty
    assert len(LOG_SUMMARIZATION_ENABLED_FEATURES) > 0
    assert "Video Call" in LOG_SUMMARIZATION_ENABLED_FEATURES
    assert "Streak" in LOG_SUMMARIZATION_ENABLED_FEATURES
