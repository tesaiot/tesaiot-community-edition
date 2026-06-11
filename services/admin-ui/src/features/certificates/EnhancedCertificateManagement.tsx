/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Shield, Key, Lock, FileCheck, Download, Upload, 
  RefreshCw, AlertTriangle, CheckCircle, XCircle,
  Fingerprint, ShieldCheck, KeyRound, Server
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { useLicenseContext } from '@/providers/license-provider';

interface Certificate {
  id: string;
  deviceId: string;
  deviceName: string;
  type: 'device' | 'ca' | 'intermediate' | 'root';
  status: 'active' | 'expired' | 'revoked' | 'pending';
  issuedAt: string;
  expiresAt: string;
  serialNumber: string;
  fingerprint: string;
  keyType: 'RSA-2048' | 'RSA-4096' | 'EC-P256' | 'EC-P384';
  usage: string[];
}

const mockCertificates: Certificate[] = [
  {
    id: 'cert-1',
    deviceId: 'dev-001',
    deviceName: 'Temperature Sensor A1',
    type: 'device',
    status: 'active',
    issuedAt: '2025-01-15T10:00:00Z',
    expiresAt: '2026-01-15T10:00:00Z',
    serialNumber: '4F:2B:8A:1C:D5:93',
    fingerprint: 'SHA256:7b:4c:89:2f:6a:1d:e3:b8:9c:5f:a2:d7:3e:91:c4:8b',
    keyType: 'EC-P256',
    usage: ['Digital Signature', 'Key Agreement']
  },
  {
    id: 'cert-2',
    deviceId: 'dev-002',
    deviceName: 'Smart Lock Gateway',
    type: 'device',
    status: 'active',
    issuedAt: '2025-02-01T14:30:00Z',
    expiresAt: '2026-02-01T14:30:00Z',
    serialNumber: '6A:1F:C3:8E:B2:47',
    fingerprint: 'SHA256:9e:2a:f5:8c:1b:d4:e7:3a:6f:c8:b9:5d:a1:e2:f3:7c',
    keyType: 'RSA-4096',
    usage: ['Digital Signature', 'Key Encipherment', 'Client Authentication']
  }
];

export default function EnhancedCertificateManagement() {
  const { edition, hasFeature } = useLicenseContext();
  const [certificates] = useState(mockCertificates);
  const [activeTab, setActiveTab] = useState('overview');

  const isCommercial = edition !== 'community';
  const hasHSMSupport = hasFeature('hsmSupport');
  const hasDedicatedPKI = hasFeature('dedicatedPKI');

  const stats = {
    total: certificates.length,
    active: certificates.filter(c => c.status === 'active').length,
    expiringSoon: certificates.filter(c => {
      const daysUntilExpiry = Math.ceil((new Date(c.expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
      return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
    }).length,
    expired: certificates.filter(c => c.status === 'expired').length,
    revoked: certificates.filter(c => c.status === 'revoked').length
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'expired':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'revoked':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="default" className="bg-green-500">Active</Badge>;
      case 'expired':
        return <Badge variant="destructive">Expired</Badge>;
      case 'revoked':
        return <Badge variant="secondary" className="bg-orange-500 text-white">Revoked</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Certificate Management</h1>
          <p className="text-muted-foreground mt-2">
            Comprehensive PKI certificate lifecycle management for IoT devices
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasHSMSupport && (
            <Badge variant="outline" className="gap-1">
              <Server className="h-3 w-3" />
              HSM Protected
            </Badge>
          )}
          {hasDedicatedPKI && (
            <Badge variant="outline" className="gap-1">
              <ShieldCheck className="h-3 w-3" />
              Dedicated PKI
            </Badge>
          )}
        </div>
      </div>

      {/* Security Trust Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4 text-green-500" />
              Trust Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">High</div>
            <Progress value={95} className="mt-2 h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {isCommercial ? 'Enterprise-grade PKI' : 'Standard PKI'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Key className="h-4 w-4 text-blue-500" />
              Key Strength
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isCommercial ? 'RSA-4096' : 'RSA-2048'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {isCommercial ? 'Maximum security' : 'Standard security'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Fingerprint className="h-4 w-4 text-purple-500" />
              Algorithm
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">SHA-256</div>
            <p className="text-xs text-muted-foreground mt-1">
              {isCommercial && 'With ECDSA support'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Lock className="h-4 w-4 text-orange-500" />
              Compliance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">100%</div>
            <p className="text-xs text-muted-foreground mt-1">
              ETSI & ISO/IEC compliant
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Certificate Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Certificate Overview</CardTitle>
          <CardDescription>
            Real-time status of all managed certificates
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold">{stats.total}</div>
              <p className="text-sm text-muted-foreground">Total Certificates</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{stats.active}</div>
              <p className="text-sm text-muted-foreground">Active</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600">{stats.expiringSoon}</div>
              <p className="text-sm text-muted-foreground">Expiring Soon</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600">{stats.expired}</div>
              <p className="text-sm text-muted-foreground">Expired</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600">{stats.revoked}</div>
              <p className="text-sm text-muted-foreground">Revoked</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Card>
        <CardContent className="p-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Certificate Overview</TabsTrigger>
              <TabsTrigger value="device">Device Provisioning</TabsTrigger>
              <TabsTrigger value="key">Key Provisioning</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-6">
              <div className="space-y-4">
                <Alert>
                  <Shield className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Zero-Trust Security Model:</strong> Every device requires a unique certificate 
                    for authentication. No default passwords or shared secrets are used.
                  </AlertDescription>
                </Alert>

                {/* Certificate List */}
                <div className="space-y-2">
                  {certificates.map((cert) => (
                    <div key={cert.id} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(cert.status)}
                            <h4 className="font-semibold">{cert.deviceName}</h4>
                            <Badge variant="outline" className="text-xs">
                              {cert.keyType}
                            </Badge>
                          </div>
                          <div className="mt-2 grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                            <div>
                              <span className="font-medium">Serial:</span> {cert.serialNumber}
                            </div>
                            <div>
                              <span className="font-medium">Expires:</span> {new Date(cert.expiresAt).toLocaleDateString()}
                            </div>
                            <div className="col-span-2">
                              <span className="font-medium">Fingerprint:</span> 
                              <code className="text-xs ml-1">{cert.fingerprint}</code>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {getStatusBadge(cert.status)}
                          <Button size="sm" variant="outline">
                            <Download className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="device" className="mt-6">
              <div className="space-y-4">
                <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/20">
                  <Key className="h-4 w-4 text-blue-600" />
                  <AlertDescription>
                    <strong>Device Provisioning:</strong> Automated certificate generation and secure 
                    delivery to IoT devices during manufacturing or initial setup.
                  </AlertDescription>
                </Alert>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Provisioning Methods</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                        <div>
                          <p className="font-medium">Zero-Touch Provisioning</p>
                          <p className="text-sm text-muted-foreground">
                            Automatic certificate enrollment on first boot
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                        <div>
                          <p className="font-medium">Bulk Provisioning</p>
                          <p className="text-sm text-muted-foreground">
                            Pre-generate certificates for manufacturing
                          </p>
                        </div>
                      </div>
                      {isCommercial && (
                        <div className="flex items-start gap-3">
                          <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                          <div>
                            <p className="font-medium">EST Protocol Support</p>
                            <p className="text-sm text-muted-foreground">
                              RFC 7030 compliant enrollment
                            </p>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Security Features</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-start gap-3">
                        <Shield className="h-5 w-5 text-blue-500 mt-0.5" />
                        <div>
                          <p className="font-medium">Unique Device Identity</p>
                          <p className="text-sm text-muted-foreground">
                            Each device gets a unique certificate
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <Lock className="h-5 w-5 text-blue-500 mt-0.5" />
                        <div>
                          <p className="font-medium">Secure Key Storage</p>
                          <p className="text-sm text-muted-foreground">
                            {isCommercial ? 'HSM-backed key protection' : 'Encrypted key storage'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-3">
                        <RefreshCw className="h-5 w-5 text-blue-500 mt-0.5" />
                        <div>
                          <p className="font-medium">Automatic Renewal</p>
                          <p className="text-sm text-muted-foreground">
                            Certificates renewed before expiry
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="flex justify-center gap-4 mt-6">
                  <Button className="gap-2">
                    <Upload className="h-4 w-4" />
                    Provision New Device
                  </Button>
                  <Button variant="outline" className="gap-2">
                    <Download className="h-4 w-4" />
                    Export Provisioning Profile
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="key" className="mt-6">
              <div className="space-y-4">
                <Alert className="border-purple-200 bg-purple-50 dark:bg-purple-950/20">
                  <KeyRound className="h-4 w-4 text-purple-600" />
                  <AlertDescription>
                    <strong>Key Provisioning:</strong> Secure generation, distribution, and lifecycle 
                    management of cryptographic keys for device authentication and data encryption.
                  </AlertDescription>
                </Alert>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Key Types</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Authentication Keys</span>
                        <Badge variant="outline">Active</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Encryption Keys</span>
                        <Badge variant="outline">Active</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Signing Keys</span>
                        <Badge variant="outline">Active</Badge>
                      </div>
                      {isCommercial && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm">KEK (Key Encryption)</span>
                          <Badge variant="outline">Active</Badge>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Key Algorithms</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">RSA-2048</span>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        </div>
                        {isCommercial && (
                          <>
                            <div className="flex items-center justify-between">
                              <span className="text-sm">RSA-4096</span>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-sm">ECC P-256</span>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-sm">ECC P-384</span>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                          </>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Key Protection</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Encrypted Storage</span>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Access Control</span>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        </div>
                        {isCommercial && (
                          <>
                            <div className="flex items-center justify-between">
                              <span className="text-sm">HSM Integration</span>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-sm">Key Escrow</span>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </div>
                          </>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {!isCommercial && (
                  <Alert className="border-yellow-200 bg-yellow-50 dark:bg-yellow-950/20">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    <AlertDescription>
                      <strong>Limited Key Features:</strong> Community edition supports basic key management. 
                      Upgrade to Commercial for HSM integration, advanced algorithms, and key escrow capabilities.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Trust Statement */}
      <Card className="border-green-500 bg-green-50/50 dark:bg-green-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <ShieldCheck className="h-8 w-8 text-green-600 mt-1" />
            <div>
              <h3 className="font-semibold text-lg mb-2">
                Enterprise-Grade Security You Can Trust
              </h3>
              <p className="text-sm text-muted-foreground mb-3">
                Our PKI infrastructure provides military-grade security for your IoT devices:
              </p>
              <ul className="space-y-1 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  No default passwords - every device has unique credentials
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Automated certificate lifecycle management
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  {isCommercial ? 'HSM-backed key protection' : 'Secure encrypted key storage'}
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Full compliance with ETSI EN 303 645 & ISO/IEC 27402
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}