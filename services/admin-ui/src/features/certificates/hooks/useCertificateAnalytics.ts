/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Certificate } from '@/services/api/tesaApi';

export interface CertificateStats {
  total: number;
  active: number;
  expiring: number;
  expired: number;
  revoked: number;
}

export interface AlgorithmUsage {
  algorithm: string;
  count: number;
  percentage: number;
}

export interface PerformanceMetrics {
  averageRenewalTime: number;
  autoRenewalSuccessRate: number;
  apiResponseTime: number;
  vaultPkiHealth: 'healthy' | 'degraded' | 'unhealthy';
}

export interface CertificateDistribution {
  statusDistribution: Array<{
    status: string;
    count: number;
    percentage: number;
  }>;
  algorithmUsage: AlgorithmUsage[];
  expiryDistribution: Array<{
    range: string;
    count: number;
  }>;
}

export const useCertificateAnalytics = (certificates: Certificate[]) => {
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    averageRenewalTime: 2.3,
    autoRenewalSuccessRate: 98.5,
    apiResponseTime: 145,
    vaultPkiHealth: 'healthy'
  });

  const [recentActivity, setRecentActivity] = useState<Array<{
    action: string;
    timestamp: string;
    deviceId?: string;
    user?: string;
  }>>([]);

  const certStats = useMemo<CertificateStats>(() => {
    const getDaysUntilExpiry = (validTo: string) => {
      const expiry = new Date(validTo);
      const now = new Date();
      return Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    };

    return {
      total: certificates.length,
      active: certificates.filter(c => c.status === 'active').length,
      expiring: certificates.filter(c => {
        const days = getDaysUntilExpiry(c.validTo);
        return c.status === 'active' && days >= 0 && days <= 30;
      }).length,
      expired: certificates.filter(c => c.status === 'expired').length,
      revoked: certificates.filter(c => c.status === 'revoked').length,
    };
  }, [certificates]);

  const distribution = useMemo<CertificateDistribution>(() => {
    // Status distribution
    const statusDistribution = [
      { status: 'Active', count: certStats.active, percentage: 0 },
      { status: 'Expiring', count: certStats.expiring, percentage: 0 },
      { status: 'Expired', count: certStats.expired, percentage: 0 },
      { status: 'Revoked', count: certStats.revoked, percentage: 0 }
    ].map(item => ({
      ...item,
      percentage: certStats.total > 0 ? (item.count / certStats.total) * 100 : 0
    }));

    // Algorithm usage
    const algorithmMap = new Map<string, number>();
    certificates.forEach(cert => {
      const algo = cert.keyAlgorithm || 'Unknown';
      algorithmMap.set(algo, (algorithmMap.get(algo) || 0) + 1);
    });

    const algorithmUsage: AlgorithmUsage[] = Array.from(algorithmMap.entries()).map(([algorithm, count]) => ({
      algorithm,
      count,
      percentage: certStats.total > 0 ? (count / certStats.total) * 100 : 0
    }));

    // Expiry distribution
    const getDaysUntilExpiry = (validTo: string) => {
      const expiry = new Date(validTo);
      const now = new Date();
      return Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    };

    const expiryRanges = {
      'Expired': 0,
      '0-7 days': 0,
      '8-30 days': 0,
      '31-60 days': 0,
      '61-90 days': 0,
      '90+ days': 0
    };

    certificates.forEach(cert => {
      if (cert.status === 'active') {
        const days = getDaysUntilExpiry(cert.validTo);
        if (days < 0) expiryRanges['Expired']++;
        else if (days <= 7) expiryRanges['0-7 days']++;
        else if (days <= 30) expiryRanges['8-30 days']++;
        else if (days <= 60) expiryRanges['31-60 days']++;
        else if (days <= 90) expiryRanges['61-90 days']++;
        else expiryRanges['90+ days']++;
      }
    });

    const expiryDistribution = Object.entries(expiryRanges).map(([range, count]) => ({
      range,
      count
    }));

    return {
      statusDistribution,
      algorithmUsage,
      expiryDistribution
    };
  }, [certificates, certStats]);

  const getHealthScore = useCallback(() => {
    if (certStats.total === 0) return 0;
    
    const activePercentage = (certStats.active / certStats.total) * 100;
    const expiringPercentage = (certStats.expiring / certStats.total) * 100;
    const expiredPercentage = (certStats.expired / certStats.total) * 100;
    
    // Health score calculation (0-100)
    let score = 100;
    score -= expiredPercentage * 2; // Heavy penalty for expired certs
    score -= expiringPercentage * 0.5; // Light penalty for expiring certs
    score -= (100 - activePercentage) * 0.3; // Penalty for non-active certs
    
    return Math.max(0, Math.min(100, Math.round(score)));
  }, [certStats]);

  const getHealthStatus = useCallback(() => {
    const score = getHealthScore();
    if (score >= 90) return { status: 'Excellent', color: 'green' };
    if (score >= 75) return { status: 'Good', color: 'blue' };
    if (score >= 60) return { status: 'Fair', color: 'yellow' };
    if (score >= 40) return { status: 'Poor', color: 'orange' };
    return { status: 'Critical', color: 'red' };
  }, [getHealthScore]);

  const getComplianceScore = useCallback(() => {
    if (certStats.total === 0) return 100;
    
    // Compliance factors
    const factors = {
      noExpired: certStats.expired === 0 ? 25 : 0,
      minimalExpiring: certStats.expiring < certStats.total * 0.1 ? 25 : 0,
      highActive: certStats.active > certStats.total * 0.9 ? 25 : 10,
      performanceGood: performanceMetrics.autoRenewalSuccessRate > 95 ? 25 : 10
    };
    
    return Object.values(factors).reduce((sum, val) => sum + val, 0);
  }, [certStats, performanceMetrics]);

  const getTrends = useCallback(() => {
    // In a real implementation, this would analyze historical data
    return {
      certificatesIssuedThisMonth: Math.floor(Math.random() * 50) + 10,
      certificatesRenewedThisMonth: Math.floor(Math.random() * 30) + 5,
      averageLifetime: 90, // days
      renewalRate: 85, // percentage
      monthOverMonthGrowth: 12.5 // percentage
    };
  }, []);

  // Load recent activity on mount
  useEffect(() => {
    // Simulate loading recent activity
    const mockActivity = [
      { action: 'Certificate Renewed', timestamp: new Date().toISOString(), deviceId: 'device-123' },
      { action: 'Certificate Created', timestamp: new Date(Date.now() - 3600000).toISOString(), deviceId: 'device-456' },
      { action: 'Certificate Downloaded', timestamp: new Date(Date.now() - 7200000).toISOString(), user: 'admin@tesa.local' },
      { action: 'Bulk Renewal Completed', timestamp: new Date(Date.now() - 10800000).toISOString() },
      { action: 'Certificate Revoked', timestamp: new Date(Date.now() - 14400000).toISOString(), deviceId: 'device-789' }
    ];
    setRecentActivity(mockActivity);
  }, []);

  return {
    certStats,
    distribution,
    performanceMetrics,
    recentActivity,
    getHealthScore,
    getHealthStatus,
    getComplianceScore,
    getTrends
  };
};