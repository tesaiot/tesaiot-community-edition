/**
 * Edge AI Telemetry Chart Component
 *
 * A Plotly-based multi-axis chart for visualizing IoT sensor data
 * with AI inference overlay (confidence, anomaly detection).
 *
 * Based on TESAIoT Platform's Edge AI Telemetry Dashboard.
 *
 * Licensed under Apache License 2.0
 * Copyright (c) 2024-2025 TESAIoT Platform
 */

import React, { useMemo, useCallback, useState, useRef } from 'react';
import Plot from 'react-plotly.js';
import type { TelemetryPoint } from '../api/tesaiotApi';

interface EdgeAIChartProps {
  /** Telemetry data points */
  data: TelemetryPoint[];
  /** Title for the chart */
  title?: string;
  /** Height of the chart in pixels */
  height?: number;
  /** Callback when zoom/pan changes */
  onRangeChange?: (range: { start: Date; end: Date } | null) => void;
}

// Color palette for sensor data
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

/**
 * Edge AI Telemetry Chart
 *
 * Features:
 * - Multi-axis chart (sensor values on left, AI scores on right)
 * - Zoom/pan with range slider
 * - Time range selector buttons (1h, 6h, 1d, 7d, All)
 * - AI prediction markers (anomaly, warning)
 * - Preserves zoom state when data updates
 */
export const EdgeAIChart: React.FC<EdgeAIChartProps> = ({
  data,
  title = 'Edge AI Telemetry',
  height = 500,
  onRangeChange,
}) => {
  const plotRef = useRef<any>(null);
  const [xAxisRange, setXAxisRange] = useState<[string, string] | null>(null);

  // Detect available sensor keys from data
  const sensorKeys = useMemo(() => {
    if (!data || data.length === 0) return [];

    const keys = new Set<string>();
    data.forEach(point => {
      Object.keys(point).forEach(key => {
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

  // Check if AI data is available
  const hasAIData = useMemo(() => {
    return data.some(point =>
      point.ai_confidence !== undefined ||
      point.ai_anomalyScore !== undefined ||
      point.ai_prediction !== undefined
    );
  }, [data]);

  // Build Plotly traces
  const traces = useMemo(() => {
    if (!data || data.length === 0) return [];

    const plotTraces: Plotly.Data[] = [];

    // Add sensor data traces
    sensorKeys.forEach((key, index) => {
      const values = data.map(point => point[key] as number);
      const times = data.map(point => point.time || point.timestamp);

      plotTraces.push({
        type: 'scatter',
        mode: 'lines',
        name: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
        x: times,
        y: values,
        yaxis: 'y',
        line: {
          color: SENSOR_COLORS[index % SENSOR_COLORS.length],
          width: 2,
        },
        hovertemplate: `<b>${key}</b><br>%{x}<br>Value: %{y:.2f}<extra></extra>`,
      });
    });

    // Add AI confidence trace (if available)
    if (hasAIData) {
      const aiConfidence = data.map(point =>
        point.ai_confidence !== undefined ? point.ai_confidence * 100 : null
      );
      const times = data.map(point => point.time || point.timestamp);

      plotTraces.push({
        type: 'scatter',
        mode: 'lines',
        name: 'AI Confidence',
        x: times,
        y: aiConfidence,
        yaxis: 'y2',
        line: {
          color: AI_COLOR,
          width: 2,
          dash: 'dot',
        },
        hovertemplate: '<b>AI Confidence</b><br>%{x}<br>%{y:.1f}%<extra></extra>',
      });

      // Add AI prediction markers (anomaly/warning)
      const anomalyPoints = data.filter(point =>
        point.ai_prediction === 'anomaly' || point.ai_prediction === 'warning'
      );

      if (anomalyPoints.length > 0) {
        plotTraces.push({
          type: 'scatter',
          mode: 'markers',
          name: 'AI Alerts',
          x: anomalyPoints.map(p => p.time || p.timestamp),
          y: anomalyPoints.map(p => (p.ai_confidence || 0.5) * 100),
          yaxis: 'y2',
          marker: {
            symbol: anomalyPoints.map(p =>
              p.ai_prediction === 'anomaly' ? 'triangle-down' : 'diamond'
            ),
            size: 12,
            color: anomalyPoints.map(p =>
              p.ai_prediction === 'anomaly' ? '#ef4444' : '#f59e0b'
            ),
          },
          hovertemplate: anomalyPoints.map(p =>
            `<b>${p.ai_prediction?.toUpperCase()}</b><br>` +
            `%{x}<br>` +
            `Confidence: %{y:.1f}%<extra></extra>`
          ),
        });
      }
    }

    return plotTraces;
  }, [data, sensorKeys, hasAIData]);

  // Layout configuration
  const layout = useMemo((): Partial<Plotly.Layout> => ({
    // Preserve zoom state when data changes
    uirevision: 'preserve-zoom',
    height,
    title: {
      text: title,
      font: { size: 16 },
    },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.25,
      x: 0.5,
      xanchor: 'center',
    },
    xaxis: {
      title: { text: 'Time' },
      type: 'date',
      showgrid: true,
      gridcolor: '#e5e7eb',
      zeroline: false,
      rangeslider: { visible: true },
      rangeselector: {
        buttons: [
          { count: 1, label: '1h', step: 'hour', stepmode: 'backward' },
          { count: 6, label: '6h', step: 'hour', stepmode: 'backward' },
          { count: 1, label: '1d', step: 'day', stepmode: 'backward' },
          { count: 7, label: '7d', step: 'day', stepmode: 'backward' },
          { step: 'all', label: 'All' },
        ],
      },
      ...(xAxisRange ? { range: xAxisRange, autorange: false } : {}),
    },
    yaxis: {
      title: { text: 'Sensor Values' },
      showgrid: true,
      gridcolor: '#e5e7eb',
      zeroline: false,
    },
    yaxis2: hasAIData ? {
      title: { text: 'AI Score (%)' },
      side: 'right',
      overlaying: 'y',
      showgrid: false,
      zeroline: false,
      range: [0, 100],
      ticksuffix: '%',
    } : undefined,
    hovermode: 'closest',
    dragmode: 'zoom',
    margin: { l: 60, r: hasAIData ? 80 : 60, t: 50, b: 100 },
  }), [title, height, hasAIData, xAxisRange]);

  // Config (no Plotly logo)
  const config = useMemo((): Partial<Plotly.Config> => ({
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    toImageButtonOptions: {
      format: 'png',
      filename: `edge_ai_telemetry_${new Date().toISOString().slice(0, 10)}`,
      height: 600,
      width: 1200,
      scale: 2,
    },
  }), []);

  // Handle zoom/pan events
  const handleRelayout = useCallback((event: any) => {
    // Direct zoom (drag/scroll)
    if (event['xaxis.range[0]'] && event['xaxis.range[1]']) {
      const rangeStart = event['xaxis.range[0]'];
      const rangeEnd = event['xaxis.range[1]'];
      setXAxisRange([rangeStart, rangeEnd]);

      if (onRangeChange) {
        onRangeChange({ start: new Date(rangeStart), end: new Date(rangeEnd) });
      }
    }

    // Rangeselector button click
    if (Array.isArray(event['xaxis.range'])) {
      const [rangeStart, rangeEnd] = event['xaxis.range'];
      setXAxisRange([rangeStart, rangeEnd]);

      if (onRangeChange) {
        onRangeChange({ start: new Date(rangeStart), end: new Date(rangeEnd) });
      }
    }

    // Reset zoom
    if (event['xaxis.autorange'] === true) {
      setXAxisRange(null);
      if (onRangeChange) {
        onRangeChange(null);
      }
    }
  }, [onRangeChange]);

  // No data state
  if (!data || data.length === 0) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        color: '#666',
      }}>
        No telemetry data available. Select a device and date range.
      </div>
    );
  }

  return (
    <div className="edge-ai-chart">
      <Plot
        ref={plotRef}
        data={traces}
        layout={layout}
        config={config}
        onRelayout={handleRelayout}
        style={{ width: '100%' }}
      />
      <div style={{
        textAlign: 'center',
        fontSize: 12,
        color: '#666',
        marginTop: 8,
      }}>
        {data.length} data points • {sensorKeys.length} sensors
        {hasAIData && ' • AI inference enabled'}
      </div>
    </div>
  );
};

export default EdgeAIChart;
