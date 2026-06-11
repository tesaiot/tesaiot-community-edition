/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { RefreshCw, LayoutGrid, Activity, Bell, History, BarChart3, Zap, Terminal, PlusCircle, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { tesaApi, Certificate } from '@/services/api/tesaApi';
import { CertificateDetailsDialog } from './components/CertificateDetailsDialog';
import { CertificateHealthDashboard } from './components/CertificateHealthDashboard';
import { AlertsView, AuditView, AnalyticsView, AcmeView, ApiExplorerView } from './views';
import { toast } from 'sonner';

export const CertificateManagement: React.FC = () => {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCert, setSelectedCert] = useState<Certificate | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'health' | 'table' | 'alerts' | 'audit' | 'analytics' | 'acme' | 'explorer'>('health');
  
  // Alert-related state
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [alertConfigOpen, setAlertConfigOpen] = useState(false);
  
  // Audit-related state
  const [auditTrail, setAuditTrail] = useState<any[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [auditFilter, setAuditFilter] = useState('all');
  
  // ACME-related state
  const [acmeEnabled, setAcmeEnabled] = useState(false);
  const [acmeCertificates, setAcmeCertificates] = useState<any[]>([]);
  
  // Analytics-related state
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  
  // Table view state
  const [createOpen, setCreateOpen] = useState(false);
  
  const baseUrl = '';

  useEffect(() => {
    loadCertificates();
    loadAcmeSettings();
  }, []);

  useEffect(() => {
    if (viewMode === 'audit' && auditTrail.length === 0) {
      loadAuditTrail();
    }
    if (viewMode === 'acme' && acmeCertificates.length === 0) {
      loadAcmeCertificates();
    }
  }, [viewMode]);

  const loadCertificates = async () => {
    try {
      setLoading(true);
      const data = await tesaApi.getCertificates();
      setCertificates(data);
    } catch (error) {
      toast.error('Error', {
        description: 'Failed to load certificates'
      });
    } finally {
      setLoading(false);
    }
  };

  const loadAuditTrail = async () => {
    try {
      setLoadingAudit(true);
      const data = await tesaApi.getCertificateAuditTrail();
      setAuditTrail(data);
    } catch (error) {
      toast.error('Error', {
        description: 'Failed to load audit trail'
      });
    } finally {
      setLoadingAudit(false);
    }
  };

  const loadAcmeSettings = async () => {
    try {
      const settings = await tesaApi.getAcmeSettings();
      setAcmeEnabled(settings.enabled || false);
    } catch (error) {
      console.error('Failed to load ACME settings:', error);
    }
  };

  const loadAcmeCertificates = async () => {
    try {
      const certs = await tesaApi.getAcmeCertificates();
      setAcmeCertificates(certs);
    } catch (error) {
      console.error('Failed to load ACME certificates:', error);
    }
  };

  const handleRenewCertificate = async (cert: Certificate) => {
    try {
      await tesaApi.renewCertificate(cert.deviceId);
      toast.success('Success', {
        description: 'Certificate renewed successfully'
      });
      loadCertificates();
    } catch (error) {
      toast.error('Error', {
        description: 'Failed to renew certificate'
      });
    }
  };

  const handleViewDetails = (cert: Certificate) => {
    setSelectedCert(cert);
    setDetailsOpen(true);
  };

  const getStatusBadge = (status: Certificate['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="success"><CheckCircle className="mr-1 h-3 w-3" />Active</Badge>;
      case 'expiring':
        return <Badge variant="warning"><Clock className="mr-1 h-3 w-3" />Expiring</Badge>;
      case 'expired':
        return <Badge variant="destructive"><XCircle className="mr-1 h-3 w-3" />Expired</Badge>;
      case 'revoked':
        return <Badge variant="secondary"><AlertTriangle className="mr-1 h-3 w-3" />Revoked</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getDaysUntilExpiry = (validTo: string) => {
    const expiry = new Date(validTo);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  // API endpoints configuration
  const apiEndpoints = [
    {
      method: 'GET',
      path: '/api/v1/certificates',
      description: 'List all certificates',
      params: []
    },
    {
      method: 'POST',
      path: '/api/v1/certificates',
      description: 'Create a new certificate',
      params: [],
      body: {
        deviceId: 'device-123',
        organizationId: 'org-456',
        commonName: 'device-123.iot.example.com',
        keyAlgorithm: 'rsa',
        keySize: 2048
      }
    },
    {
      method: 'GET',
      path: '/api/v1/certificates/{certificateId}',
      description: 'Get certificate details',
      params: [
        { name: 'certificateId', required: true, description: 'Certificate ID' }
      ]
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/{deviceId}/renew',
      description: 'Renew a certificate',
      params: [
        { name: 'deviceId', required: true, description: 'Device ID' }
      ]
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/{deviceId}/revoke',
      description: 'Revoke a certificate',
      params: [
        { name: 'deviceId', required: true, description: 'Device ID' }
      ],
      body: {
        reason: 'keyCompromise'
      }
    },
    {
      method: 'GET',
      path: '/api/v1/certificates/audit-trail',
      description: 'Get certificate audit trail',
      params: []
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/bulk',
      description: 'Perform bulk operations on certificates',
      params: [],
      body: {
        action: 'renew',
        device_ids: ['device-1', 'device-2']
      }
    }
  ];

  // Helper function to render different views based on viewMode
  const renderCertificateView = () => {
    switch (viewMode) {
      case 'health':
        return (
          <CertificateHealthDashboard 
            certificates={certificates}
            onRefresh={loadCertificates}
            onRenew={handleRenewCertificate}
          />
        );
      
      case 'alerts':
        return (
          <AlertsView
            certificates={certificates}
            alertsEnabled={alertsEnabled}
            onAlertsEnabledChange={setAlertsEnabled}
            onAlertConfigOpen={() => setAlertConfigOpen(true)}
            onViewDetails={handleViewDetails}
            onRenewCertificate={handleRenewCertificate}
            getDaysUntilExpiry={getDaysUntilExpiry}
          />
        );
      
      case 'audit':
        return (
          <AuditView
            auditTrail={auditTrail}
            auditFilter={auditFilter}
            onAuditFilterChange={setAuditFilter}
            loadingAudit={loadingAudit}
          />
        );
      
      case 'analytics':
        return (
          <AnalyticsView
            certificates={certificates}
            recentActivity={recentActivity}
            onLoadCertificates={loadCertificates}
            onViewModeChange={setViewMode}
          />
        );
      
      case 'acme':
        return (
          <AcmeView
            acmeEnabled={acmeEnabled}
            onAcmeEnabledChange={setAcmeEnabled}
            acmeCertificates={acmeCertificates}
            onAcmeCertificatesChange={setAcmeCertificates}
            onLoadAcmeCertificates={loadAcmeCertificates}
            getStatusBadge={getStatusBadge}
          />
        );
      
      case 'explorer':
        return (
          <ApiExplorerView
            baseUrl={baseUrl}
            apiEndpoints={apiEndpoints}
          />
        );
      
      // Default view (table)
      default:
        return (
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Certificates</CardTitle>
                    <CardDescription>
                      Manage device certificates and security
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => setCreateOpen(true)}
                    disabled={loading}
                  >
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Create Certificate
                  </Button>
                </div>
                <div className="flex items-center gap-4">
                  <Input
                    placeholder="Search certificates..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="max-w-sm"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p>Certificate list view content here...</p>
            </CardContent>
          </Card>
        );
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Certificate Management</h1>
          <p className="text-muted-foreground">
            Manage device certificates and PKI lifecycle
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ToggleGroup type="single" value={viewMode} onValueChange={(value) => value && setViewMode(value as any)}>
            <ToggleGroupItem value="health" aria-label="Health view">
              <Activity className="h-4 w-4 mr-2" />
              Health
            </ToggleGroupItem>
            <ToggleGroupItem value="table" aria-label="Table view">
              <LayoutGrid className="h-4 w-4 mr-2" />
              Table
            </ToggleGroupItem>
            <ToggleGroupItem value="alerts" aria-label="Alerts view">
              <Bell className="h-4 w-4 mr-2" />
              Alerts
            </ToggleGroupItem>
            <ToggleGroupItem value="audit" aria-label="Audit view">
              <History className="h-4 w-4 mr-2" />
              Audit
            </ToggleGroupItem>
            <ToggleGroupItem value="analytics" aria-label="Analytics view">
              <BarChart3 className="h-4 w-4 mr-2" />
              Analytics
            </ToggleGroupItem>
            <ToggleGroupItem value="acme" aria-label="ACME view">
              <Zap className="h-4 w-4 mr-2" />
              ACME
            </ToggleGroupItem>
            <ToggleGroupItem value="explorer" aria-label="API Explorer view">
              <Terminal className="h-4 w-4 mr-2" />
              Explorer
            </ToggleGroupItem>
          </ToggleGroup>
          <Button onClick={() => {
            if (viewMode === 'audit') {
              loadAuditTrail();
            } else {
              loadCertificates();
            }
          }}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Certificate Views */}
      {renderCertificateView()}

      {/* Certificate Details Dialog */}
      <CertificateDetailsDialog
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        certificate={selectedCert}
      />
    </div>
  );
};