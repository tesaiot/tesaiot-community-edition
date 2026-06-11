/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatRelativeTimeWithTimezone } from '@/utils/dateFormatting';
import { TableCell, TableRow } from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  MoreVertical,
  Info,
  Edit,
  Trash2,
  Key,
  MapPin,
  QrCode,
  Download,
  Wifi,
  Zap
} from 'lucide-react';
import { Device } from '../../types/device.types';

interface DeviceTableRowProps {
  device: Device;
  isSelected: boolean;
  onSelect: (selected: boolean) => void;
  getDeviceIcon: (type: string) => React.ReactNode;
  getStatusColor: (status: string) => string;
  onViewDetails: (device: Device) => void;
  onEdit: (device: Device) => void;
  onGenerateQR: (device: Device) => void;
  onDownloadCA: (device: Device) => void;
  onDownloadCert: (device: Device) => void;
  onDownloadKey: (device: Device) => void;
  onDownloadBundle: (device: Device) => void;
  onConfigure: (device: Device) => void;
  onRestart: (device: Device) => void;
  onUpdateFirmware: (device: Device) => void;
  onDelete: (device: Device) => void;
}

export function DeviceTableRow({
  device,
  isSelected,
  onSelect,
  getDeviceIcon,
  getStatusColor,
  onViewDetails,
  onEdit,
  onGenerateQR,
  onDownloadCA,
  onDownloadCert,
  onDownloadKey,
  onDownloadBundle,
  onConfigure,
  onRestart,
  onUpdateFirmware,
  onDelete
}: DeviceTableRowProps) {
  return (
    <TableRow>
      <TableCell>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(e.target.checked)}
          className="rounded border-gray-300"
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-2 rounded-lg",
            device.type === 'sensor' ? 'bg-blue-100 text-blue-600' :
            device.type === 'actuator' ? 'bg-purple-100 text-purple-600' :
            device.type === 'gateway' ? 'bg-green-100 text-green-600' :
            'bg-gray-100 text-gray-600'
          )}>
            {getDeviceIcon(device.type)}
          </div>
          <div>
            <p className="font-medium">{device.name}</p>
            <p className="text-sm text-muted-foreground">{device.serialNumber}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary">
          {device.type}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className={cn(
            "h-2 w-2 rounded-full",
            device.status === 'online' ? 'bg-green-600 animate-pulse' :
            device.status === 'offline' ? 'bg-gray-400' :
            device.status === 'error' ? 'bg-red-600' :
            'bg-yellow-600'
          )} />
          <span className={cn("text-sm font-medium", getStatusColor(device.status))}>
            {device.status}
          </span>
        </div>
      </TableCell>
      <TableCell>{device.organizationName}</TableCell>
      <TableCell>
        {device.location ? (
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3 text-muted-foreground" />
            <span className="text-sm">{device.location.name}</span>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell>
        <span className="text-sm text-muted-foreground">
          {formatRelativeTimeWithTimezone(device.lastSeen)}
        </span>
      </TableCell>
      <TableCell>
        {device.status === 'online' ? (
          <span className="text-sm font-medium">
            {device.telemetry.messagesPerMinute} msg/min
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">-</span>
        )}
      </TableCell>
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
            <DropdownMenuItem onClick={() => onViewDetails(device)}>
              <Info className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit(device)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit Device
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onGenerateQR(device)}>
              <QrCode className="mr-2 h-4 w-4" />
              QR Code
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onDownloadCA(device)}>
              <Key className="mr-2 h-4 w-4" />
              Download CA Chain
            </DropdownMenuItem>
            {/* Only show certificate downloads if device has a certificate */}
            {device.certificate && (
              <>
                <DropdownMenuItem onClick={() => onDownloadCert(device)}>
                  <Key className="mr-2 h-4 w-4" />
                  Download Certificate
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDownloadKey(device)}>
                  <Key className="mr-2 h-4 w-4" />
                  Download Private Key
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDownloadBundle(device)}>
                  <Download className="mr-2 h-4 w-4" />
                  Download Bundle (ZIP)
                </DropdownMenuItem>
              </>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onConfigure(device)}>
              <Wifi className="mr-2 h-4 w-4" />
              Configure
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onRestart(device)}>
              <Zap className="mr-2 h-4 w-4" />
              Restart
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onUpdateFirmware(device)}>
              <Download className="mr-2 h-4 w-4" />
              Update Firmware
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={() => onDelete(device)}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Device
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}