/**
 * Fluid Control & Water Quality Sensor Templates
 *
 * @module sensorCatalog/sensors/fluid
 * @description Sensor definitions for fluid control, water quality, and level monitoring
 * @category Sensors
 * @phase Phase 1.4 Week 1 Day 3 (2025-10-02)
 *
 * Contains:
 * - Valve Control (ASCO/Parker) - Solenoid valve automation
 * - Servo Control (TowerPro) - Precise positioning (SG90, MG996R)
 * - TDS/EC Sensor (DFRobot) - Water quality (TDS-3)
 * - Water Level Sensor (HC-SR04P) - Ultrasonic level monitoring
 *
 * Standards: ISO 5598, ANSI/FCI 70-2, PWM, ISO 9001, ISO 7888, ASTM D1125, ISO 4064, IEC 61508
 */

import type { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

export const fluidSensors: SensorTemplate[] = [
  {
    id: 'valve_control',
    name: 'Valve Control',
    category: 'actuator',
    subcategory: 'fluid',
    description: 'Solenoid valve control for fluid systems automation',
    manufacturer: 'ASCO / Parker',
    tags: ['valve', 'solenoid', 'fluid', 'control', 'automation', 'water', 'gas'],
    icon: getSensorIcon('valve_control'),
    standards: ['ISO 5598', 'ANSI/FCI 70-2'],
    schema: {
      type: 'object',
      properties: {
        valve_id: {
          type: 'string',
          title: 'Valve Identifier'
        },
        position: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Valve Position (%)'
        },
        state: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          default: 0,
          title: 'Valve State',
          description: '0=Closed, 1=Open, 2=Opening, 3=Closing, 4=Fault'
        },
        flow_rate: {
          type: 'number',
          minimum: 0,
          title: 'Current Flow Rate'
        },
        flow_unit: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Flow Rate Unit',
          description: '0=L/min, 1=gal/min, 2=m³/h, 3=CFM'
        },
        pressure_upstream: {
          type: 'number',
          minimum: 0,
          title: 'Upstream Pressure'
        },
        pressure_downstream: {
          type: 'number',
          minimum: 0,
          title: 'Downstream Pressure'
        },
        pressure_unit: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Pressure Unit',
          description: '0=bar, 1=psi, 2=kPa, 3=MPa'
        },
        actuation_time: {
          type: 'number',
          title: 'Actuation Time (ms)'
        },
        fault_code: {
          type: 'integer',
          minimum: 0,
          title: 'Fault Code'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['valve_id', 'position', 'state', 'timestamp']
    },
    uiSchema: {
      valve_id: { 'ui:widget': 'text', 'ui:readonly': true },
      position: { 'ui:widget': 'slider', 'ui:help': 'Valve opening percentage' },
      state: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Closed', 'Open', 'Opening', 'Closing', 'Fault']
        }
      },
      flow_rate: { 'ui:widget': 'updown', 'ui:help': 'Measured flow through valve' },
      flow_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['L/min', 'gal/min', 'm³/h', 'CFM']
        }
      },
      pressure_upstream: { 'ui:widget': 'updown', 'ui:help': 'Inlet pressure' },
      pressure_downstream: { 'ui:widget': 'updown', 'ui:help': 'Outlet pressure' },
      pressure_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['bar', 'psi', 'kPa', 'MPa']
        }
      },
      actuation_time: { 'ui:widget': 'text', 'ui:readonly': true },
      fault_code: { 'ui:widget': 'text', 'ui:readonly': true },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      valve_id: 'V-101',
      position: 75,
      state: 1,
      flow_rate: 12.5,
      flow_unit: 0,
      pressure_upstream: 4.2,
      pressure_downstream: 3.8,
      pressure_unit: 0,
      actuation_time: 250,
      fault_code: 0,
      timestamp: new Date().toISOString()
    },
    units: { flow_rate: 'L/min', pressure: 'bar', actuation_time: 'ms' },
    ranges: { position: { min: 0, max: 100 } },
    accuracy: { flow_rate: 0.1, pressure: 0.01 }
  },
  {
    id: 'servo_control',
    name: 'Servo Control',
    category: 'actuator',
    subcategory: 'positioning',
    description: 'Precise servo motor control for positioning applications (SG90, MG996R)',
    manufacturer: 'TowerPro / Futaba',
    tags: ['servo', 'motor', 'positioning', 'sg90', 'mg996r', 'robotics', 'automation'],
    icon: getSensorIcon('servo_control'),
    standards: ['PWM Standard', 'ISO 9001'],
    schema: {
      type: 'object',
      properties: {
        servo_id: {
          type: 'integer',
          minimum: 1,
          maximum: 32,
          title: 'Servo ID'
        },
        angle: {
          type: 'integer',
          minimum: 0,
          maximum: 180,
          title: 'Target Angle'
        },
        current_angle: {
          type: 'integer',
          minimum: 0,
          maximum: 180,
          title: 'Current Angle'
        },
        speed: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Movement Speed (%)'
        },
        torque: {
          type: 'number',
          minimum: 0,
          title: 'Torque Output'
        },
        torque_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Torque Unit',
          description: '0=kg⋅cm, 1=oz⋅in, 2=Nm'
        },
        pwm_pulse: {
          type: 'integer',
          minimum: 500,
          maximum: 2500,
          title: 'PWM Pulse Width (μs)'
        },
        enabled: {
          type: 'boolean',
          title: 'Servo Enabled'
        },
        temperature: {
          type: 'number',
          title: 'Internal Temperature'
        },
        load: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Current Load (%)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['servo_id', 'angle', 'enabled', 'timestamp']
    },
    uiSchema: {
      servo_id: { 'ui:widget': 'updown', 'ui:help': 'Servo channel number' },
      angle: { 'ui:widget': 'slider', 'ui:help': 'Target position (0-180 degrees)' },
      current_angle: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'Actual position feedback' },
      speed: { 'ui:widget': 'slider', 'ui:help': 'Movement speed percentage' },
      torque: { 'ui:widget': 'updown', 'ui:help': 'Output torque measurement' },
      torque_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['kg⋅cm', 'oz⋅in', 'N⋅m']
        }
      },
      pwm_pulse: { 'ui:widget': 'text', 'ui:readonly': true, 'ui:help': 'PWM signal width' },
      enabled: { 'ui:widget': 'switch', 'ui:help': 'Enable/disable servo power' },
      temperature: { 'ui:widget': 'text', 'ui:readonly': true },
      load: { 'ui:widget': 'range', 'ui:help': 'Current load percentage' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      servo_id: 1,
      angle: 90,
      current_angle: 88,
      speed: 50,
      torque: 1.8,
      torque_unit: 0,
      pwm_pulse: 1500,
      enabled: true,
      temperature: 45.2,
      load: 25,
      timestamp: new Date().toISOString()
    },
    units: { angle: '°', torque: 'kg⋅cm', pwm_pulse: 'μs', temperature: '°C' },
    ranges: {
      angle: { min: 0, max: 180 },
      speed: { min: 0, max: 100 },
      load: { min: 0, max: 100 }
    },
    accuracy: { angle: 1, torque: 0.1 }
  },
  {
    id: 'tds_ec_sensor',
    name: 'TDS/EC Water Quality Sensor',
    category: 'water',
    subcategory: 'quality',
    description: 'Total Dissolved Solids and Electrical Conductivity measurement (TDS-3)',
    manufacturer: 'DFRobot / Atlas Scientific',
    tags: ['tds', 'ec', 'conductivity', 'water-quality', 'tds-3', 'salinity', 'aquarium'],
    icon: getSensorIcon('tds_ec_sensor'),
    standards: ['ISO 7888', 'ASTM D1125'],
    schema: {
      type: 'object',
      properties: {
        tds: {
          type: 'integer',
          minimum: 0,
          maximum: 5000,
          title: 'Total Dissolved Solids'
        },
        tds_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'TDS Unit',
          description: '0=ppm, 1=mg/L, 2=g/L'
        },
        ec: {
          type: 'number',
          minimum: 0,
          maximum: 10000,
          title: 'Electrical Conductivity'
        },
        ec_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'EC Unit',
          description: '0=μS/cm, 1=mS/cm, 2=S/m'
        },
        salinity: {
          type: 'number',
          minimum: 0,
          maximum: 42,
          title: 'Salinity'
        },
        salinity_unit: {
          type: 'integer',
          enum: [0, 1],
          default: 0,
          title: 'Salinity Unit',
          description: '0=ppt, 1=PSU'
        },
        temperature: {
          type: 'number',
          title: 'Water Temperature'
        },
        temperature_unit: {
          type: 'string',
          enum: ['°C'],
          default: '°C',
          title: 'Temperature Unit'
        },
        temperature_compensation: {
          type: 'boolean',
          default: true,
          title: 'Temperature Compensation Enabled'
        },
        calibration_point: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Calibration Points',
          description: '0=Factory, 1=1-point, 2=2-point, 3=3-point'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['tds', 'ec', 'temperature', 'timestamp']
    },
    uiSchema: {
      tds: { 'ui:widget': 'updown', 'ui:help': 'Total dissolved solids measurement' },
      tds_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['ppm (parts per million)', 'mg/L', 'g/L']
        }
      },
      ec: { 'ui:widget': 'updown', 'ui:help': 'Electrical conductivity measurement' },
      ec_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['μS/cm (microsiemens)', 'mS/cm (millisiemens)', 'S/m (siemens)']
        }
      },
      salinity: { 'ui:widget': 'updown', 'ui:help': 'Calculated salinity level' },
      salinity_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['ppt (parts per thousand)', 'PSU (Practical Salinity Units)']
        }
      },
      temperature: { 'ui:widget': 'updown', 'ui:help': 'Temperature for compensation' },
      temperature_compensation: { 'ui:widget': 'checkbox', 'ui:help': 'Automatic temperature correction' },
      calibration_point: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Factory Calibration', '1-Point Calibration', '2-Point Calibration', '3-Point Calibration']
        }
      },
      temperature_unit: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      tds: 435,
      tds_unit: 0,
      ec: 870,
      ec_unit: 0,
      salinity: 0.43,
      salinity_unit: 0,
      temperature: 25.0,
      temperature_compensation: true,
      calibration_point: 2,
      timestamp: new Date().toISOString()
    },
    units: { tds: 'ppm', ec: 'μS/cm', salinity: 'ppt', temperature: '°C' },
    ranges: {
      tds: { min: 0, max: 5000 },
      ec: { min: 0, max: 10000 },
      salinity: { min: 0, max: 42 }
    },
    accuracy: { tds: 2, ec: 1, salinity: 0.01 }
  },
  {
    id: 'water_level_sensor',
    name: 'Water Level Sensor',
    category: 'water',
    subcategory: 'level',
    description: 'Ultrasonic water level monitoring for tank systems (HC-SR04P)',
    manufacturer: 'HC Electronics',
    tags: ['water-level', 'ultrasonic', 'tank', 'hc-sr04p', 'monitoring', 'reservoir'],
    icon: getSensorIcon('water_level_sensor'),
    standards: ['ISO 4064', 'IEC 61508'],
    schema: {
      type: 'object',
      properties: {
        level: {
          type: 'number',
          minimum: 0,
          maximum: 500,
          title: 'Water Level'
        },
        level_unit: {
          type: 'integer',
          enum: [0, 1, 2],
          default: 0,
          title: 'Level Unit',
          description: '0=cm, 1=m, 2=inches'
        },
        percentage: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Tank Fill Percentage'
        },
        volume: {
          type: 'number',
          minimum: 0,
          title: 'Current Volume'
        },
        volume_unit: {
          type: 'integer',
          enum: [0, 1, 2, 3],
          default: 0,
          title: 'Volume Unit',
          description: '0=L, 1=gal, 2=m³, 3=ft³'
        },
        tank_capacity: {
          type: 'number',
          minimum: 0,
          title: 'Tank Capacity'
        },
        status: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          default: 2,
          title: 'Level Status',
          description: '0=Empty, 1=Low, 2=Normal, 3=High, 4=Overflow'
        },
        alarm_low: {
          type: 'number',
          title: 'Low Level Alarm Threshold'
        },
        alarm_high: {
          type: 'number',
          title: 'High Level Alarm Threshold'
        },
        measurement_confidence: {
          type: 'integer',
          minimum: 0,
          maximum: 100,
          title: 'Measurement Confidence (%)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['level', 'percentage', 'status', 'timestamp']
    },
    uiSchema: {
      level: { 'ui:widget': 'updown', 'ui:help': 'Distance from sensor to water surface' },
      level_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Centimeters', 'Meters', 'Inches']
        }
      },
      percentage: { 'ui:widget': 'range', 'ui:help': 'Tank fill percentage' },
      volume: { 'ui:widget': 'updown', 'ui:help': 'Calculated current volume' },
      volume_unit: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Liters', 'Gallons', 'Cubic Meters', 'Cubic Feet']
        }
      },
      tank_capacity: { 'ui:widget': 'updown', 'ui:help': 'Maximum tank capacity' },
      status: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Empty', 'Low', 'Normal', 'High', 'Overflow']
        }
      },
      alarm_low: { 'ui:widget': 'updown', 'ui:help': 'Low level alert threshold' },
      alarm_high: { 'ui:widget': 'updown', 'ui:help': 'High level alert threshold' },
      measurement_confidence: { 'ui:widget': 'range', 'ui:help': 'Signal quality indicator' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      level: 75.5,
      level_unit: 0,
      percentage: 75,
      volume: 1500,
      volume_unit: 0,
      tank_capacity: 2000,
      status: 2,
      alarm_low: 20,
      alarm_high: 95,
      measurement_confidence: 95,
      timestamp: new Date().toISOString()
    },
    units: { level: 'cm', volume: 'L', measurement_confidence: '%' },
    ranges: {
      level: { min: 0, max: 500 },
      percentage: { min: 0, max: 100 },
      measurement_confidence: { min: 0, max: 100 }
    },
    accuracy: { level: 0.3, percentage: 1 }
  }
];
