"""
A wrapper for memcached libraries with a support for compression and value splits.

Compression case study:
There's a large forum discussion with 1000+ replies whose JSON data is in 693KB. With compression,
the size went down to 105KB (compression rate: 6.6) with an additional latency of 2 msec on a
t2.micro instance.

Motivation for splitting:
Memcache can store up to 1MB of data by default. If we increase this value, memory utilization
degrades, and we don't know how much to increase at this moment. So, this library takes care
of splitting a large object into multiple key-values each with a size of under 1MB.

TODO: Remove dependency to a specific MC client (initialize given a memcache client).
TODO: Replace the underlying manager with the implementation in python-duolingo-base.
"""

import zlib
from jeeves.lib.memcached_client import get_client

_CLIENT_NAME = "default"

# Each chunk after split is 500KB or less. Somehow it doesn't work when it's close to 1MB.
_CHUNK_SIZE = 500 * 1024


class MemcacheCompressionWrapper:
    @classmethod
    def _get_key(cls, cache_key, split=None):
        if split is None:
            split = "#"
        return f"{cache_key}:{split}"

    @classmethod
    def get(cls, cache_key):
        """
        Parameters:
            cache_key (str): A cache key.
        """
        M = get_client(_CLIENT_NAME)
        split_len = M.get(cls._get_key(cache_key))
        if not split_len:
            return None

        keys = [cls._get_key(cache_key, i) for i in range(split_len)]
        key_to_values = M.get_many(keys)
        values = [key_to_values[key] for key in keys]
        compressed = bytes(item for value in values for item in value)
        try:
            decompressed = zlib.decompress(compressed)
            return decompressed.decode("utf-8")
        except zlib.error:
            print("There was a zlib error")
            return None

    @classmethod
    def set(cls, cache_key, cache_value, ttl):
        """
        Parameters:
            cache_key (str): A cache key.
            cache_value (str): A cache value.
            ttl (int): Seconds to expire the cache [0, 60*60*24*30]. Avoid 0 (=never expire) since
                memcached evictions do not always work as we expect. Learn more details at
                https://github.com/memcached/memcached/wiki/Programming#expiration
        """
        M = get_client(_CLIENT_NAME, expiration=ttl, jitter=0)
        compressed_value = zlib.compress(cache_value.encode("utf-8"))
        split_ids = range(int(len(compressed_value) / _CHUNK_SIZE) + 1)
        split_compressed_values = [
            compressed_value[i * _CHUNK_SIZE : (i + 1) * _CHUNK_SIZE] for i in split_ids
        ]
        key_to_value = {
            cls._get_key(cache_key, i): split_compressed_value
            for i, split_compressed_value in enumerate(split_compressed_values)
        }
        M.set_many(key_to_value)
        M.set(cls._get_key(cache_key), len(split_compressed_values))

    @classmethod
    def delete(cls, cache_key):
        """
        Parameters:
            cache_key (str): A cache key.
        """
        M = get_client(_CLIENT_NAME)
        M.delete(cache_key)
