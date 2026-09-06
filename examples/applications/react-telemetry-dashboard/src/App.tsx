/**
 * Edge AI Telemetry Viewer - Main Application
 *
 * A standalone third-party application that demonstrates how to
 * connect to TESAIoT Platform and visualize Edge AI telemetry data.
 *
 * Licensed under Apache License 2.0
 * Copyright (c) 2024-2025 TESAIoT Platform
 */

import React, { useState, useEffect, useCallback } from 'react';
import { EdgeAIChart } from './components/EdgeAIChart';
import {
  fetchTelemetryData,
  fetchDevices,
  configureApi,
  type TelemetryPoint,
  type DeviceInfo,
} from './api/tesaiotApi';

// Styles
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    maxWidth: 1400,
    margin: '0 auto',
    padding: 20,
  },
  header: {
    backgroundColor: '#1e293b',
    color: 'white',
    padding: '20px 0',
    marginBottom: 24,
  },
  headerContent: {
    maxWidth: 1400,
    margin: '0 auto',
    padding: '0 20px',
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    opacity: 0.8,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
    padding: 20,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: '1px solid #e5e7eb',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 16,
    marginBottom: 16,
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: 500,
    color: '#374151',
  },
  input: {
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
  },
  select: {
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
    backgroundColor: 'white',
  },
  button: {
    padding: '10px 20px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: 6,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
  },
  buttonDisabled: {
    backgroundColor: '#9ca3af',
    cursor: 'not-allowed',
  },
  error: {
    padding: 12,
    backgroundColor: '#fef2f2',
    color: '#dc2626',
    borderRadius: 6,
    marginBottom: 16,
    fontSize: 14,
  },
  info: {
    padding: 12,
    backgroundColor: '#f0f9ff',
    color: '#0369a1',
    borderRadius: 6,
    marginBottom: 16,
    fontSize: 14,
  },
  footer: {
    textAlign: 'center' as const,
    padding: 20,
    color: '#6b7280',
    fontSize: 12,
  },
};

function App() {
  // State
  // Community Edition gates reads behind a JWT, not an API key: the API key is
  // a device credential for telemetry INGEST and is not accepted on reads.
  const [jwt, setJwt] = useState('');
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [telemetryData, setTelemetryData] = useState<TelemetryPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update API config when the token changes
  useEffect(() => {
    if (jwt) {
      configureApi({ token: jwt });
    }
  }, [jwt]);

  // Fetch devices on mount
  useEffect(() => {
    async function loadDevices() {
      try {
        setError(null);
        const deviceList = await fetchDevices();
        setDevices(deviceList);

        // Auto-select first device if available
        if (deviceList.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(deviceList[0].device_id);
        }
      } catch (err) {
        setError(`Failed to load devices: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }

    loadDevices();
  }, []);

  // Fetch telemetry data
  const handleFetchData = useCallback(async () => {
    if (!selectedDeviceId) {
      setError('Please select a device');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchTelemetryData(selectedDeviceId, startDate, endDate);
      setTelemetryData(data);

      if (data.length === 0) {
        setError('No data found for the selected date range');
      }
    } catch (err) {
      setError(`Failed to fetch data: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setTelemetryData([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedDeviceId, startDate, endDate]);

  // Quick date range buttons
  const setQuickRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  };

  return (
    <div>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.title}>Edge AI Telemetry Viewer</h1>
          <p style={styles.subtitle}>
            Third Party Application Example - Powered by TESAIoT Platform
          </p>
        </div>
      </header>

      <div style={styles.container}>
        {/* Configuration Card */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Configuration</h2>

          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={styles.label}>JWT (optional)</label>
              <input
                type="password"
                style={styles.input}
                value={jwt}
                onChange={(e) => setJwt(e.target.value)}
                placeholder="paste a token, or set VITE_ADMIN_EMAIL/PASSWORD"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Device</label>
              <select
                style={styles.select}
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
              >
                <option value="">Select a device...</option>
                {devices.map((device) => (
                  <option key={device.device_id} value={device.device_id}>
                    {device.name} ({device.device_type || 'Device'})
                  </option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Start Date</label>
              <input
                type="date"
                style={styles.input}
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>End Date</label>
              <input
                type="date"
                style={styles.input}
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            <button
              style={{ ...styles.button, backgroundColor: '#6b7280', padding: '6px 12px' }}
              onClick={() => setQuickRange(1)}
            >
              1D
            </button>
            <button
              style={{ ...styles.button, backgroundColor: '#6b7280', padding: '6px 12px' }}
              onClick={() => setQuickRange(7)}
            >
              7D
            </button>
            <button
              style={{ ...styles.button, backgroundColor: '#6b7280', padding: '6px 12px' }}
              onClick={() => setQuickRange(30)}
            >
              30D
            </button>
          </div>

          <button
            style={{
              ...styles.button,
              ...(isLoading || !selectedDeviceId ? styles.buttonDisabled : {}),
            }}
            onClick={handleFetchData}
            disabled={isLoading || !selectedDeviceId}
          >
            {isLoading ? 'Loading...' : 'Load Telemetry Data'}
          </button>
        </div>

        {/* Error/Info Messages */}
        {error && <div style={styles.error}>{error}</div>}

        {/* Chart Card */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Telemetry Chart</h2>
          <EdgeAIChart
            data={telemetryData}
            title={devices.find(d => d.device_id === selectedDeviceId)?.name || 'Edge AI Telemetry'}
            height={500}
            onRangeChange={(range) => {
              if (range) {
                console.log('Zoom range:', range.start, 'to', range.end);
              } else {
                console.log('Zoom reset');
              }
            }}
          />
        </div>

        {/* Info Card */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>About This Example</h2>
          <div style={styles.info}>
            <p><strong>This is a standalone third-party application example.</strong></p>
            <p style={{ marginTop: 8 }}>
              It demonstrates how to read from a Community Edition install with a JWT
              and visualize telemetry data with recharts.
            </p>
            <p style={{ marginTop: 8 }}>
              <strong>Features:</strong> Multi-axis chart, AI inference overlay, zoom/pan,
              time range selector, anomaly markers.
            </p>
            <p style={{ marginTop: 8 }}>
              <strong>Signing in:</strong> set VITE_ADMIN_EMAIL and VITE_ADMIN_PASSWORD and the
              app logs in for you, or paste a JWT above.
            </p>
          </div>
        </div>

        {/* Footer */}
        <footer style={styles.footer}>
          <p>
            Edge AI Telemetry Viewer - Open Source (Apache 2.0 License)
          </p>
          <p style={{ marginTop: 4 }}>
            Powered by TESAIoT Platform | Thai Embedded Systems Association (TESA)
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
