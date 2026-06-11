import { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

/**
 * Advanced Motion & Navigation Sensors
 *
 * Standards Compliance:
 * - IEEE 1451: Smart transducer interface
 * - ISO/IEC 21451: Information technology
 * - NMEA 0183: GPS communication protocol
 *
 * Includes:
 * - MPU6050 6-Axis IMU (accelerometer + gyroscope)
 * - VL53L0X Time-of-Flight Distance Sensor (laser ranging)
 * - NEO-8M GPS Module (GNSS positioning)
 */
export const advancedMotionSensors: SensorTemplate[] = [
  {
    id: 'mpu6050_imu',
    name: 'MPU6050 6-Axis IMU',
    category: 'motion',
    subcategory: 'inertial',
    description: 'InvenSense MPU6050 6-axis accelerometer and gyroscope',
    manufacturer: 'TDK InvenSense',
    tags: ['mpu6050', 'imu', 'accelerometer', 'gyroscope', '6axis', 'invensense'],
    icon: getSensorIcon('gyroscope'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        accel_x: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'Acceleration X (g)'
        },
        accel_y: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'Acceleration Y (g)'
        },
        accel_z: {
          type: 'number',
          minimum: -16,
          maximum: 16,
          title: 'Acceleration Z (g)'
        },
        gyro_x: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'Gyroscope X (°/s)'
        },
        gyro_y: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'Gyroscope Y (°/s)'
        },
        gyro_z: {
          type: 'number',
          minimum: -2000,
          maximum: 2000,
          title: 'Gyroscope Z (°/s)'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          title: 'Die Temperature (°C)'
        },
        accel_range: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Accelerometer Range',
          description: '0=±2g, 1=±4g, 2=±8g, 3=±16g'
        },
        gyro_range: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Gyroscope Range',
          description: '0=±250°/s, 1=±500°/s, 2=±1000°/s, 3=±2000°/s'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z', 'timestamp']
    },
    uiSchema: {
      accel_x: { 'ui:widget': 'updown', 'ui:help': 'X-axis acceleration' },
      accel_y: { 'ui:widget': 'updown', 'ui:help': 'Y-axis acceleration' },
      accel_z: { 'ui:widget': 'updown', 'ui:help': 'Z-axis acceleration' },
      gyro_x: { 'ui:widget': 'updown', 'ui:help': 'X-axis angular velocity' },
      gyro_y: { 'ui:widget': 'updown', 'ui:help': 'Y-axis angular velocity' },
      gyro_z: { 'ui:widget': 'updown', 'ui:help': 'Z-axis angular velocity' },
      temperature: { 'ui:widget': 'updown', 'ui:help': 'Internal die temperature' },
      accel_range: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['±2g', '±4g', '±8g', '±16g']
        }
      },
      gyro_range: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['±250°/s', '±500°/s', '±1000°/s', '±2000°/s']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      accel_x: 0.12,
      accel_y: -0.05,
      accel_z: 9.78,
      gyro_x: 1.2,
      gyro_y: -0.8,
      gyro_z: 0.3,
      temperature: 28.5,
      accel_range: 0,
      gyro_range: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'vl53l0x_lidar',
    name: 'VL53L0X Time-of-Flight Distance Sensor',
    category: 'distance',
    subcategory: 'lidar',
    description: 'STMicroelectronics VL53L0X laser time-of-flight ranging sensor',
    manufacturer: 'STMicroelectronics',
    tags: ['vl53l0x', 'tof', 'lidar', 'laser', 'ranging', 'stm'],
    icon: getSensorIcon('lidar_sensor'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        distance: {
          type: 'number',
          minimum: 30,
          maximum: 2000,
          title: 'Distance (mm)'
        },
        distance_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 2,
          title: 'Distance Unit',
          description: '0=cm, 1=m, 2=mm'
        },
        range_status: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          title: 'Range Status',
          description: '0=Valid, 1=Sigma_Fail, 2=Signal_Fail, 3=Min_Range_Fail, 4=Phase_Fail'
        },
        signal_rate: {
          type: 'number',
          title: 'Signal Rate (MCPS)'
        },
        ambient_rate: {
          type: 'number',
          title: 'Ambient Light Rate (MCPS)'
        },
        effective_spad_count: {
          type: 'number',
          title: 'Effective SPAD Count'
        },
        sigma_estimate: {
          type: 'number',
          title: 'Sigma Estimate (mm)'
        },
        measurement_mode: {
          type: 'integer',
          enum: [0, 1, 2],
          title: 'Measurement Mode',
          description: '0=Single, 1=Continuous, 2=Timed'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['distance', 'range_status', 'timestamp']
    },
    uiSchema: {
      distance: { 'ui:widget': 'updown', 'ui:help': 'Measured distance' },
      distance_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['cm', 'm', 'mm']
        }
      },
      range_status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Valid', 'Sigma Fail', 'Signal Fail', 'Min Range Fail', 'Phase Fail']
        }
      },
      signal_rate: { 'ui:widget': 'updown', 'ui:help': 'Signal return rate' },
      ambient_rate: { 'ui:widget': 'updown', 'ui:help': 'Ambient light interference' },
      effective_spad_count: { 'ui:widget': 'updown', 'ui:help': 'Effective photodiode count' },
      sigma_estimate: { 'ui:widget': 'updown', 'ui:help': 'Standard deviation estimate' },
      measurement_mode: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Single Shot', 'Continuous', 'Timed']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      distance: 456,
      distance_unit: 2,
      range_status: 0,
      signal_rate: 1.25,
      ambient_rate: 0.12,
      effective_spad_count: 178.5,
      sigma_estimate: 15.2,
      measurement_mode: 1,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'neo_8m_gps',
    name: 'NEO-8M GPS Module',
    category: 'navigation',
    subcategory: 'gps',
    description: 'u-blox NEO-8M concurrent GNSS receiver module',
    manufacturer: 'u-blox',
    tags: ['neo-8m', 'gps', 'gnss', 'ublox', 'location', 'positioning'],
    icon: getSensorIcon('gps_module'),
    standards: ['IEEE 1451', 'NMEA 0183'],
    schema: {
      type: 'object',
      properties: {
        latitude: {
          type: 'number',
          minimum: -90,
          maximum: 90,
          title: 'Latitude (°)'
        },
        longitude: {
          type: 'number',
          minimum: -180,
          maximum: 180,
          title: 'Longitude (°)'
        },
        altitude: {
          type: 'number',
          title: 'Altitude (m)'
        },
        speed: {
          type: 'number',
          minimum: 0,
          title: 'Speed (km/h)'
        },
        course: {
          type: 'number',
          minimum: 0,
          maximum: 360,
          title: 'Course (°)'
        },
        satellites: {
          type: 'integer',
          minimum: 0,
          maximum: 32,
          title: 'Satellites in Use'
        },
        hdop: {
          type: 'number',
          title: 'Horizontal Dilution of Precision'
        },
        fix_quality: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5],
          title: 'Fix Quality',
          description: '0=Invalid, 1=GPS, 2=DGPS, 3=PPS, 4=RTK, 5=Float_RTK'
        },
        fix_type: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Fix Type',
          description: '0=No_Fix, 1=Dead_Reckoning, 2=2D, 3=3D'
        },
        utc_time: {
          type: 'string',
          format: 'time',
          title: 'UTC Time'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['latitude', 'longitude', 'satellites', 'fix_quality', 'timestamp']
    },
    uiSchema: {
      latitude: { 'ui:widget': 'updown', 'ui:help': 'Latitude coordinate' },
      longitude: { 'ui:widget': 'updown', 'ui:help': 'Longitude coordinate' },
      altitude: { 'ui:widget': 'updown', 'ui:help': 'Altitude above sea level' },
      speed: { 'ui:widget': 'updown', 'ui:help': 'Ground speed' },
      course: { 'ui:widget': 'updown', 'ui:help': 'Course/heading direction' },
      satellites: { 'ui:widget': 'updown', 'ui:help': 'Number of satellites tracked' },
      hdop: { 'ui:widget': 'updown', 'ui:help': 'Position accuracy indicator' },
      fix_quality: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Invalid', 'GPS Fix', 'DGPS Fix', 'PPS Fix', 'RTK Fix', 'Float RTK']
        }
      },
      fix_type: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['No Fix', 'Dead Reckoning', '2D Fix', '3D Fix']
        }
      },
      utc_time: { 'ui:widget': 'time', 'ui:help': 'UTC time from satellites' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      latitude: 13.7563,
      longitude: 100.5018,
      altitude: 12.5,
      speed: 0.0,
      course: 0.0,
      satellites: 8,
      hdop: 1.2,
      fix_quality: 1,
      fix_type: 3,
      utc_time: '14:23:45',
      timestamp: new Date().toISOString()
    }
  }
];
