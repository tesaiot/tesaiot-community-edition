/**
 * TESAIoT Live Streaming Dashboard
 *
 * Real-time telemetry visualization dashboard with MQTT WebSocket connection.
 *
 * Features:
 * - Live data streaming via WSS MQTT
 * - Multi-series chart with dual Y-axis
 * - Series visibility toggle
 * - Raw data terminal view
 * - Connection status indicator
 */

import { useState, useMemo } from 'react';
import { useMQTTStream } from './hooks/useMQTTStream';
import { StreamChart } from './components/Charts/StreamChart';
import { ConnectionPanel } from './components/MQTT/ConnectionPanel';
import { RawDataTerminal } from './components/Dashboard/RawDataTerminal';
import type { SeriesConfig, ChartDataPoint } from './types';

// Default series configuration
const DEFAULT_SERIES: SeriesConfig[] = [
  { key: 'temperature', name: 'Temperature (°C)', color: '#ef4444', yAxisId: 'left', visible: true, unit: '°C' },
  { key: 'humidity', name: 'Humidity (%)', color: '#3b82f6', yAxisId: 'left', visible: true, unit: '%' },
  { key: 'pressure', name: 'Pressure (hPa)', color: '#10b981', yAxisId: 'left', visible: false, unit: 'hPa' },
  // ai_* series stay hidden by default — Community Edition excludes the AI module,
  // so stock CE telemetry never carries these fields.
  { key: 'confidence', name: 'AI Confidence', color: '#22c55e', yAxisId: 'right', visible: false },
  { key: 'anomalyScore', name: 'Anomaly Score', color: '#f97316', yAxisId: 'right', visible: false },
];

function App() {
  // Community Edition: per-device MQTT credentials (username = device id).
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  // Optional topic override — a service account may watch the fleet (device/+/telemetry).
  const [topic, setTopic] = useState('');
  const [series, setSeries] = useState<SeriesConfig[]>(DEFAULT_SERIES);
  const [showRawData, setShowRawData] = useState(false);

  const { status, error, messages, messageCount, connect, disconnect, clearMessages } = useMQTTStream({
    username,
    password,
    topic: topic || undefined,
    maxMessages: 500,
  });

  // Transform messages to chart data
  const chartData = useMemo<ChartDataPoint[]>(() => {
    return messages.map((msg) => ({
      timestamp: msg.timestamp.toISOString(),
      ...Object.fromEntries(
        Object.entries(msg.data).filter(([_, v]) => typeof v === 'number')
      ),
    }));
  }, [messages]);

  // Toggle series visibility
  const toggleSeries = (key: string) => {
    setSeries((prev) =>
      prev.map((s) => (s.key === key ? { ...s, visible: !s.visible } : s))
    );
  };

  // Handle connect button
  const handleConnect = () => {
    if (status === 'connected') {
      disconnect();
    } else {
      connect();
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">TESAIoT Live Streaming Dashboard</h1>
            <p className="text-gray-400 text-sm">Real-time MQTT telemetry visualization</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">
              Messages: {messageCount}
            </span>
            <button
              onClick={clearMessages}
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded"
            >
              Clear
            </button>
          </div>
        </div>
      </header>

      <main className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Chart Area */}
          <div className="lg:col-span-3 space-y-6">
            {/* Connection Panel */}
            <ConnectionPanel
              username={username}
              password={password}
              onUsernameChange={setUsername}
              onPasswordChange={setPassword}
              topic={topic}
              onTopicChange={setTopic}
              status={status}
              error={error?.message ?? null}
              onConnect={handleConnect}
            />

            {/* Chart */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-4">Live Telemetry</h2>
              {chartData.length > 0 ? (
                <StreamChart data={chartData} series={series} height={400} />
              ) : (
                <div className="h-[400px] flex items-center justify-center text-gray-500">
                  {status === 'connected'
                    ? 'Waiting for data...'
                    : 'Connect to start receiving data'}
                </div>
              )}
            </div>

            {/* Raw Data Terminal */}
            {showRawData && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h2 className="text-lg font-semibold mb-4">Raw Data Stream</h2>
                <RawDataTerminal messages={messages.slice(-50)} />
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Series Control */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4">Series Control</h3>
              <div className="space-y-2">
                {series.map((s) => (
                  <label
                    key={s.key}
                    className="flex items-center gap-3 cursor-pointer hover:bg-gray-700 p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={s.visible}
                      onChange={() => toggleSeries(s.key)}
                      className="w-4 h-4"
                    />
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: s.color }}
                    />
                    <span className="text-sm">{s.name}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Display Options */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4">Display Options</h3>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showRawData}
                  onChange={(e) => setShowRawData(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">Show Raw Data</span>
              </label>
            </div>

            {/* Connection Info */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4">Connection Info</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-400">Broker:</dt>
                  <dd>localhost</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-400">Port:</dt>
                  <dd>8083 (WS)</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-400">Protocol:</dt>
                  <dd>MQTT over WebSocket</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 px-6 py-4 mt-6">
        <p className="text-center text-gray-400 text-sm">
          Built with{' '}
          <a
            href="https://github.com/tesaiot/developer-hub"
            className="text-blue-400 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            TESAIoT Developer Hub
          </a>
          {' '}| Apache 2.0 License
        </p>
      </footer>
    </div>
  );
}

export default App;
