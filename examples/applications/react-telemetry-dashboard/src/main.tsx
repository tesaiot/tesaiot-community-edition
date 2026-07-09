/**
 * Edge AI Telemetry Viewer - Main Entry Point
 *
 * A standalone third-party application example that connects to
 * TESAIoT Platform via API Gateway using API Key authentication.
 *
 * Licensed under Apache License 2.0
 * Copyright (c) 2024-2025 TESAIoT Platform
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
