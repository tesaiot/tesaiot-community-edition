import { SensorTemplate } from '../types/sensor.types';
import { getSensorIcon } from '../../../components/SensorIcons';

/**
 * Advanced Actuator Sensors
 *
 * Standards Compliance:
 * - IEEE 1451: Smart transducer interface
 * - ISO/IEC 21451: Information technology - Smart transducer interface
 *
 * Includes:
 * - SG90 Servo Motor (micro servo with position feedback)
 * - Solenoid Valve Control (fluid control with position feedback)
 */
export const advancedActuatorSensors: SensorTemplate[] = [
  {
    id: 'servo_sg90',
    name: 'SG90 Servo Motor',
    category: 'actuator',
    subcategory: 'servo',
    description: 'SG90 9g micro servo motor with position feedback',
    tags: ['sg90', 'servo', 'motor', 'position', 'pwm', 'micro'],
    icon: getSensorIcon('servo_motor'),
    standards: ['IEEE 1451'],
    schema: {
      type: 'object',
      properties: {
        target_angle: {
          type: 'number',
          minimum: 0,
          maximum: 180,
          title: 'Target Angle (°)'
        },
        current_angle: {
          type: 'number',
          minimum: 0,
          maximum: 180,
          title: 'Current Angle (°)'
        },
        pwm_pulse_width: {
          type: 'number',
          minimum: 500,
          maximum: 2500,
          title: 'PWM Pulse Width (μs)'
        },
        position_error: {
          type: 'number',
          title: 'Position Error (°)'
        },
        servo_enable: {
          type: 'boolean',
          title: 'Servo Enable'
        },
        load_current: {
          type: 'number',
          title: 'Load Current (mA)'
        },
        operating_voltage: {
          type: 'number',
          minimum: 3,
          maximum: 7,
          title: 'Operating Voltage (V)'
        },
        speed: {
          type: 'number',
          title: 'Operating Speed (°/s)'
        },
        torque: {
          type: 'number',
          title: 'Output Torque (kg⋅cm)'
        },
        control_mode: {
          type: 'integer',
          enum: [0, 1, 2],
          title: 'Control Mode',
          description: '0=Position, 1=Speed, 2=Torque'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['target_angle', 'current_angle', 'pwm_pulse_width', 'timestamp']
    },
    uiSchema: {
      target_angle: { 'ui:widget': 'updown', 'ui:help': 'Desired servo position' },
      current_angle: { 'ui:widget': 'updown', 'ui:help': 'Actual servo position' },
      pwm_pulse_width: { 'ui:widget': 'updown', 'ui:help': 'PWM control signal width' },
      position_error: { 'ui:widget': 'updown', 'ui:help': 'Position feedback error' },
      servo_enable: { 'ui:widget': 'checkbox', 'ui:help': 'Servo motor enabled' },
      load_current: { 'ui:widget': 'updown', 'ui:help': 'Current consumption under load' },
      operating_voltage: { 'ui:widget': 'updown', 'ui:help': 'Supply voltage' },
      speed: { 'ui:widget': 'updown', 'ui:help': 'Rotation speed' },
      torque: { 'ui:widget': 'updown', 'ui:help': 'Output torque' },
      control_mode: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Position Control', 'Speed Control', 'Torque Control']
        }
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      target_angle: 90,
      current_angle: 89.5,
      pwm_pulse_width: 1500,
      position_error: 0.5,
      servo_enable: true,
      load_current: 45.5,
      operating_voltage: 5.0,
      speed: 60,
      torque: 1.8,
      control_mode: 0,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'solenoid_valve',
    name: 'Solenoid Valve Control',
    category: 'actuator',
    subcategory: 'valve',
    description: 'Solenoid valve for fluid control with position feedback',
    tags: ['solenoid', 'valve', 'fluid', 'water', 'pneumatic', 'hydraulic'],
    icon: getSensorIcon('valve_control'),
    standards: ['IEEE 1451', 'ISO/IEC 21451'],
    schema: {
      type: 'object',
      properties: {
        valve_state: {
          type: 'integer',
          enum: [0, 1, 2, 3, 4],
          title: 'Valve State',
          description: '0=Closed, 1=Open, 2=Opening, 3=Closing, 4=Fault'
        },
        target_state: {
          type: 'integer',
          enum: [0, 1],
          title: 'Target State',
          description: '0=Close, 1=Open'
        },
        position_feedback: {
          type: 'number',
          minimum: 0,
          maximum: 100,
          title: 'Position Feedback (%)'
        },
        coil_voltage: {
          type: 'number',
          title: 'Coil Voltage (V)'
        },
        coil_current: {
          type: 'number',
          title: 'Coil Current (mA)'
        },
        operating_pressure: {
          type: 'number',
          title: 'Operating Pressure (bar)'
        },
        flow_rate: {
          type: 'number',
          title: 'Flow Rate (L/min)'
        },
        temperature: {
          type: 'number',
          title: 'Valve Temperature (°C)'
        },
        cycle_count: {
          type: 'integer',
          title: 'Operation Cycle Count'
        },
        fault_code: {
          type: 'integer',
          title: 'Fault Code'
        },
        response_time: {
          type: 'number',
          title: 'Response Time (ms)'
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['valve_state', 'target_state', 'position_feedback', 'timestamp']
    },
    uiSchema: {
      valve_state: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Closed', 'Open', 'Opening', 'Closing', 'Fault']
        }
      },
      target_state: {
        'ui:widget': 'select',
        'ui:options': {
          enumNames: ['Close', 'Open']
        }
      },
      position_feedback: { 'ui:widget': 'updown', 'ui:help': 'Actual valve position' },
      coil_voltage: { 'ui:widget': 'updown', 'ui:help': 'Solenoid coil voltage' },
      coil_current: { 'ui:widget': 'updown', 'ui:help': 'Solenoid coil current' },
      operating_pressure: { 'ui:widget': 'updown', 'ui:help': 'System pressure' },
      flow_rate: { 'ui:widget': 'updown', 'ui:help': 'Fluid flow rate' },
      temperature: { 'ui:widget': 'updown', 'ui:help': 'Valve body temperature' },
      cycle_count: { 'ui:widget': 'updown', 'ui:help': 'Total operation cycles' },
      fault_code: { 'ui:widget': 'updown', 'ui:help': 'Error/fault identifier' },
      response_time: { 'ui:widget': 'updown', 'ui:help': 'Valve operation response time' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      valve_state: 1,
      target_state: 1,
      position_feedback: 100,
      coil_voltage: 24.0,
      coil_current: 150,
      operating_pressure: 3.5,
      flow_rate: 15.2,
      temperature: 45.5,
      cycle_count: 12567,
      fault_code: 0,
      response_time: 125,
      timestamp: new Date().toISOString()
    }
  }
];
