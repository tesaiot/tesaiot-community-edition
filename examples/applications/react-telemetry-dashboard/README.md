# Edge AI Telemetry Viewer

A standalone third-party application example that connects to TESAIoT Platform
and visualizes Edge AI telemetry data using Plotly charts.

## Overview

This example demonstrates how external applications can:
- Connect to a Community Edition install
- Authenticate with a JWT (CE gates reads behind one)
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
- A Community Edition install you can log in to

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Point it at your install and give it a way to sign in

Community Edition requires a JWT on read endpoints. Create `.env`:

```bash
VITE_API_BASE_URL=https://localhost      # the address install.sh printed
VITE_ADMIN_EMAIL=admin@localhost         # ADMIN_EMAIL from your .env
VITE_ADMIN_PASSWORD=...                  # ADMIN_PASSWORD from your .env
```

The app logs in with those and caches the token. If you would rather not put a
password in a file, paste a JWT into the field in the UI, or set `VITE_JWT`.

A device API key is **not** accepted here: in CE an API key authorises telemetry
*ingest* from a device, while reads are JWT-only.

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

Reads are JWT-authenticated. The client calls `POST /api/v1/auth/login` with the
configured email and password, then sends the token it gets back:

```
Authorization: Bearer <jwt>
```

Supplying `VITE_JWT` (or pasting a token into the UI) skips the login call.

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

Set these in `.env` rather than editing source:
- `VITE_API_BASE_URL` — your install's address
- `VITE_ADMIN_EMAIL` / `VITE_ADMIN_PASSWORD`, or `VITE_JWT`

`src/api/tesaiotApi.ts` reads them and falls back to a stock local install.

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

1. Check the device actually has data for the selected range — query
   `device_telemetry` in TimescaleDB if you are not sure
2. Look for errors in the browser console
3. Confirm `VITE_API_BASE_URL` points at your install, not the default

### Authentication Failed

1. `CE reads require authentication` means no credentials reached the client —
   set `VITE_ADMIN_EMAIL`/`VITE_ADMIN_PASSWORD`, or `VITE_JWT`
2. `Login failed (401)` means the credentials were rejected: they are the
   `ADMIN_EMAIL`/`ADMIN_PASSWORD` from your install's `.env`
3. A device API key will not work here — reads are JWT-only

## License

Apache License 2.0 - See [LICENSE](./LICENSE) file.

## Credits

- **Your Community Edition install**: the address `install.sh` printed (`https://localhost/` by default)
- **Thai Embedded Systems Association (TESA)**
- **Plotly.js**: https://plotly.com/javascript/
- **React**: https://react.dev/

## Support

- GitHub Issues: https://github.com/tesaiot/platform/issues
- Documentation: https://docs.tesaiot.com
- Community: https://community.tesaiot.com
