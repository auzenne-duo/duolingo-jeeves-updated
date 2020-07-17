"""
DAL for spiked word data for a certain day.
"""
from collections import defaultdict
import json

from jeeves.config.config import CRAWL_WINDOW_SIZE, VERSION_NUMBER
from jeeves.lib.memcached_client import get_client
from jeeves.util.date_util import date_to_str, get_eastern_today, get_n_days_ago

_CLIENT_NAME = "default"

# TODO: Set TTL to this in-memory cache
_SPIKES = defaultdict(dict)

_TTL = 60 * 60 * 24 * 7


class MemcacheSpikeDAL(object):
    def get_spikes(self, language):
        """
        Parameters:
            language(str): A two-letter language code.

        Returns:
            A JSON object from date string (YYYY-MM-DD) to a dict:
                spike: A desc-sorted list consisting of a spikiness score and a spiked word.
                new: A list of words that newly occurred on the date.
        """
        if _SPIKES[language]:
            return _SPIKES[language]
        M = get_client(_CLIENT_NAME)
        cache_key = self._get_cache_key(language)
        spike_json_str = M.get(cache_key)
        if spike_json_str:
            _SPIKES[language].update(json.loads(spike_json_str))
        return _SPIKES[language]

    def add_spikes(self, new_spike_dict, language):
        """
        Append given new_spike_dict data to existing spike date in memcache.

        Parameters:
            language(str): a two-letter language code.
            new_spike_dict: A dict from YYYY-MM-DD to spike info.
        """
        M = get_client(_CLIENT_NAME, expiration=_TTL)
        spike_dict = self.get_spikes(language)
        spike_dict.update(new_spike_dict)
        # Should be eastern
        today = get_eastern_today()
        valid_range = set(date_to_str(get_n_days_ago(today, i)) for i in range(CRAWL_WINDOW_SIZE))
        spike_dict = {k: v for k, v in spike_dict.items() if k in valid_range}
        cache_key = self._get_cache_key(language)
        M.set(cache_key, json.dumps(spike_dict))

    def reload_cache(self, language):
        """Clear and reload cache."""
        _SPIKES[language].clear()
        self.get_spikes(language)

    def _get_cache_key(self, language):
        return f"spikes_{language}_v{VERSION_NUMBER}"


SpikeDAL = MemcacheSpikeDAL()
