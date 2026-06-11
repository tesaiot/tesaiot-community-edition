/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

'use client';

import * as React from 'react';
import { SearchableSelect, SelectOption } from './searchable-select';
import { Button } from './button';
import { Card } from './card';
import { Label } from './label';
import { Input } from './input';

// Sample integration examples showing how to replace existing dropdowns

// Example 1: Device Management Form
export function DeviceManagementForm() {
  const [formData, setFormData] = React.useState({
    deviceName: '',
    deviceType: '',
    organization: '',
    location: '',
    status: 'active',
  });

  const deviceTypes: SelectOption[] = [
    { value: 'sensor', label: 'IoT Sensor', description: 'Temperature and environmental sensors' },
    { value: 'gateway', label: 'IoT Gateway', description: 'Network connectivity device' },
    { value: 'controller', label: 'Controller', description: 'Industrial automation controller' },
    { value: 'display', label: 'Display Unit', description: 'LCD and LED displays' },
  ];

  const organizations: SelectOption[] = [
    { value: 'bdh-corp', label: 'BDH Corporation' },
    { value: 'tesa', label: 'Thai Embedded Systems Association' },
    { value: 'iot-tech', label: 'IoT Technology Solutions' },
  ];

  const statusOptions: SelectOption[] = [
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' },
    { value: 'maintenance', label: 'Under Maintenance' },
    { value: 'decommissioned', label: 'Decommissioned' },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
  };

  return (
    <Card className="p-6 max-w-md">
      <h3 className="text-lg font-semibold mb-4">Add New Device</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="deviceName">Device Name</Label>
          <Input
            id="deviceName"
            value={formData.deviceName}
            onChange={(e) => setFormData(prev => ({ ...prev, deviceName: e.target.value }))}
            placeholder="Enter device name..."
          />
        </div>

        <div>
          <Label htmlFor="deviceType">Device Type</Label>
          {/* OLD WAY: Standard HTML select
          <select 
            value={formData.deviceType} 
            onChange={(e) => setFormData(prev => ({ ...prev, deviceType: e.target.value }))}
          >
            <option value="">Select device type...</option>
            <option value="sensor">IoT Sensor</option>
            <option value="gateway">IoT Gateway</option>
          </select>
          */}
          
          {/* NEW WAY: SearchableSelect */}
          <SearchableSelect
            options={deviceTypes}
            value={formData.deviceType}
            onValueChange={(value) => setFormData(prev => ({ ...prev, deviceType: value as string }))}
            placeholder="Select device type..."
            size="md"
            aria-describedby="deviceType"
          />
        </div>

        <div>
          <Label htmlFor="organization">Organization</Label>
          <SearchableSelect
            options={organizations}
            value={formData.organization}
            onValueChange={(value) => setFormData(prev => ({ ...prev, organization: value as string }))}
            placeholder="Select organization..."
            searchPlaceholder="Search organizations..."
            size="md"
          />
        </div>

        <div>
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={formData.location}
            onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
            placeholder="Enter device location..."
          />
        </div>

        <div>
          <Label htmlFor="status">Status</Label>
          <SearchableSelect
            options={statusOptions}
            value={formData.status}
            onValueChange={(value) => setFormData(prev => ({ ...prev, status: value as string }))}
            placeholder="Select status..."
            searchable={false}  // Simple dropdown, no search needed
            size="md"
          />
        </div>

        <Button type="submit" className="w-full">
          Add Device
        </Button>
      </form>
    </Card>
  );
}

// Example 2: User Role Assignment
export function UserRoleAssignment() {
  const [selectedUser, setSelectedUser] = React.useState('');
  const [assignedRoles, setAssignedRoles] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(false);

  const users: SelectOption[] = [
    { value: 'user1', label: 'John Doe', description: 'john.doe@company.com' },
    { value: 'user2', label: 'Jane Smith', description: 'jane.smith@company.com' },
    { value: 'user3', label: 'Bob Johnson', description: 'bob.johnson@company.com' },
  ];

  const roles: SelectOption[] = [
    { value: 'admin', label: 'Administrator', description: 'Full system access' },
    { value: 'operator', label: 'System Operator', description: 'Operational tasks' },
    { value: 'analyst', label: 'Data Analyst', description: 'Analytics and reporting' },
    { value: 'viewer', label: 'Viewer', description: 'Read-only access' },
  ];

  const handleAssignRoles = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    console.log('Assigning roles:', { user: selectedUser, roles: assignedRoles });
    setLoading(false);
  };

  return (
    <Card className="p-6 max-w-md">
      <h3 className="text-lg font-semibold mb-4">Assign User Roles</h3>
      <div className="space-y-4">
        <div>
          <Label>Select User</Label>
          <SearchableSelect
            options={users}
            value={selectedUser}
            onValueChange={(value) => setSelectedUser(value as string)}
            placeholder="Search and select user..."
            searchPlaceholder="Type to search users..."
          />
        </div>

        <div>
          <Label>Assign Roles</Label>
          <SearchableSelect
            options={roles}
            value={assignedRoles}
            onValueChange={(value) => setAssignedRoles(value as string[])}
            multiple
            placeholder="Select multiple roles..."
            searchPlaceholder="Search roles..."
          />
        </div>

        <Button 
          onClick={handleAssignRoles}
          disabled={!selectedUser || assignedRoles.length === 0 || loading}
          className="w-full"
        >
          {loading ? 'Assigning...' : 'Assign Roles'}
        </Button>
      </div>
    </Card>
  );
}

// Example 3: Filter Controls
export function DataTableFilters() {
  const [filters, setFilters] = React.useState({
    deviceTypes: [] as string[],
    organizations: [] as string[],
    status: [] as string[],
    location: '',
  });

  const deviceTypes: SelectOption[] = [
    { value: 'sensor', label: 'Sensors' },
    { value: 'gateway', label: 'Gateways' },
    { value: 'controller', label: 'Controllers' },
    { value: 'display', label: 'Displays' },
  ];

  const organizations: SelectOption[] = [
    { value: 'bdh-corp', label: 'BDH Corporation' },
    { value: 'tesa', label: 'TESA' },
    { value: 'iot-tech', label: 'IoT Tech' },
  ];

  const statusOptions: SelectOption[] = [
    { value: 'online', label: 'Online' },
    { value: 'offline', label: 'Offline' },
    { value: 'maintenance', label: 'Maintenance' },
    { value: 'error', label: 'Error' },
  ];

  const handleClearFilters = () => {
    setFilters({
      deviceTypes: [],
      organizations: [],
      status: [],
      location: '',
    });
  };

  return (
    <Card className="p-4">
      <div className="flex flex-wrap gap-4 items-end">
        <div className="min-w-[200px]">
          <Label className="text-xs">Device Types</Label>
          <SearchableSelect
            options={deviceTypes}
            value={filters.deviceTypes}
            onValueChange={(value) => setFilters(prev => ({ ...prev, deviceTypes: value as string[] }))}
            multiple
            placeholder="Filter by type..."
            size="sm"
          />
        </div>

        <div className="min-w-[200px]">
          <Label className="text-xs">Organizations</Label>
          <SearchableSelect
            options={organizations}
            value={filters.organizations}
            onValueChange={(value) => setFilters(prev => ({ ...prev, organizations: value as string[] }))}
            multiple
            placeholder="Filter by org..."
            size="sm"
          />
        </div>

        <div className="min-w-[150px]">
          <Label className="text-xs">Status</Label>
          <SearchableSelect
            options={statusOptions}
            value={filters.status}
            onValueChange={(value) => setFilters(prev => ({ ...prev, status: value as string[] }))}
            multiple
            placeholder="Filter by status..."
            size="sm"
          />
        </div>

        <div className="min-w-[150px]">
          <Label className="text-xs">Location</Label>
          <Input
            value={filters.location}
            onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}
            placeholder="Location..."
            size="sm"
          />
        </div>

        <Button 
          variant="outline" 
          size="sm"
          onClick={handleClearFilters}
        >
          Clear Filters
        </Button>
      </div>
    </Card>
  );
}

// Integration container showing all examples
export function SearchableSelectIntegrationExamples() {
  return (
    <div className="space-y-8 p-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">SearchableSelect Integration Examples</h1>
        <p className="text-muted-foreground mt-2">
          Real-world examples showing how to integrate SearchableSelect into existing TESA IoT Platform components.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <DeviceManagementForm />
        <UserRoleAssignment />
        <div className="lg:col-span-2 xl:col-span-1">
          <DataTableFilters />
        </div>
      </div>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Migration Tips</h3>
        <div className="space-y-4 text-sm">
          <div>
            <h4 className="font-medium">Replace HTML Select Elements</h4>
            <p className="text-muted-foreground">
              Replace <code>&lt;select&gt;</code> elements with <code>&lt;SearchableSelect&gt;</code> for enhanced UX.
            </p>
          </div>
          <div>
            <h4 className="font-medium">Maintain Form Integration</h4>
            <p className="text-muted-foreground">
              The component works seamlessly with existing form state management and validation.
            </p>
          </div>
          <div>
            <h4 className="font-medium">Progressive Enhancement</h4>
            <p className="text-muted-foreground">
              Start with basic functionality and gradually add advanced features like search, multi-select, and async loading.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default SearchableSelectIntegrationExamples;