"""
APIs.
"""
from flask import Blueprint, abort, json, make_response, render_template, request
import logging

from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.lib.time_series_generator import get_time_series
from jeeves.model.categories import CATEGORIES

# This is being referenced by the application.py
blueprint_api = Blueprint('api', __name__)

_LOG = logging.getLogger('application')


@blueprint_api.route('/api/1/hello')
def say_hello():
    return json.jsonify({'msg': 'hello'})

@blueprint_api.route('/about')
def show_about():
    return ('<html><body><h1>Hello, I am Jeeves.</h1>'
            'I am a technology-driven user support system who helps millions of Duolingo users.</body></html>')

@blueprint_api.route('/annotation')
def show_annotation_tool():
    return render_template('annotation.html', categories=CATEGORIES)

@blueprint_api.route('/ticket')
def show_ticket_list():
    return render_template('ticket.html')

@blueprint_api.route('/api/1/tickets')
def get_tickets():
    # TODO: implement `start_time` restriction
    start_time = request.args.get('start_time')
    limit = int(request.args.get('limit', '30'))
    tickets = SupportTicketDAL.get_sample_support_tickets()
    tickets = sorted(tickets, key=lambda i: i.date_time, reverse=True)
    tickets = tickets[:limit]
    category_list = sorted(CATEGORIES)
    data = [{
        'ticket_id': ticket.ticket_id,
        'date_time': ticket.date_time,
        'subject': ticket.subject,
        'description': ticket.description,
        'category_labels': {category: ticket.category_labels and category in ticket.category_labels
                            for category in category_list},
        }
        for ticket in tickets
    ]
    return json.jsonify(data)


@blueprint_api.route('/api/1/time_series')
def get_time_series_data():
    # TODO: support more parameters such as category
    word = request.args.get('word')
    if not word:
        abort(make_response('Please provide `word` parameter', 500))
    return json.jsonify(get_time_series(word))
