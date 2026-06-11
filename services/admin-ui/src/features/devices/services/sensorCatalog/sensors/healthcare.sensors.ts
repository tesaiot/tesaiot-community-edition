/**
 * Healthcare & IoMT Sensor Templates
 *
 * @module sensorCatalog/sensors/healthcare
 * @description Medical-grade sensor definitions for Internet of Medical Things (IoMT)
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 4 (2025-10-02)
 *
 * Contains:
 * - Blood Pressure Monitor (Omron/Philips) - Medical-grade cardiovascular monitoring
 *
 * Standards: ISO 81060-2, AAMI/ANSI SP-10
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const healthcareSensors: SensorTemplate[] = [
  {
    id: 'blood_pressure_monitor',
    name: 'Blood Pressure Monitor',
    category: 'health',
    subcategory: 'cardiovascular',
    description: 'Medical-grade blood pressure monitoring for IoMT applications',
    manufacturer: 'Omron / Philips',
    tags: ['blood-pressure', 'systolic', 'diastolic', 'cardiovascular', 'iomt', 'medical'],
    icon: getSensorIcon('blood_pressure_monitor'),
    standards: ['ISO 81060-2', 'AAMI/ANSI SP-10'],
    schema: {
      type: 'object',
      properties: {
        systolic: {
          type: 'integer',
          minimum: 70,
          maximum: 200,
          title: 'Systolic Pressure'
        },
        diastolic: {
          type: 'integer',
          minimum: 40,
          maximum: 130,
          title: 'Diastolic Pressure'
        },
        pressure_unit: {
          type: 'integer',
          enum: [0, 1],
          default: 0,
          title: 'Pressure Unit',
          description: '0=mmHg, 1=kPa'
        },
        mean_arterial_pressure: {
          type: 'integer',
          title: 'Mean Arterial Pressure (calculated)'
        },
        pulse_rate: {
          type: 'integer',
          minimum: 30,
          maximum: 250,
          title: 'Pulse Rate (BPM)'
        },
        irregular_heartbeat: {
          type: 'boolean',
          title: 'Irregular Heartbeat Detected'
        },
        classification: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4, 5],
          title: 'BP Classification',
          description: '0=Optimal, 1=Normal, 2=High_Normal, 3=Grade1_Hypertension, 4=Grade2_Hypertension, 5=Grade3_Hypertension'
        },
        measurement_quality: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Measurement Quality (%)'
        },
        cuff_pressure: {
          type: 'integer',
          minimum: 0,
          title: 'Cuff Pressure'
        },
        measurement_method: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Measurement Method',
          description: '0=Oscillometric, 1=Auscultatory, 2=Invasive'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['systolic', 'diastolic', 'pulse_rate', 'timestamp']
    },
    uiSchema: {
      systolic: { 'ui:widget': 'updown', 'ui:help': 'Systolic blood pressure (top number)' },
      diastolic: { 'ui:widget': 'updown', 'ui:help': 'Diastolic blood pressure (bottom number)' },
      pressure_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['mmHg (millimeters of mercury)', 'kPa (kilopascals)']
        }
      },
      mean_arterial_pressure: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Calculated MAP' },
      pulse_rate: { 'ui:widget': 'updown', 'ui:help': 'Heart rate during measurement' },
      irregular_heartbeat: { 'ui:widget': 'checkbox', 'ui:help': 'Arrhythmia detection' },
      classification: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Optimal', 'Normal', 'High Normal', 'Grade 1 Hypertension', 'Grade 2 Hypertension', 'Grade 3 Hypertension']
        }
      },
      measurement_quality: { 'ui:widget': 'range', 'ui:help': 'Confidence in measurement' },
      cuff_pressure: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Inflation pressure' },
      measurement_method: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Oscillometric', 'Auscultatory', 'Invasive']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      systolic: 120,
      diastolic: 80,
      pressure_unit: 0,
      mean_arterial_pressure: 93,
      pulse_rate: 72,
      irregular_heartbeat: false,
      classification: 1,
      measurement_quality: 95,
      cuff_pressure: 160,
      measurement_method: 0,
      timestamp: new Date().toISOString()
    },
    units: { systolic: 'mmHg', diastolic: 'mmHg', pulse_rate: 'bpm', cuff_pressure: 'mmHg' },
    ranges: {
      systolic: { min: 70, max: 200 },
      diastolic: { min: 40, max: 130 },
      pulse_rate: { min: 30, max: 250 }
    },
    accuracy: { systolic: 3, diastolic: 3, pulse_rate: 5 }
  }
];
