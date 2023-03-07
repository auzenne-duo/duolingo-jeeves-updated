#!/bin/bash
set -ex

# ----- environment variables definitions -----

MODULE=duolingo-jeeves
MODULE_S3_WORKER=duolingo-jeeves-s3-worker
MODULE_WORKER_CRON=duolingo-jeeves-worker-cron
MODULE_SQS_WORKER_1=duolingo-jeeves-sqs-worker-1
MODULE_SQS_WORKER_2=duolingo-jeeves-sqs-worker-2
MODULE_SPIKE_WORKER=duolingo-jeeves-spike-worker
MODULE_EMAIL_SENDER=duolingo-jeeves-email-sender
MODULE_PRIORITY_ESTIMATOR_UPDATER=duolingo-jeeves-priority-estimator-updater

TERRAFORM_ENV=dev
TERRAFORM_PATH="galaxy/$TERRAFORM_ENV"
DOCKER_FILE="Dockerfile.dev"

S3_FILE_STORAGE="s3://jeeves-document-cache-dev"
DUPLICATE_DETECTOR_REMOTE_PATH="$S3_FILE_STORAGE/duplicate-detector-model"
PRIORITY_ESTIMATOR_REMOTE_PATH="$S3_FILE_STORAGE/priority_estimator_model"
JEEVES_DOCUMENT_CLASSIFIER_REMOTE_PATH="$S3_FILE_STORAGE/jeeves_document_classifier"

# ----- build -----

mkdir ./duplicate-detector-model
aws s3 sync --quiet "$DUPLICATE_DETECTOR_REMOTE_PATH" ./duplicate-detector-model/
aws s3 sync --quiet "$PRIORITY_ESTIMATOR_REMOTE_PATH" ./priority_estimator_model/
aws s3 sync --quiet "$JEEVES_DOCUMENT_CLASSIFIER_REMOTE_PATH" ./document_classifier/
echo "DOCKER_FILE: $DOCKER_FILE"
IMAGE_HASH="$(docker build -q -f "$DOCKER_FILE" . | head -1)"

# ----- deploy -----

echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_S3_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_WORKER_CRON" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_1" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_2" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SPIKE_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_EMAIL_SENDER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_PRIORITY_ESTIMATOR_UPDATER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
