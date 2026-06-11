/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface ServiceFeature {
  id: string;
  name: string;
  description?: string;
  category: ServiceFeatureCategory;
  type: ServiceFeatureType;
  isRequired: boolean;
  isNew?: boolean;
  tierRestrictions?: string[]; // Which tiers can access this feature
  dependencies?: string[]; // Feature IDs that must be enabled for this to work
  conflicts?: string[]; // Feature IDs that cannot be enabled together
  metadata?: {
    icon?: string;
    route?: string;
    component?: string;
    menuPath?: string;
    dashboardCard?: boolean;
    apiEndpoint?: string;
    permissions?: string[];
  };
}

export interface ServiceConfiguration {
  organizationId: string;
  enabledFeatures: string[];
  customSettings?: Record<string, any>;
  createdBy: string;
  createdAt: Date;
  updatedBy?: string;
  updatedAt?: Date;
}

export interface OrganizationServiceConfig {
  id: string;
  organizationId: string;
  organizationName: string;
  tier: string;
  enabledFeatures: string[];
  customSettings: Record<string, any>;
  inheritedFromParent?: string;
  appliedToChildren: boolean;
  lastModified: Date;
  lastModifiedBy: string;
}

export interface ServiceConfigurationAuditLog {
  id: string;
  organizationId: string;
  featureId: string;
  featureName: string;
  action: 'enable' | 'disable' | 'update' | 'create' | 'delete';
  previousState?: boolean;
  newState: boolean;
  reason?: string;
  performedBy: string;
  performedAt: Date;
  metadata?: {
    ipAddress?: string;
    userAgent?: string;
    sessionId?: string;
    previousSettings?: Record<string, any>;
    newSettings?: Record<string, any>;
  };
}

export enum ServiceFeatureCategory {
  CORE_FEATURES = 'core_features',
  DASHBOARD_CARDS = 'dashboard_cards',
  MENU_ITEMS = 'menu_items',
  FEATURE_BUTTONS = 'feature_buttons',
  ANALYTICS = 'analytics',
  SECURITY = 'security',
  INTEGRATIONS = 'integrations',
  EXTENSIONS = 'extensions',
}

export enum ServiceFeatureType {
  MENU_ITEM = 'menu_item',
  DASHBOARD_WIDGET = 'dashboard_widget',
  FEATURE_TOGGLE = 'feature_toggle',
  API_ACCESS = 'api_access',
  UI_COMPONENT = 'ui_component',
  SERVICE_INTEGRATION = 'service_integration',
  ANALYTICS_MODULE = 'analytics_module',
  SECURITY_FEATURE = 'security_feature',
}

export interface ServiceConfigurationStats {
  totalFeatures: number;
  totalOrganizations: number;
  activeConfigurations: number;
  recentChanges: number;
  featuresByCategory: Record<ServiceFeatureCategory, number>;
  mostEnabledFeatures: Array<{ id: string; name: string; count: number }>;
  leastEnabledFeatures: Array<{ id: string; name: string; count: number }>;
}

export interface ServiceConfigPreview {
  organizationId: string;
  menuItems: Array<{
    id: string;
    name: string;
    visible: boolean;
    reason?: string;
  }>;
  dashboardCards: Array<{
    id: string;
    name: string;
    visible: boolean;
    reason?: string;
  }>;
  featureButtons: Array<{
    id: string;
    name: string;
    visible: boolean;
    reason?: string;
  }>;
  apiEndpoints: Array<{
    id: string;
    endpoint: string;
    accessible: boolean;
    reason?: string;
  }>;
  currentState: {
    visibleMenuItems: number;
    visibleCards: number;
    accessibleEndpoints: number;
  };
  enabledFeatures: number;
  disabledFeatures: number;
  affectedComponents: number;
  warnings: string[];
  errors: string[];
}

export interface ServiceConfigurationBulkOperation {
  organizationIds: string[];
  featureIds: string[];
  action: 'enable' | 'disable';
  reason?: string;
  applyToChildren?: boolean;
  schedule?: Date;
}

export interface ServiceConfigurationFilter {
  organizationIds?: string[];
  categories?: ServiceFeatureCategory[];
  tiers?: string[];
  enabled?: boolean;
  hasCustomSettings?: boolean;
  search?: string;
}

export interface ServiceConfigurationSearchResult {
  organizations: Array<{
    id: string;
    name: string;
    tier: string;
    enabledFeatureCount: number;
    lastModified: Date;
  }>;
  features: Array<{
    id: string;
    name: string;
    category: ServiceFeatureCategory;
    enabledInOrganizations: number;
    totalOrganizations: number;
  }>;
  totalResults: number;
}

export interface OrganizationTierLimits {
  tier: string;
  limits: {
    maxDevices?: number;
    maxUsers?: number;
    maxApiKeys?: number;
    maxDataRetentionDays?: number;
    maxStorageGB?: number;
    maxCertificates?: number;
    customDashboards?: boolean;
    advancedAnalytics?: boolean;
    prioritySupport?: boolean;
    whiteLabeling?: boolean;
  };
  allowedFeatures: string[];
  restrictedFeatures: string[];
}

export interface ServiceConfigurationTemplate {
  id: string;
  name: string;
  description: string;
  tier: string;
  enabledFeatures: string[];
  customSettings: Record<string, any>;
  isDefault: boolean;
  createdBy: string;
  createdAt: Date;
}

export interface FeatureDependencyGraph {
  [featureId: string]: {
    dependencies: string[];
    dependents: string[];
    conflicts: string[];
    required: boolean;
  };
}

export interface ServiceConfigurationValidation {
  isValid: boolean;
  errors: Array<{
    featureId: string;
    error: string;
    severity: 'error' | 'warning';
  }>;
  warnings: Array<{
    featureId: string;
    warning: string;
    impact: string;
  }>;
  suggestions: Array<{
    featureId: string;
    suggestion: string;
    reason: string;
  }>;
}