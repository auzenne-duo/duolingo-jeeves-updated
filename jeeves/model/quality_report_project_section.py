from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple

from jeeves.lib.quality_report_plot import create_plot
from jeeves.model.quality_report_base import QualityReportBase
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.util.date_util import date_to_str

_SCREEN_BUG_NUMBER_THRESHOLD = 0
_MAX_BUG_SCREENS = 5


class QualityReportProjectSection(QualityReportBase):
    def __init__(
        self,
        end_date: datetime,
        project: str,
        features: List[str],
        issues: List[QualityReportIssue],
        key_to_issue: Dict[str, QualityReportIssue],
        score_history: List[Tuple[datetime, int]],
        start_date: datetime,
        title: str,
    ) -> None:
        """
        Calculates and initializes quality scores for a specific project using given bugs

        Params
        See parent class
        score_history: a list of date and score tuples of previously computed quality scores
        """
        if features:
            issues = [issue for issue in issues if issue.feature in features]
        issues = [issue for issue in issues if issue.project == project]
        super().__init__(end_date, features, issues, key_to_issue, project, start_date, title)
        if not self.issues:
            return
        self.score_history = score_history.copy()
        self.score_history.append((date_to_str(self.end_date), self.overall_score))
        self.aggregate_scores = self.calculate_aggregate_scores(
            {self.project: self.score_history}, monthly=False
        )
        self.plot_filename, self.external_plot_filename = create_plot(
            self,
            self.aggregate_scores,
            self.project,
        )

        self.max_issue_screens = self.calculate_screen_count()

    def calculate_screen_count(self) -> List[Tuple[str, int]]:
        """
        Returns a list of screen strings and the number of issues per each
        """
        screen_count = Counter()
        for issue in self.issues:
            if issue.project == "DLAA":
                screen = issue.screen_content.split(".")[-1]
            elif issue.project == "DLAW":
                screen = issue.screen_content.split(".com")[-1]
            else:
                screen = issue.screen_content
            screen_count[screen] += 1
        return sorted(
            [
                (screen, count)
                for screen, count in screen_count.items()
                if screen and count > _SCREEN_BUG_NUMBER_THRESHOLD
            ],
            key=lambda x: -x[1],
        )[:_MAX_BUG_SCREENS]
