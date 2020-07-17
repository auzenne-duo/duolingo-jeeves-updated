"""
APIs.
"""
from flask import Blueprint, abort, json, make_response, redirect, render_template, request
import logging
import numpy as np
import random

from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.dal.spikes import SpikeDAL
from jeeves.lib.time_series_generator import (
    get_metadata_distribution,
    get_most_recent_ticket_timestamp,
    get_paginated_tickets,
    get_recent_tickets_by_word,
    get_time_series,
    get_viable_categories_in_metadata_distribution,
    match_description,
)
from jeeves.model.categories import CATEGORIES
from jeeves.model.metadata import Metadata
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.model.time_series import ticket_almanac
from jeeves.util.date_util import (
    datetime_to_str,
    get_utc_today,
    time_series_str_to_datetime as str_to_datetime,
)
from jeeves.util.score import pearsons_coefficient, cosine_similarity

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


@blueprint_api.route("/api/1/<lang>/tickets", methods=["GET", "PATCH"])
def manage_tickets(lang):
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')

    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))

    page = int(request.args.get("page", "0"))
    word = request.args.get("word")
    start_time = str_to_datetime(request.args.get("start_time", None))
    end_time = str_to_datetime(request.args.get("end_time", None))
    meta_filter = Metadata.from_string(request.args.get("meta_filter", "{}"))

    def get_tickets_by_word():
        limit = int(request.args.get("limit", "10"))
        tickets = get_recent_tickets_by_word(
            lang, word, start_time=start_time, end_time=end_time, meta_filter=meta_filter
        )
        tickets = get_paginated_tickets(lang, page, limit, dataframe=tickets)
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
            )
            for ticket in tickets
        ]
        return {
            "data": values,
            "next_url": f"/api/1/{lang}/tickets?word={word}&limit={limit}&page={page+1}",
        }

    def get_tickets_for_annotation():
        def replace(d, field, fn):
            d[field] = fn(d[field])
            return d

        limit = int(request.args.get("limit", "10"))
        tickets = get_paginated_tickets(lang, page, limit)
        category_list = sorted(cat.name for cat in CATEGORIES)
        # Adding more categories for demo purpose
        category_list += [
            "feature_request",
            "language_request",
            "requesting_reply",
            "challenge_feedback",
            "schools",
            "iap_refunds",
            "streak_issue",
            "forum_abuse",
        ]
        values = [
            replace(
                d=ticket.subserialize(
                    "ticket_id", "date_time", "subject", "description", "category_labels"
                ),
                field="category_labels",
                fn=lambda cl: {cat: cat in cl for cat in category_list}
                if cl
                else {cat: False for cat in category_list},
            )
            for ticket in tickets
        ]
        return {"data": values, "next_url": f"/api/1/{lang}/tickets?limit={limit}&page={page+1}"}

    if request.method == "GET":
        if word:
            response_data = get_tickets_by_word()
        else:
            response_data = get_tickets_for_annotation()
    elif request.method == "PATCH":
        response_data = CategoryAnnotationDAL.bulk_save_annotations(request.get_json())
    return json.jsonify(response_data)


@blueprint_api.route("/api/1/<lang>/time_series")
def get_time_series_data(lang):
    # TODO: support more parameters such as category
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    word = request.args.get("word")
    meta_filter = Metadata.from_string(request.args.get("meta_filter", "{}"))
    if not word:
        abort(make_response("Please provide `word` parameter", 500))
    return json.jsonify(get_time_series(lang, word, meta_filter=meta_filter))


@blueprint_api.route("/api/1/<lang>/spikes")
def get_spike_data(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    return json.jsonify(SpikeDAL.get_spikes(lang))


score_map = dict(pearsons=pearsons_coefficient, cosine=cosine_similarity)


@blueprint_api.route("/api/1/<lang>/metadata_analyze")
def get_ticket_metadata(lang):
    if not _is_language_supported(lang):
        abort(make_response("Requested language not supported", 400))
    word = request.args.get("word")
    start_time = str_to_datetime(request.args.get("start_time", None))
    end_time = str_to_datetime(request.args.get("end_time", None))

    meta_filter = Metadata.from_string(request.args.get("meta_filter", "{}"))

    score = score_map.get(request.args.get("score", None), pearsons_coefficient)

    meta_freq_dists = get_metadata_distribution(
        lang, word, start_time=start_time, end_time=end_time, meta_filter=meta_filter
    )
    wordless_freq_dists = get_metadata_distribution(
        lang, "", start_time=start_time, end_time=end_time, meta_filter=meta_filter
    )
    item = sorted(
        filter(
            lambda d: not np.isnan(d["score"]),
            (
                dict(score=score(meta_freq_dists[col], wordless_freq_dists[col]), field=col)
                for col in meta_freq_dists
            ),
        ),
        key=lambda entry: entry["score"],
    )
    return json.jsonify(dict(metadata=item, word=meta_freq_dists, wordless=wordless_freq_dists))


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
    match_description.cache_clear()
    get_time_series.cache_clear()
    get_recent_tickets_by_word.cache_clear()
    get_viable_categories_in_metadata_distribution.cache_clear()
    get_metadata_distribution.cache_clear()
    SpikeDAL.reload_cache(lang)
    ticket_almanac[lang].reload_cache()
    global _init_timestamp
    _init_timestamp = datetime_to_str(get_utc_today())
    status = _get_status(lang)
    status["status"] = "ok"
    return json.jsonify(status)


def _get_status(lang):
    return {
        "deployed_timestamp": _DEPLOYED_TIMESTAMP,
        "initialized_timestamp": _init_timestamp,
        "latest_ticket_timestamp": get_most_recent_ticket_timestamp(lang),
    }


def _is_language_supported(lang):
    return lang in [lang_name for lang_name, _ in SUPPORTED_LANGUAGES.__members__.items()]
