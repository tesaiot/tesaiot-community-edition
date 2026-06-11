/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { FileText, Shield, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ProvisioningMethod = 'sw_csr' | 'hsm_csr' | 'hsm_protected_update' | string | null | undefined;

interface ProvisioningMethodBadgeProps {
  method?: ProvisioningMethod;
  showIcon?: boolean;
  showTooltip?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

interface ProvisioningConfig {
  label: string;
  description: string;
  icon: React.ReactNode;
  variant: 'default' | 'secondary' | 'outline' | 'destructive';
  className: string;
}

const PROVISIONING_CONFIGS: Record<string, ProvisioningConfig> = {
  sw_csr: {
    label: 'SW-CSR',
    description: 'Software PKI - Certificate signed via standard CSR workflow (no hardware security)',
    icon: <FileText className="h-3 w-3 flex-shrink-0" />,
    variant: 'secondary',
    className: 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300',
  },
  hsm_csr: {
    label: 'HSM-CSR',
    description: 'Hardware Secured - CSR signed with key stored in OPTIGA Trust M secure element',
    icon: <Shield className="h-3 w-3 flex-shrink-0" />,
    variant: 'default',
    className: 'bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-300',
  },
  hsm_protected_update: {
    label: 'HSM-PU',
    description: 'OPTIGA Trust M Protected Update - RFC 9019 SUIT compliant hardware-secured provisioning',
    icon: <ShieldCheck className="h-3 w-3 flex-shrink-0" />,
    variant: 'default',
    className: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-emerald-300',
  },
};

const DEFAULT_CONFIG: ProvisioningConfig = {
  label: 'Unknown',
  description: 'Provisioning method not specified',
  icon: <FileText className="h-3 w-3" />,
  variant: 'outline',
  className: 'bg-gray-50 text-gray-500 border-gray-200',
};

export function ProvisioningMethodBadge({
  method,
  showIcon = true,
  showTooltip = true,
  className,
  size = 'md',
}: ProvisioningMethodBadgeProps) {
  const config = method && PROVISIONING_CONFIGS[method] ? PROVISIONING_CONFIGS[method] : DEFAULT_CONFIG;

  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-2.5 py-1',
  };

  const badge = (
    <Badge
      variant={config.variant}
      className={cn(
        'inline-flex items-center gap-1 font-medium border whitespace-nowrap',
        sizeClasses[size],
        config.className,
        className
      )}
    >
      {showIcon && config.icon}
      <span className="truncate">{config.label}</span>
    </Badge>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {badge}
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <p className="text-sm">{config.description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Helper function to get emoji for provisioning method (for table display)
export function getProvisioningEmoji(method?: ProvisioningMethod): string {
  switch (method) {
    case 'sw_csr':
      return '📜';
    case 'hsm_csr':
      return '🔐';
    case 'hsm_protected_update':
      return '🛡️';
    default:
      return '📄';
  }
}

// Helper function to get short label for provisioning method
export function getProvisioningLabel(method?: ProvisioningMethod): string {
  const config = method && PROVISIONING_CONFIGS[method] ? PROVISIONING_CONFIGS[method] : DEFAULT_CONFIG;
  return config.label;
}

export default ProvisioningMethodBadge;
