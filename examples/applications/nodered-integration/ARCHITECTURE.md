# Node-RED Integration Architecture

## Overview

Custom Node-RED nodes for connecting to TESAIoT Platform via MQTT and REST API.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Node-RED Runtime                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     Flow Editor                          │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐│   │
│  │  │ TESAIoT │───▶│ Function│───▶│ TESAIoT │───▶│Dashboard││   │
│  │  │ MQTT In │    │  Node   │    │ API Out │    │  Node   ││   │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘│   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   TESAIoT Nodes Package                  │   │
│  │                                                          │   │
│  │  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐ │   │
│  │  │ tesaiot-mqtt │    │ tesaiot-api  │   │tesaiot-config│ │   │
│  │  │ (sub/pub)    │    │ (REST calls) │   │ (settings)   │ │   │
│  │  └──────────────┘    └──────────────┘   └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
              │                              │
              │  WSS (MQTT)                  │  HTTPS (REST)
              ▼                              ▼
       ┌─────────────┐                ┌─────────────┐
       │ EMQX Broker │                │   REST API  │
       └─────────────┘                └─────────────┘
```

## Directory Structure

```
nodered-integration/
├── src/
│   ├── lib/
│   │   ├── mqtt-client.ts     # MQTT connection
│   │   └── api-client.ts      # REST API client
│   └── nodes/
│       ├── tesaiot-mqtt-in.ts    # Subscribe node
│       ├── tesaiot-mqtt-out.ts   # Publish node
│       ├── tesaiot-api.ts        # API node
│       └── tesaiot-config.ts     # Config node
├── flows/
│   ├── device-monitoring.json   # Example flow
│   └── alert-handler.json       # Example flow
├── theme/
│   └── icons/                   # Node icons
└── package.json
```

## Node Types

| Node | Purpose | Icon |
|------|---------|------|
| tesaiot-mqtt-in | Subscribe to topics | Input |
| tesaiot-mqtt-out | Publish to topics | Output |
| tesaiot-api | REST API calls | HTTP |
| tesaiot-config | Shared configuration | Config |

## Flow Example

```
┌─────────────────────────────────────────────────────────────────┐
│                    Device Temperature Alert                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ TESAIoT      │───▶│   Function   │───▶│   Switch     │
│ MQTT In      │    │ Parse JSON   │    │ temp > 30?   │
│ (telemetry)  │    │              │    │              │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                           ┌───────────────────┴───────────────────┐
                           │                                       │
                           ▼                                       ▼
                   ┌──────────────┐                        ┌──────────────┐
                   │   Change     │                        │    Debug     │
                   │ Set warning  │                        │   (normal)   │
                   └──────┬───────┘                        └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Email/Slack │
                   │   Alert      │
                   └──────────────┘
```

## Configuration Node

```javascript
// tesaiot-config node properties
{
  "name": "TESAIoT Production",
  "mqttHost": "mqtt.tesaiot.com",
  "mqttPort": 8085,
  "mqttProtocol": "wss",
  "apiUrl": "https://admin.tesaiot.com/api/v1",
  "apiKey": "***",
  "organizationId": "my-org"
}
```

## Installation

```bash
# From npm
npm install @tesaiot/node-red-nodes

# From source
cd nodered-integration
npm install
npm run build
npm link

# In Node-RED directory
npm link @tesaiot/node-red-nodes
```

## Message Format

```javascript
// MQTT message output
msg.payload = {
  device_id: "device-001",
  timestamp: "2024-01-15T10:30:00Z",
  data: {
    temperature: 25.5,
    humidity: 60.2
  }
};

msg.topic = "device/device-001/telemetry/sensor";
```

## Dependencies

- mqtt - MQTT client
- axios - HTTP client
- node-red - Node-RED runtime

## Example Flows

| Flow | Description |
|------|-------------|
| device-monitoring.json | Real-time device dashboard |
| alert-handler.json | Temperature alert to Slack |
