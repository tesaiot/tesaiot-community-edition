/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Navigate, Route, Routes } from 'react-router-dom';
import { RequireAuth } from '@/auth/require-auth';
import { AuthRouting } from '@/auth/auth-routing';
import { MetronicTesaLayout } from '@/layouts/MetronicTesaLayout';

// In-scope features (TESAIoT Community Edition)
import OperationalDashboard from '@/features/dashboard/OperationalDashboard';
import DeviceManagementWithCerts from '@/features/devices/DeviceManagementWithCerts';
import { DeviceDataDashboard } from '@/features/device-data-dashboard/DeviceDataDashboard';
import FullUserManagement from '@/features/users/FullUserManagement';
import CertificateManagementPage from '@/pages/certificates/CertificateManagementPage';
import { ApiKeyManagement } from '@/features/api-keys/ApiKeyManagement';
import CompliancePage from '@/pages/compliance/CompliancePage';

// Account pages for user profile and settings
import { SimpleUserProfile } from '@/pages/account/SimpleUserProfile';

export function TesaRouting() {
  return (
    <Routes>
      <Route element={<RequireAuth />}>
        <Route element={<MetronicTesaLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<OperationalDashboard />} />
          <Route path="/devices" element={<DeviceManagementWithCerts />} />
          <Route path="/device-data-dashboard" element={<DeviceDataDashboard />} />
          <Route path="/users" element={<FullUserManagement />} />
          <Route path="/identity" element={<Navigate to="/devices" replace />} />
          <Route path="/certificates" element={<CertificateManagementPage />} />
          <Route path="/api-keys" element={<ApiKeyManagement />} />
          <Route path="/security/compliance" element={<CompliancePage />} />

          {/* Account Routes */}
          <Route path="/account/home/user-profile" element={<SimpleUserProfile />} />
          <Route path="/account/home/settings-sidebar" element={<SimpleUserProfile />} />
        </Route>
      </Route>
      <Route path="auth/*" element={<AuthRouting />} />
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}
