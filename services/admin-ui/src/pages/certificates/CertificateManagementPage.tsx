/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  AlertTriangle,
  RefreshCw,
  Settings,
  FileText,
  Download,
  Upload,
  Plus,
  BarChart3,
  History,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { CertificateMonitoringDashboard } from '@/features/certificates/components/CertificateMonitoringDashboard';
import { CertificateRenewalDialog } from '@/features/certificates/components/CertificateRenewalDialog';
import { ProvisioningMethodBadge } from '@/features/certificates/components/ProvisioningMethodBadge';
import { Container } from '@/components/common/container';
import { useAuth } from '@/hooks/useAuth';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider, SliderThumb } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';

interface Certificate {
  id: string;
  deviceId: string;
  deviceName: string;
  deviceType: string;
  status: 'active' | 'expiring' | 'expired' | 'revoked';
  issuedAt: string;
  expiresAt: string;
  daysUntilExpiry: number;
  serialNumber: string;
  algorithm: string;
  organization?: string;
}

export default function CertificateManagementPage() {
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Tab state persistence via URL parameter
  const validTabs = ['dashboard', 'certificates', 'activity-logs', 'settings'];
  const initialTab = searchParams.get('tab') || 'dashboard';
  const [activeTab, setActiveTab] = useState(validTabs.includes(initialTab) ? initialTab : 'dashboard');

  const [selectedCertificate, setSelectedCertificate] = useState<Certificate | null>(null);
  const [showRenewalDialog, setShowRenewalDialog] = useState(false);
  const [loading, setLoading] = useState(false);

  // Update URL when tab changes (persist tab state)
  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    const newParams = new URLSearchParams(searchParams);
    if (tab === 'dashboard') {
      newParams.delete('tab'); // Default tab doesn't need URL param
    } else {
      newParams.set('tab', tab);
    }
    setSearchParams(newParams, { replace: true });
  };

  // Sync tab state with URL on mount
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam && validTabs.includes(tabParam) && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  // Access & role gates
  const hasAccess = currentUser?.role !== 'platform_admin';
  const isAdminRole = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');

  const navigateToDeviceCertificate = (certificate: Certificate, tab: 'overview' | 'lifecycle') => {
    if (!certificate?.deviceId) {
      toast.error('Device identifier missing for this certificate');
      return;
    }

    const params = new URLSearchParams();
    params.set('device', certificate.deviceId);
    params.set('certTab', tab);

    navigate(`/devices?${params.toString()}`);
    toast.info(`Opening device ${certificate.deviceName} certificate workspace`);
  };

  const handleCertificateRenew = (certificate: Certificate) => {
    navigateToDeviceCertificate(certificate, 'lifecycle');
  };

  const handleCertificateRevoke = (certificate: Certificate) => {
    navigateToDeviceCertificate(certificate, 'lifecycle');
  };

  const handleRenewalComplete = (certificate: Certificate, newCertificate: any) => {
    toast.success(`Certificate for ${certificate.deviceName} has been renewed successfully`);
    setShowRenewalDialog(false);
    setSelectedCertificate(null);
    // TODO: Refresh certificate data
  };

  const handleBulkRenewal = () => {
    // TODO: Implement bulk certificate renewal
    toast.info('Bulk certificate renewal feature coming soon');
  };

  const handleExportCertificates = () => {
    // TODO: Implement certificate export
    toast.info('Certificate export feature coming soon');
  };

  const handleImportCertificates = () => {
    // TODO: Implement certificate import
    toast.info('Certificate import feature coming soon');
  };

  if (!hasAccess) {
    return (
      <Container>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Access Restricted
              </CardTitle>
              <CardDescription>
                Platform Administrator Access
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertTriangle className="h-4 w-4" />
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
      </Container>
    );
  }

  return (
    <Container>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Certificate Management</h1>
            <p className="text-muted-foreground">
              Monitor and manage device certificates with automated renewal capabilities
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleExportCertificates}
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
            <Button
              variant="outline"
              onClick={handleImportCertificates}
              className="flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              Import
            </Button>
            <Button
              variant="outline"
              onClick={handleBulkRenewal}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:from-blue-600 hover:to-purple-600"
            >
              <RefreshCw className="h-4 w-4" />
              Bulk Renewal
            </Button>
          </div>
        </div>

        {/* Main Content with Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className={`grid w-full ${isAdminRole ? 'grid-cols-4' : 'grid-cols-2'}`}>
            <TabsTrigger value="dashboard" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="certificates" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Certificates
            </TabsTrigger>
            {isAdminRole && (
              <TabsTrigger value="activity-logs" className="flex items-center gap-2">
                <History className="h-4 w-4" />
                Activity Logs
              </TabsTrigger>
            )}
            {isAdminRole && (
              <TabsTrigger value="settings" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Settings
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="dashboard" className="mt-6">
          <CertificateMonitoringDashboard
            onCertificateRenew={handleCertificateRenew}
            onCertificateRevoke={handleCertificateRevoke}
            onOpenDeviceOverview={(certificate) => navigateToDeviceCertificate(certificate, 'overview')}
            onOpenDeviceLifecycle={(certificate) => navigateToDeviceCertificate(certificate, 'lifecycle')}
            showAdvancedFilters={false}
            atRiskOnly={true}
          />
          </TabsContent>

          <TabsContent value="certificates" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  All Certificates
                </CardTitle>
                <CardDescription>
                  Detailed view of all device certificates in your organization
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CertificateMonitoringDashboard
                  showRefreshButton={false}
                  onCertificateRenew={handleCertificateRenew}
                  onCertificateRevoke={handleCertificateRevoke}
                  onOpenDeviceOverview={(certificate) => navigateToDeviceCertificate(certificate, 'overview')}
                  onOpenDeviceLifecycle={(certificate) => navigateToDeviceCertificate(certificate, 'lifecycle')}
                  showAdvancedFilters={true}
                  atRiskOnly={false}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {isAdminRole && (
            <TabsContent value="activity-logs" className="mt-6">
              <div className="grid gap-6">
                <CertificateRotationHistoryCard />
                <EarlyRenewalsCard />
              </div>
            </TabsContent>
          )}

          {isAdminRole && (
            <TabsContent value="settings" className="mt-6">
              <div className="grid gap-6">
                <OrgCertificatePolicyCard />
              </div>
            </TabsContent>
          )}
        </Tabs>

        {/* Certificate Renewal Dialog */}
        <CertificateRenewalDialog
          open={showRenewalDialog}
          onOpenChange={setShowRenewalDialog}
          certificate={selectedCertificate}
          onRenewalComplete={handleRenewalComplete}
        />
      </div>
    </Container>
  );
}

import { AuthTokenManager } from '@/utils/auth-token-manager';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

// Certificate Rotation History Card Component
function CertificateRotationHistoryCard() {
  const [items, setItems] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { user: currentUser } = useAuth();
  const canView = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');
  const [deviceType, setDeviceType] = React.useState<string>('all');
  const [actionFilter, setActionFilter] = React.useState<string>('all');
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(0);
  const limit = 50;

  // Date range: last 90 days by default
  const toLocalInput = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const now = new Date();
  const ninetyDaysAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
  const [start, setStart] = React.useState<string>(toLocalInput(ninetyDaysAgo));
  const [end, setEnd] = React.useState<string>(toLocalInput(now));

  const loadData = React.useCallback(async () => {
    if (!canView) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (start) params.set('start', start);
      if (end) params.set('end', end);
      if (deviceType && deviceType !== 'all') params.set('device_type', deviceType);
      if (actionFilter && actionFilter !== 'all') params.set('action', actionFilter);
      params.set('limit', String(limit));
      params.set('offset', String(page * limit));
      const query = params.toString() ? `?${params.toString()}` : '';
      const token = AuthTokenManager.getToken();
      const res = await fetch(`/api/v1/certificates/rotation-history${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data?.items || []);
      setTotal(data?.total || 0);
    } catch (e: any) {
      setError(e.message || 'Failed to load rotation history');
    } finally {
      setLoading(false);
    }
  }, [canView, start, end, deviceType, actionFilter, page]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const getActionBadgeColor = (action: string) => {
    switch (action?.toLowerCase()) {
      case 'issued':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'renewed':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'revoked':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'expired':
        return 'bg-gray-100 text-gray-700 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const downloadCsv = async () => {
    try {
      const params = new URLSearchParams();
      if (start) params.set('start', start);
      if (end) params.set('end', end);
      if (deviceType && deviceType !== 'all') params.set('device_type', deviceType);
      if (actionFilter && actionFilter !== 'all') params.set('action', actionFilter);
      params.set('limit', '10000'); // Get all for export
      const query = params.toString() ? `?${params.toString()}` : '';
      const token = AuthTokenManager.getToken();
      const res = await fetch(`/api/v1/certificates/rotation-history${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const rows = [['timestamp', 'device_id', 'device_name', 'action', 'provisioning_method', 'serial_number', 'algorithm', 'validity_days', 'issued_by', 'reason']].concat(
        (data?.items || []).map((it: any) => [
          new Date(it.timestamp).toISOString(),
          it.device_id || '',
          it.device_name || '',
          it.action || '',
          it.provisioning_method || '',
          it.serial_number || '',
          it.algorithm || '',
          it.validity_days ?? '',
          it.issued_by || '',
          (it.reason || '').replace(/\n/g, ' ')
        ])
      );
      const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'certificate-rotation-history.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Rotation history exported');
    } catch (e: any) {
      toast.error(`Export failed: ${e.message}`);
    }
  };

  if (!canView) return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Certificate Rotation History (Admin Only)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>Only organization administrators can view audit reports.</AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Certificate Rotation History
        </CardTitle>
        <CardDescription>
          All certificate issuance, renewal, and revocation events across your organization
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div>
            <Label className="text-xs">Start</Label>
            <Input type="datetime-local" value={start} onChange={e => setStart(e.target.value)} className="w-[180px]" />
          </div>
          <div>
            <Label className="text-xs">End</Label>
            <Input type="datetime-local" value={end} onChange={e => setEnd(e.target.value)} className="w-[180px]" />
          </div>
          <div>
            <Label className="text-xs">Action</Label>
            <Select value={actionFilter} onValueChange={v => { setActionFilter(v); setPage(0); }}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="issued">Issued</SelectItem>
                <SelectItem value="renewed">Renewed</SelectItem>
                <SelectItem value="revoked">Revoked</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Device Type</Label>
            <Select value={deviceType} onValueChange={v => { setDeviceType(v); setPage(0); }}>
              <SelectTrigger className="w-[140px]"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="sensor">sensor</SelectItem>
                <SelectItem value="actuator">actuator</SelectItem>
                <SelectItem value="controller">controller</SelectItem>
                <SelectItem value="gateway">gateway</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" size="sm" onClick={() => loadData()} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
            <Button variant="outline" size="sm" onClick={downloadCsv}>
              <Download className="h-4 w-4 mr-1" />
              Export CSV
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading rotation history...
          </div>
        ) : error ? (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="text-sm text-muted-foreground mb-2">
              Showing {items.length} of {total} records
            </div>
            <div className="overflow-x-auto rounded-md border">
              <table className="min-w-full text-sm">
                <thead className="bg-muted/50">
                  <tr className="text-left">
                    <th className="py-2 px-3 font-medium">Timestamp</th>
                    <th className="py-2 px-3 font-medium">Device</th>
                    <th className="py-2 px-3 font-medium">Action</th>
                    <th className="py-2 px-3 font-medium">Provisioning</th>
                    <th className="py-2 px-3 font-medium">Serial Number</th>
                    <th className="py-2 px-3 font-medium">Algorithm</th>
                    <th className="py-2 px-3 font-medium">Validity</th>
                    <th className="py-2 px-3 font-medium">Issued By</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, idx) => (
                    <tr key={it.id || idx} className="border-t hover:bg-muted/30">
                      <td className="py-2 px-3">
                        {it.timestamp ? new Date(it.timestamp).toLocaleString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                          hour12: false
                        }) : '-'}
                      </td>
                      <td className="py-2 px-3">
                        <div className="font-medium">{it.device_name || it.device_id || '-'}</div>
                        {it.device_name && it.device_id && (
                          <div className="text-xs text-muted-foreground">{it.device_id}</div>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <Badge className={cn('text-xs border', getActionBadgeColor(it.action))}>
                          {it.action || '-'}
                        </Badge>
                      </td>
                      <td className="py-2 px-3">
                        <ProvisioningMethodBadge
                          method={it.provisioning_method}
                          size="sm"
                          showIcon={true}
                          showTooltip={true}
                        />
                      </td>
                      <td className="py-2 px-3">
                        <span className="font-mono text-xs">{it.serial_number ? it.serial_number.slice(0, 20) + (it.serial_number.length > 20 ? '...' : '') : '-'}</span>
                      </td>
                      <td className="py-2 px-3">{it.algorithm || '-'}</td>
                      <td className="py-2 px-3">{it.validity_days ? `${it.validity_days} days` : '-'}</td>
                      <td className="py-2 px-3">{it.issued_by || '-'}</td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td className="py-4 px-3 text-muted-foreground text-center" colSpan={8}>
                        No certificate rotation history found for the selected filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {total > limit && (
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-muted-foreground">
                  Page {page + 1} of {Math.ceil(total / limit)}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={(page + 1) * limit >= total}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function EarlyRenewalsCard() {
  const [items, setItems] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { user: currentUser } = useAuth();
  const canView = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');
  const [deviceType, setDeviceType] = React.useState<string>('all');
  // Defaults: last 60 days
  const toLocalInput = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const now = new Date();
  const sixtyDaysAgo = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000);
  const [start, setStart] = React.useState<string>(toLocalInput(sixtyDaysAgo));
  const [end, setEnd] = React.useState<string>(toLocalInput(now));

  React.useEffect(() => {
    const load = async () => {
      setLoading(true); setError(null);
      try {
        const params = new URLSearchParams();
        if (start) params.set('start', start);
        if (end) params.set('end', end);
        if (deviceType && deviceType !== 'all') params.set('device_type', deviceType);
        const query = params.toString() ? `?${params.toString()}` : '';
        const token = AuthTokenManager.getToken();
        const res = await fetch(`/api/v1/certificates/audit/early-renewals${query}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setItems(data?.items || []);
      } catch (e: any) {
        setError(e.message || 'Failed to load');
      } finally {
        setLoading(false);
      }
    };
    if (canView) load();
  }, [canView, start, end, deviceType]);

  const downloadCsv = async () => {
    try {
      const params = new URLSearchParams();
      if (start) params.set('start', start);
      if (end) params.set('end', end);
      if (deviceType && deviceType !== 'all') params.set('device_type', deviceType);
      const query = params.toString() ? `?${params.toString()}` : '';
      const token = AuthTokenManager.getToken();
      const res = await fetch(`/api/v1/certificates/audit/early-renewals${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const rows = [['timestamp','device','user','days_remaining','justification']].concat(
        (data?.items||[]).map((it:any)=>[
          new Date(it.timestamp).toISOString(),
          it.resource_id || it.details?.device_id || '',
          it.user?.email || it.user?.username || '',
          it.details?.days_remaining ?? '',
          (it.details?.justification||'').replace(/\n/g,' ')
        ])
      );
      const csv = rows.map(r=>r.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'early-renewals.csv';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e:any) {
      toast.error(`Export failed: ${e.message}`);
    }
  };

  if (!canView) return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Early Renewals (Admin Only)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>Only organization administrators can view audit reports.</AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Early Renewal Audit (days_remaining &gt; threshold)
        </CardTitle>
        <CardDescription>Last 500 entries</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-3 mb-4">
          <div>
            <Label className="text-xs">Start</Label>
            <Input type="datetime-local" value={start} onChange={e=>setStart(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs">End</Label>
            <Input type="datetime-local" value={end} onChange={e=>setEnd(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs">Device Type</Label>
            <Select value={deviceType} onValueChange={setDeviceType}>
              <SelectTrigger className="w-[180px]"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="sensor">sensor</SelectItem>
                <SelectItem value="actuator">actuator</SelectItem>
                <SelectItem value="controller">controller</SelectItem>
                <SelectItem value="gateway">gateway</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto">
            <Button variant="outline" onClick={downloadCsv}>Export CSV</Button>
          </div>
        </div>
        {loading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : error ? (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="py-2 pr-4">Timestamp</th>
                  <th className="py-2 pr-4">Device</th>
                  <th className="py-2 pr-4">User</th>
                  <th className="py-2 pr-4">Days Remaining</th>
                  <th className="py-2 pr-4">Justification</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-b">
                    <td className="py-2 pr-4">{it.timestamp ? new Date(it.timestamp).toLocaleString() : '-'}</td>
                    <td className="py-2 pr-4">{it.resource_id || it.details?.device_id || '-'}</td>
                    <td className="py-2 pr-4">{it.user?.email || it.user?.username || '-'}</td>
                    <td className="py-2 pr-4">{it.details?.days_remaining ?? '-'}</td>
                    <td className="py-2 pr-4 max-w-[360px] truncate" title={it.details?.justification || ''}>{it.details?.justification || '-'}</td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr><td className="py-4 text-muted-foreground" colSpan={5}>No early renewals found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
function OrgCertificatePolicyCard() {
  const { user: currentUser } = useAuth();
  const [threshold, setThreshold] = React.useState<number>(60);
  const [autoRevoke, setAutoRevoke] = React.useState<boolean>(false);
  const [requireCSR, setRequireCSR] = React.useState<boolean>(true);
  const [allowServerKeyGen, setAllowServerKeyGen] = React.useState<boolean>(false);
  // Retain is now implied by Allow; kept for backward-compatibility/mismatch detection
  const [retainKeyAtRest, setRetainKeyAtRest] = React.useState<boolean>(false);
  const [oneTimeEncrypted, setOneTimeEncrypted] = React.useState<boolean>(true);
  // Bundle inclusion policy (org-level)
  const [allowBundleIncludePassword, setAllowBundleIncludePassword] = React.useState<boolean>(false);
  const [allowBundleIncludeApiKey, setAllowBundleIncludeApiKey] = React.useState<boolean>(false);
  const [source, setSource] = React.useState<string>('default');
  const [saving, setSaving] = React.useState(false);
  const isAdmin = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [warnMsg, setWarnMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    const load = async () => {
      try {
        const token = AuthTokenManager.getToken();
        const res = await fetch('/api/v1/certificates/policies/certificates', {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (res.ok) {
          const data = await res.json();
          const pol = data?.policy || {};
          if (typeof pol?.early_renewal_threshold_days === 'number') setThreshold(pol.early_renewal_threshold_days);
          if (typeof pol?.auto_revoke_on_renew === 'boolean') setAutoRevoke(pol.auto_revoke_on_renew);
          if (typeof pol?.require_csr === 'boolean') setRequireCSR(pol.require_csr);
          // Merge toggles: Allow is considered enabled only when both allow+retain are true
          const allow = !!pol?.allow_server_side_key_gen;
          const retain = !!pol?.retain_private_key_at_rest;
          setAllowServerKeyGen(allow && retain);
          setRetainKeyAtRest(retain);
          if (typeof pol?.one_time_encrypted_key_delivery === 'boolean') setOneTimeEncrypted(pol.one_time_encrypted_key_delivery);
          if (typeof pol?.allow_bundle_include_password === 'boolean') setAllowBundleIncludePassword(pol.allow_bundle_include_password);
          if (typeof pol?.allow_bundle_include_api_key === 'boolean') setAllowBundleIncludeApiKey(pol.allow_bundle_include_api_key);
          setSource('org');
        }
      } catch {}
    };
    load();
  }, []);

  const save = async () => {
    // Validate before saving
    if (threshold < 1 || threshold > 3650) {
      setErrorMsg('Threshold must be between 1 and 3650 days.');
      return;
    }
    setSaving(true);
    try {
      const token = AuthTokenManager.getToken();
      const res = await fetch('/api/v1/certificates/policies/certificates', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          early_renewal_threshold_days: threshold,
          auto_revoke_on_renew: autoRevoke,
          require_csr: requireCSR,
          // Single-toggle: enabling Allow also enables Retain
          allow_server_side_key_gen: allowServerKeyGen,
          retain_private_key_at_rest: allowServerKeyGen,
          one_time_encrypted_key_delivery: oneTimeEncrypted,
          allow_bundle_include_password: allowBundleIncludePassword,
          allow_bundle_include_api_key: allowBundleIncludeApiKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Save failed (${res.status})`);
      }
      setSource('org');
      // Broadcast policy update so open dialogs can sync immediately
      try {
        const newPolicy = {
          early_renewal_threshold_days: threshold,
          auto_revoke_on_renew: autoRevoke,
          require_csr: requireCSR,
          allow_server_side_key_gen: allowServerKeyGen,
          retain_private_key_at_rest: allowServerKeyGen,
          one_time_encrypted_key_delivery: oneTimeEncrypted,
          allow_bundle_include_password: allowBundleIncludePassword,
          allow_bundle_include_api_key: allowBundleIncludeApiKey
        } as any;
        window.dispatchEvent(new CustomEvent('org-policy-updated', { detail: newPolicy }));
        window.dispatchEvent(new CustomEvent('certificate-dialog-soft-refresh', { detail: { reason: 'policy-updated' } }));
      } catch {}
      toast.success('Certificate policy updated');
    } catch (e: any) {
      toast.error(`Failed to update policy: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  // Handle slider/input changes with guardrails
  const updateThreshold = (v: number) => {
    const value = Math.max(1, Math.min(3650, Math.round(v)));
    setThreshold(value);
    // Recommendations: 90-day certs commonly renew at 15–30 days; for longer TTLs, ~20% of validity
    if (value > 120) {
      setWarnMsg('High threshold — ensure it matches your certificate TTL.');
    } else if (value > 30) {
      setWarnMsg('Above recommended 15–30 days for 90-day certificates.');
    } else {
      setWarnMsg(null);
    }
    setErrorMsg(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Organization Certificate Policy
        </CardTitle>
        <CardDescription>
          Configure early renewal threshold and revocation behavior
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="threshold">Early Renewal Threshold (days)</Label>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Slider
                value={[Math.min(180, Math.max(1, threshold))]}
                min={1}
                max={180}
                step={1}
                onValueChange={(vals) => updateThreshold(vals[0] ?? threshold)}
                disabled={!isAdmin}
              >
                <SliderThumb />
              </Slider>
              {/* Accurate tick marks aligned to scale */}
              {(() => {
                const min = 1, max = 180;
                const marks = [1, 30, 60, 90, 180];
                const pct = (v:number) => ((v - min) / (max - min)) * 100;
                return (
                  <div className="relative h-5 mt-1">
                    {marks.map(v => (
                      <span
                        key={v}
                        className="absolute text-xs text-muted-foreground select-none"
                        style={{ left: `${pct(v)}%`, transform: 'translateX(-50%)' }}
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                );
              })()}
            </div>
            <div className="w-[120px]">
              <Input
                id="threshold"
                type="number"
                min={1}
                max={3650}
                value={threshold}
                onChange={e => updateThreshold(parseInt(e.target.value || '0') || 0)}
                disabled={!isAdmin}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Quick set:</span>
            {[7, 15, 30, 45, 60].map((d) => (
              <Button key={d} size="sm" variant="outline" disabled={!isAdmin} onClick={() => updateThreshold(d)}>{d}d</Button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Recommendation: 15–30 days for 90‑day device certificates; for longer TTLs, consider ~20% of validity.
          </p>
          <p className="text-xs text-muted-foreground">Effective source: {source}</p>
          {warnMsg && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-yellow-700">{warnMsg}</AlertDescription>
            </Alert>
          )}
          {errorMsg && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-red-700">{errorMsg}</AlertDescription>
            </Alert>
          )}
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="auto-revoke">Auto‑revoke previous certificate after renewal</Label>
              <div className="text-sm text-muted-foreground">Applies to auto and CSR renewals; revokes the old certificate upon successful issuance.</div>
            </div>
            <Switch id="auto-revoke" checked={autoRevoke} onCheckedChange={setAutoRevoke} disabled={!isAdmin} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="require-csr">Require CSR (Production-default)</Label>
              <div className="text-sm text-muted-foreground">Device must generate and keep its private key; platform signs CSR.</div>
            </div>
            <Switch id="require-csr" checked={requireCSR} onCheckedChange={setRequireCSR} disabled={!isAdmin} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow-svr-keygen">Allow Server‑side Key Generation (implies key retention)</Label>
              <div className="text-sm text-muted-foreground">Enables Auto‑generate. When ON, the platform retains generated private keys at rest for controlled download. Prefer CSR for production.</div>
            </div>
            <Switch id="allow-svr-keygen" checked={allowServerKeyGen} onCheckedChange={(v)=>{ setAllowServerKeyGen(v); if (!v) setRetainKeyAtRest(false); }} disabled={!isAdmin} />
          </div>

          {allowServerKeyGen && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-yellow-700 text-sm">
                Security tradeoff: With server‑side key generation enabled, the platform will retain device private keys at rest for Auto‑generate flows only. Recommended for development or tightly‑controlled provisioning. For production, prefer CSR where devices keep their own private keys.
              </AlertDescription>
            </Alert>
          )}

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="one-time">One‑time Encrypted Key Delivery</Label>
              <div className="text-sm text-muted-foreground">When enabled and supported, private key is encrypted for the device on download.</div>
            </div>
            <Switch id="one-time" checked={oneTimeEncrypted} onCheckedChange={setOneTimeEncrypted} disabled={!isAdmin} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow-bundle-pass">Allow bundle to include password</Label>
              <div className="text-sm text-muted-foreground">Controls whether admins may include one‑time MQTT password in Server‑TLS bundle.</div>
            </div>
            <Switch id="allow-bundle-pass" checked={allowBundleIncludePassword} onCheckedChange={setAllowBundleIncludePassword} disabled={!isAdmin} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow-bundle-apikey">Allow bundle to include API key</Label>
              <div className="text-sm text-muted-foreground">Controls whether admins may include HTTPS API key in Server‑TLS bundle.</div>
            </div>
            <Switch id="allow-bundle-apikey" checked={allowBundleIncludeApiKey} onCheckedChange={setAllowBundleIncludeApiKey} disabled={!isAdmin} />
          </div>

          <Button onClick={save} disabled={!isAdmin || saving || !!errorMsg}>Save</Button>
        </div>
      </CardContent>
    </Card>
  );
}
