# ESP32 Server TLS Architecture (Arduino)

## Overview

Arduino-based MQTT client for ESP32 with Server TLS authentication.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32 Board                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 esp32-servertls.ino                        │ │
│  │                   (Main Sketch)                            │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                   │
│          ┌──────────────────┼───────────────────┐               │
│          │                  │                   │               │
│          ▼                  ▼                   ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐      │
│  │   WiFi.h    │    │ PubSubClient│    │ WiFiClientSecure│      │
│  │ (Network)   │    │ (MQTT)      │    │ (TLS)           │      │
│  └─────────────┘    └─────────────┘    └────────┬────────┘      │
│                                                 │               │
│  ┌─────────────┐    ┌─────────────┐             │               │
│  │  config.h   │    │ ca_cert.h   │─────────────┘               │
│  │ (Settings)  │    │ (CA Cert)   │                             │
│  └─────────────┘    └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  MQTTS (TLS 1.2)
                              │  Port 8883
                              ▼
                   ┌──────────────────────┐
                   │   TESAIoT Platform   │
                   │  ┌────────────────┐  │
                   │  │  EMQX Broker   │  │
                   │  └────────────────┘  │
                   └──────────────────────┘
```

## Connection Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        Startup Sequence                          │
└──────────────────────────────────────────────────────────────────┘

     ┌─────────┐
     │  setup()│
     └────┬────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│ WiFi.begin()    │───▶│ Wait for WiFi   │
│ (Connect AP)    │    │ Connection      │
└─────────────────┘    └────────┬────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Load CA Certificate │
                    │ WiFiClientSecure    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ TLS Handshake       │
                    │ (Verify Server)     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ MQTT CONNECT        │
                    │ (device_id, api_key)│
                    └──────────┬──────────┘
                               │
                               ▼
     ┌─────────┐     ┌─────────────────────┐
     │  loop() │◀────│ Connection Ready    │
     └────┬────┘     └─────────────────────┘
          │
          │  Every 10 seconds
          ▼
┌─────────────────┐    ┌─────────────────┐
│ Read Sensor     │───▶│ MQTT Publish    │
└─────────────────┘    └─────────────────┘
```

## Memory Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    Flash Memory (4MB)                           │
├─────────────────────────────────────────────────────────────────┤
│  Program Code (~500KB)  │  CA Certificate (~2KB)  │  SPIFFS     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      RAM (520KB)                                │
├─────────────────────────────────────────────────────────────────┤
│  Stack (8KB/task)  │  Heap (Dynamic)  │  Static Variables       │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

```cpp
// config.h
#define WIFI_SSID "your_network"
#define WIFI_PASSWORD "your_password"

#define MQTT_HOST "localhost"
#define MQTT_PORT 8883
#define MQTT_DEVICE_ID "esp32-001"
#define MQTT_API_KEY "tesa_mqtt_org_key_xxx"
```

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `device/{id}/telemetry/sensor` | Publish | Sensor data |
| `device/{id}/status` | Publish | Device status |
| `device/{id}/commands/#` | Subscribe | Commands |

## Libraries

- WiFi.h - Network connection
- WiFiClientSecure.h - TLS implementation
- PubSubClient.h - MQTT protocol
- ArduinoJson.h - JSON handling

## Error Recovery

```
┌─────────┐     No      ┌─────────────────┐
│  WiFi   │────────────▶│  Reconnect WiFi │
│Connected│             │  (Wait 5s)      │
└────┬────┘             └────────┬────────┘
     │                           │
     │ Yes                       │
     ▼                           │
┌─────────┐     No      ┌────────┴────────┐
│  MQTT   │────────────▶│  Reconnect MQTT │
│Connected│             │  (Wait 5s)      │
└────┬────┘             └─────────────────┘
     │
     │ Yes
     ▼
┌─────────────────┐
│ Publish Data    │
│ (Every 10s)     │
└─────────────────┘
```

## NCSA Compliance

| Level | Requirement | Implementation |
|-------|-------------|----------------|
| Level 1 | Encrypted transport | TLS 1.2 |
| Level 1 | Server verification | CA certificate |
| Level 2 | Secure storage | Flash-based storage |
