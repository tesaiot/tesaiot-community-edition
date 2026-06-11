/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Shield,
  ShieldCheck,
  ShieldX,
  ShieldAlert,
  RefreshCw,
  Clock,
  Calendar,
  X,
  Lock,
  Unlock,
  FileKey2,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

interface CertificateInfo {
  status: 'active' | 'expiring' | 'expired' | 'revoked' | 'none' | 'ca_only' | 'csr' | 'user_csr';
  issuedAt?: string;
  expiresAt?: string;
  daysUntilExpiry?: number;
  algorithm?: string;
  serialNumber?: string;
  authMode?: 'mtls' | 'server_tls';
}

interface CertificateStatusBadgeProps {
  certificate: CertificateInfo | null;
  className?: string;
  showRenewButton?: boolean;
  onRenew?: () => void;
  variant?: 'default' | 'compact' | 'detailed';
}

const getStatusConfig = (status: CertificateInfo['status'], authMode?: 'mtls' | 'server_tls') => {
  switch (status) {
    case 'active':
      return {
        label: authMode === 'mtls' ? 'mTLS Active' : 'Active',
        color: 'text-green-600 bg-green-50 border-green-200',
        icon: authMode === 'mtls' ? Lock : ShieldCheck,
        iconColor: 'text-green-600',
      };
    case 'expiring':
      return {
        label: authMode === 'mtls' ? 'mTLS Expiring Soon' : 'Expiring Soon',
        color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
        icon: authMode === 'mtls' ? Lock : ShieldAlert,
        iconColor: 'text-yellow-600',
      };
    case 'expired':
      return {
        label: authMode === 'mtls' ? 'mTLS Expired' : 'Expired',
        color: 'text-red-600 bg-red-50 border-red-200',
        icon: authMode === 'mtls' ? Unlock : ShieldX,
        iconColor: 'text-red-600',
      };
    case 'revoked':
      return {
        label: authMode === 'mtls' ? 'mTLS Revoked' : 'Revoked',
        color: 'text-gray-600 bg-gray-50 border-gray-200',
        icon: authMode === 'mtls' ? Unlock : ShieldX,
        iconColor: 'text-gray-600',
      };
    case 'ca_only':
      return {
        label: 'Server-TLS (CA Only)',
        color: 'text-blue-600 bg-blue-50 border-blue-200',
        icon: Shield,
        iconColor: 'text-blue-600',
      };
    case 'csr':
    case 'user_csr':
      return {
        label: 'User CSR',
        color: 'text-purple-600 bg-purple-50 border-purple-200',
        icon: FileKey2,
        iconColor: 'text-purple-600',
      };
    case 'none':
    default:
      return {
        label: 'No Certificate',
        color: 'text-gray-500 bg-gray-50 border-gray-200',
        icon: X,
        iconColor: 'text-gray-500',
      };
  }
};

export function CertificateStatusBadge({
  certificate,
  className,
  showRenewButton = false,
  onRenew,
  variant = 'default',
}: CertificateStatusBadgeProps) {
  if (!certificate || certificate.status === 'none' || certificate.status === 'ca_only' || certificate.status === 'csr' || certificate.status === 'user_csr') {
    const config = getStatusConfig(certificate?.status || 'none', certificate?.authMode);
    const IconComponent = config.icon;
    
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            <div className={cn('flex items-center gap-2', className)}>
              <Badge className={cn('flex items-center p-1', config.color)}>
                <IconComponent className="h-3 w-3" />
              </Badge>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="text-xs font-medium">{config.label}</div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  const config = getStatusConfig(certificate.status, certificate.authMode);
  const IconComponent = config.icon;
  const needsAttention = certificate.status === 'expiring' || certificate.status === 'expired';

  const renderTooltipContent = () => (
    <div className="space-y-2 text-xs">
      <div className="font-medium">Certificate Details</div>
      {certificate.authMode && (
        <div>Auth Mode: {certificate.authMode === 'mtls' ? 'Mutual TLS (mTLS)' : 'Server TLS'}</div>
      )}
      {certificate.serialNumber && (
        <div>Serial: {certificate.serialNumber}</div>
      )}
      {certificate.algorithm && (
        <div>Algorithm: {certificate.algorithm}</div>
      )}
      {certificate.issuedAt && (
        <div>Issued: {format(new Date(certificate.issuedAt), 'MMM dd, yyyy')}</div>
      )}
      {certificate.expiresAt && (
        <div>Expires: {format(new Date(certificate.expiresAt), 'MMM dd, yyyy')}</div>
      )}
      {certificate.daysUntilExpiry !== undefined && (
        <div>
          {certificate.daysUntilExpiry < 0 
            ? `Expired ${Math.abs(certificate.daysUntilExpiry)} days ago`
            : `${certificate.daysUntilExpiry} days remaining`
          }
        </div>
      )}
    </div>
  );

  if (variant === 'compact') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            <div className={cn('flex items-center gap-2', className)}>
              <Badge className={cn('flex items-center p-1', config.color)}>
                <IconComponent className="h-3 w-3" />
              </Badge>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1 text-xs">
              <div className="font-medium">{config.label}</div>
              {renderTooltipContent()}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center justify-between">
          <Badge className={cn('flex items-center gap-1', config.color)}>
            <IconComponent className="h-3 w-3" />
            {config.label}
          </Badge>
          {showRenewButton && needsAttention && onRenew && (
            <Button
              size="sm"
              variant="outline"
              onClick={onRenew}
              className="h-6 px-2 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Renew
            </Button>
          )}
        </div>
        
        {certificate.expiresAt && (
          <div className="text-xs text-muted-foreground space-y-1">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Expires: {format(new Date(certificate.expiresAt), 'MMM dd, yyyy')}
            </div>
            {certificate.daysUntilExpiry !== undefined && (
              <div className={cn(
                'flex items-center gap-1 font-medium',
                certificate.daysUntilExpiry < 0 ? 'text-red-600' :
                certificate.daysUntilExpiry <= 30 ? 'text-yellow-600' :
                'text-green-600'
              )}>
                <Clock className="h-3 w-3" />
                {certificate.daysUntilExpiry < 0 
                  ? `Expired ${Math.abs(certificate.daysUntilExpiry)} days ago`
                  : `${certificate.daysUntilExpiry} days remaining`
                }
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <div className={cn('flex items-center gap-2', className)}>
            <Badge className={cn('flex items-center p-1', config.color)}>
              <IconComponent className="h-3 w-3" />
            </Badge>
            
            {showRenewButton && needsAttention && onRenew && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRenew}
                className="h-6 px-2 text-xs ml-2"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Renew
              </Button>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1 text-xs">
            <div className="font-medium">{config.label}</div>
            {renderTooltipContent()}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Helper function to calculate certificate info from device data
export function getCertificateInfo(device: unknown): CertificateInfo | null {
  // Type assertion for device object
  const deviceData = device as {
  auth_mode?: 'mtls' | 'server_tls' | 'optiga_trust_mtls';
    certificate_status?: string;
    certificate_pending?: boolean;
    csr_provided?: boolean;
    csr_status?: string;
    generation_method?: string;
    certificate?: {
      status?: string;
      expiresAt?: string;
      expiry_date?: string;
      expires_at?: string;
      issuedAt?: string;
      issued_at?: string;
      created_at?: string;
      algorithm?: string;
      key_algorithm?: string;
      serialNumber?: string;
      serial_number?: string;
    };
  };
  const authMode = deviceData?.auth_mode || 'mtls'; // Default to mtls for backward compatibility
  
  // Check if this device has a CSR provided or pending certificate generation via CSR
  // Also check for CSR in the device name or if it's an mTLS device without a certificate
  const hasCSRIndication = 
    deviceData?.csr_provided || 
    deviceData?.generation_method === 'upload_csr' ||
    deviceData?.generation_method === 'upload-csr' ||
    deviceData?.csr_status === 'provided' ||
    deviceData?.certificate_pending ||
    (deviceData?.name && deviceData.name.toLowerCase().includes('csr')) ||
    (deviceData?.description && typeof deviceData.description === 'string' && deviceData.description.toLowerCase().includes('csr'));
  
  // Check if this is an mTLS device without a valid certificate but with CSR indication
  const isMTLSWithCSR = (authMode === 'mtls' || authMode === 'optiga_trust_mtls') && 
    !deviceData?.certificate && 
    (hasCSRIndication || deviceData?.certificate_status === 'pending');
    
  if (hasCSRIndication || isMTLSWithCSR) {
    return {
      status: 'user_csr',
      authMode: authMode as 'mtls' | 'server_tls' | 'optiga_trust_mtls'
    } as CertificateInfo;
  }
  
  // Check if this is a server_tls device (CA certificate only)
  if (deviceData?.auth_mode === 'server_tls' || deviceData?.certificate_status === 'ca_only') {
    return { 
      status: 'ca_only',
      authMode: 'server_tls'
    } as CertificateInfo;
  }

  // Check if device has valid mTLS certificate
  if (deviceData?.certificate_status === 'valid' && deviceData?.certificate) {
    // For devices with valid certificate status and detailed certificate object
    // Continue to process the certificate details below
  } else if (deviceData?.certificate_status === 'valid' && !deviceData?.certificate) {
    // For devices with valid certificate status but no detailed certificate object
    return { 
      status: 'active',
      authMode: authMode as 'mtls' | 'server_tls' | 'optiga_trust_mtls'
    } as CertificateInfo;
  }

  if (!deviceData?.certificate && deviceData?.certificate_status !== 'valid') {
    return { 
      status: 'none',
      authMode: authMode as 'mtls' | 'server_tls' | 'optiga_trust_mtls'
    };
  }

  const cert = deviceData.certificate;
  if (!cert) {
    return { 
      status: 'none',
      authMode: authMode as 'mtls' | 'server_tls'
    };
  }

  const now = new Date();
  const expiryDate = new Date(cert.expiresAt || cert.expiry_date || cert.expires_at || '');
  const daysUntilExpiry = Math.floor((expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  let status: CertificateInfo['status'] = 'active';
  
  if (cert.status === 'revoked') {
    status = 'revoked';
  } else if (daysUntilExpiry < 0) {
    status = 'expired';
  } else if (daysUntilExpiry <= 30) {
    status = 'expiring';
  }

  return {
    status,
    issuedAt: cert.issuedAt || cert.issued_at || cert.created_at,
    expiresAt: cert.expiresAt || cert.expiry_date || cert.expires_at,
    daysUntilExpiry,
    algorithm: cert.algorithm || cert.key_algorithm,
    serialNumber: cert.serialNumber || cert.serial_number,
    authMode: authMode as 'mtls' | 'server_tls',
  };
}
