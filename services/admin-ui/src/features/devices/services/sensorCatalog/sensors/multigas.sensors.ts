/**
 * Multi-Gas Sensor Templates
 *
 * @module sensorCatalog/sensors/multigas
 * @description Sensor definitions for multi-gas detection and smoke monitoring
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 6 (2025-10-02)
 *
 * Contains:
 * - MQ135 Multi-Gas - NH3, NOx, alcohol, benzene, smoke, CO2
 * - MQ2 Smoke & Gas - Smoke, LPG, methane, hydrogen detection
 *
 * Standards: IEEE 1451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const multiGasSensors: SensorTemplate[] = [
  {
    id: 'mq135_multi_gas',
    name: 'MQ135 Multi-Gas Sensor',
    category: 'environmental',
    subcategory: 'gas',
    description: 'MQ135 gas sensor for NH3, NOx, alcohol, benzene, smoke, CO2',
    tags: ['mq135', 'multi_gas', 'nh3', 'nox', 'alcohol', 'benzene', 'smoke', 'co2'],
    icon: getSensorIcon('gas_sensor'),
    standards: ['IEEE 1451'],
    schema: {
      type: 'object',
      properties: {
        analog_value: {
          type: 'number',
          minimum: 0,
          maximum: 1023,
          title: 'Analog Reading (0-1023)'
        },
        voltage: {
          type: 'number',
          minimum: 0,
          maximum: 5,
          title: 'Voltage (V)'
        },
        resistance: {
          type: 'number',
          title: 'Sensor Resistance (Ohm)'
        },
        gas_concentration: {
          type: 'number',
          title: 'Gas Concentration (ppm)'
        },
        gas_type: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5],
          title: 'Detected Gas Type',
          description: '0=CO2, 1=NH3, 2=NOx, 3=Alcohol, 4=Benzene, 5=Smoke'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['analog_value', 'voltage', 'timestamp']
    },
    uiSchema: {
      analog_value: { 'ui:widget': 'updown', 'ui:help': 'Raw ADC value' },
      voltage: { 'ui:widget': 'updown', 'ui:help': 'Analog voltage output' },
      resistance: { 'ui:widget': 'updown', 'ui:help': 'Calculated sensor resistance' },
      gas_concentration: { 'ui:widget': 'updown', 'ui:help': 'Estimated gas concentration' },
      gas_type: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['CO2', 'NH3 (Ammonia)', 'NOx (Nitrogen Oxides)', 'Alcohol', 'Benzene', 'Smoke']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      analog_value: 342,
      voltage: 1.67,
      resistance: 15400,
      gas_concentration: 89,
      gas_type: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'mq2_smoke_gas',
    name: 'MQ2 Smoke & Gas Sensor',
    category: 'environmental',
    subcategory: 'gas',
    description: 'MQ2 gas sensor for smoke, LPG, methane, hydrogen detection',
    tags: ['mq2', 'smoke', 'lpg', 'methane', 'hydrogen', 'combustible'],
    icon: getSensorIcon('flame_sensor'),
    standards: ['IEEE 1451'],
    schema: {
      type: 'object',
      properties: {
        analog_value: {
          type: 'number',
          minimum: 0,
          maximum: 1023,
          title: 'Analog Reading (0-1023)'
        },
        digital_trigger: {
          type: 'boolean',
          title: 'Digital Trigger (Threshold Exceeded)'
        },
        lpg_ppm: {
          type: 'number',
          title: 'LPG Concentration (ppm)'
        },
        methane_ppm: {
          type: 'number',
          title: 'Methane Concentration (ppm)'
        },
        hydrogen_ppm: {
          type: 'number',
          title: 'Hydrogen Concentration (ppm)'
        },
        smoke_level: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Smoke Level',
          description: '0=None, 1=Low, 2=Medium, 3=High'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['analog_value', 'digital_trigger', 'timestamp']
    },
    uiSchema: {
      analog_value: { 'ui:widget': 'updown', 'ui:help': 'Raw ADC value' },
      digital_trigger: { 'ui:widget': 'checkbox', 'ui:help': 'Digital threshold trigger' },
      lpg_ppm: { 'ui:widget': 'updown', 'ui:help': 'LPG gas concentration' },
      methane_ppm: { 'ui:widget': 'updown', 'ui:help': 'Methane gas concentration' },
      hydrogen_ppm: { 'ui:widget': 'updown', 'ui:help': 'Hydrogen gas concentration' },
      smoke_level: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['No Smoke', 'Low Smoke', 'Medium Smoke', 'High Smoke']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      analog_value: 256,
      digital_trigger: false,
      lpg_ppm: 45,
      methane_ppm: 32,
      hydrogen_ppm: 28,
      smoke_level: 1,
      timestamp: new Date().toISOString()
    }
  }
];
