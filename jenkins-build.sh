#!/bin/bash -ex

PACKAGE=duolingo-jeeves

# default WORKSPACE to current directory so we can run in dev environment too
WORKSPACE="${WORKSPACE:-$(pwd)}"

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
TERRAFORM_PATH="galaxy/$TERRAFORM_ENV"
echo "TERRAFORM_ENV: $TERRAFORM_PATH"
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
echo "$IMAGE_HASH" | deploy-galaxy -c -m "$PACKAGE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
