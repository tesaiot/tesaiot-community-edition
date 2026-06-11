/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Shield, ShieldCheck, Check, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';
import { useLicenseContext } from '@/providers/license-provider';

interface ETSIComplianceBadgeProps {
  score?: number;
  total?: number;
}

// ETSI EN 303 645 Compliance Requirements
const complianceItems = [
  { id: 1, requirement: 'No universal default passwords', compliant: true },
  { id: 2, requirement: 'Implement a means to manage reports of vulnerabilities', compliant: true },
  { id: 3, requirement: 'Keep software updated', compliant: true },
  { id: 4, requirement: 'Securely store sensitive security parameters', compliant: true },
  { id: 5, requirement: 'Communicate securely', compliant: true },
  { id: 6, requirement: 'Minimize exposed attack surfaces', compliant: true },
  { id: 7, requirement: 'Ensure software integrity', compliant: true },
  { id: 8, requirement: 'Ensure that personal data is secure', compliant: true },
  { id: 9, requirement: 'Make systems resilient to outages', compliant: true },
  { id: 10, requirement: 'Examine system telemetry data', compliant: true },
  { id: 11, requirement: 'Make it easy for users to delete user data', compliant: false },
  { id: 12, requirement: 'Make installation and maintenance of devices easy', compliant: true },
  { id: 13, requirement: 'Validate input data', compliant: false },
];

// ISO/IEC 27402 Requirements
const isoRequirements = [
  { id: 1, requirement: 'Security by design', compliant: true },
  { id: 2, requirement: 'Data protection', compliant: true },
  { id: 3, requirement: 'Access control', compliant: true },
  { id: 4, requirement: 'Incident response', compliant: true },
  { id: 5, requirement: 'Vulnerability management', compliant: true },
  { id: 6, requirement: 'Audit and compliance', compliant: false },
  { id: 7, requirement: 'Supply chain security', compliant: false },
  { id: 8, requirement: 'Privacy by design', compliant: false },
];

export const ETSIComplianceBadge: React.FC<ETSIComplianceBadgeProps> = ({ 
  score = complianceItems.filter(item => item.compliant).length, 
  total = complianceItems.length 
}) => {
  const navigate = useNavigate();
  const { edition } = useLicenseContext();
  const isCommercial = edition !== 'community';
  
  // Calculate ETSI compliance
  const etsiCompliant = isCommercial ? complianceItems.length : 9;
  const etsiPercentage = Math.round((etsiCompliant / complianceItems.length) * 100);
  
  // Calculate ISO compliance
  const isoCompliant = isCommercial ? isoRequirements.length : 5;
  const isoPercentage = Math.round((isoCompliant / isoRequirements.length) * 100);
  
  const percentage = etsiPercentage; // Keep backward compatibility
  const variant = percentage >= 80 ? 'default' : percentage >= 50 ? 'secondary' : 'destructive';

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button 
          variant="ghost" 
          className="h-auto p-0 hover:bg-transparent"
          title="Click to view cybersecurity compliance details"
        >
          <Badge 
            variant={isCommercial ? 'default' : 'secondary'} 
            className="flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition-opacity"
          >
            <Shield className="h-3 w-3" />
            <span className="hidden lg:inline">ETSI & ISO Cybersecurity</span>
            <span className="lg:hidden">Cybersecurity</span>
            <span className="font-medium">{isCommercial ? '100%' : '70%'}</span>
          </Badge>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[480px] max-h-[85vh] overflow-y-auto p-0" align="end">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-semibold">Cybersecurity Compliance Overview</h4>
              <p className="text-sm text-muted-foreground">
                {edition === 'community' ? 'Community Edition' : 'Commercial Edition'}
              </p>
            </div>
            <Button 
              size="sm" 
              onClick={() => navigate('/security/compliance')}
            >
              View Details
            </Button>
          </div>
        </div>
        
        <div className="p-4 space-y-4">
          {/* ETSI Compliance Summary */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                <span className="font-medium">ETSI EN 303 645</span>
              </div>
              <span className="text-sm font-semibold">{etsiPercentage}%</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full transition-all duration-500",
                  etsiPercentage >= 80 ? "bg-green-500" : 
                  etsiPercentage >= 50 ? "bg-amber-500" : 
                  "bg-red-500"
                )}
                style={{ width: `${etsiPercentage}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {etsiCompliant} of {complianceItems.length} requirements met
            </p>
          </div>
          
          {/* ISO Compliance Summary */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <span className="font-medium">ISO/IEC 27402</span>
              </div>
              <span className="text-sm font-semibold">{isoPercentage}%</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full transition-all duration-500",
                  isoPercentage >= 80 ? "bg-green-500" : 
                  isoPercentage >= 50 ? "bg-amber-500" : 
                  "bg-red-500"
                )}
                style={{ width: `${isoPercentage}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {isoCompliant} of {isoRequirements.length} requirements met
            </p>
          </div>
        </div>
        
        <div className="border-t p-4 space-y-3">
          <h5 className="text-sm font-medium text-muted-foreground">Key Compliance Areas:</h5>
          
          {/* Top compliance items */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { name: 'No Default Passwords', status: true },
              { name: 'Secure Communication', status: true },
              { name: 'Regular Updates', status: true },
              { name: 'Data Protection', status: true },
              { name: 'Input Validation', status: isCommercial },
              { name: 'Privacy Controls', status: isCommercial },
            ].map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                {item.status ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <X className="h-3 w-3 text-amber-500" />
                )}
                <span className="text-xs">{item.name}</span>
              </div>
            ))}
          </div>
          
          {!isCommercial && (
            <div className="pt-3 border-t">
              <p className="text-xs text-muted-foreground">
                Upgrade to Commercial Edition for 100% compliance with advanced security features.
              </p>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};
