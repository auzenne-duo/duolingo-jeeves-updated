"""
Script that sends weekly bug digest emails to bug reporters.

Add your @duolingo.com email address to the _UNSUBSCRIBED list in order to unsubscribe.
"""

import logging
from typing import Dict, List, Optional, Tuple

from duolingo_base.config import Config
from duolingo_notify.api import RequestBuilder
from jinja2 import Environment, FileSystemLoader

from jeeves import registry as app_registry
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.employees import EmployeesDAL
from jeeves.model.quality_report import QualityReport, QualityReportArea
from jeeves.util.quality_report_util import TEMPLATE_DIRECTORY

config = Config.load_config()

LOG = logging.getLogger(__name__)

_UNSUBSCRIBED = ["example@duolingo.com"]
_IS_PRODUCTION_ENV = config.get_nested(["environment"]) == "prod"

_AREA = "AREA"
_RECEIVE_ALL = "RECEIVE_ALL"
# This list is mostly based on the data from the orgchart:
# https://static.internal.duolingo.com/colombo/orgchart/orgchart.html#onboarding
# You can run get_latest_recipient_groups function to get the latest mapping of recipients

RECIPIENT_GROUPS: Dict[str, Dict[str, List]] = {
    "Design Accelerator": {
        _AREA: [("peter@duolingo", 97197056)],
        "Design Systems": [
            ("ash@duolingo.com", 1252195),
            ("shawn.buessing@duolingo.com", 18288193),
        ],
    },
    "Growth": {
        _AREA: [
            ("colombo@duolingo.com", 65494655),
            ("lizn@duolingo.com", 288283957),
            ("Paul@duolingo.com", 246396732),
            ("achim@duolingo.com", 336910773),
            ("sonya@duolingo.com", 104216619),
            ("yao@duolingo.com", 576008906),
            ("hu@duolingo.com", 766417435),
            ("ihsuan@duolingo.com", 282991771),
            ("hideki@duolingo.com", 1076),
            ("soyee@duolingo.com", 969088226),
        ],
        _RECEIVE_ALL: [
            ("ningxin@duolingo.com", 510539986),
            ("mpereslucha@duolingo.com", 759837354),
            ("ben.warsaw@duolingo.com", 404507680),
        ],
        "China": [
            ("elriczhong@duolingo.com", 338612774),
            ("kevinyang@duolingo.com", 3057357),
        ],
        "Connections": [
            ("nico@duolingo.com", 614168902),
            ("hideki@duolingo.com", 1076),
            ("maha@duolingo.com", 20528629),
            ("amia@duolingo.com", 48361939),
            ("renee@duolingo.com", 339403062),
            ("jackdu@duolingo.com", 552001465),
            ("martina@duolingo.com", 698342914),
            ("maggie.huang@duolingo.com", 49022092),
            ("bill.guo@duolingo.com", 800409886),
            ("christopher@duolingo.com", 12670686),
            ("megan@duolingo.com", 213757048),
        ],
        "Onboarding": [("sarahtracy@duolingo.com", 100396129), ("mike@duolingo.com", 32080913)],
        "Resurrection": [
            ("kevinyang@duolingo.com", 3057357),
            ("tao@duolingo.com", 515653291),
            ("allen.wang@duolingo.com", 975446875),
        ],
        "Reengagement": [
            ("osman@duolingo.com", 555374397),
            ("soyee@duolingo.com", 969088226),
            ("stephanie@duolingo.com", 350148009),
        ],
        "Retention": [
            ("jackson@duolingo.com", 19364437),
            ("antonia@duolingo.com", 190618),
            ("retention-engineering@duolingo.com", None),
        ],
        "Time Spent Learning": [
            ("rsalvador@duolingo.com", 591913431),
            ("louise@duolingo.com", 137802874),
            ("peter.kung@duolingo.com", 29667866),
        ],
        "Growth Web": [
            ("christopher@duolingo.com", 12670686),
            ("deanna@duolingo.com", 95819324),
        ],
    },
    "Infra Platform": {
        _AREA: [("peter@duolingo", 97197056)],
        "Engineering Studio": [
            ("becky@duolingo.com", 614576367),
            ("sharanya@duolingo.com", 105463277),
        ],
        "Stability and Performance": [
            ("leon@duolingo.com", 233506),
            ("caesar@duolingo.com", 197953187),
        ],
    },
    "Learning R&D": {
        _AREA: [
            ("ang@duolingo.com", 8676371),
            ("natalia@duolingo.com", 357062),
            ("joseph@duolingo.com", 47061),
            ("seun@duolingo.com", 448224015),
            ("tony@duolingo.com", 4),
            ("jenna@duolingo.com", 139182230),
            ("hoshi@duolingo.com", 35950076),
            ("liz@duolingo.com", 461557793),
        ],
        _RECEIVE_ALL: [],
        "Path": [
            ("path-team@duolingo.com", None),
        ],
        "Personalized Sessions": [
            ("ang@duolingo.com", 8676371),
            ("sanil@duolingo.com", 800086825),
            ("will.haines@duolingo.com", 13834416),
        ],
        "New Writing Systems": [("chris@duolingo.com", 15316126)],
        "Media Learning": [
            ("jasong@duolingo.com", 430902565),
            ("michael@duolingo.com", 15587805),
            ("cailyn@duolingo.com", 507747809),
        ],
    },
    "Learning Scaling": {
        _AREA: [
            ("joseph@duolingo.com", 47061),
            ("jessica@duolingo.com", 521621716),
            ("williams@duolingo.com", 402101620),
        ],
        "Generated Content": [("dominic@duolingo.com", 542060447)],
    },
    "Monetization": {
        _AREA: [
            ("itai@duolingo.com", 2200982),
            ("vicky@duolingo.com", 241673612),
            ("cem@duolingo.com", 194829322),
            ("jay@duolingo.com", 605332),
            ("wes@duolingo.com", 803633967),
            ("jonathan.duxbury@duolingo.com", 446774430),
            ("hai@duolingo.com", 825435186),
            ("jtishler@duolingo.com", 120661234),
            ("hoshi@duolingo.com", 35950076),
            ("evelyn@duolingo.com", 46472964),
            ("kuo@duolingo.com", 504628953),
        ],
        _RECEIVE_ALL: [
            ("aspen@duolingo.com", 787642145),
            ("spotter@duolingo.com", 17782348),
            ("brock@duolingo.com", 516234),
            ("matt.long@duolingo.com", 1742400),
        ],
        "Ads": [
            ("kuo@duolingo.com", 504628953),
        ],
        "Subscription Packaging": [
            ("tower@duolingo.com", 290339876),
            ("joana@duolingo.com", 26339151),
            ("kuo@duolingo.com", 504628953),
        ],
        "ABC": [("daniel@duolingo.com", 330486311)],
        "Energy": [
            ("moses@duolingo.com", 57694070),
        ],
        "Max": [
            ("megan.bednarczyk@duolingo.com", 111864136),
            ("edwin@duolingo.com", 201732115),
        ],
        "Acquisition": [
            ("evelyn@duolingo.com", 46472964),
            ("jtishler@duolingo.com", 120661234),
            ("mopewa@duolingo.com", 347408),
        ],
    },
    "New Subjects": {
        _AREA: [("colleen@duolingo.com", 591143118)],
        _RECEIVE_ALL: [("tianyu@duolingo.com", 919037599)],
        "Math": [("colleen@duolingo.com", 591143118)],
    },
}


RECEIVE_ALL_AREA_REPORTS = [
    ("natalie@duolingo.com", 762020),
    ("hazel@duolingo.com", 526665044),
    ("simmy@duolingo.com", 106984765),
    ("ash@duolingo.com", 1252195),
    ("lauren@duolingo.com", 41638666),
]

RECEIVE_ALL_REPORTS = [
    ("blanca@duolingo.com", 36291958),
    ("caleb.noble@duolingo.com", 23133309),
    ("britni@duolingo.com", 875832803),
    ("rwagner@duolingo.com", 105023805),
    ("sharanya@duolingo.com", 105463277),
    ("aaron.wang@duolingo.com", 959205988),
    ("david.sawicki@duolingo.com", 334534112),
]


def get_employees() -> Tuple[List[Dict], List[Dict]]:
    """
    Returns a list of employees data.
    """
    employees_dal = app_registry(EmployeesDAL)
    employees = employees_dal.get_employees()
    teams = employees_dal.get_teams()
    return employees, teams


def determine_team_leads():
    """
    Determines the team leads for each team.
    """
    employees, teams = get_employees()
    id_to_employee = {employee["id"]: employee for employee in employees}
    team_to_leads = {}
    area_to_leads = {}
    for team in teams:
        if " - " in team["name"]:
            team_name = team["name"].split(" - ")[-1].strip()
            team_to_leads[team_name] = [
                (id_to_employee[id]["email"], id_to_employee[id]["duolingoId"])
                for id in team.get("leads", [])
            ]
        if "Area (no specific team)" in team["name"]:
            area_name = team["name"].split("Area (no specific team)")[0].strip()
            area_to_leads[area_name] = [
                (id_to_employee[id]["email"], id_to_employee[id]["duolingoId"])
                for id in team.get("leads", [])
            ]
    return team_to_leads, area_to_leads


def get_latest_recipient_groups():
    """
    Returns the latest team and are leads according to
    https://static.internal.duolingo.com/internal-tools/employees.json
    """
    team_to_leads, area_to_leads = determine_team_leads()
    recipient_groups = {}
    for area, teams in JIRA_FEATURES.items():
        recipient_groups[area] = {_AREA: area_to_leads.get(area, [])}
        for team in teams:
            recipient_groups[area][team] = team_to_leads.get(team, [])
    return recipient_groups


def get_email_body_html(report: QualityReport) -> str:
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIRECTORY))
    if isinstance(report, QualityReportArea):
        template = environment.get_template("area_email.html")
    else:
        template = environment.get_template("team_email.html")
    return template.render(report=report)


def _get_recipients(report: QualityReport) -> List[Tuple[str, Optional[int]]]:
    """
    Returns a list of recipients for each area or team.
    """
    recipients: List[Tuple[str, Optional[int]]] = []
    if isinstance(report, QualityReportArea):
        recipients = RECIPIENT_GROUPS[report.area][_AREA]
        recipients.extend(RECEIVE_ALL_AREA_REPORTS)
    else:
        if report.title not in RECIPIENT_GROUPS[report.area]:
            LOG.info(f"missing recipients for team: {report.title}")
            return []
        recipients = RECIPIENT_GROUPS[report.area][report.title]
    recipients.extend(RECIPIENT_GROUPS[report.area].get(_RECEIVE_ALL, []))
    recipients.extend(RECEIVE_ALL_REPORTS)
    return recipients


def send_email(report: QualityReport, recipient_override: Optional[str] = None):
    # Only production environment should sent emails
    if not _IS_PRODUCTION_ENV and recipient_override is None:
        return

    dict_to_track = {
        "email_type": f"quality_report_{report.title}",
        "ui_language": "en",
    }

    if report.area not in RECIPIENT_GROUPS:
        LOG.info(f"missing recipients for area: {report.area}")
        return

    if recipient_override is not None:
        recipients: List[Tuple[str, Optional[int]]] = [(recipient_override, None)]
    else:
        recipients = _get_recipients(report)

    for email, user_id in recipients:
        if email in _UNSUBSCRIBED:
            continue

        rb = RequestBuilder()
        dict_to_track["user_id"] = user_id

        rb.add_emails(
            [email],
            f"{report.title} Quality Score {report.score_breakdown.overall_score}",
            body_html=get_email_body_html(report),
            from_field='"Quality Report" <quality-reports@duolingo.com>',
            track={"email send": dict_to_track, "email open": dict_to_track},
        )
        rb.send_medium_priority()
        LOG.info(f"sent quality report email with title {report.title} to {email}")
