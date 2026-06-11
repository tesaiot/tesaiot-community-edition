/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Layers } from 'lucide-react';

export const DigitalTwinStatus: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Layers className="h-4 w-4" />
          Digital Twin Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">Digital twin status coming soon</p>
      </CardContent>
    </Card>
  );
};