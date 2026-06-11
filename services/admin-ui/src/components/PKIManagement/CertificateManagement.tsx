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
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Certificate, 
  Plus, 
  Search, 
  Filter, 
  Download, 
  Eye, 
  Trash2, 
  RefreshCw,
  Calendar,
  Key,
  Shield,
  AlertCircle,
  CheckCircle,
  Clock,
  Copy,
  FileText,
  Settings,
  RotateCcw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, parseISO, differenceInDays, isAfter, isBefore } from 'date-fns';
import { DataGrid } from '@/components/ui/data-grid';

interface Certificate {
  id: string;
  serialNumber: string;
  commonName: string;
  subjectAlternativeNames: string[];
  issuer: string;
  status: 'active' | 'expired' | 'revoked' | 'pending';
  notBefore: string;
  notAfter: string;
  keyType: string;
  keySize: number;
  usage: string[];
  thumbprint: string;
  issuerCA: string;
  createdAt: string;
  createdBy: string;
  revokedAt?: string;
  revokedBy?: string;
  revocationReason?: string;
  downloadCount: number;
}

interface CertificateRole {
  name: string;
  description: string;
  allowedDomains: string[];
  allowSubdomains: boolean;
  allowAnyName: boolean;
  maxTTL: string;
  keyType: string;
  keyBits: number;
  usages: string[];
}

interface IssueCertificateRequest {
  role: string;
  commonName: string;
  altNames?: string;
  ipSans?: string;
  ttl?: string;
  format?: 'pem' | 'der' | 'pem_bundle';
  privateKeyFormat?: 'der' | 'pkcs8';
  excludeCnFromSans?: boolean;
}

export const CertificateManagement: React.FC = () => {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [roles, setRoles] = useState<CertificateRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedCertificate, setSelectedCertificate] = useState<Certificate | null>(null);
  const [showIssueDialog, setShowIssueDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [issueRequest, setIssueRequest] = useState<IssueCertificateRequest>({
    role: '',
    commonName: '',
    format: 'pem',
    privateKeyFormat: 'pkcs8'
  });
  const [issuingCertificate, setIssuingCertificate] = useState(false);

  // Fetch certificates and roles
  const fetchData = async () => {
    try {
      setLoading(true);
      
      const [certsResponse, rolesResponse] = await Promise.all([
        fetch('/api/v1/pki/ca/certificates', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        }),
        fetch('/api/v1/pki/ca/roles', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        })
      ]);

      if (!certsResponse.ok || !rolesResponse.ok) {
        throw new Error('Failed to fetch data');
      }

      const certsData = await certsResponse.json();
      const rolesData = await rolesResponse.json();

      setCertificates(certsData.certificates || []);
      setRoles(rolesData.roles || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filter certificates
  const filteredCertificates = certificates.filter(cert => {
    const matchesSearch = searchTerm === '' || 
      cert.commonName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.serialNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cert.issuer.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || cert.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Issue new certificate
  const handleIssueCertificate = async () => {
    if (!issueRequest.role || !issueRequest.commonName) {
      setError('Role and Common Name are required');
      return;
    }

    try {
      setIssuingCertificate(true);
      
      const response = await fetch('/api/v1/pki/ca/issue', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(issueRequest)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to issue certificate');
      }

      const result = await response.json();
      
      // Refresh certificates list
      await fetchData();
      
      // Reset form and close dialog
      setIssueRequest({
        role: '',
        commonName: '',
        format: 'pem',
        privateKeyFormat: 'pkcs8'
      });
      setShowIssueDialog(false);
      setError(null);
      
      // Show success message or download certificate
      alert(`Certificate issued successfully! Serial: ${result.serialNumber}`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to issue certificate');
    } finally {
      setIssuingCertificate(false);
    }
  };

  // Revoke certificate
  const handleRevokeCertificate = async (certificate: Certificate, reason: string = 'unspecified') => {
    if (!confirm(`Are you sure you want to revoke certificate ${certificate.commonName}?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/pki/ca/revoke/${certificate.serialNumber}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason })
      });

      if (!response.ok) {
        throw new Error('Failed to revoke certificate');
      }

      await fetchData();
      setShowDetailsDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke certificate');
    }
  };

  // Download certificate
  const handleDownloadCertificate = async (certificate: Certificate) => {
    try {
      const response = await fetch(`/api/v1/pki/ca/certificate/${certificate.serialNumber}/download`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to download certificate');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${certificate.commonName}.pem`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download certificate');
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      active: 'bg-green-100 text-green-800',
      expired: 'bg-red-100 text-red-800',
      revoked: 'bg-gray-100 text-gray-800',
      pending: 'bg-yellow-100 text-yellow-800'
    };
    return variants[status as keyof typeof variants] || variants.pending;
  };

  const getExpirationWarning = (notAfter: string) => {
    const daysUntilExpiry = differenceInDays(parseISO(notAfter), new Date());
    if (daysUntilExpiry < 0) return 'expired';
    if (daysUntilExpiry <= 7) return 'critical';
    if (daysUntilExpiry <= 30) return 'warning';
    return 'normal';
  };

  const columns = [
    {
      header: 'Common Name',
      accessorKey: 'commonName',
      cell: ({ row }: any) => (
        <div className="flex flex-col">
          <span className="font-medium">{row.original.commonName}</span>
          {row.original.subjectAlternativeNames.length > 0 && (
            <span className="text-xs text-gray-500">
              SANs: {row.original.subjectAlternativeNames.slice(0, 2).join(', ')}
              {row.original.subjectAlternativeNames.length > 2 && '...'}
            </span>
          )}
        </div>
      )
    },
    {
      header: 'Serial Number',
      accessorKey: 'serialNumber',
      cell: ({ row }: any) => (
        <code className="text-sm bg-gray-100 px-2 py-1 rounded">
          {row.original.serialNumber.slice(0, 16)}...
        </code>
      )
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ row }: any) => {
        const warning = getExpirationWarning(row.original.notAfter);
        return (
          <div className="flex flex-col space-y-1">
            <Badge className={getStatusBadge(row.original.status)}>
              {row.original.status}
            </Badge>
            {warning === 'critical' && (
              <Badge variant="destructive" className="text-xs">
                Expires Soon
              </Badge>
            )}
            {warning === 'warning' && (
              <Badge variant="outline" className="text-xs text-yellow-600">
                Expiring
              </Badge>
            )}
          </div>
        );
      }
    },
    {
      header: 'Expires',
      accessorKey: 'notAfter',
      cell: ({ row }: any) => {
        const date = parseISO(row.original.notAfter);
        const daysUntilExpiry = differenceInDays(date, new Date());
        return (
          <div className="flex flex-col">
            <span className="text-sm">{format(date, 'MMM dd, yyyy')}</span>
            <span className={cn(
              "text-xs",
              daysUntilExpiry < 0 ? "text-red-600" :
              daysUntilExpiry <= 30 ? "text-yellow-600" : "text-gray-500"
            )}>
              {daysUntilExpiry < 0 ? 'Expired' : `${daysUntilExpiry} days left`}
            </span>
          </div>
        );
      }
    },
    {
      header: 'Key Type',
      accessorKey: 'keyType',
      cell: ({ row }: any) => (
        <span className="text-sm">
          {row.original.keyType.toUpperCase()} {row.original.keySize}
        </span>
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
              setSelectedCertificate(row.original);
              setShowDetailsDialog(true);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDownloadCertificate(row.original)}
          >
            <Download className="h-4 w-4" />
          </Button>
          {row.original.status === 'active' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleRevokeCertificate(row.original)}
              className="text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      )
    }
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">Certificate Management</h1>
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
          <h1 className="text-3xl font-bold tracking-tight">Certificate Management</h1>
          <p className="text-gray-500">
            Issue, manage, and monitor digital certificates
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={fetchData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={showIssueDialog} onOpenChange={setShowIssueDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Issue Certificate
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Issue New Certificate</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="role">Certificate Role</Label>
                    <Select 
                      value={issueRequest.role} 
                      onValueChange={(value) => setIssueRequest(prev => ({ ...prev, role: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((role) => (
                          <SelectItem key={role.name} value={role.name}>
                            {role.name} - {role.description}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="commonName">Common Name</Label>
                    <Input
                      id="commonName"
                      value={issueRequest.commonName}
                      onChange={(e) => setIssueRequest(prev => ({ ...prev, commonName: e.target.value }))}
                      placeholder="example.com"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="altNames">Subject Alternative Names (Optional)</Label>
                  <Input
                    id="altNames"
                    value={issueRequest.altNames || ''}
                    onChange={(e) => setIssueRequest(prev => ({ ...prev, altNames: e.target.value }))}
                    placeholder="sub1.example.com,sub2.example.com"
                  />
                </div>
                
                <div>
                  <Label htmlFor="ipSans">IP SANs (Optional)</Label>
                  <Input
                    id="ipSans"
                    value={issueRequest.ipSans || ''}
                    onChange={(e) => setIssueRequest(prev => ({ ...prev, ipSans: e.target.value }))}
                    placeholder="127.0.0.1,192.168.1.100"
                  />
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="ttl">TTL (Optional)</Label>
                    <Input
                      id="ttl"
                      value={issueRequest.ttl || ''}
                      onChange={(e) => setIssueRequest(prev => ({ ...prev, ttl: e.target.value }))}
                      placeholder="720h"
                    />
                  </div>
                  <div>
                    <Label htmlFor="format">Certificate Format</Label>
                    <Select 
                      value={issueRequest.format} 
                      onValueChange={(value: any) => setIssueRequest(prev => ({ ...prev, format: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pem">PEM</SelectItem>
                        <SelectItem value="der">DER</SelectItem>
                        <SelectItem value="pem_bundle">PEM Bundle</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="privateKeyFormat">Private Key Format</Label>
                    <Select 
                      value={issueRequest.privateKeyFormat} 
                      onValueChange={(value: any) => setIssueRequest(prev => ({ ...prev, privateKeyFormat: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="der">DER</SelectItem>
                        <SelectItem value="pkcs8">PKCS8</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                <div className="flex justify-end space-x-2">
                  <Button 
                    variant="outline" 
                    onClick={() => setShowIssueDialog(false)}
                    disabled={issuingCertificate}
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleIssueCertificate}
                    disabled={issuingCertificate}
                  >
                    {issuingCertificate ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Issuing...
                      </>
                    ) : (
                      <>
                        <Certificate className="h-4 w-4 mr-2" />
                        Issue Certificate
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search certificates..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
                <SelectItem value="revoked">Revoked</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Certificates Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Certificates ({filteredCertificates.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataGrid
            data={filteredCertificates}
            columns={columns}
            searchable={false}
            filterable={false}
          />
        </CardContent>
      </Card>

      {/* Certificate Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Certificate Details</DialogTitle>
          </DialogHeader>
          {selectedCertificate && (
            <Tabs defaultValue="details">
              <TabsList>
                <TabsTrigger value="details">Details</TabsTrigger>
                <TabsTrigger value="extensions">Extensions</TabsTrigger>
                <TabsTrigger value="actions">Actions</TabsTrigger>
              </TabsList>
              
              <TabsContent value="details" className="space-y-4">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Common Name</Label>
                      <p className="font-medium">{selectedCertificate.commonName}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Serial Number</Label>
                      <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                        {selectedCertificate.serialNumber}
                      </code>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Status</Label>
                      <Badge className={getStatusBadge(selectedCertificate.status)}>
                        {selectedCertificate.status}
                      </Badge>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Key Type</Label>
                      <p>{selectedCertificate.keyType.toUpperCase()} {selectedCertificate.keySize} bits</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Valid From</Label>
                      <p>{format(parseISO(selectedCertificate.notBefore), 'PPpp')}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Valid Until</Label>
                      <p>{format(parseISO(selectedCertificate.notAfter), 'PPpp')}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Issuer</Label>
                      <p className="text-sm">{selectedCertificate.issuer}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-500">Thumbprint</Label>
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded block">
                        {selectedCertificate.thumbprint}
                      </code>
                    </div>
                  </div>
                </div>
                
                {selectedCertificate.subjectAlternativeNames.length > 0 && (
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Subject Alternative Names</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedCertificate.subjectAlternativeNames.map((san, index) => (
                        <Badge key={index} variant="outline">
                          {san}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="extensions" className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-gray-500">Key Usage</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedCertificate.usage.map((usage, index) => (
                      <Badge key={index} variant="secondary">
                        {usage}
                      </Badge>
                    ))}
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="actions" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Button
                    onClick={() => handleDownloadCertificate(selectedCertificate)}
                    className="h-auto p-4"
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <Download className="h-6 w-6" />
                      <span>Download Certificate</span>
                    </div>
                  </Button>
                  
                  {selectedCertificate.status === 'active' && (
                    <Button
                      variant="destructive"
                      onClick={() => handleRevokeCertificate(selectedCertificate)}
                      className="h-auto p-4"
                    >
                      <div className="flex flex-col items-center space-y-2">
                        <Trash2 className="h-6 w-6" />
                        <span>Revoke Certificate</span>
                      </div>
                    </Button>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};