/**
 * Particulate Matter Sensor Templates
 *
 * @module sensorCatalog/sensors/particulate-matter
 * @description Sensor definitions for particulate matter and air quality monitoring
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 7 (2025-10-02)
 *
 * Contains:
 * - PMS5003 (Plantower) - Laser particle sensor for PM1.0, PM2.5, PM10
 *
 * Standards: IEEE 1451, ISO/IEC 21451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const particulateMatterSensors: SensorTemplate[] = [
  {
    id: 'pms5003_pm',
    name: 'PMS5003 Particulate Matter Sensor',
    category: 'environmental',
    subcategory: 'air_quality',
    description: 'Plantower PMS5003 laser particle sensor for PM1.0, PM2.5, PM10',
    manufacturer: 'Plantower',
    tags: ['pms5003', 'pm', 'pm1.0', 'pm2.5', 'pm10', 'laser', 'particulate'],
    icon: getSensorIcon('pm_dust_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        pm1_0_cf1: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM1.0 CF=1 (μg/m³)'
        },
        pm2_5_cf1: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM2.5 CF=1 (μg/m³)'
        },
        pm10_cf1: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM10 CF=1 (μg/m³)'
        },
        pm1_0_atm: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM1.0 Atmospheric (μg/m³)'
        },
        pm2_5_atm: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM2.5 Atmospheric (μg/m³)'
        },
        pm10_atm: {
          type: 'number',
          minimum: 0,
          maximum: 1000,
          title: 'PM10 Atmospheric (μg/m³)'
        },
        particles_0_3um: {
          type: 'number',
          title: 'Particles >0.3μm (count/0.1L)'
        },
        particles_0_5um: {
          type: 'number',
          title: 'Particles >0.5μm (count/0.1L)'
        },
        particles_1_0um: {
          type: 'number',
          title: 'Particles >1.0μm (count/0.1L)'
        },
        particles_2_5um: {
          type: 'number',
          title: 'Particles >2.5μm (count/0.1L)'
        },
        particles_5_0um: {
          type: 'number',
          title: 'Particles >5.0μm (count/0.1L)'
        },
        particles_10um: {
          type: 'number',
          title: 'Particles >10μm (count/0.1L)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['pm1_0_cf1', 'pm2_5_cf1', 'pm10_cf1', 'timestamp']
    },
    uiSchema: {
      pm1_0_cf1: { 'ui:widget': 'updown', 'ui:help': 'PM1.0 standard particles' },
      pm2_5_cf1: { 'ui:widget': 'updown', 'ui:help': 'PM2.5 standard particles' },
      pm10_cf1: { 'ui:widget': 'updown', 'ui:help': 'PM10 standard particles' },
      pm1_0_atm: { 'ui:widget': 'updown', 'ui:help': 'PM1.0 atmospheric environment' },
      pm2_5_atm: { 'ui:widget': 'updown', 'ui:help': 'PM2.5 atmospheric environment' },
      pm10_atm: { 'ui:widget': 'updown', 'ui:help': 'PM10 atmospheric environment' },
      particles_0_3um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >0.3μm' },
      particles_0_5um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >0.5μm' },
      particles_1_0um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >1.0μm' },
      particles_2_5um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >2.5μm' },
      particles_5_0um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >5.0μm' },
      particles_10um: { 'ui:widget': 'updown', 'ui:help': 'Particle count >10μm' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      pm1_0_cf1: 12,
      pm2_5_cf1: 18,
      pm10_cf1: 23,
      pm1_0_atm: 8,
      pm2_5_atm: 12,
      pm10_atm: 15,
      particles_0_3um: 1245,
      particles_0_5um: 456,
      particles_1_0um: 123,
      particles_2_5um: 45,
      particles_5_0um: 12,
      particles_10um: 3,
      timestamp: new Date().toISOString()
    }
  }
];
