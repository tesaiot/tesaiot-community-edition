/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useEffect } from 'react';
import axios from 'axios';

interface ServiceConfiguration {
  organization_id: string;
  features: {
    [key: string]: boolean;
  };
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  updated_by?: string;
}

export const useServiceConfiguration = (organizationId: string | null) => {
  const [config, setConfig] = useState<ServiceConfiguration | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!organizationId || organizationId === 'default') {
      // Return default config where all features are enabled
      setConfig({
        organization_id: 'default',
        features: {
          menu_dashboard: true,
          menu_devices: true,
          menu_users: true,
          menu_security: true,
          menu_certificates: true,
          menu_analytics: true,
          menu_compliance: true,
          menu_settings: true,
        }
      });
      return;
    }

    const fetchConfig = async () => {
      setLoading(true);
      try {
        // Get auth token from localStorage
        const token = localStorage.getItem('access_token');
        
        const response = await axios.get(
          `/api/v1/platform-admin/organizations/${organizationId}/configuration`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
        
        if (response.data && response.data.data) {
          setConfig(response.data.data);
        }
      } catch (err) {
        console.error('Failed to fetch service configuration:', err);
        setError('Failed to load service configuration');
        // Set default config on error
        setConfig({
          organization_id: organizationId,
          features: {
            menu_dashboard: true,
            menu_devices: true,
            menu_users: true,
            menu_security: true,
            menu_certificates: true,
            menu_analytics: true,
            menu_compliance: true,
            menu_settings: true,
          }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [organizationId]);

  return { config, loading, error };
};