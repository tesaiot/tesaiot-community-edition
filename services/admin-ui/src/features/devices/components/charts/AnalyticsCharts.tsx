/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface AnalyticsChartsProps {
  device?: any;
}

export function AnalyticsCharts({ device }: AnalyticsChartsProps) {
  // Generate signal strength data
  const generateSignalData = () => {
    return Array.from({ length: 12 }, (_, i) => ({
      time: `${i * 2}:00`,
      signal: -50 - Math.random() * 30,
    }));
  };

  const messageDistributionData = [
    { name: 'Telemetry', value: 65, fill: '#3B82F6' },
    { name: 'Status', value: 20, fill: '#10B981' },
    { name: 'Alerts', value: 10, fill: '#F59E0B' },
    { name: 'Errors', value: 5, fill: '#EF4444' }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Message Distribution</CardTitle>
          <CardDescription>Breakdown by message type</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={messageDistributionData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              />
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Connection Quality</CardTitle>
          <CardDescription>Signal strength over time</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={generateSignalData()}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" domain={[-100, -40]} />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="signal" 
                stroke="#10B981" 
                fill="#10B981" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}