/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Activity, 
  TrendingUp, 
  AlertTriangle, 
  Brain,
  Zap,
  Settings,
  Play,
  Pause,
  BarChart3
} from 'lucide-react';
import { authFetch } from '@/utils/auth-fetch';
import { useTelemetryWebSocket } from '@/hooks/useTelemetryWebSocket';

interface StatisticalMetrics {
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  anomalyScore: number;
  sampleSize: number;
}

interface AnomalyAlert {
  id: string;
  deviceId: string;
  deviceName: string;
  metric: string;
  value: number;
  expectedRange: [number, number];
  severity: 'low' | 'medium' | 'high';
  timestamp: string;
  description: string;
}

interface RealTimeStatisticsProps {
  devices: any[];
  refreshInterval?: number;
}

export const RealTimeStatistics: React.FC<RealTimeStatisticsProps> = ({
  devices,
  refreshInterval = 5000
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [metrics, setMetrics] = useState<Record<string, StatisticalMetrics>>({});
  const [anomalies, setAnomalies] = useState<AnomalyAlert[]>([]);
  const [processedCount, setProcessedCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  
  // Legacy polling timer (removed in WS-only mode)
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const dataBufferRef = useRef<Record<string, number[]>>({});
  const windowSize = 100; // Rolling window size for statistics

  // WebSocket for live telemetry
  const { isConnected: wsConnected, subscribeToDevice, unsubscribeFromDevice } = useTelemetryWebSocket({
    onDeviceTelemetry: (deviceId: string, data: any) => {
      // Process metrics directly from WS message
      const fields = ['temperature','humidity','pressure','voltage'];
      const newMetrics: Record<string, StatisticalMetrics> = { ...metrics };
      const newAnomalies: AnomalyAlert[] = [];
      fields.forEach((metric) => {
        const v = data && typeof data === 'object' ? data[metric] : undefined;
        if (typeof v !== 'number' || Number.isNaN(v)) return;
        const key = `${deviceId}_${metric}`;
        if (!dataBufferRef.current[key]) dataBufferRef.current[key] = [];
        dataBufferRef.current[key].push(v);
        if (dataBufferRef.current[key].length > windowSize) {
          dataBufferRef.current[key] = dataBufferRef.current[key].slice(-windowSize);
        }
        const stats = calculateStatistics(dataBufferRef.current[key]);
        newMetrics[key] = stats;
        const anomaly = detectSimpleAnomaly(v, stats, { id: deviceId, name: deviceId }, metric);
        if (anomaly) newAnomalies.push(anomaly);
      });
      if (newAnomalies.length > 0) {
        setAnomalies(prev => [...newAnomalies, ...prev].slice(0, 50));
      }
      setMetrics(newMetrics);
      setProcessedCount(prev => prev + 1);
      setLastUpdate(new Date());
    },
    reconnect: true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  useEffect(() => {
    // Stop any legacy polling
    stopProcessing();
    
    if (isRunning) {
      // Subscribe each device for WS live updates
      devices.forEach(d => subscribeToDevice(d.id || d.device_id));
      // Optional: seed buffers with one-shot fetch for immediate charts
      void processRealTimeData();
    } else {
      devices.forEach(d => unsubscribeFromDevice(d.id || d.device_id));
    }
    return () => {
      devices.forEach(d => unsubscribeFromDevice(d.id || d.device_id));
    };
  }, [isRunning, devices, subscribeToDevice, unsubscribeFromDevice]);

  const startProcessing = () => { /* polling disabled in WS-only mode */ };

  const stopProcessing = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
  };

  const processRealTimeData = async () => {
    try {
      // Fetch latest telemetry for all devices
      const promises = devices.map(device => fetchLatestTelemetry(device.id));
      const results = await Promise.all(promises);
      
      const newMetrics: Record<string, StatisticalMetrics> = {};
      const newAnomalies: AnomalyAlert[] = [];

      results.forEach((telemetryData, index) => {
        const device = devices[index];
        if (!telemetryData || telemetryData.length === 0) return;

        // Process each metric
        ['temperature', 'humidity', 'pressure', 'voltage'].forEach(metric => {
          const metricKey = `${device.id}_${metric}`;
          const values = telemetryData
            .map((d: any) => d[metric])
            .filter((v: any) => v !== null && v !== undefined && !isNaN(v));

          if (values.length === 0) return;

          // Update rolling buffer
          if (!dataBufferRef.current[metricKey]) {
            dataBufferRef.current[metricKey] = [];
          }
          
          dataBufferRef.current[metricKey].push(...values);
          
          // Keep only last windowSize values
          if (dataBufferRef.current[metricKey].length > windowSize) {
            dataBufferRef.current[metricKey] = dataBufferRef.current[metricKey].slice(-windowSize);
          }

          const bufferData = dataBufferRef.current[metricKey];
          
          // Calculate statistics
          const stats = calculateStatistics(bufferData);
          newMetrics[metricKey] = stats;

          // Check for anomalies
          const latestValue = values[values.length - 1];
          const anomaly = detectSimpleAnomaly(latestValue, stats, device, metric);
          if (anomaly) {
            newAnomalies.push(anomaly);
          }
        });
      });

      setMetrics(newMetrics);
      setAnomalies(prev => [...newAnomalies, ...prev].slice(0, 50)); // Keep last 50 anomalies
      setProcessedCount(prev => prev + 1);
      setLastUpdate(new Date());

    } catch (error) {
      console.error('Real-time processing error:', error);
    }
  };

  const fetchLatestTelemetry = async (deviceId: string) => {
    try {
      const response = await authFetch(`/api/v1/devices/${deviceId}/telemetry?limit=5`);
      if (response.ok) {
        const data = await response.json();
        return data.telemetry || [];
      }
    } catch (error) {
      console.error(`Failed to fetch telemetry for device ${deviceId}:`, error);
    }
    return [];
  };

  const calculateStatistics = (values: number[]): StatisticalMetrics => {
    const sorted = [...values].sort((a, b) => a - b);
    const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
    const median = sorted[Math.floor(sorted.length / 2)];
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
    const std = Math.sqrt(variance);
    
    // Simple trend detection (last 10 vs previous 10)
    let trend: 'increasing' | 'decreasing' | 'stable' = 'stable';
    if (values.length >= 20) {
      const recent = values.slice(-10);
      const previous = values.slice(-20, -10);
      const recentMean = recent.reduce((sum, v) => sum + v, 0) / recent.length;
      const previousMean = previous.reduce((sum, v) => sum + v, 0) / previous.length;
      
      const change = (recentMean - previousMean) / previousMean;
      if (Math.abs(change) > 0.05) {
        trend = change > 0 ? 'increasing' : 'decreasing';
      }
    }

    // Simple anomaly score based on standard deviations from mean
    const latestValue = values[values.length - 1];
    const zScore = Math.abs((latestValue - mean) / std);
    const anomalyScore = Math.min(zScore / 3, 1); // Normalize to 0-1

    return {
      mean: parseFloat(mean.toFixed(2)),
      median: parseFloat(median.toFixed(2)),
      std: parseFloat(std.toFixed(2)),
      min: Math.min(...values),
      max: Math.max(...values),
      trend,
      anomalyScore: parseFloat(anomalyScore.toFixed(3)),
      sampleSize: values.length
    };
  };

  const detectSimpleAnomaly = (
    value: number, 
    stats: StatisticalMetrics, 
    device: any, 
    metric: string
  ): AnomalyAlert | null => {
    const threshold = 2.5; // Z-score threshold
    const zScore = Math.abs((value - stats.mean) / stats.std);
    
    if (zScore > threshold && stats.sampleSize >= 10) {
      const expectedRange: [number, number] = [
        stats.mean - threshold * stats.std,
        stats.mean + threshold * stats.std
      ];
      
      const severity: 'low' | 'medium' | 'high' = 
        zScore > 4 ? 'high' : zScore > 3 ? 'medium' : 'low';
      
      return {
        id: `anomaly-${Date.now()}-${Math.random()}`,
        deviceId: device.id,
        deviceName: device.name,
        metric,
        value,
        expectedRange,
        severity,
        timestamp: new Date().toISOString(),
        description: `${metric} value ${value.toFixed(2)} is ${zScore.toFixed(1)} standard deviations from normal (${stats.mean.toFixed(2)} ± ${stats.std.toFixed(2)})`
      };
    }
    
    return null;
  };

  const getMetricDisplayName = (metricKey: string) => {
    const [deviceId, metric] = metricKey.split('_');
    const device = devices.find(d => d.id === deviceId);
    return `${device?.name || deviceId} - ${metric}`;
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'decreasing':
        return <TrendingUp className="h-4 w-4 text-red-600 transform rotate-180" />;
      default:
        return <BarChart3 className="h-4 w-4 text-gray-600" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Control Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Real-time Statistical Processing
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant={isRunning ? "outline" : "default"}
                size="sm"
                onClick={() => setIsRunning(!isRunning)}
              >
                {isRunning ? (
                  <>
                    <Pause className="h-4 w-4 mr-2" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Start
                  </>
                )}
              </Button>
              <Badge variant={isRunning ? "default" : "secondary"}>
                {isRunning ? "Running" : "Stopped"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{processedCount}</div>
              <div className="text-sm text-muted-foreground">Processing Cycles</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{Object.keys(metrics).length}</div>
              <div className="text-sm text-muted-foreground">Active Metrics</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{anomalies.length}</div>
              <div className="text-sm text-muted-foreground">Anomalies Detected</div>
            </div>
            <div className="text-center">
              <div className="text-sm font-mono">
                {lastUpdate ? lastUpdate.toLocaleTimeString() : '--:--:--'}
              </div>
              <div className="text-sm text-muted-foreground">Last Update</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Current Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Live Statistical Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(metrics).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(metrics).map(([metricKey, stats]) => (
                <div key={metricKey} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-sm">{getMetricDisplayName(metricKey)}</h4>
                    {getTrendIcon(stats.trend)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">Mean:</span>
                      <span className="font-mono ml-1">{stats.mean}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Std:</span>
                      <span className="font-mono ml-1">{stats.std}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Min/Max:</span>
                      <span className="font-mono ml-1">{stats.min}/{stats.max}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Anomaly:</span>
                      <span className={`font-mono ml-1 ${stats.anomalyScore > 0.5 ? 'text-red-600' : 'text-green-600'}`}>
                        {(stats.anomalyScore * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <Badge variant="outline" className="text-xs">
                      {stats.sampleSize} samples
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {isRunning ? "Waiting for telemetry data..." : "Start processing to see metrics"}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Anomaly Alerts */}
      {anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Recent Anomalies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-60 overflow-y-auto">
              {anomalies.slice(0, 10).map((anomaly) => (
                <div key={anomaly.id} className={`p-3 border rounded-lg ${getSeverityColor(anomaly.severity)}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-sm">
                        {anomaly.deviceName} - {anomaly.metric}
                      </div>
                      <div className="text-xs mt-1">{anomaly.description}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {new Date(anomaly.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <Badge variant="outline" className="ml-2">
                      {anomaly.severity.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
