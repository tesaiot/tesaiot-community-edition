/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import type { SensorTemplate } from './sensorCatalog/types/sensor.types';
import { getSensorIcon } from '../components/SensorIcons';

// Infineon XENSIV™ Environmental Sensors
export const infineonXensivSensors: SensorTemplate[] = [
  {
    id: 'xensiv_dps368',
    name: 'XENSIV™ DPS368 Pressure Sensor',
    category: 'environmental',
    subcategory: 'pressure',
    description: 'Ultra-low power digital barometric pressure sensor with high accuracy and temperature measurement',
    manufacturer: 'Infineon',
    tags: ['pressure', 'temperature', 'barometric', 'dps368', 'xensiv', 'infineon', 'altitude'],
    icon: getSensorIcon('barometric_pressure'),
    standards: ['I2C', 'SPI'],
    specifications: {
      pressure_range: '300-1200 hPa',
      pressure_accuracy: '±0.002 hPa',
      temperature_range: '-40 to 85°C',
      temperature_accuracy: '±0.5°C',
      resolution: '24-bit',
      sampling_rate: 'up to 128 Hz',
      power_consumption: '1.7μA @ 1Hz'
    },
    schema: {
      type: 'object',
      properties: {
        pressure: {
          type: 'number',
          minimum: 300,
          maximum: 1200,
          description: 'Atmospheric pressure in hPa'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          description: 'Temperature in °C'
        },
        altitude: {
          type: 'number',
          description: 'Calculated altitude in meters (optional)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['pressure', 'temperature', 'timestamp']
    },
    uiSchema: {
      pressure: {
        'ui:widget': 'updown',
        'ui:title': 'Pressure (hPa)',
        'ui:help': 'Barometric pressure reading'
      },
      temperature: {
        'ui:widget': 'updown',
        'ui:title': 'Temperature (°C)'
      },
      altitude: {
        'ui:widget': 'text',
        'ui:readonly': true,
        'ui:help': 'Calculated from pressure'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      pressure: 1004.21,
      temperature: 26.43,
      altitude: 156.2,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_pas_co2',
    name: 'XENSIV™ PAS CO2 Sensor',
    category: 'environmental',
    subcategory: 'gas',
    description: 'Photoacoustic CO₂ sensor with integrated temperature and humidity measurement',
    manufacturer: 'Infineon',
    tags: ['co2', 'temperature', 'humidity', 'pas', 'xensiv', 'infineon', 'air-quality', 'photoacoustic'],
    icon: getSensorIcon('co2_sensor'),
    standards: ['I2C', 'UART'],
    specifications: {
      co2_range: '0-40000 ppm',
      co2_accuracy: '±30 ppm ±3%',
      temperature_range: '-40 to 85°C',
      humidity_range: '0-100% RH',
      response_time: '<60s',
      power_consumption: '15mA average'
    },
    schema: {
      type: 'object',
      properties: {
        co2: {
          type: 'integer',
          minimum: 0,
          maximum: 40000,
          description: 'CO₂ concentration in ppm'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          description: 'Temperature in °C'
        },
        humidity: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          description: 'Relative humidity in %'
        },
        air_quality: {
          type: 'string',
          enum: ['excellent', 'good', 'moderate', 'poor', 'hazardous'],
          description: 'Calculated air quality level'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['co2', 'temperature', 'humidity', 'timestamp']
    },
    uiSchema: {
      co2: {
        'ui:widget': 'updown',
        'ui:title': 'CO₂ (ppm)',
        'ui:help': 'Carbon dioxide concentration'
      },
      temperature: {
        'ui:widget': 'updown',
        'ui:title': 'Temperature (°C)'
      },
      humidity: {
        'ui:widget': 'updown',
        'ui:title': 'Humidity (%RH)'
      },
      air_quality: {
        'ui:widget': 'select',
        'ui:title': 'Air Quality'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      co2: 538,
      temperature: 25.31,
      humidity: 38.7,
      air_quality: 'good',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_bgt60ltr11aip',
    name: 'XENSIV™ BGT60LTR11AIP 60GHz Radar',
    category: 'motion',
    subcategory: 'radar',
    description: '60GHz radar sensor for presence detection, motion sensing, and vital signs monitoring',
    manufacturer: 'Infineon',
    tags: ['radar', 'motion', 'presence', '60ghz', 'xensiv', 'infineon', 'mmwave', 'vital-signs'],
    icon: getSensorIcon('radar_sensor'),
    standards: ['SPI'],
    specifications: {
      frequency: '60-64 GHz',
      detection_range: '0.3-5m',
      field_of_view: '±60° azimuth, ±60° elevation',
      motion_sensitivity: 'sub-mm',
      power_consumption: '5mW typical',
      applications: 'presence, motion, vital signs'
    },
    schema: {
      type: 'object',
      properties: {
        motion: {
          type: 'boolean'
        },
        presence: {
          type: 'boolean'
        },
        direction: {
          type: 'string',
          enum: ['approaching', 'receding', 'stationary', 'unknown'],
          description: 'Motion direction'
        },
        distance: {
          type: 'number',
          minimum: 0.3,
          maximum: 5,
          description: 'Distance to target in meters'
        },
        velocity: {
          type: 'number',
          description: 'Target velocity in m/s'
        },
        vital_signs: {
          type: 'object',
          properties: {
            breathing_rate: { type: 'number', description: 'Breaths per minute' },
            heart_rate: { type: 'number', description: 'Beats per minute' }
          },
          description: 'Optional vital signs data'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['motion', 'presence', 'timestamp']
    },
    uiSchema: {
      motion: {
        'ui:widget': 'checkbox',
        'ui:title': 'Motion Detected',
        'ui:help': 'Indicates if motion is currently detected'
      },
      presence: {
        'ui:widget': 'checkbox',
        'ui:title': 'Presence Detected',
        'ui:help': 'Indicates if presence is currently detected'
      },
      direction: {
        'ui:widget': 'select',
        'ui:title': 'Direction'
      },
      distance: {
        'ui:widget': 'updown',
        'ui:title': 'Distance (m)'
      },
      velocity: {
        'ui:widget': 'text',
        'ui:title': 'Velocity (m/s)'
      },
      vital_signs: {
        'ui:field': 'object',
        'ui:collapsible': true
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      motion: true,
      presence: true,
      direction: 'approaching',
      distance: 1.4,
      velocity: 0.5,
      vital_signs: {
        breathing_rate: 16,
        heart_rate: 72
      },
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_bmi270',
    name: 'XENSIV™ BMI270 6-Axis IMU',
    category: 'motion',
    subcategory: 'imu',
    description: 'Ultra-low power 6-axis IMU with accelerometer and gyroscope optimized for wearables',
    manufacturer: 'Infineon/Bosch',
    tags: ['imu', 'accelerometer', 'gyroscope', '6-axis', 'xensiv', 'infineon', 'bmi270', 'wearable'],
    icon: getSensorIcon('accelerometer'),
    standards: ['I2C', 'SPI'],
    specifications: {
      accel_range: '±2/±4/±8/±16 g',
      gyro_range: '±125/±250/±500/±1000/±2000 °/s',
      resolution: '16-bit',
      sampling_rate: 'up to 6.4 kHz',
      power_consumption: '0.7mA typical',
      features: 'step counter, activity recognition'
    },
    schema: {
      type: 'object',
      properties: {
        accel: {
          type: 'object',
          properties: {
            x: { type: 'number', minimum: -16, maximum: 16 },
            y: { type: 'number', minimum: -16, maximum: 16 },
            z: { type: 'number', minimum: -16, maximum: 16 }
          },
          required: ['x', 'y', 'z'],
          description: 'Acceleration in g'
        },
        gyro: {
          type: 'object',
          properties: {
            x: { type: 'number', minimum: -2000, maximum: 2000 },
            y: { type: 'number', minimum: -2000, maximum: 2000 },
            z: { type: 'number', minimum: -2000, maximum: 2000 }
          },
          required: ['x', 'y', 'z'],
          description: 'Angular velocity in °/s'
        },
        temperature: {
          type: 'number',
          description: 'IMU temperature in °C'
        },
        step_count: {
          type: 'integer',
          description: 'Pedometer step count'
        },
        activity: {
          type: 'string',
          enum: ['still', 'walking', 'running', 'cycling', 'unknown'],
          description: 'Detected activity'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['accel', 'gyro', 'timestamp']
    },
    uiSchema: {
      accel: {
        'ui:field': 'object',
        'ui:title': 'Acceleration (g)',
        x: { 'ui:widget': 'text' },
        y: { 'ui:widget': 'text' },
        z: { 'ui:widget': 'text' }
      },
      gyro: {
        'ui:field': 'object',
        'ui:title': 'Gyroscope (°/s)',
        x: { 'ui:widget': 'text' },
        y: { 'ui:widget': 'text' },
        z: { 'ui:widget': 'text' }
      },
      temperature: {
        'ui:widget': 'text',
        'ui:title': 'Temperature (°C)'
      },
      step_count: {
        'ui:widget': 'text',
        'ui:title': 'Steps'
      },
      activity: {
        'ui:widget': 'select',
        'ui:title': 'Activity'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      accel: { x: -0.02, y: 0.98, z: 9.81 },
      gyro: { x: 0.001, y: -0.002, z: 0.0005 },
      temperature: 28.5,
      step_count: 5432,
      activity: 'walking',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_bmm350',
    name: 'XENSIV™ BMM350 3-Axis Magnetometer',
    category: 'motion',
    subcategory: 'magnetometer',
    description: 'High-performance 3-axis digital geomagnetic sensor for compass and navigation',
    manufacturer: 'Infineon/Bosch',
    tags: ['magnetometer', 'compass', '3-axis', 'xensiv', 'infineon', 'bmm350', 'navigation'],
    icon: getSensorIcon('magnetometer'),
    standards: ['I2C', 'SPI'],
    specifications: {
      range: '±2000 μT',
      resolution: '0.08 μT',
      noise: '140 nT RMS',
      sampling_rate: 'up to 400 Hz',
      power_consumption: '1.5mA @ 100Hz',
      features: 'temperature compensation'
    },
    schema: {
      type: 'object',
      properties: {
        mag: {
          type: 'object',
          properties: {
            x: { type: 'number', minimum: -2000, maximum: 2000 },
            y: { type: 'number', minimum: -2000, maximum: 2000 },
            z: { type: 'number', minimum: -2000, maximum: 2000 }
          },
          required: ['x', 'y', 'z'],
          description: 'Magnetic field in μT'
        },
        heading: {
          type: 'number',
          minimum: 0,
          maximum: 360,
          description: 'Compass heading in degrees'
        },
        temperature: {
          type: 'number',
          description: 'Sensor temperature in °C'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['mag', 'timestamp']
    },
    uiSchema: {
      mag: {
        'ui:field': 'object',
        'ui:title': 'Magnetic Field (μT)',
        x: { 'ui:widget': 'text' },
        y: { 'ui:widget': 'text' },
        z: { 'ui:widget': 'text' }
      },
      heading: {
        'ui:widget': 'updown',
        'ui:title': 'Heading (°)',
        'ui:help': 'Compass heading in degrees (0-360)'
      },
      temperature: {
        'ui:widget': 'text',
        'ui:title': 'Temperature (°C)'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      mag: { x: 12.3, y: -8.5, z: 4.1 },
      heading: 127.5,
      temperature: 25.2,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_im72d128',
    name: 'XENSIV™ IM72D128 Digital MEMS Microphone',
    category: 'audio',
    subcategory: 'microphone',
    description: 'High-SNR digital MEMS microphone for voice capture and audio analytics',
    manufacturer: 'Infineon',
    tags: ['microphone', 'mems', 'audio', 'xensiv', 'infineon', 'im72d128', 'voice', 'sound'],
    icon: getSensorIcon('microphone'),
    standards: ['PDM', 'I2S'],
    specifications: {
      snr: '72 dB',
      sensitivity: '-26 dBFS',
      frequency_range: '20Hz - 20kHz',
      dynamic_range: '106 dB',
      power_consumption: '1.1mA',
      acoustic_overload: '128 dB SPL'
    },
    schema: {
      type: 'object',
      properties: {
        sound_level_db: {
          type: 'number',
          minimum: 30,
          maximum: 130,
          description: 'Sound pressure level in dB'
        },
        frequency_peak: {
          type: 'number',
          minimum: 20,
          maximum: 20000,
          description: 'Peak frequency in Hz'
        },
        fft_peaks: {
          type: 'array',
          items: { type: 'number' },
          description: 'FFT peak frequencies'
        },
        voice_detected: {
          type: 'boolean',
          description: 'Voice activity detection'
        },
        noise_level: {
          type: 'string',
          enum: ['quiet', 'moderate', 'loud', 'very_loud'],
          description: 'Noise level classification'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['sound_level_db', 'timestamp']
    },
    uiSchema: {
      sound_level_db: {
        'ui:widget': 'updown',
        'ui:title': 'Sound Level (dB)'
      },
      frequency_peak: {
        'ui:widget': 'text',
        'ui:title': 'Peak Frequency (Hz)'
      },
      fft_peaks: {
        'ui:widget': 'hidden'
      },
      voice_detected: {
        'ui:widget': 'checkbox',
        'ui:title': 'Voice Detected'
      },
      noise_level: {
        'ui:widget': 'select',
        'ui:title': 'Noise Level'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      sound_level_db: 65.2,
      frequency_peak: 1200,
      fft_peaks: [100, 1200, 2500],
      voice_detected: true,
      noise_level: 'moderate',
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_dps310',
    name: 'XENSIV™ DPS310 Pressure Sensor',
    category: 'environmental',
    subcategory: 'pressure',
    description: 'High-precision barometric pressure sensor with small footprint for IoT and consumer applications',
    manufacturer: 'Infineon',
    tags: ['pressure', 'temperature', 'barometric', 'dps310', 'xensiv', 'infineon', 'iot'],
    icon: getSensorIcon('barometric_pressure'),
    standards: ['I2C', 'SPI'],
    specifications: {
      pressure_range: '300-1200 hPa',
      pressure_accuracy: '±0.5 hPa',
      temperature_range: '-40 to 85°C',
      temperature_accuracy: '±0.5°C',
      resolution: '24-bit',
      power_consumption: '1.7μA standby'
    },
    schema: {
      type: 'object',
      properties: {
        pressure: {
          type: 'number',
          minimum: 300,
          maximum: 1200,
          description: 'Atmospheric pressure in hPa'
        },
        temperature: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          description: 'Temperature in °C'
        },
        altitude: {
          type: 'number',
          description: 'Calculated altitude in meters (optional)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['pressure', 'temperature', 'timestamp']
    },
    uiSchema: {
      pressure: {
        'ui:widget': 'updown',
        'ui:title': 'Pressure (hPa)',
        'ui:help': 'Barometric pressure reading'
      },
      temperature: {
        'ui:widget': 'updown',
        'ui:title': 'Temperature (°C)'
      },
      altitude: {
        'ui:widget': 'text',
        'ui:readonly': true,
        'ui:help': 'Calculated from pressure'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      pressure: 1013.25,
      temperature: 25.0,
      altitude: 111.2,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'xensiv_tli493d',
    name: 'XENSIV™ TLI493D 3D Magnetic Sensor',
    category: 'motion',
    subcategory: 'magnetometer',
    description: 'Ultra-low power 3D Hall sensor for contactless position sensing in x, y, z dimensions',
    manufacturer: 'Infineon',
    tags: ['magnetometer', '3d', 'hall', 'position', 'xensiv', 'infineon', 'contactless', 'tli493d'],
    icon: getSensorIcon('magnetometer'),
    standards: ['I2C'],
    specifications: {
      magnetic_range: '±130 mT',
      resolution: '12-bit',
      power_consumption: '7 nA minimum',
      update_rate: 'up to 3.2 kHz',
      temperature_range: '-40 to 125°C',
      applications: 'position sensing, joystick, rotary encoder'
    },
    schema: {
      type: 'object',
      properties: {
        mag: {
          type: 'object',
          properties: {
            x: { type: 'number', minimum: -130, maximum: 130 },
            y: { type: 'number', minimum: -130, maximum: 130 },
            z: { type: 'number', minimum: -130, maximum: 130 }
          },
          required: ['x', 'y', 'z'],
          description: 'Magnetic field in mT'
        },
        position: {
          type: 'object',
          properties: {
            angle: { type: 'number', minimum: 0, maximum: 360, description: 'Rotation angle in degrees' },
            distance: { type: 'number', description: 'Distance to magnet in mm' }
          },
          description: 'Calculated position data'
        },
        temperature: {
          type: 'number',
          description: 'Sensor temperature in °C'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['mag', 'timestamp']
    },
    uiSchema: {
      mag: {
        'ui:field': 'object',
        'ui:title': 'Magnetic Field (mT)',
        x: { 'ui:widget': 'text' },
        y: { 'ui:widget': 'text' },
        z: { 'ui:widget': 'text' }
      },
      position: {
        'ui:field': 'object',
        'ui:title': 'Position',
        angle: { 'ui:widget': 'text', 'ui:title': 'Angle (°)' },
        distance: { 'ui:widget': 'text', 'ui:title': 'Distance (mm)' }
      },
      temperature: {
        'ui:widget': 'text',
        'ui:title': 'Temperature (°C)'
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      mag: { x: 45.2, y: -12.8, z: 38.1 },
      position: { angle: 127.5, distance: 5.2 },
      temperature: 28.3,
      timestamp: new Date().toISOString()
    }
  }
];

// Note: SHT35 is actually from Sensirion, not Infineon
// But it's commonly used with Infineon development boards
export const sensirionSHT35: SensorTemplate = {
  id: 'sensirion_sht35',
  name: 'Sensirion SHT35 Temperature/Humidity',
  category: 'environmental',
  subcategory: 'temperature-humidity',
  description: 'High-accuracy digital temperature and humidity sensor (commonly used with Infineon boards)',
  manufacturer: 'Sensirion',
  tags: ['temperature', 'humidity', 'sht35', 'sensirion', 'environmental'],
  icon: getSensorIcon('temperature_humidity'),
  standards: ['I2C'],
  specifications: {
    temperature_range: '-40 to 125°C',
    temperature_accuracy: '±0.1°C',
    humidity_range: '0-100% RH',
    humidity_accuracy: '±1.5% RH',
    resolution: '16-bit',
    response_time: '8s'
  },
  schema: {
    type: 'object',
    properties: {
      temperature: {
        type: 'number',
        minimum: -40,
        maximum: 125,
        description: 'Temperature in °C'
      },
      humidity: {
        type: 'number',
        minimum: 0,
        maximum: 100,
        description: 'Relative humidity in %'
      },
      dew_point: {
        type: 'number',
        description: 'Calculated dew point in °C'
      },
      timestamp: { type: 'string', format: 'date-time' }
    },
    required: ['temperature', 'humidity', 'timestamp']
  },
  uiSchema: {
    temperature: {
      'ui:widget': 'updown',
      'ui:title': 'Temperature (°C)'
    },
    humidity: {
      'ui:widget': 'updown',
      'ui:title': 'Humidity (%RH)'
    },
    dew_point: {
      'ui:widget': 'text',
      'ui:title': 'Dew Point (°C)',
      'ui:readonly': true
    },
    timestamp: { 'ui:widget': 'hidden' }
  },
  exampleData: {
    temperature: 24.95,
    humidity: 40.2,
    dew_point: 10.7,
    timestamp: new Date().toISOString()
  }
};

// Export all sensors including the Sensirion one commonly used with Infineon
export const allInfineonXensivSensors = [
  ...infineonXensivSensors,
  sensirionSHT35
];