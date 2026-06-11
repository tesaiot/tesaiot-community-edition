/**
 * Navigation & Location Sensor Templates
 *
 * @module sensorCatalog/sensors/navigation
 * @description Sensor definitions for navigation, positioning, and location tracking
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 3 (2025-10-02)
 *
 * Contains:
 * - Gyroscope (MPU6050, BMI270) - 3-axis angular velocity
 * - LIDAR Distance (MaxBotix, TF-Luna) - Laser-based ranging
 * - GPS Module (NEO-6M, NEO-8M) - Global positioning
 *
 * Standards: IEEE 1451, ISO 16063-15, IEC 60825-1, ISO 11898, NMEA 0183, RTCM 3.x
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const navigationSensors: SensorTemplate[] = [
  {
    id: 'gyroscope',
    name: 'Gyroscope',
    category: 'motion',
    subcategory: 'rotation',
    description: '3-axis gyroscope for angular velocity measurement (MPU6050, BMI270)',
    manufacturer: 'InvenSense / Bosch',
    tags: ['gyroscope', 'angular', 'rotation', 'motion', 'mpu6050', 'bmi270', 'drone', 'robotics'],
    icon: getSensorIcon('gyroscope'),
    standards: ['IEEE 1451', 'ISO 16063-15'],
    schema: {
      type: 'object',
      properties: {
        angular_velocity_x: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'X-axis Angular Velocity'
        },
        angular_velocity_y: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'Y-axis Angular Velocity'
        },
        angular_velocity_z: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'Z-axis Angular Velocity'
        },
        unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Angular Velocity Unit',
          description: '0=°/s, 1=rad/s, 2=rpm'
        },
        temperature: {
          type: 'number',
          title: 'Internal Temperature'
        },
        calibration_status: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Calibration Status',
          description: '0=Uncalibrated, 1=Partially, 2=Good, 3=Excellent'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['angular_velocity_x', 'angular_velocity_y', 'angular_velocity_z', 'timestamp']
    },
    uiSchema: {
      angular_velocity_x: { 'ui:widget': 'updown', 'ui:help': 'Roll rotation rate' },
      angular_velocity_y: { 'ui:widget': 'updown', 'ui:help': 'Pitch rotation rate' },
      angular_velocity_z: { 'ui:widget': 'updown', 'ui:help': 'Yaw rotation rate' },
      unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['°/s (degrees/second)', 'rad/s (radians/second)', 'rpm (revolutions/minute)']
        }
      },
      temperature: { 'ui:widget': 'text', 'ui:readonly': true },
      calibration_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Uncalibrated', 'Partially Calibrated', 'Well Calibrated', 'Fully Calibrated']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      angular_velocity_x: 0.5,
      angular_velocity_y: -1.2,
      angular_velocity_z: 0.1,
      unit: 0,
      temperature: 25.5,
      calibration_status: 2,
      timestamp: new Date().toISOString()
    },
    units: { angular_velocity: '°/s', temperature: '°C' },
    ranges: {
      angular_velocity_x: { min: -2000, max: 2000 },
      angular_velocity_y: { min: -2000, max: 2000 },
      angular_velocity_z: { min: -2000, max: 2000 }
    },
    accuracy: { angular_velocity: 0.1 }
  },
  {
    id: 'lidar_sensor',
    name: 'LIDAR Distance Sensor',
    category: 'distance',
    subcategory: 'laser',
    description: 'Laser-based distance measurement for autonomous systems (MaxBotix, TF-Luna)',
    manufacturer: 'MaxBotix / Benewake',
    tags: ['lidar', 'laser', 'distance', 'autonomous', 'maxbotix', 'tf-luna', 'robotics', 'mapping'],
    icon: getSensorIcon('lidar_sensor'),
    standards: ['IEC 60825-1', 'ISO 11898'],
    schema: {
      type: 'object',
      properties: {
        distance: {
          type: 'number',
          minimum: 0.1,
          maximum: 12,
          title: 'Distance Measurement'
        },
        distance_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 1,
          title: 'Distance Unit',
          description: '0=cm, 1=m, 2=ft'
        },
        angle: {
          type: 'number',
          minimum: 0,
          maximum: 360,
          title: 'Scan Angle'
        },
        signal_strength: {
          type: 'integer',
          minimum: 0,
          maximum: 255,
          title: 'Signal Strength'
        },
        range_status: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          default: 0,
          title: 'Range Status',
          description: '0=Valid, 1=Sigma_Fail, 2=Signal_Fail, 3=Min_Range_Fail, 4=Phase_Fail'
        },
        measurement_time: {
          type: 'number',
          title: 'Measurement Time (ms)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['distance', 'signal_strength', 'timestamp']
    },
    uiSchema: {
      distance: { 'ui:widget': 'updown', 'ui:help': 'Precise laser distance measurement' },
      distance_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Centimeters', 'Meters', 'Feet']
        }
      },
      angle: { 'ui:widget': 'updown', 'ui:help': 'Scan angle for rotating LIDAR' },
      signal_strength: { 'ui:widget': 'range', 'ui:help': 'Signal quality indicator' },
      range_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Valid Reading', 'Sigma Fail', 'Signal Fail', 'Min Range Fail', 'Phase Fail']
        }
      },
      measurement_time: { 'ui:widget': 'text', 'ui:readonly': true },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      distance: 2.45,
      distance_unit: 1,
      angle: 45.2,
      signal_strength: 150,
      range_status: 0,
      measurement_time: 33,
      timestamp: new Date().toISOString()
    },
    units: { distance: 'm', angle: '°', signal_strength: 'arbitrary', measurement_time: 'ms' },
    ranges: { distance: { min: 0.1, max: 12 }, signal_strength: { min: 0, max: 255 } },
    accuracy: { distance: 0.01 }
  },
  {
    id: 'gps_module',
    name: 'GPS Module',
    category: 'navigation',
    subcategory: 'position',
    description: 'Global positioning system for location services (NEO-6M, NEO-8M)',
    manufacturer: 'u-blox',
    tags: ['gps', 'location', 'coordinates', 'neo-6m', 'neo-8m', 'navigation', 'tracking'],
    icon: getSensorIcon('gps_module'),
    standards: ['NMEA 0183', 'RTCM 3.x'],
    schema: {
      type: 'object',
      properties: {
        latitude: {
          type: 'number',
          minimum: -90,
          maximum: 90,
          title: 'Latitude'
        },
        longitude: {
          type: 'number',
          minimum: -180,
          maximum: 180,
          title: 'Longitude'
        },
        altitude: {
          type: 'number',
          title: 'Altitude Above Sea Level'
        },
        altitude_unit: {
          type: 'integer',
          enum: [0, 1],
          default: 0,
          title: 'Altitude Unit',
          description: '0=m, 1=ft'
        },
        satellites: {
          type: 'integer',
          minimum: 0,
          maximum: 32,
          title: 'Satellites in View'
        },
        fix_quality: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5],
          default: 0,
          title: 'Fix Quality',
          description: '0=Invalid, 1=GPS, 2=DGPS, 3=PPS, 4=RTK, 5=Float_RTK'
        },
        speed: {
          type: 'number',
          minimum: 0,
          title: 'Ground Speed'
        },
        speed_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Speed Unit',
          description: '0=km/h, 1=mph, 2=m/s'
        },
        heading: {
          type: 'number',
          minimum: 0,
          maximum: 360,
          title: 'Course Over Ground'
        },
        hdop: {
          type: 'number',
          title: 'Horizontal Dilution of Precision'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['latitude', 'longitude', 'satellites', 'fix_quality', 'timestamp']
    },
    uiSchema: {
      latitude: { 'ui:widget': 'updown', 'ui:help': 'Decimal degrees (-90 to 90)' },
      longitude: { 'ui:widget': 'updown', 'ui:help': 'Decimal degrees (-180 to 180)' },
      altitude: { 'ui:widget': 'updown', 'ui:help': 'Height above sea level' },
      altitude_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Meters', 'Feet']
        }
      },
      satellites: { 'ui:widget': 'updown', 'ui:help': 'Number of satellites used' },
      fix_quality: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['No Fix', 'GPS Fix', 'DGPS Fix', 'PPS Fix', 'RTK Fix', 'Float RTK']
        }
      },
      speed: { 'ui:widget': 'updown', 'ui:help': 'Movement speed' },
      speed_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['km/h', 'mph', 'm/s']
        }
      },
      heading: { 'ui:widget': 'updown', 'ui:help': 'Direction of movement (degrees)' },
      hdop: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Position accuracy indicator' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      latitude: 13.7563,
      longitude: 100.5018,
      altitude: 15,
      altitude_unit: 0,
      satellites: 8,
      fix_quality: 1,
      speed: 0,
      speed_unit: 0,
      heading: 0,
      hdop: 1.2,
      timestamp: new Date().toISOString()
    },
    units: { latitude: '°', longitude: '°', altitude: 'm', speed: 'km/h', heading: '°' },
    ranges: {
      latitude: { min: -90, max: 90 },
      longitude: { min: -180, max: 180 },
      satellites: { min: 0, max: 32 }
    },
    accuracy: { latitude: 0.000001, longitude: 0.000001, altitude: 1 }
  }
];
