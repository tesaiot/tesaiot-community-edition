/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import type {
  ServiceFeature,
  ServiceConfiguration,
  OrganizationServiceConfig,
  ServiceConfigurationAuditLog,
  ServiceConfigurationStats,
  ServiceConfigPreview,
  ServiceConfigurationBulkOperation,
  ServiceConfigurationTemplate,
  ServiceConfigurationValidation,
  FeatureDependencyGraph,
  OrganizationTierLimits,
  ServiceFeatureCategory,
} from '../types/service-configuration.types';

// Mock data for development - In production, this would come from real API calls
const MOCK_SERVICE_FEATURES: ServiceFeature[] = [
  // Core Features
  {
    id: 'device-management',
    name: 'Device Management',
    description: 'Manage IoT devices, credentials, and certificates',
    category: ServiceFeatureCategory.CORE_FEATURES,
    type: 'feature_toggle' as any,
    isRequired: true,
    metadata: {
      route: '/devices',
      component: 'DeviceManagement',
      permissions: ['device:read', 'device:write'],
    },
  },
  {
    id: 'user-management',
    name: 'User Management',
    description: 'Manage users and permissions',
    category: ServiceFeatureCategory.CORE_FEATURES,
    type: 'feature_toggle' as any,
    isRequired: true,
    metadata: {
      route: '/users',
      component: 'UserManagement',
      permissions: ['user:read', 'user:write'],
    },
  },
  {
    id: 'certificate-management',
    name: 'Certificate Management',
    description: 'PKI certificate lifecycle management',
    category: ServiceFeatureCategory.CORE_FEATURES,
    type: 'feature_toggle' as any,
    isRequired: false,
    metadata: {
      route: '/certificates',
      component: 'CertificateManagement',
      permissions: ['certificate:read', 'certificate:write'],
    },
  },
  {
    id: 'organization-management',
    name: 'Organization Management',
    description: 'Manage sub-organizations and hierarchies',
    category: ServiceFeatureCategory.CORE_FEATURES,
    type: 'feature_toggle' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    metadata: {
      route: '/organizations',
      component: 'OrganizationManagement',
      permissions: ['organization:read', 'organization:write'],
    },
  },

  // Menu Items
  {
    id: 'menu-devices',
    name: 'Devices Menu',
    description: 'Show devices in main navigation',
    category: ServiceFeatureCategory.MENU_ITEMS,
    type: 'menu_item' as any,
    isRequired: true,
    dependencies: ['device-management'],
    metadata: {
      menuPath: '/devices',
      icon: 'Monitor',
    },
  },
  {
    id: 'menu-analytics',
    name: 'Analytics Menu',
    description: 'Show analytics in main navigation',
    category: ServiceFeatureCategory.MENU_ITEMS,
    type: 'menu_item' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    metadata: {
      menuPath: '/analytics',
      icon: 'BarChart3',
    },
  },
  {
    id: 'menu-security',
    name: 'Security Menu',
    description: 'Show security monitoring in navigation',
    category: ServiceFeatureCategory.MENU_ITEMS,
    type: 'menu_item' as any,
    isRequired: false,
    tierRestrictions: ['commercial', 'enterprise'],
    metadata: {
      menuPath: '/security',
      icon: 'Shield',
    },
  },
  {
    id: 'menu-industrial',
    name: 'Industrial IoT Menu',
    description: 'Show Industrial IoT features',
    category: ServiceFeatureCategory.MENU_ITEMS,
    type: 'menu_item' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    metadata: {
      menuPath: '/industrial',
      icon: 'Factory',
    },
  },

  // Dashboard Cards
  {
    id: 'dashboard-device-stats',
    name: 'Device Statistics Card',
    description: 'Show device count and status overview',
    category: ServiceFeatureCategory.DASHBOARD_CARDS,
    type: 'dashboard_widget' as any,
    isRequired: true,
    dependencies: ['device-management'],
    metadata: {
      component: 'DeviceStatsCard',
      dashboardCard: true,
    },
  },
  {
    id: 'dashboard-system-health',
    name: 'System Health Card',
    description: 'Show system performance metrics',
    category: ServiceFeatureCategory.DASHBOARD_CARDS,
    type: 'dashboard_widget' as any,
    isRequired: false,
    metadata: {
      component: 'SystemHealthCard',
      dashboardCard: true,
    },
  },
  {
    id: 'dashboard-real-time-data',
    name: 'Real-time Data Card',
    description: 'Show live telemetry data',
    category: ServiceFeatureCategory.DASHBOARD_CARDS,
    type: 'dashboard_widget' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    metadata: {
      component: 'RealTimeDataCard',
      dashboardCard: true,
    },
  },
  {
    id: 'dashboard-ai-insights',
    name: 'AI Insights Card',
    description: 'Show AI-powered analytics and predictions',
    category: ServiceFeatureCategory.DASHBOARD_CARDS,
    type: 'dashboard_widget' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    isNew: true,
    dependencies: ['analytics-ai'],
    metadata: {
      component: 'AIInsightsCard',
      dashboardCard: true,
    },
  },

  // Feature Buttons
  {
    id: 'button-bulk-operations',
    name: 'Bulk Operations',
    description: 'Enable bulk device operations',
    category: ServiceFeatureCategory.FEATURE_BUTTONS,
    type: 'feature_toggle' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    metadata: {
      component: 'BulkOperationsButton',
    },
  },
  {
    id: 'button-export-data',
    name: 'Export Data',
    description: 'Enable data export functionality',
    category: ServiceFeatureCategory.FEATURE_BUTTONS,
    type: 'feature_toggle' as any,
    isRequired: false,
    metadata: {
      component: 'ExportDataButton',
    },
  },
  {
    id: 'button-advanced-filters',
    name: 'Advanced Filters',
    description: 'Enable advanced filtering options',
    category: ServiceFeatureCategory.FEATURE_BUTTONS,
    type: 'feature_toggle' as any,
    isRequired: false,
    tierRestrictions: ['commercial', 'enterprise'],
    metadata: {
      component: 'AdvancedFiltersButton',
    },
  },

  // Analytics Features
  {
    id: 'analytics-basic',
    name: 'Basic Analytics',
    description: 'Device usage and basic metrics',
    category: ServiceFeatureCategory.ANALYTICS,
    type: 'analytics_module' as any,
    isRequired: false,
    metadata: {
      component: 'BasicAnalytics',
      apiEndpoint: '/api/analytics/basic',
    },
  },
  {
    id: 'analytics-advanced',
    name: 'Advanced Analytics',
    description: 'Custom dashboards and advanced metrics',
    category: ServiceFeatureCategory.ANALYTICS,
    type: 'analytics_module' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    dependencies: ['analytics-basic'],
    metadata: {
      component: 'AdvancedAnalytics',
      apiEndpoint: '/api/analytics/advanced',
    },
  },
  {
    id: 'analytics-ai',
    name: 'AI-Powered Analytics',
    description: 'Machine learning insights and predictions',
    category: ServiceFeatureCategory.ANALYTICS,
    type: 'analytics_module' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    isNew: true,
    dependencies: ['analytics-advanced'],
    metadata: {
      component: 'AIAnalytics',
      apiEndpoint: '/api/analytics/ai',
    },
  },

  // Security Features
  {
    id: 'security-monitoring',
    name: 'Security Monitoring',
    description: 'Monitor security events and threats',
    category: ServiceFeatureCategory.SECURITY,
    type: 'security_feature' as any,
    isRequired: false,
    tierRestrictions: ['commercial', 'enterprise'],
    metadata: {
      component: 'SecurityMonitoring',
      apiEndpoint: '/api/security/monitoring',
    },
  },
  {
    id: 'security-compliance',
    name: 'Compliance Reporting',
    description: 'Generate compliance reports and audits',
    category: ServiceFeatureCategory.SECURITY,
    type: 'security_feature' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    dependencies: ['security-monitoring'],
    metadata: {
      component: 'ComplianceReporting',
      apiEndpoint: '/api/security/compliance',
    },
  },

  // Integrations
  {
    id: 'integration-api-keys',
    name: 'API Key Management',
    description: 'Generate and manage API keys',
    category: ServiceFeatureCategory.INTEGRATIONS,
    type: 'api_access' as any,
    isRequired: false,
    metadata: {
      component: 'ApiKeyManagement',
      apiEndpoint: '/api/integrations/api-keys',
    },
  },
  {
    id: 'integration-webhooks',
    name: 'Webhook Integration',
    description: 'Configure webhook endpoints',
    category: ServiceFeatureCategory.INTEGRATIONS,
    type: 'service_integration' as any,
    isRequired: false,
    tierRestrictions: ['professional', 'commercial', 'enterprise'],
    metadata: {
      component: 'WebhookIntegration',
      apiEndpoint: '/api/integrations/webhooks',
    },
  },
  {
    id: 'integration-mqtt-bridge',
    name: 'MQTT Bridge',
    description: 'Bridge to external MQTT brokers',
    category: ServiceFeatureCategory.INTEGRATIONS,
    type: 'service_integration' as any,
    isRequired: false,
    tierRestrictions: ['commercial', 'enterprise'],
    metadata: {
      component: 'MQTTBridge',
      apiEndpoint: '/api/integrations/mqtt-bridge',
    },
  },

  // Extensions
  {
    id: 'extension-custom-widgets',
    name: 'Custom Widgets',
    description: 'Create custom dashboard widgets',
    category: ServiceFeatureCategory.EXTENSIONS,
    type: 'ui_component' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    metadata: {
      component: 'CustomWidgets',
    },
  },
  {
    id: 'extension-white-labeling',
    name: 'White Labeling',
    description: 'Customize branding and appearance',
    category: ServiceFeatureCategory.EXTENSIONS,
    type: 'ui_component' as any,
    isRequired: false,
    tierRestrictions: ['enterprise'],
    metadata: {
      component: 'WhiteLabeling',
    },
  },
];

const MOCK_ORGANIZATIONS = [
  { id: 'org-bdh', name: 'BDH Corporation', tier: 'enterprise' },
  { id: 'org-tesa', name: 'TESA IoT Platform', tier: 'enterprise' },
  { id: 'org-demo-pro', name: 'Demo Professional Org', tier: 'professional' },
  { id: 'org-demo-com', name: 'Demo Commercial Org', tier: 'commercial' },
  { id: 'org-demo-community', name: 'Demo Community Org', tier: 'community' },
];

export class ServiceConfigurationService {
  private static getBaseUrl = () => {
    let baseURL = import.meta.env.VITE_API_URL || '';
    
    // If no explicit URL or it's localhost, use current host
    if (!baseURL || baseURL.includes('localhost')) {
      const protocol = window.location.protocol;
      const hostname = window.location.hostname;
      const port = window.location.port;
      
      // If accessed through port 80/443 (NGINX), use same origin
      if (!port || port === '80' || port === '443') {
        baseURL = ''; // Empty string means same origin
      } else {
        baseURL = `${protocol}//${hostname}:${port}`;
      }
    }
    
    return baseURL || '/';
  };
  
  private static baseUrl = ServiceConfigurationService.getBaseUrl();

  static async getServiceFeatures(): Promise<ServiceFeature[]> {
    // In development, return mock data
    if (import.meta.env.DEV) {
      return MOCK_SERVICE_FEATURES;
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/service-features`);
      if (!response.ok) {
        throw new Error('Failed to fetch service features');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching service features:', error);
      // Fallback to mock data in case of error
      return MOCK_SERVICE_FEATURES;
    }
  }

  static async getOrganizations(): Promise<Array<{ id: string; name: string; tier: string }>> {
    // In development, return mock data
    if (import.meta.env.DEV) {
      return MOCK_ORGANIZATIONS;
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/organizations`);
      if (!response.ok) {
        throw new Error('Failed to fetch organizations');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching organizations:', error);
      return MOCK_ORGANIZATIONS;
    }
  }

  static async getOrganizationConfiguration(organizationId: string): Promise<OrganizationServiceConfig> {
    // In development, return mock data
    if (import.meta.env.DEV) {
      const org = MOCK_ORGANIZATIONS.find(o => o.id === organizationId);
      const enabledFeatures = this.getMockEnabledFeatures(org?.tier || 'community');
      
      return {
        id: `config-${organizationId}`,
        organizationId,
        organizationName: org?.name || 'Unknown Organization',
        tier: org?.tier || 'community',
        enabledFeatures,
        customSettings: {},
        appliedToChildren: false,
        lastModified: new Date(),
        lastModifiedBy: 'admin@example.com',
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/organizations/${organizationId}/configuration`);
      if (!response.ok) {
        throw new Error('Failed to fetch organization configuration');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching organization configuration:', error);
      throw error;
    }
  }

  static async updateOrganizationConfiguration(
    organizationId: string,
    updates: { enabledFeatures: string[]; customSettings?: Record<string, any> }
  ): Promise<OrganizationServiceConfig> {
    // In development, simulate API call
    if (import.meta.env.DEV) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const org = MOCK_ORGANIZATIONS.find(o => o.id === organizationId);
      return {
        id: `config-${organizationId}`,
        organizationId,
        organizationName: org?.name || 'Unknown Organization',
        tier: org?.tier || 'community',
        enabledFeatures: updates.enabledFeatures,
        customSettings: updates.customSettings || {},
        appliedToChildren: false,
        lastModified: new Date(),
        lastModifiedBy: 'admin@example.com',
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/organizations/${organizationId}/configuration`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error('Failed to update organization configuration');
      }
      return await response.json();
    } catch (error) {
      console.error('Error updating organization configuration:', error);
      throw error;
    }
  }

  static async getStats(): Promise<ServiceConfigurationStats> {
    // In development, return mock data
    if (import.meta.env.DEV) {
      return {
        totalFeatures: MOCK_SERVICE_FEATURES.length,
        totalOrganizations: MOCK_ORGANIZATIONS.length,
        activeConfigurations: MOCK_ORGANIZATIONS.length,
        recentChanges: 5,
        featuresByCategory: {
          [ServiceFeatureCategory.CORE_FEATURES]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.CORE_FEATURES).length,
          [ServiceFeatureCategory.DASHBOARD_CARDS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.DASHBOARD_CARDS).length,
          [ServiceFeatureCategory.MENU_ITEMS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.MENU_ITEMS).length,
          [ServiceFeatureCategory.FEATURE_BUTTONS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.FEATURE_BUTTONS).length,
          [ServiceFeatureCategory.ANALYTICS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.ANALYTICS).length,
          [ServiceFeatureCategory.SECURITY]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.SECURITY).length,
          [ServiceFeatureCategory.INTEGRATIONS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.INTEGRATIONS).length,
          [ServiceFeatureCategory.EXTENSIONS]: MOCK_SERVICE_FEATURES.filter(f => f.category === ServiceFeatureCategory.EXTENSIONS).length,
        },
        mostEnabledFeatures: [
          { id: 'device-management', name: 'Device Management', count: 5 },
          { id: 'user-management', name: 'User Management', count: 5 },
          { id: 'dashboard-device-stats', name: 'Device Statistics Card', count: 5 },
        ],
        leastEnabledFeatures: [
          { id: 'extension-white-labeling', name: 'White Labeling', count: 1 },
          { id: 'analytics-ai', name: 'AI-Powered Analytics', count: 1 },
          { id: 'security-compliance', name: 'Compliance Reporting', count: 1 },
        ],
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/service-configuration/stats`);
      if (!response.ok) {
        throw new Error('Failed to fetch stats');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching stats:', error);
      throw error;
    }
  }

  static async getAuditLogs(organizationId: string): Promise<ServiceConfigurationAuditLog[]> {
    // In development, return mock data
    if (import.meta.env.DEV) {
      return [
        {
          id: 'audit-1',
          organizationId,
          featureId: 'analytics-ai',
          featureName: 'AI-Powered Analytics',
          action: 'enable',
          previousState: false,
          newState: true,
          reason: 'Enterprise tier upgrade',
          performedBy: 'admin@example.com',
          performedAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        },
        {
          id: 'audit-2',
          organizationId,
          featureId: 'security-compliance',
          featureName: 'Compliance Reporting',
          action: 'enable',
          previousState: false,
          newState: true,
          reason: 'Compliance requirements',
          performedBy: 'admin@example.com',
          performedAt: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
        },
        {
          id: 'audit-3',
          organizationId,
          featureId: 'integration-webhooks',
          featureName: 'Webhook Integration',
          action: 'disable',
          previousState: true,
          newState: false,
          reason: 'Security review',
          performedBy: 'admin@example.com',
          performedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
        },
      ];
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/organizations/${organizationId}/audit-logs`);
      if (!response.ok) {
        throw new Error('Failed to fetch audit logs');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      return [];
    }
  }

  static async previewConfiguration(
    organizationId: string,
    config: { enabledFeatures: string[] }
  ): Promise<ServiceConfigPreview> {
    // In development, return mock preview data
    if (import.meta.env.DEV) {
      await new Promise(resolve => setTimeout(resolve, 500));

      const menuItems = MOCK_SERVICE_FEATURES
        .filter(f => f.category === ServiceFeatureCategory.MENU_ITEMS)
        .map(f => ({
          id: f.id,
          name: f.name,
          visible: config.enabledFeatures.includes(f.id),
          reason: config.enabledFeatures.includes(f.id) ? 'Enabled' : 'Disabled in configuration',
        }));

      const dashboardCards = MOCK_SERVICE_FEATURES
        .filter(f => f.category === ServiceFeatureCategory.DASHBOARD_CARDS)
        .map(f => ({
          id: f.id,
          name: f.name,
          visible: config.enabledFeatures.includes(f.id),
          reason: config.enabledFeatures.includes(f.id) ? 'Enabled' : 'Disabled in configuration',
        }));

      const featureButtons = MOCK_SERVICE_FEATURES
        .filter(f => f.category === ServiceFeatureCategory.FEATURE_BUTTONS)
        .map(f => ({
          id: f.id,
          name: f.name,
          visible: config.enabledFeatures.includes(f.id),
          reason: config.enabledFeatures.includes(f.id) ? 'Enabled' : 'Disabled in configuration',
        }));

      const warnings: string[] = [];
      
      // Check for dependency issues
      config.enabledFeatures.forEach(featureId => {
        const feature = MOCK_SERVICE_FEATURES.find(f => f.id === featureId);
        if (feature?.dependencies) {
          feature.dependencies.forEach(depId => {
            if (!config.enabledFeatures.includes(depId)) {
              warnings.push(`${feature.name} requires ${MOCK_SERVICE_FEATURES.find(f => f.id === depId)?.name || depId} to be enabled`);
            }
          });
        }
      });

      return {
        organizationId,
        menuItems,
        dashboardCards,
        featureButtons,
        apiEndpoints: [],
        currentState: {
          visibleMenuItems: 2,
          visibleCards: 2,
          accessibleEndpoints: 5,
        },
        enabledFeatures: config.enabledFeatures.length,
        disabledFeatures: MOCK_SERVICE_FEATURES.length - config.enabledFeatures.length,
        affectedComponents: menuItems.length + dashboardCards.length + featureButtons.length,
        warnings,
        errors: [],
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/platform-admin/organizations/${organizationId}/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error('Failed to generate preview');
      }
      return await response.json();
    } catch (error) {
      console.error('Error generating preview:', error);
      throw error;
    }
  }

  private static getMockEnabledFeatures(tier: string): string[] {
    const allFeatures = MOCK_SERVICE_FEATURES;
    
    switch (tier) {
      case 'enterprise':
        return allFeatures.map(f => f.id); // All features for enterprise
      case 'commercial':
        return allFeatures
          .filter(f => !f.tierRestrictions || f.tierRestrictions.includes('commercial'))
          .map(f => f.id);
      case 'professional':
        return allFeatures
          .filter(f => !f.tierRestrictions || f.tierRestrictions.includes('professional'))
          .map(f => f.id);
      case 'community':
      default:
        return allFeatures
          .filter(f => !f.tierRestrictions || f.tierRestrictions.includes('community'))
          .map(f => f.id);
    }
  }
}