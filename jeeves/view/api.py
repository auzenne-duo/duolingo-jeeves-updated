"""
APIs.
"""
from flask import Blueprint, json
import logging

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

@blueprint_api.route('/annotate')
def show_annotation_tool():
    pass
