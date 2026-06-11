/**
 * Advanced Energy Sensors Catalog
 *
 * @module sensorCatalog/sensors/advanced-energy
 * @description Advanced energy monitoring sensor configurations
 * @category Energy Sensors
 *
 * Contains sensor templates for:
 * - PZEM-004T energy meters
 * - Advanced power monitoring devices
 *
 * @standards
 * - IEEE 1451 (Smart transducer interface)
 * - IEC 62053 (Electricity metering equipment)
 *
 * @created 2025-10-02
 * @phase Phase 1.4 Week 1 Day 2
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const advancedEnergySensors: SensorTemplate[] = [
  {
    id: 'pzem004t_energy',
    name: 'PZEM-004T Energy Monitor',
    category: 'electrical',
    subcategory: 'energy',
    description: 'PZEM-004T AC single phase energy meter with voltage, current, power, energy monitoring',
    tags: ['pzem004t', 'energy', 'power', 'voltage', 'current', 'ac', 'meter'],
    icon: getSensorIcon('energy_monitor'),
    standards: ['IEEE 1451', 'IEC 62053'],
    schema: {
      type: 'object',
      properties: {
        voltage: {
          type: 'number',
          minimum: 80,
          maximum: 260,
          title: 'Voltage (V)'
        },
        current: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Current (A)'
        },
        power: {
          type: 'number',
          minimum: 0,
          maximum: 22000,
          title: 'Active Power (W)'
        },
        energy: {
          type: 'number',
          minimum: 0,
          title: 'Energy Consumption (kWh)'
        },
        frequency: {
          type: 'number',
          minimum: 45,
          maximum: 65,
          title: 'Frequency (Hz)'
        },
        power_factor: {
          type: 'number',
          minimum: 0,
          maximum: 1,
          title: 'Power Factor'
        },
        alarm_high_power: {
          type: 'number',
          title: 'High Power Alarm Threshold (W)'
        },
        alarm_low_voltage: {
          type: 'number',
          title: 'Low Voltage Alarm Threshold (V)'
        },
        energy_reset: {
          type: 'boolean',
          title: 'Energy Counter Reset'
        },
        modbus_address: {
          type: 'integer',
          minimum: 1,
          maximum: 247,
          title: 'Modbus Slave Address'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['voltage', 'current', 'power', 'energy', 'timestamp']
    },
    uiSchema: {
      voltage: { 'ui:widget': 'updown', 'ui:help': 'AC voltage measurement' },
      current: { 'ui:widget': 'updown', 'ui:help': 'AC current measurement' },
      power: { 'ui:widget': 'updown', 'ui:help': 'Active power consumption' },
      energy: { 'ui:widget': 'updown', 'ui:help': 'Cumulative energy consumption' },
      frequency: { 'ui:widget': 'updown', 'ui:help': 'AC line frequency' },
      power_factor: { 'ui:widget': 'updown', 'ui:help': 'Power factor (cos φ)' },
      alarm_high_power: { 'ui:widget': 'updown', 'ui:help': 'High power alarm setting' },
      alarm_low_voltage: { 'ui:widget': 'updown', 'ui:help': 'Low voltage alarm setting' },
      energy_reset: { 'ui:widget': 'checkbox', 'ui:help': 'Reset energy counter' },
      modbus_address: { 'ui:widget': 'updown', 'ui:help': 'Modbus device address' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      voltage: 230.5,
      current: 2.45,
      power: 564.2,
      energy: 123.45,
      frequency: 50.0,
      power_factor: 0.92,
      alarm_high_power: 2000,
      alarm_low_voltage: 200,
      energy_reset: false,
      modbus_address: 1,
      timestamp: new Date().toISOString()
    }
  }
];
