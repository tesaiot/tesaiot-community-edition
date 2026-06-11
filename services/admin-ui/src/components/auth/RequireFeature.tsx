/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { useLicense } from '@/hooks/useLicense';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lock } from 'lucide-react';

interface RequireFeatureProps {
  feature: string | string[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const RequireFeature: React.FC<RequireFeatureProps> = ({
  feature,
  fallback,
  children
}) => {
  const { hasFeature, hasFeatures } = useLicense();
  
  // Check if user has access to the feature(s)
  const hasAccess = Array.isArray(feature) 
    ? hasFeatures(...feature)
    : hasFeature(feature as any);
  
  if (hasAccess) {
    return <>{children}</>;
  }
  
  // Show fallback or default upgrade prompt
  if (fallback) {
    return <>{fallback}</>;
  }
  
  return (
    <Card className="max-w-2xl mx-auto mt-8">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lock className="h-5 w-5 text-muted-foreground" />
          <CardTitle>Feature Restricted</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">
          This feature is not available in your current license edition.
          Upgrade to unlock advanced capabilities.
        </p>
        <div className="flex gap-3">
          <Button>
            Upgrade License
          </Button>
          <Button variant="outline">
            Learn More
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};