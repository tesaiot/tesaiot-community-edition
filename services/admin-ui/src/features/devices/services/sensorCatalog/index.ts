/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Barrel export for sensor catalog modules
 * Provides backward-compatible exports for existing imports
 */

// Re-export types
export type { SensorTemplate, SensorCategory } from './types/sensor.types';

// Re-export constants
export { UnitMappings } from './constants/unit.mappings';

// Re-export sensor arrays
export { temperatureSensors } from './sensors/temperature.sensors';
export { airQualitySensors } from './sensors/airquality.sensors';
export { motionSensors } from './sensors/motion.sensors';
export { lightSensors } from './sensors/light.sensors';
export { distanceSensors } from './sensors/distance.sensors';
export { waterSensors } from './sensors/water.sensors';
export { powerSensors } from './sensors/power.sensors';
export { soundSensors } from './sensors/sound.sensors';
export { magneticSensors } from './sensors/magnetic.sensors';
export { advancedEnergySensors } from './sensors/advanced-energy.sensors';
export { navigationSensors } from './sensors/navigation.sensors';
export { fluidSensors } from './sensors/fluid.sensors';
export { energySensors } from './sensors/energy.sensors';
export { healthcareSensors } from './sensors/healthcare.sensors';
export { communicationSensors } from './sensors/communication.sensors';
export { industrialSensors } from './sensors/industrial.sensors';
export { advancedAirQualitySensors } from './sensors/advanced-airquality.sensors';
export { multiGasSensors } from './sensors/multigas.sensors';
export { particulateMatterSensors } from './sensors/particulate-matter.sensors';
export { advancedCommunicationSensors } from './sensors/advanced-communication.sensors';
export { advancedIndustrialSensors } from './sensors/advanced-industrial.sensors';
export { advancedWaterSensors } from './sensors/advanced-water.sensors';
export { healthSensors } from './sensors/health.sensors';
export { advancedMotionSensors } from './sensors/advanced-motion.sensors';
export { advancedHealthSensors } from './sensors/advanced-health.sensors';
export { advancedActuatorSensors } from './sensors/advanced-actuator.sensors';
