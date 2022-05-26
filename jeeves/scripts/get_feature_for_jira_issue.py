"""
Takes a Jira issue key and prints the list of detected features for the issue's summary and description.

Command line argument: Jira issue key (e.g. DEL-1234)

In order to use this script, make sure to do the following:
1. Set the following environment variables:
    - JIRA_USERNAME, SHAKIRA_JIRA_USERNAME_WEB = your @duolingo email
    - JIRA_API_TOKEN, SHAKIRA_JIRA_API_TOKEN_WEB = an api token generated from your account
    - DUPLICATE_DETECTOR_MODEL = a file path on your computer
2. Before the first time running this script, you'll have to download the duplicate detector model
to the $DUPLICATE_DETECTOR_MODEL file path:
    a. Make sure the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables are set.
    b. Run the following (see below if this doesn't work):
        aws s3 sync "s3://jeeves-document-cache/duplicate-detector-model" $DUPLICATE_DETECTOR_MODEL
    c. You may have to run the following for the above to work:
        pip3 install --upgrade awscli
"""

import sys

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.manager.jira_feature_manager import JiraFeatureManager
from jeeves.manager.jira_manager import JiraManager

if __name__ == "__main__":
    apply_registry()
    try:
        jira_doc = JiraManager.download_specific_issue(sys.argv[1])

        print(f"Issue summary     : {jira_doc.header_text}")
        print(f"Issue description : {jira_doc.body_text}")
        print(f"Issue metadata    : {jira_doc.duolingo_metadata.get('raw')}")

        suggested_features = app_registry(JiraFeatureManager).get_suggested_features(
            ["DLAA", "DLAI", "DLAW"],
            summary=jira_doc.header_text,
            description=jira_doc.body_text,
            generated_description=jira_doc.duolingo_metadata.get("raw"),
        )

        print(f"Suggested features: {', '.join(suggested_features['suggested_features'])}")
    finally:
        close_registry()
