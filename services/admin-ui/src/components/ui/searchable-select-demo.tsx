/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

'use client';

import * as React from 'react';
import { SearchableSelect, SelectOption, SelectGroup } from './searchable-select';
import { Badge } from './badge';
import { Card } from './card';
import { Button } from './button';
import { 
  User, 
  Building, 
  Globe, 
  Settings, 
  Star, 
  Zap,
  Database,
  Cloud,
  Shield,
  Smartphone
} from 'lucide-react';

// Sample data
const deviceTypes: SelectOption[] = [
  { 
    value: 'sensor', 
    label: 'IoT Sensor', 
    description: 'Temperature, humidity, and environmental sensors',
    icon: <Zap className="size-4" />
  },
  { 
    value: 'gateway', 
    label: 'IoT Gateway', 
    description: 'Network gateway for device connectivity',
    icon: <Globe className="size-4" />
  },
  { 
    value: 'controller', 
    label: 'Controller', 
    description: 'Industrial automation controllers',
    icon: <Settings className="size-4" />
  },
  { 
    value: 'display', 
    label: 'Display Unit', 
    description: 'LCD and LED display devices',
    icon: <Smartphone className="size-4" />
  },
  { 
    value: 'storage', 
    label: 'Data Storage', 
    description: 'Local and cloud storage devices',
    icon: <Database className="size-4" />
  },
];

const organizations: SelectOption[] = [
  { value: 'bdh-corp', label: 'BDH Corporation', icon: <Building className="size-4" /> },
  { value: 'tesa', label: 'Thai Embedded Systems Association', icon: <Star className="size-4" /> },
  { value: 'iot-tech', label: 'IoT Technology Solutions', icon: <Cloud className="size-4" /> },
  { value: 'smart-city', label: 'Smart City Initiative', icon: <Shield className="size-4" /> },
  { value: 'industrial-auto', label: 'Industrial Automation Co.', icon: <Settings className="size-4" /> },
];

const userRoles: SelectGroup[] = [
  {
    label: 'Administration',
    options: [
      { value: 'super-admin', label: 'Super Administrator', description: 'Full system access' },
      { value: 'admin', label: 'Administrator', description: 'Organization management' },
      { value: 'moderator', label: 'Moderator', description: 'Content moderation' },
    ]
  },
  {
    label: 'Operations',
    options: [
      { value: 'operator', label: 'System Operator', description: 'Day-to-day operations' },
      { value: 'technician', label: 'Technician', description: 'Technical maintenance' },
      { value: 'analyst', label: 'Data Analyst', description: 'Data analysis and reporting' },
    ]
  },
  {
    label: 'Users',
    options: [
      { value: 'user', label: 'Standard User', description: 'Basic system access' },
      { value: 'viewer', label: 'Viewer', description: 'Read-only access' },
      { value: 'guest', label: 'Guest', description: 'Limited access' },
    ]
  }
];

const countries = [
  { value: 'th', label: 'Thailand' },
  { value: 'us', label: 'United States' },
  { value: 'jp', label: 'Japan' },
  { value: 'sg', label: 'Singapore' },
  { value: 'my', label: 'Malaysia' },
  { value: 'id', label: 'Indonesia' },
  { value: 'vn', label: 'Vietnam' },
  { value: 'ph', label: 'Philippines' },
  { value: 'in', label: 'India' },
  { value: 'cn', label: 'China' },
  { value: 'kr', label: 'South Korea' },
  { value: 'au', label: 'Australia' },
  { value: 'nz', label: 'New Zealand' },
  { value: 'de', label: 'Germany' },
  { value: 'fr', label: 'France' },
  { value: 'uk', label: 'United Kingdom' },
  { value: 'ca', label: 'Canada' },
  { value: 'br', label: 'Brazil' },
  { value: 'mx', label: 'Mexico' },
  { value: 'ar', label: 'Argentina' },
];

export function SearchableSelectDemo() {
  const [selectedDevice, setSelectedDevice] = React.useState<string>('');
  const [selectedOrg, setSelectedOrg] = React.useState<string>('');
  const [selectedRoles, setSelectedRoles] = React.useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = React.useState<string[]>([]);
  const [asyncOptions, setAsyncOptions] = React.useState<SelectOption[]>([]);
  const [asyncLoading, setAsyncLoading] = React.useState(false);

  // Simulate async search
  const handleAsyncSearch = React.useCallback(async (query: string) => {
    setAsyncLoading(true);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Filter countries based on query
    const filtered = countries.filter(country =>
      country.label.toLowerCase().includes(query.toLowerCase())
    );
    
    setAsyncOptions(filtered);
    setAsyncLoading(false);
  }, []);

  // Custom render function for selected organizations
  const renderSelectedOrganization = (options: SelectOption[]) => {
    if (options.length === 0) return null;
    const org = options[0];
    return (
      <div className="flex items-center gap-2">
        {org.icon}
        <span>{org.label}</span>
      </div>
    );
  };

  // Custom render function for role options
  const renderRoleOption = (option: SelectOption, isSelected: boolean) => (
    <div className="flex items-center justify-between w-full">
      <div>
        <div className="font-medium">{option.label}</div>
        <div className="text-xs text-muted-foreground">{option.description}</div>
      </div>
      {isSelected && <Badge variant="secondary" className="ml-2">Selected</Badge>}
    </div>
  );

  return (
    <div className="space-y-8 p-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Searchable Select Demo</h1>
        <p className="text-muted-foreground mt-2">
          Comprehensive examples of the SearchableSelect component in various configurations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Basic Single Select */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Basic Single Select</h3>
          <div className="space-y-4">
            <SearchableSelect
              options={deviceTypes}
              value={selectedDevice}
              onValueChange={(value) => setSelectedDevice(value as string)}
              placeholder="Select a device type..."
              searchPlaceholder="Search device types..."
              size="md"
            />
            <div className="text-sm text-muted-foreground">
              Selected: {selectedDevice || 'None'}
            </div>
          </div>
        </Card>

        {/* Custom Rendering */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Custom Rendering</h3>
          <div className="space-y-4">
            <SearchableSelect
              options={organizations}
              value={selectedOrg}
              onValueChange={(value) => setSelectedOrg(value as string)}
              placeholder="Select organization..."
              renderSelectedValue={renderSelectedOrganization}
              size="md"
            />
            <div className="text-sm text-muted-foreground">
              Selected: {selectedOrg || 'None'}
            </div>
          </div>
        </Card>

        {/* Multiple Select with Groups */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Multiple Select with Groups</h3>
          <div className="space-y-4">
            <SearchableSelect
              groups={userRoles}
              value={selectedRoles}
              onValueChange={(value) => setSelectedRoles(value as string[])}
              multiple
              placeholder="Select user roles..."
              renderOption={renderRoleOption}
              size="md"
              maxHeight={250}
            />
            <div className="text-sm text-muted-foreground">
              Selected: {selectedRoles.length} role(s)
            </div>
            <div className="flex flex-wrap gap-1">
              {selectedRoles.map(role => (
                <Badge key={role} variant="secondary">{role}</Badge>
              ))}
            </div>
          </div>
        </Card>

        {/* Async Search */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Async Search</h3>
          <div className="space-y-4">
            <SearchableSelect
              options={asyncOptions}
              value={selectedCountries}
              onValueChange={(value) => setSelectedCountries(value as string[])}
              multiple
              loading={asyncLoading}
              onSearch={handleAsyncSearch}
              placeholder="Search countries..."
              searchPlaceholder="Type to search countries..."
              emptyMessage="Type to search for countries"
              loadingMessage="Searching countries..."
              searchDebounceMs={500}
              size="md"
            />
            <div className="text-sm text-muted-foreground">
              Selected: {selectedCountries.length} countries
            </div>
          </div>
        </Card>

        {/* Size Variants */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Size Variants</h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Small</label>
              <SearchableSelect
                options={deviceTypes.slice(0, 3)}
                placeholder="Small size..."
                size="sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Medium (Default)</label>
              <SearchableSelect
                options={deviceTypes.slice(0, 3)}
                placeholder="Medium size..."
                size="md"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Large</label>
              <SearchableSelect
                options={deviceTypes.slice(0, 3)}
                placeholder="Large size..."
                size="lg"
              />
            </div>
          </div>
        </Card>

        {/* Advanced Features */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Advanced Features</h3>
          <div className="space-y-4">
            <SearchableSelect
              options={countries}
              multiple
              clearable
              rememberRecentSelections
              maxRecentSelections={3}
              virtualScrolling
              placeholder="Advanced select with all features..."
              searchPlaceholder="Search with virtual scrolling..."
              size="md"
              maxHeight={200}
            />
            <div className="text-xs text-muted-foreground">
              Features: Virtual scrolling, recent selections, clearable
            </div>
          </div>
        </Card>
      </div>

      {/* Usage Examples */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Usage Examples</h3>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium mb-2">Basic Usage</h4>
            <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto">
{`<SearchableSelect
  options={options}
  value={value}
  onValueChange={setValue}
  placeholder="Select an option..."
/>`}
            </pre>
          </div>

          <div>
            <h4 className="font-medium mb-2">Multiple Select with Groups</h4>
            <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto">
{`<SearchableSelect
  groups={groups}
  value={selectedValues}
  onValueChange={setSelectedValues}
  multiple
  placeholder="Select multiple options..."
/>`}
            </pre>
          </div>

          <div>
            <h4 className="font-medium mb-2">Async Search</h4>
            <pre className="bg-muted p-3 rounded-md text-sm overflow-x-auto">
{`<SearchableSelect
  options={asyncOptions}
  loading={loading}
  onSearch={handleSearch}
  searchDebounceMs={300}
  placeholder="Search..."
/>`}
            </pre>
          </div>
        </div>
      </Card>

      {/* Reset Button */}
      <div className="flex justify-center">
        <Button
          onClick={() => {
            setSelectedDevice('');
            setSelectedOrg('');
            setSelectedRoles([]);
            setSelectedCountries([]);
            setAsyncOptions([]);
          }}
          variant="outline"
        >
          Reset All Selections
        </Button>
      </div>
    </div>
  );
}

export default SearchableSelectDemo;