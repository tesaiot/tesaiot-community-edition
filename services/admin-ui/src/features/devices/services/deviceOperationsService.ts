/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { toast } from 'sonner';
import QRCode from 'qrcode';
import { format } from 'date-fns';
import { Device } from '../types/device.types';

/**
 * Service for device utility operations
 */
export class DeviceOperationsService {
  /**
   * Generate QR code for device provisioning
   * For Trust M devices: Uses API endpoint to generate Trust M UID QR code
   * For other devices: Generates QR code from provisioning data
   */
  static async generateQRCode(device: Device): Promise<string> {
    try {
      // Check if this is a Trust M device
      const trustmUid = (device as any).trustm_uid;
      const deviceId = (device as any).device_id || device.id;

      if (trustmUid) {
        // For Trust M devices, fetch QR code from API
        const { tesaApi } = await import('@/services/api/tesaApi');

        console.log('[QR Code] Fetching QR code for Trust M device:', deviceId);
        const response = await tesaApi.get(`/api/v1/devices/${deviceId}/qrcode`, {
          params: { format: 'png', size: 10 },
        });

        console.log('[QR Code] API response:', {
          hasResponse: !!response,
          hasData: !!response?.data,
          hasImageBase64: !!response?.data?.image_base64,
          dataKeys: response?.data ? Object.keys(response.data) : [],
          responseKeys: response ? Object.keys(response) : []
        });

        // Validate response structure
        // Note: API returns data directly, not wrapped in { data: {...} }
        if (!response) {
          throw new Error('No response from QR code API');
        }

        // Check if response has data wrapper (Axios wraps in .data)
        const responseData = response.data || response;

        if (!responseData.image_base64) {
          const availableFields = Object.keys(responseData).join(', ');
          throw new Error(`Response missing image_base64 field. Available fields: ${availableFields}`);
        }

        return responseData.image_base64;
      }

      // For non-Trust M devices, generate QR code from provisioning data
      console.log('[QR Code] Generating QR code for non-Trust M device:', device.id);
      // Build endpoints from the operator's actual host (domain-agnostic
      // self-host) instead of a hardcoded tesaiot.dev/.com switch, so the QR
      // encodes the install's real API/MQTT endpoints.
      const host = window.location.hostname;
      const provisioningData = {
        deviceId: device.id,
        name: device.name,
        apiUrl: `https://${host}/v1`,
        mqttUrl: `mqtts://${host}:8883`,
        certificate: device.certificate?.serial
      };

      const qrData = await QRCode.toDataURL(JSON.stringify(provisioningData));
      return qrData;
    } catch (error: any) {
      console.error('QR code generation error:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });

      const errorMessage = error.response?.data?.message
        || error.message
        || 'Failed to generate QR code';

      toast.error(errorMessage);
      throw error;
    }
  }

  /**
   * Export devices to CSV
   */
  static exportDevices(devices: Device[]): void {
    try {
      const csv = [
        ['Name', 'Type', 'Status', 'Serial Number', 'Organization', 'Location', 'Last Seen'],
        ...devices.map(device => [
          device.name,
          device.type,
          device.status,
          device.serialNumber,
          device.organizationName,
          device.location?.name || '',
          device.lastSeen ? format(device.lastSeen, 'yyyy-MM-dd HH:mm') : ''
        ])
      ].map(row => row.join(',')).join('\n');
      
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `devices-export-${format(new Date(), 'yyyy-MM-dd')}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast.success(`Export Complete: Exported ${devices.length} devices`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Failed to export devices');
    }
  }

  /**
   * Import devices from CSV
   */
  static async importDevices(file: File): Promise<Device[]> {
    try {
      const text = await file.text();
      const lines = text.split('\n');
      const headers = lines[0].split(',');
      
      // Validate headers
      const requiredHeaders = ['Name', 'Type', 'Serial Number'];
      const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
      if (missingHeaders.length > 0) {
        throw new Error(`Missing required headers: ${missingHeaders.join(', ')}`);
      }
      
      // Parse devices (skip header row)
      const devices: Partial<Device>[] = [];
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        if (values.length === headers.length) {
          devices.push({
            name: values[headers.indexOf('Name')],
            type: values[headers.indexOf('Type')] as Device['type'],
            serialNumber: values[headers.indexOf('Serial Number')]
          });
        }
      }
      
      toast.success(`Import Complete: Parsed ${devices.length} devices`);
      return devices as Device[];
    } catch (error) {
      console.error('Import error:', error);
      toast.error('Failed to import devices');
      throw error;
    }
  }

  /**
   * Generate device provisioning script
   */
  static generateProvisioningScript(device: Device, certificateBundle?: any): string {
    const script = `#!/bin/bash
# TESA IoT Device Provisioning Script
# Device: ${device.name} (${device.device_id || device.id})
# Generated: ${new Date().toISOString()}

# Configuration
DEVICE_ID="${device.device_id || device.id}"
DEVICE_NAME="${device.name}"
MQTT_URL="mqtts://mqtt.tesa.io:8883"
API_URL="https://api.tesa.io/v1"

# Install certificate files
${certificateBundle ? `
echo "Installing certificate files..."
echo "${certificateBundle.certificate}" > /etc/tesa/device.crt
echo "${certificateBundle.privateKey}" > /etc/tesa/device.key
echo "${certificateBundle.caChain}" > /etc/tesa/ca.crt
chmod 600 /etc/tesa/device.key
` : '# No certificate bundle provided'}

# Configure MQTT client
echo "Configuring MQTT client..."
cat > /etc/tesa/mqtt.conf <<EOF
device_id=$DEVICE_ID
device_name=$DEVICE_NAME
mqtt_url=$MQTT_URL
api_url=$API_URL
EOF

echo "Provisioning complete!"
`;
    return script;
  }
}

export const deviceOperationsService = DeviceOperationsService;