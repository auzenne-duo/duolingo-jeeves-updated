from abc import ABCMeta, abstractmethod
import functools


class AbstractCacheHandler(object, metaclass=ABCMeta):
    """Abstract Cache Handler to manage cache use """

    def __init__(self):
        self._cacheList = []

    def cache(self, maxsize=128, typed=False):
        cache_func = self.caching_type(maxsize=maxsize, typed=typed)

        def wrap_cacher(fn):
            wrapped_func = cache_func(fn)
            self._cacheList.append(wrapped_func)
            return wrapped_func

        return wrap_cacher

    def clear(self):
        for cache in self._cacheList:
            cache.cache_clear()

    @property
    @abstractmethod
    def caching_type(self):
        pass


class LRUCacheHandler(AbstractCacheHandler):
    """`Least Recently Used Cache` Cache Handler to manage cache use """

    @property
    def caching_type(self):
        return functools.lru_cache


CacheHandler = LRUCacheHandler()
