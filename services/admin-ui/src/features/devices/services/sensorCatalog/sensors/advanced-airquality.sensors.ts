/**
 * Advanced Air Quality & Gas Sensor Templates
 *
 * @module sensorCatalog/sensors/advanced-airquality
 * @description Advanced sensor definitions for VOC, CO2, and indoor air quality monitoring
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 6 (2025-10-02)
 *
 * Contains:
 * - SGP30 VOC & CO2eq (Sensirion) - XENSIV multi-gas sensor
 * - CCS811 VOC & CO2 (ScioSense) - Ultra-low power indoor air quality
 * - SCD30 CO2 (Sensirion) - NDIR CO2 with temperature and humidity
 *
 * Standards: IEEE 1451, ISO/IEC 21451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const advancedAirQualitySensors: SensorTemplate[] = [
  {
    id: 'sgp30_voc',
    name: 'SGP30 VOC & CO2eq Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'XENSIV SGP30 multi-gas sensor for TVOC and CO2 equivalent',
    manufacturer: 'Sensirion',
    tags: ['sgp30', 'voc', 'tvoc', 'co2eq', 'air_quality', 'xensiv'],
    icon: getSensorIcon('voc_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        tvoc: {
          type: 'number',
          minimum: 0,
          maximum: 60000,
          title: 'Total VOC (ppb)'
        },
        co2eq: {
          type: 'number',
          minimum: 400,
          maximum: 60000,
          title: 'CO2 Equivalent (ppm)'
        },
        h2_raw: {
          type: 'number',
          title: 'Raw H2 Signal'
        },
        ethanol_raw: {
          type: 'number',
          title: 'Raw Ethanol Signal'
        },
        baseline_tvoc: {
          type: 'number',
          title: 'TVOC Baseline'
        },
        baseline_co2eq: {
          type: 'number',
          title: 'CO2eq Baseline'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['tvoc', 'co2eq', 'timestamp']
    },
    uiSchema: {
      tvoc: { 'ui:widget': 'updown', 'ui:help': 'Total Volatile Organic Compounds' },
      co2eq: { 'ui:widget': 'updown', 'ui:help': 'CO2 Equivalent' },
      h2_raw: { 'ui:widget': 'updown', 'ui:help': 'Raw hydrogen signal' },
      ethanol_raw: { 'ui:widget': 'updown', 'ui:help': 'Raw ethanol signal' },
      baseline_tvoc: { 'ui:widget': 'updown', 'ui:help': 'TVOC baseline for calibration' },
      baseline_co2eq: { 'ui:widget': 'updown', 'ui:help': 'CO2eq baseline for calibration' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      tvoc: 125,
      co2eq: 450,
      h2_raw: 12543,
      ethanol_raw: 18394,
      baseline_tvoc: 36289,
      baseline_co2eq: 39816,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'ccs811_voc',
    name: 'CCS811 VOC & CO2 Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'AMS CCS811 ultra-low power digital gas sensor for monitoring indoor air quality',
    manufacturer: 'ScioSense (formerly AMS)',
    tags: ['ccs811', 'voc', 'co2', 'air_quality', 'indoor'],
    icon: getSensorIcon('voc_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        tvoc: {
          type: 'number',
          minimum: 0,
          maximum: 32768,
          title: 'Total VOC (ppb)'
        },
        co2: {
          type: 'number',
          minimum: 400,
          maximum: 32768,
          title: 'CO2 Equivalent (ppm)'
        },
        raw_data: {
          type: 'number',
          title: 'Raw ADC Data'
        },
        status: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Sensor Status',
          description: '0=Valid, 1=Warm-up, 2=Initial, 3=Error'
        },
        error_id: {
          type: 'integer',
          title: 'Error ID'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['tvoc', 'co2', 'timestamp']
    },
    uiSchema: {
      tvoc: { 'ui:widget': 'updown', 'ui:help': 'Total Volatile Organic Compounds' },
      co2: { 'ui:widget': 'updown', 'ui:help': 'CO2 Equivalent' },
      raw_data: { 'ui:widget': 'updown', 'ui:help': 'Raw sensor data' },
      status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Valid Data', 'Warm-up Mode', 'Initial Start-up', 'Error']
        }
      },
      error_id: { 'ui:widget': 'updown', 'ui:help': 'Error code if status=3' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      tvoc: 89,
      co2: 423,
      raw_data: 6543,
      status: 0,
      error_id: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'scd30_co2',
    name: 'SCD30 CO2, Temperature & Humidity Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'Sensirion SCD30 NDIR CO2 sensor with integrated temperature and humidity',
    manufacturer: 'Sensirion',
    tags: ['scd30', 'co2', 'ndir', 'temperature', 'humidity', 'combo'],
    icon: getSensorIcon('co2_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        co2: {
          type: 'number',
          minimum: 0,
          maximum: 40000,
          title: 'CO2 Concentration (ppm)'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 70,
          title: 'Temperature (°C)'
        },
        humidity: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Relative Humidity (%RH)'
        },
        altitude_compensation: {
          type: 'number',
          title: 'Altitude Compensation (m)'
        },
        auto_calibration: {
          type: 'boolean',
          title: 'Auto Self-Calibration Enabled'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['co2', 'temperature', 'humidity', 'timestamp']
    },
    uiSchema: {
      co2: { 'ui:widget': 'updown', 'ui:help': 'NDIR CO2 measurement' },
      temperature: { 'ui:widget': 'updown', 'ui:help': 'Built-in temperature sensor' },
      humidity: { 'ui:widget': 'updown', 'ui:help': 'Built-in humidity sensor' },
      altitude_compensation: { 'ui:widget': 'updown', 'ui:help': 'Altitude above sea level' },
      auto_calibration: { 'ui:widget': 'checkbox', 'ui:help': 'Automatic self-calibration feature' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      co2: 456,
      temperature: 22.5,
      humidity: 58.3,
      altitude_compensation: 100,
      auto_calibration: true,
      timestamp: new Date().toISOString()
    }
  }
];
