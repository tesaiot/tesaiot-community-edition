/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const RealtimeMetrics: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Real-time Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">WebSocket metrics coming soon</p>
      </CardContent>
    </Card>
  );
};
