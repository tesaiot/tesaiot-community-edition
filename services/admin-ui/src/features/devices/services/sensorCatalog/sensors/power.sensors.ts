/**
 * Power & Electrical Sensors Catalog
 *
 * @module sensorCatalog/sensors/power
 * @description Electrical power and current measurement sensor configurations
 * @category Electrical Sensors
 *
 * Contains sensor templates for:
 * - Current sensors (ACS712, SCT013)
 * - Power monitoring sensors
 *
 * @standards
 * - IEC 61869 (Instrument transformers)
 * - IEEE C57.13 (Standard requirements for instrument transformers)
 *
 * @created 2025-10-02
 * @phase Phase 1.4 Week 1 Day 1
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const powerSensors: SensorTemplate[] = [
  {
    id: 'current_sensor',
    name: 'Current Sensor',
    category: 'electrical',
    subcategory: 'power',
    description: 'Electrical current measurement',
    tags: ['current', 'power', 'electrical', 'acs712', 'sct013'],
    icon: getSensorIcon('current_sensor'),
    standards: ['IEC 61869', 'IEEE C57.13'],
    schema: {
      type: 'object',
      properties: {
        current: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 0, maximum: 30 },
            unit: { type: 'string', enum: ['A', 'mA'], default: 'A' },
            precision: { type: 'number', default: 0.01 }
          },
          required: ['value', 'unit']
        },
        power: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['W', 'kW'], default: 'W' }
          }
        },
        voltage: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['V'], default: 'V' }
          }
        },
        powerFactor: { type: 'number', minimum: 0, maximum: 1 },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['current', 'timestamp']
    },
    uiSchema: {
      current: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Current'
        }
      },
      power: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'text',
          'ui:size': 'large'
        }
      },
      voltage: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      powerFactor: { 'ui:widget': 'text' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      current: { value: 5.25, unit: 'A', precision: 0.01 },
      power: { value: 1207.5, unit: 'W' },
      voltage: { value: 230, unit: 'V' },
      powerFactor: 0.95,
      timestamp: new Date().toISOString()
    }
  }
];
