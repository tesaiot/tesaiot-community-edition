/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertTriangle,
  Shield,
  ShieldCheck,
  ShieldX,
  ShieldAlert,
  MoreVertical,
  RefreshCw,
  Download,
  Clock,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
  History,
  Loader2,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatDistanceToNow, format } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { tesaApi } from '@/services/api/tesaApi';
import { useAuth } from '@/hooks/useAuth';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { CertificateManagementService } from '../services/certificateManagementService';
import { ProvisioningMethodBadge } from './ProvisioningMethodBadge';

interface Certificate {
  id: string;
  deviceId: string;
  deviceName: string;
  deviceType: string;
  status: 'active' | 'expiring' | 'expired' | 'revoked' | 'no_cert' | 'server_tls';
  issuedAt: string;
  expiresAt: string;
  daysUntilExpiry: number | null;
  serialNumber: string;
  algorithm: string;
  organization?: string;
  ownerEmail?: string;
  isCaOnly?: boolean;
  provisioningMethod?: 'sw_csr' | 'hsm_csr' | 'hsm_protected_update' | string;
  trustMUid?: string;
}

interface CertificateStats {
  totalDevices: number;
  withCertificates: number;
  active: number;
  expiring: number;
  expired: number;
  noCert: number;
  serverTls: number;
  mtlsDevices: number; // withCertificates - serverTls
}

interface CaChainEntry {
  label: string;
  source: string;
  subject: string;
  issuer: string;
  serial_number: string;
  signature_algorithm: string;
  public_key_algorithm: string;
  not_before: string;
  not_after: string;
  days_remaining: number;
}

interface CertificateHistoryEntry {
  action: string;
  timestamp: string;
  serial_number?: string;
  algorithm?: string;
  validity_days?: number;
  issued_by?: string;
  reason?: string;
  old_serial?: string;
  new_serial?: string;
  provisioning_method?: 'sw_csr' | 'hsm_csr' | 'hsm_protected_update' | string;
  method?: string; // CSR method: 'csr' or 'protected_update'
}

interface DeviceCertificateHistory {
  device_id: string;
  device_name: string;
  current_certificate: {
    serial_number: string;
    issued_at: string;
    expires_at: string;
    algorithm: string;
    status: string;
  } | null;
  history: CertificateHistoryEntry[];
  total_rotations: number;
}

interface CertificateMonitoringDashboardProps {
  className?: string;
  showRefreshButton?: boolean;
  onCertificateRenew?: (certificate: Certificate) => void;
  onCertificateRevoke?: (certificate: Certificate) => void;
  onOpenDeviceOverview?: (certificate: Certificate) => void;
  onOpenDeviceLifecycle?: (certificate: Certificate) => void;
  showAdvancedFilters?: boolean; // for Certificates tab
  atRiskOnly?: boolean; // show only expiring/expired when true (Dashboard)
}

const getCertificateStatus = (daysUntilExpiry: number | null): Certificate['status'] => {
  if (typeof daysUntilExpiry !== 'number' || Number.isNaN(daysUntilExpiry)) {
    return 'active';
  }
  if (daysUntilExpiry < 0) return 'expired';
  if (daysUntilExpiry <= 30) return 'expiring';
  return 'active';
};

const getStatusColor = (status: Certificate['status']) => {
  switch (status) {
    case 'active':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'expiring':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'expired':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'revoked':
      return 'text-gray-600 bg-gray-50 border-gray-200';
    case 'server_tls':
      return 'text-blue-700 bg-blue-50 border-blue-200';
    case 'no_cert':
      return 'text-gray-600 bg-gray-50 border-gray-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

const getStatusIcon = (status: Certificate['status']) => {
  switch (status) {
    case 'active':
      return <ShieldCheck className="h-4 w-4" />;
    case 'expiring':
      return <ShieldAlert className="h-4 w-4" />;
    case 'expired':
      return <ShieldX className="h-4 w-4" />;
    case 'revoked':
      return <ShieldX className="h-4 w-4" />;
    case 'no_cert':
      return <Shield className="h-4 w-4" />;
    case 'server_tls':
      return <Shield className="h-4 w-4" />;
    default:
      return <Shield className="h-4 w-4" />;
  }
};

const getStatusText = (status: Certificate['status']) => {
  switch (status) {
    case 'no_cert':
      return 'No Certificate';
    case 'server_tls':
      return 'Server TLS';
    default:
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
};

const getCaBadgeTone = (daysRemaining: number) => {
  if (daysRemaining <= 30) return 'bg-red-100 text-red-700 border-red-200';
  if (daysRemaining <= 180) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
  return 'bg-green-100 text-green-700 border-green-200';
};

const formatCaRemaining = (daysRemaining: number) => {
  if (daysRemaining >= 0) {
    return `${daysRemaining} days remaining`;
  }
  return `Expired ${Math.abs(daysRemaining)} days ago`;
};

// Mock data used only as visual fallback when API returns no data
const mockCertificates: Certificate[] = [
  {
    id: 'cert-001',
    deviceId: 'device-001',
    deviceName: 'Temperature Sensor #1',
    deviceType: 'sensor',
    status: 'expiring',
    issuedAt: '2024-01-15T10:00:00Z',
    expiresAt: '2025-01-15T10:00:00Z',
    daysUntilExpiry: 25,
    serialNumber: '1234567890ABCDEF',
    algorithm: 'RSA-2048',
    organization: 'BDH Corporation'
  },
  {
    id: 'cert-002',
    deviceId: 'device-002',
    deviceName: 'Humidity Sensor #2',
    deviceType: 'sensor',
    status: 'active',
    issuedAt: '2024-06-01T14:30:00Z',
    expiresAt: '2025-06-01T14:30:00Z',
    daysUntilExpiry: 120,
    serialNumber: 'FEDCBA0987654321',
    algorithm: 'RSA-2048',
    organization: 'BDH Corporation'
  },
  {
    id: 'cert-003',
    deviceId: 'device-003',
    deviceName: 'Pressure Sensor #3',
    deviceType: 'sensor',
    status: 'expired',
    issuedAt: '2023-12-01T09:15:00Z',
    expiresAt: '2024-12-01T09:15:00Z',
    daysUntilExpiry: -18,
    serialNumber: '1A2B3C4D5E6F7890',
    algorithm: 'RSA-2048',
    organization: 'BDH Corporation'
  },
];

export function CertificateMonitoringDashboard({
  className,
  showRefreshButton = true,
  onCertificateRenew,
  onCertificateRevoke,
  onOpenDeviceOverview,
  onOpenDeviceLifecycle,
  showAdvancedFilters = false,
  atRiskOnly = false,
}: CertificateMonitoringDashboardProps) {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [authModeFilter, setAuthModeFilter] = useState<string>('all');
  const [deviceTypeFilter, setDeviceTypeFilter] = useState<string>('all');
  const [orgFilter, setOrgFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const { user: currentUser } = useAuth();
  const isAdminRole = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');
  const isPlatformAdmin = currentUser?.role === 'platform_admin' || currentUser?.role === 'super_admin';
  const [caChainEntries, setCaChainEntries] = useState<CaChainEntry[] | null>(null);
  const [caChainLoading, setCaChainLoading] = useState(false);
  const certificateManagementService = useMemo(() => CertificateManagementService.getInstance(), []);

  // Expandable row state for certificate history
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [historyData, setHistoryData] = useState<Record<string, DeviceCertificateHistory>>({});
  const [historyLoading, setHistoryLoading] = useState<Record<string, boolean>>({});

  const mapApiCerts = (apiCerts: any[]): Certificate[] => {
    const now = Date.now();
    return (apiCerts || []).map((c: any) => {
      const validTo = c.validTo || c.expires_at || c.valid_to;
      const validFrom = c.validFrom || c.issued_at || c.valid_from;
      const rawStatus = String(c.status || c.certificate_status || '').toLowerCase();
      const isCaOnly = ['server_tls', 'server-tls', 'ca_only', 'ca-only'].includes(rawStatus);
      const daysLeft = validTo ? Math.floor((new Date(validTo).getTime() - now) / (1000 * 60 * 60 * 24)) : null;
      let status: Certificate['status'];

      if (isCaOnly) {
        status = 'server_tls';
      } else {
        status = getCertificateStatus(daysLeft);
      }

      return {
        id: c.id || c._id || c.serialNumber || c.fingerprint || String(Math.random()),
        deviceId: c.deviceId || c.device_id || '-',
        deviceName: c.deviceName || c.device_id || c.deviceId || 'Device',
        deviceType: c.deviceType || c.device_type || 'sensor',
        status,
        issuedAt: validFrom || '',
        expiresAt: validTo || '',
        daysUntilExpiry: isCaOnly ? null : daysLeft,
        serialNumber: c.serialNumber || c.fingerprint || c.id || '-',
        algorithm: c.algorithm || (isCaOnly ? 'CA chain' : 'RSA-2048'),
        organization: c.organizationId || c.organization_id,
        isCaOnly,
        provisioningMethod: c.provisioning_method || c.provisioningMethod,
      } as Certificate;
    });
  };

  const loadCaChainHealth = useCallback(async () => {
    if (!isPlatformAdmin) {
      setCaChainEntries(null);
      return;
    }

    try {
      setCaChainLoading(true);
      const data = await tesaApi.getCaChainHealth();
      const entries = (data?.entries || []).sort((a, b) => a.label.localeCompare(b.label));
      setCaChainEntries(entries);
    } catch (error) {
      console.error('Failed to load CA chain metadata:', error);
      setCaChainEntries([]);
    } finally {
      setCaChainLoading(false);
    }
  }, [isPlatformAdmin]);

  // Load certificate history for a device when row is expanded
  const loadCertificateHistory = useCallback(async (deviceId: string) => {
    console.log('[CertHistory] loadCertificateHistory called for:', deviceId);
    console.log('[CertHistory] historyData[deviceId]:', historyData[deviceId]);
    console.log('[CertHistory] historyLoading[deviceId]:', historyLoading[deviceId]);

    // Only skip if we have valid cached data with history array
    if (historyData[deviceId]?.history?.length > 0 || historyLoading[deviceId]) {
      console.log('[CertHistory] Skipping - already have data or loading');
      return;
    }

    console.log('[CertHistory] Fetching history from API...');
    setHistoryLoading(prev => ({ ...prev, [deviceId]: true }));
    try {
      const response = await tesaApi.get(`/certificates/devices/${deviceId}/history`);
      console.log('[CertHistory] API response:', response);
      setHistoryData(prev => ({ ...prev, [deviceId]: response.data }));
    } catch (error) {
      console.error(`[CertHistory] Failed to load certificate history for ${deviceId}:`, error);
      // Set empty history on error - but allow retry next time
      setHistoryData(prev => ({
        ...prev,
        [deviceId]: {
          device_id: deviceId,
          device_name: '',
          current_certificate: null,
          history: [],
          total_rotations: 0
        }
      }));
    } finally {
      setHistoryLoading(prev => ({ ...prev, [deviceId]: false }));
    }
  }, [historyData, historyLoading]);

  // Toggle row expansion
  const toggleRowExpansion = useCallback((deviceId: string) => {
    console.log('[CertHistory] toggleRowExpansion called for:', deviceId);
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(deviceId)) {
        console.log('[CertHistory] Collapsing row for:', deviceId);
        newSet.delete(deviceId);
      } else {
        console.log('[CertHistory] Expanding row for:', deviceId);
        newSet.add(deviceId);
        // Load history when expanding
        loadCertificateHistory(deviceId);
      }
      return newSet;
    });
  }, [loadCertificateHistory]);

  // Get action badge color
  const getActionBadgeColor = (action: string) => {
    switch (action.toLowerCase()) {
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

  const loadFromApi = async () => {
    setLoading(true);
    try {
      // Load devices and certificates in parallel to enrich names
      const orgParam = (currentUser as any)?.organization_id || (currentUser as any)?.organization || undefined;
      const [devices, certData] = await Promise.all([
        tesaApi.getDevices(orgParam ? { organization: orgParam } : undefined).catch(() => []),
        tesaApi.getCertificates(),
      ]);

      // Build name map keyed by both external device_id and DB id
      const deviceNameById: Record<string, string> = {};
      const deviceOwnerById: Record<string, string> = {};
      const deviceTrustMUidById: Record<string, string> = {};
      const deviceKeyInfo: Array<{ extId: string; dbId?: string; dbIdAlt?: string; name: string; type?: string; org?: string; raw: any }>=[];
      (devices || []).forEach((d: any) => {
        if (!d) return;
        const extId = d.deviceId || d.device_id || d.uuid; // external identifier only
        const dbId = d.id && d.id !== extId ? d.id : undefined; // sometimes REST returns id
        const dbIdAlt = d._id && d._id !== extId && d._id !== dbId ? d._id : undefined; // Mongo _id
        const name = d.name || d.deviceName || d.device_name || extId;
        const type = d.type || d.deviceType || d.device_type || 'sensor';
        const org = d.organizationId || d.organization_id;
        const owner = d.created_by || d.owner_email || '';
        if (extId) deviceNameById[extId] = name;
        if (dbId) deviceNameById[dbId] = name;
        if (dbIdAlt) deviceNameById[dbIdAlt] = name;
        if (extId) deviceOwnerById[extId] = owner;
        if (dbId) deviceOwnerById[dbId] = owner;
        if (dbIdAlt) deviceOwnerById[dbIdAlt] = owner;
        const trustMUid = d.trustm_uid || d.trust_m_uid || d.trustMUid || '';
        if (trustMUid) {
          if (extId) deviceTrustMUidById[extId] = trustMUid;
          if (dbId) deviceTrustMUidById[dbId] = trustMUid;
          if (dbIdAlt) deviceTrustMUidById[dbIdAlt] = trustMUid;
        }
        deviceKeyInfo.push({ extId, dbId, dbIdAlt, name, type, org, raw: d });
      });

      // Map certs and enrich with device names when available
      let mapped = mapApiCerts(certData).map((c) => ({
        ...c,
        deviceName: c.deviceName && c.deviceName !== c.deviceId
          ? c.deviceName
          : (deviceNameById[c.deviceId] || c.deviceName || c.deviceId || 'Device'),
        ownerEmail: deviceOwnerById[c.deviceId] || (c as any).ownerEmail,
        trustMUid: deviceTrustMUidById[c.deviceId] || '',
      }));
      // Add/synthesize rows for devices without certificates
      const seen = new Set(mapped.map(m => m.deviceId));
      deviceKeyInfo.forEach(({ extId, dbId, dbIdAlt, name, type, org, raw }) => {
        if (!extId) return;
        if (seen.has(extId) || (dbId && seen.has(dbId)) || (dbIdAlt && seen.has(dbIdAlt))) return;

        // Server-TLS detection
        const authMode = String(raw?.auth_mode || raw?.authType || '').toLowerCase();
        const certStatus = String(raw?.certificate_status || '').toLowerCase();
        const ownerEmail = raw?.created_by || raw?.owner_email || '';

        // Use device-level certificate fields if present
        const serial = raw?.certificate_serial || raw?.certificate?.serial || raw?.certificateSerial;
        const issued = raw?.certificate_issued_at || raw?.certificate?.issuedAt || raw?.certificateIssuedAt;
        const expires = raw?.certificate_expires_at || raw?.certificate?.expiresAt || raw?.certificateExpiresAt;
        const alg = raw?.certificate_algorithm || raw?.certificate?.algorithm || raw?.keyAlgorithm || raw?.certificateAlgorithm;

        const caOnly = authMode === 'server_tls' || certStatus === 'ca_only';
        if (caOnly) {
          const now = Date.now();
          const daysLeft = expires ? Math.floor((new Date(expires).getTime() - now) / (1000 * 60 * 60 * 24)) : null;
          mapped.push({
            id: `server-tls-${extId}`,
            deviceId: extId,
            deviceName: name,
            deviceType: type || 'sensor',
            status: 'server_tls',
            issuedAt: issued || '',
            expiresAt: expires || '',
            daysUntilExpiry: daysLeft,
            serialNumber: String(serial || 'CA-only'),
            algorithm: alg || 'CA chain',
            organization: org,
            ownerEmail,
            isCaOnly: true,
            trustMUid: deviceTrustMUidById[extId] || '',
          });
          seen.add(extId);
          if (dbId) seen.add(dbId);
          if (dbIdAlt) seen.add(dbIdAlt);
        } else if (serial || issued || expires) {
          const now = Date.now();
          const daysLeft = expires ? Math.floor((new Date(expires).getTime() - now) / (1000*60*60*24)) : 0;
          const status: Certificate['status'] = daysLeft < 0 ? 'expired' : (daysLeft <= 30 ? 'expiring' : 'active');
          mapped.push({
            id: `device-cert-${extId}`,
            deviceId: extId,
            deviceName: name,
            deviceType: type || 'sensor',
            status,
            issuedAt: issued || '',
            expiresAt: expires || '',
            daysUntilExpiry: daysLeft,
            serialNumber: String(serial || '-'),
            algorithm: alg || '-',
            organization: org,
            ownerEmail,
            trustMUid: deviceTrustMUidById[extId] || '',
          });
          seen.add(extId);
          if (dbId) seen.add(dbId);
          if (dbIdAlt) seen.add(dbIdAlt);
        } else {
          mapped.push({
            id: `no-cert-${extId}`,
            deviceId: extId,
            deviceName: name,
            deviceType: type || 'sensor',
            status: 'no_cert',
            issuedAt: '',
            expiresAt: '',
            daysUntilExpiry: 0,
            serialNumber: '-',
            algorithm: '-',
            organization: org,
            ownerEmail,
            trustMUid: deviceTrustMUidById[extId] || '',
          });
          if (dbId) seen.add(dbId);
          if (dbIdAlt) seen.add(dbIdAlt);
        }
      });
      // Opportunistic enrichment: fetch missing names per cert.deviceId if still unresolved
      const unresolved = mapped.filter(m => !deviceNameById[m.deviceId] && (!m.deviceName || m.deviceName === m.deviceId));
      if (unresolved.length > 0) {
        const limit = Math.min(unresolved.length, 20); // keep light
        const targets = unresolved.slice(0, limit);
        const results = await Promise.allSettled(targets.map(t => tesaApi.getDevice(t.deviceId).catch(() => null)));
        results.forEach((res, idx) => {
          if (res.status === 'fulfilled' && res.value && (res.value as any).name) {
            const name = (res.value as any).name;
            const id = targets[idx].deviceId;
            deviceNameById[id] = name;
          }
        });
        // Apply enriched names
        mapped = mapped.map(c => ({
          ...c,
          deviceName: deviceNameById[c.deviceId] || c.deviceName,
        }));
      }

      if (mapped.length > 0) {
        setCertificates(mapped);
      } else {
        // No data for this organization; show empty (no mock) in production
        if (import.meta.env.DEV) {
          setCertificates(mockCertificates);
        } else {
          setCertificates([]);
        }
      }
    } catch (e:any) {
      console.warn('CertificateMonitoringDashboard: API load failed:', e?.message);
      if (import.meta.env.DEV) {
        setCertificates(mockCertificates);
      } else {
        setCertificates([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFromApi();
  }, []);

  // Calculate statistics
  const stats: CertificateStats = certificates.reduce(
    (acc, cert) => {
      if (cert.status === 'no_cert') acc.noCert += 1;
      if (cert.status === 'active') acc.active += 1;
      if (cert.status === 'expiring') acc.expiring += 1;
      if (cert.status === 'expired') acc.expired += 1;
      if (cert.status === 'server_tls') acc.serverTls += 1;
      return acc;
    },
    { totalDevices: certificates.length, withCertificates: certificates.filter(c => c.status !== 'no_cert').length, active: 0, expiring: 0, expired: 0, noCert: 0, serverTls: 0, mtlsDevices: 0 }
  );
  stats.mtlsDevices = Math.max(0, stats.withCertificates - stats.serverTls);

  // Persist and restore advanced filters (Certificates tab)
  useEffect(() => {
    if (!showAdvancedFilters) return;
    const saved = localStorage.getItem('certsTableFilters');
    if (saved) {
      try {
        const obj = JSON.parse(saved);
        if (obj.status) setStatusFilter(obj.status);
        if (obj.authMode) setAuthModeFilter(obj.authMode);
        if (obj.deviceType) setDeviceTypeFilter(obj.deviceType);
        if (obj.org) setOrgFilter(obj.org);
        if (typeof obj.search === 'string') setSearchTerm(obj.search);
      } catch {}
    }
  }, [showAdvancedFilters]);

  useEffect(() => {
    if (!showAdvancedFilters) return;
    const obj = {
      status: statusFilter,
      authMode: authModeFilter,
      deviceType: deviceTypeFilter,
      org: orgFilter,
      search: searchTerm,
    };
    localStorage.setItem('certsTableFilters', JSON.stringify(obj));
  }, [showAdvancedFilters, statusFilter, authModeFilter, deviceTypeFilter, orgFilter, searchTerm]);

  useEffect(() => {
    if (isPlatformAdmin) {
      loadCaChainHealth();
    }
  }, [isPlatformAdmin, loadCaChainHealth]);

  // Filter certificates based on search term and filters
  const filteredCertificates = certificates.filter((cert) => {
    const matchesSearch = cert.deviceName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         cert.serialNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         cert.deviceType.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || cert.status === statusFilter;
    const matchesAuthMode = authModeFilter === 'all' || (authModeFilter === 'server_tls' ? cert.status === 'server_tls' : cert.status !== 'server_tls' && cert.status !== 'no_cert');
    const matchesDeviceType = deviceTypeFilter === 'all' || (cert.deviceType || '').toLowerCase() === deviceTypeFilter;
    const matchesOrg = orgFilter === 'all' || (cert.organization || '') === orgFilter;
    const matchesAtRisk = !atRiskOnly || cert.status === 'expiring' || cert.status === 'expired';
    return matchesSearch && matchesStatus && matchesAuthMode && matchesDeviceType && matchesOrg && matchesAtRisk;
  });

  // Derived: top expiring within 30 days
  const topExpiring = certificates
    .filter(c => c.status === 'expiring' && c.daysUntilExpiry != null && c.daysUntilExpiry >= 0)
    .sort((a, b) => (a.daysUntilExpiry ?? 0) - (b.daysUntilExpiry ?? 0))
    .slice(0, 5);

  const refreshCertificates = async () => {
    await loadFromApi();
    if (isPlatformAdmin) {
      await loadCaChainHealth();
    }
    toast.success('Certificate data refreshed');
  };

  const canRenew = (c: Certificate) => {
    const ownerEmail = (c as any).ownerEmail || '';
    return isAdminRole || (!!ownerEmail && currentUser?.email && ownerEmail === currentUser.email);
  };

  const handleRenewCertificate = (certificate: Certificate) => {
    if (!canRenew(certificate)) return;
    if (onCertificateRenew) {
      onCertificateRenew(certificate);
    } else {
      toast.info(`Certificate renewal initiated for ${certificate.deviceName}`);
    }
  };

  const handleRevokeCertificate = (certificate: Certificate) => {
    if (!isAdminRole) return;
    if (onOpenDeviceLifecycle) {
      onOpenDeviceLifecycle(certificate);
      return;
    }
    if (onCertificateRevoke) {
      onCertificateRevoke(certificate);
    } else {
      toast.info(`Certificate revocation initiated for ${certificate.deviceName}`);
    }
  };

  const handleIssueCertificate = async (certificate: Certificate) => {
    try {
      await tesaApi.renewDeviceCertificate(certificate.deviceId);
      toast.success(`Certificate issued for ${certificate.deviceName}`);
      await refreshCertificates();
    } catch (e: any) {
      toast.error(`Failed to issue certificate: ${e?.message || 'Unknown error'}`);
    }
  };

  const downloadCertificate = useCallback(async (certificate: Certificate) => {
    if (onOpenDeviceOverview) {
      onOpenDeviceOverview(certificate);
      return;
    }
    if (!certificate?.deviceId) {
      toast.error('Missing device identifier for certificate download');
      return;
    }

    try {
      console.debug('[CertificateMonitoring] Download requested', {
        deviceId: certificate.deviceId,
        status: certificate.status,
        isCaOnly: certificate.isCaOnly
      });

      if (certificate.isCaOnly || certificate.status === 'server_tls') {
        toast.info('Downloading CA chain bundle');
        await tesaApi.downloadCaCertificate();
        return;
      }

      const result = await certificateManagementService.downloadCertificateBundle(certificate.deviceId);
      if (!result.success) {
        toast.error(result.error || 'Certificate download failed');
      }
    } catch (error: any) {
      console.error('[CertificateMonitoring] Download failed', error);
      toast.error(error?.message || 'Failed to download certificate bundle');
    }
  }, [certificateManagementService, onOpenDeviceOverview]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Devices</p>
                <p className="text-2xl font-bold">{stats.totalDevices}</p>
              </div>
              <Shield className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">With Certificates</p>
                <p className="text-2xl font-bold text-green-600">{stats.withCertificates}</p>
              </div>
              <ShieldCheck className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Expiring Soon</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.expiring}</p>
              </div>
              <ShieldAlert className="h-8 w-8 text-yellow-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Expired</p>
                <p className="text-2xl font-bold text-red-600">{stats.expired}</p>
              </div>
              <ShieldX className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">No Certificate</p>
                <p className="text-2xl font-bold text-gray-600">{stats.noCert}</p>
              </div>
              <ShieldX className="h-8 w-8 text-gray-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Server TLS</p>
                <p className="text-2xl font-bold text-blue-700">{stats.serverTls}</p>
              </div>
              <Shield className="h-8 w-8 text-blue-700" />
            </div>
          </CardContent>
        </Card>
      </div>

      {isPlatformAdmin && (
        <Card>
          <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4" />
                CA Chain Health
              </CardTitle>
              <CardDescription>Root and intermediate CA validity for the platform trust chain.</CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={loadCaChainHealth}
              disabled={caChainLoading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={cn('h-4 w-4', caChainLoading && 'animate-spin')} />
              Refresh
            </Button>
          </CardHeader>
          <CardContent>
            {caChainLoading ? (
              <div className="text-sm text-muted-foreground">Loading CA chain metadata…</div>
            ) : !caChainEntries || caChainEntries.length === 0 ? (
              <div className="text-sm text-muted-foreground">No CA chain information available.</div>
            ) : (
              <div className="space-y-4">
                {caChainEntries.map((entry) => {
                  const notAfter = new Date(entry.not_after);
                  return (
                    <div key={`${entry.label}-${entry.serial_number}`} className="border rounded-lg p-4">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-semibold">{entry.label}</div>
                          <div className="text-xs text-muted-foreground">
                            Expires {format(notAfter, 'MMM dd, yyyy')} ({formatDistanceToNow(notAfter, { addSuffix: true })})
                          </div>
                          <div className="text-xs text-muted-foreground truncate mt-2">Subject: {entry.subject}</div>
                          <div className="text-xs text-muted-foreground truncate">Issuer: {entry.issuer}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {entry.public_key_algorithm} • {entry.signature_algorithm}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Badge className={cn('text-xs border', getCaBadgeTone(entry.days_remaining))}>
                            {formatCaRemaining(entry.days_remaining)}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            Source: {entry.source}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Expiring Certificates Alert */}
      {stats.expiring > 0 && (
        <Alert className="border-yellow-200 bg-yellow-50">
          <AlertTriangle className="h-4 w-4 text-yellow-600" />
          <AlertTitle className="text-yellow-800">Certificate Expiration Warning</AlertTitle>
          <AlertDescription className="text-yellow-700">
            {stats.expiring} certificate{stats.expiring > 1 ? 's' : ''} will expire within 30 days.
            Please renew them to maintain device connectivity.
          </AlertDescription>
        </Alert>
      )}

      {/* Expired Certificates Alert */}
      {stats.expired > 0 && (
        <Alert className="border-red-200 bg-red-50">
          <ShieldX className="h-4 w-4 text-red-600" />
          <AlertTitle className="text-red-800">Expired Certificates</AlertTitle>
          <AlertDescription className="text-red-700">
            {stats.expired} certificate{stats.expired > 1 ? 's have' : ' has'} expired.
            Devices with expired certificates may lose connectivity.
          </AlertDescription>
        </Alert>
      )}

      {/* Top Expiring (30d) */}
      {topExpiring.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Top Expiring (30 days)
            </CardTitle>
            <CardDescription>Soonest to expire. Consider renewing now.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {topExpiring.map((c) => (
                <div key={`top-${c.id}`} className="flex items-center py-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{c.deviceName}</div>
                    <div className="text-xs text-muted-foreground">Expires {c.expiresAt ? format(new Date(c.expiresAt), 'MMM dd, yyyy') : '—'}</div>
                  </div>
                  <div className={cn('text-sm font-medium mr-4', c.daysUntilExpiry <= 7 ? 'text-red-600' : 'text-yellow-600')}>
                    {c.daysUntilExpiry} days
                  </div>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button size="sm" variant="outline" onClick={() => handleRenewCertificate(c)} disabled={!canRenew(c)}>
                            <RefreshCw className="h-3 w-3 mr-1" /> Renew
                          </Button>
                        </span>
                      </TooltipTrigger>
                      {!canRenew(c) && (
                        <TooltipContent>Not owner (Admin required)</TooltipContent>
                      )}
                    </Tooltip>
                  </TooltipProvider>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Certificates Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                {atRiskOnly ? 'At-Risk Certificates' : 'Certificate Management'}
              </CardTitle>
              <CardDescription>
                {atRiskOnly ? 'Showing only Expiring and Expired certificates' : 'Monitor certificate status and manage renewals'}
              </CardDescription>
            </div>
            {showRefreshButton && (
              <Button
                variant="outline"
                onClick={refreshCertificates}
                disabled={loading}
                className="flex items-center gap-2"
              >
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                Refresh
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex flex-col sm:flex-row flex-wrap gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search certificates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            {!atRiskOnly && (
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="expiring">Expiring Soon</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
                <SelectItem value="revoked">Revoked</SelectItem>
                <SelectItem value="no_cert">No Certificate</SelectItem>
                <SelectItem value="server_tls">Server TLS</SelectItem>
              </SelectContent>
            </Select>
            )}

            {showAdvancedFilters && !atRiskOnly && (
              <>
                <Select value={authModeFilter} onValueChange={setAuthModeFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Auth Mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Auth Modes</SelectItem>
                    <SelectItem value="mtls">mTLS</SelectItem>
                    <SelectItem value="server_tls">Server TLS</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={deviceTypeFilter} onValueChange={setDeviceTypeFilter}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Device Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="sensor">sensor</SelectItem>
                    <SelectItem value="actuator">actuator</SelectItem>
                    <SelectItem value="controller">controller</SelectItem>
                    <SelectItem value="gateway">gateway</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={orgFilter} onValueChange={setOrgFilter}>
                  <SelectTrigger className="w-full sm:w-[220px]">
                    <SelectValue placeholder="Organization" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Organizations</SelectItem>
                    {Array.from(new Set(certificates.map(c => c.organization).filter(Boolean) as string[])).map(org => (
                      <SelectItem key={org} value={org}>{org}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </>
            )}
          </div>

          {/* Certificates Table */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>Device</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead>Days Left</TableHead>
                  <TableHead>Algorithm</TableHead>
                  <TableHead>Provisioning</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCertificates.map((certificate) => {
                  const isExpanded = expandedRows.has(certificate.deviceId);
                  const history = historyData[certificate.deviceId];
                  const isLoadingHistory = historyLoading[certificate.deviceId];
                  const canExpand = certificate.status !== 'no_cert' && certificate.status !== 'server_tls';

                  return (
                    <React.Fragment key={certificate.id}>
                      <TableRow className={cn(isExpanded && 'bg-muted/30')}>
                        <TableCell className="w-8 p-2">
                          {canExpand && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => toggleRowExpansion(certificate.deviceId)}
                            >
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{certificate.deviceName}</div>
                            <div className="text-sm text-muted-foreground">
                              {certificate.serialNumber}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={cn('flex items-center gap-1 w-fit whitespace-nowrap', getStatusColor(certificate.status))}>
                            {getStatusIcon(certificate.status)}
                            {getStatusText(certificate.status)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {certificate.issuedAt ? format(new Date(certificate.issuedAt), 'MMM dd, yyyy') : '-'}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {certificate.expiresAt ? format(new Date(certificate.expiresAt), 'MMM dd, yyyy') : '-'}
                          </div>
                        </TableCell>
                        <TableCell>
                          {certificate.status === 'server_tls' ? (
                            <TooltipProvider delayDuration={150}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="text-sm font-medium text-blue-700 cursor-help">
                                    N/A (CA chain)
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs">
                                  This device relies on the shared platform CA chain. No individual leaf certificate is issued, so days remaining are not tracked here.
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : (
                            <div
                              className={cn(
                                'text-sm font-medium',
                                certificate.status === 'no_cert' || certificate.daysUntilExpiry == null
                                  ? 'text-gray-600'
                                  : certificate.daysUntilExpiry < 0
                                    ? 'text-red-600'
                                    : certificate.daysUntilExpiry <= 30
                                      ? 'text-yellow-600'
                                      : 'text-green-600'
                              )}
                            >
                              {certificate.status === 'no_cert' || certificate.daysUntilExpiry == null
                                ? '-'
                                : certificate.daysUntilExpiry < 0
                                  ? `${Math.abs(certificate.daysUntilExpiry)} days ago`
                                  : `${certificate.daysUntilExpiry} days`}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{certificate.algorithm || '-'}</div>
                        </TableCell>
                        <TableCell>
                          {certificate.status !== 'no_cert' && certificate.status !== 'server_tls' ? (
                            <ProvisioningMethodBadge
                              method={certificate.provisioningMethod}
                              size="sm"
                              showIcon={true}
                              showTooltip={true}
                            />
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          {certificate.status !== 'no_cert' && certificate.status !== 'server_tls' && (
                            <DropdownMenuItem
                              onClick={() => downloadCertificate(certificate)}
                              className="flex items-center gap-2"
                            >
                              <Download className="h-4 w-4" />
                              Download Certificate
                            </DropdownMenuItem>
                          )}
                          {certificate.status === 'server_tls' && (
                            <DropdownMenuItem
                              onClick={() => tesaApi.downloadCaCertificate()}
                              className="flex items-center gap-2"
                            >
                              <Download className="h-4 w-4" />
                              Download CA Chain
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          {(certificate.status === 'expiring' || certificate.status === 'expired') && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>
                                    <DropdownMenuItem
                                      onClick={() => handleRenewCertificate(certificate)}
                                      className="flex items-center gap-2 text-blue-600"
                                      disabled={!canRenew(certificate)}
                                    >
                                      <RefreshCw className="h-4 w-4" />
                                      Renew Certificate
                                    </DropdownMenuItem>
                                  </span>
                                </TooltipTrigger>
                                {!canRenew(certificate) && (
                                  <TooltipContent>Not owner (Admin required)</TooltipContent>
                                )}
                              </Tooltip>
                            </TooltipProvider>
                          )}
                          {certificate.status === 'active' && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>
                                    <DropdownMenuItem
                                      onClick={() => handleRevokeCertificate(certificate)}
                                      className="flex items-center gap-2 text-red-600"
                                      disabled={!isAdminRole}
                                    >
                                      <ShieldX className="h-4 w-4" />
                                      Revoke Certificate
                                    </DropdownMenuItem>
                                  </span>
                                </TooltipTrigger>
                                {!isAdminRole && (
                                  <TooltipContent>Admin only</TooltipContent>
                                )}
                              </Tooltip>
                            </TooltipProvider>
                          )}
                          {certificate.status === 'no_cert' && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>
                                    <DropdownMenuItem
                                      onClick={() => handleIssueCertificate(certificate)}
                                      className="flex items-center gap-2 text-blue-600"
                                      disabled={!isAdminRole}
                                    >
                                      <ShieldCheck className="h-4 w-4" />
                                      Issue Certificate
                                    </DropdownMenuItem>
                                  </span>
                                </TooltipTrigger>
                                {!isAdminRole && (
                                  <TooltipContent>Admin only</TooltipContent>
                                )}
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                        </TableCell>
                      </TableRow>

                      {/* Expanded History Row */}
                      {isExpanded && canExpand && (
                        <TableRow className="bg-muted/20 hover:bg-muted/30">
                          <TableCell colSpan={8} className="p-0">
                            <div className="px-6 py-4 border-t border-muted">
                              <div className="flex items-center gap-2 mb-3">
                                <History className="h-4 w-4 text-muted-foreground" />
                                <span className="font-medium text-sm">Certificate History</span>
                                {history && (
                                  <Badge variant="outline" className="text-xs">
                                    {history.total_rotations} rotation{history.total_rotations !== 1 ? 's' : ''}
                                  </Badge>
                                )}
                              </div>
                              {certificate.trustMUid && (
                                <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-md bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800">
                                  <Shield className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                                  <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">Trust M UID:</span>
                                  <span className="text-xs font-mono text-blue-600 dark:text-blue-400 break-all">{certificate.trustMUid}</span>
                                </div>
                              )}

                              {isLoadingHistory ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                  Loading history...
                                </div>
                              ) : history && history.history.length > 0 ? (
                                <div className="space-y-2">
                                  {history.history.map((entry, idx) => (
                                    <div
                                      key={`${entry.timestamp}-${idx}`}
                                      className="flex items-start gap-4 p-3 rounded-md bg-background border"
                                    >
                                      <div className="flex flex-col gap-1.5 shrink-0">
                                        <Badge className={cn('text-xs border', getActionBadgeColor(entry.action))}>
                                          {entry.action}
                                        </Badge>
                                        {entry.provisioning_method && (
                                          <ProvisioningMethodBadge
                                            method={entry.provisioning_method}
                                            size="sm"
                                            showIcon={true}
                                            showTooltip={true}
                                          />
                                        )}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="text-sm">
                                          {entry.timestamp ? new Date(entry.timestamp).toLocaleString(undefined, {
                                            year: 'numeric',
                                            month: 'short',
                                            day: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                            hour12: false
                                          }) : '-'}
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
                                          {entry.serial_number && (
                                            <div>Serial: {entry.serial_number}</div>
                                          )}
                                          {entry.algorithm && (
                                            <div>Algorithm: {entry.algorithm}</div>
                                          )}
                                          {entry.validity_days && (
                                            <div>Validity: {entry.validity_days} days</div>
                                          )}
                                          {entry.issued_by && (
                                            <div>Issued by: {entry.issued_by}</div>
                                          )}
                                          {entry.reason && (
                                            <div>Reason: {entry.reason}</div>
                                          )}
                                          {entry.old_serial && entry.new_serial && (
                                            <div>
                                              Replaced: {entry.old_serial.slice(0, 16)}... → {entry.new_serial.slice(0, 16)}...
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-sm text-muted-foreground py-2">
                                  No certificate history available for this device.
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          {filteredCertificates.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No devices or certificates match your criteria.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
