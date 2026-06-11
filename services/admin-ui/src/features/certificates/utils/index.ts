/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export {
  getStatusBadge,
  getDaysUntilExpiry,
  getExpiryBadge,
  formatDate,
  isExpiringSoon
} from './certificateStatus';

// Certificate statistics utilities
export {
  calculateCertificateStats,
  calculatePercentage,
  getExpiringCertificates,
  groupByAlgorithm,
  filterCertificates,
  type CertificateStats
} from './certificateStats';

// Certificate operation utilities
export {
  downloadCertificateBundle,
  copyCurlCommand,
  executeApiRequest,
  formatBytes
} from './certificateOperations';

// API endpoint configurations
export {
  certificateApiEndpoints,
  getBaseUrl,
  getCurlExamples,
  type ApiEndpoint
} from './apiEndpoints';

// Alert settings utilities
export {
  defaultAlertSettings,
  defaultAcmeSettings,
  defaultAcmeConfig,
  saveAlertSettingsToLocalStorage,
  loadAlertSettingsFromLocalStorage,
  type AlertSettings,
  type AlertThresholds,
  type AutoRenewalSettings,
  type AcmeSettings,
  type AcmeConfig
} from './alertSettings';