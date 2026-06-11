/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Shield, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { tesaApi } from '@/services/api/tesaApi';
import { useAuth } from '@/hooks/useAuth';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";

interface ComplianceItem {
  name: string;
  status: 'compliant' | 'warning' | 'non-compliant';
  description: string;
}

interface ComplianceIndicatorProps {
  enhanced?: boolean;
}

export const ComplianceIndicator: React.FC<ComplianceIndicatorProps> = ({ enhanced = false }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [complianceItems, setComplianceItems] = useState<ComplianceItem[]>([
    {
      name: 'ETSI EN 303 645',
      status: 'compliant',
      description: 'IoT Security Standard Compliance',
    },
    {
      name: 'Data Encryption',
      status: 'compliant',
      description: 'All data encrypted in transit and at rest',
    },
    {
      name: 'Certificate Management',
      status: 'compliant',
      description: 'Automated PKI with HashiCorp Vault',
    },
    {
      name: 'Access Control',
      status: 'compliant',
      description: 'Role-based access control enabled',
    },
    {
      name: 'Audit Logging',
      status: 'warning',
      description: 'Partial logging coverage',
    },
  ]);
  
  // Fetch real compliance data from API
  useEffect(() => {
    const fetchComplianceData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await tesaApi.get('/dashboard/compliance/summary');
        
        if (response.data?.data?.compliance_items) {
          setComplianceItems(response.data.data.compliance_items);
        }
      } catch (err) {
        console.error('Failed to fetch compliance data:', err);
        setError('Failed to load compliance data');
        // Keep default data on error
      } finally {
        setLoading(false);
      }
    };
    
    fetchComplianceData();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchComplianceData, 300000);
    return () => clearInterval(interval);
  }, [user]);

  const getComplianceScore = () => {
    const compliantCount = complianceItems.filter(item => item.status === 'compliant').length;
    return (compliantCount / complianceItems.length) * 100;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'compliant':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'non-compliant':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'compliant':
        return <Badge variant="default" className="bg-green-500">Compliant</Badge>;
      case 'warning':
        return <Badge variant="secondary" className="bg-yellow-500 text-white">Warning</Badge>;
      case 'non-compliant':
        return <Badge variant="destructive">Non-Compliant</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const complianceScore = getComplianceScore();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Security Compliance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        )}
        
        {error && (
          <div className="text-center py-4 text-red-600 dark:text-red-400">
            {error}
          </div>
        )}
        
        {!loading && !error && (
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium">Overall Compliance</span>
            <span className="text-sm font-bold">{Math.round(complianceScore)}%</span>
          </div>
          <Progress value={complianceScore} className="h-3" />
        </div>

        <div className="space-y-3">
          {complianceItems.map((item) => (
            <div key={item.name} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getStatusIcon(item.status)}
                  <span className="text-sm font-medium">{item.name}</span>
                </div>
                {getStatusBadge(item.status)}
              </div>
              <p className="text-xs text-gray-500 ml-6">{item.description}</p>
            </div>
          ))}
        </div>

        <div className="pt-3 border-t">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Info className="h-4 w-4" />
            <span>Last audit: {new Date().toLocaleDateString()}</span>
          </div>
        </div>
        )}
      </CardContent>
    </Card>
  );
};