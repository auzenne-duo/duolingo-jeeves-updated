from jeeves.config.jira_features import JIRA_FEATURES, JIRA_FEATURES_DESCRIPTIONS


def test_terms_are_disjoint():
    terms = set()

    for teams_to_features in JIRA_FEATURES.values():
        for features_to_synonyms in teams_to_features.values():
            for feature, synonyms in features_to_synonyms.items():
                assert feature.upper() not in terms
                terms.add(feature.upper())


def test_descriptions_is_subset():
    features = {
        feature.upper()
        for area_features in JIRA_FEATURES.values()
        for team_features in area_features.values()
        for feature in team_features
    }
    for description_feature in JIRA_FEATURES_DESCRIPTIONS:
        assert description_feature.upper() in features
