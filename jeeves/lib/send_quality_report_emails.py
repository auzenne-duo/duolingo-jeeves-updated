"""
Script that sends weekly bug digest emails to bug reporters.

Add your @duolingo.com email address to the _UNSUBSCRIBED list in order to unsubscribe.
"""

from duolingo_notify.api import RequestBuilder
from jinja2 import Environment, FileSystemLoader

from jeeves.model.quality_report import QualityReport, QualityReportArea
from jeeves.util.date_util import date_to_str

_TEMPLATE_DIR = "templates/quality_report/"
_UNSUBSCRIBED = ["example@duolingo.com"]


TEAM_TO_RECIPIENTS = {
    "Path": [
        ("rsalvador@duolingo.com", 591913431),
        ("ananya@duolingo.com", 361463477),
        ("path-team@duolingo.com", None),
    ],
    "Delight": [
        ("peter@duolingo", 97197056),
        ("shawn.buessing@duolingo.com", 18288193),
        ("rachael@duolingo.com", 44041393),
    ],
    "Generated Sessions": [("anton@duolingo.com", 358717862), ("sanil@duolingo.com", 800086825)],
    "New Writing Systems": [("chris@duolingo.com", 15316126)],
    "Growth": [
        ("colombo@duolingo.com", 65494655),
        ("lizn@duolingo.com", 288283957),
        ("Paul@duolingo.com", 246396732),
        ("achim@duolingo.com", 336910773),
        ("mpereslucha@duolingo.com", 759837354),
        ("ben.warsaw@duolingo.com", 404507680),
    ],
    "Learning R&D": [
        ("natalia@duolingo.com", 357062),
        ("joseph@duolingo.com", 47061),
        ("seun@duolingo.com", 448224015),
        ("tony@duolingo.com", 4),
    ],
    "Monetization": [
        ("itai@duolingo.com", 2200982),
        ("vicky@duolingo.com", 241673612),
        ("aspen@duolingo.com", 787642145),
        ("spotter@duolingo.com", 17782348),
        ("cem@duolingo.com", 194829322),
    ],
}

RECEIVE_ALL_AREA_REPORTS = [
    ("natalie@duolingo.com", 762020),
]

RECEIVE_ALL_REPORTS = [
    ("blanca@duolingo.com", 36291958),
    ("ramya@duolingo.com", 550324696),
    ("caleb.noble@duolingo.com", 23133309),
    ("brock@duolingo.com", 516234),
    ("lauren@duolingo.com", 41638666),
    ("britni@duolingo.com", 875832803),
    ("rwagner@duolingo.com", 105023805),
    ("sharanya@duolingo.com", 105463277),
]


def get_email_body_html(report: QualityReport) -> str:

    environment = Environment(loader=FileSystemLoader(_TEMPLATE_DIR))
    if isinstance(report, QualityReportArea):
        template = environment.get_template("area_email.html")
    else:
        template = environment.get_template("team_email.html")
    return template.render(report=report)


def send_email(report: QualityReport):
    dict_to_track = {
        "email_type": f"quality_report_{report.title}",
        "ui_language": "en",
    }
    if not report.title in TEAM_TO_RECIPIENTS:
        return

    recipients = TEAM_TO_RECIPIENTS[report.title]
    recipients.extend(RECEIVE_ALL_REPORTS)
    if isinstance(report, QualityReportArea):
        recipients.extend(RECEIVE_ALL_AREA_REPORTS)

    for email, user_id in recipients:
        if email in _UNSUBSCRIBED:
            continue

        rb = RequestBuilder()
        dict_to_track["user_id"] = user_id

        rb.add_emails(
            [email],
            f"{report.title} Quality Report {date_to_str(report.end_date)}",
            body_html=get_email_body_html(report),
            from_field='"Quality Report" <quality-report@duolingo.com>',
            track={"email send": dict_to_track, "email open": dict_to_track},
        )
        rb.send_medium_priority()
