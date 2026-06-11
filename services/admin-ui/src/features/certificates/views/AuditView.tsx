/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { History, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface AuditEvent {
  timestamp: string;
  event_type: string;
  user_id?: string;
  ip_address?: string;
  details: any;
}

interface AuditViewProps {
  auditTrail: AuditEvent[];
  auditFilter: string;
  onAuditFilterChange: (filter: string) => void;
  loadingAudit: boolean;
}

export const AuditView: React.FC<AuditViewProps> = ({
  auditTrail,
  auditFilter,
  onAuditFilterChange,
  loadingAudit
}) => {
  const filteredAuditTrail = auditFilter === 'all' 
    ? auditTrail 
    : auditTrail.filter(event => event.event_type === auditFilter);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Certificate Audit Trail
            </CardTitle>
            <CardDescription>
              Complete history of certificate operations and lifecycle events
            </CardDescription>
          </div>
          <Select
            value={auditFilter}
            onValueChange={onAuditFilterChange}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filter events" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Events</SelectItem>
              <SelectItem value="certificate_created">Created</SelectItem>
              <SelectItem value="certificate_renewed">Renewed</SelectItem>
              <SelectItem value="certificate_revoked">Revoked</SelectItem>
              <SelectItem value="certificate_downloaded">Downloaded</SelectItem>
              <SelectItem value="api_access">API Access</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {loadingAudit ? (
          <div className="text-center py-8">Loading audit trail...</div>
        ) : filteredAuditTrail.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>User</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAuditTrail.map((event, idx) => (
                <TableRow key={idx}>
                  <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                  <TableCell>
                    <Badge variant={
                      event.event_type.includes('created') ? 'success' :
                      event.event_type.includes('renewed') ? 'default' :
                      event.event_type.includes('revoked') ? 'destructive' :
                      'secondary'
                    }>
                      {event.event_type.replace('certificate_', '').toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>{event.user_id || 'System'}</TableCell>
                  <TableCell>{event.ip_address || 'N/A'}</TableCell>
                  <TableCell>
                    <code className="text-xs">{JSON.stringify(event.details, null, 2)}</code>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              No audit events found. Events will appear here as certificate operations are performed.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};