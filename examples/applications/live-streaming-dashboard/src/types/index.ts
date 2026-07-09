/**
 * Type Definitions for TESAIoT Live Streaming Dashboard
 *
 * Central location for all TypeScript interfaces and types.
 */

/**
 * Telemetry message received from MQTT
 */
export interface TelemetryMessage {
  deviceId: string;
  sensorType: string;
  data: Record<string, number | string | boolean>;
  timestamp: Date;
  topic?: string;
  raw?: string;
}

/**
 * Chart data point for Recharts
 */
export interface ChartDataPoint {
  timestamp: string;
  [key: string]: number | string;
}

/**
 * Series configuration for multi-axis chart
 */
export interface SeriesConfig {
  key: string;
  name: string;
  color: string;
  yAxisId: 'left' | 'right';
  visible: boolean;
  unit?: string;
}

/**
 * MQTT connection configuration
 */
export interface MQTTConfig {
  brokerUrl: string;
  token: string;
  topic: string;
  clientId?: string;
}

/**
 * MQTT connection state
 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Dashboard settings
 */
export interface DashboardSettings {
  maxDataPoints: number;
  refreshInterval: number;
  autoScroll: boolean;
  showRawData: boolean;
}

/**
 * Device information
 */
export interface Device {
  id: string;
  name: string;
  status: 'online' | 'offline';
  lastSeen?: Date;
}
