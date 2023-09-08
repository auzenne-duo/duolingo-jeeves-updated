"""
A Memcached client based on an implementation at duolingo-chatbot.
"""
import logging
from threading import Lock
from typing import Dict

from duolingo_base.config import Config
from duolingo_base.dal.caching import CachingDAL
from duolingo_base.dal.memcache import MemcacheClient

_config = Config.load_config()
_memcached_clients: Dict[str, CachingDAL] = {}
_memcached_creation_lock = Lock()

LOG = logging.getLogger(__name__)


def get_memcached_client(prefix: str, expiration: int = 0, jitter: int = 0) -> CachingDAL:
    """
    Retrieves a ``CachingDAL`` connection from the module-level dictionary
    ``_memcached_clients`` if one exists for the given ``prefix``. Otherwise, the function will
    create a new connection, populate ``_memcached_clients``, and return the connection.
    The hostname and port number are retrieved from ``config.MEMCACHED``.
    Parameters:
        prefix (str): The key prefix, prepended onto each lookup and set to isolate usage of the
            same cache for different purposes.
        expiration (int): The time (in seconds) it takes for a cache entry to expire.
        jitter (int): The time (in seconds) used to jitter the expiration.
    Returns:
        CachingDAL: Connection to the configured Memcached server or cluster.
    """
    if prefix in _memcached_clients:
        return _memcached_clients[prefix]
    else:
        with _memcached_creation_lock:
            if prefix in _memcached_clients:
                return _memcached_clients[prefix]
            host = _config.get_nested(["memcached", "host"])
            port = int(_config.get_nested(["memcached", "port"]))
            LOG.info(f"Connecting to memcached client with prefix {prefix} at {host}:{port}")
            _memcached_clients[prefix] = CachingDAL(
                MemcacheClient([(host, port)]), prefix, expiration, jitter
            )
        return _memcached_clients[prefix]
