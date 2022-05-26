"""
Manager for calculating bug report statistics.
"""

from collections import defaultdict
from datetime import date, datetime, time
from typing import Dict, List

import urllib3
from duolingo_base.util import registry

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shakira_stat import ShakiraStat
from jeeves.util.date_util import get_eastern_today, get_n_days_ago, str_to_date

_RECENT_STATS_WINDOW_DAYS = 7
_RECENT_RESOLVED_BUGS_WINDOW_DAYS = 60


@registry.bind(es_dal=registry.reference(ElasticsearchDAL))
class ShakiraStatsManager:
    def __init__(self, es_dal: ElasticsearchDAL):
        self._es_dal = es_dal

    def get_all_stats_per_reporter_email(self) -> Dict[str, Dict[ShakiraStat, int]]:
        # YK 2022-05-18 Due to a bug with Jira issue indexing (DEL-1674), these windows will end up
        # being either "Jira issues filed between 4AM to 4AM eastern" or "Jira issues filed between
        # 5AM to 5AM eastern", depending on Daylight Savings at the time of running the code.
        # Furthermore, these windows will overlap by an hour when Daylight Savings starts and will
        # miss an hour when Daylight Savings ends. We don't expect too many bugs to be reported
        # between 4AM - 5AM Eastern though.
        # More details: https://github.com/duolingo/duolingo-jeeves/pull/449#discussion_r876343004
        today = get_eastern_today()
        start_of_today = datetime.combine(today.date(), time())
        recent_stats_window_start_datetime = get_n_days_ago(
            start_of_today, _RECENT_STATS_WINDOW_DAYS
        )

        all_time_counts = self._es_dal.get_bugs_count_per_reporter_email(end_time=start_of_today)
        recent_counts = self._es_dal.get_bugs_count_per_reporter_email(
            start_time=recent_stats_window_start_datetime, end_time=start_of_today
        )
        all_time_resolved_counts = self._es_dal.get_bugs_count_per_reporter_email(
            should_count_resolved_bugs_only=True, end_time=start_of_today
        )
        recent_resolved_counts = self._es_dal.get_bugs_count_per_reporter_email(
            start_time=recent_stats_window_start_datetime,
            end_time=start_of_today,
            should_count_resolved_bugs_only=True,
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
            start_time=recent_resolved_bugs_window_start_datetime
        )
        return recent_resolved_bugs

    def get_date_of_oldest_indexed_document(self) -> date:
        return str_to_date(self._es_dal.get_min_and_max_document_dates()["min"])

    def get_jeeves_url_for_reporter(self, reporter: str):
        reporter_query = f'reporter:"{reporter}"'
        return f"https://jeeves.duolingo.com/en/discovery?q={urllib3.parse.quote(reporter_query)}&filter=INTERNAL"

    def get_jeeves_url_for_reporter_email(self, reporter_email: str):
        reporter_query = f'reporter_email:"{reporter_email}"'
        return f"https://jeeves.duolingo.com/en/discovery?q={urllib3.parse.quote(reporter_query)}&filter=INTERNAL"
