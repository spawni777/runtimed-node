ARG PYTHON_VERSION=3.12

FROM python:$PYTHON_VERSION-slim AS build

ARG TARGETARCH=amd64
ARG RUNTIMED_REPO=spawni777/runtimed
ARG RUNTIMED_BINARY_URL

ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY scripts/fetch-runtimed-release.sh /tmp/fetch-runtimed-release.sh
COPY prebuilt/ /tmp/runtimed-prebuilt/

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc python3-dev libpq-dev curl ca-certificates \
    && chmod +x /tmp/fetch-runtimed-release.sh \
    && if [ -f "/tmp/runtimed-prebuilt/runtimed-linux-${TARGETARCH}" ]; then \
         echo "Dockerfile: using prebuilt/runtimed-linux-${TARGETARCH}"; \
         RUNTIMED_LOCAL_BINARY="/tmp/runtimed-prebuilt/runtimed-linux-${TARGETARCH}" /tmp/fetch-runtimed-release.sh _ _; \
       else \
         RUNTIMED_BINARY_URL="${RUNTIMED_BINARY_URL:-}" /tmp/fetch-runtimed-release.sh "${RUNTIMED_REPO}" "${TARGETARCH}"; \
       fi \
    && rm -f /tmp/fetch-runtimed-release.sh \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip setuptools \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin/runtimed /usr/local/bin/runtimed
COPY --from=build /usr/local/share/runtimed /usr/local/share/runtimed

COPY . /code

CMD ["bash", "-c", "python main.py"]
