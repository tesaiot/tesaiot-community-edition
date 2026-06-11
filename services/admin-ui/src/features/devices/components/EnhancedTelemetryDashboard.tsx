/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
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
import { cn } from '@/lib/utils';
import { formatTelemetryData, formatTelemetryValue } from '@/utils/telemetry-formatter';
import { 
  AutoRefreshStatusBar,
  DataUpdateFlash,
  RefreshProgressBar,
  LiveIndicator,
  RefreshCountdown,
  DataFetchSpinner,
  LastUpdateTimestamp,
  logRefreshEvent
} from '@/components/AutoRefreshIndicators';

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

interface EnhancedTelemetryDashboardProps {
  devices: Device[];
  className?: string;
  isTabActive?: boolean;
  refreshInterval?: number; // Allow customizable refresh interval
}

export function EnhancedTelemetryDashboard({ 
  devices, 
  className, 
  isTabActive = true,
  refreshInterval = 1000 // Default to 1 second for real-time feel
}: EnhancedTelemetryDashboardProps) {
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [telemetryData, setTelemetryData] = useState<TelemetryData[]>([]);
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);
  const [requestCount, setRequestCount] = useState<number>(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [dataUpdateTrigger, setDataUpdateTrigger] = useState(0);
  const [countdown, setCountdown] = useState(refreshInterval / 1000);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);
  const lastRequestTimeRef = useRef<number>(0);
  const requestCountRef = useRef<number>(0);
  const nextRefreshTimeRef = useRef<number>(0);

  // Select first device by default
  useEffect(() => {
    if (devices.length > 0 && !selectedDevice) {
      setSelectedDevice(devices[0]);
    }
  }, [devices, selectedDevice]);

  // Calculate next refresh time
  const nextRefreshIn = useMemo(() => {
    if (!isAutoRefresh || !nextRefreshTimeRef.current) return 0;
    const now = Date.now();
    const timeSinceLastRefresh = now - nextRefreshTimeRef.current;
    return Math.max(0, refreshInterval - timeSinceLastRefresh);
  }, [isAutoRefresh, refreshInterval, dataUpdateTrigger]); // recalculate on data update

  // Fetch real telemetry data from API
  const fetchTelemetryData = useCallback(async () => {
    if (!selectedDevice) return;

    // Prevent excessive requests
    const now = Date.now();
    if (now - lastRequestTimeRef.current < Math.min(900, refreshInterval * 0.9)) {
      logRefreshEvent('Request throttled', { deviceId: selectedDevice.device_id });
      return;
    }

    setLoading(true);
    lastRequestTimeRef.current = now;
    requestCountRef.current += 1;
    setRequestCount(requestCountRef.current);
    
    logRefreshEvent('Fetching data', { 
      deviceId: selectedDevice.device_id, 
      requestNumber: requestCountRef.current 
    });
    
    try {
      const response = await authFetch(`/api/v1/devices/${selectedDevice.device_id}/telemetry?limit=50`);
      if (response.ok) {
        const data = await response.json();
        const formattedTelemetry = formatTelemetryData(data.telemetry || []);
        
        // Check if data actually changed
        const hasNewData = formattedTelemetry.length > 0 && 
          (telemetryData.length === 0 || 
           formattedTelemetry[0].timestamp !== telemetryData[0].timestamp);
        
        if (hasNewData) {
          setTelemetryData(formattedTelemetry);
          setDataUpdateTrigger(prev => prev + 1);
          logRefreshEvent('New data received', { 
            records: formattedTelemetry.length,
            latestTimestamp: formattedTelemetry[0]?.timestamp 
          });
        } else {
          logRefreshEvent('No new data');
        }
        
        setLastUpdate(new Date());
        setFetchError(null);
      } else {
        const errorMsg = `Failed to fetch: ${response.status} ${response.statusText}`;
        setFetchError(errorMsg);
        logRefreshEvent('Fetch error', { error: errorMsg });
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Network error';
      setFetchError(errorMsg);
      logRefreshEvent('Network error', { error: errorMsg });
    } finally {
      setLoading(false);
    }
  }, [selectedDevice, telemetryData, refreshInterval]);

  // Countdown timer effect
  useEffect(() => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
    }

    if (isAutoRefresh) {
      setCountdown(refreshInterval / 1000);
      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) return refreshInterval / 1000;
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
      }
    };
  }, [isAutoRefresh, refreshInterval]);

  // Auto-refresh telemetry data with tab visibility detection
  useEffect(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Only auto-refresh when tab is active, device is selected, and auto-refresh is enabled
    if (selectedDevice && isAutoRefresh && isTabActive) {
      logRefreshEvent('Starting auto-refresh', { 
        deviceId: selectedDevice.device_id, 
        tabActive: isTabActive,
        interval: refreshInterval 
      });
      
      // Fetch data immediately
      nextRefreshTimeRef.current = Date.now();
      fetchTelemetryData();
      
      // Set up polling interval
      intervalRef.current = setInterval(() => {
        nextRefreshTimeRef.current = Date.now();
        fetchTelemetryData();
      }, refreshInterval);
    } else if (selectedDevice && !isTabActive) {
      logRefreshEvent('Pausing auto-refresh', { 
        deviceId: selectedDevice.device_id, 
        reason: 'Tab not active' 
      });
    }

    // Cleanup function
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        logRefreshEvent('Stopped auto-refresh', { reason: 'Cleanup' });
      }
    };
  }, [selectedDevice, isAutoRefresh, isTabActive, fetchTelemetryData, refreshInterval]);

  // Get latest telemetry values for cards
  const getLatestValue = (field: string) => {
    if (telemetryData.length === 0) return '--';
    const latest = telemetryData[0];
    const dataObj = latest.data || latest;
    const value = dataObj[field];
    return formatTelemetryValue(value);
  };

  // Get unique data fields from actual telemetry
  const getDataFields = () => {
    if (telemetryData.length === 0) return [];
    const sampleData = telemetryData[0];
    const dataObj = sampleData.data || sampleData;
    const fields = Object.keys(dataObj).filter(key => {
      if (key === 'timestamp' || key === 'device_id' || key === 'id' || 
          key === 'metadata' || key === '_id') {
        return false;
      }
      const value = dataObj[key];
      return typeof value !== 'object' || value === null;
    }).sort();
    return fields;
  };

  // Simple icon mapping for common fields
  const getFieldIcon = (fieldName: string) => {
    const name = fieldName.toLowerCase();
    if (name.includes('temp')) return <Thermometer className="h-4 w-4" />;
    if (name.includes('humidity') || name.includes('humid')) return <Droplets className="h-4 w-4" />;
    if (name.includes('pressure') || name.includes('press')) return <Wind className="h-4 w-4" />;
    if (name.includes('voltage') || name.includes('current')) return <Activity className="h-4 w-4" />;
    return <Gauge className="h-4 w-4" />;
  };

  const dataFields = getDataFields();

  return (
    <div className={cn("w-full space-y-6 relative", className)}>
      {/* Data Update Flash Effect */}
      <DataUpdateFlash trigger={dataUpdateTrigger} />
      
      {/* Header with Live Indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-2xl font-bold">Enhanced Real-time Telemetry</h2>
            <p className="text-muted-foreground">
              Live data from IoT device: {selectedDevice?.name || 'No device selected'}
            </p>
          </div>
          {/* Main Live Indicator */}
          <LiveIndicator 
            isActive={isAutoRefresh} 
            isLoading={loading} 
            hasError={!!fetchError}
            className="scale-125"
          />
        </div>
        <div className="flex items-center gap-2">
          {/* Countdown Display */}
          {isAutoRefresh && (
            <div className="flex items-center gap-2 px-3 py-1 bg-muted rounded-md">
              <RefreshCw className="h-3 w-3 text-muted-foreground animate-spin" />
              <span className="text-sm font-mono font-bold">
                {countdown}s
              </span>
            </div>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTelemetryData}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Manual Refresh
          </Button>
        </div>
      </div>

      {/* Auto-Refresh Status Bar */}
      <AutoRefreshStatusBar
        isActive={isAutoRefresh}
        isLoading={loading}
        lastUpdate={lastUpdate}
        nextRefreshIn={nextRefreshIn}
        refreshInterval={refreshInterval}
        onToggle={() => setIsAutoRefresh(!isAutoRefresh)}
        hasError={!!fetchError}
        errorMessage={fetchError || undefined}
        dataCount={telemetryData.length}
      />

      {/* Progress Bar */}
      <RefreshProgressBar
        nextRefreshIn={nextRefreshIn}
        refreshInterval={refreshInterval}
        isActive={isAutoRefresh}
      />

      {/* Loading Spinner Overlay */}
      {loading && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
          <DataFetchSpinner isLoading={loading} className="scale-150" />
        </div>
      )}

      {/* Real-time Data Cards */}
      {dataFields.length > 0 ? (
        <div className="space-y-6">
          {(() => {
            const latest = telemetryData[0];
            const dataObj = latest?.data || latest || {};
            
            const primaryFields = dataFields.filter(field => {
              const value = dataObj[field];
              return typeof value === 'number' || typeof value === 'boolean';
            });
            
            return (
              <div className={cn(
                "grid gap-4",
                primaryFields.length === 1 ? "grid-cols-1" :
                primaryFields.length === 2 ? "grid-cols-2" :
                primaryFields.length <= 4 ? "grid-cols-2 lg:grid-cols-4" :
                "grid-cols-2 lg:grid-cols-4 xl:grid-cols-6"
              )}>
                {primaryFields.slice(0, 8).map((field) => (
                  <Card key={field} className="p-4 relative overflow-hidden transition-all hover:shadow-lg">
                    {/* Card-level Update Flash */}
                    <DataUpdateFlash trigger={dataUpdateTrigger} className="rounded-lg" />
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {getFieldIcon(field)}
                        <span className="text-sm font-medium capitalize">{field.replace(/_/g, ' ')}</span>
                      </div>
                      {/* Card-level Live Indicator */}
                      {isAutoRefresh && (
                        <div className="relative">
                          <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                          <div className="absolute inset-0 h-2 w-2 bg-green-500 rounded-full animate-ping" />
                        </div>
                      )}
                    </div>
                    <div className="text-2xl font-bold">
                      {getLatestValue(field)}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className="text-xs">
                        Live
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {lastUpdate && `${Math.round((Date.now() - lastUpdate.getTime()) / 1000)}s ago`}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
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
            {dataFields
              .filter(field => {
                if (telemetryData.length === 0) return false;
                const sampleValue = (telemetryData[0].data || telemetryData[0])[field];
                return typeof sampleValue === 'number';
              })
              .slice(0, 4)
              .map((field, index) => (
              <Card key={field}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {getFieldIcon(field)}
                    {field.replace(/_/g, ' ').charAt(0).toUpperCase() + field.replace(/_/g, ' ').slice(1)}
                  </CardTitle>
                  <CardDescription>
                    Historical trend for {field}
                    {isAutoRefresh && (
                      <span className="ml-2 text-xs text-green-600">
                        • Auto-updating every {refreshInterval / 1000}s
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={telemetryData.slice(0, 20).reverse().map(item => ({
                        ...item,
                        ...(item.data || {}),
                        timestamp: item.timestamp
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="timestamp"
                          tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                        />
                        <YAxis />
                        <Tooltip 
                          labelFormatter={(value) => new Date(value).toLocaleString()}
                        />
                        <Line 
                          type="monotone" 
                          dataKey={field} 
                          stroke={`hsl(${index * 60 + 200}, 70%, 50%)`}
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          animationDuration={500}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="data">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Raw Telemetry Data</CardTitle>
                    <CardDescription>Latest {telemetryData.length} records</CardDescription>
                  </div>
                  <LastUpdateTimestamp timestamp={lastUpdate} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-950 rounded-lg p-4 h-64 overflow-y-auto">
                  <div className="space-y-1 font-mono text-xs text-gray-100">
                    {telemetryData.slice(0, 10).map((record, index) => {
                      const dataObj = record.data || record;
                      const timestamp = record.timestamp;
                      return (
                        <div key={index} className="border-b border-gray-800 pb-1">
                          <div className="text-blue-400">{new Date(timestamp).toLocaleString()}</div>
                          <div className="ml-4">
                            {Object.entries(dataObj).filter(([key]) => 
                              key !== 'timestamp' && key !== 'device_id' && key !== 'id' && key !== '_id' && key !== 'metadata'
                            ).map(([key, value]) => (
                              <span key={key} className="text-gray-300 mr-4">
                                {key}: <span className="text-yellow-400">
                                  {formatTelemetryValue(value)}
                                </span>
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}