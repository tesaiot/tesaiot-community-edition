# Edge AI Telemetry Viewer

A standalone third-party application example that connects to TESAIoT Platform
and visualizes Edge AI telemetry data using Plotly charts.

## Overview

This example demonstrates how external applications can:
- Connect to TESAIoT Platform via API Gateway
- Authenticate using API Keys
- Fetch telemetry data from BDH AI API
- Visualize sensor data with AI inference overlay

## Features

- **Multi-axis Chart**: Sensor values on left Y-axis, AI scores on right Y-axis
- **AI Inference Overlay**: Confidence scores, anomaly detection markers
- **Zoom/Pan**: Interactive zoom with range slider
- **Time Range Selector**: Quick buttons (1h, 6h, 1d, 7d, All)
- **Responsive Design**: Works on desktop and mobile

## Prerequisites

- Node.js 18+ and npm
- TESAIoT Platform account with API Key

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure API Key

Edit `src/api/tesaiotApi.ts` and replace the API key:

```typescript
const API_CONFIG = {
  baseUrl: 'https://admin.tesaiot.com',
  apiKey: 'YOUR_API_KEY_HERE', // Get from TESAIoT Platform > API Keys
};
```

Or configure at runtime:

```typescript
import { configureApi } from './api/tesaiotApi';

configureApi({ apiKey: 'YOUR_API_KEY_HERE' });
```

### 3. Run Development Server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

### 4. Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## API Endpoints Used

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/devices` | List available devices |
| `GET /api/v1/telemetry/{device_id}/query` | Fetch historical telemetry data |
| `GET /api/v1/telemetry/{device_id}/latest` | Fetch latest telemetry (includes AI results) |

Note: AI inference results are embedded in telemetry data as `ai_*` fields (ai_confidence, ai_prediction, ai_anomalyScore).

## Authentication

All API requests use API Key authentication via the `X-API-Key` header:

```
X-API-Key: tesa_ak_YOUR_API_KEY_HERE
```

## Project Structure

```
edgeAI-to-third_party_App/
├── index.html              # HTML entry point
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite build configuration
├── LICENSE                 # Apache 2.0 License
├── README.md               # This file
└── src/
    ├── main.tsx            # React entry point
    ├── App.tsx             # Main application component
    ├── api/
    │   └── tesaiotApi.ts   # TESAIoT API client
    └── components/
        └── EdgeAIChart.tsx # Plotly chart component
```

## Customization

### Adding New Sensors

The chart automatically detects available sensor keys from the telemetry data.
No configuration needed for new sensor types.

### Styling

Modify the `styles` object in `App.tsx` or add CSS files as needed.

### API Configuration

Update `src/api/tesaiotApi.ts` to change:
- Base URL
- Default API Key
- Request headers

## Deployment

This app can be deployed to any static hosting service:

- **Vercel**: `vercel deploy`
- **Netlify**: Drag & drop the `dist/` folder
- **GitHub Pages**: Use GitHub Actions
- **Docker**: Build and serve with nginx

Example Dockerfile:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### CORS Errors

If running locally and getting CORS errors:
1. Use the Vite proxy (configured in `vite.config.ts`)
2. Or deploy to same domain as TESAIoT Platform
3. Or configure CORS on the API Gateway

### No Data Displayed

1. Verify API Key is valid
2. Check device has data for selected date range
3. Look for errors in browser console

### Authentication Failed

1. Verify API Key format: `tesa_ak_...`
2. Check API Key permissions in TESAIoT Platform
3. Ensure API Key is active (not revoked)

## License

Apache License 2.0 - See [LICENSE](./LICENSE) file.

## Credits

- **TESAIoT Platform**: https://admin.tesaiot.com
- **Thai Embedded Systems Association (TESA)**
- **Plotly.js**: https://plotly.com/javascript/
- **React**: https://react.dev/

## Support

- GitHub Issues: https://github.com/tesaiot/platform/issues
- Documentation: https://docs.tesaiot.com
- Community: https://community.tesaiot.com
