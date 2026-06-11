/**
 * Industrial Sensor Templates
 *
 * @module sensorCatalog/sensors/industrial
 * @description Sensor definitions for industrial monitoring and condition assessment
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 5 (2025-10-02)
 *
 * Contains:
 * - Load Cell / Weight Sensor - Force and weight measurement
 * - Vibration Sensor - Machine condition monitoring
 *
 * Standards: ISO 10816, ISO 2954
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const industrialSensors: SensorTemplate[] = [
  {
    id: 'load_cell',
    name: 'Load Cell / Weight Sensor',
    category: 'industrial',
    subcategory: 'force',
    description: 'Measures weight and force',
    tags: ['weight', 'force', 'load', 'scale', 'industrial'],
    icon: getSensorIcon('load_cell'),
    schema: {
      type: 'object',
      properties: {
        weight: {
          type: 'number',
          minimum: 0,
          title: 'Weight Value'
        },
        unit: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          default: 0,
          title: 'Weight Unit',
          description: '0=kg, 1=g, 2=lb, 3=oz, 4=ton'
        },
        tare: {
          type: 'number',
          title: 'Tare Weight'
        },
        overload: {
          type: 'boolean',
          title: 'Overload Warning'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['weight', 'timestamp']
    },
    uiSchema: {
      weight: { 'ui:widget': 'updown' },
      unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Kilograms (kg)', 'Grams (g)', 'Pounds (lb)', 'Ounces (oz)', 'Tons']
        }
      },
      tare: { 'ui:widget': 'updown' },
      overload: { 'ui:widget': 'radio' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      weight: 45.5,
      unit: 0,
      tare: 2.3,
      overload: false,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'vibration_sensor',
    name: 'Vibration Sensor',
    category: 'industrial',
    subcategory: 'vibration',
    description: 'Monitors machine vibration and condition',
    tags: ['vibration', 'condition', 'monitoring', 'industrial', 'predictive'],
    icon: getSensorIcon('vibration_sensor'),
    standards: ['ISO 10816', 'ISO 2954'],
    schema: {
      type: 'object',
      properties: {
        vibration_x: {
          type: 'number',
          title: 'X-axis Vibration'
        },
        vibration_y: {
          type: 'number',
          title: 'Y-axis Vibration'
        },
        vibration_z: {
          type: 'number',
          title: 'Z-axis Vibration'
        },
        unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Vibration Unit',
          description: '0=mm/s, 1=in/s, 2=g'
        },
        frequency: {
          type: 'number',
          minimum: 0,
          title: 'Dominant Frequency (Hz)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['vibration_x', 'vibration_y', 'vibration_z', 'timestamp']
    },
    uiSchema: {
      vibration_x: { 'ui:widget': 'updown' },
      vibration_y: { 'ui:widget': 'updown' },
      vibration_z: { 'ui:widget': 'updown' },
      unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['mm/s', 'in/s', 'g (acceleration)']
        }
      },
      frequency: { 'ui:widget': 'updown' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      vibration_x: 2.5,
      vibration_y: 1.8,
      vibration_z: 3.2,
      unit: 0,
      frequency: 50,
      timestamp: new Date().toISOString()
    }
  }
];
