[![Overall](https://img.shields.io/endpoint?style=flat&url=https%3A%2F%2Fapp.opslevel.com%2Fapi%2Fservice_level%2F8gLqSEXTmMmzxHanbqmTVPwQFDWOujrYjU1uJdWEElE)](https://app.opslevel.com/services/duolingo-jeeves/maturity-report)

# duolingo-jeeves

Technology-driven user support.

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

If you run into `ImportError: cannot import name 'BAR_TYPES' from 'pip._internal.cli.progress_bars'`, run the following to install a compatible version of pip: `pip install pip==22.0.4`

The data versioning number in `jeeves/config/config.py` should be updated whenever data should be backfilled. Changing this number to a previously unused value will create new data indices in Elasticsearch and the data update scripts will automatically fill them in. As a convention, we have been incrementing the "major" data version number (i.e. before the decimal point) for adding entirely new data sources and for major structural changes, and incrementing the "minor" data version number (i.e. after the decimal point) for smaller changes to existing structures.

### Frontend

To start a local webpack development server on [`http://localhost:8080/`](http://localhost:8080/)

```
make install
make web-dev
```

This will use the local microservice for the backend.

To proxy API requests to https://jeeves.duolingo.com, run `make web-proxy`.

### Reporting bugs to Slack

Note that Slack Reporting feature in Jeeves (`slack_channel.py`) is used for reports like visual polish or TTS which
usually do not create Jira issues. In particular, this was code used to support an older version of shake-to-report.
It still works, but we normally recommend using [Jira Automation](https://duolingo.atlassian.net/wiki/spaces/DUO/pages/2585821214/Create+Jira+Automation+to+post+issues+with+Feature+to+Slack+Channel) instead.
That's what posts to channels like #bugs or #proj-friends-quest.
Jira Automation is more reliable since it can also alert for issues whose feature field has been changed, whereas this only alerts for bugs at the time of creation.

### Reporting spikes to Slack

Set up instructions:

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

## Force Refresh

To force refresh all tickets in jeeves, build this job: [https://jenkins-ci.duolingo.com/job/duolingo-jeeves-refresh-tickets](https://jenkins-ci.duolingo.com/job/duolingo-jeeves-refresh-tickets).

To force refresh all spikes, set the `force_spike_refresh_flag` to 1 in aws bucket `jeeves-document-cache`.

# Quality Reports

To run the quality report script locally, pango must be installed:

```
sudo apt-get update
sudo apt-get install libpangocairo-1.0-0
sudo apt-get install libpangoft2-1.0-0
```

You might have to run `make install` from the Frontend section to get css fonts to work. You might need to run `npm init` and `npm install` in the web folder.

## Links

- [Jeeves Documentation](https://duolingo.atlassian.net/wiki/spaces/DUO/pages/644121212/Jeeves)
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
- [Shakira API](https://github.com/duolingo/duolingo-jeeves/tree/master/jeeves/view#shakira-routes-documentation)
