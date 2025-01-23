import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns
from dateutil.relativedelta import relativedelta

from jeeves.config.config import (
    QUALITY_REPORT_PLOTS_DIRECTORY,
    QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY,
)
from jeeves.config.jira_features import ALL_CUSTOM_PROJECTS
from jeeves.model.quality_report_base import QualityReportBase
from jeeves.util.date_util import date_to_str
from jeeves.util.quality_report_util import PROJECT_TO_PLATFORM, QUALITY_REPORT_OVERALL_KEY

# day of the month to start the monthly plots. 26 provides a buffer since the
# data is plotted on the 1st of the month
_MONTHLY_PLOT_START_DAY = 26
_PLOT_RANGE_MONTHS = 4
_PLOT_RANGE_WEEKS = 4

_JUICY_LIGHT_BLUE = "#1CB0F6"
_JUICY_ORANGE = "#FF9600"
_JUICY_PURPLE = "#CE82FF"
_JUICY_GREEN = "#58CC02"
_JUICY_YELLOW = "yellow"
_JUICY_PINK = "pink"
_JUICY_RED = "red"
_JUICY_GRAY = "#4B4B4B"
_COLOR_LIST = [
    _JUICY_LIGHT_BLUE,
    _JUICY_ORANGE,
    _JUICY_PURPLE,
    _JUICY_GREEN,
    _JUICY_YELLOW,
    _JUICY_PINK,
    _JUICY_RED,
]
_TITLE_TO_COLOR = {
    "DLAI": _JUICY_LIGHT_BLUE,
    "DLAA": _JUICY_ORANGE,
    "DLAW": _JUICY_PURPLE,
    QUALITY_REPORT_OVERALL_KEY: _JUICY_GREEN,
}

# set various plot styles
sns.set(
    rc={
        "axes.axisbelow": False,
        "axes.edgecolor": "lightgrey",
        "axes.facecolor": "None",
        "axes.grid": False,
        "axes.labelcolor": _JUICY_GRAY,
        "axes.spines.left": False,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "figure.facecolor": "white",
        "lines.solid_capstyle": "round",
        "patch.edgecolor": "w",
        "patch.force_edgecolor": True,
        "text.color": _JUICY_GRAY,
        "xtick.bottom": True,
        "xtick.color": _JUICY_GRAY,
        "xtick.direction": "out",
        "xtick.top": False,
        "ytick.color": _JUICY_GRAY,
        "ytick.direction": "out",
        "ytick.left": False,
        "ytick.right": False,
    },
)
sns.set_context("notebook", rc={"font.size": 25, "axes.titlesize": 25, "axes.labelsize": 25})


def get_plot_date_range(
    report: QualityReportBase, is_monthly: bool = False
) -> Tuple[datetime, datetime]:
    """
    Returns the start and end dates for the plot
    """
    if is_monthly:
        return get_plot_date_range_monthly(report)
    return get_plot_date_range_weekly(report)


def get_plot_date_range_monthly(report: QualityReportBase) -> Tuple[datetime, datetime]:
    """
    Returns the start and end dates for a plot of monthly scores

    Start date will be the _MONTHLY_PLOT_START_DAY of the month 4 months before the end date
    End date will be the end of the end date's month
    """
    plot_start_date = report.end_date.replace(day=_MONTHLY_PLOT_START_DAY) - relativedelta(
        months=_PLOT_RANGE_MONTHS
    )
    plot_end_date = report.end_date - timedelta(days=report.end_date.day) + relativedelta(months=1)
    return plot_start_date, plot_end_date


def get_plot_date_range_weekly(report: QualityReportBase) -> Tuple[datetime, datetime]:
    """
    Returns the start and end dates for a plot of weekly scores

    Start date will be the Saturday at least 4 weeks before the end date
    End date will be one day after the Monday before the end date
        because we plot weekly scores on Mondays and the extra day is for buffer.
    """
    plot_start_date = (
        report.end_date - timedelta(weeks=3) - timedelta(days=(report.end_date.weekday() + 2) % 7)
    )
    plot_end_date = report.end_date - timedelta(days=report.end_date.weekday()) + timedelta(1)
    return plot_start_date, plot_end_date


def find_text_placement(score, scores: List[int]) -> int:
    """
    Given a starting score and a list of all scores, finds a placement for the text
    such that it doesn't overlap with other lines
    """
    bottom_margin = 5
    top_margin = 10
    placement = score + bottom_margin
    while placement < 90:
        for score in scores:
            if 0 <= placement - score < bottom_margin or 0 <= score - placement < top_margin:
                placement = score + bottom_margin
        return placement
    return placement


def create_plot(
    report: QualityReportBase,
    project_to_scores: Dict[str, List[Tuple[datetime, int]]],
    plot_title: str,
    legend: bool = False,
    add_numbers=True,
    is_monthly=False,
) -> Tuple[str, str]:
    """
    Given a list of date/score tuples, creates a plot, saves it, and returns the internal and external filepaths

    params:
        report: QualityReportBase object
        project_to_scores: mapping from project str (eg "DLAA") to a list of date strings and score tuples
        plot_title: str to be used as the plot's title
        legend: flag to indicate whether a legend should be included
        add_numbers: flag to indicate whether the score should be added to the plot
        is_monthly: flag to indicate whether the plot is monthly or weekly

    returns: internal and external (s3) filepaths as a strings
    """
    # set the color of lines to be slightly transparent for all but Overall
    for title, color in _TITLE_TO_COLOR.items():
        rgb = matplotlib.colors.to_rgb(color)
        if title != QUALITY_REPORT_OVERALL_KEY and len(project_to_scores) > 1:
            rgb = rgb + (0.75,)
        _TITLE_TO_COLOR[title] = rgb

    plt.figure(figsize=(10, 5))
    ax = plt.subplot(111)
    plt.ylim([0, 105])

    plot_start_date, plot_end_date = get_plot_date_range(report, is_monthly)
    plt.xlim([plot_start_date, plot_end_date])

    font = {"weight": "bold", "size": 15}
    matplotlib.rc("font", **font)

    # add gray horizontal lines at each 20 tick
    plot_range = _PLOT_RANGE_MONTHS if is_monthly else _PLOT_RANGE_WEEKS
    for y in range(20, 120, 20):
        plt.plot(
            [report.end_date - relativedelta(months=x) for x in range(-1, plot_range + 1)],
            [y] * (plot_range + 2),
            "--",
            lw=0.5,
            color="black",
            alpha=0.3,
        )

    if is_monthly:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b, '%y"))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    else:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b %d, '%y"))
        plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))

    # we need to group all the scores for a particular date so we can find good text placement
    date_to_scores = defaultdict(list)
    for scores in project_to_scores.values():
        for date, score in scores:
            date_to_scores[date].append(score)

    for index, (title, scores) in enumerate(project_to_scores.items()):
        if not scores:
            continue

        # Don't graph custom project bugs because not all teams care about them
        if title in ALL_CUSTOM_PROJECTS:
            continue

        dates, y = zip(*[(date, score) for date, score in scores if date > plot_start_date.date()])
        marker = ""
        # add text labels to the plot if only one project is being plotted
        # or if the overall plot is being plotted
        if (len(project_to_scores) == 1 or title == QUALITY_REPORT_OVERALL_KEY) and add_numbers:
            marker = "o"
            for date, value in zip(dates, y):
                date_scores = date_to_scores[date]
                text_height = find_text_placement(value, date_scores)

                ax.text(
                    date,
                    text_height,
                    "%d" % value,
                    ha="center",
                    color=_TITLE_TO_COLOR.get(title, _COLOR_LIST[index % len(_COLOR_LIST)]),
                    fontsize=15,
                )
        plt.plot(
            dates,
            y,
            linestyle="-",
            linewidth=3,
            marker=marker,
            label=PROJECT_TO_PLATFORM.get(title, title),
            color=_TITLE_TO_COLOR.get(title, _COLOR_LIST[index % len(_COLOR_LIST)]),
        )
    if legend:
        box = ax.get_position()
        ax.set_position([box.x0, box.y0 + box.height * 0.2, box.width, box.height * 0.8])
        plt.legend(
            bbox_to_anchor=(0.5, -0.12),  # for legend lower center inside of plot
            loc="upper center",
            borderaxespad=0,
            frameon=False,
            prop={"size": 12},
            ncol=4,
        )

    filepath = f"{QUALITY_REPORT_PLOTS_DIRECTORY}/{report.title}_{plot_title}.png"
    external_filepath = f"{QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY}{report.title.replace(' ', '-')}-{plot_title}-{date_to_str(report.end_date)}.png"
    # Ensure directory for graphs exists
    if not os.path.exists(QUALITY_REPORT_PLOTS_DIRECTORY):
        os.mkdir(QUALITY_REPORT_PLOTS_DIRECTORY)
    plt.savefig(filepath, bbox_inches="tight")
    plt.close()
    return filepath, external_filepath
