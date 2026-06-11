/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// Components
export { CertificateMonitoringDashboard } from './components/CertificateMonitoringDashboard';
export { CertificateRenewalDialog } from './components/CertificateRenewalDialog';
export { CertificateStatusBadge, getCertificateInfo } from './components/CertificateStatusBadge';

// Services
export { 
  certificateManagementService,
  CertificateManagementService,
  type Certificate,
  type CertificateRenewalOptions,
  type CertificateStats,
} from './services/certificateManagementService';

// Hooks
export { useCertificateManagement } from './hooks/useCertificateManagement';

// Pages
export { default as CertificateManagementPage } from '@/pages/certificates/CertificateManagementPage';