from jeeves.config.jira_features import JIRA_FEATURES


def test_terms_are_disjoint():
    terms = set()

    for teams_to_features in JIRA_FEATURES.values():
        for features_to_synonyms in teams_to_features.values():
            for feature, synonyms in features_to_synonyms.items():
                assert feature.upper() not in terms
                terms.add(feature.upper())

                for synonym in synonyms:
                    assert synonym.upper() not in terms
                    terms.add(synonym.upper())
