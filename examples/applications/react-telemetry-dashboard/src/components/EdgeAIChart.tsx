/**
 * Telemetry Chart Component (Community Edition)
 *
 * A recharts-based multi-series chart for visualizing IoT sensor data, with an
 * optional AI-inference overlay when ai_* fields are present in the telemetry.
 *
 * The upstream example used plotly.js, which does not bundle reliably with Vite
 * (the chart silently renders no traces in a production build). Community Edition
 * ships this recharts implementation instead — the same library the CE Admin UI
 * uses for its telemetry views.
 *
 * Licensed under Apache License 2.0
 * Copyright TESAIoT Platform contributors
 */

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { TelemetryPoint } from '../api/tesaiotApi';

interface EdgeAIChartProps {
  /** Telemetry data points */
  data: TelemetryPoint[];
  /** Title for the chart */
  title?: string;
  /** Height of the chart in pixels */
  height?: number;
  /** Kept for API compatibility with the upstream example (zoom callbacks). */
  onRangeChange?: (range: { start: Date; end: Date } | null) => void;
}

// Color palette for sensor series
const SENSOR_COLORS = [
  '#3b82f6', // blue
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
];

// AI inference color
const AI_COLOR = '#ef4444'; // red

/** Format an ISO timestamp as a short time label for the X axis. */
function timeLabel(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export const EdgeAIChart: React.FC<EdgeAIChartProps> = ({
  data,
  title = 'Telemetry',
  height = 500,
}) => {
  // Detect available sensor keys from data (numeric, non-AI fields)
  const sensorKeys = useMemo(() => {
    if (!data || data.length === 0) return [];
    const keys = new Set<string>();
    data.forEach((point) => {
      Object.keys(point).forEach((key) => {
        if (
          typeof point[key] === 'number' &&
          !key.startsWith('ai_') &&
          !['timestamp', 'time'].includes(key)
        ) {
          keys.add(key);
        }
      });
    });
    return Array.from(keys);
  }, [data]);

  // AI overlay only when the platform provides ai_* fields (CE excludes the AI
  // module, so this stays false and the overlay is simply absent).
  const hasAIData = useMemo(
    () =>
      data.some(
        (point) =>
          point.ai_confidence !== undefined ||
          point.ai_anomalyScore !== undefined ||
          point.ai_prediction !== undefined
      ),
    [data]
  );

  // Sensors with a much larger magnitude (e.g. pressure ~1000 hPa next to
  // temperature ~25 °C) get their own right-hand axis so the small series
  // remain readable.
  const rightAxisKeys = useMemo(() => {
    if (sensorKeys.length < 2) return new Set<string>();
    const maxAbs: Record<string, number> = {};
    sensorKeys.forEach((key) => {
      maxAbs[key] = data.reduce((m, p) => Math.max(m, Math.abs((p[key] as number) || 0)), 0);
    });
    const smallest = Math.min(...Object.values(maxAbs).filter((v) => v > 0));
    return new Set(sensorKeys.filter((key) => maxAbs[key] > 20 * smallest));
  }, [data, sensorKeys]);
  const hasRightAxis = rightAxisKeys.size > 0;

  // recharts consumes an array of flat objects; add a display label and scale
  // ai_confidence to a 0-100 axis.
  const chartData = useMemo(
    () =>
      data.map((point) => ({
        ...point,
        _label: timeLabel(point.time || point.timestamp),
        ...(point.ai_confidence !== undefined
          ? { ai_confidence_pct: point.ai_confidence * 100 }
          : {}),
      })),
    [data]
  );

  // No data state
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f5f5f5',
          borderRadius: 8,
          color: '#666',
        }}
      >
        No telemetry data available. Select a device and date range.
      </div>
    );
  }

  return (
    <div className="edge-ai-chart">
      <div style={{ textAlign: 'center', fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
        {title}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 10, right: hasAIData || hasRightAxis ? 10 : 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="_label" tick={{ fontSize: 12 }} minTickGap={40} />
          <YAxis yAxisId="left" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
          {hasRightAxis && (
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
          )}
          {hasAIData && !hasRightAxis && (
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              unit="%"
              tick={{ fontSize: 12 }}
            />
          )}
          <Tooltip />
          <Legend />
          {sensorKeys.map((key, index) => (
            <Line
              key={key}
              yAxisId={rightAxisKeys.has(key) ? 'right' : 'left'}
              type="monotone"
              dataKey={key}
              name={key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
              stroke={SENSOR_COLORS[index % SENSOR_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 2 }}
              isAnimationActive={false}
            />
          ))}
          {hasAIData && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="ai_confidence_pct"
              name="AI Confidence"
              stroke={AI_COLOR}
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      <div style={{ textAlign: 'center', fontSize: 12, color: '#666', marginTop: 8 }}>
        {data.length} data points • {sensorKeys.length} sensors
        {hasAIData && ' • AI inference enabled'}
      </div>
    </div>
  );
};

export default EdgeAIChart;
