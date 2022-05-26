import sys
from typing import Dict

import rollbar
from duolingo_base.config import Config
from duolingo_notify.api import RequestBuilder

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.manager.shakira_stats_manager import ShakiraStatsManager
from jeeves.model.shakira_stat import ShakiraStat

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()


def should_send_email(stats: Dict[ShakiraStat, int]) -> bool:
    if stats[ShakiraStat.RECENT_COUNT] == 0 and stats[ShakiraStat.RECENT_RESOLVED_COUNT] == 0:
        return False
    if stats[ShakiraStat.ALL_TIME_COUNT] >= 10 and stats[ShakiraStat.ALL_TIME_RESOLVED_COUNT] == 0:
        return False
    return True


if __name__ == "__main__":
    apply_registry()
    try:
        stats_per_reporter = app_registry(ShakiraStatsManager).get_all_stats_per_reporter_email()
        stats_per_reporter_to_send_emails_to = {
            reporter: stats
            for reporter, stats in stats_per_reporter.items()
            if should_send_email(stats)
        }
        resolved_bugs_per_reporter = app_registry(
            ShakiraStatsManager
        ).get_recent_resolved_bugs_per_person()
        print(resolved_bugs_per_reporter)

        # TODO template email

        rb = RequestBuilder()
        rb.add_emails(
            ["yijin@duolingo.com"],
            "Subject",
            "Body",
            from_field='"Shake-to-report" <shakira@duolingo.com>',
        )
        rb.send_medium_priority()
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()
