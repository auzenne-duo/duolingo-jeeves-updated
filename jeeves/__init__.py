import os
from typing import Type, TypeVar

from duolingo_base.config import Config
from duolingo_base.util import registry as base_registry
from flask import Flask

from jeeves.config.jira_features import (
    JIRA_FEATURES,
    JIRA_FEATURES_DESCRIPTIONS,
    JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY,
    JIRA_FEATURES_REGISTRY_KEY,
    SESSION_END_SCREEN_TO_FEATURE,
    SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY,
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
    service_registry[JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY] = JIRA_FEATURES_DESCRIPTIONS
    service_registry[SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY] = SESSION_END_SCREEN_TO_FEATURE


def close_registry():
    service_registry.close()


def registry(t_type: Type[T]) -> T:
    """
    Access the registry in a way that lets mypy know what type of object was returned.
    This function should be used in all non-test code instead of accessing the registry directly.
    """
    return service_registry[t_type]


def register(key, value):
    service_registry[key] = value


package_directory = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.abspath(os.path.join(package_directory, "..", "data"))
