"""
Script that sends weekly bug digest emails to bug reporters.

Add your @duolingo.com email address to the _UNSUBSCRIBED list in order to unsubscribe.
"""

import logging
from typing import Dict, List, Optional, Tuple

from duolingo_notify.api import RequestBuilder
from jinja2 import Environment, FileSystemLoader

from jeeves import registry as app_registry
from jeeves.config.config import get_config
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.employees import EmployeesDAL
from jeeves.model.quality_report import QualityReport, QualityReportArea, QualityReportPillar
from jeeves.util.quality_report_util import TEMPLATE_DIRECTORY

LOG = logging.getLogger(__name__)

_UNSUBSCRIBED = ["example@duolingo.com"]
_IS_PRODUCTION_ENV = get_config().get_nested(["environment"]) == "prod"

_AREA = "AREA"
_RECEIVE_ALL = "RECEIVE_ALL"
_PILLAR = "PILLAR"
# This list is mostly based on the data from the orgchart:
# https://static.internal.duolingo.com/colombo/orgchart/orgchart.html#onboarding
# You can run get_latest_recipient_groups function to get the latest mapping of recipients


RECIPIENT_GROUPS: Dict[str, Dict[str, List]] = {
    "Growth": {
        _PILLAR: [],
        "International Growth": {
            _AREA: [
                ("colombo@duolingo.com", 65494655),
                ("hideki@duolingo.com", 1076),
                ("kevinyang@duolingo.com", 3057357),
                ("rock@duolingo.com", 95438),
                ("soyee@duolingo.com", 969088226),
                ("yao@duolingo.com", 576008906),
                ("yudi@duolingo.com", 535711458),
            ],
            "China": [
                ("elriczhong@duolingo.com", 338612774),
                ("kevinyang@duolingo.com", 3057357),
                ("tao@duolingo.com", 515653291),
                ("yang@duolingo.com", 1257270812),
            ],
            "Momentum": [
                ("momentum-team@duolingo.com", None),
            ],
            "Re-Onboarding": [
                ("allen.wang@duolingo.com", 975446875),
                ("elriczhong@duolingo.com", 338612774),
                ("xiao@duolingo.com", 15625523),
            ],
        },
        "Area - Retention": {
            _AREA: [("antonia@duolingo.com", 190618), ("jackson@duolingo.com", 19364437)],
            "Reengagement": [
                ("osman@duolingo.com", 555374397),
                ("reengagement-engineering@duolingo.com", None),
                ("sameer@duolingo.com", 497392481),
                ("soyee@duolingo.com", 969088226),
            ],
            "Retention": [
                ("retention-engineering@duolingo.com", None),
                ("retention-pm@duolingo.com", None),
            ],
            "Notifications": [
                ("cailyn@duolingo.com", 507747809),
                ("notifications-team@duolingo.com", None),
            ],
        },
        "no_area_growth": {
            _AREA: [],
            "Delight": [
                ("delight-team@duolingo.com", None),
            ],
            "Social Engagement": [
                ("lilly@duolingo.com", 425432603),
                ("rsalvador@duolingo.com", 591913431),
                ("social-engagement-engineering@duolingo.com", None),
            ],
            "Social Network": [
                ("amia@duolingo.com", 48361939),
                ("social-network-engineering@duolingo.com", None),
            ],
        },
        _RECEIVE_ALL: [
            ("hideki@duolingo.com", 1076),
            ("mpereslucha@duolingo.com", 759837354),
            ("ningxin@duolingo.com", 510539986),
        ],
    },
    "Platform": {
        _PILLAR: [],
        "Design Accelerator": {
            _AREA: [
                ("colombo@duolingo.com", 65494655),
                ("shawn.buessing@duolingo.com", 18288193),
                ("fabio@duolingo.com", 606042449),
            ],
            "Design Systems": [
                ("chris.lock@duolingo.com", 576224004),
            ],
        },
        "Infra Platform": {
            _AREA: [
                ("fabio@duolingo.com", 606042449),
                ("peter@duolingo", 97197056),
            ],
            "Engineering Studio": [
                ("becky@duolingo.com", 614576367),
            ],
            "Stability and Performance": [
                ("leon@duolingo.com", 233506),
                ("caesar@duolingo.com", 197953187),
            ],
        },
    },
    "Language Learning": {
        "Long-form Learning": {
            _AREA: [
                ("cindy@duolingo.com", 235522446),
                ("peng@duolingo.com", 450156231),
                ("jesse.bentert@duolingo.com", 233807586),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
            "Intermediate Experience": [
                ("janelle@duolingo.com", 319711134),
                ("katherine.wallace@duolingo.com", 84534537),
                ("liz@duolingo.com", 461557793),
                ("peng@duolingo.com", 450156231),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
            "Reading & Writing": [
                ("toby@duolingo.com", 384994779),
                ("catherine@duolingo.com", 1163461734),
                ("peng@duolingo.com", 450156231),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
            "Listening & Speaking": [
                ("michael@duolingo.com", 15587805),
                ("peng@duolingo.com", 450156231),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
        },
        "Short-form Learning": {
            _AREA: [
                ("luis.mas@duolingo.com", 1053329023),
                ("jenna@duolingo.com", 139182230),
                ("anand@duolingo.com", 1008909),
                ("leow@duolingo.com", 551030521),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
            "Short Form Experience": [
                ("luis.mas@duolingo.com", 1053329023),
                ("jenna@duolingo.com", 139182230),
                ("anand@duolingo.com", 1008909),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
            "GRID": [
                ("jackie.lee@duolingo.com", 2364552),
                ("margarita@duolingo.com", 508749189),
                ("lisa@duolingo.com", 111849862),
                ("anand@duolingo.com", 1008909),
                ("jessica@duolingo.com", 521621716),
                ("matt.long@duolingo.com", 1742400),
                ("rwagner@duolingo.com", 105023805),
            ],
        },
        "Video Call": {
            _AREA: [("yash@duolingo.com", 59192169), ("zan@duolingo.com", 1280054)],
            "Video Call Backend Foundations": [],
            "Video Call Experience": [],
            "Video Call Growth": [],
            "Video Call Scaffolding": [],
        },
        _PILLAR: [],
        _RECEIVE_ALL: [],
    },
    "Monetization": {
        _PILLAR: [],
        _RECEIVE_ALL: [
            ("aspen@duolingo.com", 787642145),
            ("spotter@duolingo.com", 17782348),
            ("brock@duolingo.com", 516234),
            ("ben.warsaw@duolingo.com", 404507680),
        ],
        "no_area_monetization": {
            _AREA: [],
            "Conversion": [
                ("tower@duolingo.com", 290339876),
                ("sue@duolingo.com", 411492851),
            ],
            "Energy": [
                ("moses@duolingo.com", 57694070),
            ],
            "Max": [
                ("evelyn@duolingo.com", 46472964),
                ("nozymko@duolingo.com", 270487647),
            ],
            "Acquisition": [
                ("mopewa@duolingo.com", 347408),
            ],
            "Ads": [
                ("enrique@duolingo.com", 50624505),
            ],
            "Monetization Engine": [],
            "Crossgrades": [
                ("kuo@duolingo.com", 504628953),
                ("xingyu@duolingo.com", 123603875),
            ],
        },
    },
    "New Subjects": {
        "Math": {
            _AREA: [
                ("colleen@duolingo.com", 591143118),
                ("lizn@duolingo.com", 288283957),
                ("vanessa@duolingo.com", 160465455),
            ],
            "Math Infrastructure": [],
            "Math Motivation": [],
            "Math Skills": [],
        },
        "Music": {
            _AREA: [
                ("colleen@duolingo.com", 591143118),
                ("lizn@duolingo.com", 288283957),
                ("vanessa@duolingo.com", 160465455),
                ("or@duolingo.com", 50664284),
            ],
            "Music Instruments": [],
            "Music Motivation": [],
            "Music Songs": [],
        },
        _PILLAR: [],
        _RECEIVE_ALL: [("tianyu@duolingo.com", 919037599)],
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
    ("caleb.noble@duolingo.com", 23133309),
    ("britni@duolingo.com", 875832803),
    ("rwagner@duolingo.com", 105023805),
    ("guanhua@duolingo.com", 909564076),
]

AREA_TO_EXCLUDE = ["no_area_growth", "no_area_monetization", "no_area_new_subjects"]


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
    for pillar in JIRA_FEATURES:
        for area, teams in JIRA_FEATURES[pillar].items():
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
    if isinstance(report, QualityReportPillar):
        recipients = RECIPIENT_GROUPS[report.pillar][_PILLAR]
    elif isinstance(report, QualityReportArea):
        areas = RECIPIENT_GROUPS[report.pillar]
        if report.area in AREA_TO_EXCLUDE:
            return []
        if report.area in areas:
            recipients = areas[report.area][_AREA]
            recipients.extend(RECEIVE_ALL_AREA_REPORTS)
        else:
            LOG.info(f"missing recipients for area: {report.area}")
            return []
    else:
        areas = RECIPIENT_GROUPS[report.pillar]
        teams = areas.get(report.area, {})
        if report.title not in teams:
            LOG.info(f"missing recipients for team: {report.title}")
            return []
        recipients = teams.get(report.title, [])
    recipients.extend(RECIPIENT_GROUPS[report.pillar].get(_RECEIVE_ALL, []))
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

    if report.pillar not in RECIPIENT_GROUPS:
        LOG.info(f"missing recipients for pillar: {report.pillar}")
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
