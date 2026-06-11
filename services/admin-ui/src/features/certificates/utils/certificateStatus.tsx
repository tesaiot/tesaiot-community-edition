/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Badge } from '@/components/ui/badge';
import { CheckCircle, Clock, XCircle, AlertTriangle } from 'lucide-react';
import { Certificate } from '@/services/api/tesaApi';

/**
 * Get status badge component for a certificate
 * @param status - Certificate status
 * @returns React component displaying the status badge
 */
export const getStatusBadge = (status: Certificate['status']) => {
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

/**
 * Calculate days until certificate expiry
 * @param validTo - Certificate expiration date string
 * @returns Number of days until expiry (negative if already expired)
 */
export const getDaysUntilExpiry = (validTo: string): number => {
  const expiry = new Date(validTo);
  const now = new Date();
  const days = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  return days;
};

/**
 * Get expiry badge component for a certificate
 * @param validTo - Certificate expiration date string
 * @returns React component displaying the expiry badge
 */
export const getExpiryBadge = (validTo: string) => {
  const days = getDaysUntilExpiry(validTo);
  const expiry = new Date(validTo);
  const formattedDate = `${expiry.getMonth() + 1}/${expiry.getDate()}/${expiry.getFullYear()}`;
  
  if (days < 0) {
    return <Badge variant="destructive">Expired on {formattedDate}</Badge>;
  } else if (days < 30) {
    return <Badge variant="warning"><Clock className="mr-1 h-3 w-3" />Expires {formattedDate}</Badge>;
  } else if (days < 90) {
    return <Badge variant="secondary">Expires {formattedDate}</Badge>;
  } else {
    return <Badge variant="outline">{formattedDate}</Badge>;
  }
};

/**
 * Format a date string to a localized date format
 * @param dateString - Date string to format
 * @returns Formatted date string
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return `${date.getMonth() + 1}/${date.getDate()}/${date.getFullYear()}`;
};

/**
 * Check if a certificate is expiring soon (within 30 days)
 * @param validTo - Certificate expiration date string
 * @param status - Certificate status
 * @returns Boolean indicating if certificate is expiring soon
 */
export const isExpiringSoon = (validTo: string, status: Certificate['status']): boolean => {
  const days = getDaysUntilExpiry(validTo);
  return status === 'active' && days >= 0 && days <= 30;
};