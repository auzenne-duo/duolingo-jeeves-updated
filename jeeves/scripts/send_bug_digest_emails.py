"""
Script that sends weekly bug digest emails to bug reporters.

Add your @duolingo.com email address to the _UNSUBSCRIBED list in order to unsubscribe.
"""

import codecs
import sys
from typing import Dict, List

import rollbar
from duolingo_base.config import Config
from duolingo_notify.api import RequestBuilder

# TODO use duostache
from pystache import render

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.manager.shakira_stats_manager import ShakiraStatsManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shakira_stat import ShakiraStat

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

_UNSUBSCRIBED = [
    "jake@duolingo.com",
]

_TEMPLATE_DIR = "templates/bug_digest/email/"

_SHAKIRA_STAT_HEADERS = {
    ShakiraStat.ALL_TIME_COUNT: "Total bugs reported",
    ShakiraStat.ALL_TIME_RESOLVED_COUNT: "Total resolved bug reports",
    ShakiraStat.RECENT_COUNT: "Bugs reported in the last week",
    ShakiraStat.RECENT_RESOLVED_COUNT: "Bug reports resolved in the last week",
}

_SHAKIRA_STAT_ORDER = {
    ShakiraStat.ALL_TIME_COUNT: 4,
    ShakiraStat.ALL_TIME_RESOLVED_COUNT: 3,
    ShakiraStat.RECENT_COUNT: 2,
    ShakiraStat.RECENT_RESOLVED_COUNT: 1,
}


def should_send_email(reporter: str, stats: Dict[ShakiraStat, int]) -> bool:
    if reporter in _UNSUBSCRIBED:
        return False
    if stats[ShakiraStat.RECENT_COUNT] == 0 and stats[ShakiraStat.RECENT_RESOLVED_COUNT] == 0:
        return False
    return True


def _get_jeeves_urls_for_stats(
    reporter: str, stats_dict: Dict[ShakiraStat, int]
) -> Dict[ShakiraStat, str]:
    return {
        stat: app_registry(ShakiraStatsManager).get_jeeves_url_for_reporter_email_shakira_stat(
            reporter, stat
        )
        for stat in stats_dict.keys()
    }


def _get_email_body_html(
    reporter: str, stats_dict: Dict[ShakiraStat, int], resolved_bugs: List[JeevesDocument]
) -> str:
    url_dict = _get_jeeves_urls_for_stats(reporter, stats_dict)

    # sort the stats
    stats = [
        {
            "header": _SHAKIRA_STAT_HEADERS[stat],
            "value": value,
            "url": url_dict[stat],
            "sort_order": _SHAKIRA_STAT_ORDER[stat],
        }
        for stat, value in stats_dict.items()
        if value > 0
    ]
    sorted_stats = sorted(stats, key=lambda stat: stat["sort_order"])
    recent_resolved_bugs_exist = len(resolved_bugs) > 0
    recent_resolved_bugs = [
        {
            "is_first": idx == 0,
            "issue_key": doc.issue_key,
            "issue_summary": doc.header_text,
            "issue_url": f"https://duolingo.atlassian.net/browse/{doc.issue_key}",
            "issue_resolution": doc.resolution,
        }
        for idx, doc in enumerate(resolved_bugs)
    ]

    return render(
        codecs.open(_TEMPLATE_DIR + "body_html.tmpl", "r", "utf8").read(),
        {
            "stats": sorted_stats,
            "recent_resolved_bugs_exist": recent_resolved_bugs_exist,
            "recent_resolved_bugs": recent_resolved_bugs,
        },
    )


if __name__ == "__main__":
    apply_registry()
    try:
        stats_per_reporter = app_registry(ShakiraStatsManager).get_all_stats_per_reporter_email()
        stats_per_reporter_to_send_emails_to = {
            reporter: stats
            for reporter, stats in stats_per_reporter.items()
            if should_send_email(reporter, stats)
        }
        resolved_bugs_per_reporter = app_registry(
            ShakiraStatsManager
        ).get_recent_resolved_bugs_per_person()

        for reporter, stats_dict in stats_per_reporter_to_send_emails_to.items():
            resolved_bugs = resolved_bugs_per_reporter.get(reporter, [])
            body_html = _get_email_body_html(reporter, stats_dict, resolved_bugs)
            print(f"adding {reporter}")
            rb = RequestBuilder()
            rb.add_emails(
                [reporter],
                "Your weekly Shake-to-report bug digest 💃",
                body_html=_get_email_body_html(reporter, stats_dict, resolved_bugs),
                from_field='"Shake-to-report" <shakira@duolingo.com>',
            )
            rb.send_medium_priority()
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()
