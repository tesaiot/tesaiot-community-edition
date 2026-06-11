/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Activity, 
  AlertCircle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  Cpu,
  HardDrive,
  Wifi,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { tesaApi } from '@/services/api/tesaApi';
import { useDeviceHealthWebSocket } from '@/hooks/useDeviceHealthWebSocket';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

interface DeviceHealthScore {
  score: number;
  status: 'healthy' | 'warning' | 'critical' | 'offline';
  lastUpdated: string;
  components: {
    connectivity: number;
    performance: number;
    reliability: number;
    security: number;
  };
}

interface HealthTrend {
  timestamp: string;
  score: number;
  cpu: number;
  memory: number;
  network: number;
}

interface ErrorPattern {
  id: string;
  pattern: string;
  frequency: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  firstOccurrence: string;
  lastOccurrence: string;
  affectedDevices: number;
  recommendation?: string;
}

interface DeviceHealthDashboardProps {
  deviceId?: string;
  className?: string;
}

export const DeviceHealthDashboard: React.FC<DeviceHealthDashboardProps> = ({ 
  deviceId, 
  className 
}) => {
  const [healthScore, setHealthScore] = useState<DeviceHealthScore | null>(null);
  const [healthTrends, setHealthTrends] = useState<HealthTrend[]>([]);
  const [errorPatterns, setErrorPatterns] = useState<ErrorPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Use WebSocket hook for real-time updates
  const { isConnected, subscribe } = useDeviceHealthWebSocket();

  useEffect(() => {
    fetchDeviceHealth();
    fetchHealthTrends();
    fetchErrorPatterns();

    // Subscribe to real-time health updates
    const unsubscribeHealth = subscribe('device:health:update', (data) => {
      if (!deviceId || data.deviceId === deviceId) {
        setHealthScore(data.healthScore);
      }
    });

    const unsubscribeTrends = subscribe('device:health:trends', (data) => {
      if (!deviceId || data.deviceId === deviceId) {
        setHealthTrends(prev => [...prev.slice(-23), data.trend]);
      }
    });

    const unsubscribePatterns = subscribe('device:error:pattern', (data) => {
      if (!deviceId || data.deviceId === deviceId) {
        setErrorPatterns(prev => {
          const exists = prev.find(p => p.id === data.pattern.id);
          if (exists) {
            return prev.map(p => p.id === data.pattern.id ? data.pattern : p);
          }
          return [data.pattern, ...prev].slice(0, 5);
        });
      }
    });

    return () => {
      unsubscribeHealth();
      unsubscribeTrends();
      unsubscribePatterns();
    };
  }, [deviceId]);

  const fetchDeviceHealth = async () => {
    try {
      const response = await tesaApi.getDeviceHealthScore(deviceId);
      setHealthScore(response);
    } catch (error) {
      console.error('Failed to fetch device health:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealthTrends = async () => {
    try {
      const response = await tesaApi.getDeviceHealthTrends({
        deviceId,
        timeRange: '24h',
        interval: '1h'
      });
      setHealthTrends(response.trends);
    } catch (error) {
      console.error('Failed to fetch health trends:', error);
    }
  };

  const fetchErrorPatterns = async () => {
    try {
      const response = await tesaApi.getDeviceErrorPatterns({
        deviceId,
        limit: 5
      });
      setErrorPatterns(response.patterns);
    } catch (error) {
      console.error('Failed to fetch error patterns:', error);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      fetchDeviceHealth(),
      fetchHealthTrends(),
      fetchErrorPatterns()
    ]);
    setRefreshing(false);
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 40) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getHealthBadge = (status: string) => {
    const variants: Record<string, string> = {
      healthy: 'default',
      warning: 'warning',
      critical: 'destructive',
      offline: 'secondary'
    };
    return variants[status] || 'default';
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      low: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
      medium: 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300',
      high: 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300',
      critical: 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300'
    };
    return colors[severity] || colors.low;
  };

  return (
    <div className={cn("grid gap-4", className)}>
      {/* Health Score Card */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Device Health Score
            </CardTitle>
            <div className="flex items-center gap-2">
              {isConnected && (
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-gray-500">Live</span>
                </div>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={handleRefresh}
                disabled={refreshing}
                className="h-8 px-2"
              >
                <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              <div className="animate-pulse">
                <div className="h-24 bg-gray-200 dark:bg-gray-800 rounded-lg" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-16 bg-gray-200 dark:bg-gray-800 rounded" />
                  </div>
                ))}
              </div>
            </div>
          ) : healthScore ? (
            <div className="space-y-4">
              {/* Main Score Display */}
              <div className="text-center py-4">
                <div className={cn("text-5xl font-bold mb-2", getHealthColor(healthScore.score))}>
                  {healthScore.score}%
                </div>
                <Badge variant={getHealthBadge(healthScore.status) as any} className="mb-2">
                  {healthScore.status.toUpperCase()}
                </Badge>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Last updated: {format(new Date(healthScore.lastUpdated), 'HH:mm:ss')}
                </p>
              </div>

              {/* Component Scores */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Wifi className="h-3 w-3" />
                      Connectivity
                    </span>
                    <span className="text-sm">{healthScore.components.connectivity}%</span>
                  </div>
                  <Progress value={healthScore.components.connectivity} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Cpu className="h-3 w-3" />
                      Performance
                    </span>
                    <span className="text-sm">{healthScore.components.performance}%</span>
                  </div>
                  <Progress value={healthScore.components.performance} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <HardDrive className="h-3 w-3" />
                      Reliability
                    </span>
                    <span className="text-sm">{healthScore.components.reliability}%</span>
                  </div>
                  <Progress value={healthScore.components.reliability} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" />
                      Security
                    </span>
                    <span className="text-sm">{healthScore.components.security}%</span>
                  </div>
                  <Progress value={healthScore.components.security} className="h-2" />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <AlertCircle className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No health data available
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Health Trend Chart */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Health Trends (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={healthTrends}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(value) => format(new Date(value), 'HH:mm')}
                  stroke="#6b7280"
                />
                <YAxis stroke="#6b7280" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.9)', 
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
                  labelFormatter={(value) => format(new Date(value), 'HH:mm:ss')}
                />
                <Area 
                  type="monotone" 
                  dataKey="score" 
                  stroke="#3b82f6" 
                  fillOpacity={1} 
                  fill="url(#colorScore)" 
                  name="Health Score"
                />
                <Area 
                  type="monotone" 
                  dataKey="cpu" 
                  stroke="#10b981" 
                  fillOpacity={1} 
                  fill="url(#colorCpu)" 
                  name="CPU Usage"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Error Pattern Detection */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Error Pattern Detection
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[300px] pr-4">
            {errorPatterns.length > 0 ? (
              <div className="space-y-3">
                {errorPatterns.map((pattern) => (
                  <div
                    key={pattern.id}
                    className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium">{pattern.pattern}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="secondary" className={cn("text-xs", getSeverityColor(pattern.severity))}>
                            {pattern.severity}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            {pattern.frequency} occurrences
                          </span>
                          {pattern.affectedDevices > 1 && (
                            <span className="text-xs text-gray-500">
                              • {pattern.affectedDevices} devices
                            </span>
                          )}
                        </div>
                      </div>
                      {pattern.frequency > 10 && (
                        <TrendingUp className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                    {pattern.recommendation && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                        💡 {pattern.recommendation}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      First seen: {format(new Date(pattern.firstOccurrence), 'MMM dd, HH:mm')}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-8">
                <CheckCircle className="h-12 w-12 text-green-500 mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No error patterns detected
                </p>
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};