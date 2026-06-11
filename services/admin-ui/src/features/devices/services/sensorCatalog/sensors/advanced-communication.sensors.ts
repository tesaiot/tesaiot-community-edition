/**
 * Advanced Communication Sensor Templates
 *
 * @module sensorCatalog/sensors/advanced-communication
 * @description Advanced sensor definitions for WiFi connectivity and network performance
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 7 (2025-10-02)
 *
 * Contains:
 * - ESP32 WiFi Module Status (Espressif) - Connectivity and performance monitoring
 *
 * Standards: IEEE 802.11, IEEE 1451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const advancedCommunicationSensors: SensorTemplate[] = [
  {
    id: 'esp32_wifi_status',
    name: 'ESP32 WiFi Module Status',
    category: 'communication',
    subcategory: 'wifi',
    description: 'ESP32 WiFi module connectivity and performance monitoring',
    manufacturer: 'Espressif',
    tags: ['esp32', 'wifi', 'wireless', 'connectivity', 'signal_strength', 'network'],
    icon: getSensorIcon('wifi_module_status'),
    standards: ['IEEE 802.11', 'IEEE 1451'],
    schema: {
      type: 'object',
      properties: {
        connection_status: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          title: 'Connection Status',
          description: '0=Disconnected, 1=Connecting, 2=Connected, 3=Reconnecting, 4=Error'
        },
        ssid: {
          type: 'string',
          title: 'Network SSID'
        },
        rssi: {
          type: 'number',
          minimum: -100,
          maximum: -10,
          title: 'Signal Strength (dBm)'
        },
        signal_quality: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Signal Quality (%)'
        },
        ip_address: {
          type: 'string',
          title: 'IP Address'
        },
        mac_address: {
          type: 'string',
          title: 'MAC Address'
        },
        channel: {
          type: 'integer',
          minimum: 1,
          maximum: 14,
          title: 'WiFi Channel'
        },
        encryption_type: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5],
          title: 'Encryption Type',
          description: '0=Open, 1=WEP, 2=WPA_PSK, 3=WPA2_PSK, 4=WPA_WPA2_PSK, 5=WPA2_ENTERPRISE'
        },
        data_rate: {
          type: 'number',
          title: 'Data Rate (Mbps)'
        },
        bytes_sent: {
          type: 'number',
          title: 'Bytes Sent'
        },
        bytes_received: {
          type: 'number',
          title: 'Bytes Received'
        },
        reconnect_count: {
          type: 'integer',
          title: 'Reconnection Count'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['connection_status', 'rssi', 'timestamp']
    },
    uiSchema: {
      connection_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Disconnected', 'Connecting', 'Connected', 'Reconnecting', 'Error']
        }
      },
      ssid: { 'ui:widget': 'text', 'ui:help': 'Connected network name' },
      rssi: { 'ui:widget': 'updown', 'ui:help': 'Received signal strength indicator' },
      signal_quality: { 'ui:widget': 'updown', 'ui:help': 'Signal quality percentage' },
      ip_address: { 'ui:widget': 'text', 'ui:help': 'Assigned IP address' },
      mac_address: { 'ui:widget': 'text', 'ui:help': 'Hardware MAC address' },
      channel: { 'ui:widget': 'updown', 'ui:help': 'WiFi channel number' },
      encryption_type: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Open', 'WEP', 'WPA PSK', 'WPA2 PSK', 'WPA/WPA2 PSK', 'WPA2 Enterprise']
        }
      },
      data_rate: { 'ui:widget': 'updown', 'ui:help': 'Current data transmission rate' },
      bytes_sent: { 'ui:widget': 'updown', 'ui:help': 'Total bytes transmitted' },
      bytes_received: { 'ui:widget': 'updown', 'ui:help': 'Total bytes received' },
      reconnect_count: { 'ui:widget': 'updown', 'ui:help': 'Number of reconnections' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      connection_status: 2,
      ssid: 'TESA_IoT_Network',
      rssi: -45,
      signal_quality: 85,
      ip_address: '192.168.1.123',
      mac_address: '24:0A:C4:12:34:56',
      channel: 6,
      encryption_type: 3,
      data_rate: 54.0,
      bytes_sent: 1024567,
      bytes_received: 2048934,
      reconnect_count: 2,
      timestamp: new Date().toISOString()
    }
  }
];
