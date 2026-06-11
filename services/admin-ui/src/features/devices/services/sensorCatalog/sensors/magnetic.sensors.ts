/**
 * Magnetic & Field Sensors Catalog
 *
 * @module sensorCatalog/sensors/magnetic
 * @description Magnetic field and proximity sensor configurations
 * @category Magnetic Sensors
 *
 * Contains sensor templates for:
 * - Hall effect sensors (magnetic field detection)
 * - Reed switches (door/window sensors)
 *
 * @created 2025-10-02
 * @phase Phase 1.4 Week 1 Day 2
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const magneticSensors: SensorTemplate[] = [
  {
    id: 'hall_effect',
    name: 'Hall Effect Sensor',
    category: 'magnetic',
    subcategory: 'field',
    description: 'Detects magnetic field presence and strength',
    tags: ['magnetic', 'hall', 'field', 'proximity'],
    icon: getSensorIcon('hall_effect'),
    schema: {
      type: 'object',
      properties: {
        magnetic_field: {
          type: 'number',
          title: 'Magnetic Field Strength'
        },
        unit: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Field Unit',
          description: '0=μT, 1=mT, 2=Gauss, 3=Tesla'
        },
        detected: {
          type: 'boolean',
          title: 'Magnet Detected'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['magnetic_field', 'detected', 'timestamp']
    },
    uiSchema: {
      magnetic_field: { 'ui:widget': 'updown' },
      unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['μT (micro-Tesla)', 'mT (milli-Tesla)', 'Gauss', 'Tesla']
        }
      },
      detected: { 'ui:widget': 'radio' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      magnetic_field: 125.5,
      unit: 0,
      detected: true,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'reed_switch',
    name: 'Reed Switch',
    category: 'magnetic',
    subcategory: 'switch',
    description: 'Magnetic proximity switch for door/window detection',
    tags: ['magnetic', 'switch', 'door', 'window', 'security'],
    icon: getSensorIcon('reed_switch'),
    schema: {
      type: 'object',
      properties: {
        state: {
          type: 'integer',
          enum: [0, 1],
          title: 'Switch State',
          description: '0=Open, 1=Closed'
        },
        count: {
          type: 'integer',
          minimum: 0,
          title: 'State Change Count'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['state', 'timestamp']
    },
    uiSchema: {
      state: {
        'ui:widget': 'radio',
        'ui:options': {
          enumNames: ['Open', 'Closed']
        }
      },
      count: { 'ui:widget': 'updown' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      state: 1,
      count: 42,
      timestamp: new Date().toISOString()
    }
  }
];
