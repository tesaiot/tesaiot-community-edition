# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
# TESAIoT Community Edition - API service image.

FROM python:3.11.15-slim AS builder

WORKDIR /app

# Build deps for psycopg2 / cryptography wheels
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    python3-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir --default-timeout=600 -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.11.15-slim

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user
RUN useradd -m -u 1000 -s /bin/bash tesa && \
    mkdir -p /app/logs /app/certs /app/src && \
    chown -R tesa:tesa /app

# Installed Python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Application code
COPY --chown=tesa:tesa ./api/ ./api/
COPY --chown=tesa:tesa ./utils/ ./utils/
# Device-bundle generation assets (C-header templates, trust anchors). Read at
# runtime from /app/scripts by certificate_service.py.
COPY --chown=tesa:tesa ./scripts/ ./scripts/
COPY --chown=tesa:tesa ./certificate_manager_vault_enhanced.py ./certificate_manager_vault.py \
                       ./vault_integration.py ./vault_key_manager.py ./
COPY --chown=tesa:tesa ./VERSION.txt ./VERSION.txt

ARG CACHEBUST=1
ARG BUILD_DATE=unknown
ARG BUILD_HASH=unknown
RUN echo "BUILD_TIME: ${BUILD_DATE}" > /app/BUILD_INFO && \
    echo "BUILD_ID: ${CACHEBUST}" >> /app/BUILD_INFO && \
    echo "GIT_HASH: ${BUILD_HASH}" >> /app/BUILD_INFO && \
    echo "VERSION: $(cat /app/VERSION.txt 2>/dev/null || echo 'unknown')" >> /app/BUILD_INFO && \
    chown tesa:tesa /app/BUILD_INFO

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LOG_DIR=/app/logs

USER tesa

EXPOSE 5566

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5566/api/v1/health || exit 1

# Production WSGI server (gunicorn) instead of the Werkzeug dev server.
# `python -m gunicorn` avoids any PATH dependency on /usr/local/bin (only
# site-packages are copied from the builder stage). The WSGI callable is the
# module-level `app = create_app(ENV)` in api/app.py.
# Worker/thread counts are env-tunable; defaults sized for a small host.
CMD ["sh", "-c", "exec python -m gunicorn \
      --bind 0.0.0.0:5566 \
      --workers ${GUNICORN_WORKERS:-4} \
      --threads ${GUNICORN_THREADS:-2} \
      --timeout ${GUNICORN_TIMEOUT:-120} \
      --access-logfile - \
      --error-logfile - \
      api.app:app"]
