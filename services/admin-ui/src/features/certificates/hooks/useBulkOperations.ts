/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback } from 'react';
import { tesaApi } from '@/services/api/tesaApi';
import { toast } from 'sonner';

export type BulkAction = 'renew' | 'revoke' | '';

export interface BulkOperationResult {
  device_id: string;
  status: 'success' | 'failed';
  message?: string;
  error?: string;
}

export interface BulkOperationResponse {
  results: BulkOperationResult[];
  summary: {
    total: number;
    succeeded: number;
    failed: number;
  };
}

export const useBulkOperations = (onComplete?: () => void) => {
  const [selectedCertificates, setSelectedCertificates] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState<BulkAction>('');
  const [isProcessing, setIsProcessing] = useState(false);

  const toggleCertificateSelection = useCallback((certId: string) => {
    const newSelection = new Set(selectedCertificates);
    if (newSelection.has(certId)) {
      newSelection.delete(certId);
    } else {
      newSelection.add(certId);
    }
    setSelectedCertificates(newSelection);
  }, [selectedCertificates]);

  const toggleSelectAll = useCallback((allCertIds: string[]) => {
    if (selectedCertificates.size === allCertIds.length) {
      setSelectedCertificates(new Set());
    } else {
      setSelectedCertificates(new Set(allCertIds));
    }
  }, [selectedCertificates]);

  const clearSelection = useCallback(() => {
    setSelectedCertificates(new Set());
    setBulkAction('');
  }, []);

  const handleBulkOperation = useCallback(async () => {
    if (selectedCertificates.size === 0) {
      toast.error('No certificates selected', {
        description: 'Please select certificates to perform bulk operations'
      });
      return;
    }

    if (!bulkAction) {
      toast.error('No action selected', {
        description: 'Please select a bulk action to perform'
      });
      return;
    }

    const confirmMessage = bulkAction === 'renew' 
      ? `Are you sure you want to renew ${selectedCertificates.size} certificates?`
      : `Are you sure you want to revoke ${selectedCertificates.size} certificates? This action cannot be undone.`;

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      setIsProcessing(true);
      const deviceIds = Array.from(selectedCertificates);
      
      const results = await tesaApi.bulkCertificateOperation({
        action: bulkAction,
        device_ids: deviceIds,
        reason: bulkAction === 'revoke' ? 'Bulk revocation' : undefined
      });

      const successCount = results.results.filter((r: BulkOperationResult) => r.status === 'success').length;
      const failedCount = results.results.filter((r: BulkOperationResult) => r.status === 'failed').length;

      if (successCount > 0) {
        toast.success(`Bulk ${bulkAction} completed`, {
          description: `Successfully processed ${successCount} certificates${failedCount > 0 ? `, ${failedCount} failed` : ''}`
        });
      } else {
        toast.error('Bulk operation failed', {
          description: `Failed to process all ${failedCount} certificates`
        });
      }

      // Clear selections and reload
      clearSelection();
      
      // Call the completion callback
      if (onComplete) {
        onComplete();
      }
      
    } catch (error) {
      toast.error('Bulk operation failed', {
        description: 'An error occurred during bulk operation'
      });
    } finally {
      setIsProcessing(false);
    }
  }, [selectedCertificates, bulkAction, clearSelection, onComplete]);

  const getSelectedCount = useCallback(() => {
    return selectedCertificates.size;
  }, [selectedCertificates]);

  const isSelected = useCallback((certId: string) => {
    return selectedCertificates.has(certId);
  }, [selectedCertificates]);

  const canPerformBulkAction = useCallback(() => {
    return selectedCertificates.size > 0 && bulkAction !== '';
  }, [selectedCertificates, bulkAction]);

  const getBulkActionMessage = useCallback(() => {
    if (selectedCertificates.size === 0) return '';
    
    const count = selectedCertificates.size;
    if (bulkAction === 'renew') {
      return `Renew ${count} certificate${count > 1 ? 's' : ''}`;
    } else if (bulkAction === 'revoke') {
      return `Revoke ${count} certificate${count > 1 ? 's' : ''}`;
    }
    return `${count} certificate${count > 1 ? 's' : ''} selected`;
  }, [selectedCertificates, bulkAction]);

  return {
    selectedCertificates,
    setSelectedCertificates,
    bulkAction,
    setBulkAction,
    isProcessing,
    toggleCertificateSelection,
    toggleSelectAll,
    clearSelection,
    handleBulkOperation,
    getSelectedCount,
    isSelected,
    canPerformBulkAction,
    getBulkActionMessage
  };
};