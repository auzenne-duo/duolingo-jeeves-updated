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

FROM 940168671796.dkr.ecr.us-east-1.amazonaws.com/duolingo/base/py3:0.1.0

ENV INSTALL_PATH /code
ENV REQ_TXT requirements.txt
ENV PYTHONIOENCODING UTF-8
ENV DUOLINGO_CONFIG=${INSTALL_PATH}/config/prod.yml

WORKDIR $INSTALL_PATH

# Modified techniques from:
# https://blog.codeship.com/alpine-based-docker-images-make-difference-real-world-apps/

COPY $REQ_TXT $REQ_TXT

RUN mkdir -p data/zendesk

RUN apk add --no-cache --virtual .build-deps \
  g++ linux-headers musl-dev \
    && ln -s /usr/include/locale.h /usr/include/xlocale.h \
    && pip3 install numpy==1.13.0 \
    && pip3 install -r "$REQ_TXT" \
    && find /usr/local \
        \( -type d -a -name test -o -name tests \) \
        -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
        -exec rm -rf '{}' + \
    && runDeps="$( \
        scanelf --needed --nobanner --recursive /usr/local \
                | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
                | sort -u \
                | xargs -r apk info --installed \
                | sort -u \
    )" \
    && apk add --virtual .rundeps $runDeps \
    && apk del .build-deps \
    && rm -rf /root/.cache

COPY . .
COPY --from=web-builder /code/dist ./web/dist

EXPOSE 5000

CMD ["uwsgi", "uwsgi.ini"]
