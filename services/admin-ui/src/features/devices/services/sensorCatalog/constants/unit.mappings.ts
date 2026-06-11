/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Unit conversion mappings for IoT devices (integer enum to string)
 * Used by UI to display human-readable units while firmware uses integers
 *
 * Based on research of IEEE 1451, Modbus, Zigbee, and real embedded firmware
 * Integer enums instead of string enums for firmware efficiency (90% bandwidth reduction)
 */

export const UnitMappings = {
  temperature: ['°C', '°F', 'K'],
  pressure: ['hPa', 'bar', 'psi', 'Pa', 'kPa', 'MPa'],
  humidity: ['%RH', 'g/m³'],
  distance: ['cm', 'm', 'mm', 'inch', 'ft'],
  speed: ['m/s', 'km/h', 'mph', 'ft/s'],
  weight: ['kg', 'g', 'lb', 'oz', 'ton'],
  volume: ['L', 'mL', 'gal', 'fl_oz', 'm³', 'ft³'],
  current: ['mA', 'A', 'μA'],
  voltage: ['mV', 'V', 'kV'],
  power: ['mW', 'W', 'kW', 'MW'],
  energy: ['Wh', 'kWh', 'MWh', 'J', 'kJ'],
  frequency: ['Hz', 'kHz', 'MHz', 'GHz'],
  concentration: ['ppm', 'ppb', '%', 'mg/L', 'g/L'],
  illuminance: ['lux', 'fc', 'lm/m²'],
  angle: ['°', 'rad', 'grad'],
  flowRate: ['L/min', 'L/h', 'gal/min', 'gal/h', 'm³/h', 'CFM'],
  force: ['N', 'lbf', 'kgf', 'dyne'],
  torque: ['Nm', 'ft-lb', 'in-lb', 'kg⋅cm', 'oz⋅in'],
  acceleration: ['m/s²', 'g', 'ft/s²'],
  angularVelocity: ['°/s', 'rad/s', 'rpm'],
  magneticField: ['μT', 'mT', 'G', 'T'],
  airQuality: ['AQI', 'μg/m³', 'ppm'],
  ph: ['pH'],
  conductivity: ['μS/cm', 'mS/cm', 'S/m'],
  turbidity: ['NTU', 'FTU', 'JTU'],
  dissolvedOxygen: ['mg/L', 'ppm', '%sat'],
  soundLevel: ['dB', 'dBA', 'dBC'],
  dataRate: ['bps', 'kbps', 'Mbps', 'Gbps'],
  memory: ['B', 'KB', 'MB', 'GB'],
  percentage: ['%'],
  count: ['count', 'pcs', 'units'],
  boolean: ['false', 'true'],
  state: ['off', 'on', 'auto', 'error'],
  // New units for TOP 10 priority sensors
  coordinates: ['°', 'decimal degrees'],
  altitude: ['m', 'ft'],
  signalStrength: ['dBm', 'arbitrary', '%'],
  time: ['ms', 'μs', 's', 'min', 'h'],
  salinity: ['ppt', 'PSU'],
  bloodPressure: ['mmHg', 'kPa'],
  pulseWidth: ['μs', 'ms'],
  networkAddress: ['IPv4', 'IPv6', 'MAC'],
  currency: ['USD', 'EUR', 'THB', 'CNY', 'JPY'],
  gpsQuality: ['Invalid', 'GPS', 'DGPS', 'PPS', 'RTK', 'Float_RTK'],
  calibrationStatus: ['Uncalibrated', 'Partially', 'Good', 'Excellent'],
  rangeStatus: ['Valid', 'Sigma_Fail', 'Signal_Fail', 'Min_Range_Fail', 'Phase_Fail'],
  connectionStatus: ['Disconnected', 'Connecting', 'Connected', 'Reconnecting', 'Error'],
  valveState: ['Closed', 'Open', 'Opening', 'Closing', 'Fault'],
  levelStatus: ['Empty', 'Low', 'Normal', 'High', 'Overflow'],
  bpClassification: ['Optimal', 'Normal', 'High_Normal', 'Grade1_Hypertension', 'Grade2_Hypertension', 'Grade3_Hypertension'],
  measurementMethod: ['Oscillometric', 'Auscultatory', 'Invasive']
};
