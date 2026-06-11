/**
 * Energy & Smart Grid Sensor Templates
 *
 * @module sensorCatalog/sensors/energy
 * @description Sensor definitions for energy monitoring and smart grid applications
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 4 (2025-10-02)
 *
 * Contains:
 * - Energy Monitor (YHDC/PeaceFair) - Comprehensive monitoring (SCT013, PZEM-004T)
 *
 * Standards: IEC 62053-21, IEEE 1547
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const energySensors: SensorTemplate[] = [
  {
    id: 'energy_monitor',
    name: 'Energy Monitor',
    category: 'electrical',
    subcategory: 'smart_grid',
    description: 'Comprehensive energy monitoring for smart grid applications (SCT013, PZEM-004T)',
    manufacturer: 'YHDC / PeaceFair',
    tags: ['energy', 'power', 'smart-grid', 'sct013', 'pzem-004t', 'monitoring', 'consumption'],
    icon: getSensorIcon('energy_monitor'),
    standards: ['IEC 62053-21', 'IEEE 1547'],
    schema: {
      type: 'object',
      properties: {
        voltage: {
          type: 'number',
          minimum: 0,
          maximum: 300,
          title: 'RMS Voltage'
        },
        voltage_unit: {
          type: 'string',
          enum: ['V'],
          default: 'V',
          title: 'Voltage Unit'
        },
        current: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'RMS Current'
        },
        current_unit: {
          type: 'string',
          enum: ['A'],
          default: 'A',
          title: 'Current Unit'
        },
        active_power: {
          type: 'number',
          minimum: 0,
          title: 'Active Power'
        },
        active_power_unit: {
          type: 'string',
          enum: ['W'],
          default: 'W',
          title: 'Active Power Unit'
        },
        reactive_power: {
          type: 'number',
          title: 'Reactive Power'
        },
        reactive_power_unit: {
          type: 'string',
          enum: ['var'],
          default: 'var',
          title: 'Reactive Power Unit'
        },
        apparent_power: {
          type: 'number',
          title: 'Apparent Power'
        },
        apparent_power_unit: {
          type: 'string',
          enum: ['VA'],
          default: 'VA',
          title: 'Apparent Power Unit'
        },
        power_factor: {
          type: 'number',
          minimum: -1,
          maximum: 1,
          title: 'Power Factor'
        },
        energy: {
          type: 'number',
          minimum: 0,
          title: 'Total Energy Consumed'
        },
        energy_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 1,
          title: 'Energy Unit',
          description: '0=Wh, 1=kWh, 2=MWh'
        },
        frequency: {
          type: 'number',
          minimum: 45,
          maximum: 65,
          title: 'Line Frequency'
        },
        frequency_unit: {
          type: 'string',
          enum: ['Hz'],
          default: 'Hz',
          title: 'Frequency Unit'
        },
        cost: {
          type: 'number',
          minimum: 0,
          title: 'Energy Cost'
        },
        cost_currency: {
          type: 'string',
          enum: ['USD', 'EUR', 'THB', 'CNY'],
          default: 'USD',
          title: 'Cost Currency'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['voltage', 'current', 'active_power', 'energy', 'timestamp']
    },
    uiSchema: {
      voltage: { 'ui:widget': 'updown', 'ui:help': 'RMS voltage measurement' },
      voltage_unit: { 'ui:widget': 'hidden' },
      current: { 'ui:widget': 'updown', 'ui:help': 'RMS current measurement' },
      current_unit: { 'ui:widget': 'hidden' },
      active_power: { 'ui:widget': 'updown', 'ui:help': 'Real power consumption' },
      active_power_unit: { 'ui:widget': 'hidden' },
      reactive_power: { 'ui:widget': 'updown', 'ui:help': 'Reactive power component' },
      reactive_power_unit: { 'ui:widget': 'hidden' },
      apparent_power: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Total power (calculated)' },
      apparent_power_unit: { 'ui:widget': 'hidden' },
      power_factor: { 'ui:widget': 'updown', 'ui:help': 'Efficiency indicator' },
      energy: { 'ui:widget': 'updown', 'ui:help': 'Cumulative energy consumption' },
      energy_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Wh (Watt-hours)', 'kWh (Kilowatt-hours)', 'MWh (Megawatt-hours)']
        }
      },
      frequency: { 'ui:widget': 'updown', 'ui:help': 'AC line frequency' },
      frequency_unit: { 'ui:widget': 'hidden' },
      cost: { 'ui:widget': 'updown', 'ui:help': 'Calculated energy cost' },
      cost_currency: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['US Dollar', 'Euro', 'Thai Baht', 'Chinese Yuan']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      voltage: 230.5,
      current: 8.75,
      active_power: 1912.5,
      reactive_power: 425.3,
      apparent_power: 1958.8,
      power_factor: 0.95,
      energy: 156.82,
      energy_unit: 1,
      frequency: 50.0,
      cost: 18.82,
      cost_currency: 'USD',
      timestamp: new Date().toISOString()
    },
    units: { voltage: 'V', current: 'A', active_power: 'W', energy: 'kWh', frequency: 'Hz' },
    ranges: {
      voltage: { min: 0, max: 300 },
      current: { min: 0, max: 100 },
      power_factor: { min: -1, max: 1 }
    },
    accuracy: { voltage: 0.1, current: 0.01, active_power: 1 }
  }
];
