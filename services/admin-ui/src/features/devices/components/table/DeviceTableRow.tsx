/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { format } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  formatRelativeTime, 
  formatRelativeTimeWithTimezone,
  getDateTooltipText, 
  formatDataRate, 
  getDataRateTooltip 
} from '@/utils/dateFormatting';
import { CertificateStatusBadge, getCertificateInfo } from '@/features/certificates/components/CertificateStatusBadge';
import {
  TableCell,
  TableRow,
} from '@/components/ui/table';
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
  Edit,
  Trash2,
  Shield,
  Package,
  RefreshCw,
  Info,
  QrCode,
  MapPin,
  Terminal,
  Zap,
  Router,
  Cpu,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Device } from '../../types/device.types';

interface DeviceTableRowProps {
  device: Device;
  isSelected: boolean;
  onSelectionChange: (selected: boolean) => void;
  onViewDetails: (device: Device) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  onGenerateQRCode: (device: Device) => void;
  onManageCertificates: (device: Device) => void;
  onUpdateFirmware?: (device: Device) => void;
  onRestartDevice?: (device: Device) => void;
  onRenewCertificate?: (device: Device) => void;
}

export function DeviceTableRow({
  device,
  isSelected,
  onSelectionChange,
  onViewDetails,
  onEdit,
  onDelete,
  onGenerateQRCode,
  onManageCertificates,
  onUpdateFirmware,
  onRestartDevice,
  onRenewCertificate,
}: DeviceTableRowProps) {
  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'sensor': return <Terminal className="h-4 w-4" />;
      case 'actuator': return <Zap className="h-4 w-4" />;
      case 'gateway': return <Router className="h-4 w-4" />;
      case 'controller': return <Cpu className="h-4 w-4" />;
      default: return <Server className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-600';
      case 'offline':
        return 'text-gray-600';
      case 'error':
        return 'text-red-600';
      case 'maintenance':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <TableRow>
      <TableCell>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelectionChange(e.target.checked)}
          className="rounded border-gray-300"
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-3">
          {device.metadata?.devicePicture ? (
            <div className="relative h-auto w-12 rounded-lg overflow-hidden border border-gray-200">
              <img
                src={device.metadata.devicePicture}
                alt={device.name}
                className="h-auto w-12 object-contain"
                onError={(e) => {
                  // Fallback to icon if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const parent = target.parentElement;
                  if (parent) {
                    parent.innerHTML = '';
                    parent.className = cn(
                      "h-12 w-12 p-2 rounded-lg flex items-center justify-center",
                      device.type === 'sensor' ? 'bg-blue-100 text-blue-600' :
                      device.type === 'actuator' ? 'bg-purple-100 text-purple-600' :
                      device.type === 'gateway' ? 'bg-green-100 text-green-600' :
                      'bg-gray-100 text-gray-600'
                    );
                    const icon = getDeviceIcon(device.type);
                    if (React.isValidElement(icon)) {
                      const iconElement = document.createElement('div');
                      iconElement.innerHTML = `<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">${icon.props.children || ''}</svg>`;
                      parent.appendChild(iconElement.firstChild as Node);
                    }
                  }
                }}
              />
            </div>
          ) : (
            <div className={cn(
              "h-12 w-12 p-2 rounded-lg flex items-center justify-center",
              device.type === 'sensor' ? 'bg-blue-100 text-blue-600' :
              device.type === 'actuator' ? 'bg-purple-100 text-purple-600' :
              device.type === 'gateway' ? 'bg-green-100 text-green-600' :
              'bg-gray-100 text-gray-600'
            )}>
              {getDeviceIcon(device.type)}
            </div>
          )}
          <div>
            <p className="font-medium">{device.name}</p>
            <p
              className="text-sm text-muted-foreground font-mono break-all leading-snug max-w-[260px]"
              title={device.serialNumber}
            >
              {device.serialNumber}
            </p>
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
      <TableCell>
        <CertificateStatusBadge
          certificate={getCertificateInfo(device)}
          variant="compact"
          showRenewButton={false}
          onRenew={onRenewCertificate ? () => onRenewCertificate(device) : undefined}
        />
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
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-sm cursor-help">
                {formatRelativeTimeWithTimezone(device.lastSeen)}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{getDateTooltipText(device.lastSeen)}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </TableCell>
      <TableCell>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className={cn(
                "text-sm cursor-help",
                device.status === 'online' && device.telemetry?.messagesPerMinute > 0 
                  ? "font-medium" 
                  : "text-muted-foreground"
              )}>
                {formatDataRate(device.telemetry?.messagesPerMinute, device.status === 'online')}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{getDataRateTooltip(device.telemetry?.messagesPerMinute, device.status === 'online')}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
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
            <DropdownMenuItem onClick={() => onGenerateQRCode(device)}>
              <QrCode className="mr-2 h-4 w-4" />
              QR Code
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onManageCertificates(device)}>
              <Shield className="mr-2 h-4 w-4" />
              {device.auth_mode === 'server_tls' ? 'Download CA Certificate' : 'Manage Certificates'}
            </DropdownMenuItem>
            {onRenewCertificate && device.auth_mode !== 'server_tls' && getCertificateInfo(device)?.status && (
              <DropdownMenuItem 
                onClick={() => onRenewCertificate(device)}
                className="text-blue-600"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Renew Certificate
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {onUpdateFirmware && (
              <DropdownMenuItem onClick={() => onUpdateFirmware(device)}>
                <Package className="mr-2 h-4 w-4" />
                Update Firmware
              </DropdownMenuItem>
            )}
            {onRestartDevice && (
              <DropdownMenuItem onClick={() => onRestartDevice(device)}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Restart Device
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              className="text-red-600"
              onClick={() => onDelete(device)}
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
