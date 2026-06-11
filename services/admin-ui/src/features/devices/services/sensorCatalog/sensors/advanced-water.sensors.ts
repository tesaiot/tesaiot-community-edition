/**
 * Advanced Water Quality Sensor Templates
 *
 * @module sensorCatalog/sensors/advanced-water
 * @description Advanced sensor definitions for water quality and level monitoring
 * @category Sensors
 * @phase Phase 1.4 Week 2 Day 8 (2025-10-02)
 *
 * Contains:
 * - TDS Meter - Total Dissolved Solids measurement
 * - Ultrasonic Water Level - Non-contact level measurement
 *
 * Standards: IEEE 1451, ISO/IEC 21451
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const advancedWaterSensors: SensorTemplate[] = [
  {
    id: 'tds_meter',
    name: 'TDS (Total Dissolved Solids) Meter',
    category: 'water',
    subcategory: 'quality',
    description: 'TDS meter for measuring total dissolved solids in water',
    tags: ['tds', 'conductivity', 'water_quality', 'salinity', 'purity'],
    icon: getSensorIcon('tds_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        tds_ppm: {
          type: 'number',
          minimum: 0,
          maximum: 5000,
          title: 'TDS (ppm)'
        },
        ec_value: {
          type: 'number',
          minimum: 0,
          maximum: 10000,
          title: 'Electrical Conductivity (μS/cm)'
        },
        salinity: {
          type: 'number',
          minimum: 0,
          maximum: 42,
          title: 'Salinity (ppt)'
        },
        temperature: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Water Temperature (°C)'
        },
        temperature_compensation: {
          type: 'boolean',
          title: 'Temperature Compensation Enabled'
        },
        calibration_point_low: {
          type: 'number',
          title: 'Low Calibration Point (ppm)'
        },
        calibration_point_high: {
          type: 'number',
          title: 'High Calibration Point (ppm)'
        },
        probe_type: {
          type: 'integer',
          enum: [0, 1, 2],
          title: 'Probe Type',
          description: '0=Standard, 1=High_Range, 2=Low_Range'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['tds_ppm', 'ec_value', 'temperature', 'timestamp']
    },
    uiSchema: {
      tds_ppm: { 'ui:widget': 'updown', 'ui:help': 'Total dissolved solids' },
      ec_value: { 'ui:widget': 'updown', 'ui:help': 'Electrical conductivity' },
      salinity: { 'ui:widget': 'updown', 'ui:help': 'Salt content' },
      temperature: { 'ui:widget': 'updown', 'ui:help': 'Water temperature' },
      temperature_compensation: { 'ui:widget': 'checkbox', 'ui:help': 'Auto temperature compensation' },
      calibration_point_low: { 'ui:widget': 'updown', 'ui:help': 'Low calibration standard' },
      calibration_point_high: { 'ui:widget': 'updown', 'ui:help': 'High calibration standard' },
      probe_type: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Standard Range', 'High Range (>2000ppm)', 'Low Range (<1000ppm)']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      tds_ppm: 245,
      ec_value: 490,
      salinity: 0.24,
      temperature: 22.5,
      temperature_compensation: true,
      calibration_point_low: 84,
      calibration_point_high: 1413,
      probe_type: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'water_level_ultrasonic',
    name: 'Ultrasonic Water Level Sensor',
    category: 'water',
    subcategory: 'level',
    description: 'Ultrasonic sensor for non-contact water level measurement',
    tags: ['ultrasonic', 'water_level', 'tank', 'reservoir', 'non_contact'],
    icon: getSensorIcon('water_level'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        distance_to_surface: {
          type: 'number',
          minimum: 2,
          maximum: 400,
          title: 'Distance to Surface (cm)'
        },
        water_level: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Water Level (%)'
        },
        tank_height: {
          type: 'number',
          title: 'Tank Height (cm)'
        },
        volume_liters: {
          type: 'number',
          title: 'Volume (L)'
        },
        level_status: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          title: 'Level Status',
          description: '0=Empty, 1=Low, 2=Normal, 3=High, 4=Overflow'
        },
        alarm_low_level: {
          type: 'number',
          title: 'Low Level Alarm (%)'
        },
        alarm_high_level: {
          type: 'number',
          title: 'High Level Alarm (%)'
        },
        sensor_offset: {
          type: 'number',
          title: 'Sensor Mounting Offset (cm)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['distance_to_surface', 'water_level', 'timestamp']
    },
    uiSchema: {
      distance_to_surface: { 'ui:widget': 'updown', 'ui:help': 'Ultrasonic distance measurement' },
      water_level: { 'ui:widget': 'updown', 'ui:help': 'Calculated water level percentage' },
      tank_height: { 'ui:widget': 'updown', 'ui:help': 'Total tank height' },
      volume_liters: { 'ui:widget': 'updown', 'ui:help': 'Calculated volume' },
      level_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Empty', 'Low Level', 'Normal Level', 'High Level', 'Overflow']
        }
      },
      alarm_low_level: { 'ui:widget': 'updown', 'ui:help': 'Low level alarm threshold' },
      alarm_high_level: { 'ui:widget': 'updown', 'ui:help': 'High level alarm threshold' },
      sensor_offset: { 'ui:widget': 'updown', 'ui:help': 'Distance from sensor to tank top' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      distance_to_surface: 45.2,
      water_level: 67.5,
      tank_height: 150,
      volume_liters: 1125,
      level_status: 2,
      alarm_low_level: 15,
      alarm_high_level: 85,
      sensor_offset: 5,
      timestamp: new Date().toISOString()
    }
  }
];
