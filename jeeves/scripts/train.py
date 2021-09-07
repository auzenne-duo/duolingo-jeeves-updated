"""
Script for training text classifier models.
"""

import argparse

from jeeves.model.supported_languages import SUPPORTED_LANGUAGES


def train(language):
    """
    TODO: Train a model and save it.
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="en", help="Language abbreviation.")
    args = parser.parse_args()
    print("Parameters: ", args)

    if args.language:
        assert args.language in SUPPORTED_LANGUAGES
        train(args.language)
    else:
        for language in SUPPORTED_LANGUAGES:
            train(language)

    print("Done.")
