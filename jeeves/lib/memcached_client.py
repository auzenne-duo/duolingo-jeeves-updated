"""
A Mecached client based on an implementation at duolingo-chatbot.
"""
from threading import Lock

from duolingo_base.config import Config
from duolingo_base.dal.memcache import BaseMemcacheDAL, MemcacheClient

_config = Config.load_config()

_memcache_clients = {}

_memcache_creation_lock = Lock()


def get_client(prefix, expiration=0, jitter=0):
    """
    Retrieves a ``BaseMemcacheDAL`` connection from the module-level dictionary
    ``_memcache_clients`` if one exists for the given ``prefix``. Otherwise, the function will
    create a new connection, populate ``_memcache_clients``, and return the connection.
    The hostname and port number are retrieved from ``config.MEMCACHED``.
    Parameters:
        prefix (str): The key prefix, prepended onto each lookup and set to isolate usage of the
            same cache for different purposes.
        expiration (int): The time (in seconds) it takes for a cache entry to expire.
        jitter (int): The time (in seconds) used to jitter the expiration.
    Returns:
        BaseMemcacheDAL: Connection to the configured Memcached server or cluster.
    """
    if prefix in _memcache_clients:
        return _memcache_clients[prefix]
    else:
        with _memcache_creation_lock:
            if prefix in _memcache_clients:
                return _memcache_clients[prefix]
            host = _config.get_nested(["memcached", "host"])
            port = int(_config.get_nested(["memcached", "port"]))
            _memcache_clients[prefix] = BaseMemcacheDAL(
                MemcacheClient([(host, port)]), prefix, expiration, jitter=jitter
            )
        return _memcache_clients[prefix]
