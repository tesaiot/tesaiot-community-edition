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
 * TESA IoT Platform - API Key Table Component
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

import React from 'react';
import { format } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Copy,
  MoreVertical,
  RotateCw,
  Trash2,
  Activity,
  Calendar,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '@/components/ui/skeleton';

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

interface ApiKeyTableProps {
  apiKeys: ApiKey[];
  loading: boolean;
  onRevoke: (keyId: string) => void;
  onRotate: (keyId: string) => void;
  onViewUsage: (keyId: string) => void;
}

export function ApiKeyTable({
  apiKeys,
  loading,
  onRevoke,
  onRotate,
  onViewUsage,
}: ApiKeyTableProps) {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Active</Badge>;
      case 'suspended':
        return <Badge variant="warning">Suspended</Badge>;
      case 'revoked':
        return <Badge variant="destructive">Revoked</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getScopeBadges = (scopes: string[]) => {
    return scopes.slice(0, 2).map((scope) => (
      <Badge key={scope} variant="outline" className="text-xs">
        {scope}
      </Badge>
    ));
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (apiKeys.length === 0) {
    return (
      <div className="text-center py-16">
        <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-lg font-semibold mb-2">No API Keys Yet</h3>
        <p className="text-muted-foreground mb-4">
          Create your first API key to start integrating with the platform
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>API Key</TableHead>
            <TableHead>Scopes</TableHead>
            <TableHead>Rate Limit</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Expires</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {apiKeys.map((apiKey) => (
            <TableRow key={apiKey.id}>
              <TableCell>
                <div>
                  <div className="font-medium">{apiKey.name}</div>
                  {apiKey.description && (
                    <div className="text-sm text-muted-foreground">
                      {apiKey.description}
                    </div>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <code className="text-sm bg-muted px-2 py-1 rounded">
                    {apiKey.key_prefix}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(apiKey.key_prefix)}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex gap-1 flex-wrap">
                  {getScopeBadges(apiKey.scopes)}
                  {apiKey.scopes.length > 2 && (
                    <Badge variant="secondary" className="text-xs">
                      +{apiKey.scopes.length - 2}
                    </Badge>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <div className="text-sm">
                  {apiKey.usage_limits.requests_per_minute} req/min
                </div>
              </TableCell>
              <TableCell>
                <div className="text-sm">
                  {format(new Date(apiKey.created_at), 'MMM d, yyyy')}
                </div>
              </TableCell>
              <TableCell>
                <div className="text-sm">
                  {format(new Date(apiKey.expires_at), 'MMM d, yyyy')}
                </div>
              </TableCell>
              <TableCell>{getStatusBadge(apiKey.status)}</TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onViewUsage(apiKey.id)}
                      disabled={apiKey.status !== 'active'}
                    >
                      <Activity className="h-4 w-4 mr-2" />
                      View Usage
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => onRotate(apiKey.id)}
                      disabled={apiKey.status !== 'active'}
                    >
                      <RotateCw className="h-4 w-4 mr-2" />
                      Rotate Key
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onRevoke(apiKey.id)}
                      disabled={apiKey.status === 'revoked'}
                      className="text-destructive"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Revoke Key
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}