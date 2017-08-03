#!/bin/bash
set -ex


# ----- environment variables definitions -----

MODULE=duolingo-jeeves
MODULE_S3_WORKER=duolingo-jeeves-s3-worker

DEV_TERRAFORM_ENV=dev

if [[ -n "${1+set}" ]] ; then
    TERRAFORM_ENV="$1"
else
    TERRAFORM_ENV="$DEV_TERRAFORM_ENV"
fi

if [[ "$TERRAFORM_ENV" == "prod" ]]; then
    DOCKER_FILE="Dockerfile"
else
    DOCKER_FILE="Dockerfile.dev"
fi


# ----- build -----

echo "DOCKER_FILE: $DOCKER_FILE"
IMAGE_HASH="$(build-galaxy "$DOCKER_FILE")"


# TODO: add unit tests
# # ----- test -----
# if [[ "$TERRAFORM_ENV" == "prod" ]]; then
#     echo "No unit tests in prod environment."
# else
#     docker run "$IMAGE_HASH" pytest
# fi


# ----- deploy -----

TERRAFORM_PATH="galaxy/$TERRAFORM_ENV"
echo "TERRAFORM_ENV: $TERRAFORM_PATH"
if [[ "$TERRAFORM_ENV" == "prod" ]]; then
    echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_S3_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
    echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
else
    echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
fi
