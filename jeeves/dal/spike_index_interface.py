import sys
from collections import defaultdict
from datetime import date
from typing import Any, Dict, Iterator, List, Optional

import rollbar
from duolingo_base.config import Config
from nltk.stem.snowball import SnowballStemmer
from opensearch_dsl import Mapping, Search
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import date_to_str, str_to_date
from jeeves.util.error_util import SearchUnsuccessfulException

_config = Config.load_config()


class SpikeIndexDAL:
    def __init__(self) -> None:
        host = _config.get_nested(["opensearch", "host"])
        port = int(_config.get_nested(["opensearch", "port"]))

        self._es = OpenSearch([host], port=port)

        self._spikename = (
            f"jeeves_spikes_v_{_config.get_nested(['opensearch', 'data_version_identifier'])}"
        )

    def initialize_index(self) -> None:
        """
        Initialize OpenSearch index
        Should only be called once, during server startup
        """
        if not self._es.indices.exists(index=self._spikename):
            print(f"Creating index {self._spikename}...", flush=True)
            self._es.indices.create(index=self._spikename)

            m = Mapping()
            m.field("lang", "keyword")
            m.field("spike_group", "keyword")
            m.save(self._spikename, using=self._es)
            rollbar.report_message(f"Created index {self._spikename} with new mappings", "info")

    def bulk_index_spikes(self, spikes: List[SpikeWord]) -> None:
        """
        Stores multiple spikes into OpenSearch

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
        (_, errors) = bulk(self._es, bulk_actions, raise_on_error=False, raise_on_exception=False)
        if errors:
            error_message = (
                f"Encountered {len(errors)} error{'' if len(errors) == 1 else 's'} "
                + f"when bulk indexing spikes: {errors}"
            )
            rollbar.report_exc_info(sys.exc_info())
            raise Exception(error_message)

    def _update_settings(self, settings: Dict[str, Any], spike_id: str) -> None:
        """
        Updates settings of a spikeword by spike_id to the specified states

        Parameters:
            settings: a mapping from SpikeWord attributes to the desired state.
            spike_id: id string corresponding to a SpikeWord document
            user_id: number of a user's id
        """
        response = self._es.update(  # pylint: disable=E1123
            index=self._spikename,
            id=spike_id,
            body={"doc": settings},
            refresh=True,
        )
        if response["_shards"]["total"] != response["_shards"]["successful"]:
            raise Exception(f"Update to settings {settings} of spike {spike_id} failed")

    def set_spike_confirm_setting(self, spike_id: str, desired_state: bool, user_id: int) -> None:
        """
        Sets the confirmed status of a spikeword by spike_id to the specified state

        Parameters:
            spike_id: id string corresponding to a SpikeWord document
            desired_state: desired boolean setting of the confirmed state
            user_id: number of a user's id
        """
        self._update_settings({"confirmed": desired_state, "confirmed_user_id": user_id}, spike_id)

    def set_spike_fixed_setting(self, spike_id: str, desired_state: bool, user_id: int) -> None:
        """
        Sets the fixed status of a spikeword by spike_id to the specified state

        Parameters:
            spike_id: id string corresponding to a SpikeWord document
            desired_state: desired boolean setting of the fixed state
            user_id: number of a user's id
        """
        self._update_settings({"fixed": desired_state, "fixed_user_id": user_id}, spike_id)

    def set_spike_email_sent(self, spike_id: str, user_id: int, email_sent_date: str):
        """
        Sets the email_sent_date and user_id settings of a spikeword

        Parameters:
            spike_id: id string corresponding to a SpikeWord document
            user_id: number of a user's id
            email_sent_date: date string of when the email was sent
        """
        self._update_settings(
            {"email_user_id": user_id, "email_sent_date": email_sent_date}, spike_id
        )

    def calculate_spike_stats(
        self,
        lang: str,
        spike_category: SpikeCategory,
        spike_threshold: int = 3,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Returns stats on number of spikes, confirms, and the most common spikewords

        Parameters:
            lang (str): Language to calculate spike stats for.
            spike_category: Which group we want spikes from
                         (see jeeves/model/spike_categories.py)
            spike_threshold (int): How many times a spike word must occur to count as common
            start_date (str): Date to search from
            end_date (str): Date to search to

        Return:
            dict {
                month_count: [
                    {
                        date_str: (str) date string such as "2022-08-01"
                        confirmed: int,
                        total: int,
                    }
                ]
                word_count: [
                    {
                        stem: (str) stemmed word for the spike word group (doubl for double/doubled)
                        dates: (List[str]) list of date strings when the spike occurred
                        num_confirmed: (int) number of confirmed occurrences
                        total: (int) number of spike occurrences
                        terms: (List[str]) terms included in the stem group
                    },
                    ...
                ]
            }
        """
        timestamp_dict = {}
        if start_date:
            timestamp_dict["gte"] = start_date
        if end_date:
            timestamp_dict["lte"] = end_date

        agg_spec = {
            "spikes_by_month": {
                "date_histogram": {
                    "field": "date",
                    "calendar_interval": "month",
                    "format": "yyyy-MM-dd",
                },
                "aggs": {"confirm_status": {"terms": {"field": "confirmed"}}},
            }
        }

        query = {
            "bool": {
                "filter": [{"term": {"lang": lang}}, {"term": {"spike_group": spike_category}}]
            }
        }
        if timestamp_dict:
            query["bool"]["filter"].append({"range": {"date": timestamp_dict}})

        response = self._es.search(index=self._spikename, body={"aggs": agg_spec, "query": query})
        confirm_and_total_count = []
        for month_bucket in response["aggregations"]["spikes_by_month"]["buckets"]:
            num_confirmed = 0
            for confirmed_bucket in month_bucket["confirm_status"]["buckets"]:
                if confirmed_bucket["key"]:
                    num_confirmed = confirmed_bucket["doc_count"]
            confirm_and_total_count.append(
                {
                    "confirmed": num_confirmed,
                    "date_str": month_bucket["key_as_string"],
                    "total": month_bucket["doc_count"],
                }
            )

        snow_stemmer = SnowballStemmer(language="english")
        s = (
            Search(using=self._es, index=self._spikename)
            .filter("term", lang=lang)
            .filter("term", spike_group=spike_category)
        )

        if timestamp_dict:
            s = s.filter("range", date=timestamp_dict)
        word_to_dates = defaultdict(lambda: {"dates": [], "words": set()})
        for res in s.scan():
            stem = snow_stemmer.stem(res.word)
            word_to_dates[stem]["dates"].append((str_to_date(res.date), res.confirmed))
            word_to_dates[stem]["words"].add(res.word)

        word_count = []

        # filter for unique dates by detecting clusters of consecutive dates
        for word, data in word_to_dates.items():

            dates = data["dates"]
            dates.sort(key=lambda x: x[0])

            date, confirm_status = dates[0]
            unique_dates = {date: confirm_status}
            last_added_date = date
            for i, (date, confirm_status) in enumerate(dates):
                if i != 0:
                    if (date - dates[i - 1][0]).days > 1:
                        unique_dates[date] = confirm_status
                        last_added_date = date
                    else:
                        unique_dates[last_added_date] = (
                            unique_dates[last_added_date] or confirm_status
                        )

            num_confirmed = sum(unique_dates.values())
            if len(unique_dates) >= spike_threshold or num_confirmed >= 1:
                date_strs = [date_to_str(date_obj) for date_obj in unique_dates]
                terms = sorted(list(word_to_dates[word]["words"]))
                word_count.append(
                    {
                        "stem": word,
                        "dates": date_strs,
                        "num_confirmed": num_confirmed,
                        "total": len(unique_dates),
                        "terms": terms,
                    }
                )

        return {"month_count": confirm_and_total_count, "word_count": word_count}

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
        self,
        lang: str,
        date_str: str,
        num_spikes: int,
        spike_group: SpikeCategory,
        only_bugs: bool = False,
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
            only_bugs=only_bugs,
        )

    def yield_spikes_in_date_range(
        self,
        lang: Optional[str],
        start_date: str,
        end_date: str,
        spike_group: Optional[str] = "ALL_SPIKES",
        num_spikes: Optional[int] = None,
        only_bugs: bool = False,
    ) -> Iterator[SpikeWord]:
        """
        Yields all spikes for a given language, between two dates

        Parameters:
            lang (str): Language to yield spikes for. If None, yields all spikes.
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
            .filter("term", spike_group=spike_group)
            .sort("-score")
        )

        if lang:
            s = s.filter("term", lang=lang)

        timestamp_dict = {}
        if start_date:
            timestamp_dict["gte"] = start_date
        if end_date:
            timestamp_dict["lte"] = end_date
        if timestamp_dict:
            s = s.filter("range", date=timestamp_dict)

        if only_bugs:
            s = s.filter("term", is_bug=True)

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

    def get_spike_by_id(self, spike_id: str) -> SpikeWord:
        s = Search(using=self._es, index=self._spikename).filter("term", _id=spike_id)

        response = s.execute()
        if response:
            return SpikeWord.from_dict(response[0])
        return None
