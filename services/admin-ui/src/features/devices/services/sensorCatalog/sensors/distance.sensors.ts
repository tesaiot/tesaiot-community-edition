/**
 * Distance & Proximity Sensors Catalog
 *
 * @module sensorCatalog/sensors/distance
 * @description Distance and proximity measurement sensor configurations
 * @category Distance Sensors
 *
 * Contains sensor templates for:
 * - Ultrasonic distance sensors (HC-SR04, MaxBotix)
 * - Proximity detection sensors
 *
 * @standards
 * - ISO 16063-11 (Vibration and shock - Primary calibration by laser interferometry)
 *
 * @created 2025-10-02
 * @phase Phase 1.3 Day 4
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const distanceSensors: SensorTemplate[] = [
  {
    id: 'ultrasonic_distance',
    name: 'Ultrasonic Distance Sensor',
    category: 'distance',
    subcategory: 'ultrasonic',
    description: 'Ultrasonic distance measurement',
    tags: ['distance', 'ultrasonic', 'proximity', 'hc-sr04', 'maxbotix'],
    icon: getSensorIcon('ultrasonic_distance'),
    standards: ['ISO 16063-11'],
    schema: {
      type: 'object',
      properties: {
        distance: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 2, maximum: 400 },
            unit: { type: 'string', enum: ['cm', 'm', 'in'], default: 'cm' },
            precision: { type: 'number', default: 0.3 }
          },
          required: ['value', 'unit']
        },
        echoTime: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['ms', 'μs'], default: 'ms' }
          }
        },
        objectDetected: { type: 'boolean' },
        signalStrength: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 100 },
            unit: { type: 'string', enum: ['%'], default: '%' }
          }
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['distance', 'timestamp']
    },
    uiSchema: {
      distance: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Distance'
        }
      },
      echoTime: { 'ui:widget': 'hidden' },
      objectDetected: { 'ui:widget': 'checkbox' },
      signalStrength: {
        'ui:field': 'object',
        value: { 'ui:widget': 'range' }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      distance: { value: 125.5, unit: 'cm', precision: 0.3 },
      echoTime: { value: 7.3, unit: 'ms' },
      objectDetected: true,
      signalStrength: { value: 85, unit: '%' },
      timestamp: new Date().toISOString()
    }
  }
];
