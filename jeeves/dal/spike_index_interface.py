from datetime import date
from typing import Dict, Iterator, List, Optional

import rollbar
from duolingo_base.config import Config
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_dsl import Mapping, Search

from jeeves.config.config import DATA_VERSION_IDENTIFIER
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import date_to_str
from jeeves.util.error_util import SearchUnsuccessfulException

_config = Config.load_config()


class SpikeIndexDAL:
    def __init__(self) -> None:
        host = _config.get_nested(["elasticsearch", "host"])
        port = int(_config.get_nested(["elasticsearch", "port"]))

        self._es = Elasticsearch([host], port=port)

        self._spikename = f"jeeves_spikes_v_{DATA_VERSION_IDENTIFIER}"

    def initialize_index(self) -> None:
        """
        Initialize Elasticsearch index
        Should only be called once, during server startup
        """
        if not self._es.indices.exists(index=self._spikename):
            self._es.indices.create(index=self._spikename)

            m = Mapping()
            m.field("lang", "keyword")
            m.field("spike_group", "keyword")
            m.field("user_id", "number")
            m.save(self._spikename, using=self._es)
            rollbar.report_message("Created index {self._spikename} with new mappings", "info")

    def bulk_index_spikes(self, spikes: List[SpikeWord]) -> None:
        """
        Stores multiple spikes into Elasticsearch

        Parameters:
            spikes: List of spikes to store. Each spike is a dictionary that
                    should contain:
                    - word (str): The term the spike represents.
                    - lang (str): The language that the above word is from.
                    - date (str): The date the above word spiked on.
                    - score (float): How sharp the spike was.
                    - spike_group (str): Name of spike category the spike belongs
                                         to (see SpikeCategories.py).
                    - confirmed (bool): Whether or not the spike has been confirmed as a bug
        """
        bulk_actions = [
            {
                "_index": self._spikename,
                "_source": spike.to_dict(),
                "_id": spike.get_spike_id(),
            }
            for spike in spikes
        ]
        bulk(self._es, bulk_actions)

    def set_spike_confirm_setting(self, spike_id: str, desired_state: bool, user_id: int) -> None:
        """
        Sets the confirmed stat of a spikeword by spike_id to the specified state

        Parameters:
            spike_id: id string corresponding to a SpikeWord document
            desired_state: desired boolean setting of the confirmed state
            user_id: number of a user's id (jwt)

        Returns:
            True if the update succeeded; otherwise False
        """
        response = self._es.update(
            index=self._spikename,
            id=spike_id,
            body={"doc": {"confirmed": desired_state, "user_id": user_id}},
        )
        return response["_shards"]["total"] == response["_shards"]["successful"]

    def get_min_and_max_spike_dates(self) -> Dict[str, str]:
        """
        Returns the earliest and latest dates among all spikes in our data.
        Return value is a dict with keys `min` and `max` and string
        representations of dates as values.

        This is just the same method as get_min_and_max_document_dates, but for
        spikes instead of documents.
        """

        s = Search(using=self._es, index=self._spikename)
        s.aggs.metric("min_date", "min", field="date", format="yyyy-MM-dd")
        s.aggs.metric("max_date", "max", field="date", format="yyyy-MM-dd")

        response = s.execute()

        min_date = response.aggregations.min_date.value
        max_date = response.aggregations.max_date.value

        # We need to divide the return values by 1000 because they will be in
        # milliseconds instead of seconds.
        return {
            "min": date_to_str(date.fromtimestamp(min_date / 1000)) if min_date else None,
            "max": date_to_str(date.fromtimestamp(max_date / 1000)) if max_date else None,
        }

    def yield_spikes_on_date(
        self, lang: str, date_str: str, num_spikes: int, spike_group: SpikeCategory
    ) -> Iterator[SpikeWord]:
        """
        Yields all spikes for a given language, from a particular date.

        Parameters:
            lang (str): Language to yield spikes for.
            date_str (str): Date to search on.
            num_spikes (int): How many spikes we should yield.
            spike_group: Which group we want spikes from
                         (see jeeves/model/spike_categories.py)

        Yields:
            Spikes from the requested language on the requested date.
            Results are sorted, higher values of score first.
            See documentation for bulk_index_spikes for a description of spike
            format.
        """
        print(f"Yielding {num_spikes} {spike_group.name} spikes from {date_str}")
        return self.yield_spikes_in_date_range(
            lang=lang,
            start_date=date_str,
            end_date=date_str,
            spike_group=spike_group.name,
            num_spikes=num_spikes,
        )

    def yield_spikes_in_date_range(
        self,
        lang: str,
        start_date: str,
        end_date: str,
        spike_group: Optional[str] = "ALL_SPIKES",
        num_spikes: Optional[int] = None,
    ) -> Iterator[SpikeWord]:
        """
        Yields all spikes for a given language, between two dates

        Parameters:
            lang (str): Language to yield spikes for.
            start_date (str): Date to start search on, as a string.
            end_date (str): Date to end search on, as a string.
            num_spikes (str): How many spikes we should yield.
            spike_group (str): Spike group to restrict search to. Optional,
                               defaults to returning spikes from all documents.

        Yields:
            Spikes from the requested language between requested dates.
            See documentation for bulk_index_spikes for a description of spike
            format. Results are unsorted.
        """
        s = (
            Search(using=self._es, index=self._spikename)
            .filter("term", lang=lang)
            .filter("term", spike_group=spike_group)
            .sort("-score")
        )

        timestamp_dict = {}
        if start_date:
            timestamp_dict["gte"] = start_date
        if end_date:
            timestamp_dict["lte"] = end_date
        if timestamp_dict:
            s = s.filter("range", date=timestamp_dict)

        if num_spikes is not None:
            s = s[0:num_spikes]
            response = s.execute()

            if not response.success():
                raise SearchUnsuccessfulException(response, "yield spikes on date")
            for hit in response:
                yield SpikeWord.from_dict(hit)
        else:
            for res in s.scan():
                yield SpikeWord.from_dict(res)
