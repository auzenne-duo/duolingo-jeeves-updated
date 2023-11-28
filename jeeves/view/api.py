"""
APIs.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from duolingo_base.view.auth import requires_auth
from flask import Blueprint, Response, abort, g, json, make_response, request, send_from_directory

from jeeves import registry as app_registry
from jeeves.config.config import JIRA_PRIORITY_STR_TO_INT
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.lib.send_issue_fixed_emails import IssueFixedEmailSender
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.gpt_search_manager import (
    GPTSearchManager,
    GPTSearchStartedResponse,
    KNNSearchResponse,
)
from jeeves.manager.jira_feature_manager import JiraFeatureManager
from jeeves.manager.quality_report_manager import QualityReportManager
from jeeves.manager.query_helper import QueryHelper
from jeeves.manager.sentiment_search_manager import SentimentSearchManager
from jeeves.manager.shakira import ShakiraManager
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.scripts.update_priority_estimator import (
    get_s3_overridden_priorities,
    upload_s3_overridden_priorities,
)
from jeeves.util.date_util import (
    date_to_str,
    datetime_to_str,
    get_utc_today,
    time_series_str_to_datetime as str_to_datetime,
)
from jeeves.util.priority_estimator import PriorityEstimator

# This is being referenced by the application.py
blueprint_api = Blueprint("api", __name__)

_LOG = logging.getLogger("application")

_DEPLOYED_TIMESTAMP = datetime_to_str(get_utc_today())

_init_timestamp = datetime_to_str(get_utc_today())


@blueprint_api.route("/api/1/hello")
def say_hello():
    return json.jsonify({"msg": "hello"})


@blueprint_api.route("/query_params", methods=["GET"])
def get_query_params():
    query_string = request.args.get("q")
    if not query_string:
        abort(make_response("Please provide `q` parameter", 400))
    return json.jsonify(app_registry(QueryHelper).get_dsl_query_and_topics(query_string))


@blueprint_api.route("/api/1/<lang>/tickets", methods=["GET"])
def manage_tickets(lang):
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')

    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    jeeves_id = request.args.get("jeeves_id", None)

    spike_category = request.args.get("spike-category", "ALL_SPIKES")
    if spike_category not in SpikeCategory.__members__:
        abort(make_response(f"Invalid spike category {spike_category}", 400))
    use_lemmas = request.args.get("use-lemmas", "false") == "true"
    word = request.args.get("word", "")

    beta_filter = request.args.get("beta-filter", None)
    if beta_filter and not any(beta_filter == strc.value for strc in ShakeToReportCategory):
        abort(make_response("Invalid value provided for beta-filter", 400))

    if request.args.get("start_time") == "-1":
        start_time = str_to_datetime(None)
        end_time = str_to_datetime(None)
    else:
        start_time = str_to_datetime(request.args.get("start_time"))
        end_time = str_to_datetime(request.args.get("end_time"))

    def get_tickets_by_word():
        limit = int(request.args.get("limit", "10"))
        offset = int(request.args.get("offset", "0"))
        sort_id = request.args.get("sort-id", None)
        sort_id = int(sort_id) if sort_id else None
        prev_sort_id = request.args.get("prev-sort-id", None)
        prev_sort_id = int(prev_sort_id) if prev_sort_id else None

        paginated_tickets = app_registry(OpenSearchDAL).get_recent_paginated_tickets(
            lang,
            word,
            start_time,
            end_time,
            beta_filter,
            jeeves_id,
            limit,
            sort_id,
            prev_sort_id,
            offset,
            SpikeCategory[spike_category],
            use_lemmas,
            filter_jiras_from_jeeves=True,
        )

        tickets = paginated_tickets["data"]
        values = [ticket.serialize_to_json(ticket) for ticket in tickets]
        total_records = paginated_tickets["total_records"]

        return_packet = {"data": values, "total_records": total_records}
        if total_records > offset + len(values):
            return_packet["next_sort_id"] = paginated_tickets["sort_id"]
        if offset > 0:
            return_packet["prev_sort_id"] = paginated_tickets["prev_sort_id"]

        return return_packet

    if request.method == "GET":
        response_data = get_tickets_by_word()

    return json.jsonify(response_data)


@blueprint_api.route("/api/1/<lang>/time_series")
def get_time_series_data(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    word = request.args.get("word")
    if not word:
        abort(make_response("Please provide `word` parameter", 500))
    spike_category = request.args.get("spike-category", "ALL_SPIKES")
    if spike_category not in SpikeCategory.__members__:
        abort(make_response(f"Invalid spike category {spike_category}", 400))
    use_lemmas = request.args.get("use-lemmas", "false") == "true"
    beta_filter = request.args.get("beta-filter", None)
    if beta_filter:
        if beta_filter not in ShakeToReportCategory.__members__:
            abort(make_response("Invalid value provided for beta-filter", 400))
        beta_filter = ShakeToReportCategory[beta_filter]

    response_buckets = app_registry(OpenSearchDAL).aggregate_time_series(
        lang, SpikeCategory[spike_category], word, None, use_lemmas, beta_filter
    )

    if "ERROR" in response_buckets:
        return json.jsonify(response_buckets)

    def bucket_to_value(bucket):
        date_val = str_to_datetime(bucket["key_as_string"])
        return {date_to_str(date_val): bucket["doc_count"]}

    tsd = {}
    for b in response_buckets:
        tsd.update(bucket_to_value(b))

    return json.jsonify({"values": tsd})


@blueprint_api.route("/api/1/<lang>/spikes")
def get_spike_data(lang):
    if lang == "ALL":
        lang = None
    elif not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    # I could only get around this call with an ugly conditional statement.
    # At the very least, it should be pretty fast and the user won't notice.
    min_max_possible_dates = app_registry(OpenSearchDAL).get_min_and_max_document_dates()

    start_date = request.args.get("start_date", min_max_possible_dates["min"])
    end_date = request.args.get("end_date", min_max_possible_dates["max"])

    spike_category = request.args.get("spike_category", "ALL_SPIKES")
    if spike_category not in SpikeCategory.__members__:
        abort(make_response(f"Invalid spike category {spike_category}", 400))

    stored_spikes = {}
    for spike in app_registry(SpikeIndexDAL).yield_spikes_in_date_range(
        lang, start_date, end_date, spike_category
    ):
        stored_spikes.setdefault(spike.date, {"spike": []})
        stored_spikes[spike.date]["spike"].append(
            {
                "score": spike.score,
                "word": spike.word,
                "confirmed": spike.confirmed,
                "spike_id": spike.get_spike_id(),
                "confirmed_user_id": spike.confirmed_user_id,
                "email_sent_date": spike.email_sent_date,
                "email_user_id": spike.email_user_id,
                "fixed": spike.fixed,
                "fixed_user_id": spike.fixed_user_id,
                "summary": spike.summary,
                "is_bug": spike.is_bug,
                "experiment_spikes": [
                    {"experiment": k, "score": v} for k, v in spike.experiment_spikes.items()
                ],
                "lang": spike.lang,
                "status": spike.status,
                "status_user_id": spike.status_user_id,
            }
        )
    for day in stored_spikes:
        stored_spikes[day]["spike"].sort(key=lambda spike: spike["score"], reverse=True)
    return json.jsonify(stored_spikes)


@blueprint_api.route("/api/1/set_spike_confirm", methods=["PATCH"])
@requires_auth(permission="access-jeeves")
def set_spike_confirm():
    spike_id = request.json.get("spike_id")
    desired_state = request.json.get("desired_state")
    confirm_user_id = g.user_id
    app_registry(SpikeIndexDAL).set_spike_confirm_setting(spike_id, desired_state, confirm_user_id)
    return json.jsonify({"confirmed": desired_state, "confirm_user_id": confirm_user_id})


@blueprint_api.route("/api/1/set_spike_fixed", methods=["PATCH"])
@requires_auth(permission="access-jeeves")
def set_spike_fixed():
    try:
        spike_id = request.json["spike_id"]
        desired_state = request.json["desired_state"]
    except KeyError:
        abort(make_response("Missing required form data", 400))
    fixed_user_id = g.user_id
    app_registry(SpikeIndexDAL).set_spike_fixed_setting(spike_id, desired_state, fixed_user_id)
    return json.jsonify({"fixed": desired_state, "fixed_user_id": fixed_user_id})


@blueprint_api.route("/api/1/set_spike_status", methods=["PATCH"])
@requires_auth(permission="access-jeeves")
def set_spike_status():
    try:
        spike_id = request.json.get("spike_id")
        desired_state = request.json.get("desired_state")
    except KeyError:
        abort(make_response("Missing required form data", 400))
    status_user_id = g.user_id
    app_registry(SpikeIndexDAL).set_spike_status(spike_id, desired_state, status_user_id)
    return json.jsonify({"status": desired_state, "user_id": status_user_id})


@blueprint_api.route("/api/1/send_beta_emails", methods=["POST"])
@requires_auth(permission="access-jeeves")
def send_beta_emails():
    try:
        spike_id = request.json["spike_id"]
        description = request.json["description"]
    except KeyError:
        abort(make_response("Missing required form data", 400))
    if any([not spike_id, not description]):
        abort(make_response("Missing required form data", 400))

    user_id = g.user_id

    spike = app_registry(SpikeIndexDAL).get_spike_by_id(spike_id)
    if spike.email_sent_date:
        abort(make_response("Email already sent for this spike", 400))

    app_registry(SpikeIndexDAL).set_spike_email_sent(spike_id, user_id, date_to_str(datetime.now()))
    num_emails = app_registry(IssueFixedEmailSender).send_issue_fixed_emails(spike, description)
    return json.jsonify({"email_user_id": user_id, "num_emails": num_emails})


@blueprint_api.route("/api/1/<lang>/spike_stats")
def get_spike_stats(lang):
    min_max_possible_dates = app_registry(SpikeIndexDAL).get_min_and_max_spike_dates()
    start_date = request.args.get("start_date", min_max_possible_dates["min"])
    end_date = request.args.get("end_date", min_max_possible_dates["max"])
    spike_category = request.args.get("spike_category", default="ALL_SPIKES")
    spike_threshold = request.args.get("spike_threshold", default=3)
    return json.jsonify(
        app_registry(SpikeIndexDAL).calculate_spike_stats(
            lang,
            spike_category,
            spike_threshold=spike_threshold,
            start_date=start_date,
            end_date=end_date,
        )
    )


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
    """
    Endpoint for API tokens for Jira and Slack.
    Clients use them for displaying screenshot previews of duplicate Jira issues.

    Returns:
        A dictionary of API tokens for Jira and Slack.
    """
    project = request.args.get("project")

    token_dict = app_registry(ShakiraManager).get_shake_to_report_tokens(project)

    return json.jsonify(token_dict)


@blueprint_api.route("/api/1/shakira/features")
def get_jira_project_features():
    jira_feature_manager = app_registry(JiraFeatureManager)

    project = request.args.get("project")
    if project:
        project_error_message = app_registry(ShakiraManager).get_project_error_message(project)
        if project_error_message:
            abort(make_response(project_error_message, 400))
        features = jira_feature_manager.get_features_v1(project)
    else:
        features = jira_feature_manager.get_features_v1(["DLAA", "DLAI", "DLAW"])
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
        issue_status = app_registry(ShakiraManager).report_issue(
            project=issue_data["project"],
            feature=issue_data.get("feature"),
            slack_report_type=None,
            client_specified_slack_channel_name=issue_data.get("slackChannel"),
            related_issue_key=issue_data.get("relatedJiraTicket"),
            summary=issue_data["summary"],
            description=issue_data.get("description"),
            generated_description=issue_data.get("generatedDescription"),
            reporter_email=issue_data.get("reporterEmail"),
            pre_release=issue_data.get("preRelease", False),
            release_blocker=issue_data.get("releaseBlocker", False),
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
                         OpenSearch, we attempt to download it.

    Returns:
        A list of suspected duplicate issues.
    """
    issue_key = request.args.get("issue_key")
    if not issue_key:
        abort(make_response("Please provide `issue_key` parameter.", 400))

    num_results = int(request.args.get("num_results", "5"))
    should_filter_project = request.args.get("should_filter_by_project", "0") != "0"
    max_search_depth = int(request.args.get("max_search_depth", "50"))

    include_parent_issues = request.args.get("include_parent_issues", "0") != "0"

    return json.jsonify(
        [
            issue.serialize_to_json(issue)
            for issue in app_registry(OpenSearchDAL).find_potential_jira_duplicates(
                issue_key,
                num_results=num_results,
                should_filter_project=should_filter_project,
                max_search_depth=max_search_depth,
                use_parent_issues=include_parent_issues,
            )
        ]
    )


@blueprint_api.route("/api/1/direct_query", methods=["POST"])
def execute_arbitrary_query():
    json_data = request.get_json()

    print(json_data)

    return json.jsonify(
        [
            doc.serialize_to_json(doc)
            for doc in app_registry(OpenSearchDAL).execute_arbitrary_query(json_data)
        ]
    )


@blueprint_api.route("/api/1/mark_jira_duplicates", methods=["POST"])
def cement_duplicates():
    out_key = request.args.get("outward_key", "")
    in_key = request.args.get("inward_key", "")

    if not out_key or not in_key:
        abort(make_response("Please provide both `outward_key` and `inward_key`.", 400))

    remote_success = app_registry(DuplicateGraphResolver).try_mark_duplicate_remote(out_key, in_key)
    if not remote_success:
        abort(
            make_response(
                "The JIRA API returned an error. Please make sure both of your keys exist and try again later. If this error persists, please contact the repository owner.",
                400,
            )
        )

    return json.jsonify({"Link": "Created"})


@blueprint_api.route("/api/1/submit_duplicates", methods=["POST"])
def submit_duplicates():
    """
    Wrapper around mark_jira_duplicates that allows submitting multiple duplicates,
    for use by Shakira clients.

    Post body parameters:
        newIssue (str): The key of the newly created Jira issue
        duplicates (list[str]): The keys of Jira issues to be linked
    """
    try:
        data = request.get_json()
        in_key = data["newIssue"]
        out_keys = data["duplicates"]
        if not isinstance(out_keys, list):
            out_keys = [out_keys]
        elif len(out_keys) == 0:
            abort(make_response("Please specify at least one duplicate", 400))
        remote_successes = [
            app_registry(DuplicateGraphResolver).try_mark_duplicate_remote(out_key, in_key)
            for out_key in out_keys
        ]
        if False in remote_successes:
            abort(
                make_response(
                    "Something went wrong. Make sure your issue keys exist or let #team-test-and-release-infrastructure know.",
                    400,
                )
            )
        return json.jsonify({"Links": "Created"})
    except KeyError:
        abort(make_response("Missing required field(s)", 400))


@blueprint_api.route("/api/1/fully_connect_duplicates", methods=["POST"])
def fully_connect_duplicates():
    """
    API wrapper around DuplicateGraphResolver.connect_duplicates_remote().
    Will add duplicate relations between issues until the degree of separation
    every issue with a finite degree of separation from any issue listed in the
    input becomes at most 1 (an issue is separated from itself by degree 0).
    Although the code supporting this route is tolerant to empty input, I can't
    think of a situation where an end user would intentionally submit empty
    input to this route, so empty input is considered an error. Submitting input
    of size 1 is NOT an error, in case an end user wants to make the duplicate
    graph of an arbitrary issue become fully connected.

    POST Body Parameters:
        issue_keys: Required; a list of issue keys around which we want to
                    create a fully connected duplicate graph. These issues
                    will be included in the final graph, as well as any
                    duplicates of these issues, as well as any duplicates of
                    those duplicates, and so on.
    """
    data = request.get_json()
    if (data is None) or ("issue_keys" not in data) or (not data["issue_keys"]):
        abort(make_response("Please provide a list of issue_keys to interconnect.", 400))
    issue_keys = data["issue_keys"]
    if isinstance(issue_keys, str):
        issue_keys = [issue_keys]

    result_manifest = app_registry(DuplicateGraphResolver).connect_duplicates_remote(issue_keys)
    first_line = result_manifest.split("\n")[0]
    result_dict = {"overall": first_line, "manifest": result_manifest}
    return json.jsonify(result_dict)


@blueprint_api.route("/api/2/shakira/slack_report_types")
def get_slack_report_types():
    """
    Returns information about report types that can be sent to Slack.

    Returns a list of JSON objects with the following fields:
        name (str): The name of the Slack report type.
        alsoPostsToJira (bool): Whether this Slack report type also creates an associated Jira issue.
    """
    return json.jsonify(app_registry(ShakiraManager).get_slack_report_types())


@blueprint_api.route("/api/2/shakira/features_by_team_and_area")
def get_features_by_team_and_area():
    """
    Returns a list of features, organized by area and team.
    """
    jira_feature_manager = app_registry(JiraFeatureManager)
    areasWithTeams = jira_feature_manager.get_features_by_team_and_area()
    if areasWithTeams and len(areasWithTeams) > 0:
        return json.jsonify(areasWithTeams)
    else:
        abort(make_response("Something went wrong retrieving feature options from Jira", 500))


@blueprint_api.route("/api/2/shakira/suggested_features")
def get_suggested_features():
    """
    Endpoint for detecting suggested Jira features for a bug report.
    Essentially just a wrapper around a library function so that we have an
    endpoint for that function.

    Parameters:
        project (str): The Jira project to get features from.
        summary (str): The summary of the issue.
        description (str): A more in-depth description of the issue.
        generated_description (str): Autogenerated metadata about the issue.

    Returns:
        suggested_features (str[]): The features suggested by the JiraFeatureManager.
        other_features (str[]): Other Jira features that the user may choose from.
    """
    project = request.args.get("project")
    summary = request.args.get("summary")
    if not summary:
        abort(make_response("Please provide `summary` parameter.", 400))
    description = request.args.get("description")
    generated_description = request.args.get("generated_description")

    jira_feature_manager = app_registry(JiraFeatureManager)

    if project:
        project_error_message = app_registry(ShakiraManager).get_project_error_message(project)
        if project_error_message:
            abort(make_response(project_error_message, 400))
        features = jira_feature_manager.get_suggested_features(
            project, summary, description, generated_description
        )
    else:
        features = jira_feature_manager.get_suggested_features(
            ["DLAA", "DLAI", "DLAW"], summary, description, generated_description
        )

    if features and len(features["other_features"]) > 0:
        return json.jsonify(features)
    else:
        abort(make_response("Something went wrong retrieving feature options from Jira", 500))


@blueprint_api.route("/api/2/shakira/report_issue", methods=["POST"])
def report_issue_v2():
    """
    Create an issue in JIRA and/or post the issue to Slack, depending on the feature and slackReportType fields.
    """
    try:
        issue_data = json.loads(request.form["issueData"])
        issue_status = app_registry(ShakiraManager).report_issue(
            project=issue_data["project"],
            feature=issue_data.get("feature"),
            slack_report_type=issue_data.get("slackReportType"),
            client_specified_slack_channel_name=None,
            related_issue_key=issue_data.get("relatedJiraTicket"),
            summary=issue_data["summary"],
            description=issue_data.get("description"),
            generated_description=issue_data.get("generatedDescription"),
            reporter_email=issue_data.get("reporterEmail"),
            pre_release=issue_data.get("preRelease", False),
            release_blocker=issue_data.get("releaseBlocker", False),
            files=request.files,
        )
        if "error" in issue_status:
            message, code = issue_status["error"]
            abort(make_response(message, code))
        else:
            return json.jsonify(issue_status)
    except KeyError:
        abort(make_response("Missing required field(s)", 400))


@blueprint_api.route("/api/2/shakira/estimate_priority")
def get_estimate_priority():
    """
    Endpoint for estimating priority for a Jira bug report.

    Parameters:
        summary (str): The summary of the issue.
        feature (str): The jira feature of the issue.
        reporter_email (str): email address of the reporter such as duo@duolingo.com

    Returns:
        priority (str): Jira priority as Low, Medium, or High
    """
    summary = request.args.get("summary")
    feature = request.args.get("feature", "")
    reporter_email = request.args.get("reporter_email", "")
    if not summary:
        abort(make_response("Please provide `summary` parameter.", 400))
    priority = PriorityEstimator.estimate_priority(summary, feature, reporter_email)
    return json.jsonify(priority)


@blueprint_api.route("/api/2/shakira/update_priority_estimator", methods=["POST"])
def update_priority_estimator():
    """
    Endpoint for updating the priority estimator model given true data

    Parameters:
        issue_key (str): Jira issue key
        summary (str): The summary of the issue.
        feature (str): The jira feature of the issue.
        reporter_email (str): email address of the reporter such as duo@duolingo.com
        priority (str): true priority
    """
    issue_key = request.form.get("issue_key")
    if not issue_key:
        abort(make_response("Please provide the issue key.", 400))
    summary = request.form.get("summary")
    feature = request.form.get("feature", "")
    reporter_email = request.form.get("reporter_email", "")
    priority = request.form.get("priority")
    if priority not in JIRA_PRIORITY_STR_TO_INT:
        abort(make_response(f"Invalid `priority` parameter: {priority}.", 400))

    overridden_priorities = get_s3_overridden_priorities()
    if issue_key in overridden_priorities:
        return f"Model already updated with issue {issue_key}."
    updated_priority = {
        issue_key: {
            "summary": summary,
            "feature": feature,
            "reporter_email": reporter_email,
            "priority": priority,
            "date_stored": date_to_str(datetime.now()),
        }
    }
    data = [PriorityEstimator.format_data(summary, feature, reporter_email)]
    PriorityEstimator.fit_to_data(data, [JIRA_PRIORITY_STR_TO_INT[priority]])
    overridden_priorities.update(updated_priority)
    upload_s3_overridden_priorities(overridden_priorities)
    return f"Done fitting {data} to {priority}"


@blueprint_api.route("/api/1/spike_categories")
def get_spike_categories():
    """
    Returns list of spike categories
    """
    return json.jsonify(
        [{"value": member.name, "text": member.display_name} for member in SpikeCategory]
    )


@blueprint_api.route("/api/3/gpt_search", methods=["POST"])
@blueprint_api.route("/api/3/nlp_search", methods=["POST"])
async def gpt_search() -> Response:
    """
    Entrypoint for GPT Search. Sends to GPT the top results from the OpenSearch index that match the user's query and
      asks it to answer the user's question using this as context (or summarize the results if no question is provided).

    Accepts a POST request with a JSON body containing the following fields:
    - `q` (str): The user's query typed into the search box
    - `max_search_depth` (int): The maximum number of search results to consider in the k-NN search. Defaults to 50.
    - `num_results` (int): The number of results to return. Defaults to 5.
    """
    query = request.args.get("q")
    if not query:
        error_response = GPTSearchStartedResponse(
            {}, "", "Please provide a query text parameter `q`."
        )
        abort(make_response(json.jsonify(error_response), 400))

    max_search_depth = int(request.args.get("max_search_depth", "50"))
    num_results = int(request.args.get("num_results", "5"))

    result = await app_registry(GPTSearchManager).gpt_search(query, max_search_depth, num_results)
    if result.error:
        abort(make_response(json.jsonify(result), 500))

    return json.jsonify(result)


@blueprint_api.route("/api/3/gpt_search/knn_results/<request_id>", methods=["GET"])
def gpt_search_get_knn_results(request_id: str) -> Dict[str, Any]:
    """
    The second request sent by the browser to the Jeeves API in the course of a GPT Search. Polls the memcached table
      until the results of the k-NN search are set (IDs only), and then returns the full results from the OpenSearch
      index with a multi-get request.

    Accepts a GET request with the following path parameter:
    - `request_id` (str): The hash returned by /gpt_search used to track the user's request

    Returns a JSON response with the following fields:
    - `error` (Optional[str]): A description of the error to display to the user.
    - `docs` (list[JeevesDocument]): The results of the k-NN search
    """
    if not request_id:
        error_response = KNNSearchResponse([], "Please provide a path parameter `request_id`.")
        abort(make_response(json.jsonify(error_response), 400))

    result = app_registry(GPTSearchManager).wait_for_knn_results(request_id)
    if result.error:
        abort(make_response(json.jsonify(result), 500))

    return result.to_json()


@blueprint_api.route("/api/3/gpt_search/answer/<request_id>", methods=["GET"])
def gpt_search_get_answer(request_id: str) -> Dict[str, Any]:
    """
    The third request sent by the browser to the Jeeves API in the course of a GPT Search. Polls the memcached table
      until the results of the OpenAI /chat/completions call is set, parses the results and returns them to the browser.

    Accepts a GET request with the following path parameter:
    - `request_id` (str): The hash returned by /gpt_search used to track the user's request

    Returns a JSON response with the following fields:
    - `error` (Optional[str]): A description of the error to display to the user.
    - `answer` (str): The answer to the user's question per the OpenAI /chat/completions response.
    - `supporting_docs` (list[GPTSearchResult]): The documents that best support the answer according to GPT.
    """
    if not request_id:
        error_response = KNNSearchResponse([], "Please provide a path parameter `request_id`.")
        abort(make_response(json.jsonify(error_response), 400))

    result = app_registry(GPTSearchManager).wait_for_gpt_answer(request_id)
    if result.error:
        abort(make_response(json.jsonify(result), 500))

    return result.to_dict()


@blueprint_api.route("/api/3/sentiment_time_series", methods=["GET"])
def sentiment_search():
    query = request.args.get("q")
    if not query:
        abort(make_response("Please provide a query text parameter `q`.", 400))

    result = app_registry(SentimentSearchManager).sentiment_search(query)
    return json.jsonify(result)


@blueprint_api.route("/api/3/quality_report", methods=["GET"])
def quality_report():
    """
    Returns high level quality report data for all areas for the quality report landing page
    """
    return json.jsonify({"areas": app_registry(QualityReportManager).get_area_quality_overviews()})


@blueprint_api.route("/api/3/quality_report_area", methods=["GET"])
def quality_report_area():
    """
    Retrieves the most recently generated quality report data for a specifc area along with quality report data for that area's teams
    """
    area = request.args.get("area")
    if not area:
        abort(make_response("Please provide an area parameter.", 400))

    return app_registry(QualityReportManager).get_serialized_quality_report(area)


@blueprint_api.route("/api/3/quality_report_team", methods=["GET"])
def quality_report_team():
    """
    Retrieves the most recently generated quality report data for a specifc team
    """
    team = request.args.get("team")
    if not team:
        abort(make_response("Please provide a team parameter.", 400))

    return app_registry(QualityReportManager).get_serialized_quality_report(team)


@blueprint_api.route("/", defaults={"path": ""})
@blueprint_api.route("/<path:path>")
def catch_all(path):
    """
    Serves the web client on any request that wasn't matched.
    The client will handle further routing.
    """
    base_path = "web/dist/"
    fullpath = os.path.normpath(os.path.join(base_path, path))
    if not fullpath.startswith(base_path) or path == "" or not os.path.exists(fullpath):
        return send_from_directory(base_path, "index.html")
    else:
        return send_from_directory(base_path, path)


def _get_status(lang):
    most_recent_opensearch_timestamp = app_registry(OpenSearchDAL).get_most_recent_timestamp(lang)

    return {
        "deployed_timestamp": _DEPLOYED_TIMESTAMP,
        "initialized_timestamp": _init_timestamp,
        "latest_ticket_timestamp": datetime_to_str(
            datetime.fromtimestamp(
                most_recent_opensearch_timestamp if most_recent_opensearch_timestamp else 0
            )
        ),
    }


def _is_language_supported(lang):
    return lang in [lang_name for lang_name, _ in SUPPORTED_LANGUAGES.__members__.items()]
