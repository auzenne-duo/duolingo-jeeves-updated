"""
APIs.
"""

import os
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    json,
    make_response,
    request,
    send_from_directory,
)
import logging


from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.lib.duplicate_detector import calculate_duplicates_for_JIRA_issue
from jeeves.manager.shakira import Shakira
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import (
    date_to_str,
    datetime_to_str,
    get_utc_today,
    time_series_str_to_datetime as str_to_datetime,
)

# This is being referenced by the application.py
blueprint_api = Blueprint("api", __name__)

_LOG = logging.getLogger("application")

_DEPLOYED_TIMESTAMP = datetime_to_str(get_utc_today())

_init_timestamp = datetime_to_str(get_utc_today())


@blueprint_api.route("/api/1/hello")
def say_hello():
    return json.jsonify({"msg": "hello"})


@blueprint_api.route("/api/1/<lang>/tickets", methods=["GET"])
def manage_tickets(lang):
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')

    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    page = int(request.args.get("page", "0"))
    word = request.args.get("word", "")

    beta_filter = request.args.get("beta_filter", None)
    if beta_filter and not any(beta_filter == strc.value for strc in ShakeToReportCategory):
        abort(make_response("Invalid value provided for beta_filter", 400))

    if request.args.get("start_time") == "-1":
        start_time = str_to_datetime(None)
        end_time = str_to_datetime(None)
    else:
        start_time = str_to_datetime(request.args.get("start_time"))
        end_time = str_to_datetime(request.args.get("end_time"))

    def get_tickets_by_word():
        limit = int(request.args.get("limit", "10"))

        paginated_info = ElasticDAL.get_recent_paginated_tickets(
            lang, word, page, limit, start_time, end_time, beta_filter
        )

        values = [ticket.serialize_to_json(ticket) for ticket in paginated_info["data"]]

        return_packet = {"data": values}
        return_packet.update({"total_records": paginated_info["total_records"]})

        if paginated_info["deepest_index"] < paginated_info["total_records"]:
            next_url_beta_filter = f"&beta_filter={beta_filter}" if beta_filter else ""
            return_packet.update(
                {
                    "next_url": f"/api/1/{lang}/tickets?word={word}&limit={limit}&page={page+1}{next_url_beta_filter}"
                }
            )

        return return_packet

    if request.method == "GET":
        response_data = get_tickets_by_word()

    return json.jsonify(response_data)


@blueprint_api.route("/api/1/<lang>/time_series")
def get_time_series_data(lang):
    # TODO: support more parameters such as category
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    word = request.args.get("word")
    if not word:
        abort(make_response("Please provide `word` parameter", 500))

    response_buckets = ElasticDAL.aggregate_time_series(lang, word)

    def bucket_to_value(bucket):
        date_val = str_to_datetime(bucket["key_as_string"])
        return {date_to_str(date_val): bucket["doc_count"]}

    tsd = {}
    for b in response_buckets:
        tsd.update(bucket_to_value(b))

    return json.jsonify({"values": tsd})


@blueprint_api.route("/api/1/<lang>/spikes")
def get_spike_data(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    # I could only get around this call with an ugly conditional statement.
    # At the very least, it should be pretty fast and the user won't notice.
    min_max_possible_dates = ElasticDAL.get_min_and_max_document_dates()

    start_date = request.args.get("start_date", min_max_possible_dates["min"])
    end_date = request.args.get("end_date", min_max_possible_dates["max"])

    spike_category = request.args.get("spike_category", "ALL_SPIKES")
    if spike_category not in SpikeCategory.__members__:
        abort(make_response(f"Invalid spike category {spike_category}", 400))

    stored_spikes = {}
    for spike in ElasticDAL.yield_spikes_in_date_range(lang, start_date, end_date, spike_category):
        if spike["date"] not in stored_spikes:
            stored_spikes[spike["date"]] = {"spike": []}
        stored_spikes[spike["date"]]["spike"].append((spike["score"], spike["word"]))
    for day in stored_spikes:
        stored_spikes[day]["spike"].sort(reverse=True)
    return json.jsonify(stored_spikes)


@blueprint_api.route("/api/1/<lang>/info")
def show_info(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    return json.jsonify(_get_status(lang))


@blueprint_api.route("/api/1/<lang>/init")
def do_init(lang):
    """
    Clear cache (and warm up).

    # TODO: Manage reset requirement info in memcache.
    """
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    global _init_timestamp
    _init_timestamp = datetime_to_str(get_utc_today())
    status = _get_status(lang)
    status["status"] = "ok"
    return json.jsonify(status)


@blueprint_api.route("/api/1/shake_to_report_tokens")
def get_shake_to_report_tokens():
    jira_token = os.environ.get("SHAKIRA_JIRA_API_TOKEN_IOS")
    slack_token = os.environ.get("SHAKIRA_SLACK_API_TOKEN")

    token_dict = {"jira": jira_token, "slack": slack_token}

    return json.jsonify(token_dict)


@blueprint_api.route("/api/1/shakira/features")
def get_jira_project_features():
    project = request.args.get("project")
    if project:
        project_error_message = Shakira.get_project_error_message(project)
        if project_error_message:
            abort(make_response(project_error_message, 400))
        features = Shakira.get_features(project)
    else:
        features = Shakira.get_features(["DLAI", "DLAA"])
    if features and len(features) > 0:
        return json.jsonify({"features": features})
    else:
        abort(make_response("Something went wrong retrieving feature options from Jira", 500))


@blueprint_api.route("/api/1/shakira/report_issue", methods=["POST"])
def report_issue():
    """
    Either create an issue in JIRA or post the screenshot to slack, depending on the feature and slack_channel fields.
    """
    try:
        issue_data = json.loads(request.form["issueData"])
        issue_status = Shakira.report_issue(
            project=issue_data["project"],
            feature=issue_data.get("feature"),
            client_specified_slack_channel_name=issue_data.get("slackChannel"),
            summary=issue_data["summary"],
            description=issue_data["description"],
            generated_description=issue_data.get("generatedDescription"),
            reporter_email=issue_data.get("reporterEmail"),
            pre_release=issue_data.get("preRelease", False),
            files=request.files,
        )
        if "error" in issue_status:
            message, code = issue_status["error"]
            abort(make_response(message, code))
        else:
            return json.jsonify(issue_status)
    except KeyError:
        abort(make_response("Missing required field(s)", 400))


@blueprint_api.route("/api/1/detect_duplicates")
def perform_duplicate_jira_detection():
    """
    Endpoint for running duplicate detection on JIRA records.
    Essentially just a wrapper around a library function so that we have an
    endpoint for that function.

    Parameters:
        issue_key (str): The issue key of the JIRA issue we wish to find
                         duplicates of. If this issue is not already in
                         Elasticsearch, we attempt to download it.

    Returns:
        A list of issue keys of suspected duplicate issues.
    """

    issue_key = request.args.get("issue_key")
    if not issue_key:
        abort(make_response("Please provide `issue_key` parameter.", 400))

    num_results = int(request.args.get("num_results", "5"))
    should_filter_project = request.args.get("should_filter_by_project", "0") != "0"

    return json.jsonify(
        [
            issue.serialize_to_json(issue)
            for issue in calculate_duplicates_for_JIRA_issue(
                issue_key, num_results=num_results, should_filter_project=should_filter_project
            )
        ]
    )


@blueprint_api.route("/api/1/direct_query", methods=["POST"])
def execute_arbitrary_query():
    json_data = request.get_json()

    print(json_data)

    return json.jsonify(
        [doc.serialize_to_json(doc) for doc in ElasticDAL.execute_arbitrary_query(json_data)]
    )


@blueprint_api.route("/", defaults={"path": ""})
@blueprint_api.route("/<path:path>")
def catch_all(path):
    """
    Serves the web client on any request that wasn't matched.
    The client will handle further routing.
    """
    if path != "" and os.path.exists("web/dist/" + path):
        return send_from_directory("web/dist", path)
    else:
        return send_from_directory("web/dist", "index.html")


def _get_status(lang):
    most_recent_elastic_timestamp = ElasticDAL.get_most_recent_timestamp(lang)

    return {
        "deployed_timestamp": _DEPLOYED_TIMESTAMP,
        "initialized_timestamp": _init_timestamp,
        "latest_ticket_timestamp": datetime_to_str(
            datetime.fromtimestamp(
                most_recent_elastic_timestamp if most_recent_elastic_timestamp else 0
            )
        ),
    }


def _is_language_supported(lang):
    return lang in [lang_name for lang_name, _ in SUPPORTED_LANGUAGES.__members__.items()]
