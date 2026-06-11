/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import {
  RefreshCw,
  Cpu,
  HardDrive,
  Activity,
  Wifi,
  Server,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { api } from '@/services/api/apiClient';
import { cn } from '@/lib/utils';

interface MetricData {
  current: number;
  average: number;
  min?: number;
  max?: number;
  error?: string;
  history?: [number, number][];
}

interface InfrastructureData {
  timestamp: string;
  droplet_id: string;
  period_minutes: number;
  metrics: {
    cpu?: MetricData;
    memory_used_percent?: MetricData & {
      total_gb?: number;
      used_gb?: number;
      available_gb?: number;
    };
    load_1?: MetricData;
    load_5?: MetricData;
    load_15?: MetricData;
    disk_read?: MetricData;
    disk_write?: MetricData;
    bandwidth_inbound_public?: MetricData;
    bandwidth_outbound_public?: MetricData;
  };
  summary: {
    cpu_percent: number;
    memory_percent: number;
    load_1min: number;
    load_5min: number;
    load_15min: number;
    disk_read_mbps: number;
    disk_write_mbps: number;
    bandwidth_in_mbps: number;
    bandwidth_out_mbps: number;
    status: 'healthy' | 'warning' | 'critical';
  };
}

interface InfrastructureMetricsProps {
  refreshInterval?: number;
  showCharts?: boolean;
  compact?: boolean;
}

// Mini sparkline chart component
const MiniChart: React.FC<{ data: [number, number][]; color: string; height?: number }> = ({
  data,
  color,
  height = 40
}) => {
  if (!data || data.length < 2) return null;

  const values = data.map(d => d[1]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = height - ((d[1] - min) / range) * (height - 4);
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width="100%" height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        points={points}
        className="opacity-70"
      />
      {/* Current value dot */}
      <circle
        cx="100%"
        cy={height - ((values[values.length - 1] - min) / range) * (height - 4)}
        r="3"
        fill={color}
      />
    </svg>
  );
};

export const InfrastructureMetrics: React.FC<InfrastructureMetricsProps> = ({
  refreshInterval = 60000,
  showCharts = true,
  compact = false
}) => {
  const [data, setData] = useState<InfrastructureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<InfrastructureData>('/api/v1/dashboard/infrastructure/metrics?period=60');
      setData(response);
      setLastUpdate(new Date());
    } catch (err: any) {
      console.error('Failed to fetch infrastructure metrics:', err);
      setError(err.message || 'Failed to load infrastructure metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchMetrics, refreshInterval]);

  const getStatusColor = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'text-red-500';
    if (value >= thresholds.warning) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getProgressColor = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'bg-red-500';
    if (value >= thresholds.warning) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading && !data) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4" />
            Infrastructure Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle className="h-10 w-10 text-yellow-500 mb-3" />
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" size="sm" className="mt-4" onClick={fetchMetrics}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = data?.summary;
  const metrics = data?.metrics;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4" />
            Infrastructure Metrics
          </CardTitle>
          <CardDescription className="text-xs mt-1">
            TESAIoT Platform - Real-time monitoring
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={summary?.status === 'healthy' ? 'default' : 'destructive'}
            className={cn(
              'text-xs',
              summary?.status === 'healthy' && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            )}
          >
            {summary?.status === 'healthy' ? (
              <><CheckCircle className="h-3 w-3 mr-1" /> Healthy</>
            ) : (
              <><AlertTriangle className="h-3 w-3 mr-1" /> Warning</>
            )}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchMetrics}
            disabled={loading}
            className="h-8 w-8"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className={cn('grid gap-4', compact ? 'grid-cols-2' : 'grid-cols-2 md:grid-cols-4')}>
          {/* CPU */}
          <div className="space-y-2 p-3 rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className={cn('h-4 w-4', getStatusColor(summary?.cpu_percent || 0, { warning: 70, critical: 90 }))} />
                <span className="text-sm font-medium">CPU</span>
              </div>
              <span className={cn('text-lg font-bold', getStatusColor(summary?.cpu_percent || 0, { warning: 70, critical: 90 }))}>
                {summary?.cpu_percent?.toFixed(1)}%
              </span>
            </div>
            <Progress
              value={summary?.cpu_percent || 0}
              className="h-2"
            />
            {showCharts && metrics?.cpu?.history && (
              <div className="h-10 mt-2">
                <MiniChart
                  data={metrics.cpu.history}
                  color={summary?.cpu_percent && summary.cpu_percent >= 70 ? '#ef4444' : '#22c55e'}
                />
              </div>
            )}
          </div>

          {/* Memory */}
          <div className="space-y-2 p-3 rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className={cn('h-4 w-4', getStatusColor(summary?.memory_percent || 0, { warning: 75, critical: 90 }))} />
                <span className="text-sm font-medium">Memory</span>
              </div>
              <span className={cn('text-lg font-bold', getStatusColor(summary?.memory_percent || 0, { warning: 75, critical: 90 }))}>
                {summary?.memory_percent?.toFixed(1)}%
              </span>
            </div>
            <Progress
              value={summary?.memory_percent || 0}
              className="h-2"
            />
            {metrics?.memory_used_percent && (
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>{metrics.memory_used_percent.used_gb?.toFixed(1)} GB used</span>
                <span>{metrics.memory_used_percent.total_gb?.toFixed(1)} GB total</span>
              </div>
            )}
          </div>

          {/* Load Average */}
          <div className="space-y-2 p-3 rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-medium">Load Avg</span>
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold">{summary?.load_1min?.toFixed(2)}</span>
              <span className="text-xs text-muted-foreground">1m</span>
              <span className="text-sm font-medium text-muted-foreground">{summary?.load_5min?.toFixed(2)}</span>
              <span className="text-xs text-muted-foreground">5m</span>
              <span className="text-sm font-medium text-muted-foreground">{summary?.load_15min?.toFixed(2)}</span>
              <span className="text-xs text-muted-foreground">15m</span>
            </div>
            {showCharts && metrics?.load_1?.history && (
              <div className="h-10 mt-2">
                <MiniChart
                  data={metrics.load_1.history}
                  color="#3b82f6"
                />
              </div>
            )}
          </div>

          {/* Network I/O */}
          <div className="space-y-2 p-3 rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wifi className="h-4 w-4 text-purple-500" />
                <span className="text-sm font-medium">Network</span>
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">↓ In</span>
                <span className="font-medium">{summary?.bandwidth_in_mbps?.toFixed(2)} Mbps</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">↑ Out</span>
                <span className="font-medium">{summary?.bandwidth_out_mbps?.toFixed(2)} Mbps</span>
              </div>
            </div>
            <div className="border-t border-border/50 pt-2 mt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Disk R/W</span>
                <span className="font-medium">
                  {summary?.disk_read_mbps?.toFixed(2)} / {summary?.disk_write_mbps?.toFixed(2)} MB/s
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Last update timestamp */}
        <div className="mt-4 pt-3 border-t border-border/50">
          <p className="text-xs text-muted-foreground text-center">
            Last updated: {lastUpdate.toLocaleTimeString()} • Auto-refresh every {refreshInterval / 1000}s
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default InfrastructureMetrics;
