"""
APIs.
"""
from flask import Blueprint, abort, json, make_response, render_template, request
import logging
import random

from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.lib.time_series_generator import get_time_series, get_recent_tickets_by_word, get_paginated_tickets
from jeeves.model.categories import CATEGORIES

# This is being referenced by the application.py
blueprint_api = Blueprint('api', __name__)

_LOG = logging.getLogger('application')

# Append this to resource URLs (i.e. JS and CSS) to avoid caching.
_RANDOM = random.randint(0, 1000000)

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


@blueprint_api.route('/api/1/tickets', methods=['GET', 'PATCH'])
def manage_tickets():
    # TODO: implement `start_time` restriction instead of `page`
    # start_time = request.args.get('start_time')
    page = int(request.args.get('page', '0'))
    word = request.args.get('word')
    start_time = request.args.get('start_time', None)
    end_time = request.args.get('end_time', None)

    def get_tickets_by_word():
        limit = int(request.args.get('limit', '10'))
        tickets = get_recent_tickets_by_word(word, start_time=start_time, end_time=end_time)
        tickets = sorted(tickets, key=lambda tk: tk.date_time, reverse=True)
        tickets = tickets[page * limit : (page + 1) * limit]
        values = [{'ticket_id': ticket.ticket_id,
                   'date_time': ticket.date_time,
                   'subject': ticket.subject,
                   'description': ticket.description,
                   } for ticket in tickets
                  ]
        return {'data': values,
                'next_url': '/api/1/tickets?word=%s&limit=%s&page=%s' % (word, limit, page + 1)}

    def get_tickets_for_annotation():
        limit = int(request.args.get('limit', '10'))
        tickets = get_paginated_tickets(page, limit)
        category_list = sorted(cat.name for cat in CATEGORIES)
        # Adding more categories for demo purpose
        category_list += ['feature_request', 'language_request', 'requesting_reply',
                          'challenge_feedback', 'schools', 'iap_refunds',
                          'streak_issue', 'forum_abuse']
        values = [{'ticket_id': ticket.ticket_id,
                   'date_time': ticket.date_time,
                   'subject': ticket.subject,
                   'description': ticket.description,
                   'category_labels': {category: bool(ticket.category_labels and
                                                      category in ticket.category_labels)
                                       for category in category_list},
                   } for ticket in tickets
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
    if not word:
        abort(make_response('Please provide `word` parameter', 500))
    return json.jsonify(get_time_series(word))
