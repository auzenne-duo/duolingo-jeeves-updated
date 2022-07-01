"""
Manager for calculating bug report statistics.
"""

from collections import defaultdict
from datetime import datetime, time
from typing import Dict, List, Tuple
from urllib import parse

from duolingo_base.util import registry

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shakira_stat import ShakiraStat
from jeeves.util.date_util import datetime_to_str, get_eastern_today, get_n_days_ago

_RECENT_STATS_WINDOW_DAYS = 7
_RECENT_RESOLVED_BUGS_WINDOW_DAYS = 60
_JIRA_RESOLVED_RESOLUTIONS = ["Done", "Fixed", "Merged"]


@registry.bind(es_dal=registry.reference(ElasticsearchDAL))
class ShakiraStatsManager:
    def __init__(self, es_dal: ElasticsearchDAL):
        self._es_dal = es_dal

    def _get_recent_stats_window(self) -> Tuple[datetime, datetime]:
        today = get_eastern_today()
        start_of_today = datetime.combine(today.date(), time())
        recent_stats_window_start_datetime = get_n_days_ago(
            start_of_today, _RECENT_STATS_WINDOW_DAYS
        )
        return recent_stats_window_start_datetime, start_of_today

    def get_all_stats_per_reporter_email(self) -> Dict[str, Dict[ShakiraStat, int]]:
        # YK 2022-05-18 Due to a bug with Jira issue indexing (DEL-1674), these windows will end up
        # being either "Jira issues filed between 4AM to 4AM eastern" or "Jira issues filed between
        # 5AM to 5AM eastern", depending on Daylight Savings at the time of running the code.
        # Furthermore, these windows will overlap by an hour when Daylight Savings starts and will
        # miss an hour when Daylight Savings ends. We don't expect too many bugs to be reported
        # between 4AM - 5AM Eastern though.
        # More details: https://github.com/duolingo/duolingo-jeeves/pull/449#discussion_r876343004
        recent_window_start, recent_window_end = self._get_recent_stats_window()

        all_time_counts = self._es_dal.get_bugs_count_per_reporter_email(end_time=recent_window_end)
        recent_counts = self._es_dal.get_bugs_count_per_reporter_email(
            start_time=recent_window_start, end_time=recent_window_end
        )
        all_time_resolved_counts = self._es_dal.get_bugs_count_per_reporter_email(
            resolution_filter=_JIRA_RESOLVED_RESOLUTIONS, end_time=recent_window_end
        )
        recent_resolved_counts = self._es_dal.get_bugs_count_per_reporter_email(
            start_time=recent_window_start,
            end_time=recent_window_end,
            resolution_filter=_JIRA_RESOLVED_RESOLUTIONS,
        )

        stats_per_reporter_email = defaultdict(lambda: defaultdict(int))

        for reporter, count in all_time_counts.items():
            stats_per_reporter_email[reporter][ShakiraStat.ALL_TIME_COUNT] = count

        for reporter, count in recent_counts.items():
            stats_per_reporter_email[reporter][ShakiraStat.RECENT_COUNT] = count

        for reporter, count in all_time_resolved_counts.items():
            stats_per_reporter_email[reporter][ShakiraStat.ALL_TIME_RESOLVED_COUNT] = count

        for reporter, count in recent_resolved_counts.items():
            stats_per_reporter_email[reporter][ShakiraStat.RECENT_RESOLVED_COUNT] = count

        return stats_per_reporter_email

    def get_recent_resolved_bugs_per_person(self) -> Dict[str, List[JeevesDocument]]:
        today = get_eastern_today()
        start_of_today = datetime.combine(today.date(), time())
        recent_resolved_bugs_window_start_datetime = get_n_days_ago(
            start_of_today, _RECENT_RESOLVED_BUGS_WINDOW_DAYS
        )

        recent_resolved_bugs = self._es_dal.get_most_recent_resolved_bugs_per_reporter_email(
            resolution_filter=_JIRA_RESOLVED_RESOLUTIONS,
            start_time=recent_resolved_bugs_window_start_datetime,
        )
        return recent_resolved_bugs

    def get_jeeves_url_for_reporter_email_shakira_stat(
        self, reporter_email: str, shakira_stat: ShakiraStat
    ):
        reporter_query = f'reporter_email:"{reporter_email}"'
        recent_window_start, recent_window_end = self._get_recent_stats_window()

        if shakira_stat == ShakiraStat.ALL_TIME_COUNT:
            lucene_query = (
                f"{reporter_query} AND creation_date:[* TO {datetime_to_str(recent_window_end)}]"
            )
        elif shakira_stat == ShakiraStat.RECENT_COUNT:
            lucene_query = f"{reporter_query} AND creation_date:[{datetime_to_str(recent_window_start)} TO {datetime_to_str(recent_window_end)}]"
        elif shakira_stat == ShakiraStat.ALL_TIME_RESOLVED_COUNT:
            lucene_query = f"{reporter_query} AND resolution:({'|'.join(_JIRA_RESOLVED_RESOLUTIONS)}) AND resolution_date:[* TO {datetime_to_str(recent_window_end)}]"
        elif shakira_stat == ShakiraStat.RECENT_RESOLVED_COUNT:
            lucene_query = f"{reporter_query} AND resolution:({'|'.join(_JIRA_RESOLVED_RESOLUTIONS)}) AND resolution_date:[{datetime_to_str(recent_window_start)} TO {datetime_to_str(recent_window_end)}]"
        else:
            raise Exception()

        return f"https://jeeves.duolingo.com/en/discovery?q={parse.quote(lucene_query)}&filter=INTERNAL"
