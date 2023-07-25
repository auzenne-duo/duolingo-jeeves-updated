#!/bin/bash
set -ex

# ----- environment variables definitions -----

DOCKER_FILE="Dockerfile.sync_jira"

IMAGE_HASH="$(docker build --build-arg ENVIRONMENT="$ENVIRONMENT" --build-arg REFRESH_HOURS="$REFRESH_HOURS" --build-arg JIRA_USERNAME="$JIRA_USERNAME" -q -f "$DOCKER_FILE" . | head -1)"
docker run -e JIRA_API_TOKEN=$JIRA_API_TOKEN $IMAGE_HASH python jeeves/scripts/index_pipeline_and_spike_detector/sync_jira_tickets.py
