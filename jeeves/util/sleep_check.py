"""
A utility that cleans up logs by reducing the rate of api calls when running the repo locally
"""

import time

from duolingo_base.config import Config

config = Config.load_config()


def sleep_check():
    if config.get_nested(["environment"]) == "local":
        time.sleep(1)
