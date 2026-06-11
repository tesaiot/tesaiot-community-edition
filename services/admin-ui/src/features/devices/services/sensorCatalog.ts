/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { getSensorIcon } from '../components/SensorIcons';
import { allInfineonXensivSensors } from './infineonXensivSensors';

// Import modularized types and constants
export type { SensorTemplate, SensorCategory } from './sensorCatalog/types/sensor.types';
export { UnitMappings } from './sensorCatalog/constants/unit.mappings';

// For internal use in this file
import type { SensorTemplate } from './sensorCatalog/types/sensor.types';

// [MODULARIZE:COMPLETED] - TemperatureSensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/temperature.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { temperatureSensors } from './sensorCatalog/sensors/temperature.sensors';

// [MODULARIZE:COMPLETED] - AirQualitySensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/airquality.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { airQualitySensors } from './sensorCatalog/sensors/airquality.sensors';

// [MODULARIZE:COMPLETED] - MotionSensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/motion.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { motionSensors } from './sensorCatalog/sensors/motion.sensors';

// [MODULARIZE:COMPLETED] - LightSensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/light.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { lightSensors } from './sensorCatalog/sensors/light.sensors';

// [MODULARIZE:COMPLETED] - DistanceSensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/distance.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { distanceSensors } from './sensorCatalog/sensors/distance.sensors';

// [MODULARIZE:COMPLETED] - WaterSensorsCatalog - v2025.08
// Moved to: ./sensorCatalog/sensors/water.sensors.ts
// Re-exported from: ./sensorCatalog/index.ts
import { waterSensors } from './sensorCatalog/sensors/water.sensors';

// [MODULARIZE:COMPLETED] - PowerSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/power.sensors.ts
import { powerSensors } from './sensorCatalog/sensors/power.sensors';

// Actuator Templates
const actuatorTemplates: SensorTemplate[] = [
  {
    id: 'relay_control',
    name: 'Relay Control',
    category: 'actuator',
    subcategory: 'switch',
    description: 'On/Off relay control',
    tags: ['relay', 'switch', 'control', 'on/off'],
    icon: getSensorIcon('relay_control'),
    standards: ['IEC 61810', 'UL 508'],
    schema: {
      type: 'object',
      properties: {
        state: { type: 'boolean' },
        name: { type: 'string' },
        schedule: {
          type: 'object',
          properties: {
            enabled: { type: 'boolean', default: false },
            onTime: { type: 'string', pattern: '^([01]\\d|2[0-3]):([0-5]\\d)$' },
            offTime: { type: 'string', pattern: '^([01]\\d|2[0-3]):([0-5]\\d)$' }
          }
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['state', 'name']
    },
    uiSchema: {
      state: {
        'ui:widget': 'switch',
        'ui:options': {
          onLabel: 'ON',
          offLabel: 'OFF'
        }
      },
      name: {
        'ui:widget': 'text',
        'ui:readonly': true
      },
      schedule: {
        'ui:field': 'object',
        'ui:collapsible': true
      },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      state: false,
      name: 'Main Power',
      schedule: {
        enabled: false,
        onTime: '08:00',
        offTime: '18:00'
      },
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'motor_control',
    name: 'Motor Control',
    category: 'actuator',
    subcategory: 'motor',
    description: 'Variable speed motor control',
    tags: ['motor', 'speed', 'control', 'pwm', 'vfd'],
    icon: getSensorIcon('motor_control'),
    standards: ['IEC 60034', 'NEMA MG 1'],
    schema: {
      type: 'object',
      properties: {
        motorId: { type: 'integer' },
        state: {
          type: 'string',
          enum: ['stopped', 'running', 'fault']
        },
        speed: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 3000 },
            unit: { type: 'string', enum: ['rpm', 'Hz'], default: 'rpm' }
          }
        },
        direction: {
          type: 'string',
          enum: ['forward', 'reverse']
        },
        pwm: { type: 'integer', minimum: 0, maximum: 255 },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['motorId', 'state']
    },
    uiSchema: {
      motorId: { 'ui:widget': 'hidden' },
      state: { 'ui:widget': 'select' },
      speed: {
        'ui:field': 'object',
        value: {
          'ui:widget': 'slider',
          'ui:controlMode': true
        }
      },
      direction: {
        'ui:widget': 'radio',
        'ui:options': {
          inline: true
        }
      },
      pwm: { 'ui:widget': 'hidden' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      motorId: 1,
      state: 'running',
      speed: { value: 1450, unit: 'rpm' },
      direction: 'forward',
      pwm: 180,
      timestamp: new Date().toISOString()
    }
  },
  {
    id: 'led_control',
    name: 'LED/Light Control',
    category: 'actuator',
    subcategory: 'light',
    description: 'RGB LED or light control',
    tags: ['led', 'light', 'rgb', 'dimmer', 'control'],
    icon: getSensorIcon('led_control'),
    standards: ['IEC 62386', 'IEEE 1789'],
    schema: {
      type: 'object',
      properties: {
        power: { type: 'boolean' },
        brightness: {
          type: 'object',
          properties: {
            value: { type: 'integer', minimum: 0, maximum: 100 },
            unit: { type: 'string', enum: ['%'], default: '%' }
          }
        },
        color: {
          type: 'object',
          properties: {
            red: { type: 'integer', minimum: 0, maximum: 255 },
            green: { type: 'integer', minimum: 0, maximum: 255 },
            blue: { type: 'integer', minimum: 0, maximum: 255 }
          }
        },
        mode: {
          type: 'string',
          enum: ['static', 'breathing', 'flashing', 'rainbow']
        },
        timestamp: { type: 'string', format: 'date-time' }
      },
      required: ['power']
    },
    uiSchema: {
      power: { 'ui:widget': 'switch' },
      brightness: {
        'ui:field': 'object',
        value: { 'ui:widget': 'slider' }
      },
      color: { 'ui:field': 'object' },
      mode: { 'ui:widget': 'select' },
      timestamp: { 'ui:widget': 'hidden' }
    },
    exampleData: {
      power: true,
      brightness: { value: 80, unit: '%' },
      color: { red: 255, green: 128, blue: 64 },
      mode: 'static',
      timestamp: new Date().toISOString()
    }
  }
];

// Sound & Audio Sensors
// [MODULARIZE:COMPLETED] - SoundSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/sound.sensors.ts
import { soundSensors } from './sensorCatalog/sensors/sound.sensors';

// [MODULARIZE:COMPLETED] - MagneticSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/magnetic.sensors.ts
// Phase 1.4 Week 1 Day 2 (2025-10-02)
import { magneticSensors } from './sensorCatalog/sensors/magnetic.sensors';

// [MODULARIZE:COMPLETED] - NavigationSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/navigation.sensors.ts
// Phase 1.4 Week 1 Day 3 (2025-10-02)
import { navigationSensors } from './sensorCatalog/sensors/navigation.sensors';

// [MODULARIZE:COMPLETED] - EnergySensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/energy.sensors.ts
// Phase 1.4 Week 1 Day 4 (2025-10-02)
import { energySensors } from './sensorCatalog/sensors/energy.sensors';

// [MODULARIZE:COMPLETED] - FluidSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/fluid.sensors.ts
// Phase 1.4 Week 1 Day 3 (2025-10-02)
import { fluidSensors } from './sensorCatalog/sensors/fluid.sensors';

// [MODULARIZE:COMPLETED] - HealthcareSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/healthcare.sensors.ts
// Phase 1.4 Week 1 Day 4 (2025-10-02)
import { healthcareSensors } from './sensorCatalog/sensors/healthcare.sensors';

// [MODULARIZE:COMPLETED] - CommunicationSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/communication.sensors.ts
// Phase 1.4 Week 1 Day 5 (2025-10-02)
import { communicationSensors } from './sensorCatalog/sensors/communication.sensors';

// Health & Biometric Sensors
// [MODULARIZE:COMPLETED] - HealthSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/health.sensors.ts
// Phase 1.4 Week 2 Day 9 (2025-10-02)
import { healthSensors } from './sensorCatalog/sensors/health.sensors';

// [MODULARIZE:COMPLETED] - IndustrialSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/industrial.sensors.ts
// Phase 1.4 Week 1 Day 5 (2025-10-02)
import { industrialSensors } from './sensorCatalog/sensors/industrial.sensors';

// MISSING SENSORS - Adding 20+ critical sensors for 100% IoT specification coverage

// [MODULARIZE:COMPLETED] - AdvancedAirQualitySensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-airquality.sensors.ts
// Phase 1.4 Week 2 Day 6 (2025-10-02)
import { advancedAirQualitySensors } from './sensorCatalog/sensors/advanced-airquality.sensors';

// [MODULARIZE:COMPLETED] - MultiGasSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/multigas.sensors.ts
// Phase 1.4 Week 2 Day 6 (2025-10-02)
import { multiGasSensors } from './sensorCatalog/sensors/multigas.sensors';

// [MODULARIZE:COMPLETED] - ParticulateMatterSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/particulate-matter.sensors.ts
// Phase 1.4 Week 2 Day 7 (2025-10-02)
import { particulateMatterSensors } from './sensorCatalog/sensors/particulate-matter.sensors';

// Advanced Motion & Positioning Sensors
// [MODULARIZE:COMPLETED] - AdvancedMotionSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-motion.sensors.ts
// Phase 1.4 Week 2 Day 9 (2025-10-02)
import { advancedMotionSensors } from './sensorCatalog/sensors/advanced-motion.sensors';

// [MODULARIZE:COMPLETED] - AdvancedIndustrialSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-industrial.sensors.ts
// Phase 1.4 Week 2 Day 8 (2025-10-02)
import { advancedIndustrialSensors } from './sensorCatalog/sensors/advanced-industrial.sensors';

// [MODULARIZE:COMPLETED] - AdvancedEnergySensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-energy.sensors.ts
// Phase 1.4 Week 1 Day 2 (2025-10-02)
import { advancedEnergySensors } from './sensorCatalog/sensors/advanced-energy.sensors';

// Water Quality & TDS Sensors
// [MODULARIZE:COMPLETED] - AdvancedWaterSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-water.sensors.ts
// Phase 1.4 Week 2 Day 8 (2025-10-02)
import { advancedWaterSensors } from './sensorCatalog/sensors/advanced-water.sensors';

// Health & Biometric Sensors (IoMT)
// [MODULARIZE:COMPLETED] - AdvancedHealthSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-health.sensors.ts
// Phase 1.4 Week 2 Day 10 (2025-10-02)
import { advancedHealthSensors } from './sensorCatalog/sensors/advanced-health.sensors';

// [MODULARIZE:COMPLETED] - AdvancedCommunicationSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-communication.sensors.ts
// Phase 1.4 Week 2 Day 7 (2025-10-02)
import { advancedCommunicationSensors } from './sensorCatalog/sensors/advanced-communication.sensors';

// Actuator & Control Sensors
// [MODULARIZE:COMPLETED] - AdvancedActuatorSensorsCatalog - v2025.10
// Moved to: ./sensorCatalog/sensors/advanced-actuator.sensors.ts
// Phase 1.4 Week 2 Day 10 (2025-10-02)
import { advancedActuatorSensors } from './sensorCatalog/sensors/advanced-actuator.sensors';

// [MODULARIZE:START] - SensorCatalogRegistry - v2025.08
// Description: Main registry combining all sensor catalogs
// Dependencies: All individual sensor catalog modules (after modularization)
// Estimated Size: 250 lines
// Priority: MEDIUM
// Note: After modularization, this will import from individual modules
// Sensor catalog organized by categories
export const sensorCatalog: SensorCategory[] = [
  {
    id: 'environmental',
    name: 'Temperature & Environmental',
    description: 'Temperature, humidity, pressure, and environmental monitoring sensors',
    icon: getSensorIcon('temperature_basic'),
    sensors: [...temperatureSensors, ...airQualitySensors, ...advancedAirQualitySensors, ...multiGasSensors, ...particulateMatterSensors]
  },
  {
    id: 'motion',
    name: 'Motion & Position',
    description: 'Accelerometers, gyroscopes, and motion detection sensors',
    icon: getSensorIcon('accelerometer'),
    sensors: [...motionSensors, ...navigationSensors.filter(s => s.id === 'gyroscope'), ...advancedMotionSensors.filter(s => s.category === 'motion')]
  },
  {
    id: 'navigation',
    name: 'Navigation & Location',
    description: 'GPS, LIDAR, and positioning sensors for autonomous systems',
    icon: getSensorIcon('gps_module'),
    sensors: [...navigationSensors, ...advancedMotionSensors.filter(s => s.category === 'navigation')]
  },
  {
    id: 'optical',
    name: 'Light & Optical',
    description: 'Light intensity, UV, color, and optical sensors',
    icon: getSensorIcon('light_intensity'),
    sensors: lightSensors
  },
  {
    id: 'distance',
    name: 'Distance & Proximity',
    description: 'Ultrasonic, infrared, and LIDAR distance sensors',
    icon: getSensorIcon('ultrasonic_distance'),
    sensors: [...distanceSensors, ...navigationSensors.filter(s => s.id === 'lidar_sensor'), ...advancedMotionSensors.filter(s => s.category === 'distance')]
  },
  {
    id: 'water',
    name: 'Water & Liquid',
    description: 'pH, flow rate, level, and water quality sensors',
    icon: getSensorIcon('water_level'),
    sensors: [...waterSensors, ...fluidSensors.filter(s => s.category === 'water'), ...advancedWaterSensors]
  },
  {
    id: 'electrical',
    name: 'Power & Electrical',
    description: 'Current, voltage, power, and energy monitoring',
    icon: getSensorIcon('current_sensor'),
    sensors: [...powerSensors, ...energySensors, ...advancedEnergySensors]
  },
  {
    id: 'actuator',
    name: 'Actuators & Controllers',
    description: 'Relays, motors, valves, and output devices',
    icon: getSensorIcon('relay_control'),
    sensors: [...actuatorTemplates, ...fluidSensors.filter(s => s.category === 'actuator'), ...advancedActuatorSensors]
  },
  {
    id: 'sound',
    name: 'Sound & Audio',
    description: 'Sound level, frequency, and acoustic sensors',
    icon: getSensorIcon('sound_level'),
    sensors: soundSensors
  },
  {
    id: 'magnetic',
    name: 'Magnetic & Field',
    description: 'Hall effect, reed switches, and magnetic field sensors',
    icon: getSensorIcon('hall_effect'),
    sensors: magneticSensors
  },
  {
    id: 'health',
    name: 'Health & Biometric (IoMT)',
    description: 'Heart rate, blood pressure, and medical monitoring sensors',
    icon: getSensorIcon('heart_rate'),
    sensors: [...healthSensors, ...healthcareSensors, ...advancedHealthSensors]
  },
  {
    id: 'communication',
    name: 'Communication & Network',
    description: 'WiFi, network diagnostics, and connectivity monitoring',
    icon: getSensorIcon('wifi_module_status'),
    sensors: [...communicationSensors, ...advancedCommunicationSensors]
  },
  {
    id: 'industrial',
    name: 'Industrial & Machinery',
    description: 'Load cells, vibration, and industrial monitoring sensors',
    icon: getSensorIcon('load_cell'),
    sensors: [...industrialSensors, ...advancedIndustrialSensors]
  },
  {
    id: 'infineon_xensiv',
    name: 'Infineon XENSIV™ Sensors',
    description: 'Premium XENSIV™ sensor series from Infineon: DPS368, PAS CO2, BGT60 Radar, BMI270, BMM350, IM72D128',
    icon: getSensorIcon('xensiv_sensor'),
    sensors: [...allInfineonXensivSensors]
  }
];

// Helper function to get all sensors as a flat list
export const getAllSensors = (): SensorTemplate[] => {
  return sensorCatalog.flatMap(category => category.sensors);
};

// Helper function to search sensors
export const searchSensors = (query: string): SensorTemplate[] => {
  const lowerQuery = query.toLowerCase();
  return getAllSensors().filter(sensor =>
    sensor.name.toLowerCase().includes(lowerQuery) ||
    sensor.description.toLowerCase().includes(lowerQuery) ||
    sensor.tags.some(tag => tag.toLowerCase().includes(lowerQuery)) ||
    sensor.category.toLowerCase().includes(lowerQuery)
  );
};

// Helper function to get sensor by ID
export const getSensorById = (id: string): SensorTemplate | undefined => {
  return getAllSensors().find(sensor => sensor.id === id);
};

// Helper function to merge multiple sensor schemas
export const mergeSensorSchemas = (
  sensors: SensorTemplate[],
  options?: {
    namespacePrefix?: boolean;
    includeTimestamp?: boolean;
    mergeMode?: 'nested' | 'flat';
  }
): { schema: RJSFSchema; uiSchema: UiSchema } => {
  const { 
    namespacePrefix = false, 
    includeTimestamp = true,
    mergeMode = 'flat' 
  } = options || {};

  const mergedSchema: RJSFSchema = {
    type: 'object',
    title: 'Combined Sensor Schema',
    properties: {}
  };
  const mergedUiSchema: UiSchema = {};

  sensors.forEach((sensor, index) => {
    const prefix = namespacePrefix ? `${sensor.id}_` : '';
    
    if (mergeMode === 'nested') {
      // Create nested structure for each sensor
      mergedSchema.properties![sensor.id] = {
        type: 'object',
        title: sensor.name,
        properties: sensor.schema.properties
      };
      mergedUiSchema[sensor.id] = {
        'ui:field': 'object',
        'ui:title': sensor.name,
        ...sensor.uiSchema
      };
    } else {
      // Flat structure with prefixed field names
      Object.entries(sensor.schema.properties || {}).forEach(([key, value]) => {
        if (key !== 'timestamp' || (key === 'timestamp' && index === 0)) {
          mergedSchema.properties![`${prefix}${key}`] = value;
          if (sensor.uiSchema[key]) {
            mergedUiSchema[`${prefix}${key}`] = sensor.uiSchema[key];
          }
        }
      });
    }
  });

  // Add single timestamp if needed
  if (includeTimestamp && !mergedSchema.properties!.timestamp) {
    mergedSchema.properties!.timestamp = {
      type: 'string',
      format: 'date-time'
    };
    mergedUiSchema.timestamp = { 'ui:widget': 'hidden' };
  }

  // Collect all required fields from individual sensors
  const allRequiredFields: string[] = [];
  
  sensors.forEach((sensor, index) => {
    const sensorRequired = sensor.schema.required || [];
    sensorRequired.forEach(field => {
      if (mergeMode === 'nested') {
        // For nested mode, required fields are handled per sensor object
        // The required fields will be nested within each sensor object
        return;
      } else {
        // For flat mode, merge all required fields with proper prefixing
        if (field !== 'timestamp' || index === 0) {
          const prefix = namespacePrefix ? `${sensor.id}_` : '';
          const fieldName = field === 'timestamp' && index === 0 ? 'timestamp' : `${prefix}${field}`;
          if (!allRequiredFields.includes(fieldName)) {
            allRequiredFields.push(fieldName);
          }
        }
      }
    });
  });

  // Ensure timestamp is included if requested and not already present
  if (includeTimestamp && !allRequiredFields.includes('timestamp')) {
    allRequiredFields.push('timestamp');
  }

  // Set the merged required fields
  mergedSchema.required = allRequiredFields;

  return { schema: mergedSchema, uiSchema: mergedUiSchema };
};

// Export sensor icons for UI
export const sensorIcons: Record<string, string> = {
  temperature: '🌡️',
  humidity: '💧',
  pressure: '🔵',
  air_quality: '💨',
  motion: '🏃',
  light: '💡',
  distance: '📏',
  water: '💧',
  electrical: '⚡',
  actuator: '🎮',
  sound: '🔊',
  gas: '💨',
  magnetic: '🧲',
  gps: '📍',
  health: '❤️',
  // New icons for TOP 10 priority sensors
  gyroscope: '🌀',
  lidar: '📡',
  energy: '🔋',
  valve: '🚰',
  servo: '⚙️',
  tds: '🧪',
  level: '📊',
  blood_pressure: '🩺',
  wifi: '📶',
  navigation: '🧭',
  communication: '📡',
  fluid: '💧',
  smart_grid: '🏭',
  positioning: '📍',
  quality: '🧪',
  cardiovascular: '❤️',
  network: '🌐',
  iomt: '🏥',
  // New icons for missing sensors
  gas_sensor: '🔍',
  energy_monitor: '⚡',
  tds_sensor: '🧬',
  servo_motor: '🔧',
  valve_control: '🚰',
  vibration_sensor: '📳',
  // Infineon XENSIV™ brand icon
  xensiv_sensor: '🔬'
};
// [MODULARIZE:END] - SensorCatalogRegistry

/*
 * MODULARIZATION SUMMARY for sensorCatalog.ts
 * ============================================
 * 
 * Total File Size: ~5,073 lines
 * Modules Identified: 28+
 * 
 * Core Modules:
 * - SensorCatalogTypes: Type definitions (30 lines)
 * - UnitMappingsModule: Unit conversion mappings (55 lines)
 * - SensorCatalogRegistry: Main registry (250 lines)
 * 
 * Sensor Category Modules:
 * - TemperatureSensorsCatalog: Temperature sensors (350 lines)
 * - AirQualitySensorsCatalog: Air quality sensors (150 lines)
 * - MotionSensorsCatalog: Motion sensors (300 lines)
 * - LightSensorsCatalog: Light sensors (150 lines)
 * - DistanceSensorsCatalog: Distance sensors (200 lines)
 * - WaterSensorsCatalog: Water quality sensors (250 lines)
 * - PowerSensorsCatalog: Power monitoring sensors (200 lines)
 * - SoundSensorsCatalog: Sound sensors (100 lines)
 * - MagneticSensorsCatalog: Magnetic sensors (150 lines)
 * - NavigationSensorsCatalog: GPS/navigation sensors (200 lines)
 * - EnergySensorsCatalog: Energy sensors (200 lines)
 * - FluidSensorsCatalog: Fluid/flow sensors (250 lines)
 * - HealthcareSensorsCatalog: Healthcare sensors (300 lines)
 * - CommunicationSensorsCatalog: Network sensors (200 lines)
 * - IndustrialSensorsCatalog: Industrial sensors (400 lines)
 * - Plus 10+ advanced sensor categories
 * 
 * Estimated Total Effort: 40-60 hours
 * Priority: HIGH (largest file in codebase)
 * 
 * Benefits after modularization:
 * - Each sensor category can be loaded on-demand
 * - Parallel development by sensor type
 * - Better tree-shaking for smaller bundles
 * - Easier testing and maintenance
 * - Reduced build times
 * 
 * Next Steps:
 * 1. Complete marking all sensor categories
 * 2. Create module structure plan
 * 3. Implement using Strangler Fig pattern
 * 4. Validate with parallel runs
 */
