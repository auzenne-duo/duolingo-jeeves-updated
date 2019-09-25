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
- Opening a PR will automatically trigger deployment to [`https://duolingo-jeeves-dev.duolingo.com`](https://duolingo-jeeves-dev.duolingo.com)
- Merging a PR will automatically trigger deployment to [`https://duolingo-jeeves-prod.duolingo.com`](https://duolingo-jeeves-prod.duolingo.com)

## How to contribute
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

Run `make format` when you made changes to JS files.

## Links
- [Jeeves Documentation](https://app.getguru.com/#/facts/60992fb0-ec19-4c3a-b3d1-8429750d448e)
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
