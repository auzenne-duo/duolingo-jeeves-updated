#!/usr/bin/env bash

set -eu -o pipefail

export DUOLINGO_CONFIG=local.yml

CONFIG_DIR=config
DUOLINGO_CONFIG_BASE=base.yml
CONFIG_FILE=${CONFIG_DIR}/${DUOLINGO_CONFIG}
CONFIG_FILE_BASE=${CONFIG_DIR}/${DUOLINGO_CONFIG_BASE}

get_config_value() {
  result=$(yq -er "$1" ${CONFIG_FILE} 2> /dev/null) || result=$(yq -er "$1" ${CONFIG_FILE_BASE} 2> /dev/null)
}

# Check for JIRA_USERNAME and JIRA_API_TOKEN environment variables
if [ -z "${JIRA_USERNAME:-}" ] || [ -z "${JIRA_API_TOKEN:-}" ]; then
  echo "Warning: JIRA_USERNAME and/or JIRA_API_TOKEN are empty. These are recommended in order to pull JIRA tickets into your local Elasticsearch instance."
  echo "Create an API key and export these variables inside your '~/.zshrc' file (or in your current shell): https://id.atlassian.com/manage-profile/security/api-tokens"
  echo "For more information, please read: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/"
fi

# Check for DUOLINGO_JWT
if [ -z "${DUOLINGO_JWT:-}" ]; then
  echo "Warning: DUOLINGO_JWT is empty. This is needed in order to create embeddings for your local Elasticsearch documents."
  echo "Run 'duo login' or follow these instructions: https://duolingo.atlassian.net/wiki/spaces/DUO/pages/674890786"
fi

# Check for AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  echo "Warning: AWS_ACCESS_KEY_ID and/or AWS_SECRET_ACCESS_KEY are empty. These are needed to download the necessary files for running the Spike Detector."
  echo "Run 'duo login-aws' and export those returned values as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
fi

# Check for jq
if ! command -v jq > /dev/null 2>&1; then
  echo "Error: 'jq' not found."
  echo "To install 'jq', please run:"
  echo "On macOS (via Homebrew): 'brew install jq'"
  echo "On Codespaces (Ubuntu): 'sudo apt-get update && sudo apt-get -y --no-install-recommends install jq'"
  exit 1
fi

# Check for yq
if ! command -v yq > /dev/null 2>&1; then
  echo "Error: 'yq' not found."
  echo "To install 'yq', please run: 'pip install yq'"
  exit 1
fi

get_config_value ".elasticsearch.data_version_identifier"
if [ -z "${result}" ]; then
  echo "Error: Could not get the value of 'data_version_identifier' from either ${CONFIG_FILE} or ${CONFIG_FILE_BASE}."
  exit 1
fi
export DATA_VERSION_IDENTIFIER=${result}
echo "Using DATA_VERSION_IDENTIFIER v${DATA_VERSION_IDENTIFIER}"

export USER_AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
export USER_AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

export AWS_ACCESS_KEY_ID=foo
export AWS_DEFAULT_REGION=us-east-1
export AWS_SECRET_ACCESS_KEY=bar
export COMPOSE_FILE=docker-compose-local.yml

make web
