/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect } from 'react';
import { Device, DeviceGroup } from '../types/device.types';
import { deviceService } from '../services/deviceService';
import { organizationService } from '../../organizations/services/organizationService';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

/**
 * Custom hook for managing device data
 */
export function useDeviceData() {
  const { user: currentUser } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceGroups, setDeviceGroups] = useState<DeviceGroup[]>([]);
  const [organizationMap, setOrganizationMap] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(false);

  // Load organizations for mapping
  const loadOrganizations = async () => {
    try {
      const orgs = await organizationService.getOrganizations();
      
      // Create a map of organization IDs to names
      const map = new Map<string, string>();
      orgs.forEach((org: any) => {
        // Map all possible ID formats
        if (org.id) map.set(org.id, org.name);
        if (org._id) map.set(org._id, org.name);
        if (org.organization_id) map.set(org.organization_id, org.name);
        
        // Special mapping for BDH
        if (org.name === 'BDH Corporation') {
          map.set('bdh-corp', 'BDH Corporation');
        }
      });
      
      // Add hardcoded mappings for known organizations
      map.set('bdh-corp', 'BDH Corporation');
      map.set('org-001', 'TESA Demo Organization');
      map.set('org-002', 'Acme IoT Solutions');
      map.set('org-003', 'Smart Home Tech');
      
      setOrganizationMap(map);
    } catch (error) {
      console.error('Failed to load organizations:', error);
      // Set default mappings even if API fails
      const defaultMap = new Map<string, string>([
        ['bdh-corp', 'BDH Corporation'],
        ['org-001', 'TESA Demo Organization'],
        ['org-002', 'Acme IoT Solutions'],
        ['org-003', 'Smart Home Tech']
      ]);
      setOrganizationMap(defaultMap);
    }
  };

  const loadDevicesFromAPI = async () => {
    try {
      setLoading(true);
      
      // Filter devices by organization for non-super admin users
      let organizationId: string | undefined;
      if (currentUser && currentUser.role !== 'super_admin' && currentUser.organization_id) {
        organizationId = currentUser.organization_id;
      }
      
      const data = await deviceService.fetchDevices(organizationId);
      
      // Convert API data to our Device interface - PRESERVE ALL FIELDS
      const deviceData = data.map((device: any) => {
        
        
        
        const mapped = {
          id: device._id || device.id,
          device_id: device.device_id || device.id,
          name: device.name || '', // Don't fallback to device_id
          type: device.type || 'sensor',
          status: device.status || 'offline',
          organizationId: device.organization_id || 'org-001',
          organizationName: organizationMap.get(device.organization_id) || device.organization || device.organizationName || 'Unknown Organization',
          serialNumber: device.device_id || device.serialNumber,
          firmwareVersion: device.firmware_version || device.metadata?.firmwareVersion || '1.0.0',
          lastSeen: device.last_seen ? new Date(device.last_seen) : null,
          registeredAt: new Date(device.created_at),
          location: device.location ? { name: device.location } : device.location_details ? { name: device.location_details.name || device.location_details.address } : undefined,
          // PRESERVE AUTHENTICATION MODE FROM API RESPONSE
          auth_mode: device.auth_mode || 'mtls', // Default to mtls for backward compatibility
          // PRESERVE ENCRYPTION FIELDS FROM API RESPONSE
          key_encryption_enabled: device.key_encryption_enabled || false,
          device_public_key: device.device_public_key || null,
          public_key: device.public_key || null,
          // PRESERVE CERTIFICATE FIELDS
          certificate_algorithm: device.certificate_algorithm || device.metadata?.certificate_algorithm || '',
          certificate_info: device.certificate_info || null,
          certificate_serial: device.certificate_serial || null,
          certificate_issued_at: device.certificate_issued_at || null,
          certificate_expires_at: device.certificate_expires_at || null,
          certificate_status: device.certificate_status || null,
          // CRITICAL: PRESERVE CSR FIELDS FOR DETECTION
          certificate_generation_method: device.certificate_generation_method,
          generation_method: device.generation_method,
          csr_provided: device.csr_provided === true || device.csr_provided === 'true',
          // CRITICAL: PRESERVE TRUST M UID FOR TRUST M DEVICE DETECTION
          trustm_uid: device.trustm_uid || (device as any).trustmUid,
          trustmUid: device.trustm_uid || (device as any).trustmUid, // camelCase variant
          metadata: {
            manufacturer: device.metadata?.manufacturer || device.manufacturer || 'Unknown',
            model: device.metadata?.model || device.model || 'Unknown', 
            protocol: device.metadata?.protocol || device.protocol || 'MQTT',
            ipAddress: device.metadata?.ipAddress || device.ip_address || undefined,
            macAddress: device.metadata?.macAddress || device.mac_address || undefined,
            devicePicture: device.metadata?.devicePicture || null,
            industry: device.metadata?.industry || '',
            industrySpecificData: device.metadata?.industrySpecificData || null,
            factory_uid: device.metadata?.factory_uid || (device as any).factory_uid || undefined,
            // PRESERVE CSR field in metadata too
            certificate_generation_method: device.metadata?.certificate_generation_method || null
          },
          telemetry: {
            messagesPerMinute: Math.floor(Math.random() * 100),
            dataUsage: Math.floor(Math.random() * 100),
            uptime: Math.floor(Math.random() * 1000000),
            signalStrength: device.signal_strength,
            batteryLevel: device.battery_level
          },
          certificate: (device.certificate_status === 'valid' || device.certificate_status === 'Valid' || device.certificate_info?.status === 'valid') ? (() => {
            
            // Check all possible locations for algorithm
            const algorithm = device.certificate_info?.key_algorithm ||
                            device.certificate_algorithm || 
                            device.metadata?.certificate_algorithm || 
                            device.metadata?.certificateType ||
                            device.certificate_options?.algorithm ||
                            null;
            
            // Format algorithm properly if needed
            let formattedAlgorithm = 'Unknown';
            if (algorithm) {
              // If it's already formatted (like "RSA 3072" or "ECC P-256"), use it directly
              if (algorithm.includes(' ') && (algorithm.startsWith('RSA') || algorithm.startsWith('ECC'))) {
                formattedAlgorithm = algorithm;
              } else {
                // Otherwise format it
                const algoLower = algorithm.toLowerCase();
                if (algoLower === 'ecc-p256' || algoLower === 'ecc p-256') {
                  formattedAlgorithm = 'ECC P-256';
                } else if (algoLower === 'ecc-p384' || algoLower === 'ecc p-384') {
                  formattedAlgorithm = 'ECC P-384';
                } else if (algoLower === 'rsa-2048' || algoLower === 'rsa 2048') {
                  formattedAlgorithm = 'RSA 2048';
                } else if (algoLower === 'rsa-3072' || algoLower === 'rsa 3072') {
                  formattedAlgorithm = 'RSA 3072';
                } else if (algoLower === 'rsa-4096' || algoLower === 'rsa 4096') {
                  formattedAlgorithm = 'RSA 4096';
                } else {
                  // Try to format unknown algorithms
                  formattedAlgorithm = algorithm.toUpperCase().replace(/-/g, ' ');
                }
              }
            }
            
            // Extract dates from multiple possible locations
            const issuedAt = device.certificate_issued_at || device.certificate_info?.issued_at;
            const expiresAt = device.certificate_expires_at || device.certificate_info?.expires_at;
            
            return {
              serial: device.certificate_serial || device.certificate_info?.serial_number || 'N/A',
              expiresAt: expiresAt ? new Date(expiresAt) : undefined,
              status: device.certificate_info?.status || device.certificate_status || 'active',
              algorithm: formattedAlgorithm,
              // Add validFrom and validTo for UI compatibility
              validFrom: issuedAt ? new Date(issuedAt) : undefined,
              validTo: expiresAt ? new Date(expiresAt) : undefined,
              // Also include the raw certificate_info for detailed views
              issuer: device.certificate_info?.issuer || 'CN=TESA IoT Intermediate CA',
              subject: device.certificate_info?.subject || `CN=${device.device_id}.sensor.tesa.iot,OU=IoT Sensors,O=TESA IoT Platform,C=TH`
            };
          })() : undefined,
          tags: device.tags || [],
          // Include telemetry and actuator schemas for edit functionality
          telemetrySchema: device.telemetrySchema ? {
            schema: device.telemetrySchema.schema || {},
            uiSchema: device.telemetrySchema.uiSchema || {},
            formData: device.telemetrySchema.formData || {},
            lastUpdated: device.telemetrySchema.lastUpdated
          } : null,
          actuatorSchema: device.actuatorSchema ? {
            schema: device.actuatorSchema.schema || {},
            uiSchema: device.actuatorSchema.uiSchema || {},
            formData: device.actuatorSchema.formData || {},
            lastUpdated: device.actuatorSchema.lastUpdated
          } : null
        };
        
        return mapped;
      });
      
      setDevices(deviceData);

      // Device grouping is part of the OTA feature, which is out of scope for the
      // Community Edition. Keep the state for API compatibility but leave it empty.
      setDeviceGroups([]);
    } catch (error) {
      console.error('Failed to load devices from API:', error);
      toast.error('Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  // Load organizations first
  useEffect(() => {
    loadOrganizations();
  }, []);

  // Load devices after organizations are loaded
  useEffect(() => {
    if (organizationMap.size > 0) {
      loadDevicesFromAPI();
    }
  }, [organizationMap, currentUser]);

  return {
    devices,
    setDevices,
    deviceGroups,
    setDeviceGroups,
    organizationMap,
    loading,
    reloadDevices: loadDevicesFromAPI
  };
}
