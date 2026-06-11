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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  Eye, 
  RefreshCw,
  Calendar as CalendarIcon,
  User,
  Shield,
  AlertCircle,
  CheckCircle,
  Clock,
  Activity,
  Database,
  Key,
  Certificate,
  Trash2,
  Settings,
  ExternalLink
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, parseISO, subDays, startOfDay, endOfDay } from 'date-fns';
import { DataGrid } from '@/components/ui/data-grid';

interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  resource: string;
  resourceId: string;
  user: string;
  userRole: string;
  sourceIP: string;
  userAgent: string;
  status: 'success' | 'failure' | 'warning';
  details: any;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  sessionId: string;
  correlationId?: string;
}

interface AuditFilter {
  startDate?: Date;
  endDate?: Date;
  user?: string;
  action?: string;
  resource?: string;
  status?: string;
  riskLevel?: string;
  searchTerm?: string;
}

const AUDIT_ACTIONS = [
  'certificate_issued',
  'certificate_revoked',
  'certificate_renewed',
  'role_created',
  'role_updated',
  'role_deleted',
  'ca_created',
  'ca_rotated',
  'policy_changed',
  'user_login',
  'user_logout',
  'permission_granted',
  'permission_revoked',
  'configuration_changed',
  'backup_created',
  'backup_restored',
  'system_startup',
  'system_shutdown'
];

const RESOURCE_TYPES = [
  'certificate',
  'ca',
  'role',
  'policy',
  'user',
  'system',
  'configuration',
  'backup'
];

export const AuditViewer: React.FC = () => {
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [filter, setFilter] = useState<AuditFilter>({
    startDate: subDays(new Date(), 7),
    endDate: new Date()
  });
  const [showDatePicker, setShowDatePicker] = useState<'start' | 'end' | null>(null);

  // Fetch audit entries
  const fetchAuditEntries = async () => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams();
      if (filter.startDate) params.append('start_date', filter.startDate.toISOString());
      if (filter.endDate) params.append('end_date', filter.endDate.toISOString());
      if (filter.user) params.append('user', filter.user);
      if (filter.action) params.append('action', filter.action);
      if (filter.resource) params.append('resource', filter.resource);
      if (filter.status) params.append('status', filter.status);
      if (filter.riskLevel) params.append('risk_level', filter.riskLevel);
      if (filter.searchTerm) params.append('search', filter.searchTerm);
      
      const response = await fetch(`/api/v1/pki/ca/audit?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch audit entries');
      }

      const data = await response.json();
      setAuditEntries(data.entries || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit entries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEntries();
  }, [filter]);

  // Export audit log
  const exportAuditLog = async (format: 'csv' | 'json' | 'pdf' = 'csv') => {
    try {
      const params = new URLSearchParams();
      if (filter.startDate) params.append('start_date', filter.startDate.toISOString());
      if (filter.endDate) params.append('end_date', filter.endDate.toISOString());
      if (filter.user) params.append('user', filter.user);
      if (filter.action) params.append('action', filter.action);
      if (filter.resource) params.append('resource', filter.resource);
      if (filter.status) params.append('status', filter.status);
      if (filter.riskLevel) params.append('risk_level', filter.riskLevel);
      params.append('format', format);
      
      const response = await fetch(`/api/v1/pki/ca/audit/export?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to export audit log');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pki-audit-${format}-${format(new Date(), 'yyyy-MM-dd')}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export audit log');
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      success: 'bg-green-100 text-green-800',
      failure: 'bg-red-100 text-red-800',
      warning: 'bg-yellow-100 text-yellow-800'
    };
    return variants[status as keyof typeof variants] || variants.warning;
  };

  const getRiskLevelBadge = (riskLevel: string) => {
    const variants = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return variants[riskLevel as keyof typeof variants] || variants.low;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failure':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const getActionIcon = (action: string) => {
    if (action.includes('certificate')) return <Certificate className="h-4 w-4" />;
    if (action.includes('role')) return <User className="h-4 w-4" />;
    if (action.includes('ca')) return <Shield className="h-4 w-4" />;
    if (action.includes('policy')) return <Settings className="h-4 w-4" />;
    if (action.includes('backup')) return <Database className="h-4 w-4" />;
    if (action.includes('login') || action.includes('logout')) return <Key className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  const columns = [
    {
      header: 'Timestamp',
      accessorKey: 'timestamp',
      cell: ({ row }: any) => (
        <div className="flex flex-col">
          <span className="text-sm font-medium">
            {format(parseISO(row.original.timestamp), 'MMM dd, HH:mm:ss')}
          </span>
          <span className="text-xs text-gray-500">
            {format(parseISO(row.original.timestamp), 'yyyy')}
          </span>
        </div>
      )
    },
    {
      header: 'Action',
      accessorKey: 'action',
      cell: ({ row }: any) => (
        <div className="flex items-center space-x-2">
          {getActionIcon(row.original.action)}
          <span className="text-sm">
            {row.original.action.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
          </span>
        </div>
      )
    },
    {
      header: 'Resource',
      accessorKey: 'resource',
      cell: ({ row }: any) => (
        <div className="flex flex-col">
          <span className="text-sm font-medium">{row.original.resource}</span>
          <code className="text-xs text-gray-500">
            {row.original.resourceId?.slice(0, 20)}...
          </code>
        </div>
      )
    },
    {
      header: 'User',
      accessorKey: 'user',
      cell: ({ row }: any) => (
        <div className="flex flex-col">
          <span className="text-sm font-medium">{row.original.user}</span>
          <Badge variant="outline" className="text-xs w-fit">
            {row.original.userRole}
          </Badge>
        </div>
      )
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ row }: any) => (
        <div className="flex items-center space-x-2">
          {getStatusIcon(row.original.status)}
          <Badge className={getStatusBadge(row.original.status)}>
            {row.original.status}
          </Badge>
        </div>
      )
    },
    {
      header: 'Risk Level',
      accessorKey: 'riskLevel',
      cell: ({ row }: any) => (
        <Badge className={getRiskLevelBadge(row.original.riskLevel)}>
          {row.original.riskLevel.toUpperCase()}
        </Badge>
      )
    },
    {
      header: 'Source IP',
      accessorKey: 'sourceIP',
      cell: ({ row }: any) => (
        <code className="text-sm bg-gray-100 px-2 py-1 rounded">
          {row.original.sourceIP}
        </code>
      )
    },
    {
      header: 'Actions',
      id: 'actions',
      cell: ({ row }: any) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setSelectedEntry(row.original);
            setShowDetailsDialog(true);
          }}
        >
          <Eye className="h-4 w-4" />
        </Button>
      )
    }
  ];

  if (loading && auditEntries.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">PKI Audit Log</h1>
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
          <h1 className="text-3xl font-bold tracking-tight">PKI Audit Log</h1>
          <p className="text-gray-500">
            Monitor and track all PKI-related activities and changes
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={fetchAuditEntries} variant="outline">
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button onClick={() => exportAuditLog('csv')} variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button onClick={() => exportAuditLog('json')} variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filters</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Date Range */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Label>From:</Label>
              <Popover open={showDatePicker === 'start'} onOpenChange={(open) => setShowDatePicker(open ? 'start' : null)}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <CalendarIcon className="h-4 w-4 mr-2" />
                    {filter.startDate ? format(filter.startDate, 'MMM dd, yyyy') : 'Select date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={filter.startDate}
                    onSelect={(date) => {
                      setFilter(prev => ({ ...prev, startDate: date }));
                      setShowDatePicker(null);
                    }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
            
            <div className="flex items-center space-x-2">
              <Label>To:</Label>
              <Popover open={showDatePicker === 'end'} onOpenChange={(open) => setShowDatePicker(open ? 'end' : null)}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <CalendarIcon className="h-4 w-4 mr-2" />
                    {filter.endDate ? format(filter.endDate, 'MMM dd, yyyy') : 'Select date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={filter.endDate}
                    onSelect={(date) => {
                      setFilter(prev => ({ ...prev, endDate: date }));
                      setShowDatePicker(null);
                    }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="search"
                  placeholder="Search entries..."
                  value={filter.searchTerm || ''}
                  onChange={(e) => setFilter(prev => ({ ...prev, searchTerm: e.target.value }))}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div>
              <Label htmlFor="user">User</Label>
              <Input
                id="user"
                placeholder="Filter by user..."
                value={filter.user || ''}
                onChange={(e) => setFilter(prev => ({ ...prev, user: e.target.value }))}
              />
            </div>
            
            <div>
              <Label htmlFor="action">Action</Label>
              <Select value={filter.action || ''} onValueChange={(value) => setFilter(prev => ({ ...prev, action: value || undefined }))}>
                <SelectTrigger>
                  <SelectValue placeholder="All actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All actions</SelectItem>
                  {AUDIT_ACTIONS.map((action) => (
                    <SelectItem key={action} value={action}>
                      {action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="resource">Resource</Label>
              <Select value={filter.resource || ''} onValueChange={(value) => setFilter(prev => ({ ...prev, resource: value || undefined }))}>
                <SelectTrigger>
                  <SelectValue placeholder="All resources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All resources</SelectItem>
                  {RESOURCE_TYPES.map((resource) => (
                    <SelectItem key={resource} value={resource}>
                      {resource.charAt(0).toUpperCase() + resource.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="status">Status</Label>
              <Select value={filter.status || ''} onValueChange={(value) => setFilter(prev => ({ ...prev, status: value || undefined }))}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All statuses</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failure">Failure</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="riskLevel">Risk Level</Label>
              <Select value={filter.riskLevel || ''} onValueChange={(value) => setFilter(prev => ({ ...prev, riskLevel: value || undefined }))}>
                <SelectTrigger>
                  <SelectValue placeholder="All levels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All levels</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Audit Entries Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Audit Entries ({auditEntries.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataGrid
            data={auditEntries}
            columns={columns}
            searchable={false}
            filterable={false}
          />
        </CardContent>
      </Card>

      {/* Entry Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Audit Entry Details</DialogTitle>
          </DialogHeader>
          {selectedEntry && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Timestamp</Label>
                    <p className="font-medium">{format(parseISO(selectedEntry.timestamp), 'PPpp')}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Action</Label>
                    <div className="flex items-center space-x-2">
                      {getActionIcon(selectedEntry.action)}
                      <span>
                        {selectedEntry.action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Resource</Label>
                    <div className="flex flex-col">
                      <span className="font-medium">{selectedEntry.resource}</span>
                      <code className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded mt-1">
                        {selectedEntry.resourceId}
                      </code>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Status</Label>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(selectedEntry.status)}
                      <Badge className={getStatusBadge(selectedEntry.status)}>
                        {selectedEntry.status}
                      </Badge>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium text-gray-500">User</Label>
                    <div className="flex flex-col">
                      <span className="font-medium">{selectedEntry.user}</span>
                      <Badge variant="outline" className="w-fit mt-1">
                        {selectedEntry.userRole}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Risk Level</Label>
                    <Badge className={getRiskLevelBadge(selectedEntry.riskLevel)}>
                      {selectedEntry.riskLevel.toUpperCase()}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Source IP</Label>
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {selectedEntry.sourceIP}
                    </code>
                  </div>
                  <div>
                    <Label className="text-sm font-medium text-gray-500">Session ID</Label>
                    <code className="text-xs bg-gray-100 px-2 py-1 rounded block">
                      {selectedEntry.sessionId}
                    </code>
                  </div>
                </div>
              </div>

              {/* User Agent */}
              <div>
                <Label className="text-sm font-medium text-gray-500">User Agent</Label>
                <p className="text-sm bg-gray-50 p-3 rounded border">
                  {selectedEntry.userAgent}
                </p>
              </div>

              {/* Details */}
              {selectedEntry.details && (
                <div>
                  <Label className="text-sm font-medium text-gray-500">Additional Details</Label>
                  <ScrollArea className="h-48 w-full border rounded">
                    <pre className="p-4 text-xs">
                      {JSON.stringify(selectedEntry.details, null, 2)}
                    </pre>
                  </ScrollArea>
                </div>
              )}

              {/* Correlation ID */}
              {selectedEntry.correlationId && (
                <div>
                  <Label className="text-sm font-medium text-gray-500">Correlation ID</Label>
                  <div className="flex items-center space-x-2">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {selectedEntry.correlationId}
                    </code>
                    <Button variant="outline" size="sm">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Related
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};