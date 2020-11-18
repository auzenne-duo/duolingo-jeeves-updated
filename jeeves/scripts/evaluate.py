"""
Script for evaluating text classification accuracy.
"""

import argparse
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES


def evaluate(language):
    """
    TODO: Run N-fold cross-validation to evaluate classification accuracy.
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="en", help="Language abbreviation.")
    args = parser.parse_args()
    print("Parameters: ", args)

    if args.language:
        assert args.language in SUPPORTED_LANGUAGES
        evaluate(args.language)
    else:
        for language in SUPPORTED_LANGUAGES:
            evaluate(language)

    print("Done.")
