FROM node:12.13.1-alpine3.10 AS web-requirements

WORKDIR /code
COPY web/package.json .
COPY web/package-lock.json .
RUN npm ci

FROM node:12.13.1-alpine3.10 AS web-builder

WORKDIR /code
COPY web .
COPY --from=web-requirements /code/node_modules ./node_modules
RUN rm -rf dist && \
  "$(npm bin)/tsc" -p config && \
  "$(npm bin)/webpack" --config config/webpack.config.js --mode production

FROM ubuntu:18.04

ENV INSTALL_PATH /code
ENV REQ_TXT requirements.txt
ENV PYTHONIOENCODING UTF-8
ENV DUOLINGO_CONFIG=${INSTALL_PATH}/config/prod.yml
ENV DUPLICATE_DETECTOR_MODEL=${INSTALL_PATH}/duplicate-detector-model/

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
 && rm -rf /var/lib/apt/lists/* \
 && ln -s /usr/bin/python3 /usr/bin/python

RUN pip3 install -U pip pip-tools wheel \
 && pip3 install setuptools==49.6.0

ARG REQUIREMENTS=requirements.txt
COPY $REQUIREMENTS $REQUIREMENTS
RUN pip3 install -r "$REQUIREMENTS" --src /usr/local/src

COPY . .
COPY --from=web-builder /code/dist ./web/dist

EXPOSE 5000

CMD ["uwsgi", "uwsgi.ini"]
