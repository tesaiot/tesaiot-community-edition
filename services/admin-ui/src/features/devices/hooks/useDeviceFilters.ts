/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useMemo } from 'react';
import { Device } from '../types/device.types';

/**
 * Custom hook for managing device filters
 */
export function useDeviceFilters(devices: Device[]) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterOrg, setFilterOrg] = useState<string>('all');

  // Filter devices based on all criteria
  const filteredDevices = useMemo(() => {
    return devices.filter(device => {
      const matchesSearch = 
        device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.serialNumber.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesType = filterType === 'all' || device.type === filterType;
      const matchesStatus = filterStatus === 'all' || device.status === filterStatus;
      const matchesOrg = filterOrg === 'all' || device.organizationId === filterOrg;
      
      return matchesSearch && matchesType && matchesStatus && matchesOrg;
    });
  }, [devices, searchTerm, filterType, filterStatus, filterOrg]);

  return {
    searchTerm,
    setSearchTerm,
    filterType,
    setFilterType,
    filterStatus,
    setFilterStatus,
    filterOrg,
    setFilterOrg,
    filteredDevices
  };
}