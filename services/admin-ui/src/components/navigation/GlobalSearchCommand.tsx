/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Global Search Command Palette
 *
 * Implements best practices for admin portal global search:
 * - Command palette pattern (⌘K / Ctrl+K)
 * - Fuzzy search across navigation, devices, users, actions
 * - Keyboard shortcuts support
 * - Quick actions for common tasks
 * - RBAC filtering based on user role
 * - Comprehensive sub-page coverage
 *
 * Based on:
 * - shadcn/ui Command component (cmdk)
 * - Modern admin dashboard patterns (2025)
 *
 * Version: 2.0.0 (Added RBAC filtering and comprehensive sub-pages)
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  Home,
  Server,
  Users,
  Key,
  Activity,
  FileText,
  BarChart3,
  CheckCircle,
  Building2,
  Crown,
  Settings,
  LogOut,
  Plus,
  Search,
  Bell,
  Shield,
  Cpu,
  FileCheck,
  ShieldCheck,
  Lock,
  UserCog,
  Database,
  Zap,
  Clock,
  AlertCircle,
  Download,
  Upload,
  Wifi,
  HardDrive,
  RefreshCw,
  CheckSquare,
  UserCheck,
  Code,
  Package,
  Box,
  ExternalLink,
} from 'lucide-react';
import { getFeatureFlags } from '@/config/features.config';

type UserRole = 'admin' | 'organization_admin' | 'user' | 'platform_admin' | 'super_admin';

interface SearchItem {
  id: string;
  title: string;
  description?: string;
  icon: React.ReactNode;
  href?: string;
  action?: () => void;
  keywords?: string[];
  group: 'navigation' | 'actions' | 'sub-pages' | 'settings' | 'reports';
  requiredRoles?: UserRole[];
  requiredFeature?: string;
}

interface GlobalSearchCommandProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userRole?: UserRole;
}

// Helper function to check if user has required role
function hasRequiredRole(userRole: UserRole | undefined, requiredRoles?: UserRole[]): boolean {
  if (!requiredRoles || requiredRoles.length === 0) return true;
  if (!userRole) return false;

  // Role hierarchy: super_admin > platform_admin > admin > organization_admin > user
  const roleHierarchy: Record<UserRole, number> = {
    'super_admin': 5,
    'platform_admin': 4,
    'admin': 3,
    'organization_admin': 2,
    'user': 1,
  };

  const userLevel = roleHierarchy[userRole] || 0;
  return requiredRoles.some(role => userLevel >= roleHierarchy[role]);
}

export function GlobalSearchCommand({
  open,
  onOpenChange,
  userRole = 'user' // Default to most restrictive role
}: GlobalSearchCommandProps) {
  const navigate = useNavigate();
  const [mounted, setMounted] = useState(false);
  const featureFlags = getFeatureFlags();

  // Keyboard shortcut (Ctrl+K or Cmd+K)
  useEffect(() => {
    setMounted(true);

    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, onOpenChange]);

  const handleSelect = useCallback((item: SearchItem) => {
    onOpenChange(false);

    if (item.action) {
      item.action();
    } else if (item.href) {
      navigate(item.href);
    }
  }, [navigate, onOpenChange]);

  // Comprehensive search items with RBAC and sub-pages
  const allSearchItems: SearchItem[] = useMemo(() => [
    // ============ Navigation Pages (Main) ============
    {
      id: 'nav-dashboard',
      title: 'Dashboard',
      description: 'Platform overview and metrics',
      icon: <Home className="h-4 w-4" />,
      href: '/dashboard',
      keywords: ['home', 'overview', 'main'],
      group: 'navigation',
    },
    {
      id: 'nav-devices',
      title: 'Devices & Identity',
      description: 'Manage IoT devices and provisioning',
      icon: <Server className="h-4 w-4" />,
      href: '/devices',
      keywords: ['iot', 'device', 'hardware', 'provision'],
      group: 'navigation',
    },
    {
      id: 'nav-users',
      title: 'Users',
      description: 'Team members and access control',
      icon: <Users className="h-4 w-4" />,
      href: '/users',
      keywords: ['team', 'people', 'access', 'roles', 'permissions'],
      group: 'navigation',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'nav-certificates',
      title: 'Certificates',
      description: 'PKI certificates and key provisioning',
      icon: <Key className="h-4 w-4" />,
      href: '/certificates',
      keywords: ['pki', 'ssl', 'tls', 'security', 'crypto'],
      group: 'navigation',
    },
    {
      id: 'nav-system-health',
      title: 'System Health',
      description: 'Monitor platform performance',
      icon: <Activity className="h-4 w-4" />,
      href: '/system-health',
      keywords: ['monitoring', 'status', 'uptime', 'performance'],
      group: 'navigation',
      requiredFeature: 'SYSTEM_HEALTH',
    },
    {
      id: 'nav-logs',
      title: 'Activity Logs',
      description: 'Audit trails and system events',
      icon: <FileText className="h-4 w-4" />,
      href: '/activity-logs',
      keywords: ['audit', 'events', 'history', 'tracking'],
      group: 'navigation',
      requiredFeature: 'ACTIVITY_LOGS',
    },
    {
      id: 'nav-analytics',
      title: 'Analytics',
      description: 'Usage trends and insights',
      icon: <BarChart3 className="h-4 w-4" />,
      href: '/analytics',
      keywords: ['reports', 'statistics', 'metrics', 'trends'],
      group: 'navigation',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
      requiredFeature: 'ANALYTICS',
    },
    {
      id: 'nav-compliance',
      title: 'Compliance',
      description: 'Industry standards and certification',
      icon: <CheckCircle className="h-4 w-4" />,
      href: '/security/compliance',
      keywords: ['etsi', 'standards', 'iso', 'gdpr', 'audit'],
      group: 'navigation',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'nav-organizations',
      title: 'Organizations',
      description: 'Multi-tenant management',
      icon: <Building2 className="h-4 w-4" />,
      href: '/organizations',
      keywords: ['tenants', 'orgs', 'departments'],
      group: 'navigation',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'nav-api-keys',
      title: 'API Keys',
      description: 'Integration credentials',
      icon: <Code className="h-4 w-4" />,
      href: '/api-keys',
      keywords: ['tokens', 'credentials', 'integration', 'developer'],
      group: 'navigation',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'nav-platform-admin',
      title: 'Platform Admin',
      description: 'Platform administration',
      icon: <Crown className="h-4 w-4" />,
      href: '/platform-admin',
      keywords: ['admin', 'super', 'configuration'],
      group: 'navigation',
      requiredRoles: ['platform_admin', 'super_admin'],
    },

    // ============ Extensions ============
    {
      id: 'nav-3d-model-store',
      title: '3D Model Store',
      description: 'Product industrial design and 3D model management',
      icon: <Box className="h-4 w-4" />,
      href: '/product-models',
      keywords: ['3d', 'model', 'product', 'industrial', 'design', 'cad', 'store', 'extension'],
      group: 'navigation',
    },

    // ============ Device Management Sub-Pages ============
    {
      id: 'sub-device-provisioning',
      title: 'Device Provisioning',
      description: 'Register and provision new devices',
      icon: <Plus className="h-4 w-4" />,
      href: '/devices?tab=provisioning',
      keywords: ['register', 'provision', 'onboard', 'setup', 'device'],
      group: 'sub-pages',
    },
    {
      id: 'sub-device-credentials',
      title: 'Device Credentials',
      description: 'Manage device authentication credentials',
      icon: <Lock className="h-4 w-4" />,
      href: '/devices?tab=credentials',
      keywords: ['credentials', 'auth', 'certificate', 'device', 'security'],
      group: 'sub-pages',
    },
    {
      id: 'sub-device-health',
      title: 'Device Health',
      description: 'Monitor device status and health',
      icon: <Activity className="h-4 w-4" />,
      href: '/devices?tab=health',
      keywords: ['health', 'status', 'monitor', 'device', 'uptime'],
      group: 'sub-pages',
    },
    {
      id: 'sub-device-telemetry',
      title: 'Device Telemetry',
      description: 'View real-time device data',
      icon: <BarChart3 className="h-4 w-4" />,
      href: '/devices?tab=telemetry',
      keywords: ['telemetry', 'data', 'metrics', 'device', 'realtime'],
      group: 'sub-pages',
    },

    // ============ Certificate Management Sub-Pages ============
    {
      id: 'sub-cert-settings',
      title: 'Certificate Settings',
      description: 'Configure certificate policies',
      icon: <Settings className="h-4 w-4" />,
      href: '/certificates?tab=settings',
      keywords: ['certificate', 'settings', 'policy', 'config'],
      group: 'sub-pages',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'sub-cert-report',
      title: 'Certificate Report',
      description: 'View certificate inventory and expiry',
      icon: <FileCheck className="h-4 w-4" />,
      href: '/certificates?tab=report',
      keywords: ['certificate', 'report', 'inventory', 'expiry', 'audit'],
      group: 'reports',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'sub-cert-generation',
      title: 'Certificate Generation',
      description: 'Generate new certificates',
      icon: <Plus className="h-4 w-4" />,
      href: '/certificates?tab=generate',
      keywords: ['certificate', 'generate', 'create', 'new', 'issue'],
      group: 'sub-pages',
    },
    {
      id: 'sub-cert-renewal',
      title: 'Certificate Renewal',
      description: 'Renew expiring certificates',
      icon: <RefreshCw className="h-4 w-4" />,
      href: '/certificates?tab=renewal',
      keywords: ['certificate', 'renew', 'refresh', 'expiry'],
      group: 'sub-pages',
    },
    {
      id: 'sub-acme-config',
      title: 'ACME Configuration',
      description: 'Configure ACME auto-renewal',
      icon: <ShieldCheck className="h-4 w-4" />,
      href: '/certificates?tab=acme',
      keywords: ['acme', 'letsencrypt', 'auto', 'renewal', 'certificate'],
      group: 'settings',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
    },

    // ============ User Management Sub-Pages ============
    {
      id: 'sub-user-profile',
      title: 'User Profile',
      description: 'View and edit your profile',
      icon: <UserCog className="h-4 w-4" />,
      href: '/account/home/user-profile',
      keywords: ['profile', 'account', 'settings', 'personal'],
      group: 'sub-pages',
    },
    {
      id: 'sub-security-settings',
      title: 'Security Settings',
      description: 'Password, MFA, and security preferences',
      icon: <Shield className="h-4 w-4" />,
      href: '/account/home/security-settings',
      keywords: ['security', 'password', 'mfa', '2fa', 'authentication'],
      group: 'settings',
    },
    {
      id: 'sub-user-roles',
      title: 'User Roles & Permissions',
      description: 'Manage roles and access control',
      icon: <UserCheck className="h-4 w-4" />,
      href: '/users?tab=roles',
      keywords: ['roles', 'permissions', 'rbac', 'access', 'control'],
      group: 'sub-pages',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },

    // ============ Organization Sub-Pages ============
    {
      id: 'sub-org-settings',
      title: 'Organization Settings',
      description: 'Configure organization preferences',
      icon: <Settings className="h-4 w-4" />,
      href: '/organizations?tab=settings',
      keywords: ['organization', 'settings', 'config', 'tenant'],
      group: 'settings',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'sub-org-departments',
      title: 'Department Management',
      description: 'Manage organizational units',
      icon: <Building2 className="h-4 w-4" />,
      href: '/organizations?tab=departments',
      keywords: ['department', 'unit', 'organization', 'structure'],
      group: 'sub-pages',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },

    // ============ Platform Admin Sub-Pages ============
    {
      id: 'sub-service-config',
      title: 'Service Configuration',
      description: 'Configure platform services',
      icon: <Cpu className="h-4 w-4" />,
      href: '/platform-admin?tab=services',
      keywords: ['service', 'config', 'platform', 'docker', 'container'],
      group: 'settings',
      requiredRoles: ['platform_admin', 'super_admin'],
    },
    {
      id: 'sub-platform-settings',
      title: 'Platform Settings',
      description: 'Global platform configuration',
      icon: <Settings className="h-4 w-4" />,
      href: '/platform-admin?tab=settings',
      keywords: ['platform', 'settings', 'global', 'config'],
      group: 'settings',
      requiredRoles: ['platform_admin', 'super_admin'],
    },
    {
      id: 'sub-container-mgmt',
      title: 'Container Management',
      description: 'Manage Docker containers',
      icon: <Package className="h-4 w-4" />,
      href: '/platform-admin?tab=containers',
      keywords: ['container', 'docker', 'services', 'platform'],
      group: 'sub-pages',
      requiredRoles: ['platform_admin', 'super_admin'],
    },

    // ============ Analytics & Reports Sub-Pages ============
    {
      id: 'sub-usage-analytics',
      title: 'Usage Analytics',
      description: 'Platform usage trends and metrics',
      icon: <BarChart3 className="h-4 w-4" />,
      href: '/analytics?tab=usage',
      keywords: ['usage', 'analytics', 'metrics', 'trends', 'statistics'],
      group: 'reports',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
      requiredFeature: 'USAGE_ANALYTICS',
    },
    {
      id: 'sub-performance-analytics',
      title: 'Performance Analytics',
      description: 'System performance metrics',
      icon: <Zap className="h-4 w-4" />,
      href: '/analytics?tab=performance',
      keywords: ['performance', 'analytics', 'speed', 'latency'],
      group: 'reports',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
      requiredFeature: 'ANALYTICS',
    },
    {
      id: 'sub-device-analytics',
      title: 'Device Analytics',
      description: 'Device usage and health analytics',
      icon: <Server className="h-4 w-4" />,
      href: '/analytics?tab=devices',
      keywords: ['device', 'analytics', 'iot', 'telemetry'],
      group: 'reports',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
      requiredFeature: 'ANALYTICS',
    },

    // ============ System Health Sub-Pages ============
    {
      id: 'sub-performance-monitor',
      title: 'Performance Monitor',
      description: 'Real-time performance monitoring',
      icon: <Zap className="h-4 w-4" />,
      href: '/performance-monitor',
      keywords: ['performance', 'monitor', 'realtime', 'websocket'],
      group: 'sub-pages',
      requiredRoles: ['admin', 'platform_admin', 'super_admin'],
      requiredFeature: 'SYSTEM_HEALTH',
    },

    // ============ Quick Actions ============
    {
      id: 'action-new-device',
      title: 'Register New Device',
      description: 'Add a new IoT device',
      icon: <Plus className="h-4 w-4" />,
      action: () => navigate('/devices?action=register'),
      keywords: ['create', 'add', 'new', 'device', 'register'],
      group: 'actions',
    },
    {
      id: 'action-new-user',
      title: 'Create New User',
      description: 'Add team member',
      icon: <Plus className="h-4 w-4" />,
      action: () => navigate('/users?action=create'),
      keywords: ['create', 'add', 'invite', 'user'],
      group: 'actions',
      requiredRoles: ['admin', 'organization_admin', 'platform_admin', 'super_admin'],
    },
    {
      id: 'action-generate-cert',
      title: 'Generate Certificate',
      description: 'Create new certificate',
      icon: <Key className="h-4 w-4" />,
      action: () => navigate('/certificates?action=generate'),
      keywords: ['create', 'new', 'certificate', 'pki', 'generate'],
      group: 'actions',
    },
    {
      id: 'action-view-notifications',
      title: 'View Notifications',
      description: 'Check recent alerts',
      icon: <Bell className="h-4 w-4" />,
      action: () => {
        const notificationButton = document.querySelector('[data-notification-trigger]') as HTMLButtonElement;
        notificationButton?.click();
      },
      keywords: ['alerts', 'notifications', 'messages', 'inbox'],
      group: 'actions',
    },
    {
      id: 'action-download-bundle',
      title: 'Download Certificate Bundle',
      description: 'Download device credentials',
      icon: <Download className="h-4 w-4" />,
      action: () => navigate('/certificates?action=download'),
      keywords: ['download', 'bundle', 'certificate', 'credentials'],
      group: 'actions',
    },
  ], [navigate]);

  // Filter search items based on RBAC and feature flags
  const filteredSearchItems = useMemo(() => {
    return allSearchItems.filter(item => {
      // Check RBAC permissions
      if (!hasRequiredRole(userRole, item.requiredRoles)) {
        return false;
      }

      // Check feature flags
      if (item.requiredFeature && !featureFlags[item.requiredFeature as keyof typeof featureFlags]) {
        return false;
      }

      return true;
    });
  }, [allSearchItems, userRole, featureFlags]);

  if (!mounted) return null;

  const groupedItems = {
    navigation: filteredSearchItems.filter(item => item.group === 'navigation'),
    subPages: filteredSearchItems.filter(item => item.group === 'sub-pages'),
    settings: filteredSearchItems.filter(item => item.group === 'settings'),
    reports: filteredSearchItems.filter(item => item.group === 'reports'),
    actions: filteredSearchItems.filter(item => item.group === 'actions'),
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search pages, features, settings, actions..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {groupedItems.navigation.length > 0 && (
          <>
            <CommandGroup heading="Navigation">
              {groupedItems.navigation.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.title} ${item.description} ${item.keywords?.join(' ')}`}
                  onSelect={() => handleSelect(item)}
                >
                  {item.icon}
                  <div className="flex flex-col">
                    <span className="font-medium">{item.title}</span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {groupedItems.subPages.length > 0 && (
          <>
            <CommandGroup heading="Feature Pages">
              {groupedItems.subPages.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.title} ${item.description} ${item.keywords?.join(' ')}`}
                  onSelect={() => handleSelect(item)}
                >
                  {item.icon}
                  <div className="flex flex-col">
                    <span className="font-medium">{item.title}</span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {groupedItems.settings.length > 0 && (
          <>
            <CommandGroup heading="Settings & Configuration">
              {groupedItems.settings.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.title} ${item.description} ${item.keywords?.join(' ')}`}
                  onSelect={() => handleSelect(item)}
                >
                  {item.icon}
                  <div className="flex flex-col">
                    <span className="font-medium">{item.title}</span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {groupedItems.reports.length > 0 && (
          <>
            <CommandGroup heading="Reports & Analytics">
              {groupedItems.reports.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`${item.title} ${item.description} ${item.keywords?.join(' ')}`}
                  onSelect={() => handleSelect(item)}
                >
                  {item.icon}
                  <div className="flex flex-col">
                    <span className="font-medium">{item.title}</span>
                    {item.description && (
                      <span className="text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {groupedItems.actions.length > 0 && (
          <CommandGroup heading="Quick Actions">
            {groupedItems.actions.map((item) => (
              <CommandItem
                key={item.id}
                value={`${item.title} ${item.description} ${item.keywords?.join(' ')}`}
                onSelect={() => handleSelect(item)}
              >
                {item.icon}
                <div className="flex flex-col">
                  <span className="font-medium">{item.title}</span>
                  {item.description && (
                    <span className="text-xs text-muted-foreground">{item.description}</span>
                  )}
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>

      <div className="border-t border-border p-2 text-xs text-muted-foreground">
        <div className="flex items-center justify-between px-2">
          <span>Press <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">⌘K</kbd> or <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">Ctrl+K</kbd> to open</span>
          <span className="text-muted-foreground/60">{filteredSearchItems.length} items</span>
        </div>
      </div>
    </CommandDialog>
  );
}
