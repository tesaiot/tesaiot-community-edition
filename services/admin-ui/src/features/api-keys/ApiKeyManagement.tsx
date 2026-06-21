/*
 * TESA IoT Platform
 * Copyright (c) 2024-2025 Assoc. Prof. Wiroon Sriborrirux (BDH Corporation)
 * Managed by: Thai Embedded Systems Association (TESA)
 *
 * License: TESA Collaboration License (TESA-COLLABORATION-2025)
 * SPDX-FileCopyrightText: 2024-2025 Wiroon Sriborrirux
 * SPDX-License-Identifier: LicenseRef-TESA-Collaboration-2025
 *
 * Notice:
 * - The Owner retains all rights. TESA is authorized to use, modify, and
 *   deploy the code to build the AIoT Foundation Platform.
 * - Public redistribution or sublicensing requires prior written consent from
 *   the Owner.
 * - See LICENSES/TESA-COLLABORATION-2025.txt for full terms.
 *
 * Contact: sriborrirux@gmail.com
 */

/**
 * Copyright (c) 2024-2025 Assoc. Prof. Wiroon Sriborrirux, BDH Corporation
 * Licensed under the Apache License, Version 2.0
 * Managed by: Thai Embedded Systems Association (TESA)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/**
 * TESA IoT Platform - API Key Management
 * Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.
 * 
 * Licensed through: Thai Embedded Systems Association (TESA)
 *  * 
 * This dual-licensed software is provided under either:
 * - Apache License 2.0 (for open-source community)
 * - Commercial License (for enterprise features)
 * 
 * Contact: sriborrirux@gmail.com
 * 
 * v2025.06-beta-8 - API Key Management for Organizations
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Key, RefreshCw, Shield, Activity, Zap, Radio, Gauge, Lock, Clock, Wifi, ChevronRight, BookOpen } from 'lucide-react';
import { authFetch } from '@/utils/auth-fetch';
import { toast } from 'sonner';
import { ApiKeyTable } from './components/ApiKeyTable';
import { CreateApiKeyDialog } from './components/CreateApiKeyDialog';
import { ApiKeyUsageDialog } from './components/ApiKeyUsageDialog';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

type AccessType = 'api' | 'streaming' | null;

interface AccessCardProps {
  title: string;
  tagline: string;
  badge: string;
  badgeVariant: 'emerald' | 'blue';
  icon: React.ReactNode;
  features: { icon: React.ReactNode; text: string }[];
  onClick: () => void;
  isActive?: boolean;
}

const AccessCard = ({
  title,
  tagline,
  badge,
  badgeVariant,
  icon,
  features,
  onClick,
  isActive = false,
}: AccessCardProps) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <Card
      className={cn(
        'relative overflow-hidden cursor-pointer transition-all duration-300',
        'hover:shadow-lg hover:border-primary/30',
        'group',
        isActive && 'ring-2 ring-primary border-primary'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      <div
        className={cn(
          'absolute inset-0 opacity-0 transition-opacity duration-300',
          isHovered && 'opacity-100',
          badgeVariant === 'emerald'
            ? 'bg-gradient-to-br from-emerald-500/5 to-transparent'
            : 'bg-gradient-to-br from-blue-500/5 to-transparent'
        )}
      />
      <CardContent className="relative p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'p-3 rounded-xl transition-colors duration-300',
                badgeVariant === 'emerald'
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                  : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
              )}
            >
              {icon}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">{title}</h3>
              <Badge
                variant="outline"
                className={cn(
                  'mt-1 text-xs font-medium',
                  badgeVariant === 'emerald'
                    ? 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20'
                    : 'border-blue-500/30 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                )}
              >
                {badge}
              </Badge>
            </div>
          </div>
          <ChevronRight
            className={cn(
              'h-5 w-5 text-muted-foreground transition-transform duration-300',
              isHovered && 'translate-x-1 text-primary'
            )}
          />
        </div>
        <p className="text-sm text-muted-foreground mb-5">{tagline}</p>
        <div className="space-y-2.5">
          {features.map((feature, index) => (
            <div key={index} className="flex items-center gap-2.5 text-sm">
              <span
                className={cn(
                  'p-1 rounded',
                  badgeVariant === 'emerald'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-blue-600 dark:text-blue-400'
                )}
              >
                {feature.icon}
              </span>
              <span className="text-foreground/80">{feature.text}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

interface ApiKey {
  id: string;
  name: string;
  description: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  status: 'active' | 'suspended' | 'revoked';
  usage_limits: {
    requests_per_minute: number;
    requests_per_day: number;
    concurrent_connections: number;
  };
}

interface UsageSummaryState {
  totalRequests: number;
  maxRequestsPerMinute: number;
}

export function ApiKeyManagement() {
  const { user, loading: authLoading } = useAuth();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedKeyForUsage, setSelectedKeyForUsage] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [usageSummary, setUsageSummary] = useState<UsageSummaryState>({
    totalRequests: 0,
    maxRequestsPerMinute: 0,
  });
  const [usageSummaryLoading, setUsageSummaryLoading] = useState(false);
  const [activeCard, setActiveCard] = useState<AccessType>(null);

  // Get organization ID from user
  const organizationId = user?.organization_id || user?.organizationId;

  // Debug logging
  useEffect(() => {
    console.log('ApiKeyManagement - Auth loading:', authLoading);
    console.log('ApiKeyManagement - User:', user);
    console.log('ApiKeyManagement - Organization ID:', organizationId);
    console.log('ApiKeyManagement - User full object:', JSON.stringify(user, null, 2));
  }, [authLoading, user, organizationId]);

  const formatCompactNumber = (value: number): string => {
    if (!Number.isFinite(value)) return '0';
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toLocaleString();
  };

  const updateUsageSummary = useCallback(
    async (keys: ApiKey[]) => {
      if (!organizationId || !keys.length) {
        setUsageSummary({ totalRequests: 0, maxRequestsPerMinute: 0 });
        return;
      }

      const activeKeys = keys.filter((key) => key.status === 'active');
      const keysToProcess = activeKeys.length ? activeKeys : keys;
      setUsageSummaryLoading(true);

      try {
        const metricsResponses = await Promise.all(
          keysToProcess.map(async (key) => {
            try {
              const response = await authFetch(
                `/api/v1/organizations/${organizationId}/api-keys/${key.id}/metrics?range=24h`,
              );
              if (!response.ok) {
                console.warn(`Failed to fetch metrics for API key ${key.id}:`, response.statusText);
                return 0;
              }
              const data = await response.json();
              return Number(data?.total_requests ?? 0);
            } catch (error) {
              console.error(`Error fetching metrics for API key ${key.id}:`, error);
              return 0;
            }
          }),
        );

        const totalRequests = metricsResponses.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
        const maxRequestsPerMinute = keysToProcess.reduce(
          (max, key) => Math.max(max, key?.usage_limits?.requests_per_minute ?? 0),
          0,
        );

        setUsageSummary({ totalRequests, maxRequestsPerMinute });
      } catch (error) {
        console.error('Error calculating usage summary:', error);
        const fallbackRate = keysToProcess.reduce(
          (max, key) => Math.max(max, key?.usage_limits?.requests_per_minute ?? 0),
          0,
        );
        setUsageSummary({ totalRequests: 0, maxRequestsPerMinute: fallbackRate });
      } finally {
        setUsageSummaryLoading(false);
      }
    },
    [organizationId],
  );

  const fetchApiKeys = useCallback(async () => {
    setLoading(true);
    // Don't show error if auth is still loading
    if (!organizationId) {
      if (!authLoading) {
        console.error('No organization ID found. User object:', user);
        toast.error('No organization found for current user');
      }
      setLoading(false);
      setUsageSummary({ totalRequests: 0, maxRequestsPerMinute: 0 });
      return;
    }

    try {
      const response = await authFetch(`/api/v1/organizations/${organizationId}/api-keys`);
      if (!response.ok) {
        throw new Error('Failed to fetch API keys');
      }
      const data = await response.json();
      const keys = (data.api_keys as ApiKey[]) || [];
      setApiKeys(keys);
      await updateUsageSummary(keys);
    } catch (error) {
      console.error('Error fetching API keys:', error);
      toast.error('Failed to load API keys');
      setUsageSummary({ totalRequests: 0, maxRequestsPerMinute: 0 });
    } finally {
      setLoading(false);
    }
  }, [organizationId, authLoading, updateUsageSummary]);

  useEffect(() => {
    // Only fetch if we have an organization ID or auth is done loading
    if (organizationId || !authLoading) {
      fetchApiKeys();
    }
  }, [fetchApiKeys, organizationId, authLoading]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchApiKeys();
    setRefreshing(false);
    toast.success('API keys refreshed');
  };

  const handleCreateSuccess = (newKey: any) => {
    // Add the new key to the list
    fetchApiKeys();
    toast.success('API key created successfully');
  };

  const handleRevoke = async (keyId: string) => {
    if (!organizationId) return;

    try {
      const response = await authFetch(
        `/api/v1/organizations/${organizationId}/api-keys/${keyId}`,
        { method: 'DELETE' }
      );
      if (!response.ok) {
        // Extract error details from response
        let errorMessage = 'Failed to revoke API key';
        let errorDetails = {};
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.error || errorMessage;
          errorDetails = errorData;
          console.error('API error response:', errorData);
          
          // Check for specific error types
          if (errorData.error && errorData.error.includes('AttributeError')) {
            errorMessage = 'Server configuration error. Please contact support.';
          } else if (response.status === 404) {
            errorMessage = 'API key not found or already deleted.';
          } else if (response.status === 403) {
            errorMessage = 'You do not have permission to delete this API key.';
          } else if (response.status === 500) {
            errorMessage = 'Internal server error. Please try again later.';
          }
        } catch (e) {
          // If response body can't be parsed as JSON
          console.error('Failed to parse error response:', e);
          errorMessage = `Server error (${response.status}): ${response.statusText}`;
        }
        console.error(`API key revocation failed - Status: ${response.status}, Message: ${errorMessage}, Details:`, errorDetails);
        throw new Error(errorMessage);
      }
      await fetchApiKeys();
      toast.success('API key revoked successfully');
    } catch (error) {
      console.error('Error revoking API key:', error);
      // Show detailed error message in toast
      toast.error(
        <div className="space-y-1">
          <p className="font-semibold">{error.message || 'Failed to revoke API key'}</p>
          <p className="text-xs text-muted-foreground">Check console for more details</p>
        </div>
      );
    }
  };

  const handleRotate = async (keyId: string) => {
    if (!organizationId) return;

    try {
      const response = await authFetch(
        `/api/v1/organizations/${organizationId}/api-keys/${keyId}/rotate`,
        { method: 'POST' }
      );
      if (!response.ok) {
        throw new Error('Failed to rotate API key');
      }
      const data = await response.json();
      await fetchApiKeys();
      
      // Show the new API key to the user
      toast.success(
        <div className="space-y-2">
          <p>API key rotated successfully!</p>
          <p className="text-xs">New key: {data.api_key}</p>
          <p className="text-xs text-muted-foreground">Save this key securely - it won't be shown again</p>
        </div>,
        { duration: 10000 }
      );
    } catch (error) {
      console.error('Error rotating API key:', error);
      toast.error('Failed to rotate API key');
    }
  };

  // Show loading state while auth is loading
  if (authLoading) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="py-16 text-center">
            <RefreshCw className="h-16 w-16 mx-auto mb-4 text-muted-foreground animate-spin" />
            <h2 className="text-2xl font-semibold mb-2">Loading...</h2>
            <p className="text-muted-foreground">
              Fetching user information...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Only show no organization error after auth has loaded
  if (!authLoading && !organizationId) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="py-16 text-center">
            <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-2xl font-semibold mb-2">No Organization Access</h2>
            <p className="text-muted-foreground">
              You need to be part of an organization to manage API keys.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Key className="h-8 w-8" />
            Developer Access
          </h1>
          <p className="text-muted-foreground mt-1">
            Choose your integration method to connect with TESAIoT Platform
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {(activeCard === 'api' || activeCard === null) && (
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create API Key
            </Button>
          )}
        </div>
      </div>

      {/* Access Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <AccessCard
          title="API Integration"
          tagline="High-performance gateway for secure platform access"
          badge="Secure REST"
          badgeVariant="emerald"
          icon={<Zap className="h-6 w-6" />}
          features={[
            { icon: <Gauge className="h-4 w-4" />, text: 'Dynamic rate limiting' },
            { icon: <Lock className="h-4 w-4" />, text: 'Scoped permissions' },
            { icon: <Shield className="h-4 w-4" />, text: 'Enterprise-grade security' },
          ]}
          onClick={() => setActiveCard(activeCard === 'api' ? null : 'api')}
          isActive={activeCard === 'api'}
        />

        <AccessCard
          title="Live Data Streaming"
          tagline="Real-time bi-directional data connectivity"
          badge="Secure WebSocket"
          badgeVariant="blue"
          icon={<Radio className="h-6 w-6" />}
          features={[
            { icon: <Clock className="h-4 w-4" />, text: 'Low latency' },
            { icon: <Activity className="h-4 w-4" />, text: 'Event-driven architecture' },
            { icon: <Wifi className="h-4 w-4" />, text: 'Subscribe to live telemetry' },
          ]}
          onClick={() => setActiveCard(activeCard === 'streaming' ? null : 'streaming')}
          isActive={activeCard === 'streaming'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Main Content - 3 columns */}
        <div className="xl:col-span-3 space-y-6">
          {/* Stats Cards - only show for API */}
          {(activeCard === 'api' || activeCard === null) && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Total API Keys</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{apiKeys.length}</div>
                  <p className="text-xs text-muted-foreground">
                    {apiKeys.filter(k => k.status === 'active').length} active
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Usage Today</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {usageSummaryLoading ? '…' : formatCompactNumber(usageSummary.totalRequests)}
                  </div>
                  <p className="text-xs text-muted-foreground">API calls in the last 24 hours</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Rate Limits</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {usageSummaryLoading
                      ? '…'
                      : usageSummary.maxRequestsPerMinute > 0
                        ? usageSummary.maxRequestsPerMinute.toLocaleString()
                        : '—'}
                  </div>
                  <p className="text-xs text-muted-foreground">Highest requests/minute across active keys</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* API Keys Table - show for API or null */}
          {(activeCard === 'api' || activeCard === null) && (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>API Keys</CardTitle>
                  <Badge variant="outline" className="gap-1">
                    <Activity className="h-3 w-3" />
                    APISIX Powered
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <ApiKeyTable
                  apiKeys={apiKeys}
                  loading={loading}
                  onRevoke={handleRevoke}
                  onRotate={handleRotate}
                  onViewUsage={(keyId) => setSelectedKeyForUsage(keyId)}
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - 1 column */}
        <div className="xl:col-span-1 space-y-6">
          {/* Quick Reference Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-primary" />
                Quick Reference
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Zap className="h-4 w-4 text-emerald-500" />
                  <span className="font-medium">REST API</span>
                </div>
                <code className="block text-xs bg-muted p-2 rounded break-all">
                  {`${window.location.origin}/api/v1`}
                </code>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Radio className="h-4 w-4 text-blue-500" />
                  <span className="font-medium">WSS MQTT</span>
                </div>
                <code className="block text-xs bg-muted p-2 rounded break-all">
                  {`wss://${window.location.hostname}:8084/mqtt`}
                </code>
              </div>
            </CardContent>
          </Card>

          {/* Usage Tips */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Integration Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Use <strong>REST API</strong> for device management, user operations, and batch data queries.</p>
              <p>Use <strong>WSS MQTT</strong> for real-time telemetry streaming and live device monitoring.</p>
              <p className="text-xs border-l-2 border-primary pl-3">
                Both methods support organization-scoped access with proper authentication.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Create API Key Dialog */}
      <CreateApiKeyDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        organizationId={organizationId}
        onSuccess={handleCreateSuccess}
      />

      {/* Usage Dialog */}
      {selectedKeyForUsage && (
        <ApiKeyUsageDialog
          keyId={selectedKeyForUsage}
          organizationId={organizationId}
          onClose={() => setSelectedKeyForUsage(null)}
        />
      )}
    </div>
  );
}
