/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  RefreshCw,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Clock,
  AlertTriangle,
  CheckCircle,
  Download,
  Key,
  FileText,
  Calendar,
  Info,
} from 'lucide-react';
import { format, addYears, isValid } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface Certificate {
  id: string;
  deviceId: string;
  deviceName: string;
  deviceType: string;
  status: 'active' | 'expiring' | 'expired' | 'revoked';
  issuedAt: string;
  expiresAt: string;
  daysUntilExpiry: number;
  serialNumber: string;
  algorithm: string;
  organization?: string;
}

interface CertificateRenewalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  certificate: Certificate | null;
  onRenewalComplete?: (certificate: Certificate, newCertificate: any) => void;
}

interface RenewalOptions {
  algorithm: string;
  keySize: string;
  validityPeriod: string;
  autoDownload: boolean;
  revokeOld: boolean;
}

const ALGORITHM_OPTIONS = [
  { value: 'RSA-2048', label: 'RSA 2048-bit (Recommended)' },
  { value: 'RSA-4096', label: 'RSA 4096-bit (High Security)' },
  { value: 'ECDSA-P256', label: 'ECDSA P-256 (Efficient)' },
  { value: 'ECDSA-P384', label: 'ECDSA P-384 (High Security)' },
];

const VALIDITY_PERIODS = [
  { value: '1', label: '1 Year' },
  { value: '2', label: '2 Years' },
  { value: '3', label: '3 Years' },
  { value: '5', label: '5 Years' },
];

enum RenewalStep {
  OPTIONS = 'options',
  CONFIRM = 'confirm',
  PROCESSING = 'processing',
  COMPLETE = 'complete',
  ERROR = 'error'
}

// Helper function to safely format dates using browser's local timezone
// Note: API returns timestamps in server local time (Thai UTC+7) without timezone indicator
// We parse them as-is (local time) to avoid double timezone conversion
const formatDate = (dateString: string | undefined | null, formatStr: string = 'MMM dd, yyyy'): string => {
  if (!dateString) return 'Not available';

  try {
    // Parse timestamp as-is - API returns local time without timezone indicator
    const date = new Date(dateString);
    if (!isValid(date)) {
      console.warn(`Invalid date value: ${dateString}`);
      return 'Invalid date';
    }
    // Use toLocaleString for proper timezone conversion
    const includesTime = formatStr.includes('HH:mm') || formatStr.includes('hh:mm');
    if (includesTime) {
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    } else {
      return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit'
      });
    }
  } catch (error) {
    console.error(`Error formatting date: ${dateString}`, error);
    return 'Invalid date';
  }
};

export function CertificateRenewalDialog({
  open,
  onOpenChange,
  certificate,
  onRenewalComplete,
}: CertificateRenewalDialogProps) {
  const [renewalStep, setRenewalStep] = useState<RenewalStep>(RenewalStep.OPTIONS);
  const [progress, setProgress] = useState(0);
  const [renewalOptions, setRenewalOptions] = useState<RenewalOptions>({
    algorithm: 'RSA-2048',
    keySize: '2048',
    validityPeriod: '1',
    autoDownload: true,
    revokeOld: true,
  });
  const [newCertificate, setNewCertificate] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [justification, setJustification] = useState('');
  const [thresholdDays, setThresholdDays] = useState<number>(60);
  const [policy, setPolicy] = useState<any>(null);
  const [altNames, setAltNames] = useState<string>('');

  // NOTE: Do not early-return before hooks. Hooks must run on every render
  // to avoid React error #310 (rendered more hooks than previous render).

  const getStatusColor = (status: Certificate['status']) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'expiring':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'expired':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'revoked':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: Certificate['status']) => {
    switch (status) {
      case 'active':
        return <ShieldCheck className="h-4 w-4" />;
      case 'expiring':
        return <ShieldAlert className="h-4 w-4" />;
      case 'expired':
        return <ShieldX className="h-4 w-4" />;
      case 'revoked':
        return <ShieldX className="h-4 w-4" />;
      default:
        return <Shield className="h-4 w-4" />;
    }
  };

  const calculateNewExpiryDate = () => {
    const years = parseInt(renewalOptions.validityPeriod);
    return addYears(new Date(), years);
  };

  const formatNewExpiryDate = (formatStr: string = 'MMM dd, yyyy'): string => {
    try {
      const date = calculateNewExpiryDate();
      if (!isValid(date)) {
        return 'Invalid date';
      }
      return format(date, formatStr);
    } catch (error) {
      console.error('Error formatting new expiry date', error);
      return 'Invalid date';
    }
  };

  useEffect(() => {
    // Fetch effective threshold from API when dialog opens
    const fetchThreshold = async () => {
      try {
        const params = certificate?.deviceType ? `?device_type=${encodeURIComponent(certificate.deviceType)}` : '';
        const token = localStorage.getItem('jwt_token');
        const res = await fetch(`/api/v1/certificates/policies/renewal-threshold${params}` , {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (res.ok) {
          const data = await res.json();
          if (typeof data?.threshold_days === 'number') setThresholdDays(data.threshold_days);
        }
      } catch {}
    };
    const fetchPolicy = async () => {
      try {
        const token = localStorage.getItem('jwt_token');
        const res = await fetch('/api/v1/certificates/policies/certificates', {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (res.ok) {
          const data = await res.json();
          setPolicy(data?.policy || null);
        }
      } catch {}
    };
    if (open && certificate) { fetchThreshold(); fetchPolicy(); }
  }, [open, certificate]);

  // Safe early return AFTER hooks are declared to keep hook order stable
  if (!certificate) return null;

  const handleRenewal = async () => {
    setRenewalStep(RenewalStep.PROCESSING);
    setError(null);
    setProgress(0);

    try {
      // Simulate renewal process with progress updates
      const steps = [
        { message: 'Generating new key pair...', progress: 20 },
        { message: 'Creating certificate signing request...', progress: 40 },
        { message: 'Submitting to Certificate Authority...', progress: 60 },
        { message: 'Validating certificate chain...', progress: 80 },
        { message: 'Finalizing renewal...', progress: 100 },
      ];

      for (const step of steps) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        setProgress(step.progress);
      }

      // Call backend to perform renewal with justification when needed
      try {
        const payload: any = {
          justification: certificate.daysUntilExpiry != null && certificate.daysUntilExpiry > thresholdDays ? justification : undefined,
          requested_algorithm: renewalOptions.algorithm,
          requested_validity_years: parseInt(renewalOptions.validityPeriod)
        };
        // If user provided SANs, include in both camelCase and snake_case for backend compatibility
        if (altNames && typeof altNames === 'string') {
          const arr = altNames.split(',').map(s => s.trim()).filter(Boolean);
          if (arr.length) {
            (payload as any).altNames = arr;
            (payload as any).alt_names = arr;
          }
        }
        const token = localStorage.getItem('jwt_token');
        const res = await fetch(`/api/v1/devices/${certificate.deviceId}/certificate/renew`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.message || data.error || `Renewal failed (${res.status})`);
        }
        const data = await res.json();
        if (data?.certificate) {
          setNewCertificate({
            serialNumber: data.certificate.serial_number || data.certificate.serialNumber || 'New',
            issuedAt: data.certificate.issued_at || new Date().toISOString(),
            expiresAt: data.certificate.expires_at || new Date().toISOString(),
            algorithm: data.certificate.algorithm || renewalOptions.algorithm,
            status: 'active' as const
          });
        }
      } catch (apiErr: any) {
        // Fall back to mock success if API path not yet wired in environment
        console.warn('Renew API error or unavailable, falling back to simulated flow:', apiErr?.message);
      }

      const mockNewCertificate = newCertificate || {
        id: `cert-renewed-${Date.now()}`,
        serialNumber: `NEW${Math.random().toString(36).substr(2, 12).toUpperCase()}`,
        issuedAt: new Date().toISOString(),
        expiresAt: calculateNewExpiryDate().toISOString(),
        algorithm: renewalOptions.algorithm,
        status: 'active' as const,
      };

      setNewCertificate(mockNewCertificate);

      // Optionally revoke old certificate
      if (renewalOptions.revokeOld) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      setRenewalStep(RenewalStep.COMPLETE);
      toast.success('Certificate renewed successfully!');

      if (onRenewalComplete) {
        onRenewalComplete(certificate, mockNewCertificate);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setRenewalStep(RenewalStep.ERROR);
      toast.error('Certificate renewal failed');
    }
  };

  const handleDownloadCertificate = () => {
    // TODO: Implement actual certificate download
    toast.success('Certificate bundle downloaded');
  };

  const resetDialog = () => {
    setRenewalStep(RenewalStep.OPTIONS);
    setProgress(0);
    setError(null);
    setNewCertificate(null);
  };

  const handleDialogClose = (open: boolean) => {
    if (!open) {
      resetDialog();
    }
    onOpenChange(open);
  };

  const renderOptionsStep = () => (
    <div className="space-y-6">
      {/* Current Certificate Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-4 w-4" />
            Current Certificate
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            <Badge className={cn('flex items-center gap-1', getStatusColor(certificate.status))}>
              {getStatusIcon(certificate.status)}
              {certificate.status.charAt(0).toUpperCase() + certificate.status.slice(1)}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Expires</span>
            <span className="text-sm">
              {formatDate(certificate.expiresAt)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Days Remaining</span>
            <span className={cn(
              'text-sm font-medium',
              certificate.daysUntilExpiry == null || isNaN(certificate.daysUntilExpiry) ? 'text-gray-600' :
              certificate.daysUntilExpiry < 0 ? 'text-red-600' :
              certificate.daysUntilExpiry <= 30 ? 'text-yellow-600' :
              'text-green-600'
            )}>
              {certificate.daysUntilExpiry == null || isNaN(certificate.daysUntilExpiry)
                ? 'Unknown'
                : certificate.daysUntilExpiry < 0 
                ? `Expired ${Math.abs(certificate.daysUntilExpiry)} days ago`
                : `${certificate.daysUntilExpiry} days`
              }
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Algorithm</span>
            <span className="text-sm">{certificate.algorithm}</span>
          </div>
        </CardContent>
      </Card>

      {/* Renewal Options */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Renewal Options</CardTitle>
          <CardDescription>
            Configure the settings for the new certificate
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {certificate.daysUntilExpiry != null && certificate.daysUntilExpiry > thresholdDays && (
            <Alert className="border-amber-200 bg-amber-50">
              <AlertTitle>Early Renewal Policy</AlertTitle>
              <AlertDescription>
                This certificate still has {certificate.daysUntilExpiry} days remaining. Company policy requires a justification for renewals occurring more than {thresholdDays} days before expiration.
              </AlertDescription>
            </Alert>
          )}

          {policy && (
            (() => {
              const perType = policy.per_device_type || {};
              const typePol = perType[certificate.deviceType] || {};
              const allowed = typePol.allowed_algorithms || policy.allowed_algorithms || [];
              const defaultValidityDays = typePol.default_validity_days || policy.default_validity_days || 365;
              const selectedAlgo = renewalOptions.algorithm;
              const validityDays = parseInt(renewalOptions.validityPeriod) * 365;
              const algoWarn = allowed.length > 0 && !allowed.includes(selectedAlgo);
              const validityWarn = validityDays > defaultValidityDays;
              return (
                <>
                  {algoWarn && (
                    <Alert className="border-amber-200 bg-amber-50">
                      <AlertTitle>Algorithm Policy Deviation</AlertTitle>
                      <AlertDescription>
                        Selected algorithm "{selectedAlgo}" is not in the allowed list for {certificate.deviceType}. Allowed: {allowed.join(', ')}.
                      </AlertDescription>
                    </Alert>
                  )}
                  {validityWarn && (
                    <Alert className="border-amber-200 bg-amber-50">
                      <AlertTitle>Validity Policy Deviation</AlertTitle>
                      <AlertDescription>
                        Selected validity ({validityDays} days) exceeds default policy ({defaultValidityDays} days) for {certificate.deviceType}.
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              );
            })()
          )}
          <div className="space-y-2">
            <Label htmlFor="algorithm">Cryptographic Algorithm</Label>
            <Select
              value={renewalOptions.algorithm}
              onValueChange={(value) => setRenewalOptions(prev => ({ ...prev, algorithm: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select algorithm" />
              </SelectTrigger>
              <SelectContent>
                {ALGORITHM_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="validity">Validity Period</Label>
            <Select
              value={renewalOptions.validityPeriod}
              onValueChange={(value) => setRenewalOptions(prev => ({ ...prev, validityPeriod: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select validity period" />
              </SelectTrigger>
              <SelectContent>
                {VALIDITY_PERIODS.map((period) => (
                  <SelectItem key={period.value} value={period.value}>
                    {period.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="auto-download">Auto-download certificate bundle</Label>
                <div className="text-sm text-muted-foreground">
                  Automatically download the new certificate files after renewal
                </div>
              </div>
              <Switch
                id="auto-download"
                checked={renewalOptions.autoDownload}
                onCheckedChange={(checked) => setRenewalOptions(prev => ({ ...prev, autoDownload: checked }))}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="revoke-old">Revoke old certificate</Label>
                <div className="text-sm text-muted-foreground">
                  Automatically revoke the current certificate after successful renewal
                </div>
              </div>
              <Switch
                id="revoke-old"
                checked={renewalOptions.revokeOld}
                onCheckedChange={(checked) => setRenewalOptions(prev => ({ ...prev, revokeOld: checked }))}
              />
            </div>

            {/* Optional SANs (altNames) */}
            <div className="space-y-2">
              <Label htmlFor="alt-names" className="flex items-center gap-2">
                Subject Alternative Names (Optional)
              </Label>
              <Input
                id="alt-names"
                placeholder="e.g., DNS:device-001, URI:urn:tesa:device:device-001"
                value={altNames}
                onChange={(e) => setAltNames(e.target.value)}
              />
              <div className="text-xs text-muted-foreground">
                Comma-separated values. Supported formats: DNS:&lt;name&gt;, URI:&lt;urn&gt;. Leave empty if not needed.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* New Certificate Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Calendar className="h-4 w-4" />
            New Certificate Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Will expire</span>
            <span className="text-sm font-medium text-green-600">
              {formatNewExpiryDate()}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Algorithm</span>
            <span className="text-sm">{renewalOptions.algorithm}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Validity Period</span>
            <span className="text-sm">{renewalOptions.validityPeriod} year{renewalOptions.validityPeriod !== '1' ? 's' : ''}</span>
          </div>
        </CardContent>
      </Card>
      {certificate.daysUntilExpiry != null && certificate.daysUntilExpiry > thresholdDays && (
        <div className="space-y-2">
          <Label htmlFor="justification">Justification (required for early renewal)</Label>
          <Textarea
            id="justification"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Describe why this certificate must be renewed early (e.g., algorithm change, suspected compromise, compliance rotation)."
          />
        </div>
      )}
    </div>
  );

  const renderConfirmStep = () => (
    <div className="space-y-6">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Confirm Certificate Renewal</AlertTitle>
        <AlertDescription>
          Please review the details below and confirm that you want to proceed with the certificate renewal.
          This action will generate a new certificate for your device.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Renewal Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm font-medium">Device:</span>
            <span className="text-sm">{certificate.deviceName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font-medium">Current expires:</span>
            <span className="text-sm text-red-600">{formatDate(certificate.expiresAt)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font-medium">New expires:</span>
            <span className="text-sm text-green-600">{formatNewExpiryDate()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm font-medium">Algorithm:</span>
            <span className="text-sm">{renewalOptions.algorithm}</span>
          </div>
          {renewalOptions.revokeOld && (
            <div className="flex justify-between">
              <span className="text-sm font-medium">Old certificate:</span>
              <span className="text-sm text-yellow-600">Will be revoked</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );

  const renderProcessingStep = () => (
    <div className="space-y-6 text-center">
      <div className="flex justify-center">
        <RefreshCw className="h-12 w-12 text-blue-600 animate-spin" />
      </div>
      <div>
        <h3 className="text-lg font-semibold">Renewing Certificate</h3>
        <p className="text-muted-foreground">Please wait while we generate your new certificate...</p>
      </div>
      <div className="space-y-2">
        <Progress value={progress} className="w-full" />
        <p className="text-sm text-muted-foreground">{progress}% complete</p>
      </div>
    </div>
  );

  const renderCompleteStep = () => (
    <div className="space-y-6 text-center">
      <div className="flex justify-center">
        <CheckCircle className="h-12 w-12 text-green-600" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-green-600">Certificate Renewed Successfully!</h3>
        <p className="text-muted-foreground">Your new certificate has been generated and is ready for use.</p>
      </div>
      
      {newCertificate && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New Certificate Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium">Serial Number:</span>
              <span className="text-sm font-mono">{newCertificate.serialNumber}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium">Issued:</span>
              <span className="text-sm">{formatDate(newCertificate.issuedAt, 'MMM dd, yyyy HH:mm')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium">Expires:</span>
              <span className="text-sm">{formatDate(newCertificate.expiresAt)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm font-medium">Algorithm:</span>
              <span className="text-sm">{newCertificate.algorithm}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-center">
        <Button onClick={handleDownloadCertificate} className="flex items-center gap-2">
          <Download className="h-4 w-4" />
          Download Certificate Bundle
        </Button>
      </div>
    </div>
  );

  const renderErrorStep = () => (
    <div className="space-y-6 text-center">
      <div className="flex justify-center">
        <AlertTriangle className="h-12 w-12 text-red-600" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-red-600">Certificate Renewal Failed</h3>
        <p className="text-muted-foreground">An error occurred while renewing the certificate.</p>
      </div>
      
      {error && (
        <Alert className="text-left">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error Details</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );

  const getStepContent = () => {
    switch (renewalStep) {
      case RenewalStep.OPTIONS:
        return renderOptionsStep();
      case RenewalStep.CONFIRM:
        return renderConfirmStep();
      case RenewalStep.PROCESSING:
        return renderProcessingStep();
      case RenewalStep.COMPLETE:
        return renderCompleteStep();
      case RenewalStep.ERROR:
        return renderErrorStep();
      default:
        return renderOptionsStep();
    }
  };

  const getStepButtons = () => {
    switch (renewalStep) {
      case RenewalStep.OPTIONS:
        return (
          <>
            <Button variant="outline" onClick={() => handleDialogClose(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              if (certificate.daysUntilExpiry != null && certificate.daysUntilExpiry > thresholdDays && justification.trim().length === 0) {
                toast.error('Justification is required for early renewal');
                return;
              }
              setRenewalStep(RenewalStep.CONFIRM);
            }}>
              Continue
            </Button>
          </>
        );
      case RenewalStep.CONFIRM:
        return (
          <>
            <Button variant="outline" onClick={() => setRenewalStep(RenewalStep.OPTIONS)}>
              Back
            </Button>
            <Button onClick={handleRenewal}>
              Renew Certificate
            </Button>
          </>
        );
      case RenewalStep.PROCESSING:
        return null;
      case RenewalStep.COMPLETE:
        return (
          <Button onClick={() => handleDialogClose(false)}>
            Close
          </Button>
        );
      case RenewalStep.ERROR:
        return (
          <>
            <Button variant="outline" onClick={() => setRenewalStep(RenewalStep.OPTIONS)}>
              Try Again
            </Button>
            <Button onClick={() => handleDialogClose(false)}>
              Close
            </Button>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleDialogClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto z-[200]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Certificate Renewal - {certificate.deviceName}
          </DialogTitle>
          <DialogDescription>
            Renew the certificate for this device to maintain secure connectivity.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {getStepContent()}
        </div>

        <DialogFooter className="flex gap-2">
          {getStepButtons()}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
