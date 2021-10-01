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
.PHONY: install
install:
	cd web && npm ci

# Starts a local microservice.
.PHONY: web
web:
# TODO don't use build args for secrets (See https://docs.docker.com/engine/reference/builder/#arg
	docker-compose build --build-arg aws_access_key=${AWS_ACCESS_KEY_ID} --build-arg aws_secret_key=${AWS_SECRET_ACCESS_KEY}
	docker-compose up

spike-worker:
# TODO don't use build args for secrets (See https://docs.docker.com/engine/reference/builder/#arg
	docker compose build spike-worker --build-arg aws_access_key=${AWS_ACCESS_KEY_ID} --build-arg aws_secret_key=${AWS_SECRET_ACCESS_KEY}
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
