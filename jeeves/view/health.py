"""
Health check view to ensure service is alive.
"""
from flask import Blueprint

blueprint_health = Blueprint("health", __name__)


@blueprint_health.route("/health")
def health():
    """Check the health of the service (200 OK if healthy)."""
    return "OK"
