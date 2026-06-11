/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { RefreshCw, Trash2, Download, Power, Edit, Eye } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

// Import BdhDataGrid components
import {
  BdhDataGrid,
  BdhDataGridTable,
  BdhDataGridToolbar,
  BdhDataGridPagination,
  BdhDataGridBulkActions,
  BulkAction,
  RowAction,
} from '@/components/ui/bdh-data-grid';

// ============================================================================
// Types
// ============================================================================

interface Device {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'warning';
  type: string;
  firmware: string;
  lastSeen: string;
  ipAddress: string;
  certificates: {
    device: { valid: boolean; expiresAt: string };
    mqtt: { valid: boolean; expiresAt: string };
  };
}

// ============================================================================
// Mock Data
// ============================================================================

const mockDevices: Device[] = [
  {
    id: '1',
    name: 'PSoC Edge E84 - Factory Floor 1',
    status: 'online',
    type: 'PSoC Edge E84',
    firmware: 'v2.1.0',
    lastSeen: '2026-01-18T10:30:00Z',
    ipAddress: '192.168.1.101',
    certificates: {
      device: { valid: true, expiresAt: '2027-01-18T00:00:00Z' },
      mqtt: { valid: true, expiresAt: '2027-01-18T00:00:00Z' },
    },
  },
  {
    id: '2',
    name: 'ESP32-S3 Temperature Sensor',
    status: 'offline',
    type: 'ESP32-S3',
    firmware: 'v1.5.2',
    lastSeen: '2026-01-17T15:45:00Z',
    ipAddress: '192.168.1.102',
    certificates: {
      device: { valid: true, expiresAt: '2026-06-15T00:00:00Z' },
      mqtt: { valid: false, expiresAt: '2026-01-01T00:00:00Z' },
    },
  },
  {
    id: '3',
    name: 'Raspberry Pi Gateway',
    status: 'warning',
    type: 'Raspberry Pi 4',
    firmware: 'v3.0.1',
    lastSeen: '2026-01-18T10:28:00Z',
    ipAddress: '192.168.1.103',
    certificates: {
      device: { valid: true, expiresAt: '2026-02-28T00:00:00Z' },
      mqtt: { valid: true, expiresAt: '2026-02-28T00:00:00Z' },
    },
  },
  // Add more mock devices as needed...
];

// ============================================================================
// Column Definitions
// ============================================================================

const columns: ColumnDef<Device>[] = [
  {
    accessorKey: 'name',
    header: 'Device Name',
    cell: ({ row }) => (
      <div className="font-medium">{row.original.name}</div>
    ),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.original.status;
      const variants = {
        online: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        offline: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
        warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      };
      return (
        <Badge className={variants[status]}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      );
    },
  },
  {
    accessorKey: 'type',
    header: 'Device Type',
  },
  {
    accessorKey: 'firmware',
    header: 'Firmware',
    cell: ({ row }) => (
      <code className="text-xs bg-muted px-1 py-0.5 rounded">
        {row.original.firmware}
      </code>
    ),
  },
  {
    accessorKey: 'lastSeen',
    header: 'Last Seen',
    cell: ({ row }) => {
      const date = new Date(row.original.lastSeen);
      return date.toLocaleString();
    },
  },
  {
    accessorKey: 'ipAddress',
    header: 'IP Address',
    cell: ({ row }) => (
      <code className="text-xs">{row.original.ipAddress}</code>
    ),
  },
];

// ============================================================================
// Example Component
// ============================================================================

export function DeviceListExample() {
  const [devices, setDevices] = useState<Device[]>(mockDevices);
  const [isLoading, setIsLoading] = useState(false);

  // ============================================================================
  // Bulk Actions
  // ============================================================================

  const bulkActions: BulkAction<Device>[] = [
    {
      id: 'restart',
      label: 'Restart',
      icon: <RefreshCw className="h-4 w-4" />,
      onClick: async (selectedDevices) => {
        toast.promise(
          new Promise((resolve) => setTimeout(resolve, 2000)),
          {
            loading: `Restarting ${selectedDevices.length} device(s)...`,
            success: `Successfully restarted ${selectedDevices.length} device(s)`,
            error: 'Failed to restart devices',
          }
        );
      },
    },
    {
      id: 'export',
      label: 'Export',
      icon: <Download className="h-4 w-4" />,
      onClick: (selectedDevices) => {
        toast.success(`Exported ${selectedDevices.length} device(s) to CSV`);
      },
    },
    {
      id: 'delete',
      label: 'Delete',
      icon: <Trash2 className="h-4 w-4" />,
      variant: 'destructive',
      requireConfirmation: true,
      confirmationMessage: 'This will permanently delete the selected devices. This action cannot be undone.',
      onClick: async (selectedDevices) => {
        const ids = selectedDevices.map((d) => d.id);
        setDevices((prev) => prev.filter((d) => !ids.includes(d.id)));
        toast.success(`Deleted ${selectedDevices.length} device(s)`);
      },
    },
  ];

  // ============================================================================
  // Row Actions
  // ============================================================================

  const rowActions: RowAction<Device>[] = [
    {
      id: 'view',
      label: 'View Details',
      icon: <Eye className="h-4 w-4" />,
      onClick: (device) => {
        toast.info(`Viewing details for ${device.name}`);
      },
    },
    {
      id: 'edit',
      label: 'Edit',
      icon: <Edit className="h-4 w-4" />,
      onClick: (device) => {
        toast.info(`Editing ${device.name}`);
      },
    },
    {
      id: 'restart',
      label: 'Restart',
      icon: <RefreshCw className="h-4 w-4" />,
      disabled: (device) => device.status === 'offline',
      onClick: (device) => {
        toast.promise(
          new Promise((resolve) => setTimeout(resolve, 2000)),
          {
            loading: `Restarting ${device.name}...`,
            success: `Successfully restarted ${device.name}`,
            error: 'Failed to restart device',
          }
        );
      },
    },
    {
      id: 'toggle-power',
      label: 'Power Off',
      icon: <Power className="h-4 w-4" />,
      variant: 'destructive',
      onClick: (device) => {
        toast.warning(`Powering off ${device.name}`);
      },
    },
  ];

  // ============================================================================
  // Auto-Sync Handler
  // ============================================================================

  const handleDataRefresh = async (): Promise<Device[]> => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    // In real app, fetch from API
    return devices;
  };

  // ============================================================================
  // Render Expanded Row
  // ============================================================================

  const renderExpandedRow = (device: Device) => (
    <div className="grid grid-cols-2 gap-4 p-4">
      <div>
        <h4 className="font-medium mb-2">Device Information</h4>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Type:</dt>
            <dd>{device.type}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Firmware:</dt>
            <dd>{device.firmware}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted-foreground">IP Address:</dt>
            <dd>{device.ipAddress}</dd>
          </div>
        </dl>
      </div>
      <div>
        <h4 className="font-medium mb-2">Certificate Status</h4>
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Device Certificate:</dt>
            <dd>
              <Badge variant={device.certificates.device.valid ? 'default' : 'destructive'}>
                {device.certificates.device.valid ? 'Valid' : 'Expired'}
              </Badge>
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted-foreground">MQTT Certificate:</dt>
            <dd>
              <Badge variant={device.certificates.mqtt.valid ? 'default' : 'destructive'}>
                {device.certificates.mqtt.valid ? 'Valid' : 'Expired'}
              </Badge>
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">All Devices</h1>
      </div>

      <BdhDataGrid
        data={devices}
        columns={columns}
        getRowId={(device) => device.id}
        // Feature flags
        enableSelection={true}
        enableBulkActions={true}
        enableSorting={true}
        enableExpandableRows={true}
        enablePagination={true}
        enableSearch={true}
        enableColumnVisibility={true}
        enableAutoSync={true}
        enableExport={true}
        enableRowActions={true}
        // Pagination options
        initialPageSize={10}
        pageSizeOptions={[10, 20, 50, 100]}
        // Selection
        selectionMode="multiple"
        onSelectionChange={(ids, rows) => {
          console.log('Selected:', ids, rows);
        }}
        // Bulk actions
        bulkActions={bulkActions}
        // Row actions
        rowActions={rowActions}
        // Expandable rows
        renderExpandedRow={renderExpandedRow}
        // Auto-sync
        syncMode="polling"
        pollingInterval={30000}
        onDataRefresh={handleDataRefresh}
        // Export
        exportFormats={['csv', 'excel', 'json']}
        exportFilename="devices"
        // Loading state
        isLoading={isLoading}
        // Events
        onRowClick={(device) => {
          console.log('Row clicked:', device);
        }}
      >
        {/* Toolbar with search, filters, column visibility, export */}
        <BdhDataGridToolbar
          searchPlaceholder="Search devices by name, type, or IP..."
          showSearch={true}
          showColumnVisibility={true}
          showExport={true}
          showRefresh={true}
        />

        {/* Bulk actions bar (shows when items selected) */}
        <BdhDataGridBulkActions position="floating" />

        {/* Data table */}
        <BdhDataGridTable
          stickyHeader={true}
          stripedRows={true}
          compactMode={false}
        />

        {/* Pagination controls */}
        <BdhDataGridPagination
          showRowsPerPage={true}
          showPageNumbers={true}
          showItemCount={true}
          showFirstLast={false}
        />
      </BdhDataGrid>
    </div>
  );
}

export default DeviceListExample;
