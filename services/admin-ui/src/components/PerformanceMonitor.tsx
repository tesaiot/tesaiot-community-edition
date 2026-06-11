/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PerformanceMetrics } from '@/hooks/useSmartRefreshRate';

interface PerformanceMonitorProps {
  metrics: PerformanceMetrics;
  refreshMode?: 'active' | 'background' | 'idle' | 'lowPerformance';
  currentInterval?: number;
  className?: string;
  showCharts?: boolean;
  compactMode?: boolean;
}

interface HistoricalData {
  timestamp: string;
  cpu: number;
  memory: number;
  responseTime: number;
  errorRate: number;
}

export function PerformanceMonitor({
  metrics,
  refreshMode = 'active',
  currentInterval = 30000,
  className,
  showCharts = true,
  compactMode = false,
}: PerformanceMonitorProps) {
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([]);
  const [trend, setTrend] = useState<{ cpu: 'up' | 'down' | 'stable', memory: 'up' | 'down' | 'stable' }>({
    cpu: 'stable',
    memory: 'stable',
  });
  
  const prevMetricsRef = useRef<PerformanceMetrics>(metrics);

  // Track historical data
  useEffect(() => {
    const newDataPoint: HistoricalData = {
      timestamp: new Date().toLocaleTimeString(),
      cpu: metrics.cpuUsage,
      memory: metrics.memoryUsage,
      responseTime: metrics.averageResponseTime,
      errorRate: metrics.errorRate * 100,
    };

    setHistoricalData((prev) => {
      const updated = [...prev, newDataPoint];
      // Keep only last 20 data points
      return updated.slice(-20);
    });

    // Calculate trends
    const cpuDiff = metrics.cpuUsage - prevMetricsRef.current.cpuUsage;
    const memDiff = metrics.memoryUsage - prevMetricsRef.current.memoryUsage;

    setTrend({
      cpu: cpuDiff > 5 ? 'up' : cpuDiff < -5 ? 'down' : 'stable',
      memory: memDiff > 5 ? 'up' : memDiff < -5 ? 'down' : 'stable',
    });

    prevMetricsRef.current = metrics;
  }, [metrics]);

  const getStatusColor = (value: number, threshold: number) => {
    if (value > threshold) return 'text-red-500';
    if (value > threshold * 0.75) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getProgressVariant = (value: number, threshold: number): 'default' | 'destructive' => {
    return value > threshold ? 'destructive' : 'default';
  };

  const formatInterval = (ms: number) => {
    if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`;
    return `${(ms / 60000).toFixed(0)}m`;
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3 w-3 text-red-500" />;
      case 'down':
        return <TrendingDown className="h-3 w-3 text-green-500" />;
      default:
        return <Minus className="h-3 w-3 text-gray-500" />;
    }
  };

  if (compactMode) {
    return (
      <div className={cn("grid grid-cols-2 lg:grid-cols-4 gap-3", className)}>
        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
          <Cpu className={cn("h-4 w-4", getStatusColor(metrics.cpuUsage, 80))} />
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">CPU</div>
            <div className="flex items-center gap-1">
              <span className="font-semibold">{metrics.cpuUsage.toFixed(0)}%</span>
              {getTrendIcon(trend.cpu)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
          <HardDrive className={cn("h-4 w-4", getStatusColor(metrics.memoryUsage, 85))} />
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Memory</div>
            <div className="flex items-center gap-1">
              <span className="font-semibold">{metrics.memoryUsage.toFixed(0)}%</span>
              {getTrendIcon(trend.memory)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
          <Wifi className="h-4 w-4 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Response</div>
            <span className="font-semibold">{metrics.averageResponseTime.toFixed(0)}ms</span>
          </div>
        </div>

        <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Mode</div>
            <Badge variant={refreshMode === 'lowPerformance' ? 'destructive' : 'secondary'} className="text-xs">
              {refreshMode}
            </Badge>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Performance Monitor
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Refresh: {formatInterval(currentInterval)}
            </Badge>
            <Badge 
              variant={refreshMode === 'lowPerformance' ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {refreshMode.replace(/([A-Z])/g, ' $1').trim()}
            </Badge>
          </div>
        </CardTitle>
        <CardDescription>
          Real-time system performance and resource utilization
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* CPU Usage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className={cn("h-4 w-4", getStatusColor(metrics.cpuUsage, 80))} />
                <span className="text-sm font-medium">CPU Usage</span>
                {getTrendIcon(trend.cpu)}
              </div>
              <span className={cn("text-sm font-bold", getStatusColor(metrics.cpuUsage, 80))}>
                {metrics.cpuUsage.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics.cpuUsage} 
              variant={getProgressVariant(metrics.cpuUsage, 80)}
              className="h-2"
            />
          </div>

          {/* Memory Usage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className={cn("h-4 w-4", getStatusColor(metrics.memoryUsage, 85))} />
                <span className="text-sm font-medium">Memory Usage</span>
                {getTrendIcon(trend.memory)}
              </div>
              <span className={cn("text-sm font-bold", getStatusColor(metrics.memoryUsage, 85))}>
                {metrics.memoryUsage.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics.memoryUsage} 
              variant={getProgressVariant(metrics.memoryUsage, 85)}
              className="h-2"
            />
          </div>

          {/* Response Time */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wifi className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Avg Response Time</span>
              </div>
              <span className={cn("text-sm font-bold", 
                metrics.averageResponseTime > 5000 ? 'text-red-500' : 
                metrics.averageResponseTime > 2000 ? 'text-yellow-500' : 
                'text-green-500'
              )}>
                {metrics.averageResponseTime.toFixed(0)}ms
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Active Requests: {metrics.activeRequests}</span>
            </div>
          </div>

          {/* Error Rate */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Error Rate</span>
              </div>
              <span className={cn("text-sm font-bold",
                metrics.errorRate > 0.1 ? 'text-red-500' :
                metrics.errorRate > 0.05 ? 'text-yellow-500' :
                'text-green-500'
              )}>
                {(metrics.errorRate * 100).toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics.errorRate * 100} 
              variant={getProgressVariant(metrics.errorRate * 100, 10)}
              className="h-2"
            />
          </div>
        </div>

        {/* Performance Charts */}
        {showCharts && historicalData.length > 1 && (
          <div className="space-y-4">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={historicalData}>
                  <defs>
                    <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                    </linearGradient>
                    <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    domain={[0, 100]}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'rgba(0, 0, 0, 0.8)',
                      border: 'none',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ fontSize: '12px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpu"
                    stroke="#3b82f6"
                    fill="url(#cpuGradient)"
                    strokeWidth={2}
                    name="CPU %"
                  />
                  <Area
                    type="monotone"
                    dataKey="memory"
                    stroke="#10b981"
                    fill="url(#memoryGradient)"
                    strokeWidth={2}
                    name="Memory %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historicalData}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                  />
                  <YAxis 
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'rgba(0, 0, 0, 0.8)',
                      border: 'none',
                      borderRadius: '8px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="responseTime"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={false}
                    name="Response (ms)"
                  />
                  <Line
                    type="monotone"
                    dataKey="errorRate"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                    name="Error %"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Performance Alerts */}
        {(metrics.cpuUsage > 80 || metrics.memoryUsage > 85 || metrics.errorRate > 0.1) && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">Performance Alert</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              System is experiencing high load. Refresh rates have been automatically adjusted.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}