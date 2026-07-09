# ESP32 → TESAIoT Platform (Server TLS)

Arduino-based MQTT client for ESP32 using Server TLS authentication.

**Security Level:** NCSA Level 1-2 (TLS + Password Authentication)

---

## Overview

This example demonstrates how to connect an ESP32 to TESAIoT Platform using:
- **MQTTS** (MQTT over TLS 1.2+) on port 8884
- Username/password authentication
- WiFi connectivity

## Prerequisites

### Hardware
- ESP32 Development Board (ESP32-DevKitC, ESP32-WROOM-32, etc.)
- USB cable for programming

### Software
- [Arduino IDE 2.x](https://www.arduino.cc/en/software) or [PlatformIO](https://platformio.org/)
- ESP32 Board Package installed
- Required libraries (see below)

### TESAIoT Platform
- Active TESAIoT account
- Device registered on TESAIoT Platform
- Server TLS credentials bundle downloaded

## Arduino IDE Setup

### 1. Install ESP32 Board Package

1. Open **File** → **Preferences**
2. Add to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Open **Tools** → **Board** → **Boards Manager**
4. Search for "esp32" and install **esp32 by Espressif Systems**

### 2. Install Required Libraries

Open **Sketch** → **Include Library** → **Manage Libraries** and install:

| Library | Version | Purpose |
|---------|---------|---------|
| PubSubClient | 2.8+ | MQTT Client |
| ArduinoJson | 7.0+ | JSON Serialization |
| WiFiClientSecure | (included) | TLS Support |

### 3. Configure Credentials

1. Copy `config.h.example` to `config.h`
2. Edit with your credentials:

```cpp
// WiFi Configuration
#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

// MQTT Configuration
#define MQTT_HOST "localhost"
#define MQTT_PORT 8884
#define DEVICE_ID "your-device-id"
#define MQTT_USERNAME "your-device-id"
#define MQTT_PASSWORD "your-mqtt-password"
```

3. Update `ca_cert.h` with TESAIoT CA certificate

### 4. Upload and Run

1. Select your ESP32 board: **Tools** → **Board** → **ESP32 Dev Module**
2. Select the correct port: **Tools** → **Port**
3. Click **Upload**
4. Open **Serial Monitor** (115200 baud)

## Project Structure

```
esp32-servertls/
├── esp32-servertls.ino  # Main sketch
├── config.h.example     # Configuration template
├── ca_cert.h.example    # CA certificate template
├── mqtt_client.cpp      # MQTT client implementation
├── mqtt_client.h        # MQTT client header
├── telemetry.cpp        # Telemetry generation
├── telemetry.h          # Telemetry header
└── README.md            # This file
```

## PlatformIO Setup (Alternative)

```ini
; platformio.ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0.0
monitor_speed = 115200
```

## Telemetry Format

The ESP32 sends JSON telemetry every 10 seconds:

```json
{
  "device_id": "esp32-sensor-001",
  "timestamp": "2025-12-27T21:00:00Z",
  "data": {
    "temperature": 25.5,
    "humidity": 65.2,
    "wifi_rssi": -45,
    "heap_free": 120000
  }
}
```

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `device/{device_id}/telemetry` | Publish | Send sensor data |
| `device/{device_id}/commands` | Subscribe | Receive commands |
| `device/{device_id}/config` | Subscribe | Receive configuration |

## Memory Considerations

- ESP32 has ~320KB RAM
- MQTT buffer size: 512 bytes (adjustable)
- Keep JSON payloads compact
- Use `ArduinoJson` to calculate buffer size

## Power Saving (Optional)

For battery-powered applications:

```cpp
// Deep sleep for 60 seconds
ESP.deepSleep(60e6);
```

## Troubleshooting

### WiFi Connection Failed
- Check SSID and password
- Verify WiFi is 2.4GHz (ESP32 default)

### MQTT Connection Refused (Code 5)
- Verify MQTT_USERNAME matches device_id
- Check password is from Server TLS bundle
- Ensure port 8884 (not 8883 for mTLS)

### SSL Handshake Failed
- Update CA certificate in `ca_cert.h`
- Check ESP32 time is correct (use NTP)

### Memory Issues
- Reduce JSON buffer size
- Use StaticJsonDocument instead of DynamicJsonDocument

## Hardware Sensors (Optional)

Connect DHT22 sensor for real temperature/humidity:

```cpp
#include <DHT.h>
#define DHT_PIN 4
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);
```

## Security Notes

- Always use TLS (port 8884)
- Never hardcode credentials in production
- Consider using ESP32 NVS for secure storage
- This is NCSA Level 1-2; consider mTLS for Level 2+

## Next Steps

After mastering Server TLS, advance to:
- [device-mtls](../device-mtls/) - Mutual TLS with client certificates
- [optiga-trustm](../../advanced/optiga-trustm/) - Hardware security module

---

**NCSA Compliance:** Level 1-2 (Security Baseline + Foundational)
**Last Updated:** 2025-12-27
