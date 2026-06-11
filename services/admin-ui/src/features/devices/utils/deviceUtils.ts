/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import authFetch from '@/utils/auth-fetch';
import { DEVICE_API_ENDPOINTS, DEVICE_STATUS_COLORS } from '../constants/device.constants';
import { Terminal, Zap, Router, Cpu, Server } from 'lucide-react';

/**
 * Create a function to fetch real telemetry data from API
 */
export function createFetchRealTelemetryData(setRealTelemetryData: any, setTelemetryLoading: any) {
  return async (deviceId: string) => {
    try {
      setTelemetryLoading(true);
      const response = await authFetch(DEVICE_API_ENDPOINTS.TELEMETRY(deviceId));
      if (response.ok) {
        const data = await response.json();
        const formattedData = data.telemetry?.map((t: any) => {
          const timestamp = new Date(t.timestamp);
          const sensorData = t.data || {};
          return {
            time: timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            timestamp: timestamp.getTime(),
            temperature: sensorData.sensors?.temperature || sensorData.temperature,
            humidity: sensorData.sensors?.humidity || sensorData.humidity,
            pressure: sensorData.sensors?.pressure || sensorData.pressure,
            cpu: sensorData.system?.cpu_usage || sensorData.cpu,
            memory: sensorData.system?.memory_usage || sensorData.memory,
            battery: sensorData.system?.battery_level || sensorData.battery,
            signalStrength: sensorData.system?.signal_strength || sensorData.signal_strength,
            // Support flexible sensor types from virtual devices
            ...Object.keys(sensorData.sensors || {}).reduce((acc, key) => {
              acc[key] = sensorData.sensors[key];
              return acc;
            }, {} as any)
          };
        }).reverse() || []; // Reverse to show latest first
        
        setRealTelemetryData(formattedData);
        return formattedData;
      }
    } catch (error) {
      console.error('Failed to fetch telemetry data:', error);
    } finally {
      setTelemetryLoading(false);
    }
    return [];
  };
}

/**
 * Generate fallback mock data for demo purposes (when no real data available)
 */
export function generateFallbackData() {
  const data = [];
  const now = new Date();
  for (let i = 30; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60000);
    data.push({
      time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      temperature: 23 + Math.random() * 4 + Math.sin(i / 5) * 2,
      humidity: 45 + Math.random() * 3 + Math.cos(i / 5) * 2,
    });
  }
  return data;
}

/**
 * Smart chart helper - Dynamic min-max detection for flexible sensor data
 */
export function getSmartChartDomain(data: any[], dataKey: string, padding = 0.1): [number, number] {
  if (!data || data.length === 0) return [0, 100];
  
  const values = data.map(d => d[dataKey]).filter(v => typeof v === 'number' && !isNaN(v));
  if (values.length === 0) return [0, 100];
  
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  const paddingAmount = range * padding;
  
  return [
    Math.max(0, min - paddingAmount), // Don't go below 0 for sensor data
    max + paddingAmount
  ];
}

/**
 * Generate signal strength data for demo purposes
 */
export function generateSignalData() {
  const data = [];
  const now = new Date();
  for (let i = 20; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 300000); // 5-minute intervals
    data.push({
      time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      signal: -45 - Math.random() * 15 - (i % 5) * 2,
    });
  }
  return data;
}

/**
 * Format device ID for display
 */
export function formatDeviceId(deviceId: string): string {
  if (!deviceId) return '';
  // Format long device IDs for better display
  if (deviceId.length > 20) {
    return `${deviceId.substring(0, 8)}...${deviceId.substring(deviceId.length - 8)}`;
  }
  return deviceId;
}

/**
 * Calculate device uptime in human readable format
 */
export function formatUptime(uptimeSeconds: number): string {
  if (!uptimeSeconds || uptimeSeconds < 0) return '0m';
  
  const days = Math.floor(uptimeSeconds / 86400);
  const hours = Math.floor((uptimeSeconds % 86400) / 3600);
  const minutes = Math.floor((uptimeSeconds % 3600) / 60);
  
  if (days > 0) {
    return `${days}d ${hours}h`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
}

/**
 * Format data usage in human readable format
 */
export function formatDataUsage(megabytes: number): string {
  if (!megabytes || megabytes < 0) return '0 MB';
  
  if (megabytes >= 1024) {
    return `${(megabytes / 1024).toFixed(2)} GB`;
  }
  return `${megabytes.toFixed(2)} MB`;
}

/**
 * Get battery level status
 */
export function getBatteryStatus(level: number | undefined): { color: string; text: string } {
  if (level === undefined || level === null) {
    return { color: 'text-gray-500', text: 'N/A' };
  }
  
  if (level > 80) {
    return { color: 'text-green-600', text: `${level}%` };
  } else if (level > 30) {
    return { color: 'text-yellow-600', text: `${level}%` };
  } else {
    return { color: 'text-red-600', text: `${level}%` };
  }
}

/**
 * Get signal strength status
 */
export function getSignalStrengthStatus(rssi: number | undefined): { color: string; text: string; bars: number } {
  if (rssi === undefined || rssi === null) {
    return { color: 'text-gray-500', text: 'N/A', bars: 0 };
  }
  
  if (rssi > -50) {
    return { color: 'text-green-600', text: 'Excellent', bars: 4 };
  } else if (rssi > -60) {
    return { color: 'text-green-500', text: 'Good', bars: 3 };
  } else if (rssi > -70) {
    return { color: 'text-yellow-600', text: 'Fair', bars: 2 };
  } else {
    return { color: 'text-red-600', text: 'Poor', bars: 1 };
  }
}

/**
 * Get status color based on device status
 */
export function getStatusColor(status: string) {
  return DEVICE_STATUS_COLORS[status as keyof typeof DEVICE_STATUS_COLORS] || DEVICE_STATUS_COLORS.default;
}

/**
 * Get device icon based on device type
 */
export function getDeviceIcon(type: string) {
  switch (type) {
    case 'sensor': return React.createElement(Terminal, { className: "h-4 w-4" });
    case 'actuator': return React.createElement(Zap, { className: "h-4 w-4" });
    case 'gateway': return React.createElement(Router, { className: "h-4 w-4" });
    case 'controller': return React.createElement(Cpu, { className: "h-4 w-4" });
    default: return React.createElement(Server, { className: "h-4 w-4" });
  }
}