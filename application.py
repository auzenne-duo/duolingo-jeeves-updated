"""
Main entry point for running the service, through command line or mod_wsgi.
"""

import logging
import os

from duolingo_base.config import Config
from duolingo_base.view.auth import auth_after_request, requires_auth
from flask import Flask, request
from flask_cors import CORS

from jeeves import apply_registry_to_app, close_registry, registry as app_registry
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES

LOG = logging.getLogger("application")

config = Config.load_config()

application = Flask(__name__)

# Allow cross-subdomain API calls
cors_origins = [r".*\.duolingo\.(com|cn)$", r"^https?:\/\/(localhost|10\.1\.\d+\.\d+):\d+$"]
CORS(application, supports_credentials=True, origins=cors_origins, max_age=1728000)


def auth_before_request():
    if config.get_nested(["environment"]) == "local":
        return None

    # Don't require authentication on CORS preflight.
    if request.method == "OPTIONS":
        return None
    # We want health checks to not need authentication, and I don't think
    # anyone has set up auth credentials for the update script yet, so in the
    # meantime we just allow all the routes it uses to be serviced without auth
    elif request.path in {"/health"} | {f"/api/1/{lang.name}/init" for lang in SUPPORTED_LANGUAGES}:
        return None
    elif request.path == "/api/1/shake_to_report_tokens":
        return requires_auth(permission="unlock-skill-tree")(lambda: None)()
    elif request.path.startswith("/api/1/shakira/"):
        return requires_auth(permission="shake-to-report")(lambda: None)()
    else:
        return requires_auth(permission="access-jeeves")(lambda: None)()


application.before_request(auth_before_request)
application.after_request(auth_after_request)

apply_registry_to_app(application)

# Register blueprints

config.apply_all(registry=application.registry, flask_app=application)


@application.route("/error", methods=["GET", "POST", "PATCH", "PUT"])
def error():
    raise Exception("Error handling test")


def init():
    """
    Initialize the service on startup.

    This sets up logging, applies the desired configuration and initializes
    required data structures.
    """
    is_production_env = config.get_nested(["environment"]) == "prod"

    # Initialize logging subsystem
    log_level = logging.INFO if is_production_env else logging.DEBUG
    logging.basicConfig()
    LOG.setLevel(log_level)
    logging.getLogger("jeeves").setLevel(log_level)
    LOG.info("initializing")

    if is_production_env:
        LOG.info("production")
    else:
        LOG.info("development")

    app_registry(OpenSearchDAL).initialize_index()
    app_registry(SpikeIndexDAL).initialize_index()


def destroy():
    """
    Shutdown the service gracefully, cleaning up resources created in init().
    """
    LOG.info("stopping")

    close_registry()


if __name__ == "__main__":
    """
    Called as main python script, start the server.
    """
    started = False
    # when use_reloader (application.debug) is true, this function
    # will run twice, this check makes sure init is only called once
    if not application.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        init()
        started = True

    # Start the flask server, this runs until ctrl-c is pressed
    application.run(
        config.get_nested(["flask", "host"], default="127.0.0.1"),
        config.get_nested(["flask", "port"], default=8080),
    )

    if started:
        destroy()

elif __name__ == "uwsgi_file_application":
    """
    If called as a uWSGI application, just initialize the server.
    """
    init()
