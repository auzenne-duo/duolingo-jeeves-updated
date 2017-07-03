# duolingo-jeeves
Technology-driven user support.

## Owner
- Lawrence Wolf-Sonkin, lawrence@duolingo.com
- Hideki Shima, hideki@duolingo.com

## Set up
- [Install Docker](https://docs.docker.com/docker-for-mac/install/) on your computer.
- Run `docker-compose build` in the repo directory.
- Run `docker-compose up` to start the service with log output streaming to the console.
- Open [`http://localhost:5000/`](http://localhost:5000/)
- Press `Ctrl-C` to stop the service. If the service does not stop cleanly (check with
`docker-compose ps`), you can run `docker-compose down` to forcefully stop it.

## How to deploy
- Opening a PR will automatically trigger deployment to [`https://duolingo-jeeves-dev.duolingo.com`](https://duolingo-jeeves-dev.duolingo.com)
- Merging a PR will automatically trigger deployment to [`https://duolingo-jeeves-prod.duolingo.com`](https://duolingo-jeeves-prod.duolingo.com)

## Links
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
