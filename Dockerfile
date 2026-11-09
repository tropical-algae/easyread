# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY easyread ./easyread
RUN python -m pip wheel --wheel-dir /wheels .


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EASYREAD_HOME=/data \
    EASYREAD_LOG_STDERR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-dejavu-core \
        fonts-noto-cjk \
        nodejs \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/*.whl \
    && rm -rf /wheels \
    && groupadd --system --gid 10001 easyread \
    && useradd --system --uid 10001 --gid easyread --home-dir /home/easyread --create-home easyread \
    && mkdir -p /data \
    && chown easyread:easyread /data

USER easyread
WORKDIR /data

VOLUME ["/data"]
EXPOSE 8765
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/version', timeout=4).read()"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "easyread", "serve", "--host", "0.0.0.0", "--port", "8765"]
