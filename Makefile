NPM_BIN = $(shell npm bin)

# Run Prettier to format all JavaScript
.PHONY: format
format:
	$(NPM_BIN)/prettier --single-quote --trailing-comma es5 --write "jeeves/**/*.js"

# Starts a local microservice.
.PHONY: web
web: install-requirements
	docker-compose build
	docker-compose up

# Recompiles the *requirements.in files -> *requirements.txt.
%.txt : %.in
	pip-compile $<

# Installs the requirements to the local environment.
.PHONY: install-requirements
install-requirements: requirements.txt
	pip install -r requirements.txt
