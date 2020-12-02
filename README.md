# duolingo-jeeves

Technology-driven user support.

## Owner

- Peter Chapman, peter@duolingo.com

## Badges

![Code](https://s3.amazonaws.com/duolingo-data/severin/code-bronze.png "Code")
![Tests](https://s3.amazonaws.com/duolingo-data/severin/test-bronze.png "Tests")
![Documentation](https://s3.amazonaws.com/duolingo-data/severin/docs-bronze.png "Documentation")
![Process](https://s3.amazonaws.com/duolingo-data/severin/proc-gold.png "Process")

Look into the [Microservice Review](docs/microservice-review.md) for details.

## Set up

- Run `make web` to start a microservice locally on [Install Docker](https://docs.docker.com/docker-for-mac/install/).
- Open [`http://localhost:5000/`](http://localhost:5000/)

## How to deploy

- Use this Jenkins job [`https://jenkins-ci.duolingo.com/job/duolingo-jeeves-deploy-galaxy-dev/`](https://jenkins-ci.duolingo.com/job/duolingo-jeeves-deploy-galaxy-dev/) to deploy to the dev cluster at [`https://duolingo-jeeves-dev.duolingo.com`](https://duolingo-jeeves-dev.duolingo.com)
- Merging a PR will automatically trigger deployment to [`https://duolingo-jeeves-prod.duolingo.com`](https://duolingo-jeeves-prod.duolingo.com)

## How to contribute

### Backend

Make sure to set up Python3 virtual environment, or pylint would fail when trying to commit.

- Run `virtualenv -p python3 env`
- Run `export PYTHONPATH=$(pwd)`
- Run `source env/bin/activate`
- Run `pip3 install -r requirements.txt`
- Run `pip3 install -r dev-requirements.txt`
- Run `npm install`

The following are required when you updated requirements.

- Run `pip-compile --output-file requirements.txt requirements.in`
- Run `pip-compile --output-file dev-requirements.txt dev-requirements.in`

The data versioning number in `jeeves/config/config.py` should be updated whenever data should be backfilled. Changing this number to a previously unused value will create new data indices in Elasticsearch and the data update scripts will automatically fill them in. As a convention, we have been incrementing the "major" data version number (i.e. before the decimal point) for adding entirely new data sources and for major structural changes, and incrementing the "minor" data version number (i.e. after the decimal point) for smaller changes to existing structures.

### Frontend

To start a local webpack development server and proxy API requests to https://jeeves.duolingo.com:

```
make install
make web-dev
make web-proxy
```

## Links

- [Jeeves Documentation](https://duolingo.atlassian.net/wiki/spaces/DUO/pages/644121212/Jeeves)
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
