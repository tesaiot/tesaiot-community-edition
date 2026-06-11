/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { 
  Wifi, 
  WifiOff, 
  Activity, 
  Shield, 
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Download,
  Settings,
  BarChart3,
  Clock,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { tesaApi } from '@/services/api/tesaApi';
import { getActivityLogsWebSocket } from '@/services/websocket/activityLogsWebSocket';
import { WS_EVENT_TYPES, SEVERITY_COLORS } from '@/constants/activityLogs';

interface DeviceHealthStats {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  devices_with_errors: number;
  connectivity_score: number;
  telemetry_score: number;
  security_score: number;
  overall_health: number;
}

interface DeviceLogEntry {
  device_id: string;
  device_name: string;
  category: string;
  severity: string;
  message: string;
  timestamp: string;
}

export const DeviceHealthOverview: React.FC = () => {
  const [stats, setStats] = useState<DeviceHealthStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDeviceHealth();
    const interval = setInterval(fetchDeviceHealth, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDeviceHealth = async () => {
    try {
      const response = await tesaApi.getDeviceHealthStats();
      // Safe access with fallback
      const statsData = response?.data || null;
      setStats(statsData);
      setError(null);
    } catch (error) {
      console.error('Failed to fetch device health stats:', error);
      // Set null on error to prevent crashes
      setStats(null);
      setError('Failed to load device health data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-500">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <Activity className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No device health data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const connectivityRate = (stats?.total_devices || 0) > 0 ? ((stats?.online_devices || 0) / (stats?.total_devices || 1)) * 100 : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Device Health Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Overall Health Score */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-500">Overall Health</span>
              <span className="text-2xl font-bold">
                {stats?.overall_health || 0}%
              </span>
            </div>
            <Progress value={stats?.overall_health || 0} className="h-2" />
          </div>

          {/* Device Status */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <p className="text-xs text-gray-500">Online Devices</p>
              <p className="text-lg font-semibold text-green-600">
                {stats?.online_devices || 0}/{stats?.total_devices || 0}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-gray-500">Connectivity Rate</p>
              <p className="text-lg font-semibold">
                {connectivityRate.toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Health Scores */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Wifi className="h-3 w-3" />
                Connectivity
              </span>
              <span className="text-xs font-medium">{stats?.connectivity_score || 0}%</span>
            </div>
            <Progress value={stats?.connectivity_score || 0} className="h-1" />

            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Activity className="h-3 w-3" />
                Telemetry
              </span>
              <span className="text-xs font-medium">{stats?.telemetry_score || 0}%</span>
            </div>
            <Progress value={stats?.telemetry_score || 0} className="h-1" />

            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Shield className="h-3 w-3" />
                Security
              </span>
              <span className="text-xs font-medium">{stats?.security_score || 0}%</span>
            </div>
            <Progress value={stats?.security_score || 0} className="h-1" />
          </div>

          {/* Error Count */}
          {(stats?.devices_with_errors || 0) > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
              <p className="text-xs text-red-600 dark:text-red-400 font-medium">
                {stats?.devices_with_errors || 0} device{(stats?.devices_with_errors || 0) > 1 ? 's' : ''} with errors
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export const RecentDeviceLogs: React.FC = () => {
  const [logs, setLogs] = useState<DeviceLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecentLogs();
    
    // Subscribe to real-time device logs
    const ws = getActivityLogsWebSocket();
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.DEVICE_LOG_NEW, (log) => {
      // Safe access with validation
      if (log && log.device_id) {
        setLogs(prev => [{
          device_id: log.device_id,
          device_name: log.device_name || log.device_id,
          category: log.category || 'general',
          severity: log.severity || log.level || 'info',
          message: log.message || '',
          timestamp: log.timestamp || new Date().toISOString()
        }, ...prev].slice(0, 10)); // Keep only latest 10
      }
    });

    return () => unsubscribe();
  }, []);

  const fetchRecentLogs = async () => {
    try {
      const response = await tesaApi.getRecentDeviceLogs({ limit: 10 });
      // Safe access with fallback to empty array
      const logsData = response?.data?.logs || [];
      setLogs(logsData);
      setError(null);
    } catch (error) {
      console.error('Failed to fetch recent device logs:', error);
      // Set empty array on error to prevent crashes
      setLogs([]);
      setError('Failed to load recent device logs');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    const severityLower = (severity || '').toLowerCase();
    switch (severityLower) {
      case 'critical':
      case 'error':
        return <XCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <CheckCircle className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-200 rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Recent Device Logs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-red-500 py-8">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Recent Device Logs
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px]">
          <div className="space-y-3">
            {logs.length > 0 ? (
              logs.map((log, index) => (
                <div
                  key={`${log.device_id}-${log.timestamp}-${index}`}
                  className="p-3 border rounded-lg space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {log.device_name || log.device_id || 'Unknown Device'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {log.message || 'No message'}
                      </p>
                    </div>
                    <div className={cn(
                      "p-1 rounded",
                      SEVERITY_COLORS[(log.severity || '').toLowerCase()]?.bg || 'bg-gray-100',
                      SEVERITY_COLORS[(log.severity || '').toLowerCase()]?.text || 'text-gray-600'
                    )}>
                      {getSeverityIcon(log.severity)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {log.category || 'general'}
                    </Badge>
                    <span className="text-xs text-gray-400">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Unknown time'}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Activity className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No recent device logs</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export const DeviceConnectivityStatus: React.FC = () => {
  const [connectionEvents, setConnectionEvents] = useState<any[]>([]);
  
  useEffect(() => {
    // Subscribe to device connectivity events
    const ws = getActivityLogsWebSocket();
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.DEVICE_CONNECTIVITY, (event) => {
      try {
        // Enhanced validation for safe access
        if (event && typeof event === 'object' && event.device_id) {
          setConnectionEvents(prev => {
            const newEvent = {
              ...event,
              device_name: event.device_name || event.device_id || 'Unknown Device',
              status: event.status || 'unknown',
              timestamp: event.timestamp || new Date().toISOString()
            };
            
            // Ensure prev is an array and filter out any invalid entries
            const validPrev = Array.isArray(prev) ? prev.filter(item => item && typeof item === 'object') : [];
            return [newEvent, ...validPrev].slice(0, 5);
          });
        }
      } catch (error) {
        console.warn('DeviceConnectivityStatus: Error processing WebSocket event:', error);
      }
    });

    return () => unsubscribe();
  }, []);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Wifi className="h-4 w-4" />
          Device Connectivity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {connectionEvents && connectionEvents.length > 0 ? (
            connectionEvents.filter(event => event && typeof event === 'object').map((event, index) => (
              <div key={index} className="flex items-center gap-3">
                {(event?.status || '').toLowerCase() === 'connected' ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-500" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium">{event?.device_name || 'Unknown Device'}</p>
                  <p className="text-xs text-gray-500">
                    {(event?.status || '').toLowerCase() === 'connected' ? 'Connected' : 'Disconnected'}
                  </p>
                </div>
                <span className="text-xs text-gray-400">
                  {event?.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'Unknown time'}
                </span>
              </div>
            ))
          ) : (
            <div className="text-center py-4 text-gray-500">
              <Wifi className="h-6 w-6 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No recent connectivity events</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export const DeviceCategoryBreakdown: React.FC = () => {
  const [breakdown, setBreakdown] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCategoryBreakdown();
  }, []);

  const fetchCategoryBreakdown = async () => {
    try {
      const response = await tesaApi.getDeviceLogCategoryBreakdown();
      // Safe access with fallback to empty object
      const breakdownData = response?.data?.breakdown || {};
      setBreakdown(breakdownData);
      setError(null);
    } catch (error) {
      console.error('Failed to fetch category breakdown:', error);
      // Set empty object on error to prevent crashes
      setBreakdown({});
      setError('Failed to load category breakdown');
    } finally {
      setLoading(false);
    }
  };

  const categoryIcons: Record<string, any> = {
    connectivity: Wifi,
    telemetry: Activity,
    health: TrendingUp,
    security: Shield,
    firmware: Download,
    configuration: Settings,
    performance: BarChart3
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-200 rounded"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Logs by Category
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-red-500 py-8">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const total = Object.values(breakdown || {}).reduce((sum, count) => sum + count, 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Logs by Category
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {breakdown && typeof breakdown === 'object' && Object.entries(breakdown).length > 0 ? (
            Object.entries(breakdown).filter(([category, count]) => 
              category && typeof category === 'string' && typeof count === 'number'
            ).map(([category, count]) => {
              const Icon = categoryIcons[category] || Activity;
              const percentage = total > 0 ? (Number(count) / total) * 100 : 0;
              
              return (
                <div key={category}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm flex items-center gap-2">
                      <Icon className="h-3 w-3" />
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </span>
                    <span className="text-sm font-medium">{count}</span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                </div>
              );
            })
          ) : (
            <div className="text-center py-4 text-gray-500">
              <BarChart3 className="h-6 w-6 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No log categories available</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};