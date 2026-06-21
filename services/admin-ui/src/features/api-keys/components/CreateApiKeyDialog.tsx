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
 * TESA IoT Platform - Create API Key Dialog
 * Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.
 * 
 * Licensed through: Thai Embedded Systems Association (TESA)
 *  * 
 * This dual-licensed software is provided under either:
 * - Apache License 2.0 (for open-source community)
 * - Commercial License (for enterprise features)
 * 
 * Contact: sriborrirux@gmail.com
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { authFetch } from '@/utils/auth-fetch';
import { toast } from 'sonner';
import { Copy, Key, Shield, Clock, Globe, Plus, X } from 'lucide-react';

interface CreateApiKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  organizationId: string;
  onSuccess: (apiKey: any) => void;
}

// Security Best Practice: Third-party partners should only have READ permissions
// WRITE permissions are hidden to prevent accidental privilege escalation
const AVAILABLE_SCOPES = [
  { value: 'devices:read', label: 'Read Devices', description: 'View device information' },
  // { value: 'devices:write', label: 'Write Devices', description: 'Create and update devices' }, // HIDDEN for third-party
  { value: 'telemetry:read', label: 'Read Telemetry', description: 'View telemetry data' },
  // { value: 'telemetry:write', label: 'Write Telemetry', description: 'Send telemetry data' }, // HIDDEN for third-party
  { value: 'organizations:read', label: 'Read Organizations', description: 'View organization info' },
  { value: 'certificates:read', label: 'Read Certificates', description: 'View certificates' },
  // { value: 'certificates:write', label: 'Write Certificates', description: 'Manage certificates' }, // HIDDEN for third-party
];

// For internal use only - can be enabled via environment variable or admin override
const WRITE_SCOPES_HIDDEN = [
  { value: 'devices:write', label: 'Write Devices', description: 'Create and update devices' },
  { value: 'telemetry:write', label: 'Write Telemetry', description: 'Send telemetry data' },
  { value: 'certificates:write', label: 'Write Certificates', description: 'Manage certificates' },
];

export function CreateApiKeyDialog({
  open,
  onOpenChange,
  organizationId,
  onSuccess,
}: CreateApiKeyDialogProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    scopes: ['devices:read', 'telemetry:read', 'organizations:read'], // Read-only by default
    rate_limit: 100, // Reduced default rate limit for third-party
    expires_in_days: 90, // Shorter default expiry for security
    ip_whitelist: [] as string[], // Optional IP whitelist
  });
  const [loading, setLoading] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [ipInput, setIpInput] = useState(''); // For IP address input

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('Please provide a name for the API key');
      return;
    }

    if (formData.scopes.length === 0) {
      toast.error('Please select at least one scope');
      return;
    }

    setLoading(true);
    try {
      const response = await authFetch(
        `/api/v1/organizations/${organizationId}/api-keys`,
        {
          method: 'POST',
          body: JSON.stringify(formData),
        }
      );

      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        console.error('Failed to parse response:', jsonError);
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }

      if (!response.ok) {
        console.error('API error response:', data);
        throw new Error(data.error || data.message || `Failed to create API key: ${response.status}`);
      }
      
      if (data.success && data.api_key) {
        setCreatedKey(data.api_key);
        onSuccess(data);
      } else {
        throw new Error(data.error || 'Failed to create API key');
      }
    } catch (error) {
      console.error('Error creating API key:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create API key';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleScopeToggle = (scope: string) => {
    setFormData((prev) => ({
      ...prev,
      scopes: prev.scopes.includes(scope)
        ? prev.scopes.filter((s) => s !== scope)
        : [...prev.scopes, scope],
    }));
  };

  // IP Whitelist Management Functions
  const validateIPAddress = (ip: string): boolean => {
    // Validate IPv4 address format
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipv4Regex.test(ip)) return false;
    
    // Check each octet is <= 255
    const octets = ip.split('.');
    return octets.every(octet => parseInt(octet) <= 255);
  };

  const validateCIDR = (cidr: string): boolean => {
    // Validate CIDR notation (e.g., 192.168.1.0/24)
    const cidrRegex = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
    if (!cidrRegex.test(cidr)) return false;
    
    const [ip, prefix] = cidr.split('/');
    if (!validateIPAddress(ip)) return false;
    
    const prefixNum = parseInt(prefix);
    return prefixNum >= 0 && prefixNum <= 32;
  };

  const handleAddIP = () => {
    const trimmedIP = ipInput.trim();
    
    if (!trimmedIP) {
      toast.error('Please enter an IP address or CIDR block');
      return;
    }

    // Validate IP or CIDR format
    if (!validateIPAddress(trimmedIP) && !validateCIDR(trimmedIP)) {
      toast.error('Invalid IP address or CIDR format. Use format like 192.168.1.1 or 192.168.1.0/24');
      return;
    }

    // Check for duplicates
    if (formData.ip_whitelist.includes(trimmedIP)) {
      toast.error('This IP address is already in the whitelist');
      return;
    }

    setFormData(prev => ({
      ...prev,
      ip_whitelist: [...prev.ip_whitelist, trimmedIP]
    }));
    setIpInput('');
    toast.success('IP address added to whitelist');
  };

  const handleRemoveIP = (ip: string) => {
    setFormData(prev => ({
      ...prev,
      ip_whitelist: prev.ip_whitelist.filter(item => item !== ip)
    }));
  };

  const copyToClipboard = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      toast.success('API key copied to clipboard');
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      description: '',
      scopes: ['devices:read', 'telemetry:read', 'organizations:read'], // Read-only by default
      rate_limit: 100, // Reduced default rate limit for third-party
      expires_in_days: 90, // Shorter default expiry for security
      ip_whitelist: [], // Reset IP whitelist
    });
    setCreatedKey(null);
    setIpInput(''); // Reset IP input field
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        {!createdKey ? (
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Create API Key
              </DialogTitle>
              <DialogDescription>
                Generate a new API key for programmatic access to the platform
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="Production API Key"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Key for production environment mobile app integration"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                />
              </div>

              <div className="space-y-2">
                <Label>Permissions (Scopes)</Label>
                <div className="space-y-2 rounded-lg border p-4">
                  {AVAILABLE_SCOPES.map((scope) => (
                    <div key={scope.value} className="flex items-start space-x-3">
                      <Checkbox
                        id={scope.value}
                        checked={formData.scopes.includes(scope.value)}
                        onCheckedChange={() => handleScopeToggle(scope.value)}
                      />
                      <div className="space-y-1">
                        <label
                          htmlFor={scope.value}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {scope.label}
                        </label>
                        <p className="text-xs text-muted-foreground">
                          {scope.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="rate_limit">Rate Limit (req/min)</Label>
                  <Select
                    value={formData.rate_limit.toString()}
                    onValueChange={(value) => setFormData({ ...formData, rate_limit: parseInt(value) })}
                  >
                    <SelectTrigger id="rate_limit">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="100">100 req/min</SelectItem>
                      <SelectItem value="500">500 req/min</SelectItem>
                      <SelectItem value="1000">1,000 req/min</SelectItem>
                      <SelectItem value="5000">5,000 req/min</SelectItem>
                      <SelectItem value="10000">10,000 req/min</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expires">Expires In</Label>
                  <Select
                    value={formData.expires_in_days.toString()}
                    onValueChange={(value) => setFormData({ ...formData, expires_in_days: parseInt(value) })}
                  >
                    <SelectTrigger id="expires">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30">30 days</SelectItem>
                      <SelectItem value="90">90 days</SelectItem>
                      <SelectItem value="180">180 days</SelectItem>
                      <SelectItem value="365">1 year</SelectItem>
                      <SelectItem value="730">2 years</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* IP Whitelist Section */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Globe className="h-4 w-4" />
                  IP Whitelist (Optional)
                </Label>
                <p className="text-xs text-muted-foreground">
                  Restrict API key usage to specific IP addresses or CIDR blocks. Leave empty to allow access from any IP.
                </p>
                
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g., 203.0.113.45 or 198.51.100.0/24"
                    value={ipInput}
                    onChange={(e) => setIpInput(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddIP();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleAddIP}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>

                {formData.ip_whitelist.length > 0 && (
                  <div className="rounded-lg border p-3 space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      Allowed IP Addresses ({formData.ip_whitelist.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {formData.ip_whitelist.map((ip) => (
                        <Badge
                          key={ip}
                          variant="secondary"
                          className="flex items-center gap-1 pr-1"
                        >
                          <span className="font-mono text-xs">{ip}</span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4 p-0 hover:bg-transparent"
                            onClick={() => handleRemoveIP(ip)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {formData.ip_whitelist.length === 0 && (
                  <Alert>
                    <Globe className="h-4 w-4" />
                    <AlertDescription>
                      No IP restrictions configured. This API key will be accessible from any IP address.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Create API Key'}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-600">
                <Shield className="h-5 w-5" />
                API Key Created Successfully
              </DialogTitle>
              <DialogDescription>
                Save this API key securely. You won't be able to see it again.
              </DialogDescription>
            </DialogHeader>

            <div className="py-4 space-y-4">
              <Alert>
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  This key expires in {formData.expires_in_days} days
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label>Your API Key</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 bg-muted rounded-md text-sm break-all">
                    {createdKey}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={copyToClipboard}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Granted Permissions</Label>
                <div className="flex flex-wrap gap-2">
                  {formData.scopes.map((scope) => (
                    <Badge key={scope} variant="secondary">
                      {scope}
                    </Badge>
                  ))}
                </div>
              </div>

              {formData.ip_whitelist.length > 0 && (
                <div className="space-y-2">
                  <Label>IP Whitelist</Label>
                  <div className="flex flex-wrap gap-2">
                    {formData.ip_whitelist.map((ip) => (
                      <Badge key={ip} variant="outline">
                        <Globe className="h-3 w-3 mr-1" />
                        {ip}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}