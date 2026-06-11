/**
 * Air Quality Sensors Catalog
 *
 * @module sensorCatalog/sensors/airquality
 * @description Air quality and atmospheric composition sensor configurations
 * @category Environmental Sensors
 *
 * Contains sensor templates for:
 * - CO₂ sensors (NDIR, MH-Z19, SCD30)
 * - Particulate matter sensors (PM2.5, PM10, PMS5003, SDS011)
 *
 * @standards
 * - ISO 16000-26 (CO₂ measurement)
 * - ISO 7708 (Air quality - particle size definitions)
 * - ASHRAE 62.1 (Ventilation for acceptable indoor air quality)
 * - EPA PM2.5 NAAQS (National Ambient Air Quality Standards)
 *
 * @created 2025-10-02
 * @phase Phase 1.3 Day 1
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const airQualitySensors: SensorTemplate[] = [
  {
    id: 'co2_sensor',
    name: 'CO₂ Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'Carbon dioxide concentration measurement',
    tags: ['co2', 'air quality', 'ndir', 'mh-z19', 'scd30'],
    icon: getSensorIcon('co2_sensor'),
    standards: ['ISO 16000-26', 'ASHRAE 62.1'],
    schema: {
      type: 'object',
      properties: {
        co2: {
          type: 'integer',
          minimum: 400,
          maximum: 10000,
          title: 'CO₂ Level'
        },
        co2_unit: {
          type: 'string',
          enum: ['ppm'],
          default: 'ppm',
          title: 'CO₂ Unit'
        },
        air_quality: {
          type: 'string',
          enum: ['excellent', 'good', 'moderate', 'poor', 'hazardous'],
          title: 'Air Quality Status'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['co2', 'timestamp']
    },
    uiSchema: {
      co2: {
        'ui:widget': 'updown',
        'ui:help': 'CO₂ concentration in ppm'
      },
      co2_unit: { 'ui:widget': 'hidden' },
      air_quality: {
        'ui:widget': 'select',
        'ui:help': 'Calculated air quality status'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      co2: 412,
      co2_unit: 'ppm',
      air_quality: 'good',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'pm_dust_sensor',
    name: 'PM2.5/PM10 Dust Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'Particulate matter concentration measurement',
    tags: ['pm2.5', 'pm10', 'dust', 'air quality', 'pms5003', 'sds011'],
    icon: getSensorIcon('pm_dust_sensor'),
    standards: ['ISO 7708', 'EPA PM2.5 NAAQS'],
    schema: {
      type: 'object',
      properties: {
        pm1_0: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 1000 },
            unit: { type: 'string', enum: ['μg/m³'], default: 'μg/m³' }
          }
        },
        pm2_5: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 1000 },
            unit: { type: 'string', enum: ['μg/m³'], default: 'μg/m³' }
          },
          required: ['value', 'unit']
        },
        pm10: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 1000 },
            unit: { type: 'string', enum: ['μg/m³'], default: 'μg/m³' }
          },
          required: ['value', 'unit']
        },
        aqi: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 500 },
            unit: { type: 'string', enum: ['index'], default: 'index' }
          }
        },
        airQuality: {
          type: 'string',
          enum: ['good', 'moderate', 'unhealthy_sensitive', 'unhealthy', 'very_unhealthy', 'hazardous']
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['pm2_5', 'pm10', 'timestamp']
    },
    uiSchema: {
      pm1_0: {
        'ui:field': 'object',
        value: { 'ui:widget': 'text' }
      },
      pm2_5: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'PM2.5'
        }
      },
      pm10: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'PM10'
        }
      },
      aqi: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'updown',
          'ui:title': 'Air Quality Index'
        }
      },
      airQuality: {
        'ui:widget': 'select',
        'ui:colorMap': {
          good: 'success',
          moderate: 'warning',
          unhealthy_sensitive: 'orange',
          unhealthy: 'danger',
          very_unhealthy: 'purple',
          hazardous: 'dark'
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      pm1_0: { value: 8, unit: 'μg/m³' },
      pm2_5: { value: 15, unit: 'μg/m³' },
      pm10: { value: 22, unit: 'μg/m³' },
      aqi: { value: 55, unit: 'index' },
      airQuality: 'moderate',
      timestamp: new Date().toISOString()
    }
  }
];
