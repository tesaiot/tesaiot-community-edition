/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Certificate } from '@/services/api/tesaApi';
import { 
  Calendar,
  Key,
  Shield,
  FileText,
  Download,
  RefreshCw
} from 'lucide-react';

interface CertificateDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  certificate: Certificate | null;
  onRenew?: (cert: Certificate) => void;
  onRevoke?: (cert: Certificate) => void;
  onDownload?: (cert: Certificate) => void;
}

export const CertificateDetailsDialog: React.FC<CertificateDetailsDialogProps> = ({
  open,
  onOpenChange,
  certificate,
  onRenew,
  onRevoke,
  onDownload,
}) => {
  if (!certificate) return null;

  const getStatusColor = (status: Certificate['status']) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50';
      case 'expired': return 'text-red-600 bg-red-50';
      case 'revoked': return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Certificate Details</DialogTitle>
          <DialogDescription className="break-words">
            Certificate information for {certificate.subject}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            <Badge className={getStatusColor(certificate.status)}>
              {certificate.status.toUpperCase()}
            </Badge>
          </div>

          {/* Certificate Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="min-w-0">
              <p className="text-muted-foreground">Subject</p>
              <p className="font-medium break-all overflow-hidden">{certificate.subject}</p>
            </div>
            <div className="min-w-0">
              <p className="text-muted-foreground">Serial Number</p>
              <p className="font-mono text-xs break-all word-break overflow-hidden">{certificate.serialNumber}</p>
            </div>
            <div className="min-w-0">
              <p className="text-muted-foreground">Issuer</p>
              <p className="font-medium break-all overflow-hidden">{certificate.issuer}</p>
            </div>
            <div className="min-w-0">
              <p className="text-muted-foreground">Algorithm</p>
              <p className="font-medium">{certificate.algorithm || 'RSA-2048'}</p>
            </div>
          </div>

          {/* Validity Period */}
          <div className="border-t pt-4">
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Validity Period
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Valid From</p>
                <p>{new Date(certificate.validFrom).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Valid Until</p>
                <p>{new Date(certificate.validTo || certificate.validUntil).toLocaleDateString()}</p>
              </div>
            </div>
          </div>

          {/* Key Usage */}
          {certificate.keyUsage && (
            <div className="border-t pt-4">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Key className="h-4 w-4" />
                Key Usage
              </h4>
              <div className="flex flex-wrap gap-2">
                {certificate.keyUsage.map((usage, index) => (
                  <Badge key={index} variant="secondary">
                    {usage}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Certificate Chain */}
          {certificate.chain && (
            <div className="border-t pt-4">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Certificate Chain
              </h4>
              <ul className="space-y-1 text-sm">
                {certificate.chain.map((cert, index) => (
                  <li key={index} className="flex items-start gap-2 min-w-0">
                    <FileText className="h-3 w-3 flex-shrink-0 mt-0.5" />
                    <span className="break-all overflow-hidden min-w-0 flex-1">{cert}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            {certificate.status === 'active' && onRevoke && (
              <Button
                variant="destructive"
                onClick={() => {
                  onRevoke(certificate);
                  onOpenChange(false);
                }}
              >
                Revoke Certificate
              </Button>
            )}
            {certificate.status === 'active' && onRenew && (
              <Button
                variant="outline"
                onClick={() => {
                  onRenew(certificate);
                  onOpenChange(false);
                }}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Renew
              </Button>
            )}
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const token = localStorage.getItem('jwt_token');
                  const url = `/api/v1/certificates/devices/${certificate.deviceId}/certificate/download/bundle`;
                  
                  const response = await fetch(url, {
                    headers: {
                      'Authorization': `Bearer ${token}`
                    }
                  });
                  
                  if (!response.ok) {
                    throw new Error('Download failed');
                  }
                  
                  const blob = await response.blob();
                  const downloadUrl = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = downloadUrl;
                  // Use server-provided filename when available; fallback to mqtts-mtls-bundle
                  const cd = response.headers.get('Content-Disposition') || '';
                  const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
                  let filename = '';
                  if (match) {
                    filename = decodeURIComponent((match[1] || match[2] || '').trim());
                  }
                  if (!filename) {
                    const ts = new Date().toISOString().replace(/:/g, '-').split('.')[0];
                    filename = `${certificate.deviceId}-mqtts-mtls-bundle-${ts}.zip`;
                  }
                  a.download = filename;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(downloadUrl);
                  
                  // Optionally surface a toast here in production
                } catch (error) {
                  console.error('Download failed:', error);
                  alert('Failed to download certificate bundle');
                }
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download Bundle
            </Button>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
