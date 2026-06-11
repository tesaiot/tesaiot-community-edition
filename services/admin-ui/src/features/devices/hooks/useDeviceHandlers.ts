/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { toast } from 'sonner';
import { Device } from '../types/device.types';
import { deviceService } from '../services/deviceService';
import { certificateService } from '../services/certificateService';
import { deviceOperationsService } from '../services/deviceOperationsService';
import { TOAST_MESSAGES } from '../constants/device.constants';

interface UseDeviceHandlersProps {
  devices: Device[];
  setDevices: (devices: Device[]) => void;
  filteredDevices: Device[];
  selectedDevices: string[];
  setSelectedDevices: (devices: string[]) => void;
  reloadDevices: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  setShowBulkDialog: (show: boolean) => void;
  setQrCodeData: (data: string) => void;
  setSelectedDevice: (device: Device | null) => void;
  setShowQRDialog: (show: boolean) => void;
  newDevice: any;
  resetNewDevice: () => void;
  setShowAddDialog: (show: boolean) => void;
  currentUser: any;
  setCreationSteps: (steps: any) => void;
  setIsCreating: (creating: boolean) => void;
  setCurrentAddTab: (tab: string) => void;
  setCreationStep: (step: string) => void;
  setCreatedDeviceId: (id: string) => void;
  setCertificateDetails: (details: any) => void;
  setCertificateBundle: (bundle: any) => void;
}

/**
 * Custom hook for device management handlers
 */
export function useDeviceHandlers({
  devices,
  setDevices,
  filteredDevices,
  selectedDevices,
  setSelectedDevices,
  reloadDevices,
  setLoading,
  setShowBulkDialog,
  setQrCodeData,
  setSelectedDevice,
  setShowQRDialog,
  newDevice,
  resetNewDevice,
  setShowAddDialog,
  currentUser,
  setCreationSteps,
  setIsCreating,
  setCurrentAddTab,
  setCreationStep,
  setCreatedDeviceId,
  setCertificateDetails,
  setCertificateBundle
}: UseDeviceHandlersProps) {
  
  // Original handleAddDevice (kept for backward compatibility if needed)
  const handleAddDeviceOriginal = async () => {
    setLoading(true);
    
    try {
      // Create device in backend API - PRESERVE ALL METADATA FIELDS
      const devicePayload = {
        device_id: `dev-${Date.now()}`,
        name: newDevice.name,
        type: newDevice.type,
        location: newDevice.location ? { name: newDevice.location, address: newDevice.location } : {},
        metadata: {
          manufacturer: newDevice.manufacturer || 'Unknown',
          model: newDevice.model || 'Unknown', 
          protocol: newDevice.protocol || 'MQTT',
          serialNumber: newDevice.serialNumber,
          firmwareVersion: '1.0.0',
          // Add default values to ensure fields are saved
          ipAddress: '',
          macAddress: ''
        },
        firmware_version: '1.0.0',
        tags: newDevice.tags
      };

      const createdDevice = await deviceService.createDevice(devicePayload);
      
      // If certificate generation is requested, create certificate
      if (newDevice.generateCertificate) {
        const certResult = await deviceService.generateCertificate(createdDevice.device_id);
        if (!certResult) {
          console.error('Failed to generate certificate for device');
        }
      }
      
      // Reload devices to get fresh data from API
      await reloadDevices();
      
      setShowAddDialog(false);
      toast.success(TOAST_MESSAGES.DEVICE_ADDED(newDevice.name));
      
      // Reset form
      resetNewDevice();
    } catch (error) {
      console.error('Failed to create device:', error);
      toast.error('Failed to create device. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Enhanced add device function with certificate generation
  const handleEnhancedAddDevice = async () => {
    setIsCreating(true);
    setCurrentAddTab('progress');
    
    // Update creation steps
    const updateStep = (stepId: string, status: 'active' | 'completed' | 'error') => {
      setCreationSteps((prev: any) => prev.map((step: any) => 
        step.id === stepId ? { ...step, status } : step
      ));
    };
    
    try {
      // Step 1: Create device
      updateStep('device', 'active');
      setCreationStep('Creating device record...');
      
      const devicePayload = {
        device_id: newDevice.serialNumber || `dev-${Date.now()}`,
        name: newDevice.name,
        type: newDevice.type,
        location: newDevice.location ? { name: newDevice.location, address: newDevice.location } : {},
        metadata: {
          manufacturer: newDevice.manufacturer || 'Unknown',
          model: newDevice.model || 'Unknown',
          protocol: newDevice.protocol || 'MQTT',
          serialNumber: newDevice.serialNumber,
          firmwareVersion: '1.0.0',
          certificateType: newDevice.certificateType,
          ipAddress: '',
          macAddress: ''
        },
        firmware_version: '1.0.0',
        tags: newDevice.tags
      };

      const createdDevice = await deviceService.createDevice(devicePayload);
      setCreatedDeviceId(createdDevice.device_id);
      updateStep('device', 'completed');
      
      // Step 2: Generate certificate if requested
      if (newDevice.generateCertificate) {
        updateStep('certificate', 'active');
        setCreationStep('Generating PKI certificate...');
        
        // Determine algorithm based on certificateType
        let algorithm = 'rsa-3072'; // Default to RSA 3072
        if (newDevice.certificateType === 'ecc-p256') {
          algorithm = 'ecc-p256';
        } else if (newDevice.certificateType === 'rsa-4096') {
          algorithm = 'rsa-4096';
        } else if (newDevice.certificateType === 'auto') {
          // Auto-select based on device type
          algorithm = newDevice.type === 'gateway' ? 'rsa-3072' : 'ecc-p256';
        }
        
        const certResult = await deviceService.generateCertificate(createdDevice.device_id, { algorithm });
        if (certResult) {
          setCertificateDetails(certResult);
          updateStep('certificate', 'completed');
          
          // Step 3: Store in Vault PKI (simulated)
          updateStep('vault', 'active');
          setCreationStep('Storing certificate in Vault PKI...');
          await new Promise(resolve => setTimeout(resolve, 1000));
          updateStep('vault', 'completed');
          
          // Step 4: Finalize
          updateStep('complete', 'active');
          setCreationStep('Finalizing device setup...');
          
          // Create certificate bundle for download
          const bundle = {
            deviceId: createdDevice.device_id,
            certificate: certResult.certificate,
            privateKey: certResult.private_key,
            caChain: certResult.ca_chain,
            algorithm: algorithm,
            format: newDevice.certificateFormat || 'pem'
          };
          setCertificateBundle(bundle);
          
          await new Promise(resolve => setTimeout(resolve, 500));
          updateStep('complete', 'completed');
          
          // Switch to complete tab
          setCurrentAddTab('complete');
        } else {
          throw new Error('Failed to generate certificate');
        }
      } else {
        // Skip certificate generation
        updateStep('certificate', 'completed');
        updateStep('vault', 'completed');
        updateStep('complete', 'completed');
        setCurrentAddTab('complete');
      }
      
      // Reload devices to show the new device
      await reloadDevices();
      
      setIsCreating(false);
      toast.success(TOAST_MESSAGES.DEVICE_ADDED(newDevice.name));
      
    } catch (error) {
      console.error('Failed to create device:', error);
      toast.error('Failed to create device. Please try again.');
      
      // Mark failed step
      const activeStep = (await Promise.resolve(setCreationSteps)).find((s: any) => s.status === 'active');
      if (activeStep) {
        updateStep(activeStep.id, 'error');
      }
      
      setIsCreating(false);
    }
  };

  const handleDeleteDevice = async (device: Device) => {
    if (!confirm(`Are you sure you want to delete ${device.name}?`)) {
      return;
    }
    
    setLoading(true);
    
    try {
      // Use device_id instead of id for API calls
      const deviceId = device.device_id || device.id;
      await deviceService.deleteDevice(deviceId);
      await reloadDevices();
      toast.success(`Device Deleted: ${device.name} has been removed`);
    } catch (error) {
      console.error('Failed to delete device:', error);
      toast.error('Failed to delete device. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkAction = async (action: string) => {
    setLoading(true);
    
    switch (action) {
      case 'delete':
        if (!confirm(`Are you sure you want to delete ${selectedDevices.length} devices?`)) {
          setLoading(false);
          return;
        }
        
        try {
          // Delete devices one by one (could be optimized with batch API)
          for (const deviceId of selectedDevices) {
            await deviceService.deleteDevice(deviceId);
          }
          
          await reloadDevices();
          toast.error(`Devices Deleted: ${selectedDevices.length} devices removed`);
        } catch (error) {
          console.error('Failed to delete devices:', error);
          toast.error('Failed to delete some devices');
        }
        break;
      
      case 'restart':
        toast.success(`Restart Command Sent: Restarting ${selectedDevices.length} devices`);
        break;
      
      case 'update':
        setShowBulkDialog(true);
        break;
    }
    
    setSelectedDevices([]);
    setLoading(false);
  };

  // Download certificate files from Vault PKI
  const downloadCertificateFile = async (device: Device, fileType: 'ca-chain' | 'device-cert' | 'device-key' | 'bundle') => {
    await certificateService.downloadCertificateFile(device, fileType);
  };

  const generateQRCode = async (device: Device) => {
    try {
      const qrData = await deviceOperationsService.generateQRCode(device);
      setQrCodeData(qrData);
      setSelectedDevice(device);
      setShowQRDialog(true);
    } catch (error) {
      console.error('Failed to generate QR code:', error);
    }
  };

  const exportDevices = () => {
    deviceOperationsService.exportDevices(filteredDevices);
  };

  return {
    handleAddDeviceOriginal,
    handleEnhancedAddDevice,
    handleDeleteDevice,
    handleBulkAction,
    downloadCertificateFile,
    generateQRCode,
    exportDevices
  };
}