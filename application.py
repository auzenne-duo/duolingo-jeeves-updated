"""
Main entry point for running the service, through command line or mod_wsgi.
"""

from flask import Flask
import logging
import os
# import rollbar
# import rollbar.contrib.flask

from duolingo.base.config import Config
from duolingo.base.util import registry
from duolingo.base.view.auth import auth_after_request

from jeeves.view.api import blueprint_api


LOG = logging.getLogger('application')


config = Config.load_config()

application = Flask(__name__,
                    static_folder='jeeves/static',
                    template_folder='jeeves/templates')
application.after_request(auth_after_request)

# Register blueprints
application.register_blueprint(blueprint_api)

application.registry = registry.initialize()

config.apply_all(registry=application.registry,
                 flask_app=application)


@application.route('/error', methods=['GET', 'POST', 'PATCH', 'PUT'])
def error():
    raise Exception('Error handling test')


def init():
    """
    Initialize the service on startup.

    This sets up logging, applies the desired configuration and initializes
    required data structures.
    """
    is_production_env = config.get_nested(['environment']) == 'prod'

    # Initialize logging subsystem
    log_level = logging.INFO if is_production_env else logging.DEBUG
    logging.basicConfig()
    LOG.setLevel(log_level)
    logging.getLogger('jeeves').setLevel(log_level)
    LOG.info('initializing')

    # Initialize Rollbar
#     rollbar_config_dict = config.get_nested(['rollbar'])
#     rollbar.init(rollbar_config_dict['access_token'],
#                  environment=rollbar_config_dict['environment'],
#                  root=os.path.dirname(os.path.realpath(__file__)),
#                  allow_logging_basic_config=False)
#     got_request_exception.connect(rollbar.contrib.flask.report_exception, application)

    # Start registry
    application.registry.start()

    # Configure development / production environment
    if is_production_env:
        LOG.info('production')
    else:
        LOG.info('development')


def destroy():
    """
    Shutdown the service gracefully, cleaning up resources created in init().
    """
    LOG.info('stopping')

    application.registry.close()


if __name__ == '__main__':
    """
    Called as main python script, start the server.
    """
    started = False
    # when use_reloader (application.debug) is true, this function
    # will run twice, this check makes sure init is only called once
    if not application.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        init()
        started = True

    # Start the flask server, this runs until ctrl-c is pressed
    application.run(config.get_nested(['flask', 'host'], default='127.0.0.1'),
                    config.get_nested(['flask', 'port'], default=5000))

    if started:
        destroy()

elif __name__ == 'uwsgi_file_application':
    """
    If called as a uWSGI application, just initialize the server.
    """
    init()
