#!/usr/bin/env bash
set -eu -o pipefail

echo
echo "Starting localstack init.sh script..."

apt-get update \
  && apt-get -y --no-install-recommends install jq \
  && rm -rf /var/lib/apt/lists/*

pip install yq

CONFIG_DIR=/home/localstack/config
DUOLINGO_CONFIG_BASE=base.yml
DUOLINGO_CONFIG_PROD=prod.yml
CONFIG_FILE=${CONFIG_DIR}/${DUOLINGO_CONFIG}
CONFIG_FILE_BASE=${CONFIG_DIR}/${DUOLINGO_CONFIG_BASE}
CONFIG_FILE_PROD=${CONFIG_DIR}/${DUOLINGO_CONFIG_PROD}

get_config_values() {
  result_prod=$(yq -er "$1" ${CONFIG_FILE_PROD} 2> /dev/null) || result=$(yq -er "$1" ${CONFIG_FILE_BASE} 2> /dev/null)
  result_local=$(yq -er "$1" ${CONFIG_FILE} 2> /dev/null) || result=$(yq -er "$1" ${CONFIG_FILE_BASE} 2> /dev/null)
}

get_config_values ".s3_document_cache.bucket_name"
prod_bucket=${result_prod}
local_bucket=${result_local}

echo
echo "Downloading static files from production S3..."

fixed_date="2023-05-01"
today=$(date +%Y-%m-%d)

LOCAL_AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID
LOCAL_AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY

# Temporarily set the AWS credentials in this env to the user's credentials
export AWS_ACCESS_KEY_ID=${USER_AWS_ACCESS_KEY_ID}
export AWS_SECRET_ACCESS_KEY=${USER_AWS_SECRET_ACCESS_KEY}

tmp_bucket_dir="tmp_bucket_dir"
mkdir -p ${tmp_bucket_dir}
sources="AppFigures JIRA Reddit Zendesk"
for source in ${sources}; do
  n=10
  echo "Downloading ${n} sample documents from s3://${prod_bucket}/${source} from ${fixed_date}..."

  # Copy the first 10 files from fixed_date to our local bucket and make it look like today's date
  mkdir -p ${tmp_bucket_dir}/${source}/${today}
  s3_folder="s3://${prod_bucket}/${source}/${fixed_date}"
  set +o pipefail # Turn off pipefail for this line because we get 141 errors due to SIGPIPE otherwise
  first_ten=$(aws s3 ls ${s3_folder}/ | sort -n | head -n ${n} | awk '{print $4}')
  set -o pipefail
  while read -r file; do
    aws s3 cp "${s3_folder}/${file}" ${tmp_bucket_dir}/${source}/${today}/
  done <<< "${first_ten}"
done

# Uncomment this to download the duplicate detector and priority detector models because they take a long time
# other_items="duplicate-detector-model spike_exclude_words spike_lemma_stats"
other_items="spike_exclude_words spike_lemma_stats"
for item in ${other_items}; do
  echo "Downloading ${item} from s3://${prod_bucket} ..."
  aws s3 cp s3://${prod_bucket}/${item} ${tmp_bucket_dir}/${item}
done

# Restore AWS credentials to the dummy ones
export AWS_ACCESS_KEY_ID=${LOCAL_AWS_ACCESS_KEY_ID}
export AWS_SECRET_ACCESS_KEY=${LOCAL_AWS_SECRET_ACCESS_KEY}

echo
echo "Done downloading static files from production S3."

echo
echo "Initializing S3 buckets..."

REGION=${AWS_DEFAULT_REGION}
URL="http://localstack:4566"

aws --endpoint-url=${URL} --region ${REGION} s3 mb s3://${local_bucket}
for source in ${sources}; do
  echo "Uploading ${source} to s3://${local_bucket}/${source} ..."
  aws --endpoint-url=${URL} --region ${REGION} s3 sync ./${tmp_bucket_dir}/${source} s3://${local_bucket}/${source}
done

for item in ${other_items}; do
  echo "Uploading ${item} to s3://${local_bucket}/${item} ..."
  aws --endpoint-url=${URL} --region ${REGION} s3 cp ./${tmp_bucket_dir}/${item} s3://${local_bucket}/${item}
done

echo "Done initializing S3 buckets."
echo
echo "Initializing SQS queues..."

aws --endpoint-url=${URL} --region ${REGION} sqs create-queue --queue-name jeeves-pipeline-break-download-verify-local
aws --endpoint-url=${URL} --region ${REGION} sqs create-queue --queue-name jeeves-pipeline-break-verify-index-local

echo "Done initializing SQS queues."
echo "Finished localstack init.sh script"
