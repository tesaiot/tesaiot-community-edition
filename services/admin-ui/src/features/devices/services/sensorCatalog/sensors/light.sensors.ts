/**
 * Light & Optical Sensors Catalog
 *
 * @module sensorCatalog/sensors/light
 * @description Light, optical, and color measurement sensor configurations
 * @category Optical Sensors
 *
 * Contains sensor templates for:
 * - Light intensity sensors (BH1750, TSL2561)
 * - UV index sensors (ML8511, VEML6070)
 * - Color sensors (TCS3200, APDS9960)
 * - Flame/IR sensors (KY-026)
 *
 * @standards
 * - ISO 23539 (Photometry)
 * - ISO 17166 (Erythema reference action spectrum)
 * - CIE 1931 (Colorimetry)
 * - ISO 11664 (Colorimetry standards)
 * - CIE S 009/E:2002 (Photobiological safety)
 * - UL 268 (Smoke detectors)
 * - EN 54-5 (Fire detection systems)
 *
 * @created 2025-10-02
 * @phase Phase 1.3 Day 3
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const lightSensors: SensorTemplate[] = [
  {
    id: 'light_intensity',
    name: 'Light Intensity Sensor',
    category: 'optical',
    subcategory: 'light',
    description: 'Ambient light level measurement',
    tags: ['light', 'lux', 'illuminance', 'bh1750', 'tsl2561'],
    icon: getSensorIcon('light_intensity'),
    standards: ['ISO 23539', 'CIE S 009/E:2002'],
    schema: {
      type: 'object',
      properties: {
        illuminance: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 0, maximum: 65535 },
            unit: { type: 'string', enum: ['lux', 'fc'], default: 'lux' }
          },
          required: ['value', 'unit']
        },
        brightness: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 100 },
            unit: { type: 'string', enum: ['%'], default: '%' }
          }
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['illuminance', 'timestamp']
    },
    uiSchema: {
      illuminance: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Light Level'
        }
      },
      brightness: {
        'ui:field': 'object',
        value: { 'ui:widget': 'range' }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      illuminance: { value: 350.5, unit: 'lux' },
      brightness: { value: 45, unit: '%' },
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'uv_sensor',
    name: 'UV Index Sensor',
    category: 'optical',
    subcategory: 'light',
    description: 'Ultraviolet radiation measurement',
    tags: ['uv', 'ultraviolet', 'sun', 'ml8511', 'veml6070'],
    icon: getSensorIcon('uv_sensor'),
    standards: ['ISO 17166', 'WHO UV Index'],
    schema: {
      type: 'object',
      properties: {
        uvIndex: {
          type: 'object',
          properties: {
            value: { type: 'number', minimum: 0, maximum: 15 },
            unit: { type: 'string', enum: ['index'], default: 'index' }
          },
          required: ['value', 'unit']
        },
        uvA: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['mW/cm²'], default: 'mW/cm²' }
          }
        },
        uvB: {
          type: 'object',
          properties: {
            value: { type: 'number' },
            unit: { type: 'string', enum: ['mW/cm²'], default: 'mW/cm²' }
          }
        },
        exposure: {
          type: 'string',
          enum: ['low', 'moderate', 'high', 'very_high', 'extreme']
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['uvIndex', 'timestamp']
    },
    uiSchema: {
      uvIndex: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'UV Index',
          'ui:warningThreshold': 6,
          'ui:dangerThreshold': 8
        }
      },
      uvA: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      uvB: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      exposure: {
        'ui:widget': 'select',
        'ui:colorMap': {
          low: 'success',
          moderate: 'info',
          high: 'warning',
          very_high: 'danger',
          extreme: 'dark'
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      uvIndex: { value: 6.5, unit: 'index' },
      uvA: { value: 0.85, unit: 'mW/cm²' },
      uvB: { value: 0.42, unit: 'mW/cm²' },
      exposure: 'high',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'color_sensor',
    name: 'Color Sensor',
    category: 'optical',
    subcategory: 'color',
    description: 'RGB color detection and measurement',
    tags: ['color', 'rgb', 'wavelength', 'tcs3200', 'apds9960'],
    icon: getSensorIcon('color_sensor'),
    standards: ['CIE 1931', 'ISO 11664'],
    schema: {
      type: 'object',
      properties: {
        red: {
          type: 'number',
          minimum: 0,
          maximum: 255,
          title: 'Red Component'
        },
        green: {
          type: 'number',
          minimum: 0,
          maximum: 255,
          title: 'Green Component'
        },
        blue: {
          type: 'number',
          minimum: 0,
          maximum: 255,
          title: 'Blue Component'
        },
        color_temperature: {
          type: 'number',
          minimum: 2000,
          maximum: 10000,
          title: 'Color Temperature'
        },
        color_temperature_unit: {
          type: 'string',
          enum: ['K'],
          default: 'K',
          title: 'Color Temperature Unit'
        },
        hex: {
          type: 'string',
          title: 'Hex Color Code'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['red', 'green', 'blue', 'timestamp']
    },
    uiSchema: {
      red: {
        'ui:widget': 'updown',
        'ui:help': 'Red color component (0-255)'
      },
      green: {
        'ui:widget': 'updown',
        'ui:help': 'Green color component (0-255)'
      },
      blue: {
        'ui:widget': 'updown',
        'ui:help': 'Blue color component (0-255)'
      },
      color_temperature: {
        'ui:widget': 'updown',
        'ui:help': 'Color temperature in Kelvin'
      },
      color_temperature_unit: { 'ui:widget': 'hidden' },
      hex: {
        'ui:widget': 'text',
        'ui:readonly': true,
        'ui:help': 'Calculated hex color code'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      red: 255,
      green: 128,
      blue: 64,
      color_temperature: 5600,
      color_temperature_unit: 'K',
      hex: '#FF8040',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'flame_sensor',
    name: 'Flame Sensor',
    category: 'optical',
    subcategory: 'infrared',
    description: 'Fire and flame detection sensor',
    tags: ['flame', 'fire', 'infrared', 'safety', 'ky-026'],
    icon: getSensorIcon('flame_sensor'),
    standards: ['UL 268', 'EN 54-5'],
    schema: {
      type: 'object',
      properties: {
        flame_detected: {
          type: 'boolean',
          title: 'Flame Detected'
        },
        intensity: {
          type: 'number',
          minimum: 0,
          maximum: 1023,
          title: 'Flame Intensity'
        },
        intensity_unit: {
          type: 'string',
          enum: ['ADC'],
          default: 'ADC',
          title: 'Intensity Unit'
        },
        wavelength: {
          type: 'number',
          minimum: 760,
          maximum: 1100,
          title: 'Detection Wavelength'
        },
        wavelength_unit: {
          type: 'string',
          enum: ['nm'],
          default: 'nm',
          title: 'Wavelength Unit'
        },
        distance: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Detection Distance'
        },
        distance_unit: {
          type: 'string',
          enum: ['cm'],
          default: 'cm',
          title: 'Distance Unit'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['flame_detected', 'intensity', 'timestamp']
    },
    uiSchema: {
      flame_detected: {
        'ui:widget': 'checkbox',
        'ui:help': 'Fire or flame detection status'
      },
      intensity: {
        'ui:widget': 'updown',
        'ui:help': 'Flame intensity reading'
      },
      intensity_unit: { 'ui:widget': 'hidden' },
      wavelength: {
        'ui:widget': 'updown',
        'ui:help': 'IR wavelength detection range'
      },
      wavelength_unit: { 'ui:widget': 'hidden' },
      distance: {
        'ui:widget': 'updown',
        'ui:help': 'Maximum detection distance'
      },
      distance_unit: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      flame_detected: true,
      intensity: 850,
      intensity_unit: 'ADC',
      wavelength: 940,
      wavelength_unit: 'nm',
      distance: 30,
      distance_unit: 'cm',
      timestamp: new Date().toISOString()
    }
  }
];
