from typing import Set, Tuple

import attr


@attr.s(kw_only=True)
class JiraDuplicateGraph:
    issue_keys: Set[str] = attr.ib()
    existing_issue_links: Set[Tuple[str]] = attr.ib()
