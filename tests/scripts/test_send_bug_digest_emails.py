from collections import defaultdict
from typing import Dict

import pytest

from jeeves.model.shakira_stat import ShakiraStat
from jeeves.scripts.send_bug_digest_emails import should_send_email

should_send_email_test_cases = [
    ({}, False),
    ({ShakiraStat.ALL_TIME_COUNT: 1, ShakiraStat.ALL_TIME_RESOLVED_COUNT: 1}, False),
    (
        {
            ShakiraStat.ALL_TIME_COUNT: 1,
            ShakiraStat.ALL_TIME_RESOLVED_COUNT: 1,
            ShakiraStat.RECENT_RESOLVED_COUNT: 1,
        },
        True,
    ),
]


@pytest.mark.parametrize("input_stats,expected", should_send_email_test_cases)
def test_should_send_email(input_stats: Dict[ShakiraStat, int], expected: bool):
    stats = defaultdict(int)
    stats.update(input_stats)
    assert should_send_email("yijin@duolingo.com", stats) == expected
