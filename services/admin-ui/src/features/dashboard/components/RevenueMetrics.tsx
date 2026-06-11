/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DollarSign } from 'lucide-react';

export const RevenueMetrics: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <DollarSign className="h-4 w-4" />
          Revenue Metrics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">Revenue metrics coming soon</p>
      </CardContent>
    </Card>
  );
};