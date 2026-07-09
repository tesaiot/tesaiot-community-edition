/**
 * StreamChart Component
 *
 * Real-time streaming chart with dual Y-axis support for telemetry visualization.
 * Uses Recharts library for rendering responsive line charts with configurable series.
 *
 * Features:
 * - Dual Y-axis (left/right) for different value ranges
 * - Configurable series visibility
 * - Auto-scrolling time axis
 * - Responsive container
 * - Tooltip with formatted values
 *
 * @example
 * ```tsx
 * <StreamChart
 *   data={chartData}
 *   series={[
 *     { key: 'temperature', name: 'Temperature', color: '#ef4444', yAxisId: 'left', visible: true },
 *     { key: 'humidity', name: 'Humidity', color: '#3b82f6', yAxisId: 'left', visible: true },
 *   ]}
 *   height={400}
 * />
 * ```
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { ChartDataPoint, SeriesConfig } from '../../types';

interface StreamChartProps {
  /** Array of data points with timestamp and metric values */
  data: ChartDataPoint[];
  /** Series configuration for each metric line */
  series: SeriesConfig[];
  /** Chart height in pixels */
  height?: number;
  /** Maximum number of data points to display (auto-scroll) */
  maxDataPoints?: number;
}

/**
 * Format timestamp for X-axis display
 * Shows HH:MM:SS format for readability
 */
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

/**
 * Custom tooltip component for chart hover
 * Displays timestamp and all visible series values
 */
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string; unit?: string }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
      <p className="text-gray-400 text-xs mb-2">{label && formatTime(label)}</p>
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-300">{entry.name}:</span>
            <span className="text-white font-medium">
              {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
              {entry.unit && <span className="text-gray-400 ml-1">{entry.unit}</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StreamChart({
  data,
  series,
  height = 400,
  maxDataPoints = 100,
}: StreamChartProps) {
  // Filter to only visible series
  const visibleSeries = series.filter((s) => s.visible);

  // Slice data to show only the most recent points (auto-scroll effect)
  const displayData = data.slice(-maxDataPoints);

  // Check if we have data for any visible series
  const hasData = displayData.length > 0 && visibleSeries.length > 0;

  if (!hasData) {
    return (
      <div
        className="flex items-center justify-center text-gray-500"
        style={{ height }}
      >
        No data to display. Enable series from the control panel.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={displayData}
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        {/* Grid for readability */}
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />

        {/* X-axis with formatted timestamps */}
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTime}
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          interval="preserveStartEnd"
        />

        {/* Left Y-axis for primary metrics (temperature, humidity, pressure) */}
        <YAxis
          yAxisId="left"
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          domain={['auto', 'auto']}
        />

        {/* Right Y-axis for normalized metrics (confidence, anomaly score 0-1) */}
        <YAxis
          yAxisId="right"
          orientation="right"
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          domain={[0, 1]}
        />

        {/* Interactive tooltip */}
        <Tooltip content={<CustomTooltip />} />

        {/* Legend showing series names */}
        <Legend
          wrapperStyle={{ paddingTop: 20 }}
          formatter={(value) => <span className="text-gray-300">{value}</span>}
        />

        {/* Render a line for each visible series */}
        {visibleSeries.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            yAxisId={s.yAxisId}
            dot={false}
            strokeWidth={2}
            connectNulls
            isAnimationActive={false} // Disable animation for real-time performance
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export default StreamChart;
