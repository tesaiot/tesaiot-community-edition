/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useMemo } from 'react';
import { Card } from '@/components/ui/card';

interface AqiGaugeProps {
  value?: number | null;
  compact?: boolean;
}

// US EPA AQI breakpoints
const BANDS = [
  { max: 50, label: 'Good', color: '#2ecc71' },
  { max: 100, label: 'Moderate', color: '#f1c40f' },
  { max: 150, label: 'USG', color: '#e67e22' },
  { max: 200, label: 'Unhealthy', color: '#e74c3c' },
  { max: 300, label: 'Very Unhealthy', color: '#8e44ad' },
  { max: 500, label: 'Hazardous', color: '#7f1d1d' }
];

function clamp(v: number) { return Math.max(0, Math.min(500, v)); }

export const AqiGauge: React.FC<AqiGaugeProps> = ({ value, compact }) => {
  const v = typeof value === 'number' ? clamp(value) : null;
  const markerLeft = useMemo(() => {
    if (v == null) return 0;
    return (v / 500) * 100;
  }, [v]);

  const current = useMemo(() => {
    if (v == null) return { label: 'No Data', color: '#95a5a6' };
    return BANDS.find(b => v <= b.max) || BANDS[BANDS.length - 1];
  }, [v]);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <div className="text-sm text-muted-foreground">Air Quality Index</div>
        <div className="text-sm" style={{ color: current.color }}>
          {v != null ? `${v.toFixed(0)} · ${current.label}` : current.label}
        </div>
      </div>
      <div className="relative h-3 rounded bg-muted overflow-hidden">
        <div className="absolute inset-0 flex">
          {BANDS.map((b, i) => {
            const prev = i === 0 ? 0 : BANDS[i - 1].max;
            const width = ((b.max - prev) / 500) * 100;
            return <div key={b.max} style={{ width: `${width}%`, background: b.color }} />;
          })}
        </div>
        {/* Marker */}
        <div className="absolute -top-1 h-5 w-0.5 bg-white" style={{ left: `${markerLeft}%` }} />
      </div>
      {!compact && (
        <div className="flex justify-between mt-1 text-[10px] text-muted-foreground">
          <span>0</span>
          <span>100</span>
          <span>200</span>
          <span>300</span>
          <span>400</span>
          <span>500</span>
        </div>
      )}
    </div>
  );
};

