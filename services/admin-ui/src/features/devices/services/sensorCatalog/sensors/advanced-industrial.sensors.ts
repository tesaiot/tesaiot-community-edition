/**
 * Advanced Industrial Sensor Templates
 *
 * @module sensorCatalog/sensors/advanced-industrial
 * @description Advanced sensor definitions for industrial monitoring and precision measurement
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 8 (2025-10-02)
 *
 * Contains:
 * - HX711 Load Cell Amplifier - Precision weight measurement
 * - ADXL345 3-Axis Accelerometer (Analog Devices) - Vibration monitoring
 *
 * Standards: IEEE 1451, ISO/IEC 21451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const advancedIndustrialSensors: SensorTemplate[] = [
  {
    id: 'hx711_load_cell',
    name: 'HX711 Load Cell Amplifier',
    category: 'industrial',
    subcategory: 'force',
    description: 'HX711 precision ADC for load cell and weight measurement applications',
    tags: ['hx711', 'load_cell', 'weight', 'strain_gauge', 'adc', 'precision'],
    icon: getSensorIcon('load_cell'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        raw_value: {
          type: 'number',
          title: 'Raw ADC Value'
        },
        weight: {
          type: 'number',
          minimum: -1000,
          maximum: 1000,
          title: 'Weight'
        },
        weight_unit: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Weight Unit',
          description: '0=kg, 1=g, 2=lb, 3=oz'
        },
        tare_offset: {
          type: 'number',
          title: 'Tare Offset'
        },
        calibration_factor: {
          type: 'number',
          title: 'Calibration Factor'
        },
        stable: {
          type: 'boolean',
          title: 'Reading Stable'
        },
        overload: {
          type: 'boolean',
          title: 'Overload Detected'
        },
        gain: {
          type: 'integer',
          enum: [0, 1, 2],
          title: 'Amplifier Gain',
          description: '0=128, 1=64, 2=32'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['raw_value', 'weight', 'timestamp']
    },
    uiSchema: {
      raw_value: { 'ui:widget': 'updown', 'ui:help': 'Raw 24-bit ADC reading' },
      weight: { 'ui:widget': 'updown', 'ui:help': 'Calculated weight value' },
      weight_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['kg (Kilogram)', 'g (Gram)', 'lb (Pound)', 'oz (Ounce)']
        }
      },
      tare_offset: { 'ui:widget': 'updown', 'ui:help': 'Zero offset calibration' },
      calibration_factor: { 'ui:widget': 'updown', 'ui:help': 'Scale calibration factor' },
      stable: { 'ui:widget': 'checkbox', 'ui:help': 'Reading is stable/settled' },
      overload: { 'ui:widget': 'checkbox', 'ui:help': 'Load cell overloaded' },
      gain: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['128x (Channel A)', '64x (Channel A)', '32x (Channel B)']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      raw_value: 8423567,
      weight: 2.45,
      weight_unit: 0,
      tare_offset: 8245123,
      calibration_factor: 420.5,
      stable: true,
      overload: false,
      gain: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'adxl345_vibration',
    name: 'ADXL345 3-Axis Accelerometer',
    category: 'industrial',
    subcategory: 'vibration',
    description: 'Analog Devices ADXL345 digital accelerometer for vibration monitoring',
    manufacturer: 'Analog Devices',
    tags: ['adxl345', 'accelerometer', 'vibration', 'mems', 'digital', 'spi', 'i2c'],
    icon: getSensorIcon('vibration_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        accel_x: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'X-axis Acceleration (g)'
        },
        accel_y: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'Y-axis Acceleration (g)'
        },
        accel_z: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'Z-axis Acceleration (g)'
        },
        magnitude: {
          type: 'number',
          title: 'Acceleration Magnitude (g)'
        },
        vibration_rms: {
          type: 'number',
          title: 'RMS Vibration Level'
        },
        frequency_peak: {
          type: 'number',
          title: 'Peak Frequency (Hz)'
        },
        range: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Measurement Range',
          description: '0=±2g, 1=±4g, 2=±8g, 3=±16g'
        },
        resolution: {
          type: 'integer',
          enum: [0, 1],
          title: 'Resolution Mode',
          description: '0=10-bit, 1=Full_Resolution'
        },
        data_rate: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
          title: 'Data Rate',
          description: '0=0.1Hz, 15=3200Hz'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['accel_x', 'accel_y', 'accel_z', 'timestamp']
    },
    uiSchema: {
      accel_x: { 'ui:widget': 'updown', 'ui:help': 'X-axis acceleration' },
      accel_y: { 'ui:widget': 'updown', 'ui:help': 'Y-axis acceleration' },
      accel_z: { 'ui:widget': 'updown', 'ui:help': 'Z-axis acceleration' },
      magnitude: { 'ui:widget': 'updown', 'ui:help': 'Resultant acceleration magnitude' },
      vibration_rms: { 'ui:widget': 'updown', 'ui:help': 'RMS vibration level' },
      frequency_peak: { 'ui:widget': 'updown', 'ui:help': 'Dominant frequency component' },
      range: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['±2g', '±4g', '±8g', '±16g']
        }
      },
      resolution: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['10-bit Fixed', 'Full Resolution']
        }
      },
      data_rate: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['0.1 Hz', '0.2 Hz', '0.39 Hz', '0.78 Hz', '1.56 Hz', '3.13 Hz',
                     '6.25 Hz', '12.5 Hz', '25 Hz', '50 Hz', '100 Hz', '200 Hz',
                     '400 Hz', '800 Hz', '1600 Hz', '3200 Hz']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      accel_x: 0.12,
      accel_y: -0.05,
      accel_z: 9.78,
      magnitude: 9.79,
      vibration_rms: 0.15,
      frequency_peak: 60,
      range: 0,
      resolution: 1,
      data_rate: 9,
      timestamp: new Date().toISOString()
    }
  }
];
