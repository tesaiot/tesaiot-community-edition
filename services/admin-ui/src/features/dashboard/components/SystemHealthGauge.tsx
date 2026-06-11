/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { SystemHealth } from '@/services/api/tesaApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';

interface SystemHealthGaugeProps {
  health: SystemHealth | null;
}

export const SystemHealthGauge: React.FC<SystemHealthGaugeProps> = ({ health }) => {
  if (!health) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  const getHealthScore = () => {
    if (!health.services) return 0;
    const totalServices = Object.keys(health.services).length;
    const healthyServices = Object.values(health.services).filter(
      (service) => service.status === 'healthy'
    ).length;
    return totalServices > 0 ? (healthyServices / totalServices) * 100 : 0;
  };

  const getHealthStatus = (score: number) => {
    if (score >= 90) return { label: 'Excellent', color: 'green', icon: CheckCircle };
    if (score >= 70) return { label: 'Good', color: 'yellow', icon: Activity };
    return { label: 'Critical', color: 'red', icon: AlertTriangle };
  };

  const healthScore = getHealthScore();
  const healthStatus = getHealthStatus(healthScore);
  const StatusIcon = healthStatus.icon;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gray-100">
            <StatusIcon 
              className={`h-12 w-12 ${
                healthStatus.color === 'green' ? 'text-green-500' :
                healthStatus.color === 'yellow' ? 'text-yellow-500' :
                'text-red-500'
              }`} 
            />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold">{Math.round(healthScore)}%</div>
            <Badge 
              variant={
                healthStatus.color === 'green' ? 'default' :
                healthStatus.color === 'yellow' ? 'secondary' :
                'destructive'
              }
              className="mt-1"
            >
              {healthStatus.label}
            </Badge>
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-sm font-medium">Service Status</div>
          {health.services && Object.entries(health.services).map(([name, service]) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-sm capitalize">{name}</span>
              <Badge
                variant={service.status === 'healthy' ? 'default' : 'destructive'}
                className="text-xs"
              >
                {service.status}
              </Badge>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Overall Health</span>
            <span>{Math.round(healthScore)}%</span>
          </div>
          <Progress value={healthScore} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
};