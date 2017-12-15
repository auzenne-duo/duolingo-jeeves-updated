# Microservice Review — `duolingo-jeeves`

---

Use the following legend for `Status`:

| Status | Status Description |
| :---: | ---- |
| :white_check_mark: | Passed automated check |
| :x: | Failed automated check |
| :heavy_check_mark: | Passed manual check |
| :heavy_multiplication_x: | Failed manual check |
| N/A | Not applicable |
| None | No automated check — requires human intervention |

---

## Documentation
| Item | Status |
| ---- |:---:|
| Is there a README file? | :white_check_mark: |
| Does the README file specify an owner? | :white_check_mark: |
| Is the documentation sufficient to install and run the microservice locally? | :heavy_check_mark: |
| Does the README state its dependencies on other microservices? | :heavy_multiplication_x: |
| Does the README state its clients? | :heavy_multiplication_x: |
| Is the API documented? | :heavy_multiplication_x: |
| Is the architecture explained? (e.g. architecture diagram) | :heavy_multiplication_x: |
| Are operational processes explained? (e.g. deployment, DB schema changes, data loaders) | :heavy_multiplication_x: |



## Software Architecture, Code Quality, and Security
| Item | Status |
| ---- |:---:|
| Is data access cleanly separated from models, i.e. is there a DAL? | :white_check_mark: |
| What is the linter output on the codebase? | :white_check_mark: |
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
| Is there a pre-commit yaml and is it extensive? | :white_check_mark: |



## Tests
| Item | Status |
| ---- |:---:|
| What is the unit test coverage? | None |
| Are there appropriate integration and acceptance tests? | N/A (Not much code yet) |
| Are there instructions for running the tests locally? | :heavy_multiplication_x: |
| Are there _quick_ smoke tests (e.g. `curl` one-liners) for local development to make sure that the environment is working as expected? | :heavy_multiplication_x: |



## Processes
| Item | Status |
| ---- |:---:|
| Is there CI? | :white_check_mark: |
| Does the CI run on every PR? | :white_check_mark: |
| Is code review taken seriously and done rigorously? | :white_check_mark: |
| How long does it take for PRs to be merged? | <1 day |
| Are there no old outstanding PRs? | :heavy_check_mark: |
| Does it use Galaxy (where applicable)? | :white_check_mark: |
| Does it have a `dev` environment? | :white_check_mark: |
| Does it have a `stage` environment? | :x: |
| Does it have CloudWatch alarms? | N/A |
| Does it have Rollbar set up? | N/A |
| Are Grafana dashboards complete? | N/A |
| Are application logs available in Kibana and are the fields properly parsed? | N/A |
| Is there a PagerDuty rotation in place? | N/A |
