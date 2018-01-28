"""
APIs.
"""
from flask import Blueprint, abort, json, make_response, render_template, request
import logging
import numpy as np
import random

from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.dal.spikes import SpikeDAL
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.lib.time_series_generator import (
    get_metadata_distribution,
    get_most_recent_ticket_timestamp,
    get_paginated_tickets,
    get_recent_tickets_by_word,
    get_time_series,
    get_viable_categories_in_metadata_distribution,
    match_description
)
from jeeves.model.categories import CATEGORIES
from jeeves.model.metadata import Metadata
from jeeves.model.time_series import TS
from jeeves.util.date_util import datetime_to_str, get_eastern_today, \
    time_series_str_to_datetime as str_to_datetime
from jeeves.util.score import pearsons_coefficient, cosine_similarity

# This is being referenced by the application.py
blueprint_api = Blueprint('api', __name__)

_LOG = logging.getLogger('application')

# Append this to resource URLs (i.e. JS and CSS) to avoid caching.
_RANDOM = random.randint(0, 1000000)

_DEPLOYED_TIMESTAMP = datetime_to_str(get_eastern_today())

_init_timestamp = datetime_to_str(get_eastern_today())


@blueprint_api.route('/api/1/hello')
def say_hello():
    return json.jsonify({'msg': 'hello'})


@blueprint_api.route('/')
def show_index():
    return render_template('index.html', random=_RANDOM)


@blueprint_api.route('/annotation')
def show_train_jeeves():
    return render_template('annotation.html', random=_RANDOM)


@blueprint_api.route('/analysis')
def show_analysis():
    return render_template('analysis.html', random=_RANDOM)


@blueprint_api.route('/spike')
def show_spike():
    return render_template('spike.html', random=_RANDOM)


@blueprint_api.route('/api/1/tickets', methods=['GET', 'PATCH'])
def manage_tickets():
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')
    page = int(request.args.get('page', '0'))
    word = request.args.get('word')
    start_time = str_to_datetime(request.args.get('start_time', None))
    end_time = str_to_datetime(request.args.get('end_time', None))
    meta_filter = Metadata.from_string(request.args.get('meta_filter', '{}'))

    def get_tickets_by_word():
        limit = int(request.args.get('limit', '10'))
        tickets = get_recent_tickets_by_word(word, start_time=start_time,
                                             end_time=end_time, meta_filter=meta_filter)
        tickets = get_paginated_tickets(page, limit, dataframe=tickets)
        values = [
            ticket.subserialize(
                'ticket_id',
                'date_time',
                'subject',
                'description',
                'priority',
                'via',
                'tags',
                'requester_id',
                'metadata'
            )
            for ticket in tickets
        ]
        return {'data': values,
                'next_url': '/api/1/tickets?word=%s&limit=%s&page=%s' % (word, limit, page + 1)}

    def get_tickets_for_annotation():
        def replace(d, field, fn):
            d[field] = fn(d[field])
            return d
        limit = int(request.args.get('limit', '10'))
        tickets = get_paginated_tickets(page, limit)
        category_list = sorted(cat.name for cat in CATEGORIES)
        # Adding more categories for demo purpose
        category_list += ['feature_request', 'language_request', 'requesting_reply',
                          'challenge_feedback', 'schools', 'iap_refunds',
                          'streak_issue', 'forum_abuse']
        values = [
            replace(
                d=ticket.subserialize(
                    'ticket_id',
                    'date_time',
                    'subject',
                    'description',
                    'category_labels'
                ),
                field='category_labels',
                fn=lambda cl: {
                    cat: cat in cl
                    for cat in category_list
                } if cl else {
                    cat: False
                    for cat in category_list
                }
            )
            for ticket in tickets
        ]
        return {'data': values,
                'next_url': '/api/1/tickets?limit=%s&page=%s' % (limit, page + 1)}

    if request.method == 'GET':
        if word:
            response_data = get_tickets_by_word()
        else:
            response_data = get_tickets_for_annotation()
    elif request.method == 'PATCH':
        response_data = CategoryAnnotationDAL.bulk_save_annotations(request.get_json())
    return json.jsonify(response_data)


@blueprint_api.route('/api/1/time_series')
def get_time_series_data():
    # TODO: support more parameters such as category
    word = request.args.get('word')
    meta_filter = Metadata.from_string(request.args.get('meta_filter', '{}'))
    if not word:
        abort(make_response('Please provide `word` parameter', 500))
    return json.jsonify(get_time_series(word, meta_filter=meta_filter))


@blueprint_api.route('/api/1/spikes')
def get_spike_data():
    return json.jsonify(SpikeDAL.get_spikes())


score_map = dict(pearsons=pearsons_coefficient, cosine=cosine_similarity)

@blueprint_api.route('/api/1/metadata_analyze')
def get_ticket_metadata():
    word = request.args.get('word')
    start_time = str_to_datetime(request.args.get('start_time', None))
    end_time = str_to_datetime(request.args.get('end_time', None))

    meta_filter = Metadata.from_string(request.args.get('meta_filter', '{}'))

    score = score_map.get(request.args.get('score', None), pearsons_coefficient)

    meta_freq_dists = get_metadata_distribution(word, start_time=start_time,
                                                end_time=end_time, meta_filter=meta_filter)
    wordless_freq_dists = get_metadata_distribution('', start_time=start_time,
                                                    end_time=end_time, meta_filter=meta_filter)
    item = sorted(filter(lambda d: not np.isnan(d['score']),
                         (dict(score=score(meta_freq_dists[col], wordless_freq_dists[col]), field=col)
                         for col in meta_freq_dists)), key=lambda entry: entry['score'])
    return json.jsonify(dict(metadata=item, word=meta_freq_dists, wordless=wordless_freq_dists))


@blueprint_api.route('/api/1/info')
def show_info():
    return json.jsonify({'deployed_timestamp': _DEPLOYED_TIMESTAMP,
                         'initialized_timestamp': _init_timestamp,
                         'lastest_ticket_timestamp': get_most_recent_ticket_timestamp()})


@blueprint_api.route('/api/1/init')
def do_init():
    """
    Clear cache (and warm up).
    """
    match_description.cache_clear()
    get_time_series.cache_clear()
    get_recent_tickets_by_word.cache_clear()
    get_viable_categories_in_metadata_distribution.cache_clear()
    get_metadata_distribution.cache_clear()
    SpikeDAL.reload_cache()
    TS.reload_cache()
    SupportTicketDAL.lazy_init()
    global _init_timestamp
    _init_timestamp = datetime_to_str(get_eastern_today())
    return json.jsonify({'status': 'ok', 'timestamp': _init_timestamp})
