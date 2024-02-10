FROM node:16.13.1-alpine3.15 AS web-requirements
# Sentry config
ARG JENKINS_BUILD_NUMBER
ENV SENTRY_RELEASE $JENKINS_BUILD_NUMBER
ENV JENKINS_BUILD_NUMBER=$JENKINS_BUILD_NUMBER

WORKDIR /code
COPY web/package.json .
COPY web/package-lock.json .
RUN npm ci

FROM node:16.13.1-alpine3.15 AS web-builder
# Sentry config
ARG JENKINS_BUILD_NUMBER
ENV SENTRY_RELEASE $JENKINS_BUILD_NUMBER
ENV JENKINS_BUILD_NUMBER=$JENKINS_BUILD_NUMBER

WORKDIR /code
COPY web .
COPY --from=web-requirements /code/node_modules ./node_modules
RUN rm -rf dist && \
  "$(npm bin)/tsc" -p config && \
  "$(npm bin)/webpack" --config config/webpack.config.js --mode production

FROM ubuntu:20.04
# Sentry config
ARG JENKINS_BUILD_NUMBER
ENV SENTRY_RELEASE $JENKINS_BUILD_NUMBER
ENV JENKINS_BUILD_NUMBER=$JENKINS_BUILD_NUMBER

# Opentelemetry Configuration
ENV OTEL_LOGS_EXPORTER none
ENV OTEL_METRICS_EXPORTER none
ENV OTEL_TRACES_EXPORTER otlp,console
ENV OTEL_EXPORTER_OTLP_ENDPOINT 172.17.0.1:4317
ENV OTEL_EXPORTER_OTLP_INSECURE true
ENV OTEL_EXPORTER_OTLP_PROTOCOL grpc
ENV OTEL_EXPORTER_OTLP_TIMEOUT 1
ENV OTEL_SERVICE_NAME jeeves
ENV OTEL_TRACES_SAMPLER parentbased_traceidratio
ENV OTEL_TRACES_SAMPLER_ARG 0.1
ENV OTEL_PROPAGATORS tracecontext,baggage,jaeger


ENV INSTALL_PATH /code
ENV REQ_TXT requirements.txt
ENV PYTHONIOENCODING UTF-8
ENV DUOLINGO_CONFIG=${INSTALL_PATH}/config/prod.yml
ENV PYTHONPATH /code
ENV DUPLICATE_DETECTOR_MODEL=${INSTALL_PATH}/duplicate-detector-model/
ENV PRIORITY_ESTIMATOR_MODEL=${INSTALL_PATH}/priority_estimator_model/

WORKDIR $INSTALL_PATH

# Modified techniques from:
# https://blog.codeship.com/alpine-based-docker-images-make-difference-real-world-apps/

COPY $REQ_TXT $REQ_TXT

RUN mkdir -p data/zendesk

RUN apt-get update \
 && apt-get -y --no-install-recommends install \
      build-essential \
      python3-dev \
      python3-pip \
#     libpq-dev is a postgres library needed by sqlalchemy
      libpq-dev \
#     necessary for weasyprint to create pdf files for bug reports
      libpango-1.0-0 \
      libharfbuzz0b \
      libpangoft2-1.0-0 \
 && rm -rf /var/lib/apt/lists/* \
 && ln -s /usr/bin/python3 /usr/bin/python

RUN pip3 install -U pip pip-tools wheel \
 && pip3 install setuptools

ARG REQUIREMENTS=requirements.txt
COPY $REQUIREMENTS $REQUIREMENTS
RUN pip3 install -r "$REQUIREMENTS" --src /usr/local/src

COPY . .
COPY --from=web-builder /code/dist ./web/dist

EXPOSE 5000

CMD ["opentelemetry-instrument", "uwsgi", "uwsgi.ini"]
