/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Temperature and Environmental Sensor Configurations
 * Includes: Basic temperature, temperature+humidity, pressure+temperature, VOC sensors
 */

import { getSensorIcon } from '../../../components/SensorIcons';
import type { SensorTemplate } from '../types/sensor.types';

export const temperatureSensors: SensorTemplate[] = [
  {
    id: 'temperature_basic',
    name: 'Temperature Sensor',
    category: 'environmental',
    subcategory: 'temperature',
    description: 'Basic temperature measurement sensor (IoT optimized)',
    tags: ['temperature', 'thermal', 'environmental'],
    icon: getSensorIcon('temperature_basic'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 125,
          title: 'Temperature Value'
        },
        unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Temperature Unit',
          description: '0=°C, 1=°F, 2=K'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['temperature', 'timestamp']
    },
    uiSchema: {
      temperature: {
        'ui:widget': 'updown',
        'ui:help': 'Temperature reading'
      },
      unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['°C (Celsius)', '°F (Fahrenheit)', 'K (Kelvin)']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      temperature: 25.5,
      unit: 0,
      timestamp: new Date().toISOString()
    },
    units: { temperature: '°C' },
    ranges: { temperature: { min: -40, max: 125 } },
    accuracy: { temperature: 0.1 }
  },
  {
    id: 'temperature_humidity',
    name: 'Temperature & Humidity Sensor',
    category: 'environmental',
    subcategory: 'temperature',
    description: 'Combined temperature and humidity measurement',
    tags: ['temperature', 'humidity', 'environmental', 'dht22', 'sht31'],
    icon: getSensorIcon('temperature_humidity'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 125,
          title: 'Temperature Value'
        },
        temperature_unit: {
          type: 'string',
          enum: ['°C', '°F', 'K'],
          default: '°C',
          title: 'Temperature Unit'
        },
        humidity: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Humidity Value'
        },
        humidity_unit: {
          type: 'integer',
          enum: [0],
          default: 0,
          title: 'Humidity Unit',
          description: '0=%RH'
        },
        dew_point: {
          type: 'number',
          title: 'Dew Point (calculated)'
        },
        dew_point_unit: {
          type: 'string',
          enum: ['°C'],
          default: '°C',
          title: 'Dew Point Unit'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['temperature', 'humidity', 'timestamp']
    },
      uiSchema: {
      temperature: {
        'ui:widget': 'updown',
        'ui:help': 'Temperature reading'
      },
      temperature_unit: { 'ui:widget': 'hidden' },
      humidity: {
        'ui:widget': 'updown',
        'ui:help': 'Humidity percentage'
      },
      humidity_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['%RH (Relative Humidity)']
        }
      },
      dew_point: {
        'ui:widget': 'text',
        'ui:readonly': true,
        'ui:help': 'Automatically calculated'
      },
      dew_point_unit: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      temperature: 24.8,
      temperature_unit: 0,
      humidity: 65.2,
      humidity_unit: 0,
      dew_point: 17.3,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'pressure_temperature',
    name: 'Pressure & Temperature Sensor',
    category: 'environmental',
    subcategory: 'pressure',
    description: 'Atmospheric pressure with temperature compensation',
    tags: ['pressure', 'temperature', 'altitude', 'bmp280', 'bme280'],
    icon: getSensorIcon('pressure_temperature'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        pressure: {
          type: 'number',
          minimum: 300,
          maximum: 1200,
          title: 'Atmospheric Pressure'
        },
        pressure_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Pressure Unit',
          description: '0=hPa, 1=bar, 2=psi'
        },
        altitude: {
          type: 'number',
          title: 'Altitude (calculated)'
        },
        altitude_unit: {
          type: 'integer',
          enum: [0, 1],
          default: 0,
          title: 'Altitude Unit',
          description: '0=m, 1=ft'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          title: 'Temperature'
        },
        temperature_unit: {
          type: 'string',
          enum: ['°C', '°F', 'K'],
          default: '°C',
          title: 'Temperature Unit'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['pressure', 'temperature', 'timestamp']
    },
    uiSchema: {
      pressure: {
        'ui:widget': 'updown',
        'ui:help': 'Atmospheric pressure reading'
      },
      pressure_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['hPa (hectopascal)', 'bar', 'psi (pounds per square inch)']
        }
      },
      altitude: {
        'ui:widget': 'text',
        'ui:readonly': true,
        'ui:help': 'Calculated from pressure'
      },
      altitude_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['m (meters)', 'ft (feet)']
        }
      },
      temperature: {
        'ui:widget': 'updown',
        'ui:help': 'Temperature reading'
      },
      temperature_unit: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      pressure: 1013.25,
      pressure_unit: 0,
      altitude: 156.2,
      altitude_unit: 0,
      temperature: 22.3,
      temperature_unit: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'voc_sensor',
    name: 'VOC Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'Volatile Organic Compounds measurement',
    tags: ['voc', 'tvoc', 'eco2', 'iaq', 'air quality', 'sgp30', 'ccs811'],
    icon: getSensorIcon('voc_sensor'),
    standards: ['ISO 16000', 'ASHRAE 62.1'],
    schema: {
      type: 'object',
      properties: {
        tvoc: {
          type: 'number',
          minimum: 0,
          maximum: 60000,
          title: 'TVOC Concentration'
        },
        tvoc_unit: {
          type: 'string',
          enum: ['ppb'],
          default: 'ppb',
          title: 'TVOC Unit'
        },
        eco2: {
          type: 'number',
          minimum: 400,
          maximum: 60000,
          title: 'Equivalent CO2'
        },
        eco2_unit: {
          type: 'string',
          enum: ['ppm'],
          default: 'ppm',
          title: 'eCO2 Unit'
        },
        iaq: {
          type: 'number',
          minimum: 0,
          maximum: 500,
          title: 'Indoor Air Quality Index'
        },
        iaq_unit: {
          type: 'string',
          enum: ['index'],
          default: 'index',
          title: 'IAQ Unit'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['tvoc', 'eco2', 'timestamp']
    },
    uiSchema: {
      tvoc: {
        'ui:widget': 'updown',
        'ui:help': 'Total Volatile Organic Compounds'
      },
      tvoc_unit: { 'ui:widget': 'hidden' },
      eco2: {
        'ui:widget': 'updown',
        'ui:help': 'Equivalent CO2 concentration'
      },
      eco2_unit: { 'ui:widget': 'hidden' },
      iaq: {
        'ui:widget': 'updown',
        'ui:help': 'Indoor Air Quality Index (0-500)'
      },
      iaq_unit: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      tvoc: 125,
      tvoc_unit: 'ppb',
      eco2: 435,
      eco2_unit: 'ppm',
      iaq: 95,
      iaq_unit: 'index',
      timestamp: new Date().toISOString()
    }
  }
];
