# TESAIoT Live Streaming Dashboard

Real-time MQTT telemetry visualization dashboard for TESAIoT Platform. Stream and visualize IoT device data with WebSocket Secure (WSS) MQTT connections.

![Dashboard Screenshot](docs/screenshot.png)

## Features

- **Real-time Streaming**: Live telemetry data via WSS MQTT
- **Multi-Series Charts**: Dual Y-axis for different value ranges
- **Series Control**: Toggle visibility of individual metrics
- **Raw Data Terminal**: View incoming MQTT messages in terminal format
- **Connection Management**: Token-based authentication with status indicators
- **Responsive Design**: Works on desktop and tablet devices
- **Dark Theme**: Easy on the eyes for monitoring sessions

## Quick Start

### Prerequisites

- Node.js 18+ or 20+
- npm or yarn
- TESAIoT Platform account with MQTT API token

### Get Your MQTT Token

1. Log in to [TESAIoT Admin Portal](https://admin.tesaiot.com)
2. Navigate to **Settings → MQTT API Tokens**
3. Click **Create Token**
4. Copy the generated token (format: `tesa_mqtt_<org>_<32chars>`)

### Development

```bash
# Clone the repository
git clone https://github.com/tesaiot/developer-hub.git
cd developer-hub/examples/live-streaming-dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:5173 in your browser
```

### Production Build

```bash
# Build optimized bundle
npm run build

# Preview production build
npm run preview
```

### Docker Deployment

```bash
# Build and run with Docker
docker build -t tesaiot-streaming-dashboard .
docker run -p 8080:80 tesaiot-streaming-dashboard

# Or use docker-compose
docker-compose up -d
```

## Configuration

### Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_MQTT_BROKER_URL` | WSS MQTT broker URL | `wss://mqtt.tesaiot.com:8085/mqtt` |
| `VITE_MQTT_TOPIC` | Telemetry topic pattern | `device/+/telemetry/#` |

### Chart Series

The default series configuration in `App.tsx`:

| Series | Color | Y-Axis | Default Visible |
|--------|-------|--------|-----------------|
| Temperature (°C) | Red | Left | Yes |
| Humidity (%) | Blue | Left | Yes |
| Pressure (hPa) | Green | Left | No |
| AI Confidence | Green | Right | Yes |
| Anomaly Score | Orange | Right | No |

Customize by editing the `DEFAULT_SERIES` array in `src/App.tsx`.

## Project Structure

```
live-streaming-dashboard/
├── src/
│   ├── components/
│   │   ├── Charts/
│   │   │   └── StreamChart.tsx    # Recharts line chart
│   │   ├── Dashboard/
│   │   │   └── RawDataTerminal.tsx # Terminal-style message view
│   │   └── MQTT/
│   │       └── ConnectionPanel.tsx # Connection controls
│   ├── hooks/
│   │   └── useMQTTStream.ts       # MQTT connection hook
│   ├── types/
│   │   └── index.ts               # TypeScript interfaces
│   ├── App.tsx                    # Main application
│   ├── main.tsx                   # React entry point
│   └── index.css                  # Tailwind imports
├── Dockerfile                     # Multi-stage production build
├── docker-compose.yml             # Container orchestration
├── nginx.conf                     # Production server config
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## API Reference

### useMQTTStream Hook

```typescript
import { useMQTTStream } from './hooks/useMQTTStream';

const {
  status,       // 'disconnected' | 'connecting' | 'connected' | 'error'
  error,        // Error message or null
  messages,     // Array of TelemetryMessage
  messageCount, // Total messages received
  connect,      // () => void
  disconnect,   // () => void
  clearMessages // () => void
} = useMQTTStream({
  token: 'tesa_mqtt_...',           // Required: MQTT API token
  brokerUrl: 'wss://...',           // Optional: Custom broker URL
  topic: 'device/+/telemetry/#',    // Optional: Custom topic pattern
  maxMessages: 1000,                // Optional: Message buffer size
});
```

### TelemetryMessage Interface

```typescript
interface TelemetryMessage {
  topic: string;      // Full MQTT topic
  deviceId: string;   // Extracted device ID
  timestamp: Date;    // Message receive time
  data: Record<string, unknown>;  // Parsed JSON payload
}
```

## Customization

### Adding New Series

1. Edit `DEFAULT_SERIES` in `src/App.tsx`:

```typescript
const DEFAULT_SERIES: SeriesConfig[] = [
  // ... existing series
  {
    key: 'battery',           // Key in telemetry payload
    name: 'Battery Level',    // Display name
    color: '#8b5cf6',         // Line color (hex)
    yAxisId: 'left',          // 'left' or 'right'
    visible: true,            // Initial visibility
    unit: '%'                 // Optional unit display
  },
];
```

2. Ensure your devices send telemetry with the matching key:

```json
{
  "temperature": 25.5,
  "humidity": 60.0,
  "battery": 85.0
}
```

### Changing Theme Colors

Edit `tailwind.config.js` or modify Tailwind classes in components.

## MQTT Topic Structure

The dashboard subscribes to: `device/+/telemetry/#`

Expected topic format:
```
device/{device_id}/telemetry/{subtopic}
```

Examples:
- `device/sensor-001/telemetry/environment`
- `device/gateway-a/telemetry/system`

## Troubleshooting

### Connection Fails

1. **Check token format**: Must start with `tesa_mqtt_`
2. **Verify token is active**: Check in Admin Portal
3. **Check browser console**: Look for WebSocket errors
4. **Firewall**: Ensure port 8085 is accessible

### No Data Appearing

1. **Verify devices are publishing**: Check device logs
2. **Check topic pattern**: Ensure topic matches subscription
3. **JSON format**: Payload must be valid JSON with numeric values

### Chart Not Updating

1. **Check series visibility**: Enable series in sidebar
2. **Verify numeric values**: Chart only shows numeric fields
3. **Check data keys**: Keys must match series configuration

## Contributing

Contributions are welcome! Please read our [Contributing Guide](../../CONTRIBUTING.md).

## License

Apache 2.0 - See [LICENSE](../../LICENSE)

## Credits

Built with [TESAIoT Platform Examples](https://github.com/tesaiot/developer-hub)
