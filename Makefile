# Recompiles the *requirements.in files -> *requirements.txt.
%.txt : %.in
	pip-compile $<

# Installs the requirements to the local environment.
.PHONY: install
install:
	cd web && npm ci

# Starts a local microservice.
.PHONY: web
web:
	docker-compose build
	docker-compose up

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
