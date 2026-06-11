/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { BreadcrumbItem as BreadcrumbItemType, generateBreadcrumbsFromTitle, generateBreadcrumbs } from '@/utils/breadcrumb-utils';
import { cn } from '@/lib/utils';

// Match the NavItem interface from the layout
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

interface TesaBreadcrumbProps {
  pageTitle?: string;
  className?: string;
  customBreadcrumbs?: BreadcrumbItemType[];
  navItems?: NavItem[];
}

export const TesaBreadcrumb: React.FC<TesaBreadcrumbProps> = ({
  pageTitle,
  className,
  customBreadcrumbs,
  navItems
}) => {
  const location = useLocation();
  
  // Generate breadcrumbs based on current path and navigation items
  const breadcrumbs = customBreadcrumbs || 
    (navItems ? generateBreadcrumbs(location.pathname, navItems) :
     generateBreadcrumbsFromTitle(location.pathname, pageTitle || 'Page'));

  // Don't render breadcrumbs if we only have one item (Dashboard)
  if (breadcrumbs.length <= 1) {
    return null;
  }

  return (
    <Breadcrumb className={cn('flex items-center', className)}>
      <BreadcrumbList>
        {breadcrumbs.map((item, index) => {
          const isLast = index === breadcrumbs.length - 1;
          
          return (
            <React.Fragment key={`breadcrumb-${index}`}>
              <BreadcrumbItem>
                {!isLast && item.href ? (
                  <BreadcrumbLink asChild>
                    <Link 
                      to={item.href}
                      className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {item.icon && <item.icon className="h-4 w-4" />}
                      {item.label}
                    </Link>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage className="flex items-center gap-1.5 text-sm font-normal text-foreground">
                    {item.icon && <item.icon className="h-4 w-4" />}
                    {item.label}
                  </BreadcrumbPage>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
};

export default TesaBreadcrumb;