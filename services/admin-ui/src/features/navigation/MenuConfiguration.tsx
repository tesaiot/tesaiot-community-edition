/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import {
  Home,
  Server as DevicesOther,
  BarChart3 as Analytics,
  RefreshCw as SystemUpdate,
  Copy as ContentCopy,
  Code2 as Api,
  Key as VpnKey,
  Brain as Psychology,
  Factory,
  Activity as HealthAndSafety,
  FileText as Description,
  Users as People,
  Building2 as Business,
  Settings,
  Wrench as Build,
  Settings as SettingsApplications,
  Timeline,
  Shield as AdminPanelSettings,
  Puzzle as Extension,
  Store,
  Zap as Performance,
  Activity,
  TrendingUp,
  ShieldCheck,
  Box
} from 'lucide-react';
import { isFeatureEnabled, getFeatureFlags } from '../../config/features.config';

export interface MenuItem {
  id: string;
  label: string;
  path?: string;
  icon?: React.ElementType;
  children?: MenuItem[];
  badge?: string;
  badgeColor?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
  requiredPermission?: string;
  requiredLicense?: string;
  expanded?: boolean;
  dividerAfter?: boolean;
  disabled?: boolean;
  tooltip?: string;
  action?: string;
  external?: boolean; // Use <a> instead of React Router <Link> for external/third-party services
}

export interface MenuGroup {
  id: string;
  label: string;
  icon?: React.ElementType;
  items: MenuItem[];
  expanded?: boolean;
  visibility?: 'always' | 'role_based' | 'license_based';
}

/**
 * Complete menu configuration for TESA IoT Platform
 * Organized by functional areas and access patterns
 */
export const menuConfiguration: MenuGroup[] = [
  // Always visible - Dashboard
  {
    id: 'dashboard',
    label: 'Dashboard',
    visibility: 'always',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        path: '/dashboard',
        icon: Home,
        dividerAfter: true
      }
    ]
  },

  // Operations - Core daily tasks
  {
    id: 'operations',
    label: 'Operations',
    icon: Build,
    expanded: true,
    items: [
      {
        id: 'device-management',
        label: 'Device Management',
        path: '/devices',
        icon: DevicesOther
      }
    ]
  },

  // Extensions - Modular add-ons via Extension Store + System Tools
  {
    id: 'extensions',
    label: 'Extensions',
    icon: Extension,
    expanded: false,
    items: [
      // System monitoring tools - temporarily disabled (incomplete implementation)
      // {
      //   id: 'system-health',
      //   label: 'System Health',
      //   path: '/system-health',
      //   icon: HealthAndSafety,
      //   disabled: false,
      //   tooltip: 'Real-time system monitoring and health dashboard'
      // },
      // {
      //   id: 'activity-logs',
      //   label: 'Activity Logs',
      //   path: '/activity-logs',
      //   icon: Description,
      //   disabled: false,
      //   tooltip: 'Comprehensive activity tracking and audit logs'
      // },
      {
        id: 'performance-monitor',
        label: 'Performance Monitor',
        path: '/performance-monitor',
        icon: Performance,
        badge: 'Rust',
        badgeColor: 'success',
        disabled: false,
        tooltip: 'WebSocket performance monitoring showing Rust vs Python service comparison'
      },
      {
        id: 'divider-system',
        label: 'divider',
        dividerAfter: true
      },
      // Enterprise extensions
      {
        id: 'pki-services',
        label: 'PKI Services',
        path: '/extensions/pki-services',
        icon: VpnKey,
        badge: 'Soon',
        badgeColor: 'info',
        disabled: true,
        tooltip: 'Enterprise PKI Extensions - Coming with Extension Store'
      },
      {
        id: 'api-services',
        label: 'API Services',
        path: '/extensions/api-services',
        icon: Api,
        badge: 'Soon',
        badgeColor: 'info',
        disabled: true,
        tooltip: 'API Gateway Extensions - Coming with Extension Store'
      },
      {
        id: 'etl-data-analytics',
        label: 'ETL Data Analytics',
        path: '/extensions/etl-data-analytics',
        icon: TrendingUp,
        badge: 'Soon',
        badgeColor: 'info',
        disabled: true,
        tooltip: 'ETL Data Analytics Extensions - Coming with Extension Store'
      },
      {
        id: 'security-assessment',
        label: 'Security Assessment',
        path: '/extensions/security-assessment',
        icon: ShieldCheck,
        badge: 'Soon',
        badgeColor: 'info',
        disabled: true,
        tooltip: 'Security Assessment Extensions - Coming with Extension Store'
      },
      {
        id: 'divider-store',
        label: 'divider',
        dividerAfter: true
      },
      {
        id: '3d-model-store',
        label: '3D Model Store',
        path: '/product-models',
        icon: Box,
        badge: 'New',
        badgeColor: 'success',
        disabled: false,
        tooltip: 'Browse and download 3D models for IoT devices and industrial equipment'
      }
    ]
  },

  // Administration - User and system management
  {
    id: 'administration',
    label: 'Administration',
    icon: AdminPanelSettings,
    expanded: false,
    items: [
      {
        id: 'users',
        label: 'User Management',
        path: '/users',
        icon: People
      },
      {
        id: 'organizations',
        label: 'Organization Management',
        path: '/organizations',
        icon: Business
      },
      {
        id: 'settings',
        label: 'Settings',
        path: '/settings',
        icon: Settings
      }
    ]
  }
];

/**
 * Get filtered menu based on user permissions, license, and feature flags
 */
export function getFilteredMenu(
  userPermissions: string[],
  userLicense: string,
  userRole: string
): MenuGroup[] {
  const featureFlags = getFeatureFlags();
  
  return menuConfiguration
    .filter(group => {
      // Check group visibility
      if (group.visibility === 'license_based' && !hasRequiredLicense(userLicense, 'enterprise')) {
        return false;
      }
      return true;
    })
    .map(group => ({
      ...group,
      items: filterMenuItemsByFeatures(filterMenuItems(group.items, userPermissions, userLicense, userRole), featureFlags)
    }))
    .filter(group => group.items.length > 0); // Remove empty groups
}

/**
 * Recursively filter menu items based on permissions and license
 */
function filterMenuItems(
  items: MenuItem[],
  userPermissions: string[],
  userLicense: string,
  userRole: string
): MenuItem[] {
  return items.filter(item => {
    // Check permissions
    if (item.requiredPermission && !hasPermission(userPermissions, item.requiredPermission)) {
      return false;
    }

    // Check license
    if (item.requiredLicense && !hasRequiredLicense(userLicense, item.requiredLicense)) {
      return false;
    }

    // Filter children recursively
    if (item.children) {
      item.children = filterMenuItems(item.children, userPermissions, userLicense, userRole);
    }

    return true;
  });
}

/**
 * Filter menu items based on feature flags
 */
function filterMenuItemsByFeatures(
  items: MenuItem[],
  featureFlags: ReturnType<typeof getFeatureFlags>
): MenuItem[] {
  return items.filter(item => {
    // Skip dividers
    if (item.id === 'divider') return true;
    
    // If showing coming soon items is disabled and item is disabled, hide it
    if (!featureFlags.SHOW_COMING_SOON && item.disabled) {
      return false;
    }
    
    // Check specific feature flags
    // Note: 3d-model-store removed from feature map - it's now a standalone feature at /product-models
    const featureMap: Record<string, keyof typeof featureFlags> = {
      'system-health': 'SYSTEM_HEALTH',
      'activity-logs': 'ACTIVITY_LOGS',
      'pki-services': 'PKI_SERVICES',
      'api-services': 'API_SERVICES',
      'etl-data-analytics': 'AI_ANALYTICS',
      'security-assessment': 'INDUSTRIAL_IOT'
    };
    
    const requiredFeature = featureMap[item.id];
    
    // If feature is mapped and not enabled, check if we should show it disabled
    if (requiredFeature && !featureFlags[requiredFeature]) {
      // If SHOW_COMING_SOON is true, show as disabled
      // If false, hide completely
      return featureFlags.SHOW_COMING_SOON;
    }
    
    // Filter children recursively
    if (item.children) {
      item.children = filterMenuItemsByFeatures(item.children, featureFlags);
    }
    
    return true;
  });
}

/**
 * Check if user has required permission
 */
function hasPermission(userPermissions: string[], requiredPermission: string): boolean {
  // Admin has all permissions
  if (userPermissions.includes('*')) return true;
  
  // Check specific permission
  return userPermissions.includes(requiredPermission);
}

/**
 * Check if user has required license
 */
function hasRequiredLicense(userLicense: string, requiredLicense: string): boolean {
  const licenseLevels = {
    'basic': 1,
    'standard': 2,
    'professional': 3,
    'enterprise': 4,
    'ai_addon': 5,
    'industry_pack': 5
  };

  const userLevel = licenseLevels[userLicense] || 1;
  const requiredLevel = licenseLevels[requiredLicense] || 1;

  return userLevel >= requiredLevel;
}

/**
 * Menu display preferences
 */
export interface MenuPreferences {
  collapsed: boolean;
  expandedGroups: string[];
  favoriteItems: string[];
  recentItems: string[];
}

/**
 * Default menu preferences
 */
export const defaultMenuPreferences: MenuPreferences = {
  collapsed: false,
  expandedGroups: ['operations'],
  favoriteItems: ['dashboard', 'device-management', 'telemetry'],
  recentItems: []
};

/**
 * Save menu preferences to localStorage
 */
export function saveMenuPreferences(preferences: MenuPreferences): void {
  localStorage.setItem('tesa-menu-preferences', JSON.stringify(preferences));
}

/**
 * Load menu preferences from localStorage
 */
export function loadMenuPreferences(): MenuPreferences {
  const stored = localStorage.getItem('tesa-menu-preferences');
  return stored ? JSON.parse(stored) : defaultMenuPreferences;
}