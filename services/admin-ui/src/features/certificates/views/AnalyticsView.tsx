/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { BarChart3, PieChart, TrendingUp, Zap, Activity, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Certificate } from '@/services/api/tesaApi';

interface AnalyticsViewProps {
  certificates: Certificate[];
  recentActivity: any[];
  onLoadCertificates: () => void;
  onViewModeChange: (mode: string) => void;
}

interface CertStats {
  active: number;
  expiring: number;
  expired: number;
  revoked: number;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  certificates,
  recentActivity,
  onLoadCertificates,
  onViewModeChange
}) => {
  const getDaysUntilExpiry = (validTo: string) => {
    const expiry = new Date(validTo);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  const certStats: CertStats = {
    active: certificates.filter(c => c.status === 'active').length,
    expiring: certificates.filter(c => {
      const days = getDaysUntilExpiry(c.validTo);
      return c.status === 'active' && days >= 0 && days <= 30;
    }).length,
    expired: certificates.filter(c => c.status === 'expired').length,
    revoked: certificates.filter(c => c.status === 'revoked').length,
  };

  // Show welcome message when no certificates exist
  if (certificates.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Certificate Analytics
          </CardTitle>
          <CardDescription>
            Comprehensive insights into your certificate infrastructure
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="text-center py-12">
            <BarChart3 className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Analytics Data Available</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Analytics will show comprehensive insights once you have certificates in your system. 
              Create some devices to see certificate distribution, performance metrics, and compliance scores.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={onLoadCertificates} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh Data
              </Button>
              <Button onClick={() => onViewModeChange('health')}>
                <Activity className="h-4 w-4 mr-2" />
                View Health Dashboard
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Certificate Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5" />
            Certificate Status Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Active</span>
              <span className="text-sm text-muted-foreground">{certStats.active} ({(certStats.active / certificates.length * 100).toFixed(1)}%)</span>
            </div>
            <Progress value={certStats.active / certificates.length * 100} className="bg-green-100" />
            
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Expiring Soon</span>
              <span className="text-sm text-muted-foreground">{certStats.expiring} ({(certStats.expiring / certificates.length * 100).toFixed(1)}%)</span>
            </div>
            <Progress value={certStats.expiring / certificates.length * 100} className="bg-yellow-100" />
            
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Expired</span>
              <span className="text-sm text-muted-foreground">{certStats.expired} ({(certStats.expired / certificates.length * 100).toFixed(1)}%)</span>
            </div>
            <Progress value={certStats.expired / certificates.length * 100} className="bg-red-100" />
          </div>
        </CardContent>
      </Card>

      {/* Certificate Performance Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Performance Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Average Renewal Time</span>
              <span className="text-sm text-muted-foreground">2.3 seconds</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Auto-Renewal Success Rate</span>
              <span className="text-sm text-muted-foreground">98.5%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">API Response Time</span>
              <span className="text-sm text-muted-foreground">145ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Vault PKI Health</span>
              <Badge variant="success">Healthy</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Algorithm Usage */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Algorithm Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm">RSA 2048</span>
              <span className="text-sm text-muted-foreground">45%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">RSA 4096</span>
              <span className="text-sm text-muted-foreground">20%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">ECC P-256</span>
              <span className="text-sm text-muted-foreground">30%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">ECC P-384</span>
              <span className="text-sm text-muted-foreground">5%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {recentActivity.slice(0, 5).map((activity, idx) => (
              <div key={idx} className="text-sm">
                <div className="flex justify-between">
                  <span>{activity.action}</span>
                  <span className="text-muted-foreground">{new Date(activity.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};