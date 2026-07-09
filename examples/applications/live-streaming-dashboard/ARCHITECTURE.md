# Live Streaming Dashboard Architecture

## Overview

The Live Streaming Dashboard is a React-based Single Page Application (SPA) that provides real-time visualization of IoT telemetry data streamed via MQTT over WebSocket Secure (WSS).

```ini
┌─────────────────────────────────────────────────────────────────────────┐
│                        Browser Application                              │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                           App.tsx                                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │ │
│  │  │ Connection   │  │  Stream      │  │  Series Control        │    │ │
│  │  │ Panel        │  │  Chart       │  │  + Display Options     │    │ │
│  │  └──────┬───────┘  └──────┬───────┘  └────────────────────────┘    │ │
│  │         │                 │                                        │ │
│  │         ▼                 ▼                                        │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │                    useMQTTStream Hook                         │ │ │
│  │  │  - Connection management                                      │ │ │
│  │  │  - Message parsing                                            │ │ │
│  │  │  - State synchronization                                      │ │ │
│  │  └──────────────────────────┬────────────────────────────────────┘ │ │
│  └─────────────────────────────│──────────────────────────────────────┘ │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                        mqtt.js Library                              ││
│  │                    (WebSocket Transport)                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ WSS (Port 8085)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        TESAIoT Platform                                  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                      EMQX MQTT Broker                              │  │
│  │  - WebSocket listener on :8085                                     │  │
│  │  - Token-based authentication                                      │  │
│  │  - Topic ACL enforcement                                           │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 ▲                                        │
│                                 │ MQTT                                   │
│                                 │                                        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                     IoT Devices                                    │  │
│  │  - Publish to device/{id}/telemetry/{type}                         │  │
│  │  - JSON payloads with numeric sensor values                        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Authentication Flow

```ini
┌──────────┐        ┌────────────┐        ┌─────────────┐
│  User    │  1.    │ Dashboard  │  2.    │   EMQX      │
│          │───────▶│            │───────▶│   Broker    │
│          │ Enter  │            │ CONNECT│             │
│          │ Token  │            │ with   │             │
│          │        │            │ token  │             │
│          │        │            │        │             │
│          │  4.    │            │  3.    │             │
│          │◀───────│            │◀───────│             │
│          │ Show   │            │ CONNACK│             │
│          │ Status │            │        │             │
└──────────┘        └────────────┘        └─────────────┘
```

__Token Format__: `tesa_mqtt_<org>_<32chars>`

The token encodes:

- Organization identifier
- Access permissions (which topics can be subscribed)

### 2. Subscription Flow

```ini
┌────────────┐        ┌─────────────┐        ┌────────────┐
│ Dashboard  │  1.    │   EMQX      │        │  Devices   │
│            │───────▶│   Broker    │        │            │
│            │SUBSCRIBE             │        │            │
│            │device/+│             │        │            │
│            │/telem..│             │        │            │
│            │        │             │        │            │
│            │  2.    │             │  3.    │            │
│            │◀───────│             │◀───────│            │
│            │ SUBACK │             │PUBLISH │            │
│            │        │             │        │            │
│            │  4.    │             │        │            │
│            │◀───────│             │        │            │
│            │PUBLISH │             │        │            │
│            │(forward)             │        │            │
└────────────┘        └─────────────┘        └────────────┘
```

**Topic Pattern**: `device/+/telemetry/#`

- `+` = Single-level wildcard (device ID)
- `#` = Multi-level wildcard (telemetry subtopics)

### 3. Message Processing

```ini
Raw MQTT Message
     │
     ▼
┌──────────────────────────────────────────────────┐
│  useMQTTStream.ts                                │
│  ┌────────────────────────────────────────────┐  │
│  │  1. Extract device ID from topic           │  │
│  │     device/{id}/telemetry/...              │  │
│  │                  ▼                         │  │
│  │  2. Parse JSON payload                     │  │
│  │     { "temperature": 25.5, ... }           │  │
│  │                  ▼                         │  │
│  │  3. Create TelemetryMessage object         │  │
│  │     { topic, deviceId, timestamp, data }   │  │
│  │                  ▼                         │  │
│  │  4. Add to message buffer                  │  │
│  │     (circular buffer, max 1000)            │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│  App.tsx - chartData transformation              │
│  ┌────────────────────────────────────────────┐  │
│  │  messages.map(msg => ({                    │  │
│  │    timestamp: msg.timestamp.toISOString(), │  │
│  │    ...msg.data (numeric values only)       │  │
│  │  }))                                       │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│  StreamChart.tsx                                 │
│  ┌────────────────────────────────────────────┐  │
│  │  Recharts LineChart                        │  │
│  │  - X-axis: timestamp                       │  │
│  │  - Y-axis (left): sensor values            │  │
│  │  - Y-axis (right): normalized (0-1)        │  │
│  │  - Lines: one per visible series           │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

## Component Architecture

### Component Hierarchy

```ini
App
├── ConnectionPanel
│   ├── Token Input
│   ├── Status Indicator
│   └── Connect/Disconnect Button
│
├── StreamChart
│   ├── ResponsiveContainer
│   ├── LineChart
│   │   ├── CartesianGrid
│   │   ├── XAxis (timestamp)
│   │   ├── YAxis (left - sensor values)
│   │   ├── YAxis (right - normalized)
│   │   ├── Tooltip (CustomTooltip)
│   │   ├── Legend
│   │   └── Line[] (one per series)
│   └── CustomTooltip
│
├── RawDataTerminal
│   ├── Terminal Header
│   └── MessageRow[]
│
└── Series Control Panel
    └── Checkbox[] (one per series)
```

### State Management

```typescript
// App.tsx - Main application state
const [token, setToken] = useState('');
const [series, setSeries] = useState<SeriesConfig[]>(DEFAULT_SERIES);
const [showRawData, setShowRawData] = useState(false);

// useMQTTStream - Connection state (internal)
const [status, setStatus] = useState<ConnectionStatus>('disconnected');
const [error, setError] = useState<string | null>(null);
const [messages, setMessages] = useState<TelemetryMessage[]>([]);
```

**State Flow**:

```ini
User Input (token) ──▶ useMQTTStream ──▶ MQTT Client
                              │
                              ▼
                      Connection Status ──▶ ConnectionPanel (display)
                              │
                              ▼
                      Messages Array ──▶ App.chartData (derived)
                                               │
                                               ▼
                                         StreamChart (render)
                                               │
                                               ▼
                                         RawDataTerminal (render)
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| UI Framework | React 18 | Component-based UI |
| Language | TypeScript 5 | Type safety |
| Build Tool | Vite 5 | Fast development, optimized builds |
| Styling | Tailwind CSS 3 | Utility-first CSS |
| Charts | Recharts 2 | React charting library |
| MQTT | mqtt.js 5 | MQTT client with WebSocket |
| HTTP Server | nginx | Production static file serving |
| Container | Docker | Consistent deployment |

## Performance Considerations

### Message Buffer Management

```typescript
// Circular buffer to prevent memory growth
const MAX_MESSAGES = 1000;

setMessages(prev => {
  const newMessages = [...prev, message];
  if (newMessages.length > MAX_MESSAGES) {
    return newMessages.slice(-MAX_MESSAGES);
  }
  return newMessages;
});
```

### Chart Optimization

```typescript
// Disable animation for real-time data
<Line isAnimationActive={false} ... />

// Limit displayed data points
const displayData = data.slice(-maxDataPoints);
```

### Memoization

```typescript
// Memoize chart data transformation
const chartData = useMemo<ChartDataPoint[]>(() => {
  return messages.map(msg => ({...}));
}, [messages]);
```

## Security

### Authentication

- Token-based authentication via MQTT username field
- Token validation happens at EMQX broker level
- No credentials stored in browser localStorage

### Transport Security

- WSS (WebSocket Secure) on port 8085
- TLS 1.2+ encryption
- Certificate validation

### Content Security

- No user input rendered as HTML
- JSON.parse wrapped in try-catch
- XSS protection headers in nginx

## Deployment Options

### 1. Static Hosting (Recommended)

```bash
npm run build
# Deploy dist/ folder to any static host:
# - GitHub Pages
# - Vercel
# - Netlify
# - AWS S3 + CloudFront
```

### 2. Docker Container

```bash
docker build -t streaming-dashboard .
docker run -p 8080:80 streaming-dashboard
```

### 3. Reverse Proxy Integration

```nginx
# Add to existing nginx config
location /dashboard/ {
    alias /path/to/dist/;
    try_files $uri $uri/ /dashboard/index.html;
}
```

## Extending the Dashboard

### Adding New Visualization Components

1. Create component in `src/components/`
2. Define props interface with TypeScript
3. Import and use in `App.tsx`

### Custom MQTT Processing

1. Extend `TelemetryMessage` type in `src/types/`
2. Modify parser in `useMQTTStream.ts`
3. Update chart data transformation in `App.tsx`

### Additional Data Sources

The architecture supports adding:

- REST API polling alongside MQTT
- Multiple MQTT broker connections
- Local device discovery via mDNS

## Future Improvements

- [ ] Historical data loading from REST API
- [ ] Multiple dashboard layouts
- [ ] Alert thresholds with notifications
- [ ] Export data to CSV/JSON
- [ ] Device grouping and filtering
- [ ] Mobile-responsive layout
