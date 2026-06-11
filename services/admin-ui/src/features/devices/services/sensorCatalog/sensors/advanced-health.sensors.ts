import { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

/**
 * Advanced Health & Medical Sensors
 *
 * Standards Compliance:
 * - IEEE 1451: Smart transducer interface
 * - ISO/IEC 80601-2-61: Pulse oximeters requirements
 * - ISO 80601-2-56: Clinical thermometers
 *
 * Includes:
 * - MAX30102 SpO2 & Heart Rate Sensor (pulse oximetry with PPG)
 * - MLX90614 Non-Contact Temperature (infrared thermometer)
 */
export const advancedHealthSensors: SensorTemplate[] = [
  {
    id: 'max30102_spo2',
    name: 'MAX30102 SpO2 & Heart Rate Sensor',
    category: 'health',
    subcategory: 'cardiovascular',
    description: 'Maxim MAX30102 pulse oximetry and heart rate sensor',
    manufacturer: 'Maxim Integrated',
    tags: ['max30102', 'spo2', 'heart_rate', 'pulse_oximetry', 'ppg', 'cardiovascular'],
    icon: getSensorIcon('heart_rate'),
    standards: ['IEEE 1451', 'ISO/IEC 80601-2-61'],
    schema: {
      type: 'object',
      properties: {
        heart_rate_bpm: {
          type: 'number',
          minimum: 30,
          maximum: 200,
          title: 'Heart Rate (BPM)'
        },
        spo2_percent: {
          type: 'number',
          minimum: 70,
          maximum: 100,
          title: 'SpO2 (%)'
        },
        red_led_value: {
          type: 'number',
          title: 'Red LED Raw Value'
        },
        ir_led_value: {
          type: 'number',
          title: 'IR LED Raw Value'
        },
        perfusion_index: {
          type: 'number',
          title: 'Perfusion Index (%)'
        },
        signal_quality: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          title: 'Signal Quality',
          description: '0=Poor, 1=Fair, 2=Good, 3=Excellent'
        },
        finger_detected: {
          type: 'boolean',
          title: 'Finger Detected'
        },
        led_current_red: {
          type: 'number',
          title: 'Red LED Current (mA)'
        },
        led_current_ir: {
          type: 'number',
          title: 'IR LED Current (mA)'
        },
        sample_rate: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5, 6, 7],
          title: 'Sample Rate',
          description: '0=50sps, 7=3200sps'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['heart_rate_bpm', 'spo2_percent', 'finger_detected', 'timestamp']
    },
    uiSchema: {
      heart_rate_bpm: { 'ui:widget': 'updown', 'ui:help': 'Heart rate in beats per minute' },
      spo2_percent: { 'ui:widget': 'updown', 'ui:help': 'Blood oxygen saturation' },
      red_led_value: { 'ui:widget': 'updown', 'ui:help': 'Raw red LED photodiode value' },
      ir_led_value: { 'ui:widget': 'updown', 'ui:help': 'Raw infrared LED photodiode value' },
      perfusion_index: { 'ui:widget': 'updown', 'ui:help': 'Peripheral perfusion strength' },
      signal_quality: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Poor Signal', 'Fair Signal', 'Good Signal', 'Excellent Signal']
        }
      },
      finger_detected: { 'ui:widget': 'checkbox', 'ui:help': 'Finger presence detection' },
      led_current_red: { 'ui:widget': 'updown', 'ui:help': 'Red LED drive current' },
      led_current_ir: { 'ui:widget': 'updown', 'ui:help': 'IR LED drive current' },
      sample_rate: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['50 sps', '100 sps', '200 sps', '400 sps', '800 sps', '1000 sps', '1600 sps', '3200 sps']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      heart_rate_bpm: 72,
      spo2_percent: 98.5,
      red_led_value: 145632,
      ir_led_value: 89456,
      perfusion_index: 3.2,
      signal_quality: 2,
      finger_detected: true,
      led_current_red: 6.4,
      led_current_ir: 6.4,
      sample_rate: 2,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'mlx90614_body_temp',
    name: 'MLX90614 Non-Contact Temperature',
    category: 'health',
    subcategory: 'temperature',
    description: 'Melexis MLX90614 infrared thermometer for non-contact body temperature',
    manufacturer: 'Melexis',
    tags: ['mlx90614', 'infrared', 'non_contact', 'body_temperature', 'fever', 'thermometer'],
    icon: getSensorIcon('temperature_basic'),
    standards: ['IEEE 1451', 'ISO 80601-2-56'],
    schema: {
      type: 'object',
      properties: {
        object_temp: {
          type: 'number',
          minimum: -70,
          maximum: 125,
          title: 'Object Temperature (°C)'
        },
        ambient_temp: {
          type: 'number',
          minimum: -40,
          maximum: 85,
          title: 'Ambient Temperature (°C)'
        },
        emissivity: {
          type: 'number',
          minimum: 0.1,
          maximum: 1.0,
          title: 'Emissivity Setting'
        },
        body_temp_corrected: {
          type: 'number',
          title: 'Body Temperature Corrected (°C)'
        },
        fever_detected: {
          type: 'boolean',
          title: 'Fever Detected (>37.5°C)'
        },
        measurement_distance: {
          type: 'number',
          title: 'Measurement Distance (cm)'
        },
        temperature_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Temperature Unit',
          description: '0=°C, 1=°F, 2=K'
        },
        accuracy_class: {
          type: 'integer',
          enum: [0, 1, 2],
          title: 'Accuracy Class',
          description: '0=Medical, 1=Industrial, 2=General'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['object_temp', 'ambient_temp', 'timestamp']
    },
    uiSchema: {
      object_temp: { 'ui:widget': 'updown', 'ui:help': 'Measured object/body temperature' },
      ambient_temp: { 'ui:widget': 'updown', 'ui:help': 'Ambient environment temperature' },
      emissivity: { 'ui:widget': 'updown', 'ui:help': 'Material emissivity factor' },
      body_temp_corrected: { 'ui:widget': 'updown', 'ui:help': 'Body temperature with corrections' },
      fever_detected: { 'ui:widget': 'checkbox', 'ui:help': 'Automatic fever detection' },
      measurement_distance: { 'ui:widget': 'updown', 'ui:help': 'Distance to object' },
      temperature_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['°C (Celsius)', '°F (Fahrenheit)', 'K (Kelvin)']
        }
      },
      accuracy_class: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Medical Grade', 'Industrial Grade', 'General Purpose']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      object_temp: 36.8,
      ambient_temp: 23.2,
      emissivity: 0.98,
      body_temp_corrected: 36.9,
      fever_detected: false,
      measurement_distance: 5,
      temperature_unit: 0,
      accuracy_class: 0,
      timestamp: new Date().toISOString()
    }
  }
];
