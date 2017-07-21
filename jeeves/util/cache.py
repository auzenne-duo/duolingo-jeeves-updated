from abc import ABCMeta, abstractmethod
import functools

class AbstractCacheHandler(object, metaclass=ABCMeta):
    """Abstract Cache Handler to manage cache use """
    def __init__(self):
        self.cacheList = []

    def cache(self, maxsize=128, typed=False):
        c = self.caching_type(maxsize=maxsize, typed=typed)
        self.cacheList.append(c)
        return c

    def clear(self):
        for cache in self.cacheList:
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
