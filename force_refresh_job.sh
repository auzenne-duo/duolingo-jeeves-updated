#!/bin/bash
set -ex

# ----- environment variables definitions -----

DOCKER_FILE="Dockerfile.refresh"

IMAGE_HASH="$(docker build --build-arg ENVIRONMENT="$ENVIRONMENT" --build-arg REFRESH_START_DATE="$REFRESH_START_DATE" --build-arg REFRESH_END_DATE="$REFRESH_END_DATE" -q -f "$DOCKER_FILE" . | head -1)"
docker run $IMAGE_HASH python jeeves/scripts/index_pipeline_and_spike_detector/force_refresh.py
