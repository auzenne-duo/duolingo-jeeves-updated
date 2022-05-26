import os
from typing import Type, TypeVar

from duolingo_base.config import Config
from duolingo_base.util import registry as base_registry
from flask import Flask

from jeeves.config.jira_features import JIRA_FEATURES, JIRA_FEATURES_REGISTRY_KEY
from jeeves.manager.jira_feature_manager import (
    SUBSTRINGS_TO_IGNORE_BY_TERM,
    SUBSTRINGS_TO_IGNORE_REGISTRY_KEY,
)

service_registry = base_registry.initialize()

T = TypeVar("T")


def apply_registry_to_app(application: Flask):
    apply_registry()
    application.registry = service_registry


def apply_registry():
    config = Config.load_config()
    config.apply_registry(registry=service_registry)
    service_registry.start()

    service_registry[JIRA_FEATURES_REGISTRY_KEY] = JIRA_FEATURES
    service_registry[SUBSTRINGS_TO_IGNORE_REGISTRY_KEY] = SUBSTRINGS_TO_IGNORE_BY_TERM


def close_registry():
    service_registry.close()


def registry(t_type: Type[T]) -> T:
    """
    Access the registry in a way that lets mypy know what type of object was returned.
    This function should be used in all non-test code instead of accessing the registry directly.
    """
    return service_registry[t_type]


package_directory = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.abspath(os.path.join(package_directory, "..", "data"))
