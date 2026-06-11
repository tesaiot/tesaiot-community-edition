/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { Search, Cpu, Gauge, Network, Router, CheckCircle, XCircle, AlertTriangle, Wrench, Building2 } from 'lucide-react';

interface DeviceFilterFormProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  filterType: string;
  onFilterTypeChange: (value: string) => void;
  filterStatus: string;
  onFilterStatusChange: (value: string) => void;
  filterOrg: string;
  onFilterOrgChange: (value: string) => void;
  showOrgFilter: boolean;
}

export function DeviceFilterForm({
  searchTerm,
  onSearchChange,
  filterType,
  onFilterTypeChange,
  filterStatus,
  onFilterStatusChange,
  filterOrg,
  onFilterOrgChange,
  showOrgFilter
}: DeviceFilterFormProps) {
  return (
    <div className="flex flex-col md:flex-row gap-4 mb-6">
      <div className="flex-1">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search devices..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
      
      <SearchableSelect
        options={[
          { 
            value: 'all', 
            label: 'All Types',
            description: 'Show all device types'
          },
          { 
            value: 'sensor', 
            label: 'Sensors',
            description: 'Environmental and monitoring sensors',
            icon: <Cpu className="h-4 w-4 text-blue-500" />
          },
          { 
            value: 'actuator', 
            label: 'Actuators',
            description: 'Control and automation devices',
            icon: <Gauge className="h-4 w-4 text-green-500" />
          },
          { 
            value: 'gateway', 
            label: 'Gateways',
            description: 'Network and communication gateways',
            icon: <Network className="h-4 w-4 text-purple-500" />
          },
          { 
            value: 'controller', 
            label: 'Controllers',
            description: 'Device controllers and orchestrators',
            icon: <Router className="h-4 w-4 text-orange-500" />
          }
        ]}
        value={filterType}
        onValueChange={onFilterTypeChange}
        placeholder="Device type"
        searchable={false}
        className="w-[180px]"
      />
      
      <SearchableSelect
        options={[
          { 
            value: 'all', 
            label: 'All Status',
            description: 'Show devices in any status'
          },
          { 
            value: 'online', 
            label: 'Online',
            description: 'Active and connected devices',
            icon: <CheckCircle className="h-4 w-4 text-green-500" />
          },
          { 
            value: 'offline', 
            label: 'Offline',
            description: 'Disconnected or powered off',
            icon: <XCircle className="h-4 w-4 text-gray-500" />
          },
          { 
            value: 'error', 
            label: 'Error',
            description: 'Devices with errors or issues',
            icon: <AlertTriangle className="h-4 w-4 text-red-500" />
          },
          { 
            value: 'maintenance', 
            label: 'Maintenance',
            description: 'Under maintenance or repair',
            icon: <Wrench className="h-4 w-4 text-yellow-500" />
          }
        ]}
        value={filterStatus}
        onValueChange={onFilterStatusChange}
        placeholder="Status"
        searchable={false}
        className="w-[180px]"
      />
      
      {showOrgFilter && (
        <SearchableSelect
          options={[
            { 
              value: 'all', 
              label: 'All Organizations',
              description: 'Show devices from all organizations',
              icon: <Building2 className="h-4 w-4 text-blue-500" />
            },
            { 
              value: 'org-001', 
              label: 'Acme IoT Solutions',
              description: 'Industrial IoT provider',
              icon: <Building2 className="h-4 w-4 text-gray-500" />
            },
            { 
              value: 'org-002', 
              label: 'Smart Factory GmbH',
              description: 'Manufacturing automation',
              icon: <Building2 className="h-4 w-4 text-gray-500" />
            },
            { 
              value: 'org-003', 
              label: 'CityLink IoT',
              description: 'Smart city infrastructure',
              icon: <Building2 className="h-4 w-4 text-gray-500" />
            }
          ]}
          value={filterOrg}
          onValueChange={onFilterOrgChange}
          placeholder="Organization"
          searchable={true}
          searchPlaceholder="Search organizations..."
          className="w-[250px]"
        />
      )}
    </div>
  );
}