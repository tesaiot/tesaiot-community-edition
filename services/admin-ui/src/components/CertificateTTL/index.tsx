/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Info, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

export interface CertificateTTLValue {
  days: number;
  preset?: string;
  justification?: string;
  requiresApproval?: boolean;
  securityScore?: number;
  riskLevel?: 'none' | 'low' | 'medium' | 'high' | 'critical';
}

interface CertificateTTLProps {
  value?: CertificateTTLValue;
  onChange: (value: CertificateTTLValue) => void;
  disabled?: boolean;
  showRecommendations?: boolean;
  organizationMaxTTL?: number;
}

interface TTLPreset {
  value: number;
  label: string;
  description: string;
  riskLevel: 'none' | 'low' | 'medium' | 'high' | 'critical';
}

const TTL_PRESETS: TTLPreset[] = [
  { 
    value: 7, 
    label: 'Development (7 days)', 
    description: 'For testing and development environments only',
    riskLevel: 'none' 
  },
  { 
    value: 30, 
    label: 'Production - High Security (30 days)', 
    description: 'Recommended for critical infrastructure and high-value assets',
    riskLevel: 'low' 
  },
  { 
    value: 90, 
    label: 'Production - Standard (90 days)', 
    description: 'Industry standard for most production IoT devices',
    riskLevel: 'low' 
  },
  { 
    value: 365, 
    label: 'Remote Deployment (1 year)', 
    description: 'For devices with limited connectivity or update capabilities',
    riskLevel: 'medium' 
  }
];

export const CertificateTTL: React.FC<CertificateTTLProps> = ({
  value,
  onChange,
  disabled = false,
  showRecommendations = true,
  organizationMaxTTL = 1095
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('90');
  const [customDays, setCustomDays] = useState<string>('');
  const [justification, setJustification] = useState<string>(value?.justification || '');
  const [showCustom, setShowCustom] = useState(false);

  // Initialize from value prop
  useEffect(() => {
    if (value?.days) {
      const preset = TTL_PRESETS.find(p => p.value === value.days);
      if (preset) {
        setSelectedPreset(value.days.toString());
        setShowCustom(false);
      } else {
        setSelectedPreset('custom');
        setCustomDays(value.days.toString());
        setShowCustom(true);
      }
      setJustification(value.justification || '');
    }
  }, [value]);

  const currentDays = selectedPreset === 'custom' 
    ? parseInt(customDays) || 0 
    : parseInt(selectedPreset) || 0;

  const requiresJustification = currentDays > 365;
  const requiresApproval = currentDays > 730;

  const calculateSecurityScore = (days: number): number => {
    if (days <= 7) return 10;
    if (days <= 30) return 9;
    if (days <= 90) return 8;
    if (days <= 180) return 7;
    if (days <= 365) return 6;
    if (days <= 730) return 4;
    return 2;
  };

  const getRiskLevel = (days: number): 'none' | 'low' | 'medium' | 'high' | 'critical' => {
    if (days <= 30) return 'none';
    if (days <= 90) return 'low';
    if (days <= 365) return 'medium';
    if (days <= 730) return 'high';
    return 'critical';
  };

  const getWarning = (days: number) => {
    if (days <= 7) {
      return {
        level: 'info',
        icon: <Info className="w-4 h-4 text-blue-500" />,
        message: 'Development mode: Very short validity for testing purposes only'
      };
    }
    if (days <= 30) {
      return {
        level: 'success',
        icon: <CheckCircle className="w-4 h-4 text-green-500" />,
        message: 'Excellent security: Following zero-trust best practices'
      };
    }
    if (days <= 90) {
      return {
        level: 'success',
        icon: <CheckCircle className="w-4 h-4 text-green-500" />,
        message: 'Good security: Industry standard certificate rotation'
      };
    }
    if (days <= 365) {
      return {
        level: 'warning',
        icon: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
        message: 'Acceptable for remote devices with update constraints'
      };
    }
    if (days <= 730) {
      return {
        level: 'danger',
        icon: <AlertTriangle className="w-4 h-4 text-orange-500" />,
        message: 'High risk: Consider implementing automated certificate rotation'
      };
    }
    return {
      level: 'critical',
      icon: <XCircle className="w-4 h-4 text-red-500" />,
      message: 'Critical risk: Exceeds all industry security recommendations'
    };
  };

  const warning = getWarning(currentDays);

  const handlePresetChange = (presetValue: string) => {
    setSelectedPreset(presetValue);
    
    if (presetValue === 'custom') {
      setShowCustom(true);
      // Don't update parent until custom value is entered
      return;
    }
    
    setShowCustom(false);
    const days = parseInt(presetValue);
    const preset = TTL_PRESETS.find(p => p.value === days);
    
    onChange({
      days,
      preset: preset?.label,
      justification: days > 365 ? justification : undefined,
      requiresApproval: days > 730,
      securityScore: calculateSecurityScore(days),
      riskLevel: getRiskLevel(days)
    });
  };

  const handleCustomDaysChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setCustomDays(value);
    
    const days = parseInt(value);
    if (!isNaN(days) && days > 0) {
      onChange({
        days,
        preset: 'custom',
        justification: days > 365 ? justification : undefined,
        requiresApproval: days > 730,
        securityScore: calculateSecurityScore(days),
        riskLevel: getRiskLevel(days)
      });
    }
  };

  const handleJustificationChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setJustification(text);
    
    if (currentDays > 0) {
      onChange({
        days: currentDays,
        preset: selectedPreset === 'custom' ? 'custom' : TTL_PRESETS.find(p => p.value === currentDays)?.label,
        justification: text,
        requiresApproval: currentDays > 730,
        securityScore: calculateSecurityScore(currentDays),
        riskLevel: getRiskLevel(currentDays)
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label>Certificate Validity Period</Label>
          <Info 
            className="h-4 w-4 text-muted-foreground cursor-help" 
            title="Certificate validity period determines how long the device's security credentials remain valid. Shorter periods provide better security but require more frequent updates."
          />
        </div>
        
        <RadioGroup 
          value={selectedPreset} 
          onValueChange={handlePresetChange}
          disabled={disabled}
        >
          {TTL_PRESETS.map((preset) => (
            <div key={preset.value} className="flex items-center space-x-2">
              <RadioGroupItem value={preset.value.toString()} id={`ttl-${preset.value}`} />
              <Label htmlFor={`ttl-${preset.value}`} className="font-normal cursor-pointer">
                <div>
                  <div className="font-medium">{preset.label}</div>
                  <div className="text-sm text-muted-foreground">
                    {preset.description}
                  </div>
                </div>
              </Label>
            </div>
          ))}
          
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="custom" id="ttl-custom" />
            <Label htmlFor="ttl-custom" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium">Custom Duration</div>
                <div className="text-sm text-muted-foreground">
                  Specify a custom validity period (requires justification for &gt;365 days)
                </div>
              </div>
            </Label>
          </div>
        </RadioGroup>

        {showCustom && (
          <div className="ml-6 mt-2 space-y-2">
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min="1"
                max={organizationMaxTTL}
                value={customDays}
                onChange={handleCustomDaysChange}
                placeholder="Enter days"
                className="w-32"
                disabled={disabled}
              />
              <span className="text-sm text-muted-foreground">days</span>
            </div>
            {parseInt(customDays) > organizationMaxTTL && (
              <p className="text-sm text-destructive">
                Maximum allowed: {organizationMaxTTL} days
              </p>
            )}
          </div>
        )}
      </div>

      {currentDays > 0 && (
        <>
          <Alert className={
            warning.level === 'success' ? 'border-green-500 bg-green-50' :
            warning.level === 'warning' ? 'border-yellow-500 bg-yellow-50' :
            warning.level === 'danger' ? 'border-orange-500 bg-orange-50' :
            warning.level === 'critical' ? 'border-red-500 bg-red-50' :
            'border-blue-500 bg-blue-50'
          }>
            <div className="flex items-start gap-2">
              {warning.icon}
              <AlertDescription className="space-y-2">
                <p className="font-medium">{warning.message}</p>
                <div className="flex flex-wrap gap-4 text-sm">
                  <span className="flex items-center gap-1">
                    <Shield className="w-3 h-3" />
                    Security Score: {calculateSecurityScore(currentDays)}/10
                  </span>
                  <span>First renewal: Day {Math.max(1, currentDays - 5)}</span>
                  <span>Frequency: Every {currentDays} days</span>
                </div>
              </AlertDescription>
            </div>
          </Alert>

          {requiresJustification && (
            <div className="space-y-2">
              <Label htmlFor="justification" className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                Business Justification Required
                {requiresApproval && (
                  <Badge variant="destructive" className="ml-2">Requires Approval</Badge>
                )}
              </Label>
              <Textarea
                id="justification"
                value={justification}
                onChange={handleJustificationChange}
                placeholder="Please provide business justification for extended certificate validity (minimum 100 characters)"
                className="min-h-[100px]"
                disabled={disabled}
                required
              />
              {justification.length < 100 && justification.length > 0 && (
                <p className="text-sm text-destructive">
                  {100 - justification.length} more characters required
                </p>
              )}
            </div>
          )}

          {showRecommendations && currentDays > 365 && (
            <Alert className="border-orange-500 bg-orange-50">
              <AlertTriangle className="w-4 h-4" />
              <AlertDescription>
                <p className="font-medium mb-2">Security Recommendations:</p>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  <li>AWS, Azure, and Google Cloud all recommend against certificates &gt; 1 year</li>
                  <li>Industry trend: Moving from 398 days → 90 days → 47 days by 2029</li>
                  <li>Consider implementing automatic certificate rotation instead</li>
                  <li>Ensure device has capability to update certificates remotely</li>
                </ul>
              </AlertDescription>
            </Alert>
          )}
        </>
      )}
    </div>
  );
};

export default CertificateTTL;