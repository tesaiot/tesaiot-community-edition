# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# TESAIoT Community Edition - MQTT Telemetry Bridge image.
# Runs the single telemetry/status/heartbeat bridge (no CSR/OTA bridges).

FROM python:3.11.15-slim

WORKDIR /app

# openssl is used (via subprocess) for certificate validity/CN extraction
# when running in mTLS mode; ca-certificates for outbound TLS to the API.
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install only the libraries the bridge actually imports.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the self-contained bridge.
COPY mqtt_telemetry_bridge.py .

# Run as a non-root user.
RUN useradd -m -u 1000 mqttbridge && chown -R mqttbridge:mqttbridge /app
USER mqttbridge

ENV PYTHONUNBUFFERED=1 \
    TMPDIR=/tmp

CMD ["python", "-u", "mqtt_telemetry_bridge.py"]
