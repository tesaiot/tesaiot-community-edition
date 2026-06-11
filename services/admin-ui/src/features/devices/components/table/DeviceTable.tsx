/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Table, TableBody } from '@/components/ui/table';
import { Device } from '../../types/device.types';
import { DeviceTableHeader } from './DeviceTableHeader';
import { DeviceTableRow } from './DeviceTableRow';

interface DeviceTableProps {
  devices: Device[];
  selectedDevices: string[];
  onSelectionChange: (deviceIds: string[]) => void;
  onViewDetails: (device: Device) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  onGenerateQRCode: (device: Device) => void;
  onManageCertificates: (device: Device) => void;
  onUpdateFirmware?: (device: Device) => void;
  onRestartDevice?: (device: Device) => void;
  onRenewCertificate?: (device: Device) => void;
}

export function DeviceTable({
  devices,
  selectedDevices,
  onSelectionChange,
  onViewDetails,
  onEdit,
  onDelete,
  onGenerateQRCode,
  onManageCertificates,
  onUpdateFirmware,
  onRestartDevice,
  onRenewCertificate,
}: DeviceTableProps) {
  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      onSelectionChange(devices.map(d => d.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectDevice = (deviceId: string, selected: boolean) => {
    if (selected) {
      onSelectionChange([...selectedDevices, deviceId]);
    } else {
      onSelectionChange(selectedDevices.filter(id => id !== deviceId));
    }
  };

  const isAllSelected = selectedDevices.length === devices.length && devices.length > 0;

  return (
    <div className="rounded-md border overflow-x-auto">
      <Table className="min-w-full">
        <DeviceTableHeader 
          isAllSelected={isAllSelected}
          onSelectAll={handleSelectAll}
        />
        <TableBody>
          {devices.map((device) => (
            <DeviceTableRow
              key={device.id}
              device={device}
              isSelected={selectedDevices.includes(device.id)}
              onSelectionChange={(selected) => handleSelectDevice(device.id, selected)}
              onViewDetails={onViewDetails}
              onEdit={onEdit}
              onDelete={onDelete}
              onGenerateQRCode={onGenerateQRCode}
              onManageCertificates={onManageCertificates}
              onUpdateFirmware={onUpdateFirmware}
              onRestartDevice={onRestartDevice}
              onRenewCertificate={onRenewCertificate}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}