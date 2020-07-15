#!/bin/bash
set -ex

# ----- environment variables definitions -----

MODULE=duolingo-jeeves
MODULE_S3_WORKER=duolingo-jeeves-s3-worker
MODULE_WORKER_CRON=duolingo-jeeves-worker-cron

DEV_TERRAFORM_ENV=dev

if [[ -n ${1+set} ]]; then
  TERRAFORM_ENV="$1"
else
  TERRAFORM_ENV="$DEV_TERRAFORM_ENV"
fi

if [[ $TERRAFORM_ENV == "prod" ]]; then
  DOCKER_FILE="Dockerfile"
else
  DOCKER_FILE="Dockerfile.dev"
fi

# ----- build -----

echo "DOCKER_FILE: $DOCKER_FILE"
IMAGE_HASH="$(docker build -q -f "$DOCKER_FILE" .)"

# ----- test -----
if [[ $TERRAFORM_ENV == "prod" ]]; then
  echo "No unit tests in prod environment."
else

  # --- run git hooks on CI ---

  # Running this outside of Docker because of an issue with Alpine + Python 3
  # https://github.com/python/cpython/pull/4783
  WORKSPACE=${WORKSPACE:-$(pwd)}
  PYENV_HOME="$WORKSPACE/.pyenv/"
  python3 -m venv "$PYENV_HOME"
  . "$PYENV_HOME/bin/activate"
  export PYTHONPATH="$WORKSPACE"

  pip install -U pip wheel setuptools
  pip install -r dev-requirements.txt

  # --- run tests ---
  WORKDIR="/code"
  CMD="pytest --junitxml=results.xml --cov-report=term --cov-report=xml:cobertura.xml --cov-report=html --cov=jeeves"
  docker run --rm --volume "$(pwd):$WORKDIR" "$IMAGE_HASH" sh -c "$CMD"
  sed -i"" "s#<source>/code/jeeves</source>#<source>$WORKSPACE/jeeves</source>#" cobertura.xml
fi

# ----- deploy -----

TERRAFORM_PATH="galaxy/$TERRAFORM_ENV"
echo "TERRAFORM_ENV: $TERRAFORM_PATH"
if [[ $TERRAFORM_ENV == "prod" ]]; then
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_S3_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_WORKER_CRON" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
else
  echo "No auto-deployment in dev environment."
fi
