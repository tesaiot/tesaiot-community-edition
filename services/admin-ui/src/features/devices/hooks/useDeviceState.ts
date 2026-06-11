/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState } from 'react';
import { Device } from '../types/device.types';

/**
 * Custom hook for managing device component state
 * Centralizes all state management for the DeviceManagementWithCerts component
 */
export function useDeviceState(currentUserId?: string) {
  // Dialog visibility states
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [showQRDialog, setShowQRDialog] = useState(false);
  const [showTelemetryDashboard, setShowTelemetryDashboard] = useState(false);
  const [showTelemetryDashboardBeta, setShowTelemetryDashboardBeta] = useState(false);
  const [showEdgeAITelemetry, setShowEdgeAITelemetry] = useState(false);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [showCertificateDialog, setShowCertificateDialog] = useState(false);
  
  // Selected device and UI states
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [qrCodeData, setQrCodeData] = useState('');
  const [activeDetailTab, setActiveDetailTab] = useState('overview');
  
  // Telemetry states
  const [realTelemetryData, setRealTelemetryData] = useState<any[]>([]);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  
  // New device form state
  const [newDevice, setNewDevice] = useState({
    name: '',
    type: 'sensor' as const,
    serialNumber: '',
    organizationId: currentUserId || '',
    location: '',
    manufacturer: '',
    model: '',
    protocol: 'MQTT' as const,
    tags: [] as string[],
    generateCertificate: true,
    certificateType: 'auto' as string,
    certificateFormat: 'pem' as string
  });
  
  // Enhanced dialog states for add device
  const [currentAddTab, setCurrentAddTab] = useState('device');
  const [isCreating, setIsCreating] = useState(false);
  const [creationStep, setCreationStep] = useState('');
  const [certificateDetails, setCertificateDetails] = useState<any>(null);
  const [certificateBundle, setCertificateBundle] = useState<any>(null);
  const [createdDeviceId, setCreatedDeviceId] = useState('');
  const [creationSteps, setCreationSteps] = useState([
    { id: 'device', label: 'Creating device record', status: 'pending' },
    { id: 'certificate', label: 'Generating certificate', status: 'pending' },
    { id: 'vault', label: 'Storing in Vault PKI', status: 'pending' },
    { id: 'complete', label: 'Finalizing setup', status: 'pending' }
  ]);
  
  // Edit device form state
  const [editDevice, setEditDevice] = useState({
    name: '',
    type: 'sensor' as const,
    serialNumber: '',
    organizationId: '',
    location: '',
    manufacturer: '',
    model: '',
    protocol: 'MQTT' as const,
    firmwareVersion: '',
    ipAddress: '',
    macAddress: '',
    tags: [] as string[],
    status: 'online' as const
  });
  
  // Helper function to reset new device form
  const resetNewDevice = () => {
    setNewDevice({
      name: '',
      type: 'sensor',
      serialNumber: '',
      organizationId: currentUserId || '',
      location: '',
      manufacturer: '',
      model: '',
      protocol: 'MQTT',
      tags: [],
      generateCertificate: true,
      certificateType: 'auto',
      certificateFormat: 'pem'
    });
    setCurrentAddTab('device');
    setCreationSteps(steps => steps.map(step => ({ ...step, status: 'pending' })));
    setCertificateDetails(null);
    setCertificateBundle(null);
    setCreatedDeviceId('');
  };
  
  // Helper function to populate edit device form
  const populateEditDevice = (device: Device) => {
    setEditDevice({
      name: device.name,
      type: device.type,
      serialNumber: device.serialNumber,
      organizationId: device.organizationId,
      location: device.location?.name || '',
      manufacturer: device.metadata.manufacturer || '',
      model: device.metadata.model || '',
      protocol: device.metadata.protocol,
      firmwareVersion: device.firmwareVersion || '',
      ipAddress: device.metadata.ipAddress || '',
      macAddress: device.metadata.macAddress || '',
      tags: device.tags,
      status: device.status
    });
  };
  
  return {
    // Dialog visibility states
    selectedDevices,
    setSelectedDevices,
    showAddDialog,
    setShowAddDialog,
    showEditDialog,
    setShowEditDialog,
    showDetailsDialog,
    setShowDetailsDialog,
    showBulkDialog,
    setShowBulkDialog,
    showQRDialog,
    setShowQRDialog,
    showTelemetryDashboard,
    setShowTelemetryDashboard,
    showTelemetryDashboardBeta,
    setShowTelemetryDashboardBeta,
    showEdgeAITelemetry,
    setShowEdgeAITelemetry,
    showAIAssistant,
    setShowAIAssistant,
    showCertificateDialog,
    setShowCertificateDialog,
    
    // Selected device and UI states
    selectedDevice,
    setSelectedDevice,
    qrCodeData,
    setQrCodeData,
    activeDetailTab,
    setActiveDetailTab,
    
    // Telemetry states
    realTelemetryData,
    setRealTelemetryData,
    telemetryLoading,
    setTelemetryLoading,
    
    // Form states
    newDevice,
    setNewDevice,
    editDevice,
    setEditDevice,
    
    // Enhanced dialog states
    currentAddTab,
    setCurrentAddTab,
    isCreating,
    setIsCreating,
    creationStep,
    setCreationStep,
    certificateDetails,
    setCertificateDetails,
    certificateBundle,
    setCertificateBundle,
    createdDeviceId,
    setCreatedDeviceId,
    creationSteps,
    setCreationSteps,
    
    // Helper functions
    resetNewDevice,
    populateEditDevice
  };
}
