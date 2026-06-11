/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Search, Award, Shield, History, Bell, Settings, Code, BarChart3, Plus, Activity, RefreshCw, AlertCircle, Key } from "lucide-react";
import { DataGrid } from "@/components/ui/data-grid";
import { Certificate as CertificateType } from '@/services/api/tesaApi';
import { useAuth } from '@/hooks/useAuth';

// Import modular hooks
import {
  useCertificates,
  useCertificateAlerts,
  useCertificateAudit,
  useAcmeSettings,
  useBulkOperations,
  useApiExplorer,
  useCertificateAnalytics
} from './hooks';

// Import views
import {
  AlertsView,
  AuditView,
  AnalyticsView,
  AcmeView,
  ApiExplorerView
} from './views';

// Import v2.5.0-beta components
import { CertificateHealthDashboard } from './components/CertificateHealthDashboard';
import { CertificateDetailsDialog } from './components/CertificateDetailsDialog';
import { KeyProvisioningPanel } from './components/KeyProvisioningPanel';

// Import utilities
import {
  getStatusBadge,
  getExpiryBadge,
  filterCertificates,
  calculateCertificateStats
} from './utils';

export const CertificateManagement: React.FC = () => {
  const { user } = useAuth();
  const isPlatformAdmin = user?.role === 'platform_admin';
  const [searchParams, setSearchParams] = useSearchParams();

  // Core state using modular hooks
  const {
    certificates,
    loading,
    error,
    loadCertificates,
    handleRevokeCertificate,
    handleRenewCertificate,
    handleExportCertificate
  } = useCertificates();

  const {
    alertSettings,
    updateAlertSettings,
    expiringCertificates
  } = useCertificateAlerts(certificates);

  const {
    auditTrail,
    loadingAudit,
    loadAuditTrail
  } = useCertificateAudit();

  const {
    acmeSettings,
    updateAcmeSettings,
    acmeCertificates,
    loadAcmeCertificates
  } = useAcmeSettings();

  const {
    selectedCertificates,
    toggleCertificateSelection,
    toggleSelectAll,
    performBulkOperation
  } = useBulkOperations(certificates);

  const {
    apiEndpoints,
    executeApiRequest,
    copyApiCommand
  } = useApiExplorer();

  const analytics = useCertificateAnalytics(certificates);

  // Local UI state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCert, setSelectedCert] = useState<CertificateType | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  
  // v2.5.0-beta enhancement: Default to 'health' view for better UX with URL parameter support
  const [viewMode, setViewMode] = useState<'health' | 'table' | 'alerts' | 'audit' | 'analytics' | 'acme' | 'explorer' | 'key-provisioning'>(() => {
    const tabParam = searchParams.get('tab');
    return tabParam === 'key-provisioning' ? 'key-provisioning' : 'health';
  });
  
  // Update URL when view mode changes
  const handleViewModeChange = (mode: string) => {
    setViewMode(mode as any);
    const newSearchParams = new URLSearchParams(searchParams);
    if (mode === 'key-provisioning') {
      newSearchParams.set('tab', 'key-provisioning');
    } else {
      newSearchParams.delete('tab');
    }
    setSearchParams(newSearchParams);
  };

  // Load data on component mount
  useEffect(() => {
    loadCertificates();
  }, []);

  // Filter certificates based on search and active tab
  const filteredCertificates = filterCertificates(certificates, searchTerm, activeTab);

  // Calculate statistics for display
  const stats = calculateCertificateStats(certificates);

  const handleViewDetails = (cert: CertificateType) => {
    setSelectedCert(cert);
    setDetailsOpen(true);
  };

  const handleRefresh = () => {
    if (viewMode === 'audit') {
      loadAuditTrail();
    } else if (viewMode === 'acme') {
      loadAcmeCertificates();
    } else {
      loadCertificates();
    }
  };

  const getDaysUntilExpiry = (validTo: string): number => {
    const expiry = new Date(validTo);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  // Render different views based on viewMode
  const renderCertificateView = () => {
    switch (viewMode) {
      case 'health':
        return (
          <CertificateHealthDashboard 
            certificates={certificates}
            onRefresh={loadCertificates}
            onRenew={handleRenewCertificate}
            onViewDetails={handleViewDetails}
          />
        );
      
      case 'table':
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Award className="h-5 w-5" />
                Certificate Table View
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataGrid
                table={{
                  data: filteredCertificates,
                  columns: [
                    { key: 'subject', title: 'Subject' },
                    { key: 'status', title: 'Status' },
                    { key: 'validTo', title: 'Expires' },
                    { key: 'algorithm', title: 'Algorithm' }
                  ]
                }}
                onRowClick={handleViewDetails}
                onRenew={handleRenewCertificate}
                onRevoke={handleRevokeCertificate}
                onExport={handleExportCertificate}
              />
            </CardContent>
          </Card>
        );
      
      case 'alerts':
        return (
          <AlertsView
            certificates={certificates}
            alertsEnabled={alertSettings?.enabled || false}
            onAlertsEnabledChange={(enabled) => updateAlertSettings({ enabled })}
            onAlertConfigOpen={() => {/* TODO: Open alert config dialog */}}
            onViewDetails={handleViewDetails}
            onRenewCertificate={handleRenewCertificate}
            getDaysUntilExpiry={getDaysUntilExpiry}
          />
        );
      
      case 'audit':
        return (
          <AuditView
            auditTrail={auditTrail}
            loading={loadingAudit}
            onRefresh={loadAuditTrail}
          />
        );
      
      case 'analytics':
        return (
          <AnalyticsView
            certificates={certificates}
            recentActivity={[]}
            onLoadCertificates={loadCertificates}
            onViewModeChange={(mode) => setViewMode(mode as any)}
          />
        );
      
      case 'acme':
        return (
          <AcmeView
            settings={acmeSettings}
            certificates={acmeCertificates}
            onUpdateSettings={updateAcmeSettings}
            onRefresh={loadAcmeCertificates}
          />
        );
      
      case 'explorer':
        return (
          <ApiExplorerView
            baseUrl=""
            apiEndpoints={apiEndpoints || []}
          />
        );
      
      case 'key-provisioning':
        return (
          <KeyProvisioningPanel />
        );
      
      default:
        return null;
    }
  };

  // Platform admins cannot access certificate management
  if (isPlatformAdmin) {
    return (
      <div className="space-y-6 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Access Restricted
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="space-y-2">
                <p>
                  As a platform administrator, you have access to infrastructure management only.
                  Certificate management is restricted to organization administrators.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Platform administrators can manage:
                </p>
                <ul className="list-disc list-inside text-sm text-muted-foreground ml-4">
                  <li>System infrastructure and monitoring</li>
                  <li>Platform-wide settings and configuration</li>
                  <li>Service health and performance metrics</li>
                </ul>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

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
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Search and Stats */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search certificates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        
        {/* Quick Stats */}
        <div className="flex gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats.active}</div>
            <div className="text-xs text-muted-foreground">Active</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">{stats.expiring}</div>
            <div className="text-xs text-muted-foreground">Expiring</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{stats.expired}</div>
            <div className="text-xs text-muted-foreground">Expired</div>
          </div>
        </div>
      </div>

      {/* View Mode Tabs - v2.5.0-beta Enhancement */}
      <Tabs value={viewMode} onValueChange={handleViewModeChange}>
        <TabsList className="grid w-full grid-cols-8">
          <TabsTrigger value="health" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Health
          </TabsTrigger>
          <TabsTrigger value="table" className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            Table
          </TabsTrigger>
          <TabsTrigger value="alerts" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Alerts
          </TabsTrigger>
          <TabsTrigger value="audit" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Audit
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="acme" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            ACME
          </TabsTrigger>
          <TabsTrigger value="explorer" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            Explorer
          </TabsTrigger>
          <TabsTrigger value="key-provisioning" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            Key Provisioning
          </TabsTrigger>
        </TabsList>

        <TabsContent value={viewMode} className="mt-6">
          {renderCertificateView()}
        </TabsContent>
      </Tabs>

      {/* Certificate Details Dialog */}
      <CertificateDetailsDialog
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        certificate={selectedCert}
      />
    </div>
  );
};