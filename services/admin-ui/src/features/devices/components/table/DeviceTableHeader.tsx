/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import {
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface DeviceTableHeaderProps {
  isAllSelected: boolean;
  onSelectAll: (selected: boolean) => void;
}

export function DeviceTableHeader({ isAllSelected, onSelectAll }: DeviceTableHeaderProps) {
  return (
    <TableHeader>
      <TableRow>
        <TableHead className="w-[50px]">
          <input
            type="checkbox"
            checked={isAllSelected}
            onChange={(e) => onSelectAll(e.target.checked)}
            className="rounded border-gray-300"
          />
        </TableHead>
        <TableHead>Device</TableHead>
        <TableHead>Type</TableHead>
        <TableHead>Status</TableHead>
        <TableHead>Certificate</TableHead>
        <TableHead>Organization</TableHead>
        <TableHead>Location</TableHead>
        <TableHead>Last Seen</TableHead>
        <TableHead>Telemetry Rate</TableHead>
        <TableHead className="text-right">Actions</TableHead>
      </TableRow>
    </TableHeader>
  );
}