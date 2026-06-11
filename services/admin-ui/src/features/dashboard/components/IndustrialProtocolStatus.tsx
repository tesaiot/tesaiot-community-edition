/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Network } from 'lucide-react';

export const IndustrialProtocolStatus: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Network className="h-4 w-4" />
          Industrial Protocol Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">Protocol status coming soon</p>
      </CardContent>
    </Card>
  );
};