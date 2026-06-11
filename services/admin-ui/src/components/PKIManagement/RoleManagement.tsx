/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  RefreshCw,
  Key,
  Shield,
  Settings,
  AlertCircle,
  CheckCircle,
  Clock,
  Copy,
  FileText,
  Globe,
  Lock,
  Unlock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DataGrid } from '@/components/ui/data-grid';

interface PKIRole {
  name: string;
  description: string;
  enabled: boolean;
  allowedDomains: string[];
  allowSubdomains: boolean;
  allowBareDomains: boolean;
  allowAnyName: boolean;
  allowIPSans: boolean;
  allowLocalhost: boolean;
  maxTTL: string;
  defaultTTL: string;
  keyType: 'rsa' | 'ec' | 'ed25519';
  keyBits: number;
  keyUsage: string[];
  extKeyUsage: string[];
  clientFlag: boolean;
  serverFlag: boolean;
  codeSigningFlag: boolean;
  emailProtectionFlag: boolean;
  requireCn: boolean;
  allowedOtherSans: string[];
  allowedSerialNumbers: string[];
  createdAt: string;
  updatedAt: string;
  certificatesIssued: number;
}

interface CreateRoleRequest {
  name: string;
  description: string;
  allowedDomains: string;
  allowSubdomains: boolean;
  allowBareDomains: boolean;
  allowAnyName: boolean;
  allowIPSans: boolean;
  allowLocalhost: boolean;
  maxTTL: string;
  keyType: 'rsa' | 'ec' | 'ed25519';
  keyBits: number;
  keyUsage: string[];
  extKeyUsage: string[];
  clientFlag: boolean;
  serverFlag: boolean;
  codeSigningFlag: boolean;
  emailProtectionFlag: boolean;
  requireCn: boolean;
}

const DEFAULT_KEY_USAGE = [
  'digital_signature',
  'key_encipherment',
  'key_agreement'
];

const DEFAULT_EXT_KEY_USAGE = [
  'server_auth',
  'client_auth'
];

const KEY_USAGE_OPTIONS = [
  { value: 'digital_signature', label: 'Digital Signature' },
  { value: 'key_encipherment', label: 'Key Encipherment' },
  { value: 'key_agreement', label: 'Key Agreement' },
  { value: 'certificate_signing', label: 'Certificate Signing' },
  { value: 'crl_signing', label: 'CRL Signing' },
  { value: 'content_commitment', label: 'Content Commitment' },
  { value: 'data_encipherment', label: 'Data Encipherment' },
  { value: 'encipher_only', label: 'Encipher Only' },
  { value: 'decipher_only', label: 'Decipher Only' }
];

const EXT_KEY_USAGE_OPTIONS = [
  { value: 'server_auth', label: 'Server Authentication' },
  { value: 'client_auth', label: 'Client Authentication' },
  { value: 'code_signing', label: 'Code Signing' },
  { value: 'email_protection', label: 'Email Protection' },
  { value: 'ipsec_end_system', label: 'IPSec End System' },
  { value: 'ipsec_tunnel', label: 'IPSec Tunnel' },
  { value: 'ipsec_user', label: 'IPSec User' },
  { value: 'timestamping', label: 'Time Stamping' }
];

export const RoleManagement: React.FC = () => {
  const [roles, setRoles] = useState<PKIRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState<PKIRole | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [createRequest, setCreateRequest] = useState<CreateRoleRequest>({
    name: '',
    description: '',
    allowedDomains: '',
    allowSubdomains: true,
    allowBareDomains: true,
    allowAnyName: false,
    allowIPSans: true,
    allowLocalhost: true,
    maxTTL: '720h',
    keyType: 'rsa',
    keyBits: 2048,
    keyUsage: [...DEFAULT_KEY_USAGE],
    extKeyUsage: [...DEFAULT_EXT_KEY_USAGE],
    clientFlag: true,
    serverFlag: true,
    codeSigningFlag: false,
    emailProtectionFlag: false,
    requireCn: true
  });
  const [creatingRole, setCreatingRole] = useState(false);

  // Fetch roles
  const fetchRoles = async () => {
    try {
      setLoading(true);
      
      const response = await fetch('/api/v1/pki/ca/roles', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch roles');
      }

      const data = await response.json();
      setRoles(data.roles || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  // Filter roles
  const filteredRoles = roles.filter(role => 
    role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    role.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Create new role
  const handleCreateRole = async () => {
    if (!createRequest.name.trim()) {
      setError('Role name is required');
      return;
    }

    try {
      setCreatingRole(true);
      
      const requestData = {
        ...createRequest,
        allowedDomains: createRequest.allowedDomains.split(',').map(d => d.trim()).filter(d => d)
      };
      
      const response = await fetch('/api/v1/pki/ca/roles', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create role');
      }

      await fetchRoles();
      
      // Reset form and close dialog
      setCreateRequest({
        name: '',
        description: '',
        allowedDomains: '',
        allowSubdomains: true,
        allowBareDomains: true,
        allowAnyName: false,
        allowIPSans: true,
        allowLocalhost: true,
        maxTTL: '720h',
        keyType: 'rsa',
        keyBits: 2048,
        keyUsage: [...DEFAULT_KEY_USAGE],
        extKeyUsage: [...DEFAULT_EXT_KEY_USAGE],
        clientFlag: true,
        serverFlag: true,
        codeSigningFlag: false,
        emailProtectionFlag: false,
        requireCn: true
      });
      setShowCreateDialog(false);
      setError(null);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create role');
    } finally {
      setCreatingRole(false);
    }
  };

  // Delete role
  const handleDeleteRole = async (roleName: string) => {
    if (!confirm(`Are you sure you want to delete the role "${roleName}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/pki/ca/roles/${roleName}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete role');
      }

      await fetchRoles();
      setShowDetailsDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete role');
    }
  };

  // Toggle key usage
  const toggleKeyUsage = (usage: string, isExtended: boolean = false) => {
    const field = isExtended ? 'extKeyUsage' : 'keyUsage';
    const currentUsages = createRequest[field];
    
    if (currentUsages.includes(usage)) {
      setCreateRequest(prev => ({
        ...prev,
        [field]: currentUsages.filter(u => u !== usage)
      }));
    } else {
      setCreateRequest(prev => ({
        ...prev,
        [field]: [...currentUsages, usage]
      }));
    }
  };

  const columns = [
    {
      header: 'Role Name',
      accessorKey: 'name',
      cell: ({ row }: any) => (
        <div className="flex flex-col">
          <span className="font-medium">{row.original.name}</span>
          <span className="text-sm text-gray-500">{row.original.description}</span>
        </div>
      )
    },
    {
      header: 'Status',
      accessorKey: 'enabled',
      cell: ({ row }: any) => (
        <Badge variant={row.original.enabled ? 'default' : 'secondary'}>
          {row.original.enabled ? 'Enabled' : 'Disabled'}
        </Badge>
      )
    },
    {
      header: 'Key Type',
      accessorKey: 'keyType',
      cell: ({ row }: any) => (
        <span className="font-mono text-sm">
          {row.original.keyType.toUpperCase()} {row.original.keyBits}
        </span>
      )
    },
    {
      header: 'Max TTL',
      accessorKey: 'maxTTL'
    },
    {
      header: 'Certificates Issued',
      accessorKey: 'certificatesIssued',
      cell: ({ row }: any) => (
        <span className="font-medium">{row.original.certificatesIssued || 0}</span>
      )
    },
    {
      header: 'Actions',
      id: 'actions',
      cell: ({ row }: any) => (
        <div className="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedRole(row.original);
              setShowDetailsDialog(true);
            }}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteRole(row.original.name)}
            className="text-red-600 hover:text-red-700"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )
    }
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">PKI Role Management</h1>
        </div>
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">PKI Role Management</h1>
          <p className="text-gray-500">
            Configure certificate issuance roles and policies
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={fetchRoles} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Role
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <DialogHeader>
                <DialogTitle>Create New PKI Role</DialogTitle>
              </DialogHeader>
              <Tabs defaultValue="basic">
                <TabsList>
                  <TabsTrigger value="basic">Basic Settings</TabsTrigger>
                  <TabsTrigger value="domains">Domain Policy</TabsTrigger>
                  <TabsTrigger value="crypto">Cryptography</TabsTrigger>
                  <TabsTrigger value="usage">Key Usage</TabsTrigger>
                </TabsList>
                
                <TabsContent value="basic" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Role Name</Label>
                      <Input
                        id="name"
                        value={createRequest.name}
                        onChange={(e) => setCreateRequest(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="web-server"
                      />
                    </div>
                    <div>
                      <Label htmlFor="maxTTL">Maximum TTL</Label>
                      <Input
                        id="maxTTL"
                        value={createRequest.maxTTL}
                        onChange={(e) => setCreateRequest(prev => ({ ...prev, maxTTL: e.target.value }))}
                        placeholder="720h"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={createRequest.description}
                      onChange={(e) => setCreateRequest(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Role description..."
                    />
                  </div>
                </TabsContent>
                
                <TabsContent value="domains" className="space-y-4">
                  <div>
                    <Label htmlFor="allowedDomains">Allowed Domains (comma-separated)</Label>
                    <Textarea
                      id="allowedDomains"
                      value={createRequest.allowedDomains}
                      onChange={(e) => setCreateRequest(prev => ({ ...prev, allowedDomains: e.target.value }))}
                      placeholder="example.com, *.example.com, sub.example.com"
                      rows={3}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allowSubdomains">Allow Subdomains</Label>
                        <Switch
                          id="allowSubdomains"
                          checked={createRequest.allowSubdomains}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, allowSubdomains: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allowBareDomains">Allow Bare Domains</Label>
                        <Switch
                          id="allowBareDomains"
                          checked={createRequest.allowBareDomains}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, allowBareDomains: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allowAnyName">Allow Any Name</Label>
                        <Switch
                          id="allowAnyName"
                          checked={createRequest.allowAnyName}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, allowAnyName: checked }))}
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allowIPSans">Allow IP SANs</Label>
                        <Switch
                          id="allowIPSans"
                          checked={createRequest.allowIPSans}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, allowIPSans: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allowLocalhost">Allow Localhost</Label>
                        <Switch
                          id="allowLocalhost"
                          checked={createRequest.allowLocalhost}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, allowLocalhost: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="requireCn">Require Common Name</Label>
                        <Switch
                          id="requireCn"
                          checked={createRequest.requireCn}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, requireCn: checked }))}
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="crypto" className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="keyType">Key Type</Label>
                      <Select 
                        value={createRequest.keyType} 
                        onValueChange={(value: any) => setCreateRequest(prev => ({ ...prev, keyType: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="rsa">RSA</SelectItem>
                          <SelectItem value="ec">Elliptic Curve</SelectItem>
                          <SelectItem value="ed25519">Ed25519</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label htmlFor="keyBits">Key Size (bits)</Label>
                      <Select 
                        value={createRequest.keyBits.toString()} 
                        onValueChange={(value) => setCreateRequest(prev => ({ ...prev, keyBits: parseInt(value) }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {createRequest.keyType === 'rsa' && (
                            <>
                              <SelectItem value="2048">2048</SelectItem>
                              <SelectItem value="3072">3072</SelectItem>
                              <SelectItem value="4096">4096</SelectItem>
                            </>
                          )}
                          {createRequest.keyType === 'ec' && (
                            <>
                              <SelectItem value="256">256 (P-256)</SelectItem>
                              <SelectItem value="384">384 (P-384)</SelectItem>
                              <SelectItem value="521">521 (P-521)</SelectItem>
                            </>
                          )}
                          {createRequest.keyType === 'ed25519' && (
                            <SelectItem value="256">256</SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="usage" className="space-y-6">
                  <div>
                    <Label className="text-base font-medium">Certificate Flags</Label>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="clientFlag">Client Authentication</Label>
                        <Switch
                          id="clientFlag"
                          checked={createRequest.clientFlag}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, clientFlag: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="serverFlag">Server Authentication</Label>
                        <Switch
                          id="serverFlag"
                          checked={createRequest.serverFlag}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, serverFlag: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="codeSigningFlag">Code Signing</Label>
                        <Switch
                          id="codeSigningFlag"
                          checked={createRequest.codeSigningFlag}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, codeSigningFlag: checked }))}
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <Label htmlFor="emailProtectionFlag">Email Protection</Label>
                        <Switch
                          id="emailProtectionFlag"
                          checked={createRequest.emailProtectionFlag}
                          onCheckedChange={(checked) => setCreateRequest(prev => ({ ...prev, emailProtectionFlag: checked }))}
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <Label className="text-base font-medium">Key Usage</Label>
                    <div className="grid grid-cols-3 gap-2 mt-4">
                      {KEY_USAGE_OPTIONS.map((option) => (
                        <div key={option.value} className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id={`ku-${option.value}`}
                            checked={createRequest.keyUsage.includes(option.value)}
                            onChange={() => toggleKeyUsage(option.value)}
                            className="rounded border-gray-300"
                          />
                          <Label htmlFor={`ku-${option.value}`} className="text-sm">
                            {option.label}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <Label className="text-base font-medium">Extended Key Usage</Label>
                    <div className="grid grid-cols-2 gap-2 mt-4">
                      {EXT_KEY_USAGE_OPTIONS.map((option) => (
                        <div key={option.value} className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id={`eku-${option.value}`}
                            checked={createRequest.extKeyUsage.includes(option.value)}
                            onChange={() => toggleKeyUsage(option.value, true)}
                            className="rounded border-gray-300"
                          />
                          <Label htmlFor={`eku-${option.value}`} className="text-sm">
                            {option.label}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
              
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              
              <div className="flex justify-end space-x-2">
                <Button 
                  variant="outline" 
                  onClick={() => setShowCreateDialog(false)}
                  disabled={creatingRole}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleCreateRole}
                  disabled={creatingRole}
                >
                  {creatingRole ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Users className="h-4 w-4 mr-2" />
                      Create Role
                    </>
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Roles Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            PKI Roles ({filteredRoles.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataGrid
            data={filteredRoles}
            columns={columns}
            searchable={false}
            filterable={false}
          />
        </CardContent>
      </Card>

      {/* Role Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Role Details: {selectedRole?.name}</DialogTitle>
          </DialogHeader>
          {selectedRole && (
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="domains">Domain Policy</TabsTrigger>
                <TabsTrigger value="crypto">Cryptography</TabsTrigger>
                <TabsTrigger value="usage">Key Usage</TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview" className="space-y-4">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Role Name</Label>
                      <p className="font-medium">{selectedRole.name}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Description</Label>
                      <p>{selectedRole.description || 'No description provided'}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Status</Label>
                      <Badge variant={selectedRole.enabled ? 'default' : 'secondary'}>
                        {selectedRole.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Max TTL</Label>
                      <p>{selectedRole.maxTTL}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Certificates Issued</Label>
                      <p className="font-medium">{selectedRole.certificatesIssued || 0}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Last Updated</Label>
                      <p>{new Date(selectedRole.updatedAt).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="domains" className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Allowed Domains</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedRole.allowedDomains.map((domain, index) => (
                      <Badge key={index} variant="outline">
                        {domain}
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Allow Subdomains</span>
                      {selectedRole.allowSubdomains ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Allow Bare Domains</span>
                      {selectedRole.allowBareDomains ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Allow Any Name</span>
                      {selectedRole.allowAnyName ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Allow IP SANs</span>
                      {selectedRole.allowIPSans ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Allow Localhost</span>
                      {selectedRole.allowLocalhost ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Require CN</span>
                      {selectedRole.requireCn ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="crypto" className="space-y-4">
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Key Type</Label>
                    <p className="font-mono">{selectedRole.keyType.toUpperCase()}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Key Size</Label>
                    <p className="font-mono">{selectedRole.keyBits} bits</p>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="usage" className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Certificate Flags</Label>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Client Auth</span>
                      {selectedRole.clientFlag ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Server Auth</span>
                      {selectedRole.serverFlag ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Code Signing</span>
                      {selectedRole.codeSigningFlag ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Email Protection</span>
                      {selectedRole.emailProtectionFlag ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                  </div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Key Usage</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedRole.keyUsage.map((usage, index) => (
                      <Badge key={index} variant="outline">
                        {usage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <div>
                  <Label className="text-sm font-medium text-gray-500">Extended Key Usage</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedRole.extKeyUsage.map((usage, index) => (
                      <Badge key={index} variant="secondary">
                        {usage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Badge>
                    ))}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};