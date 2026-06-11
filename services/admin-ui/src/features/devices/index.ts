/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// Main component
export { default as DeviceManagementWithCerts } from './DeviceManagementWithCerts';
export { default as CompleteDeviceManagement } from './DeviceManagementWithCerts';

// Types
export * from './types/device.types';

// Hooks
export { useDeviceState } from './hooks/useDeviceState';
export { useDeviceHandlers } from './hooks/useDeviceHandlers';
export { useDeviceData } from './hooks/useDeviceData';
export { useDeviceFilters } from './hooks/useDeviceFilters';

// Services
export { deviceService } from './services/deviceService';
export { certificateService } from './services/certificateService';
export { deviceOperationsService } from './services/deviceOperationsService';

// Components
export { DeviceDialog } from './components/DeviceDialog';
export { DeviceTable } from './components/table/DeviceTable';
export { DeviceDetailsDialog } from './components/dialogs/DeviceDetailsDialog';
export { QRCodeDialog } from './components/dialogs/QRCodeDialog';
export { DeviceFilterForm } from './components/forms/DeviceFilterForm';
export { DeviceStatsCards } from './components/cards/DeviceStatsCards';
export { CertificateGenerationDialog } from './components/CertificateGenerationDialog';
export { SmartTelemetryDashboard } from './components/SmartTelemetryDashboard';

// Constants
export * from './constants/device.constants';

// Utils
export * from './utils/deviceUtils';