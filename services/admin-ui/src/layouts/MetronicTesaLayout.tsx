/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  Shield,
  Server,
  FileText,
  Users,
  Key,
  Package,
  LogOut,
  Menu,
  X,
  Home,
  CheckCircle,
  Moon,
  Sun,
  Palette,
  Crown,
  Zap,
  Building2,
  BrainCircuit,
  Radio,
  Code2,
  ChevronDown,
  Bell,
  Search,
  Settings,
  ChevronFirst,
  Puzzle,
  Store,
  BarChart3,
  TrendingUp,
  Info,
  ShieldCheck,
  Box
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/hooks/useAuth';
import { getFilteredMenu, type MenuItem, type MenuGroup } from '@/features/navigation/MenuConfiguration';
import { useLicenseContext, RequireFeature } from '@/providers/license-provider';
import { useTheme, ThemeToggle } from '@/providers/enhanced-theme-provider';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { MenuTooltip } from "@/components/ui/menu-tooltip";
import { ETSIComplianceBadge } from '@/features/dashboard/components/ETSIComplianceBadge';
import '@/css/metronic-sidebar.css';
import { isFeatureEnabled } from '@/config/features.config';
import { NotificationsSheet } from '@/partials/topbar/notifications-sheet';
import { useNotifications } from '@/features/notifications/NotificationService';
import { TesaBreadcrumb } from '@/components/navigation/TesaBreadcrumb';
import { useServiceConfiguration } from '@/features/platform-admin/hooks/useServiceConfiguration';
import { MobileBlockerOverlay } from './components/MobileBlockerOverlay';
import { GlobalSearchCommand } from '@/components/navigation/GlobalSearchCommand';
import { SidebarFooter } from './demo1/components/sidebar-footer';

interface NavItem {
  title: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  feature?: string;
  children?: NavItem[];
  disabled?: boolean;
  tooltip?: string;
  tooltipText?: string; // Info tooltip content
  divider?: boolean;
  action?: string;
  external?: boolean; // Use <a> instead of React Router <Link> for external/third-party services
}

export const MetronicTesaLayout: React.FC = () => {
  // Load sidebar state from localStorage for persistence (default expanded)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('tesa-sidebar-collapsed');
    return saved !== null ? JSON.parse(saved) : false; // Default to expanded
  });
  // Remove hover state - only manual toggle
  const sidebarHover = false;
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { edition, hasFeature, isCommercial, getUpgradeUrl } = useLicenseContext();
  
  
  const { notifications, unreadCount } = useNotifications();
  const { currentTheme } = useTheme();
  
  const organizationId = user?.organization_id || user?.organization || 'default';
  const { config: serviceConfig, loading: configLoading } = useServiceConfiguration(
    hasFeature('multiOrganization') ? organizationId : null
  );
  
  // Get app version
  const appVersion = import.meta.env.VITE_APP_VERSION || 'dev';
  
  // Stabilize edition display to prevent flickering
  const [displayEdition, setDisplayEdition] = useState(edition);
  
  useEffect(() => {
    // Debounce edition changes to prevent flickering
    const timer = setTimeout(() => {
      setDisplayEdition(edition);
    }, 100);
    
    return () => clearTimeout(timer);
  }, [edition]);

  // Check if mobile
  useEffect(() => {
    const checkViewport = () => {
      const width = window.innerWidth;
      setIsMobile(width < 768);
      setIsTablet(width >= 768 && width < 1024);
    };

    checkViewport();
    window.addEventListener('resize', checkViewport);
    return () => window.removeEventListener('resize', checkViewport);
  }, []);

  // Save sidebar state to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('tesa-sidebar-collapsed', JSON.stringify(sidebarCollapsed));
  }, [sidebarCollapsed]);

  // Apply body classes for Metronic styling
  useEffect(() => {
    document.body.className = cn(
      'tesa-layout bg-gray-100 dark:bg-gray-900',
      currentTheme,
      sidebarCollapsed && 'sidebar-collapse',
      'sidebar-fixed'
    );
  }, [sidebarCollapsed, currentTheme]);


  // Build navigation items based on service configuration
  const navItems: NavItem[] = [
    // Dashboard - conditional based on service config
    ...(serviceConfig?.features?.menu_dashboard !== false ? [{
      title: 'Dashboard', 
      href: '/dashboard', 
      icon: <Home className="h-5 w-5" />
    }] : []),
    // Devices & Identity - conditional based on service config
    ...(serviceConfig?.features?.menu_devices !== false ? [{
      title: 'Devices & Identity', 
      href: '/devices', 
      icon: <Server className="h-5 w-5" />,
      tooltipText: 'Manage your IoT devices, configure settings, and handle device provisioning.\n\n• Device inventory management\n• Real-time status monitoring\n• Bulk operations support\n• Device provisioning workflows'
    }] : []),
    // Users - conditional based on service config
    ...(serviceConfig?.features?.menu_users !== false ? [{
      title: 'Users', 
      href: '/users', 
      icon: <Users className="h-5 w-5" />,
      tooltipText: 'Manage team members, assign roles, and control access permissions.\n\n• User account management\n• Role-based access control\n• Permission assignment\n• Multi-organization support'
    }] : []),
    // Certificates - conditional based on service config
    ...(serviceConfig?.features?.menu_certificates !== false ? [{
      title: 'Certificates', 
      href: '/certificates', 
      icon: <Key className="h-5 w-5" />,
      tooltipText: 'Digital security certificates and key provisioning for secure communications.\n\n• PKI certificate generation\n• Key provisioning workflows\n• Certificate lifecycle management\n• Automated renewal policies',
      divider: true
    }] : []),
    
    // Temporarily disabled - incomplete implementation
    // System Health - conditional based on service config
    // ...(serviceConfig?.features?.menu_system_health !== false ? [{
    //   title: 'System Health',
    //   href: '/system-health',
    //   icon: <Activity className="h-5 w-5" />,
    //   tooltip: 'Real-time system monitoring and health dashboard',
    //   tooltipText: 'Real-time monitoring of platform performance and service health.\n\n• System resource monitoring\n• Service status tracking\n• Performance metrics\n• Alert notifications'
    // }] : []),
    // Activity Logs - conditional based on service config
    // ...(serviceConfig?.features?.menu_activity_logs !== false ? [{
    //   title: 'Activity Logs',
    //   href: '/activity-logs',
    //   icon: <FileText className="h-5 w-5" />,
    //   tooltip: 'Comprehensive activity tracking and audit logs',
    //   tooltipText: 'Track all user actions, system events, and security activities.\n\n• User activity tracking\n• System event logs\n• Security audit trails\n• Compliance reporting'
    // }] : []),

    // Analytics Dashboard - conditionally shown based on service config
    // ...(serviceConfig?.features?.menu_analytics !== false ? [{
    //   title: 'Analytics',
    //   href: '/analytics',
    //   icon: <BarChart3 className="h-5 w-5" />,
    //   tooltip: 'Comprehensive usage analytics and trends',
    //   tooltipText: 'Business intelligence dashboards and operational insights.\n\n• Usage trend analysis\n• Performance metrics\n• Device analytics\n• Custom reports'
    // }] : []),
    
    // Compliance - conditionally shown based on service config
    ...(serviceConfig?.features?.menu_compliance !== false ? [{
      title: 'Compliance', 
      href: '/security/compliance', 
      icon: <CheckCircle className="h-5 w-5" />,
      tooltipText: 'Industry standards compliance tracking and certification.\n\n• ETSI EN 303 645 compliance\n• ISO/IEC 27402 standards\n• GDPR requirements\n• Audit report generation',
      divider: true
    }] : []),
    
    // Organizations - conditional based on service config AND admin role
    ...(serviceConfig?.features?.menu_organizations !== false ? [{
      title: 'Organizations', 
      href: '/organizations', 
      icon: <Building2 className="h-5 w-5" />, 
      feature: 'multiOrganization',
      badge: 'ADMIN',
      tooltipText: 'Multi-tenant management for enterprise deployments.\n\n• Organization isolation\n• Department management\n• Data segregation\n• Custom settings per org'
    }] : []),

    // API Keys - organization API keys for the REST API / APISIX gateway.
    ...(['admin', 'organization_admin', 'super_admin'].includes(user?.role || '') ? [{
      title: 'API Keys',
      href: '/api-keys',
      icon: <Key className="h-5 w-5" />,
      tooltipText: 'Organization API keys for REST API / gateway access (scopes, rotation, expiry).'
    }] : []),

    // Platform Admin - SINGLE MENU ITEM ONLY
    ...(user?.role === 'platform_admin' ? [
      {
        title: 'divider',
        href: '#',
        icon: null,
        divider: true
      },
      {
        title: 'Platform Admin',
        href: '/platform-admin',
        icon: <Crown className="h-5 w-5 text-purple-600" />,
        tooltipText: 'Platform administration dashboard'
      }
    ] : []),
    
    // Extensions menu (commercial "Coming soon" add-ons + 3D Model Store)
    // removed for the Community Edition.
  ];


  const handleLogout = () => {
    logout();
    navigate('/auth/sign-in');
  };

  const isNavItemVisible = (item: NavItem): boolean => {
    if (!item.feature) return true;
    return hasFeature(item.feature as any);
  };

  const getLicenseBadgeColor = () => {
    switch (displayEdition) {
      case 'enterprise': return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
      case 'business': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
      case 'startup': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const expandedSidebarWidth = isTablet ? 'w-[240px]' : 'w-[290px]';
  const collapsedSidebarWidth = isTablet ? 'w-[68px]' : 'w-[80px]';
  const headerPaddingClass = isTablet ? 'px-4' : 'px-6';
  const contentPaddingClass = isTablet ? 'px-4 py-4' : '';
  const isCompactNav = isMobile || isTablet;

  return (
    <TooltipProvider>
      <div className={cn(
        "tesa-layout min-h-screen",
        sidebarCollapsed && 'sidebar-collapse',
        !isMobile && !isTablet && 'min-w-[1024px]'
      )}>
        <MobileBlockerOverlay visible={isMobile} />
        {/* Mobile sidebar overlay */}
      {isCompactNav && !sidebarCollapsed && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarCollapsed(true)}
        />
      )}
      
      {/* Sidebar - Fixed positioned */}
      <aside 
        className={cn(
          'sidebar bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen',
          sidebarCollapsed ? collapsedSidebarWidth : expandedSidebarWidth,
          'transition-all duration-300 ease-in-out',
          isCompactNav && !sidebarCollapsed && 'sidebar-open'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={cn(
            "aside-logo flex items-center h-[70px] border-b border-gray-200 dark:border-gray-700 px-6 relative"
          )}>
            <div className="flex items-center flex-1">
              <img 
                src="/images/TESA_logo.png" 
                alt="TESA Logo" 
                className={cn(
                  "transition-all duration-300",
                  sidebarCollapsed && !sidebarHover ? "h-14 w-auto mx-auto" : "h-[68px] w-auto mr-3"
                )}
              />
              <div className={cn(
                "transition-all duration-300 overflow-hidden",
                sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-auto opacity-100"
              )}>
                <h1 className="font-semibold text-gray-900 dark:text-white whitespace-nowrap" style={{ fontSize: '1.1rem' }}>
                  TES<span style={{ fontSize: '1.4rem', verticalAlign: 'super', position: 'relative', top: '0.3em' }}>⩓</span>IoT Platform
                </h1>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <Badge
                    variant="outline"
                    className={cn(
                      'inline-flex items-center h-5 px-2 py-0 rounded-md border-transparent text-[10px] font-semibold tracking-wider uppercase shadow-sm',
                      displayEdition === 'enterprise' && 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white',
                      displayEdition === 'business' && 'bg-gradient-to-r from-blue-600 to-sky-600 text-white',
                      displayEdition === 'startup' && 'bg-gradient-to-r from-emerald-600 to-green-600 text-white',
                      // Elegant, understated slate for the free Community edition
                      // (white on a deep slate gradient; inverts cleanly in dark mode).
                      displayEdition === 'community' && 'bg-gradient-to-r from-slate-700 to-slate-900 text-white dark:from-slate-200 dark:to-white dark:text-slate-900'
                    )}
                  >
                    {displayEdition.toUpperCase()}
                  </Badge>
                  <Badge
                    variant="secondary"
                    className="inline-flex items-center justify-center h-5 px-1.5 py-0 rounded-md text-[10px] font-medium tracking-tight tabular-nums bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700"
                  >
                    v{appVersion.replace(/^v/, '')}
                  </Badge>
                </div>
              </div>
            </div>
            {!isMobile && (
              <Button
                variant="outline"
                size="icon"
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className={cn(
                  "absolute -right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full bg-white dark:bg-gray-800 shadow-md sidebar-toggle-btn",
                  sidebarCollapsed ? "rotate-180" : ""
                )}
                title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                <ChevronFirst className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Navigation */}
          <nav className="aside-menu flex-1 py-5 overflow-y-auto px-3">
            {navItems.filter(isNavItemVisible).map((item) => {
              // Check if this is a divider item
              if (item.title === 'divider') {
                return (
                  <div key={`divider-${item.href}`} className="my-2 px-3">
                    <div className="border-t border-gray-200 dark:border-gray-700"></div>
                  </div>
                );
              }
              
              // Render divider if specified (after the menu item, not instead of it)
              const shouldShowDivider = item.divider;
              
              const isActive = location.pathname === item.href || 
                             location.pathname.startsWith(item.href + '/') ||
                             (item.children && item.children.some(child => location.pathname === child.href)) ||
                             // Handle compliance route special case
                             (item.title === 'Compliance' && location.pathname === '/security/compliance');
              const isLocked = item.feature && !hasFeature(item.feature as any);
              const isDisabled = item.disabled || false;
              
              
              // Handle items with children (Extensions menu)
              if (item.children) {
                return (
                  <div key={item.title} className="menu-item mb-1">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          className={cn(
                            'menu-link w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                            isActive
                              ? 'bg-primary/10 text-primary dark:bg-primary/20'
                              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                          )}
                          title={item.tooltip || (sidebarCollapsed && !sidebarHover ? item.title : undefined)}
                        >
                          <span className={cn('menu-icon flex-shrink-0', isActive && 'text-primary')}>{item.icon}</span>
                          <span className={cn(
                            "flex-1 transition-all duration-300 whitespace-nowrap text-left",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                          )}>{item.title}</span>
                          {item.tooltipText && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Info className={cn(
                                  "h-4 w-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help transition-all duration-300",
                                  sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                                )} />
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-xs">
                                <p className="text-sm">{item.tooltipText}</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                          {item.badge && (
                            <Badge 
                              variant="secondary"
                              className={cn(
                                "text-xs transition-all duration-300",
                                sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "opacity-100",
                                item.badge === 'Preview' && "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300"
                              )}
                            >
                              {item.badge}
                            </Badge>
                          )}
                          <ChevronDown className={cn(
                            "h-4 w-4 transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                          )} />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="w-56">
                        {item.children.map((child) => {
                          if (child.divider) {
                            return <DropdownMenuSeparator key={child.title} />;
                          }
                          return (
                            <DropdownMenuItem
                              key={child.title}
                              disabled={child.disabled}
                              className={cn(
                                child.disabled && "opacity-60 cursor-not-allowed"
                              )}
                              onSelect={(e) => {
                                if (child.disabled) {
                                  e.preventDefault();
                                } else if (child.action === 'openExtensionStore') {
                                  // Handle extension store action
                                  e.preventDefault();
                                } else if (child.external) {
                                  // External link - open in new tab
                                  window.open(child.href, '_blank', 'noopener,noreferrer');
                                } else if (!child.disabled) {
                                  navigate(child.href);
                                }
                              }}
                            >
                              <span className="flex items-center gap-2 w-full">
                                {child.icon}
                                <span className="flex-1">{child.title}</span>
                                {child.badge && (
                                  <Badge variant="outline" className="text-xs">
                                    {child.badge}
                                  </Badge>
                                )}
                              </span>
                            </DropdownMenuItem>
                          );
                        })}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                );
              }
              
              return (
                <React.Fragment key={item.title || item.href}>
                  <div className="menu-item mb-1">
                  {isLocked ? (
                    <div
                      className={cn(
                        'menu-link flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors cursor-not-allowed opacity-60',
                        'text-gray-500 dark:text-gray-400'
                      )}
                      onClick={() => navigate(getUpgradeUrl())}
                      title={item.tooltip || (sidebarCollapsed && !sidebarHover ? item.title : undefined)}
                    >
                      <span className="menu-icon flex-shrink-0">{item.icon}</span>
                      <span className={cn(
                        "flex-1 transition-all duration-300 whitespace-nowrap",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                      )}>{item.title}</span>
                      {item.tooltipText && !sidebarCollapsed && (
                        <MenuTooltip 
                          title={item.title}
                          content={item.tooltipText}
                          iconClassName={cn(
                            "transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                          )}
                        />
                      )}
                      <Crown className={cn(
                        "h-4 w-4 transition-all duration-300",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                      )} />
                    </div>
                  ) : isDisabled ? (
                    <div
                      className={cn(
                        'menu-link flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors cursor-not-allowed opacity-60',
                        'text-gray-500 dark:text-gray-400'
                      )}
                      title={item.tooltip || (sidebarCollapsed && !sidebarHover ? item.title : undefined)}
                    >
                      <span className="menu-icon flex-shrink-0">{item.icon}</span>
                      <span className={cn(
                        "flex-1 transition-all duration-300 whitespace-nowrap",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                      )}>{item.title}</span>
                      {item.tooltipText && !sidebarCollapsed && (
                        <MenuTooltip 
                          title={item.title}
                          content={item.tooltipText}
                          iconClassName={cn(
                            "transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                          )}
                        />
                      )}
                      {item.badge && (
                        <Badge 
                          variant="secondary"
                          className={cn(
                            "text-xs transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "opacity-100",
                            item.badge === 'Coming Soon' && "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300"
                          )}
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </div>
                  ) : item.external ? (
                    // External link - use <a> tag for third-party services like Product Model Store
                    <a
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        'menu-link flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                        isActive
                          ? 'bg-primary/10 text-primary dark:bg-primary/20'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700',
                      )}
                      title={item.tooltip || (sidebarCollapsed && !sidebarHover ? item.title : undefined)}
                    >
                      <span className={cn('menu-icon flex-shrink-0', isActive && 'text-primary')}>{item.icon}</span>
                      <span className={cn(
                        "flex-1 transition-all duration-300 whitespace-nowrap",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                      )}>{item.title}</span>
                      {item.tooltipText && !sidebarCollapsed && (
                        <MenuTooltip
                          title={item.title}
                          content={item.tooltipText}
                          iconClassName={cn(
                            "transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                          )}
                        />
                      )}
                      {item.badge && (
                        <Badge
                          variant={item.badge === 'New' ? 'default' : 'secondary'}
                          className={cn(
                            "text-xs transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "opacity-100",
                            item.badge === 'New' && "bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300"
                          )}
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </a>
                  ) : (
                    // Internal link - use React Router <Link>
                    <Link
                      to={item.href}
                      className={cn(
                        'menu-link flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                        isActive
                          ? 'bg-primary/10 text-primary dark:bg-primary/20'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700',
                      )}
                      title={item.tooltip || (sidebarCollapsed && !sidebarHover ? item.title : undefined)}
                    >
                      <span className={cn('menu-icon flex-shrink-0', isActive && 'text-primary')}>{item.icon}</span>
                      <span className={cn(
                        "flex-1 transition-all duration-300 whitespace-nowrap",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                      )}>{item.title}</span>
                      {item.tooltipText && !sidebarCollapsed && (
                        <MenuTooltip
                          title={item.title}
                          content={item.tooltipText}
                          iconClassName={cn(
                            "transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                          )}
                        />
                      )}
                      {item.badge && (
                        <Badge
                          variant={item.badge === 'NEW' ? 'default' : 'secondary'}
                          className={cn(
                            "text-xs transition-all duration-300",
                            sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "opacity-100",
                            item.badge === 'ADMIN' && "bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300",
                            item.badge === 'PRO' && "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300",
                            item.badge === 'ENTERPRISE' && "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300"
                          )}
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </Link>
                  )}
                </div>
                  {/* Render divider after the menu item if specified */}
                  {shouldShowDivider && (
                    <div className="my-2 border-t border-gray-200 dark:border-gray-700" />
                  )}
                </React.Fragment>
              );
            })}
          </nav>

          {/* Storage Usage Indicator */}
          {(!sidebarCollapsed || sidebarHover) && <SidebarFooter />}

          {/* User section */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            {(!sidebarCollapsed || sidebarHover) ? (
              <div className="space-y-3">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer">
                      <Avatar className="w-10 h-10 flex-shrink-0">
                        <AvatarImage 
                          src={user?.pic || user?.avatar || ''} 
                          alt={user?.name || user?.email || 'User'} 
                        />
                        <AvatarFallback className="bg-primary/10">
                          <Users className="h-5 w-5 text-primary" />
                        </AvatarFallback>
                      </Avatar>
                      <div className={cn(
                        "flex-1 transition-all duration-300",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0 overflow-hidden" : "w-auto opacity-100"
                      )}>
                        <p className="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap">
                          {user?.email || 'Admin User'}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Administrator</p>
                      </div>
                      <ChevronDown className={cn(
                        "h-4 w-4 text-gray-400 transition-all duration-300",
                        sidebarCollapsed && !sidebarHover ? "w-0 opacity-0" : "w-4 opacity-100"
                      )} />
                    </div>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>My Account</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/account/home/user-profile" className="flex items-center">
                        <Users className="mr-2 h-4 w-4" />
                        <span>Profile</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onSelect={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Logout</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Avatar className="w-10 h-10">
                  <AvatarImage 
                    src={user?.pic || user?.avatar || ''} 
                    alt={user?.name || user?.email || 'User'} 
                  />
                  <AvatarFallback className="bg-primary/10">
                    <Users className="h-5 w-5 text-primary" />
                  </AvatarFallback>
                </Avatar>
                <Button 
                  variant="ghost" 
                  size="icon"
                  onClick={handleLogout}
                  className="w-full"
                  title="Logout"
                >
                  <LogOut className="h-5 w-5" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content wrapper - No flex container needed */}
      <div className="wrapper min-h-screen">
        {/* Header */}
        <header className={cn(
          'header h-[70px] bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between',
          headerPaddingClass
        )}>
          <div className="flex items-center gap-4 flex-1">
            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </Button>
            
            {/* Breadcrumb Navigation */}
            <TesaBreadcrumb 
              pageTitle={navItems.find(item => 
                item.href === location.pathname || 
                location.pathname.startsWith(item.href + '/')
              )?.title || 'Dashboard'}
              navItems={navItems}
              className="flex-1"
            />
            
            {/* Search - Click to open Command Palette */}
            <div className="hidden md:flex items-center max-w-md">
              <Button
                variant="outline"
                className="relative w-full justify-start text-sm text-muted-foreground bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => setSearchOpen(true)}
              >
                <Search className="mr-2 h-4 w-4" />
                <span className="flex-1 text-left">Search pages, actions...</span>
                <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                  <span className="text-xs">⌘</span>K
                </kbd>
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Theme Toggle */}
            <RequireFeature feature="darkTheme" fallback={null}>
              <ThemeToggle />
            </RequireFeature>

            {/* Notifications */}
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={() => setNotificationOpen(true)}
              data-notification-trigger
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Button>

            {/* Compliance Status */}
            <ETSIComplianceBadge score={hasFeature('etsiFull') ? 13 : 5} total={13} />

            {/* Upgrade CTA removed for the Community Edition (self-host, Apache-2.0):
                it opened a commercial pricing/upgrade page, which is not appropriate
                for the free CE. */}
          </div>
        </header>

        {/* Page content */}
        <main className={cn(
          'content overflow-auto bg-gray-50 dark:bg-gray-900',
          contentPaddingClass
        )}>
          <Outlet />
        </main>
      </div>
      
        {/* Notifications Sheet */}
        <NotificationsSheet
          open={notificationOpen}
          onOpenChange={setNotificationOpen}
        />

        {/* Global Search Command Palette */}
        <GlobalSearchCommand
          open={searchOpen}
          onOpenChange={setSearchOpen}
          userRole={user?.role}
        />
      </div>
    </TooltipProvider>
  );
};
