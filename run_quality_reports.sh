#!/bin/bash
set -ex

# Docker image is sometimes too big and will cause error on transfer from the remote builder
# This line will force the builds to happen locally instead of on the remote builder
export DOCKER_BUILD_OPT_OUT="true"
# ----- environment variables definitions -----

DOCKER_FILE="Dockerfile.quality_reports"

IMAGE_HASH="$(docker build --build-arg ENVIRONMENT="$ENVIRONMENT" --build-arg SAVE_SNAPSHOTS="$SAVE_SNAPSHOTS" --build-arg JIRA_USERNAME="$JIRA_USERNAME" -q -f "$DOCKER_FILE" . | head -1)"
docker run \
  -e JIRA_API_TOKEN=$JIRA_API_TOKEN \
  -e DRY_RUN=$DRY_RUN \
  -e DRY_RUN_RECIPIENT=$DRY_RUN_RECIPIENT \
  $IMAGE_HASH python jeeves/scripts/quality_reports/quality_report_script.py
