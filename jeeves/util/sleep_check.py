import time

from jeeves.config.config import get_config


def sleep_check(num_sec: int = 1) -> None:
    """
    A utility to help slow down services when running Jeeves locally. This makes debugging and logging more manageable.
    Sleeps for num_sec seconds (default: 1) only if the environment is "local".

    :param num_sec: Number of seconds to sleep for
    """
    if get_config().get_nested(["environment"]) == "local":
        time.sleep(num_sec)
