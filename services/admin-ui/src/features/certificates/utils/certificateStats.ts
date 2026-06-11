/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Certificate } from '@/services/api/tesaApi';
import { getDaysUntilExpiry, isExpiringSoon } from './certificateStatus';

/**
 * Certificate statistics interface
 */
export interface CertificateStats {
  total: number;
  active: number;
  expiring: number;
  expired: number;
  revoked: number;
}

/**
 * Calculate certificate statistics from a list of certificates
 * @param certificates - Array of certificates
 * @returns Certificate statistics object
 */
export const calculateCertificateStats = (certificates: Certificate[]): CertificateStats => {
  const expiringCerts = certificates.filter(cert => 
    isExpiringSoon(cert.validTo, cert.status)
  );

  return {
    total: certificates.length,
    active: certificates.filter(c => c.status === 'active').length,
    expiring: expiringCerts.length,
    expired: certificates.filter(c => c.status === 'expired').length,
    revoked: certificates.filter(c => c.status === 'revoked').length,
  };
};

/**
 * Calculate percentage for a specific status
 * @param count - Count of certificates with specific status
 * @param total - Total number of certificates
 * @returns Percentage as a fixed decimal string
 */
export const calculatePercentage = (count: number, total: number): string => {
  if (total === 0) return '0.0';
  return ((count / total) * 100).toFixed(1);
};

/**
 * Get expiring certificates from a list
 * @param certificates - Array of certificates
 * @param daysThreshold - Number of days to consider as "expiring soon" (default: 30)
 * @returns Array of expiring certificates
 */
export const getExpiringCertificates = (
  certificates: Certificate[], 
  daysThreshold: number = 30
): Certificate[] => {
  return certificates.filter(cert => {
    const days = getDaysUntilExpiry(cert.validTo);
    return cert.status === 'active' && days >= 0 && days <= daysThreshold;
  });
};

/**
 * Group certificates by algorithm type
 * @param certificates - Array of certificates
 * @returns Map of algorithm to count
 */
export const groupByAlgorithm = (certificates: Certificate[]): Map<string, number> => {
  const algorithmMap = new Map<string, number>();
  
  certificates.forEach(cert => {
    const algorithm = `${cert.keyAlgorithm} ${cert.keySize}`;
    algorithmMap.set(algorithm, (algorithmMap.get(algorithm) || 0) + 1);
  });
  
  return algorithmMap;
};

/**
 * Filter certificates based on search term and active tab
 * @param certificates - Array of certificates
 * @param searchTerm - Search term to filter by
 * @param activeTab - Active tab filter
 * @returns Filtered array of certificates
 */
export const filterCertificates = (
  certificates: Certificate[],
  searchTerm: string,
  activeTab: string
): Certificate[] => {
  return certificates.filter(cert => {
    const matchesSearch = 
      cert.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.issuer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.fingerprint.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (activeTab === 'all') return matchesSearch;
    if (activeTab === 'expiring') {
      const days = getDaysUntilExpiry(cert.validTo);
      return matchesSearch && days >= 0 && days <= 30;
    }
    return matchesSearch && cert.status === activeTab;
  });
};