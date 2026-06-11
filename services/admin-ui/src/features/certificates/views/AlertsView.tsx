/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Bell, Settings, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Certificate } from '@/services/api/tesaApi';

interface AlertsViewProps {
  certificates: Certificate[];
  alertsEnabled: boolean;
  onAlertsEnabledChange: (enabled: boolean) => void;
  onAlertConfigOpen: () => void;
  onViewDetails: (cert: Certificate) => void;
  onRenewCertificate: (cert: Certificate) => void;
  getDaysUntilExpiry: (validTo: string) => number;
}

export const AlertsView: React.FC<AlertsViewProps> = ({
  certificates,
  alertsEnabled,
  onAlertsEnabledChange,
  onAlertConfigOpen,
  onViewDetails,
  onRenewCertificate,
  getDaysUntilExpiry
}) => {
  const expiringCerts = certificates.filter(cert => {
    const days = getDaysUntilExpiry(cert.validTo);
    return cert.status === 'active' && days >= 0 && days <= 30;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Certificate Expiration Alerts
            </CardTitle>
            <CardDescription>
              Monitor certificates approaching expiration and configure alert rules
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onAlertConfigOpen}>
              <Settings className="h-4 w-4 mr-2" />
              Configure Alerts
            </Button>
            <Switch
              checked={alertsEnabled}
              onCheckedChange={onAlertsEnabledChange}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {alertsEnabled && (
          <div className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Email notifications will be sent to configured recipients when certificates approach expiration thresholds.
              </AlertDescription>
            </Alert>
            
            {expiringCerts.length > 0 ? (
              <div className="space-y-2">
                {expiringCerts.map((cert) => (
                  <Alert key={cert.deviceId} variant={getDaysUntilExpiry(cert.validTo) <= 7 ? "destructive" : "warning"}>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="flex justify-between items-center">
                        <div>
                          <strong>{cert.commonName}</strong> expires in <strong>{getDaysUntilExpiry(cert.validTo)} days</strong>
                          <div className="text-sm text-muted-foreground mt-1">
                            Device ID: {cert.deviceId} | Valid until: {new Date(cert.validTo).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => onViewDetails(cert)}>
                            View Details
                          </Button>
                          <Button size="sm" onClick={() => onRenewCertificate(cert)}>
                            Renew Now
                          </Button>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            ) : (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  All certificates are healthy. No certificates are expiring within the configured thresholds.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};