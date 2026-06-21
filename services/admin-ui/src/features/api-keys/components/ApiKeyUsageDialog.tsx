/*
 * TESA IoT Platform
 * Copyright (c) 2024-2025 Assoc. Prof. Wiroon Sriborrirux (BDH Corporation)
 * Managed by: Thai Embedded Systems Association (TESA)
 *
 * License: TESA Collaboration License (TESA-COLLABORATION-2025)
 * SPDX-FileCopyrightText: 2024-2025 Wiroon Sriborrirux
 * SPDX-License-Identifier: LicenseRef-TESA-Collaboration-2025
 *
 * Notice:
 * - The Owner retains all rights. TESA is authorized to use, modify, and
 *   deploy the code to build the AIoT Foundation Platform.
 * - Public redistribution or sublicensing requires prior written consent from
 *   the Owner.
 * - See LICENSES/TESA-COLLABORATION-2025.txt for full terms.
 *
 * Contact: sriborrirux@gmail.com
 */

/**
 * Copyright (c) 2024-2025 Assoc. Prof. Wiroon Sriborrirux, BDH Corporation
 * Licensed under the Apache License, Version 2.0
 * Managed by: Thai Embedded Systems Association (TESA)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/**
 * TESA IoT Platform - API Key Usage Analytics Dialog
 * Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.
 * 
 * Licensed through: Thai Embedded Systems Association (TESA)
 *  * 
 * This component displays comprehensive usage analytics for API keys
 * including metrics, time-series charts, endpoint usage, and error analysis
 * 
 * Priority 1 Features Implemented:
 * - Key Metrics Dashboard
 * - Time Series Analytics  
 * - Endpoint Usage Breakdown
 * - Error Analysis
 * - Security Monitoring
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { authFetch } from '@/utils/auth-fetch';
import { toast } from 'sonner';
import { 
  Activity, 
  TrendingUp, 
  AlertCircle, 
  Clock,
  BarChart3,
  Zap,
  RefreshCw,
  Download,
  CheckCircle,
  AlertTriangle,
  Globe,
  Shield
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts';
import { format, parseISO } from 'date-fns';

interface ApiKeyUsageDialogProps {
  keyId: string;
  keyName?: string;
  organizationId: string;
  onClose: () => void;
}

// Updated interfaces for Priority 1 features
interface MetricsData {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
  rate_limit_hits: number;
  data_transfer_mb: number;
  unique_ips: number;
  last_used: string | null;
  created_at: string;
  expires_at: string;
  is_active: boolean;
  name: string;
}

interface TimeSeriesPoint {
  timestamp: string;
  requests: number;
  errors: number;
  response_time: number;
  rate_limit_hits: number;
}

interface EndpointUsage {
  endpoint: string;
  method: string;
  count: number;
  avg_response_time: number;
  error_rate: number;
  min_response_time: number;
  max_response_time: number;
  p95_response_time: number;
}

interface ErrorBreakdown {
  status_code: number;
  message: string;
  count: number;
  percentage: number;
  error_messages: string[];
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6'];

export function ApiKeyUsageDialog({
  keyId,
  keyName = 'API Key',
  organizationId,
  onClose,
}: ApiKeyUsageDialogProps) {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState('24h');
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data states for Priority 1 features
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesPoint[]>([]);
  const [endpoints, setEndpoints] = useState<EndpointUsage[]>([]);
  const [errors, setErrors] = useState<ErrorBreakdown[]>([]);

  // Fetch all Priority 1 data endpoints
  const fetchData = async (showLoader = true) => {
    if (showLoader) setLoading(true);
    else setRefreshing(true);

    try {
      // Parallel fetch for better performance
      const [metricsRes, timeSeriesRes, endpointsRes, errorsRes] = await Promise.all([
        authFetch(`/api/v1/organizations/${organizationId}/api-keys/${keyId}/metrics?range=${timeRange}`),
        authFetch(`/api/v1/organizations/${organizationId}/api-keys/${keyId}/timeseries?range=${timeRange}`),
        authFetch(`/api/v1/organizations/${organizationId}/api-keys/${keyId}/endpoints?range=${timeRange}&limit=10`),
        authFetch(`/api/v1/organizations/${organizationId}/api-keys/${keyId}/errors?range=${timeRange}`)
      ]);

      // Process responses
      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        setMetrics(metricsData);
      }
      
      if (timeSeriesRes.ok) {
        const timeSeriesData = await timeSeriesRes.json();
        setTimeSeries(timeSeriesData.data || []);
      }
      
      if (endpointsRes.ok) {
        const endpointsData = await endpointsRes.json();
        setEndpoints(endpointsData.endpoints || []);
      }
      
      if (errorsRes.ok) {
        const errorsData = await errorsRes.json();
        setErrors(errorsData.errors || []);
      }
    } catch (error) {
      console.error('Error fetching usage data:', error);
      toast.error('Failed to load usage analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (keyId) {
      fetchData();
    }
  }, [keyId, timeRange]);

  // Helper functions
  const handleRefresh = () => fetchData(false);
  
  const handleExport = () => {
    const exportData = {
      metrics, timeSeries, endpoints, errors,
      exported_at: new Date().toISOString(),
      time_range: timeRange,
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `api-key-usage-${keyId}-${timeRange}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Usage data exported successfully');
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return format(parseISO(timestamp), 'MMM dd, HH:mm');
    } catch {
      return timestamp;
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  // Loading state
  if (loading) {
    return (
      <Dialog open={true} onOpenChange={onClose}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Loading Usage Analytics...</DialogTitle>
            <DialogDescription>
              Fetching usage data for API key
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 p-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            API Key Usage Analytics
          </DialogTitle>
          <DialogDescription>
            Usage statistics for "{keyName}"
          </DialogDescription>
        </DialogHeader>

        {/* Controls */}
        <div className="flex items-center justify-between gap-4 py-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
            >
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
          </div>
        </div>

        {/* Tabs for Priority 1 Features */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
            <TabsTrigger value="errors">Errors</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
          </TabsList>

          {/* Overview Tab - Priority 1: Key Metrics & Time Series */}
          <TabsContent value="overview" className="space-y-4">
            {/* Metrics Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatNumber(metrics?.total_requests || 0)}</div>
                  <p className="text-xs text-muted-foreground">
                    {metrics?.last_used ? `Last used ${formatTimestamp(metrics.last_used)}` : 'Never used'}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                  <CheckCircle className="h-4 w-4 text-green-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.success_rate || 100}%</div>
                  <Progress value={metrics?.success_rate || 100} className="mt-2" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
                  <Zap className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.avg_response_time || 0}ms</div>
                  <p className="text-xs text-muted-foreground">
                    P95: {metrics?.p95_response_time || 0}ms
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Rate Limit Hits</CardTitle>
                  <AlertTriangle className="h-4 w-4 text-orange-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.rate_limit_hits || 0}</div>
                  <p className="text-xs text-muted-foreground">
                    {metrics?.unique_ips || 0} unique IPs
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Time Series Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Request Volume Over Time</CardTitle>
                <CardDescription>
                  Successful and failed requests over the selected time period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={timeSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={formatTimestamp}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis />
                    <Tooltip 
                      labelFormatter={formatTimestamp}
                      formatter={(value: number) => formatNumber(value)}
                    />
                    <Area
                      type="monotone"
                      dataKey="requests"
                      stackId="1"
                      stroke="#10b981"
                      fill="#10b981"
                      fillOpacity={0.6}
                      name="Successful"
                    />
                    <Area
                      type="monotone"
                      dataKey="errors"
                      stackId="1"
                      stroke="#ef4444"
                      fill="#ef4444"
                      fillOpacity={0.6}
                      name="Errors"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Response Time Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Response Time Trend</CardTitle>
                <CardDescription>
                  Average response time over the selected period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={timeSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={formatTimestamp}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis />
                    <Tooltip 
                      labelFormatter={formatTimestamp}
                      formatter={(value: number) => `${value}ms`}
                    />
                    <Line
                      type="monotone"
                      dataKey="response_time"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                      name="Avg Response Time"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Endpoints Tab - Priority 1: Endpoint Usage Breakdown */}
          <TabsContent value="endpoints" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Top API Endpoints</CardTitle>
                <CardDescription>
                  Most frequently accessed endpoints
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {endpoints.map((endpoint, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{endpoint.method}</Badge>
                          <span className="font-mono text-sm">{endpoint.endpoint}</span>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {formatNumber(endpoint.count)} requests
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Avg: {endpoint.avg_response_time}ms</span>
                        <span>P95: {endpoint.p95_response_time}ms</span>
                        <span>Error rate: {endpoint.error_rate}%</span>
                      </div>
                      <Progress value={(endpoint.count / (endpoints[0]?.count || 1)) * 100} />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Errors Tab - Priority 1: Error Analysis */}
          <TabsContent value="errors" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Error Breakdown</CardTitle>
                <CardDescription>
                  Distribution of error status codes
                </CardDescription>
              </CardHeader>
              <CardContent>
                {errors.length > 0 ? (
                  <div className="space-y-4">
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie
                          data={errors}
                          dataKey="count"
                          nameKey="message"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          label={(entry) => `${entry.status_code}: ${entry.percentage}%`}
                        >
                          {errors.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                    
                    <div className="space-y-2">
                      {errors.map((error, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg border">
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                            />
                            <Badge variant={error.status_code >= 500 ? 'destructive' : 'secondary'}>
                              {error.status_code}
                            </Badge>
                            <span className="text-sm">{error.message}</span>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatNumber(error.count)} ({error.percentage}%)
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      No errors recorded in the selected time period
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab - Priority 1: Security Monitoring */}
          <TabsContent value="security" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Security Overview</CardTitle>
                <CardDescription>
                  API key security status and access patterns
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Key Status</div>
                    <Badge variant={metrics?.is_active ? 'default' : 'destructive'}>
                      {metrics?.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Expiration</div>
                    <p className="text-sm">
                      {metrics?.expires_at ? formatTimestamp(metrics.expires_at) : 'Never expires'}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Unique IPs</div>
                    <p className="text-sm">{metrics?.unique_ips || 0} different IP addresses</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Data Transfer</div>
                    <p className="text-sm">{metrics?.data_transfer_mb || 0} MB</p>
                  </div>
                </div>

                {metrics?.rate_limit_hits && metrics.rate_limit_hits > 0 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      This API key hit rate limits {metrics.rate_limit_hits} times in the selected period.
                      Consider increasing the rate limit if legitimate usage.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}