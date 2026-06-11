/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  BarChart3,
  Settings,
  Zap,
  Clock,
  Battery,
  Wifi,
  WifiOff,
  Radio,
  AlertTriangle,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { authFetch } from '@/utils/auth-fetch';
import { cn } from '@/lib/utils';
import { formatTelemetryData, formatTelemetryValue } from '@/utils/telemetry-formatter';
import { useSmartRefreshRate, type RefreshRateConfig } from '@/hooks/useSmartRefreshRate';
import { useTelemetryWebSocket } from '@/hooks/useTelemetryWebSocket-python-workaround';
import { RefreshRateSettings } from '@/components/RefreshRateSettings';
import { PerformanceMonitor } from '@/components/PerformanceMonitor';
import { useToast } from '@/hooks/use-toast';
import { RawDataPanel } from '@/features/telemetry/RawDataPanel';

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

interface SmartTelemetryDashboardProps {
  devices: Device[];
  className?: string;
  isTabActive?: boolean;
  showTitle?: boolean;
}

export function SmartTelemetryDashboard({ devices, className, isTabActive = true, showTitle = true }: SmartTelemetryDashboardProps) {
  const { toast } = useToast();
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [telemetryData, setTelemetryData] = useState<TelemetryData[]>([]);
  const [telemetryCache, setTelemetryCache] = useState<Record<string, TelemetryData[]>>({});
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPerformance, setShowPerformance] = useState(false);
  
  // WebSocket state
  const [useWebSocket, setUseWebSocket] = useState(() => {
    return localStorage.getItem('useWebSocketTelemetry') === 'true';
  });
  const [wsConnectionStatus, setWsConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [lastWebSocketMessage, setLastWebSocketMessage] = useState<Date | null>(null);
  const [webSocketMetrics, setWebSocketMetrics] = useState({
    messagesReceived: 0,
    connectionTime: 0,
    reconnects: 0
  });
  
  // Load saved refresh configuration
  const [refreshConfig, setRefreshConfig] = useState<Partial<RefreshRateConfig>>(() => {
    const saved = localStorage.getItem('telemetryRefreshConfig');
    const config = saved ? JSON.parse(saved) : { userPreference: 'normal' };
    console.log('[SmartTelemetry] 📋 Loaded refresh config:', config);
    return config;
  });

  // WebSocket hook for real-time telemetry
  const {
    isConnected: wsConnected,
    error: wsError,
    lastMessage,
    subscribeToDevice,
    unsubscribeFromDevice,
    reconnect: reconnectWebSocket
  } = useTelemetryWebSocket({
    enabled: useWebSocket,  // Only connect when WebSocket is enabled
    onDeviceTelemetry: useCallback((deviceId: string, data: any) => {
      // Handle real-time telemetry data from WebSocket
      // STRICT CHECK: Only accept data for the currently selected device
      const currentDeviceId = selectedDevice?.device_id || selectedDevice?.id;
      
      if (!currentDeviceId || currentDeviceId !== deviceId) {
        console.log('[SmartTelemetry] Ignoring telemetry for non-selected device:', deviceId, 'Current:', currentDeviceId);
        return;
      }
      
      if (selectedDevice && (selectedDevice.device_id === deviceId || selectedDevice.id === deviceId)) {
        console.log('[SmartTelemetry] WebSocket telemetry received for selected device:', deviceId, data);
        
        // Normalize timestamp to ISO string format
        let telemetryTimestamp;
        if (data.timestamp) {
          // If it's already an ISO string, use it
          if (typeof data.timestamp === 'string' && data.timestamp.includes('T')) {
            telemetryTimestamp = data.timestamp;
          }
          // If it's a Unix timestamp (number or string)
          else if (typeof data.timestamp === 'number' || (typeof data.timestamp === 'string' && /^\d+$/.test(data.timestamp))) {
            const ts = typeof data.timestamp === 'string' ? parseInt(data.timestamp) : data.timestamp;
            // Unix timestamps can be in seconds or milliseconds
            const multiplier = ts < 10000000000 ? 1000 : 1;
            telemetryTimestamp = new Date(ts * multiplier).toISOString();
          }
          // Otherwise try to parse it as a date
          else {
            telemetryTimestamp = new Date(data.timestamp).toISOString();
          }
        } else {
          telemetryTimestamp = new Date().toISOString();
        }
        
        const newTelemetryRecord = {
          ...data,
          timestamp: telemetryTimestamp,  // Always store as ISO string
          data: data.data || data,
          device_id: deviceId,  // Ensure device_id is always present for filtering
          deviceId: deviceId    // Include both formats for compatibility
        };
        
        // Update current telemetry data
        setTelemetryData(prev => {
          // IMPORTANT: Only keep data for the current device
          // Filter out any data that doesn't belong to the current device
          const currentDeviceData = prev.filter(item => {
            const itemDeviceId = item.device_id || item.deviceId;
            return itemDeviceId === deviceId;
          });
          
          // Add new record and sort by timestamp to maintain chronological order
          const updated = [newTelemetryRecord, ...currentDeviceData];
          
          // Sort by timestamp (newest first) and keep only last 50
          const sortedData = updated.sort((a, b) => {
            // Since we normalized to ISO strings, we can directly compare
            const timeA = new Date(a.timestamp).getTime();
            const timeB = new Date(b.timestamp).getTime();
            return timeB - timeA; // Newest first
          }).slice(0, 50);
          
          // Also update the cache for this device
          setTelemetryCache(cache => ({
            ...cache,
            [deviceId]: sortedData
          }));
          
          return sortedData;
        });
        
        setLastWebSocketMessage(new Date());
        setWebSocketMetrics(prev => ({
          ...prev,
          messagesReceived: prev.messagesReceived + 1
        }));
      }
    }, [selectedDevice]),
    onMessage: useCallback((message) => {
      console.log('[SmartTelemetry] WebSocket message received:', message);
    }, []),
    reconnectAttempts: 5,
    reconnectInterval: 3000
  });

  // Update WebSocket connection status with a short grace period to avoid red-flash on first connect
  useEffect(() => {
    if (!useWebSocket) {
      setWsConnectionStatus('disconnected');
      return;
    }

    if (wsConnected) {
      setWsConnectionStatus('connected');
      setWebSocketMetrics(prev => ({ ...prev, connectionTime: Date.now() }));
      return;
    }

    if (wsError) {
      // Grace window: if just mounted or within 1500ms of toggling WS, show 'connecting' instead of 'error'
      const startedAt = (window as any).__tesa_ws_start_time__ || Date.now();
      (window as any).__tesa_ws_start_time__ = startedAt;
      const elapsed = Date.now() - startedAt;
      if (elapsed < 1500) {
        setWsConnectionStatus('connecting');
      } else {
        setWsConnectionStatus('error');
      }
      return;
    }

    setWsConnectionStatus('connecting');
  }, [useWebSocket, wsConnected, wsError]);

  // Select first device by default or handle device changes
  useEffect(() => {
    if (devices.length > 0) {
      // If no device is selected, select the first online device or first available
      if (!selectedDevice) {
        // Prioritize online devices
        const onlineDevice = devices.find(d => d.status === 'online' || d.status === 'active');
        const deviceToSelect = onlineDevice || devices[0];
        setSelectedDevice(deviceToSelect);
        console.log('[SmartTelemetry] Auto-selected device:', deviceToSelect.name, 'Status:', deviceToSelect.status);
      } else {
        // Check if the currently selected device still exists in the devices list
        const deviceStillExists = devices.find(d => 
          (d.device_id && d.device_id === selectedDevice.device_id) ||
          (d.id && d.id === selectedDevice.id)
        );
        
        // If the selected device no longer exists, select the first available device
        if (!deviceStillExists) {
          const onlineDevice = devices.find(d => d.status === 'online' || d.status === 'active');
          const deviceToSelect = onlineDevice || devices[0];
          setSelectedDevice(deviceToSelect);
          console.log('[SmartTelemetry] Selected device no longer available, switched to:', deviceToSelect.name);
        }
      }
    } else {
      // No devices available, clear selection
      if (selectedDevice) {
        setSelectedDevice(null);
        console.log('[SmartTelemetry] No devices available, cleared selection');
      }
    }
  }, [devices, selectedDevice]);

  // Fetch telemetry data (HTTP fallback or initial load)
  const fetchTelemetryData = useCallback(async () => {
    if (!selectedDevice) return;

    const deviceId = selectedDevice.device_id || selectedDevice.id;
    
    // Check if we have cached data for this device
    const cachedData = telemetryCache[deviceId];
    if (cachedData && cachedData.length > 0) {
      console.log(`[SmartTelemetry] Using cached data for device ${deviceId}: ${cachedData.length} records`);
      setTelemetryData(cachedData);
      return;
    }

    setLoading(true);
    try {
      console.log('Smart refresh: Fetching telemetry for device:', deviceId);
      // Only fetch recent telemetry (last 2 minutes) for initial load
      const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000).toISOString();
      const response = await authFetch(`/api/v1/devices/${deviceId}/telemetry?limit=20&since=${twoMinutesAgo}`);
      if (response.ok) {
        const data = await response.json();
        const formattedTelemetry = formatTelemetryData(data.telemetry || []);
        
        // Update both current data and cache
        setTelemetryData(formattedTelemetry);
        setTelemetryCache(prev => ({
          ...prev,
          [deviceId]: formattedTelemetry
        }));
      } else {
        console.error('Telemetry fetch failed:', response.status, response.statusText);
        throw new Error(`Failed to fetch telemetry: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error fetching telemetry data:', error);
      // Error will be tracked by smart refresh hook
      throw error;
    } finally {
      setLoading(false);
    }
  }, [selectedDevice, telemetryCache]);

  // Initial data fetch when device is selected
  useEffect(() => {
    if (selectedDevice && (!useWebSocket || wsConnectionStatus !== 'connected')) {
      // Only fetch initial data if not using WebSocket or WebSocket is not connected
      console.log('[SmartTelemetry] Triggering initial refresh for device:', selectedDevice.device_id);
      fetchTelemetryData().catch(error => {
        console.error('[SmartTelemetry] Initial refresh failed:', error);
      });
    }
  }, [selectedDevice, fetchTelemetryData, useWebSocket, wsConnectionStatus]);

  // Handle device subscription when selectedDevice changes
  useEffect(() => {
    if (!selectedDevice) return;
    
    const deviceId = selectedDevice.device_id || selectedDevice.id;
    
    // Load cached data immediately when switching devices
    const cachedData = telemetryCache[deviceId];
    if (cachedData && cachedData.length > 0) {
      console.log(`[SmartTelemetry] Loading cached data for device ${deviceId}: ${cachedData.length} records`);
      setTelemetryData(cachedData);
    } else {
      // No cached data, clear and wait for new data
      console.log(`[SmartTelemetry] No cached data for device ${deviceId}, starting fresh`);
      setTelemetryData([]);
    }
    
    // Always unsubscribe from all devices first to prevent data bleeding
    if (unsubscribeFromDevice) {
      // Get all device IDs to unsubscribe from
      devices.forEach(device => {
        const id = device.device_id || device.id;
        if (id && id !== deviceId) {  // Don't unsubscribe from the device we're about to subscribe to
          unsubscribeFromDevice(id);
        }
      });
    }
    
    // Then subscribe to the selected device only
    if (useWebSocket && wsConnected && selectedDevice) {
      console.log('[SmartTelemetry] Subscribing to WebSocket telemetry for device:', deviceId);
      
      // Small delay to ensure unsubscribe completes first
      setTimeout(() => {
        subscribeToDevice(deviceId);
      }, 100);
      
      return () => {
        console.log('[SmartTelemetry] Cleanup: Unsubscribing from device:', deviceId);
        unsubscribeFromDevice(deviceId);
      };
    }
  }, [useWebSocket, wsConnected, selectedDevice, subscribeToDevice, unsubscribeFromDevice, devices, telemetryCache]);

  // Use smart refresh rate hook - keep HTTP polling as fallback even when WebSocket is enabled
  const {
    isRefreshing,
    currentInterval,
    refreshMode,
    performanceMetrics,
    pause,
    resume,
    forceRefresh,
    updateConfig,
    isActive,
  } = useSmartRefreshRate({
    onRefresh: fetchTelemetryData,
    config: refreshConfig,
    enableTabVisibility: true,
    enablePerformanceMonitoring: true,
    enableIdleDetection: true,
    // Disable HTTP polling when:
    // 1. No device selected OR
    // 2. WebSocket is enabled AND connected
    disabled: !selectedDevice || (useWebSocket && wsConnectionStatus === 'connected'),
  });

  // Simplified refresh management - HTTP polling as reliable fallback
  useEffect(() => {
    console.log('[SmartTelemetry] 🔄 Refresh state check:', {
      isTabActive,
      isActive,
      selectedDevice: !!selectedDevice,
      useWebSocket,
      wsConnectionStatus
    });
    
    // Only use HTTP polling when WebSocket is NOT connected
    const shouldUseHttpPolling = !useWebSocket || wsConnectionStatus !== 'connected';
    
    if (isTabActive && selectedDevice && !isActive && shouldUseHttpPolling) {
      console.log('[SmartTelemetry] ▶️ Resuming HTTP auto-refresh (WebSocket not connected)');
      resume();
    } else if (!isTabActive && isActive) {
      console.log('[SmartTelemetry] ⏸️ Pausing auto-refresh (tab not active)');
      pause();
    } else if (useWebSocket && wsConnectionStatus === 'connected' && isActive) {
      console.log('[SmartTelemetry] ⏸️ Pausing HTTP polling (WebSocket is connected)');
      pause();
    }
  }, [isTabActive, isActive, selectedDevice, pause, resume, useWebSocket, wsConnectionStatus]);

  // Handle WebSocket connection state changes for data continuity
  useEffect(() => {
    const prevConnectionStatus = wsConnectionStatus;
    
    if (useWebSocket && selectedDevice) {
      if (wsConnectionStatus === 'error' && prevConnectionStatus === 'connected') {
        // WebSocket connection lost - immediately fetch latest data via HTTP and resume polling
        console.log('[SmartTelemetry] WebSocket connection lost, falling back to HTTP');
        fetchTelemetryData().catch(error => {
          console.error('[SmartTelemetry] Fallback data fetch failed:', error);
        });
        if (isTabActive) {
          resume();
        }
      } else if (wsConnectionStatus === 'connected' && prevConnectionStatus !== 'connected') {
        // WebSocket connected - pause HTTP polling
        console.log('[SmartTelemetry] WebSocket connected, switching to real-time mode');
        pause();
      }
    }
  }, [wsConnectionStatus, useWebSocket, selectedDevice, fetchTelemetryData, isTabActive, resume, pause]);

  // Handle config changes
  const handleConfigChange = (newConfig: Partial<RefreshRateConfig>) => {
    setRefreshConfig(newConfig);
    updateConfig(newConfig);
  };

  // Save config to localStorage
  const handleConfigSave = () => {
    localStorage.setItem('telemetryRefreshConfig', JSON.stringify(refreshConfig));
    toast({
      title: "Settings Saved",
      description: "Refresh rate configuration has been saved",
    });
    setShowSettings(false);
  };

  // Reset config
  const handleConfigReset = () => {
    const defaultConfig = { userPreference: 'normal' as const };
    setRefreshConfig(defaultConfig);
    updateConfig(defaultConfig);
    localStorage.removeItem('telemetryRefreshConfig');
    toast({
      title: "Settings Reset",
      description: "Refresh rate configuration has been reset to defaults",
    });
  };

  // Handle data refresh when switching between modes
  const handleModeSwitch = useCallback(async (fromWebSocket: boolean, toWebSocket: boolean) => {
    if (!selectedDevice) return;
    
    if (fromWebSocket && !toWebSocket) {
      // Switching from WebSocket to HTTP - fetch latest data
      console.log('[SmartTelemetry] Switching from WebSocket to HTTP, fetching latest data');
      try {
        await fetchTelemetryData();
      } catch (error) {
        console.error('[SmartTelemetry] Failed to fetch data during mode switch:', error);
      }
    } else if (!fromWebSocket && toWebSocket) {
      // Switching from HTTP to WebSocket - clear old data to avoid stale data mixing
      console.log('[SmartTelemetry] Switching from HTTP to WebSocket, clearing old data for fresh real-time stream');
      // Clear existing data to start fresh with WebSocket data only
      setTelemetryData([]);
    }
  }, [selectedDevice, fetchTelemetryData]);

  // Handle WebSocket toggle
  const handleWebSocketToggle = useCallback(async () => {
    const newUseWebSocket = !useWebSocket;
    const oldUseWebSocket = useWebSocket;
    
    setUseWebSocket(newUseWebSocket);
    localStorage.setItem('useWebSocketTelemetry', newUseWebSocket.toString());
    
    // Handle data refresh during mode switch
    await handleModeSwitch(oldUseWebSocket, newUseWebSocket);
    
    if (newUseWebSocket) {
      // Switching to WebSocket mode - pause HTTP polling
      pause();
      toast({
        title: "WebSocket Enabled",
        description: "Switching to real-time WebSocket streaming",
      });
    } else {
      // Switching to HTTP mode - resume HTTP polling if tab is active and device is selected
      if (selectedDevice && isTabActive) {
        resume();
      }
      toast({
        title: "WebSocket Disabled",
        description: "Falling back to HTTP polling",
      });
    }
  }, [useWebSocket, toast, resume, pause, selectedDevice, isTabActive, handleModeSwitch]);

  // Handle WebSocket reconnect
  const handleWebSocketReconnect = useCallback(() => {
    setWebSocketMetrics(prev => ({
      ...prev,
      reconnects: prev.reconnects + 1
    }));
    reconnectWebSocket();
    toast({
      title: "Reconnecting",
      description: "Attempting to reconnect WebSocket...",
    });
  }, [reconnectWebSocket, toast]);

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

  // Smart Y-axis domain calculation to make oscillations visible
  // Auto-domain can hide small variations (e.g., 25.0-25.5 on 0-100 scale looks flat)
  const getSmartChartDomain = useCallback((data: any[], key: string, padding = 0.15): [number, number] | ['auto', 'auto'] => {
    if (!data || data.length === 0) return ['auto', 'auto'];

    const values = data.map(d => {
      const dataObj = d.data || d;
      return dataObj[key];
    }).filter(v => typeof v === 'number' && !isNaN(v));
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

  // Get refresh mode icon and color
  const getRefreshModeDisplay = () => {
    const modes = {
      realtime: { icon: <Zap className="h-3 w-3" />, color: 'text-red-500' },
      normal: { icon: <Clock className="h-3 w-3" />, color: 'text-blue-500' },
      conservative: { icon: <Battery className="h-3 w-3" />, color: 'text-green-500' },
      manual: { icon: <Settings className="h-3 w-3" />, color: 'text-purple-500' },
    };
    return modes[refreshConfig.userPreference as keyof typeof modes] || modes.normal;
  };

  const modeDisplay = getRefreshModeDisplay();

  return (
    <div className={cn("w-full space-y-6", className)}>
      {/* Header with Smart Controls */}
      <div className="flex items-center justify-between">
        <div className="flex-1">
          {showTitle && <h2 className="text-2xl font-bold">Smart Telemetry Dashboard</h2>}
          <div className={cn("flex items-center gap-4", showTitle ? "mt-2" : "mt-0")}>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-muted-foreground">Select Device:</label>
              <Select
                value={selectedDevice?.device_id || selectedDevice?.id || ''}
                onValueChange={(deviceId) => {
                  const device = devices.find(d => d.device_id === deviceId || d.id === deviceId);
                  if (device) {
                    // CRITICAL: Clear ALL telemetry data immediately when switching devices
                    setTelemetryData([]);
                    
                    // Force a small delay to ensure state is cleared before setting new device
                    setTimeout(() => {
                      setSelectedDevice(device);
                      console.log('[SmartTelemetry] Device selected:', device.name, 'ID:', deviceId);
                    }, 10);
                    
                    // Reset WebSocket connection for new device if needed
                    if (useWebSocket && wsConnected && selectedDevice) {
                      const oldDeviceId = selectedDevice.device_id || selectedDevice.id;
                      console.log('[SmartTelemetry] Switching WebSocket subscription from', oldDeviceId, 'to', deviceId);
                      unsubscribeFromDevice(oldDeviceId);
                    }
                    
                    // If not using WebSocket or WebSocket is not connected, fetch initial data
                    if (!useWebSocket || wsConnectionStatus !== 'connected') {
                      setTimeout(() => {
                        fetchTelemetryData().catch(error => {
                          console.error('[SmartTelemetry] Failed to fetch data for new device:', error);
                        });
                      }, 100); // Small delay to allow state updates
                    }
                  }
                }}
              >
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Choose a device">
                    {selectedDevice ? (
                      <span className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          selectedDevice.status === 'online' ? 'bg-green-500' : 
                          selectedDevice.status === 'offline' ? 'bg-gray-400' : 
                          selectedDevice.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                        }`} />
                        {selectedDevice.name || selectedDevice.device_id}
                      </span>
                    ) : 'Select device...'}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {devices.length === 0 ? (
                    <SelectItem value="no-devices" disabled>
                      No devices available
                    </SelectItem>
                  ) : (
                    devices.map((device) => (
                      <SelectItem 
                        key={device.device_id || device.id} 
                        value={device.device_id || device.id}
                      >
                        <div className="flex items-center gap-2 w-full">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            device.status === 'online' ? 'bg-green-500' : 
                            device.status === 'offline' ? 'bg-gray-400' : 
                            device.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                          }`} />
                          <div className="flex flex-col">
                            <span className="font-medium">{device.name || device.device_id}</span>
                            <span className="text-xs text-muted-foreground">
                              {device.type} • {device.status}
                            </span>
                          </div>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span>{devices.length} device{devices.length !== 1 ? 's' : ''} available</span>
              {selectedDevice && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 rounded-md border border-blue-200">
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    isActive ? "bg-green-500 animate-pulse" : "bg-gray-400"
                  )} />
                  <span className="text-xs font-medium text-blue-700">
                    Auto-refresh: {currentInterval ? `${Math.round(currentInterval / 1000)}s` : '30s'}
                  </span>
                  {/* Hidden: (click ⏱️ to change) - Functionality remains in the popover button */}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* WebSocket Status Badge */}
          {useWebSocket && (
            <Badge 
              variant={wsConnectionStatus === 'connected' ? "default" : 
                      wsConnectionStatus === 'error' ? "destructive" : "outline"} 
              className="flex items-center gap-1"
            >
              {wsConnectionStatus === 'connected' && <Wifi className="h-3 w-3 text-green-500" />}
              {wsConnectionStatus === 'connecting' && <Radio className="h-3 w-3 animate-pulse" />}
              {wsConnectionStatus === 'error' && <AlertTriangle className="h-3 w-3" />}
              {wsConnectionStatus === 'disconnected' && <WifiOff className="h-3 w-3" />}
              <span className="text-xs">
                {wsConnectionStatus === 'connected' ? 'WebSocket Live' :
                 wsConnectionStatus === 'connecting' ? 'Connecting...' :
                 wsConnectionStatus === 'error' ? 'WS Error' : 'HTTP Mode'}
              </span>
            </Badge>
          )}
          
          {/* Refresh Status Badge */}
          <Badge variant="outline" className="flex items-center gap-1">
            <span className={cn("", modeDisplay.color)}>{modeDisplay.icon}</span>
            <span className="text-xs">
              {useWebSocket && wsConnectionStatus === 'connected' ? 'Real-time' : refreshMode}
            </span>
          </Badge>

          {/* WebSocket Toggle */}
          <Button
            variant={useWebSocket ? "default" : "outline"}
            size="sm"
            onClick={handleWebSocketToggle}
            className="flex items-center gap-1"
          >
            {useWebSocket ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
            <span className="text-xs">
              {useWebSocket ? 'WebSocket' : 'HTTP Only'}
            </span>
          </Button>

          {/* WebSocket Reconnect (only show when WebSocket is enabled but has error) */}
          {useWebSocket && wsConnectionStatus === 'error' && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleWebSocketReconnect}
              className="text-orange-600"
            >
              <Radio className="h-4 w-4 mr-1" />
              Reconnect
            </Button>
          )}

          {/* Refresh Interval Display & Quick Selector */}
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="min-w-[100px] justify-between hover:bg-blue-50"
              >
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  <span className="text-xs">
                    {currentInterval ? `${Math.round(currentInterval / 1000)}s` : '30s'}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground ml-1">▼</div>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-64" align="end">
              <div className="space-y-3">
                <h4 className="font-medium text-sm">Auto-Refresh Interval</h4>
                <div className="space-y-2">
                  {[
                    { label: 'Real-time (2s)', value: 'realtime', interval: 2 },
                    { label: 'Normal (10s)', value: 'normal', interval: 10 },
                    { label: 'Conservative (30s)', value: 'conservative', interval: 30 },
                    { label: 'Manual Only', value: 'manual', interval: 0 }
                  ].map((option) => (
                    <Button
                      key={option.value}
                      variant={refreshConfig.userPreference === option.value ? "default" : "ghost"}
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => {
                        const newConfig = { userPreference: option.value as any };
                        setRefreshConfig(newConfig);
                        updateConfig(newConfig);
                        localStorage.setItem('telemetryRefreshConfig', JSON.stringify(newConfig));
                        toast({
                          title: "Refresh Interval Updated",
                          description: `Auto-refresh set to ${option.label.toLowerCase()}`,
                        });
                      }}
                    >
                      <div className="flex items-center gap-2 w-full">
                        <div className={cn(
                          "w-2 h-2 rounded-full",
                          refreshConfig.userPreference === option.value ? "bg-blue-500" : "bg-gray-300"
                        )} />
                        <span className="flex-1 text-left">{option.label}</span>
                        <span className="text-xs text-muted-foreground">
                          {option.interval === 0 ? 'Off' : `${option.interval}s`}
                        </span>
                      </div>
                    </Button>
                  ))}
                </div>
                <div className="text-xs text-muted-foreground pt-2 border-t">
                  Current mode: <span className="font-medium capitalize">{refreshMode}</span>
                  {refreshMode === 'lowPerformance' && (
                    <div className="text-orange-600 mt-1">
                      ⚠️ Slow refresh due to performance
                    </div>
                  )}
                </div>
              </div>
            </PopoverContent>
          </Popover>

          {/* Manual Refresh Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={forceRefresh}
            disabled={isRefreshing}
            className="relative"
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
            {isRefreshing ? 'Updating...' : 'Refresh Now'}
            {useWebSocket && wsConnectionStatus === 'connected' && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
            )}
          </Button>

          {/* Play/Pause Toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (isActive || (useWebSocket && wsConnectionStatus === 'connected')) {
                pause();
                toast({
                  title: "Auto-refresh Paused",
                  description: "Click to resume automatic updates",
                });
              } else {
                resume();
                toast({
                  title: "Auto-refresh Started",
                  description: `Updates every ${Math.round(currentInterval / 1000)} seconds`,
                });
              }
            }}
            className={cn(
              (isActive || (useWebSocket && wsConnectionStatus === 'connected')) 
                ? "bg-green-50 border-green-200 text-green-700 hover:bg-green-100" 
                : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
            )}
          >
            {(isActive || (useWebSocket && wsConnectionStatus === 'connected')) ? 
              <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            {(isActive || (useWebSocket && wsConnectionStatus === 'connected')) ? 'Pause' : 'Start'}
          </Button>


          {/* Settings Popover */}
          <Popover open={showSettings} onOpenChange={setShowSettings}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-96 max-h-[80vh] overflow-y-auto" align="end">
              <div className="space-y-4">
                {/* WebSocket Settings */}
                <div className="border-b pb-3">
                  <h4 className="font-medium mb-2">Connection Mode</h4>
                  <div className="flex items-center gap-2 mb-2">
                    <Button
                      variant={useWebSocket ? "default" : "outline"}
                      size="sm"
                      onClick={handleWebSocketToggle}
                      className="flex items-center gap-1"
                    >
                      {useWebSocket ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                      WebSocket Real-time
                    </Button>
                    {useWebSocket && wsConnectionStatus === 'error' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleWebSocketReconnect}
                        className="text-orange-600"
                      >
                        <Radio className="h-3 w-3 mr-1" />
                        Retry
                      </Button>
                    )}
                  </div>
                  
                  {/* WebSocket Metrics */}
                  {useWebSocket && (
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div className="flex justify-between">
                        <span>Status:</span>
                        <span className={cn(
                          "font-medium",
                          wsConnectionStatus === 'connected' ? 'text-green-600' :
                          wsConnectionStatus === 'error' ? 'text-red-600' : 'text-orange-600'
                        )}>
                          {wsConnectionStatus}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Messages:</span>
                        <span>{webSocketMetrics.messagesReceived}</span>
                      </div>
                      {webSocketMetrics.reconnects > 0 && (
                        <div className="flex justify-between">
                          <span>Reconnects:</span>
                          <span>{webSocketMetrics.reconnects}</span>
                        </div>
                      )}
                      {lastWebSocketMessage && (
                        <div className="flex justify-between">
                          <span>Last Message:</span>
                          <span>{lastWebSocketMessage.toLocaleTimeString()}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* HTTP Polling Settings */}
                <div>
                  <h4 className="font-medium mb-2">HTTP Polling (Fallback)</h4>
                  <RefreshRateSettings
                    currentConfig={refreshConfig}
                    performanceMetrics={performanceMetrics}
                    refreshMode={refreshMode}
                    onConfigChange={handleConfigChange}
                    onSave={handleConfigSave}
                    onReset={handleConfigReset}
                    disabled={useWebSocket && wsConnectionStatus === 'connected'}
                  />
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Performance Monitor (Collapsible) */}
      {showPerformance && (
        <PerformanceMonitor
          metrics={performanceMetrics}
          refreshMode={refreshMode}
          currentInterval={currentInterval}
          compactMode={false}
          showCharts={true}
        />
      )}

      {/* Compact Performance Metrics */}
      {!showPerformance && (
        <PerformanceMonitor
          metrics={performanceMetrics}
          refreshMode={refreshMode}
          currentInterval={currentInterval}
          compactMode={true}
        />
      )}


      {/* Real-time Data Cards */}
      {dataFields.length > 0 ? (
        <div className="space-y-6">
          {/* Primary sensor values - show as cards */}
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
                  <Card key={field} className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      {getFieldIcon(field)}
                      <span className="text-sm font-medium capitalize">{field.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="text-2xl font-bold">
                      {getLatestValue(field)}
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      <Badge 
                        variant={useWebSocket && wsConnectionStatus === 'connected' ? "default" : "secondary"} 
                        className="text-xs flex items-center gap-1"
                      >
                        {useWebSocket && wsConnectionStatus === 'connected' ? (
                          <>
                            <Zap className="h-2 w-2" />
                            Live
                          </>
                        ) : (
                          <>
                            <Clock className="h-2 w-2" />
                            Historical
                          </>
                        )}
                      </Badge>
                      {useWebSocket && wsConnectionStatus === 'connected' && (
                        <Badge variant="outline" className="text-xs flex items-center gap-1">
                          <Wifi className="h-2 w-2" />
                          WebSocket
                        </Badge>
                      )}
                      {refreshMode === 'lowPerformance' && (
                        <Badge variant="destructive" className="text-xs">
                          Degraded
                        </Badge>
                      )}
                      {useWebSocket && wsConnectionStatus === 'error' && (
                        <Badge variant="destructive" className="text-xs">
                          WS Error
                        </Badge>
                      )}
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
            {!selectedDevice ? (
              <>
                <p className="text-lg font-medium mb-2">No Device Selected</p>
                <p className="text-sm mb-4">
                  Please select a device from the dropdown above to view telemetry data.
                </p>
                <div className="text-xs space-y-1">
                  <p>Available devices: {devices.length}</p>
                  {devices.length === 0 && (
                    <p className="text-red-500">No devices found. Please add devices first.</p>
                  )}
                </div>
              </>
            ) : (
              <>
                <p className="text-lg font-medium mb-2">No Telemetry Data Available</p>
                <p className="text-sm mb-4">
                  Device "{selectedDevice.name || selectedDevice.device_id}" hasn't sent any telemetry data yet.
                </p>
                <div className="text-xs space-y-1">
                  <p>Device ID: {selectedDevice.device_id}</p>
                  <p>Device Status: {selectedDevice.status}</p>
                  <p>Connection: {useWebSocket && wsConnectionStatus === 'connected' ? 'WebSocket (Real-time)' : `HTTP (${refreshMode})`}</p>
                  {useWebSocket && wsConnectionStatus === 'connected' ? (
                    <p>Status: Live streaming enabled</p>
                  ) : (
                    <p>Interval: {(currentInterval / 1000).toFixed(0)}s</p>
                  )}
                  {useWebSocket && wsConnectionStatus === 'error' && (
                    <p className="text-red-500">WebSocket Error - Using HTTP fallback</p>
                  )}
                </div>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={forceRefresh}
                    disabled={isRefreshing || !selectedDevice}
                  >
                    <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
                    Check Again
                  </Button>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {/* Historical Data Charts */}
      {dataFields.length > 0 && telemetryData.length > 1 && (
        <Tabs defaultValue="charts" className="w-full">
          <TabsList>
            <TabsTrigger value="charts">
              Historical Charts
              {useWebSocket && wsConnectionStatus === 'connected' && (
                <Badge variant="outline" className="ml-2 text-xs">
                  <Zap className="h-2 w-2 mr-1" />
                  Live Updates
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="data">Raw Data</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
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
                  <CardDescription>Historical trend for {field}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={telemetryData
                        .slice(0, 20)
                        .sort((a, b) => {
                          // Sort chronologically (oldest first for the chart)
                          // Timestamps are now normalized to ISO strings
                          const timeA = new Date(a.timestamp).getTime();
                          const timeB = new Date(b.timestamp).getTime();
                          return timeA - timeB; // Oldest first for chart display
                        })
                        .map(item => ({
                        ...item,
                        ...(item.data || {}),
                        // Convert ISO string timestamp to milliseconds for chart
                        timestamp: new Date(item.timestamp).getTime()
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="timestamp"
                          tickFormatter={(value) => {
                            if (!value) return '';
                            // Value is now always in milliseconds
                            const date = new Date(value);
                            return date.toLocaleTimeString();
                          }}
                        />
                        <YAxis domain={getSmartChartDomain(telemetryData.slice(0, 20), field)} />
                        <Tooltip 
                          labelFormatter={(value) => {
                            if (!value) return '';
                            const date = new Date(typeof value === 'number' && value < 10000000000 ? value * 1000 : value);
                            return date.toLocaleString();
                          }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey={field} 
                          stroke={`hsl(${index * 60 + 200}, 70%, 50%)`}
                          strokeWidth={2}
                          dot={{ r: 3 }}
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
                <CardTitle>Raw Telemetry Data</CardTitle>
                <CardDescription>Latest {telemetryData.length} records</CardDescription>
              </CardHeader>
              <CardContent>
                <RawDataPanel data={telemetryData} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="stats">
            <Card>
              <CardHeader>
                <CardTitle>Telemetry Statistics</CardTitle>
                <CardDescription>Data source and performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Total Records</p>
                    <p className="text-2xl font-bold">{telemetryData.length}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      {useWebSocket && wsConnectionStatus === 'connected' ? 'Connection' : 'Refresh Interval'}
                    </p>
                    <p className="text-2xl font-bold">
                      {useWebSocket && wsConnectionStatus === 'connected' ? 'WebSocket' : `${(currentInterval / 1000).toFixed(0)}s`}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      {useWebSocket && wsConnectionStatus === 'connected' ? 'Stream Mode' : 'Refresh Mode'}
                    </p>
                    <p className="text-2xl font-bold capitalize">
                      {useWebSocket && wsConnectionStatus === 'connected' ? 'Real-time' : refreshMode}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Avg Response Time</p>
                    <p className="text-2xl font-bold">{performanceMetrics.averageResponseTime.toFixed(0)}ms</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Error Rate</p>
                    <p className="text-2xl font-bold">{(performanceMetrics.errorRate * 100).toFixed(1)}%</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      {useWebSocket && wsConnectionStatus === 'connected' ? 'WS Messages' : 'Active Requests'}
                    </p>
                    <p className="text-2xl font-bold">
                      {useWebSocket && wsConnectionStatus === 'connected' ? webSocketMetrics.messagesReceived : performanceMetrics.activeRequests}
                    </p>
                  </div>
                  {useWebSocket && webSocketMetrics.reconnects > 0 && (
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">WS Reconnects</p>
                      <p className="text-2xl font-bold">{webSocketMetrics.reconnects}</p>
                    </div>
                  )}
                </div>

                {/* Data Source Information */}
                <div className="mt-6 pt-6 border-t">
                  <h4 className="text-sm font-medium text-muted-foreground mb-4">Data Source Information</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Primary Source</p>
                      <div className="flex items-center gap-2">
                        {useWebSocket && wsConnectionStatus === 'connected' ? (
                          <>
                            <Zap className="h-4 w-4 text-green-500" />
                            <span className="font-medium">Live MQTT Stream</span>
                          </>
                        ) : (
                          <>
                            <Clock className="h-4 w-4 text-blue-500" />
                            <span className="font-medium">Database (Historical)</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Data Freshness</p>
                      <div className="flex items-center gap-2">
                        {telemetryData.length > 0 && (
                          <span className="font-medium">
                            {(() => {
                              const latestData = telemetryData[telemetryData.length - 1];
                              const timestamp = latestData.timestamp || latestData.created_at;
                              if (!timestamp) return 'Unknown';
                              const age = Date.now() - new Date(timestamp).getTime();
                              if (age < 5000) return 'Real-time';
                              if (age < 60000) return `${Math.floor(age / 1000)}s ago`;
                              if (age < 3600000) return `${Math.floor(age / 60000)}m ago`;
                              return `${Math.floor(age / 3600000)}h ago`;
                            })()}
                          </span>
                        )}
                      </div>
                    </div>
                    {lastWebSocketMessage && (
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Last Live Update</p>
                        <span className="font-medium">
                          {new Date(lastWebSocketMessage).toLocaleTimeString()}
                        </span>
                      </div>
                    )}
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
