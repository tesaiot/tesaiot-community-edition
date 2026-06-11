/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useCallback, useRef, useMemo, memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Activity, 
  Thermometer, 
  Droplets, 
  Wind, 
  Gauge,
  RefreshCw,
  Play,
  Pause,
  Download,
  BarChart3
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { authFetch } from '@/utils/auth-fetch';
import { useTelemetryWebSocket } from '@/hooks/useTelemetryWebSocket';
import { cn } from '@/lib/utils';
import { formatTelemetryData, formatTelemetryValue } from '@/utils/telemetry-formatter';
import { RawDataPanel } from '@/features/telemetry/RawDataPanel';
import { useThrottledCallback, useDebouncedCallback } from '@/hooks/useDebounce';
import { TelemetryDashboardSkeleton, TelemetryCardSkeleton } from '@/components/LoadingSkeleton';
import ErrorBoundary from '@/components/ui/error-boundary';

interface TelemetryData {
  timestamp: string;
  [key: string]: any;
}

interface Device {
  id: string;
  device_id: string;
  name: string;
  status: string;
  type: string;
}

interface TelemetryDashboardProps {
  devices: Device[];
  className?: string;
  isTabActive?: boolean;
  showTitle?: boolean;
}

// Memoized components for better performance
const TelemetryCard = memo(({ field, value, icon }: { field: string; value: string; icon: React.ReactNode }) => (
  <Card className="p-4">
    <div className="flex items-center gap-2 mb-2">
      {icon}
      <span className="text-sm font-medium capitalize">{field.replace(/_/g, ' ')}</span>
    </div>
    <div className="text-2xl font-bold">
      {value}
    </div>
    <Badge variant="secondary" className="mt-1 text-xs">
      Live
    </Badge>
  </Card>
));
TelemetryCard.displayName = 'TelemetryCard';

const ChartContainer = memo(({ children, dataChanged }: { children: React.ReactNode; dataChanged: boolean }) => (
  <div className={cn(
    "w-full h-full transition-all duration-300",
    dataChanged && "ring-1 ring-green-500 ring-opacity-30 rounded-lg"
  )}>
    {children}
  </div>
));
ChartContainer.displayName = 'ChartContainer';

const TelemetryDashboardInner = memo(function TelemetryDashboardInner({ devices, className, isTabActive = true, showTitle = true }: TelemetryDashboardProps) {
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [telemetryData, setTelemetryData] = useState<TelemetryData[]>([]);
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [requestCount, setRequestCount] = useState<number>(0);
  const [countdown, setCountdown] = useState<number>(15);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [dataChanged, setDataChanged] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null); // Auto-refresh interval timer
  const countdownRef = useRef<NodeJS.Timeout | null>(null); // Countdown display timer
  const lastRequestTimeRef = useRef<number>(0);
  const requestCountRef = useRef<number>(0);

  // WebSocket for live telemetry
  const {
    isConnected: wsConnected,
    subscribeToDevice,
    unsubscribeFromDevice,
  } = useTelemetryWebSocket({
    onDeviceTelemetry: (deviceId: string, data: any) => {
      // Push live record to the head; cap to 200 entries
      const record = {
        timestamp: new Date().toISOString(),
        ...(typeof data === 'object' ? data : { value: data }),
      } as TelemetryData;
      setTelemetryData(prev => [record, ...prev].slice(0, 200));
      setLastUpdateTime(new Date());
      setDataChanged(true);
      setTimeout(() => setDataChanged(false), 800);
    },
    reconnect: true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  // Select first device by default
  useEffect(() => {
    if (devices.length > 0 && !selectedDevice) {
      setSelectedDevice(devices[0]);
    }
  }, [devices, selectedDevice]);

  // Throttled fetch function to prevent excessive API calls
  const fetchTelemetryDataInternal = useCallback(async () => {
    if (!selectedDevice) return;

    // Prevent excessive requests - throttle to max 1 request per 900ms even with 1s interval
    const now = Date.now();
    if (now - lastRequestTimeRef.current < 900) {
      console.log('[Telemetry] Request throttled to prevent overload');
      return;
    }

    setLoading(true);
    lastRequestTimeRef.current = now;
    requestCountRef.current += 1;
    setRequestCount(requestCountRef.current); // Update state for UI display
    
    try {
      console.log(`[Telemetry] Fetching telemetry for device: ${selectedDevice.device_id} (Request #${requestCountRef.current})`);
      // One-shot initial load to seed charts; WS handles live updates
      const response = await authFetch(`/api/v1/devices/${selectedDevice.device_id}/telemetry?limit=50`);
      if (response.ok) {
        const data = await response.json();
        console.log('Telemetry API response:', data);
        console.log('Telemetry array length:', (data.telemetry || []).length);
        console.log('Raw telemetry data:', data.telemetry);
        // Format telemetry data to handle MongoDB extended JSON
        const formattedTelemetry = formatTelemetryData(data.telemetry || []);
        console.log('Formatted telemetry data:', formattedTelemetry);
        
        // Check if data actually changed
        const hasChanged = JSON.stringify(formattedTelemetry) !== JSON.stringify(telemetryData);
        
        setTelemetryData(formattedTelemetry);
        setLastUpdateTime(new Date());
        setDataChanged(hasChanged);
        
        // Reset flash effect after 1 second
        if (hasChanged) {
          setTimeout(() => setDataChanged(false), 1000);
        }
        
        // Clear initial loading state
        if (initialLoading) {
          setInitialLoading(false);
        }
      } else {
        console.error('Telemetry fetch failed:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('Error response body:', errorText);
      }
    } catch (error) {
      console.error('Error fetching telemetry data:', error);
    } finally {
      setLoading(false);
      // Clear initial loading even on error
      if (initialLoading) {
        setInitialLoading(false);
      }
    }
  }, [selectedDevice, telemetryData, initialLoading]); // Include telemetryData for proper comparison

  // Use throttled version of fetch function (min 1 second between calls)
  const fetchTelemetryData = useThrottledCallback(fetchTelemetryDataInternal, 1000, [fetchTelemetryDataInternal]);

  // Auto-refresh interval constant (seconds)
  const AUTO_REFRESH_INTERVAL = 15;

  // WebSocket subscription lifecycle and initial fetch
  useEffect(() => {
    if (selectedDevice) {
      // Subscribe to WS for live updates
      subscribeToDevice(selectedDevice.device_id);
      // Initial fetch to seed data
      fetchTelemetryData();
    }
    return () => {
      if (selectedDevice) {
        unsubscribeFromDevice(selectedDevice.device_id);
      }
    };
  }, [selectedDevice, fetchTelemetryData, subscribeToDevice, unsubscribeFromDevice]);

  // Auto-refresh polling with countdown timer - FIX for Issue #2
  // This ensures data updates even when WebSocket doesn't push new data
  useEffect(() => {
    // Cleanup previous timers
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }

    // Only run when auto-refresh is enabled, tab is active, and device is selected
    if (!isAutoRefresh || !isTabActive || !selectedDevice) {
      setCountdown(AUTO_REFRESH_INTERVAL);
      return;
    }

    // Reset countdown
    setCountdown(AUTO_REFRESH_INTERVAL);

    // Countdown timer - updates every second
    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          return AUTO_REFRESH_INTERVAL; // Reset countdown after reaching 0
        }
        return prev - 1;
      });
    }, 1000);

    // Auto-refresh interval - fetch data every AUTO_REFRESH_INTERVAL seconds
    intervalRef.current = setInterval(() => {
      console.log('[Telemetry] Auto-refresh triggered');
      fetchTelemetryData();
    }, AUTO_REFRESH_INTERVAL * 1000);

    return () => {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      if (countdownRef.current) { clearInterval(countdownRef.current); countdownRef.current = null; }
    };
  }, [isAutoRefresh, isTabActive, selectedDevice, fetchTelemetryData]);

  // Memoized function to get latest telemetry values
  const getLatestValue = useCallback((field: string) => {
    if (telemetryData.length === 0) return '--';
    const latest = telemetryData[0];
    // Handle nested data structure from API
    const dataObj = latest.data || latest;
    const value = dataObj[field];
    return formatTelemetryValue(value);
  }, [telemetryData]);

  // Memoized data fields extraction for better performance
  const dataFields = useMemo(() => {
    console.log('Computing dataFields, telemetryData length:', telemetryData.length);
    if (telemetryData.length === 0) {
      console.log('No telemetry data available');
      return [];
    }
    const sampleData = telemetryData[0];
    console.log('Sample telemetry data:', sampleData);
    // Handle nested data structure from API
    const dataObj = sampleData.data || sampleData;
    console.log('Data object for field extraction:', dataObj);
    const fields = Object.keys(dataObj).filter(key => {
      // Exclude metadata fields
      if (key === 'timestamp' || key === 'device_id' || key === 'id' || 
          key === 'metadata' || key === '_id') {
        return false;
      }
      
      // Check if the value is a simple type (not an object)
      const value = dataObj[key];
      return typeof value !== 'object' || value === null;
    }).sort();
    console.log('Extracted fields:', fields);
    return fields;
  }, [telemetryData]);

  // Memoized icon mapping for better performance
  const getFieldIcon = useCallback((fieldName: string) => {
    const name = fieldName.toLowerCase();
    if (name.includes('temp')) return <Thermometer className="h-4 w-4" />;
    if (name.includes('humidity') || name.includes('humid')) return <Droplets className="h-4 w-4" />;
    if (name.includes('pressure') || name.includes('press')) return <Wind className="h-4 w-4" />;
    if (name.includes('voltage') || name.includes('current')) return <Activity className="h-4 w-4" />;
    return <Gauge className="h-4 w-4" />;
  }, []);

  // Smart Y-axis domain calculation to make oscillations visible
  // Auto-domain can hide small variations (e.g., 25.0-25.5 on 0-100 scale looks flat)
  const getSmartChartDomain = useCallback((data: any[], key: string, padding = 0.15): [number, number] | ['auto', 'auto'] => {
    if (!data || data.length === 0) return ['auto', 'auto'];

    const values = data.map(d => d[key]).filter(v => typeof v === 'number' && !isNaN(v));
    if (values.length === 0) return ['auto', 'auto'];

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;

    // If range is too small, expand it to show variation
    // Minimum range of 0.5 to avoid flat lines
    const effectiveRange = Math.max(range, 0.5);
    const paddingAmount = effectiveRange * padding;

    return [
      Math.floor((min - paddingAmount) * 100) / 100,
      Math.ceil((max + paddingAmount) * 100) / 100
    ];
  }, []);

  // Memoized chart data preparation
  const chartData = useMemo(() => {
    return dataFields
      .filter(field => {
        // Only show charts for numeric fields
        if (telemetryData.length === 0) return false;
        const sampleValue = (telemetryData[0].data || telemetryData[0])[field];
        return typeof sampleValue === 'number';
      })
      .slice(0, 4)
      .map(field => {
        const data = telemetryData.slice(0, 20).reverse().map(item => ({
          ...item,
          ...(item.data || {}),
          timestamp: item.timestamp
        }));
        return {
          field,
          data,
          yDomain: getSmartChartDomain(data, field)
        };
      });
  }, [dataFields, telemetryData, getSmartChartDomain]);

  return (
    <div className={cn(
      "w-full space-y-6 transition-all duration-300",
      dataChanged && "ring-2 ring-green-500 ring-opacity-50",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          {showTitle && <h2 className="text-2xl font-bold">Real-time Telemetry</h2>}
          <p className="text-muted-foreground">
            Live data from IoT device: {selectedDevice?.name || 'No device selected'}
          </p>
          {selectedDevice && (
            <div className="flex items-center gap-4 mt-2">
              {isAutoRefresh && isTabActive && (
                <>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                      <div className="absolute inset-0 h-2 w-2 bg-green-500 rounded-full animate-ping" />
                    </div>
                    <span className="text-xs font-medium text-green-600">LIVE</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Next refresh in {countdown}s
                  </span>
                </>
              )}
              {!isAutoRefresh && (
                <Badge variant="secondary" className="text-xs">
                  PAUSED
                </Badge>
              )}
              {requestCount > 0 && (
                <span className="text-xs text-muted-foreground">
                  {requestCount} updates • Last: {lastUpdateTime ? lastUpdateTime.toLocaleTimeString() : 'Never'}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTelemetryData}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAutoRefresh(!isAutoRefresh)}
          >
            {isAutoRefresh ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            {isAutoRefresh ? 'Pause' : 'Start'} Auto-refresh
          </Button>
        </div>
      </div>

      {/* Show loading skeleton during initial load */}
      {initialLoading && telemetryData.length === 0 ? (
        <TelemetryDashboardSkeleton />
      ) : (
        <>
      {/* Real-time Data Cards - Smart Display */}
      {dataFields.length > 0 ? (
        <div className="space-y-6">
          {/* Primary sensor values - show as cards */}
          {(() => {
            const latest = telemetryData[0];
            const dataObj = latest?.data || latest || {};
            
            // Primary numeric values to show as cards
            const primaryFields = dataFields.filter(field => {
              const value = dataObj[field];
              return typeof value === 'number' || typeof value === 'boolean';
            });
            
            // Complex objects to show in separate sections
            const complexFields = dataFields.filter(field => {
              const value = dataObj[field];
              return typeof value === 'object' && value !== null;
            });
            
            return (
              <>
                {/* Primary Value Cards */}
                {primaryFields.length > 0 && (
                  <div className={cn(
                    "grid gap-4",
                    primaryFields.length === 1 ? "grid-cols-1" :
                    primaryFields.length === 2 ? "grid-cols-2" :
                    primaryFields.length <= 4 ? "grid-cols-2 lg:grid-cols-4" :
                    "grid-cols-2 lg:grid-cols-4 xl:grid-cols-6"
                  )}>
                    {primaryFields.slice(0, 8).map((field) => (
                      <TelemetryCard
                        key={field}
                        field={field}
                        value={getLatestValue(field)}
                        icon={getFieldIcon(field)}
                      />
                    ))}
                  </div>
                )}
                
                {/* Complex Data Sections */}
                {complexFields.map((field) => {
                  const value = dataObj[field];
                  const fieldName = field.replace(/_/g, ' ').charAt(0).toUpperCase() + field.replace(/_/g, ' ').slice(1);
                  
                  return (
                    <Card key={field} className="p-4">
                      <CardHeader className="px-0 pt-0">
                        <CardTitle className="text-sm flex items-center gap-2">
                          {getFieldIcon(field)}
                          {fieldName}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="px-0 pb-0">
                        {(() => {
                          // Connection Info
                          if (field === 'connection_info' && typeof value === 'object') {
                            return (
                              <div className="grid grid-cols-2 gap-2">
                                {value.rssi !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Signal Strength</div>
                                    <div className="font-semibold">{value.rssi} dBm</div>
                                  </div>
                                )}
                                {value.auth_mode && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Auth Mode</div>
                                    <div className="font-semibold">{value.auth_mode}</div>
                                  </div>
                                )}
                                {value.mqtt_qos !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">MQTT QoS</div>
                                    <div className="font-semibold">{value.mqtt_qos}</div>
                                  </div>
                                )}
                                {value.protocol && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Protocol</div>
                                    <div className="font-semibold">{value.protocol}</div>
                                  </div>
                                )}
                              </div>
                            );
                          }
                          
                          // Device Health
                          if (field === 'device_health' && typeof value === 'object') {
                            return (
                              <div className="grid grid-cols-2 gap-2">
                                {value.battery_level !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Battery</div>
                                    <div className="font-semibold text-lg">🔋 {value.battery_level}%</div>
                                  </div>
                                )}
                                {value.cpu_usage !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">CPU Usage</div>
                                    <div className="font-semibold">{value.cpu_usage}%</div>
                                  </div>
                                )}
                                {value.memory_usage !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Memory</div>
                                    <div className="font-semibold">{value.memory_usage}%</div>
                                  </div>
                                )}
                                {value.uptime_hours !== undefined && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground">Uptime</div>
                                    <div className="font-semibold">{value.uptime_hours}h</div>
                                  </div>
                                )}
                              </div>
                            );
                          }
                          
                          // Motion Data
                          if (field === 'motion_data' && typeof value === 'object') {
                            return (
                              <div className="space-y-2">
                                {value.motion_detected !== undefined && (
                                  <div className="flex items-center gap-2">
                                    <div className={cn(
                                      "w-3 h-3 rounded-full",
                                      value.motion_detected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                                    )} />
                                    <span className="font-medium">
                                      {value.motion_detected ? 'Motion Detected' : 'No Motion'}
                                    </span>
                                  </div>
                                )}
                                {value.accelerometer && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground mb-1">Accelerometer</div>
                                    <div className="font-mono text-sm">
                                      X: {value.accelerometer.x?.toFixed(2) || 0} | 
                                      Y: {value.accelerometer.y?.toFixed(2) || 0} | 
                                      Z: {value.accelerometer.z?.toFixed(2) || 0}
                                    </div>
                                  </div>
                                )}
                                {value.gyroscope && (
                                  <div className="bg-muted p-2 rounded">
                                    <div className="text-xs text-muted-foreground mb-1">Gyroscope</div>
                                    <div className="font-mono text-sm">
                                      X: {value.gyroscope.x?.toFixed(2) || 0} | 
                                      Y: {value.gyroscope.y?.toFixed(2) || 0} | 
                                      Z: {value.gyroscope.z?.toFixed(2) || 0}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          }
                          
                          // Generic object display
                          return (
                            <div className="text-sm text-muted-foreground">
                              {formatTelemetryValue(value)}
                            </div>
                          );
                        })()}
                      </CardContent>
                    </Card>
                  );
                })}
              </>
            );
          })()}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <div className="text-muted-foreground">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">No Telemetry Data Available</p>
            <p className="text-sm mb-4">
              This device hasn't sent any telemetry data yet.
            </p>
            <div className="text-xs space-y-1">
              <p>Device ID: {selectedDevice?.device_id}</p>
              <p>Total records fetched: {telemetryData.length}</p>
              <p>Auto-refresh: {isAutoRefresh ? 'Enabled' : 'Disabled'}</p>
            </div>
            <div className="mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchTelemetryData}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
                Check Again
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Historical Data Charts */}
      {dataFields.length > 0 && telemetryData.length > 1 && (
        <Tabs defaultValue="charts" className="w-full">
          <TabsList>
            <TabsTrigger value="charts">Historical Charts</TabsTrigger>
            <TabsTrigger value="data">Raw Data</TabsTrigger>
          </TabsList>
          
          <TabsContent value="charts" className="space-y-4">
            {chartData.map((chartInfo, index) => (
              <Card key={chartInfo.field}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {getFieldIcon(chartInfo.field)}
                    {chartInfo.field.replace(/_/g, ' ').charAt(0).toUpperCase() + chartInfo.field.replace(/_/g, ' ').slice(1)}
                  </CardTitle>
                  <CardDescription>Historical trend for {chartInfo.field}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer dataChanged={dataChanged}>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartInfo.data}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis
                            dataKey="timestamp"
                            tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                          />
                          <YAxis domain={chartInfo.yDomain} />
                          <Tooltip 
                            labelFormatter={(value) => new Date(value).toLocaleString()}
                          />
                          <Line 
                            type="monotone" 
                            dataKey={chartInfo.field} 
                            stroke={`hsl(${index * 60 + 200}, 70%, 50%)`}
                            strokeWidth={2}
                            dot={{ r: 3 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </ChartContainer>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="data">
            <Card>
              <CardHeader>
                <CardTitle>Raw Telemetry Data</CardTitle>
                <CardDescription>Latest {telemetryData.length} records</CardDescription>
              </CardHeader>
              <CardContent>
                <RawDataPanel data={telemetryData} className="max-h-[520px]" />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
        </>
      )}
    </div>
  );
});

// Export with error boundary
export const TelemetryDashboard = memo(function TelemetryDashboard(props: TelemetryDashboardProps) {
  return (
    <ErrorBoundary>
      <TelemetryDashboardInner {...props} />
    </ErrorBoundary>
  );
});
