/**
 * Sound & Acoustic Sensors Catalog
 *
 * @module sensorCatalog/sensors/sound
 * @description Sound pressure level and acoustic measurement sensor configurations
 * @category Sound Sensors
 *
 * Contains sensor templates for:
 * - Sound level meters (SPL sensors)
 * - Acoustic measurement devices
 *
 * @standards
 * - IEC 61672 (Electroacoustics - Sound level meters)
 * - ANSI S1.4 (Specification for sound level meters)
 *
 * @created 2025-10-02
 * @phase Phase 1.4 Week 1 Day 1
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const soundSensors: SensorTemplate[] = [
  {
    id: 'sound_level',
    name: 'Sound Level Sensor',
    category: 'sound',
    subcategory: 'acoustic',
    description: 'Measures sound pressure level with IoT-optimized data',
    tags: ['sound', 'audio', 'noise', 'decibel', 'acoustic', 'spl'],
    icon: getSensorIcon('sound_level'),
    standards: ['IEC 61672', 'ANSI S1.4'],
    schema: {
      type: 'object',
      properties: {
        sound_level: {
          type: 'number',
          minimum: 0,
          maximum: 140,
          title: 'Sound Level (dB)'
        },
        sound_level_unit: {
          type: 'string',
          enum: ['dB'],
          default: 'dB',
          title: 'Sound Level Unit'
        },
        frequency: {
          type: 'number',
          minimum: 20,
          maximum: 20000,
          title: 'Dominant Frequency (Hz)'
        },
        frequency_unit: {
          type: 'string',
          enum: ['Hz'],
          default: 'Hz',
          title: 'Frequency Unit'
        },
        weighting: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Frequency Weighting',
          description: '0=A-weighting, 1=C-weighting, 2=Z-weighting, 3=Custom'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['sound_level', 'timestamp']
    },
    uiSchema: {
      sound_level: { 'ui:widget': 'updown' },
      sound_level_unit: { 'ui:widget': 'hidden' },
      frequency_unit: { 'ui:widget': 'hidden' },
      frequency: { 'ui:widget': 'updown' },
      weighting: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['A-weighting', 'C-weighting', 'Z-weighting', 'Custom']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      sound_level: 65.5,
      frequency: 1000,
      weighting: 0,
      timestamp: new Date().toISOString()
    }
  }
];
