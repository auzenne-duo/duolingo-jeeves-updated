"""
DAL for spiked word data for a certain day.
"""
import json
import os

from jeeves.util.s3 import S3, S3_SPIKE_DIR, S3_BUCKET_ID


# TODO: Set TTL to this in-memory cache
_SPIKES = {}


class AbstractSpikeDAL(object):

    def get_spikes(self):
        """
        Returns:
            A JSON object from date string (YYYY-MM-DD) to a dict:
                spike: A desc-sorted list consisting of a spikiness score and a spiked word.
                new: A list of words that newly occurred on the date.
        """
        pass

    def reload_cache(self):
        """Clear and reload cache."""
        pass


class S3RemoteSpikeDAL(AbstractSpikeDAL):

    def get_spikes(self):
        if _SPIKES:
            return _SPIKES
        # TODO: Load data for the last N-days only
        for s3_path in S3.yield_filenames(S3_BUCKET_ID, path_prefix=S3_SPIKE_DIR):
            file_name = os.path.basename(s3_path)
            json_str = S3.download(S3_BUCKET_ID, os.path.join(S3_SPIKE_DIR, file_name))
            _SPIKES[file_name] = json.loads(json_str)
        return _SPIKES

    def reload_cache(self):
        _SPIKES.clear()
        self.get_spikes()


SpikeDAL = S3RemoteSpikeDAL()
