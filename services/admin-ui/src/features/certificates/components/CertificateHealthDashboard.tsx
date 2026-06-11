/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Clock, 
  RefreshCw,
  Shield,
  Activity,
  TrendingUp,
  TrendingDown,
  Calendar,
  ShieldAlert,
  ShieldCheck,
  Info
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { tesaApi, Certificate } from '@/services/api/tesaApi';
import { toast } from 'sonner';

interface CertificateHealthDashboardProps {
  certificates: Certificate[];
  onRefresh: () => void;
  onRenew: (cert: Certificate) => void;
}

interface HealthMetrics {
  score: number;
  healthy: number;
  warning: number;
  critical: number;
  expired: number;
  expiringIn7Days: number;
  expiringIn30Days: number;
  expiringIn90Days: number;
  averageDaysToExpiry: number;
  renewalRecommended: Certificate[];
}

export const CertificateHealthDashboard: React.FC<CertificateHealthDashboardProps> = ({
  certificates,
  onRefresh,
  onRenew
}) => {
  const [loading, setLoading] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState<'7d' | '30d' | '90d'>('30d');

  // Calculate health metrics
  const healthMetrics = useMemo<HealthMetrics>(() => {
    const now = new Date();
    const metrics: HealthMetrics = {
      score: 100,
      healthy: 0,
      warning: 0,
      critical: 0,
      expired: 0,
      expiringIn7Days: 0,
      expiringIn30Days: 0,
      expiringIn90Days: 0,
      averageDaysToExpiry: 0,
      renewalRecommended: []
    };

    let totalDaysToExpiry = 0;
    let validCertCount = 0;

    certificates.forEach(cert => {
      const expiryDate = new Date(cert.validTo);
      const daysToExpiry = Math.floor((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

      if (cert.status === 'revoked') {
        // Revoked certificates don't affect health score
        return;
      }

      if (daysToExpiry < 0) {
        metrics.expired++;
        metrics.critical++;
        metrics.score -= 10; // Heavy penalty for expired certs
      } else if (daysToExpiry <= 7) {
        metrics.expiringIn7Days++;
        metrics.critical++;
        metrics.renewalRecommended.push(cert);
        metrics.score -= 5;
      } else if (daysToExpiry <= 30) {
        metrics.expiringIn30Days++;
        metrics.warning++;
        metrics.renewalRecommended.push(cert);
        metrics.score -= 2;
      } else if (daysToExpiry <= 90) {
        metrics.expiringIn90Days++;
        metrics.warning++;
        metrics.score -= 1;
      } else {
        metrics.healthy++;
        validCertCount++;
        totalDaysToExpiry += daysToExpiry;
      }

      if (daysToExpiry > 0) {
        validCertCount++;
        totalDaysToExpiry += daysToExpiry;
      }
    });

    metrics.averageDaysToExpiry = validCertCount > 0 ? Math.floor(totalDaysToExpiry / validCertCount) : 0;
    metrics.score = Math.max(0, metrics.score); // Ensure score doesn't go below 0

    return metrics;
  }, [certificates]);

  // Get health score color
  const getHealthScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 50) return 'text-orange-600';
    return 'text-red-600';
  };

  // Get health score badge
  const getHealthScoreBadge = (score: number) => {
    if (score >= 90) return { icon: ShieldCheck, text: 'Excellent', variant: 'success' as const };
    if (score >= 70) return { icon: Shield, text: 'Good', variant: 'warning' as const };
    if (score >= 50) return { icon: ShieldAlert, text: 'Fair', variant: 'warning' as const };
    return { icon: ShieldAlert, text: 'Critical', variant: 'destructive' as const };
  };

  const handleBulkRenewal = async () => {
    setLoading(true);
    let successCount = 0;
    let failCount = 0;

    for (const cert of healthMetrics.renewalRecommended) {
      try {
        await onRenew(cert);
        successCount++;
      } catch (error) {
        failCount++;
      }
    }

    setLoading(false);
    
    if (successCount > 0) {
      toast.success('Bulk Renewal Complete', {
        description: `Successfully renewed ${successCount} certificates${failCount > 0 ? `, ${failCount} failed` : ''}`
      });
    } else {
      toast.error('Bulk Renewal Failed', {
        description: 'Failed to renew certificates'
      });
    }

    onRefresh();
  };

  const healthBadge = getHealthScoreBadge(healthMetrics.score);
  const HealthIcon = healthBadge.icon;

  // Show welcome message when no certificates exist
  if (certificates.length === 0) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Certificate Health Overview
            </CardTitle>
            <CardDescription>
              Real-time monitoring of certificate health across your fleet
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <ShieldCheck className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Welcome to Certificate Management</h3>
              <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                No certificates found in your system yet. Create device certificates through Device Management 
                or use the Certificate Management tools to get started with PKI security.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button onClick={onRefresh} variant="outline">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh Certificates
                </Button>
                <Button onClick={() => window.location.href = '#/devices'}>
                  <Shield className="h-4 w-4 mr-2" />
                  Go to Device Management
                </Button>
              </div>
              <Alert className="mt-6 max-w-2xl mx-auto">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>Getting Started:</strong> Certificates are automatically generated when you create devices. 
                  Visit Device Management to create your first IoT device and its security certificates.
                </AlertDescription>
              </Alert>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Health Score Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Certificate Health Overview
              </CardTitle>
              <CardDescription>
                Real-time monitoring of certificate health across your fleet
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {/* Health Score */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Health Score</p>
                    <div className="flex items-center gap-2">
                      <span className={cn("text-3xl font-bold", getHealthScoreColor(healthMetrics.score))}>
                        {healthMetrics.score}
                      </span>
                      <span className="text-sm text-muted-foreground">/100</span>
                    </div>
                    <Badge variant={healthBadge.variant} className="mt-2">
                      <HealthIcon className="h-3 w-3 mr-1" />
                      {healthBadge.text}
                    </Badge>
                  </div>
                  <div className="relative h-24 w-24">
                    <svg className="transform -rotate-90 h-24 w-24">
                      <circle
                        cx="48"
                        cy="48"
                        r="36"
                        stroke="currentColor"
                        strokeWidth="8"
                        fill="none"
                        className="text-muted"
                      />
                      <circle
                        cx="48"
                        cy="48"
                        r="36"
                        stroke="currentColor"
                        strokeWidth="8"
                        fill="none"
                        strokeDasharray={`${(healthMetrics.score / 100) * 226} 226`}
                        className={getHealthScoreColor(healthMetrics.score)}
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <HealthIcon className={cn("h-8 w-8", getHealthScoreColor(healthMetrics.score))} />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Certificate Status */}
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground mb-3">Certificate Status</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Healthy</span>
                    </div>
                    <span className="font-semibold">{healthMetrics.healthy}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-600" />
                      <span className="text-sm">Warning</span>
                    </div>
                    <span className="font-semibold">{healthMetrics.warning}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-600" />
                      <span className="text-sm">Critical</span>
                    </div>
                    <span className="font-semibold">{healthMetrics.critical}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Expiration Timeline */}
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground mb-3">Expiration Timeline</p>
                <div className="space-y-3">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          className={cn(
                            "w-full text-left p-2 rounded-md transition-colors",
                            selectedTimeframe === '7d' ? 'bg-muted' : 'hover:bg-muted/50'
                          )}
                          onClick={() => setSelectedTimeframe('7d')}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm">7 days</span>
                            <Badge variant={healthMetrics.expiringIn7Days > 0 ? 'destructive' : 'secondary'}>
                              {healthMetrics.expiringIn7Days}
                            </Badge>
                          </div>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Certificates expiring within 7 days</p>
                      </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          className={cn(
                            "w-full text-left p-2 rounded-md transition-colors",
                            selectedTimeframe === '30d' ? 'bg-muted' : 'hover:bg-muted/50'
                          )}
                          onClick={() => setSelectedTimeframe('30d')}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm">30 days</span>
                            <Badge variant={healthMetrics.expiringIn30Days > 0 ? 'warning' : 'secondary'}>
                              {healthMetrics.expiringIn30Days}
                            </Badge>
                          </div>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Certificates expiring within 30 days</p>
                      </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          className={cn(
                            "w-full text-left p-2 rounded-md transition-colors",
                            selectedTimeframe === '90d' ? 'bg-muted' : 'hover:bg-muted/50'
                          )}
                          onClick={() => setSelectedTimeframe('90d')}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm">90 days</span>
                            <Badge variant="secondary">
                              {healthMetrics.expiringIn90Days}
                            </Badge>
                          </div>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Certificates expiring within 90 days</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </CardContent>
            </Card>

            {/* Average Days to Expiry */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-muted-foreground">Avg. Days to Expiry</p>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-4 w-4 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Average remaining validity period across all active certificates</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{healthMetrics.averageDaysToExpiry}</span>
                  <span className="text-sm text-muted-foreground">days</span>
                </div>
                <Progress 
                  value={(healthMetrics.averageDaysToExpiry / 365) * 100} 
                  className="mt-3"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  {healthMetrics.averageDaysToExpiry > 180 ? 'Healthy lifecycle' :
                   healthMetrics.averageDaysToExpiry > 90 ? 'Monitor closely' :
                   'Renewal planning needed'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Renewal Recommendations */}
          {healthMetrics.renewalRecommended.length > 0 && (
            <Alert className="mt-6">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="flex items-center justify-between">
                  <span>
                    {healthMetrics.renewalRecommended.length} certificate{healthMetrics.renewalRecommended.length > 1 ? 's' : ''} 
                    {' '}recommended for renewal
                  </span>
                  <Button 
                    size="sm" 
                    onClick={handleBulkRenewal}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Renewing...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Renew All
                      </>
                    )}
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Expiring Certificates List */}
      {selectedTimeframe && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Certificates Expiring in {selectedTimeframe === '7d' ? '7 Days' : selectedTimeframe === '30d' ? '30 Days' : '90 Days'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {certificates
                .filter(cert => {
                  const daysToExpiry = Math.floor(
                    (new Date(cert.validTo).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
                  );
                  if (selectedTimeframe === '7d') return daysToExpiry > 0 && daysToExpiry <= 7;
                  if (selectedTimeframe === '30d') return daysToExpiry > 0 && daysToExpiry <= 30;
                  return daysToExpiry > 0 && daysToExpiry <= 90;
                })
                .sort((a, b) => new Date(a.validTo).getTime() - new Date(b.validTo).getTime())
                .map(cert => {
                  const daysToExpiry = Math.floor(
                    (new Date(cert.validTo).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
                  );
                  return (
                    <div key={cert.id} className="flex items-center justify-between p-3 rounded-lg border">
                      <div>
                        <p className="font-medium">{cert.subject}</p>
                        <p className="text-sm text-muted-foreground">Device: {cert.deviceName}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={daysToExpiry <= 7 ? 'destructive' : daysToExpiry <= 30 ? 'warning' : 'secondary'}>
                          {daysToExpiry} days
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onRenew(cert)}
                        >
                          Renew
                        </Button>
                      </div>
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};