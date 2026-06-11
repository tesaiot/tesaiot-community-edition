/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TelemetryChartProps {
  data: any[];
  loading?: boolean;
  title?: string;
  description?: string;
}

export function TelemetryChart({
  data,
  loading = false,
  title = "Live Telemetry Data",
  description = "Real-time sensor data",
}: TelemetryChartProps) {
  // Generate fallback data if no real data available
  const generateFallbackData = () => {
    return Array.from({ length: 20 }, (_, i) => ({
      time: new Date(Date.now() - (19 - i) * 60000).toLocaleTimeString('en-US', { 
        hour: 'numeric',
        minute: '2-digit'
      }),
      temperature: 20 + Math.random() * 5,
      humidity: 60 + Math.random() * 10,
    }));
  };

  // Smart domain calculation for charts
  const getSmartChartDomain = (data: any[], key: string, padding = 0.1) => {
    if (!data || data.length === 0) return ['auto', 'auto'];
    
    const values = data.map(d => d[key]).filter(v => v !== undefined && v !== null);
    if (values.length === 0) return ['auto', 'auto'];
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const paddingAmount = range * padding;
    
    return [
      Math.floor((min - paddingAmount) * 10) / 10,
      Math.ceil((max + paddingAmount) * 10) / 10
    ];
  };

  const chartData = data.length > 0 ? data : generateFallbackData();

  return (
    <Card className="xl:col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{title}</span>
          <div className="flex items-center gap-2">
            {loading && <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />}
            <Badge variant={data.length > 0 ? "default" : "secondary"}>
              {data.length > 0 ? `${data.length} data points` : 'Demo data'}
            </Badge>
          </div>
        </CardTitle>
        <CardDescription>
          {data.length > 0 
            ? 'Real-time sensor data from virtual devices via VerneMQ'
            : 'Start virtual device simulator to see real data'
          }
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="temperature" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="temperature">Temperature</TabsTrigger>
            <TabsTrigger value="humidity">Humidity</TabsTrigger>
            <TabsTrigger value="combined">Combined</TabsTrigger>
          </TabsList>
          <TabsContent value="temperature" className="h-[250px] md:h-[300px] lg:h-[350px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '11px' }}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  style={{ fontSize: '11px' }}
                  domain={getSmartChartDomain(chartData, 'temperature')}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '6px'
                  }}
                  labelStyle={{ color: '#D1D5DB' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="temperature" 
                  stroke="#EF4444" 
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </TabsContent>
          <TabsContent value="humidity" className="h-[250px] md:h-[300px] lg:h-[350px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '11px' }}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  style={{ fontSize: '11px' }}
                  domain={getSmartChartDomain(chartData, 'humidity')}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '6px'
                  }}
                  labelStyle={{ color: '#D1D5DB' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="humidity" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={false}
                  animationDuration={300}
                />
              </LineChart>
            </ResponsiveContainer>
          </TabsContent>
          <TabsContent value="combined" className="h-[250px] md:h-[300px] lg:h-[350px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '11px' }}
                />
                <YAxis 
                  yAxisId="temp"
                  orientation="left"
                  stroke="#EF4444"
                  style={{ fontSize: '11px' }}
                  domain={getSmartChartDomain(chartData, 'temperature')}
                />
                <YAxis 
                  yAxisId="humid"
                  orientation="right"
                  stroke="#3B82F6"
                  style={{ fontSize: '11px' }}
                  domain={getSmartChartDomain(chartData, 'humidity')}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '6px'
                  }}
                  labelStyle={{ color: '#D1D5DB' }}
                />
                <Legend 
                  wrapperStyle={{ paddingTop: '10px' }}
                  iconType="line"
                />
                <Line 
                  yAxisId="temp"
                  type="monotone" 
                  dataKey="temperature" 
                  stroke="#EF4444" 
                  strokeWidth={2}
                  dot={false}
                  name="Temperature (°C)"
                />
                <Line 
                  yAxisId="humid"
                  type="monotone" 
                  dataKey="humidity" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={false}
                  name="Humidity (%)"
                />
              </LineChart>
            </ResponsiveContainer>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}