#!/bin/bash
set -ex

# ----- environment variables definitions -----

DOCKER_FILE="Dockerfile.quality_reports"

IMAGE_HASH="$(docker build --build-arg ENVIRONMENT="$ENVIRONMENT" --build-arg SAVE_SNAPSHOTS="$SAVE_SNAPSHOTS" --build-arg JIRA_USERNAME="$JIRA_USERNAME" -q -f "$DOCKER_FILE" . | head -1)"
docker run -e JIRA_API_TOKEN=$JIRA_API_TOKEN $IMAGE_HASH python jeeves/scripts/quality_reports/quality_report_script.py
