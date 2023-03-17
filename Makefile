# Recompiles the *requirements.in files -> *requirements.txt.
%.txt : %.in
	pip-compile $<

.PHONY: eslint
eslint:
	cd web && "$$(npm bin)/eslint" --ext=.ts,.tsx src

.PHONY: eslint-fix
eslint-fix:
	cd web && "$$(npm bin)/eslint" --ext=.ts,.tsx --fix src

# Installs the requirements to the local environment.
.PHONY: python-install
python-install: dev-requirements.txt
# Create a virtual environment.
	python3 -m venv .venv
# Install the requirements.
	.venv/bin/pip install -r dev-requirements.txt

.PHONY: install
install:
	cd web && npm ci

.PHONY: test
test: web-config
	cd web && "$$(npm bin)/jest" --config config/jest.config.js --silent --watch

.PHONY: python-test
python-test: python-install
	.venv/bin/python -m pytest --disable-warnings

# Starts a local microservice.
.PHONY: web
web:
	docker-compose build
	docker-compose up

spike-worker:
	docker compose build spike-worker
	docker compose up spike-worker

.PHONY: web-build
web-build: web-config
	rm -rf web/dist
	cd web && "$$(npm bin)/webpack" --config config/webpack.config.js --mode production

# Compiles TypeScript files in the web/config/ directory.
.PHONY: web-config
web-config:
	cd web && "$$(npm bin)/tsc" -p config

.PHONY: web-dev
web-dev: web-config
	cd web && "$$(npm bin)/webpack" serve --config config/webpack.config.js --mode development

.PHONY: web-proxy
web-proxy:
	cd web && "$$(npm bin)/lcp" --proxyUrl https://jeeves.duolingo.com --port 5000 --proxyPartial '' --credentials --origin http://localhost:8080
