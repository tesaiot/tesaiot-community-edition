/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback } from 'react';
import { tesaApi } from '@/services/api/tesaApi';
import { toast } from 'sonner';

export interface AuditEvent {
  timestamp: string;
  event_type: string;
  user_id?: string;
  ip_address?: string;
  details: any;
}

export type AuditFilter = 'all' | 'certificate_created' | 'certificate_renewed' | 'certificate_revoked' | 'certificate_downloaded' | 'api_access';

export const useCertificateAudit = () => {
  const [auditTrail, setAuditTrail] = useState<AuditEvent[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [auditFilter, setAuditFilter] = useState<AuditFilter>('all');
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  const loadAuditTrail = useCallback(async () => {
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
  }, []);

  const loadRecentActivity = useCallback(async () => {
    try {
      const data = await tesaApi.getRecentCertificateActivity();
      setRecentActivity(data);
    } catch (error) {
      console.error('Failed to load recent activity:', error);
    }
  }, []);

  const filterAuditEvents = useCallback((events: AuditEvent[]) => {
    if (auditFilter === 'all') return events;
    return events.filter(event => event.event_type === auditFilter);
  }, [auditFilter]);

  const getEventBadgeVariant = useCallback((eventType: string) => {
    if (eventType.includes('created')) return 'success';
    if (eventType.includes('renewed')) return 'default';
    if (eventType.includes('revoked')) return 'destructive';
    return 'secondary';
  }, []);

  const formatEventType = useCallback((eventType: string) => {
    return eventType.replace('certificate_', '').toUpperCase();
  }, []);

  const exportAuditLog = useCallback(async (format: 'csv' | 'json' = 'json') => {
    try {
      const token = localStorage.getItem('jwt_token');
      const url = `/api/v1/certificates/audit-trail/export?format=${format}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `certificate-audit-${new Date().toISOString()}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success('Audit Log Exported', {
        description: `Audit log exported successfully as ${format.toUpperCase()}`
      });
    } catch (error) {
      toast.error('Export Failed', {
        description: 'Failed to export audit log'
      });
    }
  }, []);

  const searchAuditLog = useCallback(async (query: string, startDate?: Date, endDate?: Date) => {
    try {
      setLoadingAudit(true);
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (startDate) params.append('start', startDate.toISOString());
      if (endDate) params.append('end', endDate.toISOString());
      
      const data = await tesaApi.searchCertificateAuditTrail(params.toString());
      setAuditTrail(data);
    } catch (error) {
      toast.error('Search Failed', {
        description: 'Failed to search audit trail'
      });
    } finally {
      setLoadingAudit(false);
    }
  }, []);

  return {
    auditTrail,
    loadingAudit,
    auditFilter,
    setAuditFilter,
    recentActivity,
    loadAuditTrail,
    loadRecentActivity,
    filterAuditEvents,
    getEventBadgeVariant,
    formatEventType,
    exportAuditLog,
    searchAuditLog
  };
};