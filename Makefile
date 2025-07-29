# Recompiles the *requirements.in files -> *requirements.txt.
%.txt : %.in
	pip-compile $<

.PHONY: eslint
eslint:
	cd web && npx eslint --ext=.ts,.tsx src

.PHONY: eslint-fix
eslint-fix:
	cd web && npx eslint --ext=.ts,.tsx --fix src

.PHONY: lint-spec
lint-spec:
	duo apiary spec lint docs/openapi.yaml --use-ignore-file docs/ignore.yaml

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
	cd web && npx jest --config config/jest.config.js --silent --watch

.PHONY: python-test
python-test: python-install
	.venv/bin/python -m pytest --disable-warnings

# Starts a local microservice.
.PHONY: web
web:
	docker compose build
	docker compose up

spike-worker:
	docker compose build spike-worker
	docker compose up spike-worker

.PHONY: web-build
web-build: web-config
	rm -rf web/dist
	cd web && npx webpack --config config/webpack.config.js --mode production

# Compiles TypeScript files in the web/config/ directory.
.PHONY: web-config
web-config:
	cd web && npx tsc -p config

.PHONY: web-dev
web-dev: web-config
	cd web && npx webpack serve --config config/webpack.config.js --mode development --env api='http://localhost:5000/api'

.PHONY: web-proxy
web-proxy:
	cd web && npx lcp --proxyUrl https://jeeves.duolingo.com --port 5000 --proxyPartial '' --credentials --origin http://localhost:8080
