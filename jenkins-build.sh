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

S3_FILE_STORAGE="s3://jeeves-document-cache"
DUPLICATE_DETECTOR_REMOTE_PATH="$S3_FILE_STORAGE/duplicate-detector-model"

# ----- lint -----
if [[ $TERRAFORM_ENV == "prod" ]]; then
  echo "No linting in prod environment."
else

  # --- run eslint ---
  WORKDIR="/code"
  CMD="cd /code && make install eslint"
  docker run --rm --volume "$(pwd):$WORKDIR" node:16.13.1 sh -c "$CMD"
fi

# ----- build -----

mkdir ./duplicate-detector-model
aws s3 sync --quiet "$DUPLICATE_DETECTOR_REMOTE_PATH" ./duplicate-detector-model/
echo "DOCKER_FILE: $DOCKER_FILE"
IMAGE_HASH="$(docker build -q -f "$DOCKER_FILE" . | head -1)"

# ----- test -----
if [[ $TERRAFORM_ENV == "prod" ]]; then
  echo "No unit tests in prod environment."
else

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
  # --- report deployment to rollbar ---
  curl https://api.rollbar.com/api/1/deploy/ \
    -F access_token="d706122c96ae40a79f2542e0e0cab6bb" \
    -F environment="$TERRAFORM_ENV" \
    -F revision="$GIT_COMMIT" \
    -F local_username="jenkins-ci"

  # --- deploy Docker images ---
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_S3_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_WORKER_CRON" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_1" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SQS_WORKER_2" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_SPIKE_WORKER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"
  echo "$IMAGE_HASH" | deploy-galaxy -c -m "$MODULE_EMAIL_SENDER" -v "$BUILD_NUMBER" -p "$TERRAFORM_PATH"

  # --- run Jira Feature creation script ---
  WORKSPACE=${WORKSPACE:-$(pwd)}
  PYENV_HOME="$WORKSPACE/.pyenv/"
  python3 -m venv "$PYENV_HOME"
  . "$PYENV_HOME/bin/activate"
  export PYTHONPATH="$WORKSPACE"
  export SHAKIRA_JIRA_USERNAME_WEB="jira-automation@duolingo.com"
  set +x
  export SHAKIRA_JIRA_API_TOKEN_WEB=$(aws secretsmanager get-secret-value --secret-id 'PRODUCT_QUALITY_JIRA_TOKEN' | jq -r '.SecretString')
  set -x

  pip install -U pip wheel setuptools
  pip install -r dev-requirements.txt

  python jeeves/scripts/create_jira_features.py
else
  echo "No auto-deployment in dev environment."
fi
