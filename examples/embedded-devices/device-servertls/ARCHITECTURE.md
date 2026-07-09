# Device Server TLS Architecture (C)

## Overview

C-based MQTT client with Server TLS for embedded systems and Linux devices.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      C Application                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │     main.c      │───▶│  mqtt_handler.c │                     │
│  │  (Entry Point)  │    │  (Paho MQTT C)  │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                              │
│           ▼                      ▼                              │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │   config.c      │    │   tls_config.c  │                     │
│  │ (JSON Parser)   │    │   (OpenSSL)     │                     │
│  └─────────────────┘    └─────────┬───────┘                     │
│                                   │                             │
└───────────────────────────────────┼─────────────────────────────┘
                                    │
                                    │  MQTTS (TLS 1.2+)
                                    │  Port 8883
                                    ▼
                         ┌──────────────────────┐
                         │   TESAIoT Platform   │
                         │                      │
                         │  ┌────────────────┐  │
                         │  │  EMQX Broker   │  │
                         │  │  (MQTTS)       │  │
                         │  └────────────────┘  │
                         └──────────────────────┘
```

## TLS Handshake

```
Device                                         EMQX Broker
  │                                                  │
  │──────────── TCP Connect :8883 ─────────────────▶ │
  │                                                  │
  │◀─────────── ServerHello + Certificate ────────── │
  │                                                  │
  │  ┌─────────────────┐                             │
  │  │ Verify against  │                             │
  │  │ CA Certificate  │                             │
  │  └─────────────────┘                             │
  │                                                  │
  │──────────── ClientKeyExchange ─────────────────▶ │
  │                                                  │
  │◀─────────── Finished ─────────────────────────── │
  │                                                  │
  │═══════════ TLS Tunnel Established ══════════════ │
  │                                                  │
  │──────────── MQTT CONNECT + API Key ────────────▶ │
  │                                                  │
  │◀─────────── CONNACK (Success) ────────────────── │
  │                                                  │
```

## Memory Layout

```
┌─────────────────────────────────────────────────────┐
│                   Flash/ROM                         │
├─────────────────────────────────────────────────────┤
│  Program Code        │  CA Certificate (~2KB)       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    RAM                              │
├─────────────────────────────────────────────────────┤
│  Stack (local vars)  │  Heap (MQTT/SSL contexts)    │
├─────────────────────────────────────────────────────┤
│  Static/Global       │  Message Buffers             │
└─────────────────────────────────────────────────────┘
```

## Key Components

| Component | Description | File |
|-----------|-------------|------|
| Main Entry | Application setup | `main.c` |
| MQTT Handler | Connection and messaging | `mqtt_handler.c` |
| TLS Setup | OpenSSL configuration | `tls_config.c` |
| Config Parser | JSON/ENV parsing | `config.c` |

## Build

```bash
# CMake
mkdir build && cd build
cmake .. && make

# Manual
gcc -o device_client main.c mqtt_handler.c tls_config.c \
    -lpaho-mqtt3as -lssl -lcrypto -lpthread
```

## Libraries

- libpaho-mqtt3as - MQTT with async/SSL
- libssl - TLS implementation
- libcrypto - Cryptographic operations

## NCSA Compliance

| Level | Requirement | Implementation |
|-------|-------------|----------------|
| Level 1 | Transport encryption | TLS 1.2+ via OpenSSL |
| Level 1 | Server authentication | CA certificate validation |
| Level 2 | Credential security | API key in env/file |
