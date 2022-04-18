# duolingo-jeeves

Technology-driven user support.

## Owner

- Yijin Kang, yijin@duolingo.com

## Badges

![Code](https://s3.amazonaws.com/duolingo-data/severin/code-bronze.png "Code")
![Tests](https://s3.amazonaws.com/duolingo-data/severin/test-bronze.png "Tests")
![Documentation](https://s3.amazonaws.com/duolingo-data/severin/docs-bronze.png "Documentation")
![Process](https://s3.amazonaws.com/duolingo-data/severin/proc-gold.png "Process")

Look into the [Microservice Review](docs/microservice-review.md) for details.

## How to deploy

- Use this Jenkins job [`https://jenkins-ci.duolingo.com/job/duolingo-jeeves-deploy-galaxy-dev/`](https://jenkins-ci.duolingo.com/job/duolingo-jeeves-deploy-galaxy-dev/) to deploy to the dev cluster at [`https://duolingo-jeeves-dev.duolingo.com`](https://duolingo-jeeves-dev.duolingo.com)
- Merging a PR will automatically trigger deployment to [`https://jeeves.duolingo.com`](https://jeeves.duolingo.com)

## How to contribute

Make sure to set up Python 3 virtual environment, or pylint would fail when trying to commit.

- Run `virtualenv -p python3 env` (If that doesn't work, try `python3 -m venv env`)
- Run `export PYTHONPATH=$(pwd)`
- Run `source env/bin/activate`
- Run `pip3 install -r requirements.txt`
- Run `pip3 install -r dev-requirements.txt`

TODO localstack for sqs queues on local dev

### Backend

To run the microservice locally:

- [Install Docker](https://docs.docker.com/docker-for-mac/install/) and increase the memory limit to 8GB if you haven't already.
- Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables.
- Run `make web` to start a microservice locally on Docker.
- If you hit an error due to another process listening on port 5000, [turn off AirPlay Receiver under Sharing in System Preferences](https://developer.apple.com/forums/thread/682332?answerId=678289022#678289022)
- Open [`http://localhost:5000/`](http://localhost:5000/).

The following are required when you update requirements.

- Run `pip-compile --output-file requirements.txt requirements.in`
- Run `pip-compile --output-file dev-requirements.txt dev-requirements.in`

The data versioning number in `jeeves/config/config.py` should be updated whenever data should be backfilled. Changing this number to a previously unused value will create new data indices in Elasticsearch and the data update scripts will automatically fill them in. As a convention, we have been incrementing the "major" data version number (i.e. before the decimal point) for adding entirely new data sources and for major structural changes, and incrementing the "minor" data version number (i.e. after the decimal point) for smaller changes to existing structures.

### Frontend

To start a local webpack development server on [`http://localhost:8080/`](http://localhost:8080/)

```
make install
make web-dev
```

This will use the local microservice for the backend.

To proxy API requests to https://jeeves.duolingo.com, run `make web-proxy`.

### Slack Reporting

- Set the `SPIKE_REPORTER_SLACK_API_TOKEN` environment variable, or comment out the code that makes the request to the Slack API.
- Run the steps above to set up the Python virtual environment
- Run `./env/bin/python ./jeeves/scripts/slack.py`

## Import Infrastructure

See yml files in `/config` to get exact s3 bucket/queue names.
Galaxy module (`/galaxy`) | Python script (`/jeeves/scripts`) | Description | Reads from | Outputs to
------------ | ------------- | ------------- | ------------- | -------------
s3-worker.json | update_jeeves_data.py | Calls `ticket_crawler.crawl_tickets()`, which also calls methods in each `jeeves_manager` implementation in order to make API calls to pull individual documents. | Individual sources (AppFigures, Jira, Zendesk) | S3 bucket: `config.s3_document_cache`, SQS queue: `config.sqs_download_verify_pipeline`
sqs-worker-1.json | sqs_verify_worker.py | Calls `process_document()` from the relevant `jeeves_manager` implementation. This method returns `None` if the corresponding `jeeves_document.check_should_index_document()` method returns `False`. | SQS queue: `config.sqs_download_verify_pipeline` | SQS queue: `config.sqs_verify_index_pipeline`
sqs-worker-2.json | sqs_index_worker.py | Calls `check_should_index_document()` from the relevant `jeeves_document` implementation to determine if a document should be indexed. For Zendesk email documents, checks for duplicates before indexing. | SQS queue: `config.sqs_verify_index_pipeline` | Document gets indexed in ElasticSearch

## Links

- [Jeeves Documentation](https://duolingo.atlassian.net/wiki/spaces/DUO/pages/644121212/Jeeves)
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
- [Shakira API](https://github.com/duolingo/duolingo-jeeves/tree/master/jeeves/view#shakira-routes-documentation)
