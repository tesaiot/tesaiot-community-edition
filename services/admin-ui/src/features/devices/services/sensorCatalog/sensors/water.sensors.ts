/**
 * Water & Liquid Sensors Catalog
 *
 * @module sensorCatalog/sensors/water
 * @description Water quality and liquid flow sensor configurations
 * @category Water Sensors
 *
 * Contains sensor templates for:
 * - pH sensors (aquarium, hydroponics)
 * - Flow rate sensors (YF-S201, industrial)
 *
 * @standards
 * - ISO 10523 (Water quality - pH determination)
 * - ASTM D1293 (Standard test methods for pH of water)
 * - ISO 4064 (Water meters)
 * - OIML R 49 (Water meters intended for measuring volumes of cold potable water)
 *
 * @created 2025-10-02
 * @phase Phase 1.3 Day 5 (Final)
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const waterSensors: SensorTemplate[] = [
  {
    id: 'ph_sensor',
    name: 'pH Sensor',
    category: 'water',
    subcategory: 'chemistry',
    description: 'Water pH level measurement',
    tags: ['ph', 'water', 'chemistry', 'aquarium', 'hydroponics'],
    icon: getSensorIcon('ph_sensor'),
    standards: ['ISO 10523', 'ASTM D1293'],
    schema: {
      type: 'object',
      properties: {
        ph: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 0, maximum: 14 },
            unit: { type: 'string', enum: ['pH'], default: 'pH' },
            precision: { type: 'number', default: 0.01 }
          },
          required: ['value', 'unit']
        },
        temperature: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['°C', '°F'], default: '°C' }
          }
        },
        voltage: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['V', 'mV'], default: 'V' }
          }
        },
        calibrated: { type: 'boolean' },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['ph', 'timestamp']
    },
    uiSchema: {
      ph: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'pH Level',
          'ui:colorRanges': [
            { min: 0, max: 6.5, color: 'danger' },
            { min: 6.5, max: 7.5, color: 'success' },
            { min: 7.5, max: 14, color: 'warning' }
          ]
        }
      },
      temperature: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      voltage: { 'ui:widget': 'hidden' },
      calibrated: { 'ui:widget': 'checkbox' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      ph: { value: 7.2, unit: 'pH', precision: 0.01 },
      temperature: { value: 25.0, unit: '°C' },
      voltage: { value: 2.15, unit: 'V' },
      calibrated: true,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'flow_rate',
    name: 'Flow Rate Sensor',
    category: 'water',
    subcategory: 'flow',
    description: 'Liquid flow rate measurement',
    tags: ['flow', 'water', 'liquid', 'yf-s201', 'industrial'],
    icon: getSensorIcon('flow_rate'),
    standards: ['ISO 4064', 'OIML R 49'],
    schema: {
      type: 'object',
      properties: {
        flowRate: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 0, maximum: 30 },
            unit: { type: 'string', enum: ['L/min', 'gal/min', 'm³/h'], default: 'L/min' }
          },
          required: ['value', 'unit']
        },
        totalVolume: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['L', 'gal', 'm³'], default: 'L' }
          }
        },
        pulseCount: { type: 'integer' },
        temperature: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['°C', '°F'], default: '°C' }
          }
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['flowRate', 'timestamp']
    },
    uiSchema: {
      flowRate: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Flow Rate'
        }
      },
      totalVolume: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Total Volume'
        }
      },
      pulseCount: { 'ui:widget': 'hidden' },
      temperature: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      flowRate: { value: 2.5, unit: 'L/min' },
      totalVolume: { value: 125.6, unit: 'L' },
      pulseCount: 4580,
      temperature: { value: 23.5, unit: '°C' },
      timestamp: new Date().toISOString()
    }
  }
];
