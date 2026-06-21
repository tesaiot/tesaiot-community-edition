/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useState } from 'react';
import { Cloud, ExternalLink } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { organizationService } from '@/features/organizations/services/organizationService';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

interface UsageData {
  storage: number;
  storageLimit: number;
  apiCalls: number;
  apiCallsLimit: number;
  devices: number;
  devicesLimit: number;
}

export function SidebarFooter() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUsage() {
      if (!user?.organization_id) {
        setLoading(false);
        return;
      }

      try {
        const org = await organizationService.getOrganization(user.organization_id);
        if (org) {
          setUsage({
            storage: org.storage_bytes || org.usage?.storage || 0,
            storageLimit: org.limits?.storage || -1,
            apiCalls: org.api_calls || org.usage?.apiCalls || 0,
            apiCallsLimit: org.limits?.apiCalls || -1,
            devices: org.device_count || org.usage?.devices || 0,
            devicesLimit: org.limits?.devices || -1,
          });
        }
      } catch (error) {
        console.error('[SidebarFooter] Failed to fetch usage:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchUsage();
  }, [user?.organization_id]);

  // Format storage size
  const formatStorage = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Format storage limit
  const formatStorageLimit = (gb: number): string => {
    if (gb === -1) return 'Unlimited';
    if (gb >= 1000) return `${(gb / 1000).toFixed(1)} TB`;
    return `${gb} GB`;
  };

  // Calculate percentage
  const getPercentage = (used: number, limit: number): number => {
    if (limit === -1) return 10; // Show minimal bar for unlimited
    if (limit === 0) return 0;
    return Math.min((used / (limit * 1024 * 1024 * 1024)) * 100, 100);
  };

  // Get color based on percentage
  const getBarColor = (percentage: number): string => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  if (loading) {
    return (
      <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
        <div className="animate-pulse">
          <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-20 mb-2"></div>
          <div className="h-1.5 bg-gray-200 dark:bg-gray-600 rounded w-full"></div>
        </div>
      </div>
    );
  }

  if (!usage) {
    // Show appropriate message for Super Admin or when org not found
    const isSuperAdmin = user?.role === 'super_admin';
    return (
      <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cloud className="h-4 w-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Storage</span>
          </div>
        </div>
        <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden mb-1.5">
          <div className="h-full w-[5%] bg-blue-500 rounded-full" />
        </div>
        <div className="text-[10px] text-gray-500 dark:text-gray-400">
          {isSuperAdmin ? 'Platform-wide (see Organizations)' : 'Not available'}
        </div>
      </div>
    );
  }

  const percentage = getPercentage(usage.storage, usage.storageLimit);
  const barColor = getBarColor(percentage);

  return (
    <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
      {/* Storage indicator */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Cloud className="h-4 w-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Storage</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden mb-1.5">
        <div
          className={cn("h-full rounded-full transition-all duration-300", barColor)}
          style={{ width: `${Math.max(percentage, 2)}%` }}
        />
      </div>

      {/* Usage text */}
      <div className="text-[10px] text-gray-500 dark:text-gray-400">
        {formatStorage(usage.storage)} of {formatStorageLimit(usage.storageLimit)} used
      </div>
    </div>
  );
}
