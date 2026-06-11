/**
 * Communication & Connectivity Sensor Templates
 *
 * @module sensorCatalog/sensors/communication
 * @description Sensor definitions for network connectivity and communication diagnostics
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 5 (2025-10-02)
 *
 * Contains:
 * - WiFi Module Status (Espressif) - Connectivity diagnostics (ESP32, ESP8266)
 *
 * Standards: IEEE 802.11, TCP/IP
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const communicationSensors: SensorTemplate[] = [
  {
    id: 'wifi_module_status',
    name: 'WiFi Module Status',
    category: 'communication',
    subcategory: 'network',
    description: 'WiFi connectivity and network diagnostics (ESP32, ESP8266)',
    manufacturer: 'Espressif',
    tags: ['wifi', 'network', 'connectivity', 'esp32', 'esp8266', 'signal', 'diagnostics'],
    icon: getSensorIcon('wifi_module_status'),
    standards: ['IEEE 802.11', 'TCP/IP'],
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
        bssid: {
          type: 'string',
          title: 'Access Point BSSID'
        },
        rssi: {
          type: 'integer',
          minimum: -120,
          maximum: -30,
          title: 'Signal Strength (RSSI)'
        },
        signal_quality: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Signal Quality (%)'
        },
        channel: {
          type: 'integer',
          minimum: 1,
          maximum: 14,
          title: 'WiFi Channel'
        },
        frequency: {
          type: 'number',
          title: 'Frequency (MHz)'
        },
        ip_address: {
          type: 'string',
          title: 'IP Address'
        },
        subnet_mask: {
          type: 'string',
          title: 'Subnet Mask'
        },
        gateway: {
          type: 'string',
          title: 'Gateway Address'
        },
        dns_primary: {
          type: 'string',
          title: 'Primary DNS'
        },
        mac_address: {
          type: 'string',
          title: 'MAC Address'
        },
        tx_power: {
          type: 'number',
          minimum: 0,
          maximum: 20,
          title: 'Transmission Power (dBm)'
        },
        data_rate: {
          type: 'number',
          title: 'Data Rate (Mbps)'
        },
        packet_loss: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Packet Loss (%)'
        },
        latency: {
          type: 'number',
          minimum: 0,
          title: 'Network Latency (ms)'
        },
        uptime: {
          type: 'integer',
          minimum: 0,
          title: 'Connection Uptime (seconds)'
        },
        reconnect_count: {
          type: 'integer',
          minimum: 0,
          title: 'Reconnection Count'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['connection_status', 'ssid', 'rssi', 'ip_address', 'timestamp']
    },
    uiSchema: {
      connection_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Disconnected', 'Connecting', 'Connected', 'Reconnecting', 'Error']
        }
      },
      ssid: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Network name' },
      bssid: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Access point identifier' },
      rssi: { 'ui:widget': 'updown', 'ui:help': 'Signal strength in dBm' },
      signal_quality: { 'ui:widget': 'range', 'ui:help': 'Signal quality percentage' },
      channel: { 'ui:widget': 'updown', 'ui:help': 'WiFi channel number' },
      frequency: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Operating frequency' },
      ip_address: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Assigned IP address' },
      subnet_mask: { 'ui:widget': 'text', 'ui:readonly': true },
      gateway: { 'ui:widget': 'text', 'ui:readonly': true },
      dns_primary: { 'ui:widget': 'text', 'ui:readonly': true },
      mac_address: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Hardware address' },
      tx_power: { 'ui:widget': 'updown', 'ui:help': 'Transmission power level' },
      data_rate: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Current data rate' },
      packet_loss: { 'ui:widget': 'updown', 'ui:help': 'Percentage of lost packets' },
      latency: { 'ui:widget': 'updown', 'ui:help': 'Network response time' },
      uptime: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Connection duration' },
      reconnect_count: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Number of reconnections' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      connection_status: 2,
      ssid: 'IoT_Network',
      bssid: '00:1B:44:11:3A:B7',
      rssi: -65,
      signal_quality: 75,
      channel: 6,
      frequency: 2437,
      ip_address: '192.168.1.100',
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns_primary: '8.8.8.8',
      mac_address: '30:AE:A4:07:0D:64',
      tx_power: 20,
      data_rate: 150,
      packet_loss: 0.1,
      latency: 5,
      uptime: 3600,
      reconnect_count: 2,
      timestamp: new Date().toISOString()
    },
    units: { rssi: 'dBm', frequency: 'MHz', tx_power: 'dBm', data_rate: 'Mbps', latency: 'ms', uptime: 's' },
    ranges: {
      rssi: { min: -120, max: -30 },
      signal_quality: { min: 0, max: 100 },
      channel: { min: 1, max: 14 },
      packet_loss: { min: 0, max: 100 }
    },
    accuracy: { rssi: 1, latency: 1 }
  }
];
