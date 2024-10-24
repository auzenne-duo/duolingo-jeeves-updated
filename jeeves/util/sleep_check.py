import time

from duolingo_base.config import Config


def sleep_check(config: Config, num_sec: int = 1) -> None:
    """
    A utility to help slow down services when running Jeeves locally. This helps make logging more manageable.

    Sleeps for num_sec seconds (default: 1) only if the environment is "local"

    :param config: Config object
    :param num_sec: Number of seconds to sleep for
    """
    if config.get_nested(["environment"]) == "local":
        time.sleep(num_sec)
