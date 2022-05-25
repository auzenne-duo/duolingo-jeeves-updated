from typing import Dict

from duolingo_notify.api import RequestBuilder

from jeeves.manager.shakira_stats_manager import ShakiraStats
from jeeves.model.shakira_stat import ShakiraStat


def should_send_email(stats: Dict[ShakiraStat, int]) -> bool:
    if stats[ShakiraStat.RECENT_COUNT] == 0 and stats[ShakiraStat.RECENT_RESOLVED_COUNT] == 0:
        return False
    if stats[ShakiraStat.ALL_TIME_COUNT] >= 10 and stats[ShakiraStat.ALL_TIME_RESOLVED_COUNT] == 0:
        return False
    return True


stats_per_reporter = ShakiraStats.get_all_stats_per_reporter_email()
stats_per_reporter_to_send_emails_to = {
    reporter: stats for reporter, stats in stats_per_reporter.items() if should_send_email(stats)
}
resolved_bugs_per_reporter = ShakiraStats.get_recent_resolved_bugs_per_person()

# TODO template email

rb = RequestBuilder()
rb.add_emails(
    ["yijin@duolingo.com"], "Subject", "Body", from_field='"Shake-to-report" <shakira@duolingo.com>'
)
rb.send_medium_priority()
