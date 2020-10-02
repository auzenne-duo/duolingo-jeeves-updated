"""
APIs.
"""

from datetime import datetime


from flask import Blueprint, abort, json, make_response, redirect, render_template, request
import logging
import random


from jeeves.dal.elasticsearch_interface import ElasticDAL


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

# Append this to resource URLs (i.e. JS and CSS) to avoid caching.
_RANDOM = random.randint(0, 1000000)

_DEPLOYED_TIMESTAMP = datetime_to_str(get_utc_today())

_init_timestamp = datetime_to_str(get_utc_today())


@blueprint_api.route("/api/1/hello")
def say_hello():
    return json.jsonify({"msg": "hello"})


@blueprint_api.route("/<lang>")
def show_index(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    return render_template("index.html", random=_RANDOM, lang=lang)


@blueprint_api.route("/")
def no_lang():
    return redirect("/en")


@blueprint_api.route("/<lang>/annotation")
def show_train_jeeves(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    return render_template("annotation.html", random=_RANDOM, lang=lang)


@blueprint_api.route("/<lang>/analysis")
def show_analysis(lang):
    print("Entered show_analysis", flush=True)
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    print("Passed show_analysis lang check", flush=True)
    return render_template("analysis.html", random=_RANDOM, lang=lang)


@blueprint_api.route("/<lang>/spike")
def show_spike(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    return render_template("spike.html", random=_RANDOM, lang=lang)


@blueprint_api.route("/api/1/<lang>/tickets", methods=["GET"])
def manage_tickets(lang):
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')

    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    page = int(request.args.get("page", "0"))
    word = request.args.get("word")

    if request.args.get("start_time") == "-1":
        start_time = str_to_datetime(None)
        end_time = str_to_datetime(None)
    else:
        start_time = str_to_datetime(request.args.get("start_time"))
        end_time = str_to_datetime(request.args.get("end_time"))

    def get_tickets_by_word():
        limit = int(request.args.get("limit", "10"))

        tickets = ElasticDAL.get_recent_paginated_tickets(
            lang, word, page, limit, start_time, end_time
        )

        values = [
            ticket.subserialize(
                "ticket_id",
                "date_time",
                "subject",
                "description",
                "priority",
                "via",
                "tags",
                "requester_id",
                "metadata",
                "data_source",
            )
            for ticket in tickets
        ]
        return {
            "data": values,
            "next_url": f"/api/1/{lang}/tickets?word={word}&limit={limit}&page={page+1}",
        }

    if request.method == "GET":
        if word:
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

    stored_spikes = {}
    for spike in ElasticDAL.yield_all_spikes(lang):
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
