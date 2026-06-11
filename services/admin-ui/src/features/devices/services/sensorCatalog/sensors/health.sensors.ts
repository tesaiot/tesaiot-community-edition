import { getSensorIcon } from '../../../components/SensorIcons';
import type { SensorTemplate } from '../types/sensor.types';

/**
 * Health & Wellness Sensors
 *
 * Standards Compliance:
 * - ISO 80601-2-61: Pulse oximeters
 * - ISO 80601-2-56: Clinical thermometers
 * - ISO 15197: Blood glucose monitoring systems
 *
 * Includes:
 * - Heart Rate Sensor
 * - Blood Oxygen Sensor (SpO2)
 * - Body Temperature
 * - Blood Glucose Monitor
 * - Sleep Summary
 * - ECG Summary
 * - EMG Summary
 */
export const healthSensors: SensorTemplate[] = [
  {
    id: 'heart_rate',
    name: 'Heart Rate Sensor',
    category: 'health',
    subcategory: 'vital_signs',
    description: 'Measures heart rate and pulse',
    tags: ['heart', 'pulse', 'bpm', 'health', 'fitness'],
    icon: getSensorIcon('heart_rate'),
    standards: ['ISO 80601-2-61'],
    schema: {
      type: 'object',
      properties: {
        heart_rate: {
          type: 'integer',
          minimum: 30,
          maximum: 250,
          title: 'Heart Rate (BPM)'
        },
        heart_rate_unit: {
          type: 'string',
          enum: ['bpm'],
          default: 'bpm',
          title: 'Heart Rate Unit'
        },
        signal_quality: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Signal Quality (%)'
        },
        motion: {
          type: 'boolean',
          title: 'Motion Detected',
          description: 'Movement affects accuracy'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['heart_rate', 'timestamp']
    },
    uiSchema: {
      heart_rate: { 'ui:widget': 'updown' },
      heart_rate_unit: { 'ui:widget': 'hidden' },
      signal_quality: { 'ui:widget': 'range' },
      motion: { 'ui:widget': 'radio' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      heart_rate: 72,
      signal_quality: 95,
      motion: false,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'blood_oxygen',
    name: 'Blood Oxygen Sensor (SpO2)',
    category: 'health',
    subcategory: 'vital_signs',
    description: 'Measures blood oxygen saturation',
    tags: ['spo2', 'oxygen', 'saturation', 'health', 'pulse-ox'],
    icon: getSensorIcon('blood_oxygen'),
    standards: ['ISO 80601-2-61'],
    schema: {
      type: 'object',
      properties: {
        spo2: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'SpO2 Level (%)'
        },
        spo2_unit: {
          type: 'string',
          enum: ['%'],
          default: '%',
          title: 'SpO2 Unit'
        },
        pulse_rate: {
          type: 'integer',
          minimum: 30,
          maximum: 250,
          title: 'Pulse Rate (BPM)'
        },
        pulse_rate_unit: {
          type: 'string',
          enum: ['bpm'],
          default: 'bpm',
          title: 'Pulse Rate Unit'
        },
        perfusion_index: {
          type: 'number',
          minimum: 0,
          maximum: 20,
          title: 'Perfusion Index'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['spo2', 'timestamp']
    },
    uiSchema: {
      spo2: { 'ui:widget': 'updown' },
      spo2_unit: { 'ui:widget': 'hidden' },
      pulse_rate: { 'ui:widget': 'updown' },
      pulse_rate_unit: { 'ui:widget': 'hidden' },
      perfusion_index: { 'ui:widget': 'updown' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      spo2: 98,
      pulse_rate: 75,
      perfusion_index: 2.5,
      timestamp: new Date().toISOString()
    }
  }
  ,
  {
    id: 'body_temperature',
    name: 'Body Temperature',
    category: 'health',
    subcategory: 'vital_signs',
    description: 'Core/skin temperature measurement',
    tags: ['temperature', 'body', 'health', 'thermometer'],
    icon: getSensorIcon('temperature_basic'),
    standards: ['ISO 80601-2-56'],
    schema: {
      type: 'object',
      properties: {
        temperature: { type: 'number', minimum: 30, maximum: 45, title: 'Temperature' },
        temperature_unit: { type: 'string', enum: ['°C', '°F'], default: '°C' },
        site: { type: 'string', enum: ['oral', 'tympanic', 'axillary', 'rectal', 'temporal', 'core'] },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['temperature', 'timestamp']
    },
    uiSchema: {
      temperature: { 'ui:widget': 'updown' },
      temperature_unit: { 'ui:widget': 'hidden' },
      site: { 'ui:widget': 'select' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: { temperature: 36.8, temperature_unit: '°C', site: 'oral', timestamp: new Date().toISOString() }
  },
  {
    id: 'glucose_monitor',
    name: 'Blood Glucose',
    category: 'health',
    subcategory: 'metabolic',
    description: 'Blood glucose concentration (glucometer/CGM)',
    tags: ['glucose', 'blood sugar', 'diabetes', 'cgm'],
    icon: getSensorIcon('blood_oxygen'),
    standards: ['ISO 15197'],
    schema: {
      type: 'object',
      properties: {
        glucose: { type: 'number', minimum: 0, maximum: 600, title: 'Glucose' },
        glucose_unit: { type: 'string', enum: ['mg/dL', 'mmol/L'], default: 'mg/dL' },
        trend: { type: 'string', enum: ['rising', 'falling', 'steady'] },
        meal: { type: 'string', enum: ['fasting', 'preprandial', 'postprandial', 'random'] },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['glucose', 'timestamp']
    },
    uiSchema: {
      glucose: { 'ui:widget': 'updown' },
      glucose_unit: { 'ui:widget': 'hidden' },
      trend: { 'ui:widget': 'select' },
      meal: { 'ui:widget': 'select' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: { glucose: 108, glucose_unit: 'mg/dL', trend: 'steady', meal: 'random', timestamp: new Date().toISOString() }
  },
  {
    id: 'sleep_summary',
    name: 'Sleep Summary',
    category: 'health',
    subcategory: 'sleep',
    description: 'High-level sleep metrics for the previous period',
    tags: ['sleep', 'stages', 'actigraphy', 'wearable'],
    icon: getSensorIcon('activity_monitor'),
    schema: {
      type: 'object',
      properties: {
        duration_minutes: { type: 'integer', minimum: 0, maximum: 24*60 },
        sleep_efficiency: { type: 'integer', minimum: 0, maximum: 100 },
        stage_light: { type: 'integer', minimum: 0, maximum: 24*60 },
        stage_deep: { type: 'integer', minimum: 0, maximum: 24*60 },
        stage_rem: { type: 'integer', minimum: 0, maximum: 24*60 },
        awakenings: { type: 'integer', minimum: 0, maximum: 60 },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['duration_minutes', 'timestamp']
    },
    uiSchema: {
      duration_minutes: { 'ui:widget': 'updown' },
      sleep_efficiency: { 'ui:widget': 'range' },
      stage_light: { 'ui:widget': 'updown' },
      stage_deep: { 'ui:widget': 'updown' },
      stage_rem: { 'ui:widget': 'updown' },
      awakenings: { 'ui:widget': 'updown' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: { duration_minutes: 420, sleep_efficiency: 92, stage_light: 220, stage_deep: 120, stage_rem: 80, awakenings: 2, timestamp: new Date().toISOString() }
  },
  {
    id: 'ecg_summary',
    name: 'ECG Summary',
    category: 'health',
    subcategory: 'cardiovascular',
    description: 'Summarized ECG metrics (not raw waveform)',
    tags: ['ecg', 'cardiac', 'arrhythmia'],
    icon: getSensorIcon('heart_rate'),
    schema: {
      type: 'object',
      properties: {
        heart_rate_bpm: { type: 'integer', minimum: 30, maximum: 250 },
        rr_interval_ms: { type: 'number', minimum: 200, maximum: 2000 },
        qrs_duration_ms: { type: 'number', minimum: 40, maximum: 200 },
        qt_interval_ms: { type: 'number', minimum: 200, maximum: 700 },
        rhythm: { type: 'string', enum: ['sinus', 'afib', 'svt', 'vt', 'unknown'] },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['heart_rate_bpm', 'timestamp']
    },
    uiSchema: {
      heart_rate_bpm: { 'ui:widget': 'updown' },
      rr_interval_ms: { 'ui:widget': 'updown' },
      qrs_duration_ms: { 'ui:widget': 'updown' },
      qt_interval_ms: { 'ui:widget': 'updown' },
      rhythm: { 'ui:widget': 'select' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: { heart_rate_bpm: 72, rr_interval_ms: 830, qrs_duration_ms: 90, qt_interval_ms: 410, rhythm: 'sinus', timestamp: new Date().toISOString() }
  },
  {
    id: 'emg_summary',
    name: 'EMG Summary',
    category: 'health',
    subcategory: 'muscle',
    description: 'Summarized EMG metrics (not raw waveform)',
    tags: ['emg', 'muscle', 'rehab'],
    icon: getSensorIcon('vibration_sensor'),
    schema: {
      type: 'object',
      properties: {
        muscle_activity_level: { type: 'integer', minimum: 0, maximum: 100 },
        fatigue_index: { type: 'integer', minimum: 0, maximum: 100 },
        dominant_frequency_hz: { type: 'number', minimum: 0, maximum: 500 },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['muscle_activity_level', 'timestamp']
    },
    uiSchema: {
      muscle_activity_level: { 'ui:widget': 'range' },
      fatigue_index: { 'ui:widget': 'range' },
      dominant_frequency_hz: { 'ui:widget': 'updown' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: { muscle_activity_level: 45, fatigue_index: 30, dominant_frequency_hz: 85.5, timestamp: new Date().toISOString() }
  }
];
