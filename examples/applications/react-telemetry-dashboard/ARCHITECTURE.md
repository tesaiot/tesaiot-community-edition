# React Dashboard Architecture

## Overview

React-based Edge AI dashboard for visualizing IoT telemetry with Plotly charts.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Application                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      App.tsx                             │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│         ┌──────────────────┼───────────────────┐                │
│         │                   │                  │                │
│         ▼                   ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐      │
│  │ components/ │    │   api/      │    │   hooks/        │      │
│  │ - Header    │    │ - client.ts │    │ - useTelemetry  │      │
│  │ - Sidebar   │    │ - devices   │    │ - useDevices    │      │
│  │ - Charts    │    │ - telemetry │    │                 │      │
│  └─────────────┘    └──────┬──────┘    └─────────────────┘      │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             │  HTTPS (REST API)
                             │  Port 443
                             ▼
                  ┌──────────────────────┐
                  │   TESAIoT Platform   │
                  │  ┌────────────────┐  │
                  │  │   REST API     │  │
                  │  └────────────────┘  │
                  └──────────────────────┘
```

## Directory Structure

```
react-dashboard/
├── src/
│   ├── App.tsx                 # Main application
│   ├── components/
│   │   ├── Header.tsx          # Navigation header
│   │   ├── Sidebar.tsx         # Device list
│   │   ├── TimeSeriesChart.tsx # Plotly chart
│   │   └── GaugeChart.tsx      # Gauge visualization
│   └── api/
│       ├── client.ts           # API client setup
│       └── devices.ts          # Device API calls
├── package.json
└── vite.config.ts
```

## Component Hierarchy

```
App
├── Header
│   ├── Logo
│   └── Navigation
├── Sidebar
│   ├── DeviceList
│   └── DeviceFilter
└── MainContent
    ├── DashboardGrid
    │   ├── TimeSeriesChart (x2)
    │   ├── GaugeChart (x2)
    │   └── DataTable
    └── AlertPanel
```

## Data Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  REST API    │───▶│  API Client  │───▶│  React Hook  │
│  /devices    │    │  (axios)     │    │ (useSWR)     │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │  Component State     │
                                    │  (devices, loading)  │
                                    └──────────┬───────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────┐
               │                               │                           │
               ▼                               ▼                           ▼
       ┌─────────────┐                ┌─────────────┐             ┌─────────────┐
       │ DeviceList  │                │ Charts      │             │ DataTable   │
       └─────────────┘                └─────────────┘             └─────────────┘
```

## API Client

```typescript
// api/client.ts
import axios from 'axios';

const client = axios.create({
  baseURL: 'https://admin.tesaiot.com/api/v1',
  headers: {
    'X-API-Key': process.env.VITE_API_KEY,
  },
});

export default client;
```

## Key Components

| Component | Purpose | Props |
|-----------|---------|-------|
| Header | Navigation and branding | logo, nav links |
| Sidebar | Device selection | devices, onSelect |
| TimeSeriesChart | Plotly line chart | data, title |
| GaugeChart | Plotly gauge | value, min, max |

## Hooks

```typescript
// hooks/useDevices.ts
const useDevices = () => {
  const { data, error, isLoading } = useSWR(
    '/devices',
    () => client.get('/devices').then(res => res.data)
  );

  return { devices: data, error, isLoading };
};
```

## Dependencies

- react - UI framework
- react-router-dom - Routing
- plotly.js - Charting
- react-plotly.js - React wrapper
- axios - HTTP client
- swr - Data fetching

## Running

```bash
# Install
npm install

# Development
npm run dev

# Build
npm run build
```

## Environment Variables

```bash
# .env
VITE_API_URL=https://admin.tesaiot.com/api/v1
VITE_API_KEY=your_api_key
```
