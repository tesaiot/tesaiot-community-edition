/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { LucideIcon, Home } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: LucideIcon;
  isCurrentPage?: boolean;
}

// Navigation items interface that matches the current layout structure
interface NavItem {
  title: string;
  href: string;
  icon?: React.ReactNode;
  children?: NavItem[];
  badge?: string;
  feature?: string;
  disabled?: boolean;
  tooltip?: string;
  tooltipText?: string;
  divider?: boolean;
  action?: string;
}

/**
 * Generate breadcrumb items from current pathname and navigation items
 */
export function generateBreadcrumbs(
  currentPath: string,
  navItems: NavItem[]
): BreadcrumbItem[] {
  const breadcrumbs: BreadcrumbItem[] = [];
  
  // Always start with Dashboard as home
  breadcrumbs.push({
    label: 'Dashboard',
    href: '/dashboard',
    icon: Home,
    isCurrentPage: currentPath === '/dashboard'
  });

  // If we're on dashboard, return just the dashboard breadcrumb
  if (currentPath === '/dashboard' || currentPath === '/') {
    return breadcrumbs;
  }

  // Find the matching navigation item for the current path
  const matchingItem = findNavItemByPath(currentPath, navItems);
  
  if (matchingItem) {
    // Add the current page as the last breadcrumb item
    breadcrumbs.push({
      label: matchingItem.title,
      href: matchingItem.href,
      isCurrentPage: true
    });
  } else {
    // Fallback: generate breadcrumb from path segments
    const pathSegments = currentPath.split('/').filter(Boolean);
    const lastSegment = pathSegments[pathSegments.length - 1];
    
    if (lastSegment) {
      // Convert path segment to readable title
      const title = pathSegmentToTitle(lastSegment);
      breadcrumbs.push({
        label: title,
        href: currentPath,
        isCurrentPage: true
      });
    }
  }

  return breadcrumbs;
}

/**
 * Find navigation item by path (exact match or starts with)
 */
function findNavItemByPath(path: string, navItems: NavItem[]): NavItem | null {
  for (const item of navItems) {
    // Check for exact match first
    if (item.href === path) {
      return item;
    }
    
    // Check if path starts with item.href (for nested routes)
    if (path.startsWith(item.href) && item.href !== '/') {
      return item;
    }
    
    // Recursively check children if they exist
    if (item.children) {
      const childMatch = findNavItemByPath(path, item.children);
      if (childMatch) {
        return childMatch;
      }
    }
  }
  
  return null;
}

/**
 * Convert path segment to readable title
 */
function pathSegmentToTitle(segment: string): string {
  return segment
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Generate breadcrumbs from page title and current path
 */
export function generateBreadcrumbsFromTitle(
  currentPath: string,
  pageTitle: string
): BreadcrumbItem[] {
  const breadcrumbs: BreadcrumbItem[] = [];
  
  // Always start with Dashboard as home
  breadcrumbs.push({
    label: 'Dashboard',
    href: '/dashboard',
    icon: Home,
    isCurrentPage: currentPath === '/dashboard'
  });

  // If we're on dashboard, return just the dashboard breadcrumb
  if (currentPath === '/dashboard' || currentPath === '/') {
    return breadcrumbs;
  }

  // Add the current page title
  breadcrumbs.push({
    label: pageTitle,
    href: currentPath,
    isCurrentPage: true
  });

  return breadcrumbs;
}