/**
 * Motion & Position Sensors Catalog
 *
 * @module sensorCatalog/sensors/motion
 * @description Motion, acceleration, and presence detection sensor configurations
 * @category Motion Sensors
 *
 * Contains sensor templates for:
 * - Accelerometers (3-axis, MPU6050, ADXL345)
 * - PIR motion sensors (HC-SR501)
 * - Presence detection sensors
 *
 * @standards
 * - IEEE 1451 (Smart transducer interface)
 * - ISO 16063 (Vibration and shock sensor calibration)
 * - IEC 60839-2-5 (Alarm systems - PIR detectors)
 *
 * @created 2025-10-02
 * @phase Phase 1.3 Day 2
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const motionSensors: SensorTemplate[] = [
  {
    id: 'accelerometer',
    name: 'Accelerometer',
    category: 'motion',
    subcategory: 'acceleration',
    description: '3-axis acceleration measurement',
    tags: ['acceleration', 'motion', 'vibration', 'mpu6050', 'adxl345'],
    icon: getSensorIcon('accelerometer'),
    standards: ['IEEE 1451', 'ISO 16063'],
    schema: {
      type: 'object',
      properties: {
        acceleration: {
          type: 'object',
          properties: {
            x: {
              type: 'object',
              properties: {
                value: { type: 'number', minimum: -16, maximum: 16 },
                unit: { type: 'string', enum: ['g', 'm/s²'], default: 'g' }
              }
            },
            y: {
              type: 'object',
              properties: {
                value: { type: 'number', minimum: -16, maximum: 16 },
                unit: { type: 'string', enum: ['g', 'm/s²'], default: 'g' }
              }
            },
            z: {
              type: 'object',
              properties: {
                value: { type: 'number', minimum: -16, maximum: 16 },
                unit: { type: 'string', enum: ['g', 'm/s²'], default: 'g' }
              }
            }
          },
          required: ['x', 'y', 'z']
        },
        magnitude: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['g', 'm/s²'], default: 'g' },
            calculated: { type: 'boolean', default: true }
          }
        },
        orientation: {
          type: 'string',
          enum: ['upright', 'upside_down', 'left', 'right', 'face_up', 'face_down']
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['acceleration', 'timestamp']
    },
    uiSchema: {
      acceleration: {
        'ui:field': 'object',
        'ui:widget': 'textarea'
      },
      magnitude: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'text',
          'ui:readonly': true
        }
      },
      orientation: {
        'ui:widget': 'select'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      acceleration: {
        x: { value: 0.02, unit: 'g' },
        y: { value: -0.98, unit: 'g' },
        z: { value: 9.81, unit: 'g' }
      },
      magnitude: { value: 9.81, unit: 'g', calculated: true },
      orientation: 'upright',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'pir_motion',
    name: 'PIR Motion Sensor',
    category: 'motion',
    subcategory: 'presence',
    description: 'Passive infrared motion detection',
    tags: ['motion', 'pir', 'presence', 'security', 'hc-sr501'],
    icon: getSensorIcon('pir_motion'),
    standards: ['IEC 60839-2-5'],
    schema: {
      type: 'object',
      properties: {
        motionDetected: { type: 'boolean' },
        lastMotionTime: { type: 'string', format: 'date-time' },
        sensitivity: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 100 },
            unit: { type: 'string', enum: ['%'], default: '%' }
          }
        },
        detectionRange: {
          type: 'object',
          properties: {
            value: { type: 'integer', maximum: 10 },
            unit: { type: 'string', enum: ['m'], default: 'm' }
          }
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['motionDetected', 'timestamp']
    },
    uiSchema: {
      motionDetected: {
        'ui:widget': 'checkbox',
        'ui:options': {
          trueLabel: 'Motion Detected',
          falseLabel: 'No Motion',
          trueColor: 'danger',
          falseColor: 'success'
        }
      },
      lastMotionTime: {
        'ui:widget': 'text',
        'ui:format': 'relative'
      },
      sensitivity: {
        'ui:field': 'object',
        value: { 'ui:widget': 'slider' }
      },
      detectionRange: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'text',
          'ui:readonly': true
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      motionDetected: true,
      lastMotionTime: new Date().toISOString(),
      sensitivity: { value: 75, unit: '%' },
      detectionRange: { value: 7, unit: 'm' },
      timestamp: new Date().toISOString()
    }
  }
];
