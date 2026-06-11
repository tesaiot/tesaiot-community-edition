/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Smart Telemetry Dashboard (Beta Duplicate)
 * Purpose: Parallel internal testing; leaves original SmartTelemetryDashboard untouched
 */

import React from 'react';
import { SmartTelemetryDashboard as OriginalSmart } from './SmartTelemetryDashboard';

interface Device { id: string; device_id: string; name: string; status: string; type: string; }

interface SmartTelemetryDashboardBetaProps {
  devices: Device[];
  className?: string;
  isTabActive?: boolean;
  showTitle?: boolean;
}

export function SmartTelemetryDashboardBeta(props: SmartTelemetryDashboardBetaProps) {
  return (
    <div className="space-y-2">
      {props.showTitle !== false && (
        <h2 className="text-xl font-semibold">Smart Telemetry Dashboard (Beta)</h2>
      )}
      <OriginalSmart {...props} showTitle={false} />
    </div>
  );
}

