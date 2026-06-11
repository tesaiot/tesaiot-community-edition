/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Shield, Info, AlertCircle, Lock, CheckCircle, RefreshCw } from 'lucide-react';
import { api } from '@/services/api/apiClient';
import { useWebSocket } from '@/hooks/useWebSocket';
import { showNotification } from '@/utils/notifications';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

// Security Analytics Types
interface RBACViolation {
  id: string;
  user_id: string;
  user_email: string;
  attempted_action: string;
  resource: string;
  timestamp: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  details?: string;
}

interface ThreatMetrics {
  anomaly_score: number;
  suspicious_activities: number;
  blocked_attempts: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

interface ComplianceAlert {
  id: string;
  type: 'ETSI_EN_303_645' | 'ISO_IEC_27402' | 'GDPR' | 'CUSTOM';
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  timestamp: string;
  action_required?: string;
}

interface CertificateWarning {
  id: string;
  device_id: string;
  device_name: string;
  certificate_cn: string;
  expiry_date: string;
  days_until_expiry: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

interface SecurityAnalytics {
  rbac_violations: RBACViolation[];
  threat_detection: ThreatMetrics;
  compliance_alerts: ComplianceAlert[];
  certificate_warnings: CertificateWarning[];
  failed_auth_attempts: {
    count: number;
    recent_attempts: Array<{
      username: string;
      ip_address: string;
      timestamp: string;
      reason: string;
    }>;
  };
}

interface SecurityAlert {
  id: string;
  type: 'rbac' | 'auth' | 'certificate' | 'compliance' | 'threat';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  message: string;
  timestamp: string;
  details?: any;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface SecurityAlertsProps {
  enhanced?: boolean;
  maxAlerts?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onAlertClick?: (alert: SecurityAlert) => void;
}

export const SecurityAlerts: React.FC<SecurityAlertsProps> = ({ 
  enhanced = false,
  maxAlerts = 10,
  autoRefresh = true,
  refreshInterval = 30000,
  onAlertClick
}) => {
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const refreshTimerRef = useRef<NodeJS.Timeout>();

  // WebSocket URL construction
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}://${window.location.host}/ws/security-analytics`;
  const { data: wsData, isConnected } = useWebSocket<SecurityAnalytics>(wsUrl);

  // Convert security analytics data to alerts
  const convertToAlerts = (data: SecurityAnalytics): SecurityAlert[] => {
    const alerts: SecurityAlert[] = [];

    // RBAC Violations
    data.rbac_violations.forEach(violation => {
      alerts.push({
        id: `rbac-${violation.id}`,
        type: 'rbac',
        severity: violation.severity,
        title: 'RBAC Violation Detected',
        message: `User ${violation.user_email} attempted unauthorized action: ${violation.attempted_action}`,
        timestamp: violation.timestamp,
        details: violation,
        action: {
          label: 'View Details',
          onClick: () => onAlertClick?.({
            id: `rbac-${violation.id}`,
            type: 'rbac',
            severity: violation.severity,
            title: 'RBAC Violation Detected',
            message: `User ${violation.user_email} attempted unauthorized action: ${violation.attempted_action}`,
            timestamp: violation.timestamp,
            details: violation
          })
        }
      });
    });

    // Failed Authentication Attempts
    if (data.failed_auth_attempts.count > 0) {
      const severity = data.failed_auth_attempts.count > 10 ? 'high' : 
                      data.failed_auth_attempts.count > 5 ? 'medium' : 'low';
      alerts.push({
        id: 'auth-failures',
        type: 'auth',
        severity,
        title: 'Failed Authentication Attempts',
        message: `${data.failed_auth_attempts.count} failed login attempts detected`,
        timestamp: new Date().toISOString(),
        details: data.failed_auth_attempts,
        action: {
          label: 'Review Attempts',
          onClick: () => onAlertClick?.({
            id: 'auth-failures',
            type: 'auth',
            severity,
            title: 'Failed Authentication Attempts',
            message: `${data.failed_auth_attempts.count} failed login attempts detected`,
            timestamp: new Date().toISOString(),
            details: data.failed_auth_attempts
          })
        }
      });
    }

    // Certificate Warnings
    data.certificate_warnings.forEach(warning => {
      alerts.push({
        id: `cert-${warning.id}`,
        type: 'certificate',
        severity: warning.severity,
        title: 'Certificate Expiry Warning',
        message: `Certificate for ${warning.device_name} expires in ${warning.days_until_expiry} days`,
        timestamp: new Date().toISOString(),
        details: warning,
        action: {
          label: 'Renew Certificate',
          onClick: () => onAlertClick?.({
            id: `cert-${warning.id}`,
            type: 'certificate',
            severity: warning.severity,
            title: 'Certificate Expiry Warning',
            message: `Certificate for ${warning.device_name} expires in ${warning.days_until_expiry} days`,
            timestamp: new Date().toISOString(),
            details: warning
          })
        }
      });
    });

    // Compliance Alerts
    data.compliance_alerts.forEach(alert => {
      alerts.push({
        id: `compliance-${alert.id}`,
        type: 'compliance',
        severity: alert.severity,
        title: alert.title,
        message: alert.description,
        timestamp: alert.timestamp,
        details: alert,
        action: alert.action_required ? {
          label: 'Take Action',
          onClick: () => onAlertClick?.({
            id: `compliance-${alert.id}`,
            type: 'compliance',
            severity: alert.severity,
            title: alert.title,
            message: alert.description,
            timestamp: alert.timestamp,
            details: alert
          })
        } : undefined
      });
    });

    // Threat Detection
    if (data.threat_detection.risk_level !== 'low') {
      alerts.push({
        id: 'threat-detection',
        type: 'threat',
        severity: data.threat_detection.risk_level === 'critical' ? 'critical' : 
                 data.threat_detection.risk_level === 'high' ? 'high' : 'medium',
        title: 'Threat Detection Alert',
        message: `Risk level: ${data.threat_detection.risk_level}. Anomaly score: ${data.threat_detection.anomaly_score}`,
        timestamp: new Date().toISOString(),
        details: data.threat_detection,
        action: {
          label: 'View Threats',
          onClick: () => onAlertClick?.({
            id: 'threat-detection',
            type: 'threat',
            severity: data.threat_detection.risk_level === 'critical' ? 'critical' : 
                     data.threat_detection.risk_level === 'high' ? 'high' : 'medium',
            title: 'Threat Detection Alert',
            message: `Risk level: ${data.threat_detection.risk_level}. Anomaly score: ${data.threat_detection.anomaly_score}`,
            timestamp: new Date().toISOString(),
            details: data.threat_detection
          })
        }
      });
    }

    // Sort by timestamp (newest first) and limit
    return alerts
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, maxAlerts);
  };

  // Fetch security analytics data
  const fetchSecurityAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.get<SecurityAnalytics>('/api/v1/dashboard/realtime/security-analytics');
      const newAlerts = convertToAlerts(data);
      setAlerts(newAlerts);
      setLastUpdate(new Date());

      // Show critical alerts as notifications
      newAlerts
        .filter(alert => alert.severity === 'critical')
        .forEach(alert => {
          showNotification({
            type: 'error',
            title: alert.title,
            message: alert.message,
            duration: 10000
          });
        });
    } catch (err) {
      console.error('Failed to fetch security analytics:', err);
      setError('Failed to load security alerts');
    } finally {
      setLoading(false);
    }
  }, [maxAlerts]);

  // Initial fetch
  useEffect(() => {
    fetchSecurityAnalytics();
  }, [fetchSecurityAnalytics]);

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      refreshTimerRef.current = setInterval(() => {
        fetchSecurityAnalytics();
      }, refreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchSecurityAnalytics]);

  // WebSocket updates
  useEffect(() => {
    if (wsData) {
      const newAlerts = convertToAlerts(wsData);
      setAlerts(newAlerts);
      setLastUpdate(new Date());
    }
  }, [wsData, maxAlerts]);

  const getSeverityIcon = (severity: string, type: string) => {
    if (type === 'certificate') {
      return <Lock className="h-4 w-4" />;
    }
    if (type === 'compliance') {
      return <CheckCircle className="h-4 w-4" />;
    }
    switch (severity) {
      case 'critical':
        return <AlertCircle className="h-4 w-4" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4" />;
      case 'medium':
        return <Shield className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'destructive';
      case 'high': return 'destructive';
      case 'medium': return 'secondary';
      default: return 'outline';
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Security Alerts</CardTitle>
        <div className="flex items-center gap-2">
          {isConnected && (
            <Badge variant="outline" className="text-xs">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
              Live
            </Badge>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchSecurityAnalytics}
            disabled={loading}
            className="h-8 w-8"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && alerts.length === 0 ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="text-sm text-destructive p-3 border border-destructive/20 rounded-lg">
            {error}
          </div>
        ) : (
          <ScrollArea className={enhanced ? "h-[400px]" : "h-[300px]"}>
            <div className="space-y-2 pr-4">
              {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
                    <CheckCircle className="h-7 w-7 text-green-600 dark:text-green-400" />
                  </div>
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">All Clear</p>
                  <p className="text-xs text-muted-foreground mt-2 max-w-[200px] text-center">
                    No active security alerts. System is operating normally.
                  </p>
                  <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                      <span>Monitoring active</span>
                    </div>
                  </div>
                </div>
              ) : (
                alerts.map((alert) => (
                  <div 
                    key={alert.id} 
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors"
                    onClick={() => alert.action?.onClick()}
                  >
                    <div className={`mt-0.5 ${getSeverityColor(alert.severity) === 'destructive' ? 'text-destructive' : ''}`}>
                      {getSeverityIcon(alert.severity, alert.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="text-sm font-medium leading-none mb-1">
                            {alert.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {alert.message}
                          </p>
                        </div>
                        <Badge 
                          variant={getSeverityColor(alert.severity) as any} 
                          className="text-xs shrink-0"
                        >
                          {alert.severity}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <p className="text-xs text-muted-foreground">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </p>
                        {alert.action && (
                          <Button
                            variant="link"
                            size="sm"
                            className="h-auto p-0 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              alert.action!.onClick();
                            }}
                          >
                            {alert.action.label}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        )}
        {!loading && !error && alerts.length > 0 && (
          <div className="mt-3 pt-3 border-t">
            <p className="text-xs text-muted-foreground text-center">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};