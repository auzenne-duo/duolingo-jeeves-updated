#!/bin/bash
set -ex

# ----- environment variables definitions -----

MODULE=duolingo-jeeves
MODULE_S3_WORKER=duolingo-jeeves-s3-worker
MODULE_WORKER_CRON=duolingo-jeeves-worker-cron
MODULE_SQS_WORKER_1=duolingo-jeeves-sqs-worker-1
MODULE_SQS_WORKER_2=duolingo-jeeves-sqs-worker-2
MODULE_SPIKE_WORKER=duolingo-jeeves-spike-worker

TERRAFORM_ENV=dev
TERRAFORM_PATH="galaxy/$TERRAFORM_ENV"
DOCKER_FILE="Dockerfile.dev"

# ----- build -----

echo "DOCKER_FILE: $DOCKER_FILE"
IMAGE_HASH="$(docker build -q -f "$DOCKER_FILE" . | head -1)"

# ----- deploy -----

echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_S3_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_WORKER_CRON" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_1" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_2" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SPIKE_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
