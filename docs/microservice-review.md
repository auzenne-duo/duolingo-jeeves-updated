# Microservice Review — `{duolingo-jeeves}` (self-evaluation)

---

- Based on the [Microservice Review rubric](https://docs.google.com/a/duolingo.com/document/d/1RlihzU59vZWiCQ638Key_AzH4PikpNUiG0WK3eZFExg/edit?usp=sharing)
- `(*)`: not a yes-no question

Use the following legend for `Status`:
- `:heavy_check_mark:` (:heavy_check_mark:) for "all good"
- (empty) for "needs work" or if unsure
- `N/A` for "does not apply"

---

## Documentation
| Item | Status |
| ---- |:---:|
| Is there a README file? | :heavy_check_mark: |
| Does the README file specify an owner? | :heavy_check_mark: |
| Is the documentation sufficient to install and run the microservice locally? | :heavy_check_mark: |
| Does the README state its dependencies? | |
| Does the README state its clients? | |
| Is the API documented? | |
| Is the architecture explained? (e.g. architecture diagram) |  |
| Are there instructions for setting up a working development environment? | :heavy_check_mark: |
| Are processes explained? | |


## Software Architecture, Code Quality, and Security
| Item | Status |
| ---- |:---:|
| Is data access cleanly separated from models, i.e. is there a DAL? | N/A (Not much code yet) |
| `(*)` What is the linter output on the codebase? | |
| Is there no duplicate code? | N/A (Not much code yet) |
| Is there, in general, one way to do things? | N/A (Not much code yet) |
| Is there no dead code? | N/A (Not much code yet) |
| Are variables, functions, files, classes, etc. properly named? | N/A (Not much code yet) |
| Is the code performant? (e.g. avoids queries in loops, uses sets where appropriate) | N/A (Not much code yet) |
| Is the code architected to be scalable and flexible? | N/A (Not much code yet) |
| Is the API RESTful and well-designed? | N/A (Not much code yet) |
| Are there no passwords or keys stored in plaintext in the repo? | :heavy_check_mark: |
| Is the code documented? (e.g. docstrings) | N/A (Not much code yet) |
| Does data (e.g. json, tables) have a schema? | N/A (Not much code yet) |
| Is there a pre-commit yaml and is it extensive? | :heavy_check_mark: |


## Tests
| Item | Status |
| ---- |:---:|
| `(*)` What is the unit test coverage? | |
| Are there appropriate integration and acceptance tests? | N/A (Not much code yet) |


## Processes
| Item | Status |
| ---- |:---:|
| Is there CI? | :heavy_check_mark: |
| Does the CI run on every PR? | :heavy_check_mark: |
| `(*)` How long does it take for PRs to be merged? | |
| Are there no old outstanding PRs? | :heavy_check_mark: |
| Does it use Galaxy (where applicable)? | :heavy_check_mark: |
| Does it have a `dev` environment? | :heavy_check_mark: |
| Does it have a `stage` environment? | |
| Does it have CloudWatch alarms? |  |
| Does it have Rollbar set up? | |
| Are Grafana dashboards complete? | |
| Are application logs available in Kibana and are the fields properly parsed? | |
| Is there a PagerDuty rotation in place? | |
| Is code review taken seriously and done rigorously? | |
| Are there _quick_ smoke tests (e.g. `curl` one-liners) for local development to make sure that the environment is working as expected? | |
