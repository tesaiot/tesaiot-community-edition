/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const ApiUsageChart: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">API Usage</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">API usage chart coming soon</p>
      </CardContent>
    </Card>
  );
};
