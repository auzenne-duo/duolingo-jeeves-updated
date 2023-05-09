#!/bin/bash
set -ex

# ----- environment variables definitions -----

DOCKER_FILE="Dockerfile.refresh"

IMAGE_HASH="$(docker build --build-arg ENVIRONMENT="$ENVIRONMENT" --build-arg REFRESH_DAYS="$REFRESH_DAYS" -q -f "$DOCKER_FILE" . | head -1)"
docker run $IMAGE_HASH python jeeves/scripts/force_refresh.py
