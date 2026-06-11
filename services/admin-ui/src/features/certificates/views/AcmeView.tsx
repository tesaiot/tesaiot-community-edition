/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState } from 'react';
import { Globe, Info, AlertCircle, Save, RotateCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { tesaApi } from '@/services/api/tesaApi';

interface AcmeConfig {
  directoryUrl: string;
  contactEmail: string;
  challengeType: string;
}

interface AcmeCertificate {
  domain: string;
  status: string;
  expiresAt: string;
  autoRenew: boolean;
}

interface AcmeViewProps {
  acmeEnabled: boolean;
  onAcmeEnabledChange: (enabled: boolean) => void;
  acmeCertificates: AcmeCertificate[];
  onAcmeCertificatesChange: (certs: AcmeCertificate[]) => void;
  onLoadAcmeCertificates: () => void;
  getStatusBadge: (status: string) => JSX.Element;
}

export const AcmeView: React.FC<AcmeViewProps> = ({
  acmeEnabled,
  onAcmeEnabledChange,
  acmeCertificates,
  onAcmeCertificatesChange,
  onLoadAcmeCertificates,
  getStatusBadge
}) => {
  const [acmeConfig, setAcmeConfig] = useState<AcmeConfig>({
    directoryUrl: '',
    contactEmail: '',
    challengeType: 'http-01'
  });

  const handleSaveAcmeConfig = async () => {
    try {
      await tesaApi.updateAcmeSettings(acmeConfig);
      toast.success('ACME Configuration Saved', {
        description: 'ACME settings have been updated successfully'
      });
    } catch (error) {
      toast.error('Save Failed', {
        description: 'Failed to save ACME configuration'
      });
    }
  };

  const handleToggleAutoRenew = async (domain: string, enabled: boolean) => {
    try {
      await tesaApi.updateAcmeCertificate(domain, { autoRenew: enabled });
      const updatedCerts = acmeCertificates.map(cert => 
        cert.domain === domain ? { ...cert, autoRenew: enabled } : cert
      );
      onAcmeCertificatesChange(updatedCerts);
      toast.success('Auto-Renewal Updated', {
        description: `Auto-renewal ${enabled ? 'enabled' : 'disabled'} for ${domain}`
      });
    } catch (error) {
      toast.error('Update Failed', {
        description: 'Failed to update auto-renewal setting'
      });
    }
  };

  const handleRenewAcmeCert = async (domain: string) => {
    try {
      await tesaApi.renewAcmeCertificate(domain);
      toast.success('Certificate Renewed', {
        description: `Certificate for ${domain} has been renewed`
      });
      // Reload ACME certificates
      onLoadAcmeCertificates();
    } catch (error) {
      toast.error('Renewal Failed', {
        description: 'Failed to renew ACME certificate'
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              ACME Certificate Management
            </CardTitle>
            <CardDescription>
              Automated Certificate Management Environment for Let's Encrypt certificates
            </CardDescription>
          </div>
          <Switch
            checked={acmeEnabled}
            onCheckedChange={onAcmeEnabledChange}
          />
        </div>
      </CardHeader>
      <CardContent>
        {acmeEnabled ? (
          <div className="space-y-6">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                ACME integration allows automatic certificate issuance and renewal using Let's Encrypt.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>ACME Directory URL</Label>
                <Input
                  value={acmeConfig.directoryUrl}
                  onChange={(e) => setAcmeConfig({...acmeConfig, directoryUrl: e.target.value})}
                  placeholder="https://acme-v02.api.letsencrypt.org/directory"
                />
              </div>
              <div>
                <Label>Contact Email</Label>
                <Input
                  value={acmeConfig.contactEmail}
                  onChange={(e) => setAcmeConfig({...acmeConfig, contactEmail: e.target.value})}
                  placeholder="admin@example.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Challenge Type</Label>
              <Select
                value={acmeConfig.challengeType}
                onValueChange={(value) => setAcmeConfig({...acmeConfig, challengeType: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="http-01">HTTP-01 (Port 80)</SelectItem>
                  <SelectItem value="dns-01">DNS-01 (DNS TXT Record)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button onClick={handleSaveAcmeConfig} className="w-full">
              <Save className="mr-2 h-4 w-4" />
              Save ACME Configuration
            </Button>

            <Separator />

            <div className="space-y-4">
              <h4 className="text-sm font-medium">ACME Certificates</h4>
              {acmeCertificates.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Domain</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Auto-Renew</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {acmeCertificates.map((cert) => (
                      <TableRow key={cert.domain}>
                        <TableCell>{cert.domain}</TableCell>
                        <TableCell>{getStatusBadge(cert.status)}</TableCell>
                        <TableCell>{new Date(cert.expiresAt).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <Switch
                            checked={cert.autoRenew}
                            onCheckedChange={(checked) => handleToggleAutoRenew(cert.domain, checked)}
                          />
                        </TableCell>
                        <TableCell>
                          <Button size="sm" variant="outline" onClick={() => handleRenewAcmeCert(cert.domain)}>
                            <RotateCw className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    No ACME certificates configured. Add a domain above to get started.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </div>
        ) : (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              ACME integration is disabled. Enable it to use Let's Encrypt certificates.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};