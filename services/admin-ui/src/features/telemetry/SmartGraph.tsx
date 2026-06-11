/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useMemo } from 'react';
import type { RJSFSchema } from '@rjsf/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { introspectSchema, assignAxes, decimate, type Metric } from './useSchemaMetrics';

interface SmartGraphProps {
  schema?: RJSFSchema;
  data: Array<Record<string, any>>; // array of telemetry records with ISO timestamp and flat/nested fields
  maxPoints?: number;
  // Optional server rollups for percentile bands (same timestamps as buckets)
  rollups?: Array<{
    timestamp: string;
    avg?: number;
    p10?: number;
    p90?: number;
    min?: number;
    max?: number;
  }>;
}

const THRESHOLDS: Record<string, number[]> = {
  '°C': [0, 25, 35],
  ppm: [800, 1000, 2000],
  'μg/m³': [25, 50, 150],
  '%RH': [30, 60, 80]
};

function getValue(rec: any, path: string): number | null {
  const parts = path.split('.');
  let cur: any = rec;
  for (const p of parts) {
    if (cur == null) return null;
    cur = cur[p];
  }
  if (typeof cur === 'number') return cur;
  if (typeof cur === 'string' && cur.trim() !== '' && !isNaN(Number(cur))) return Number(cur);
  // Fallback: flattened transport keys like accel_x for path accel.x
  const flatKey = path.replace(/\./g, '_');
  const flatVal = (rec as any)[flatKey];
  if (typeof flatVal === 'number') return flatVal;
  if (typeof flatVal === 'string' && flatVal.trim() !== '' && !isNaN(Number(flatVal))) return Number(flatVal);
  // Fallback for {value} flattening: pm2_5.value -> pm2_5_value
  if (path.endsWith('.value')) {
    const alt = path.slice(0, -('.value'.length)).replace(/\./g, '_') + '_value';
    const altVal = (rec as any)[alt];
    if (typeof altVal === 'number') return altVal;
    if (typeof altVal === 'string' && altVal.trim() !== '' && !isNaN(Number(altVal))) return Number(altVal);
  }
  return null;
}

// Insert gap rows with null values to break the line when time jumps are large
function insertGaps(rows: any[], keys: string[]): any[] {
  if (rows.length < 2) return rows;
  const out: any[] = [rows[0]];
  // Estimate median interval from first 20 deltas
  const deltas: number[] = [];
  for (let i = 1; i < Math.min(rows.length, 20); i++) {
    deltas.push(new Date(rows[i].timestamp).getTime() - new Date(rows[i - 1].timestamp).getTime());
  }
  const sorted = deltas.filter((d) => d > 0).sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  const threshold = median > 0 ? median * 3 : 120000; // default 2 minutes if unknown

  for (let i = 1; i < rows.length; i++) {
    const prev = rows[i - 1];
    const cur = rows[i];
    const gap = new Date(cur.timestamp).getTime() - new Date(prev.timestamp).getTime();
    if (gap > threshold) {
      const gapRow: any = { timestamp: new Date(new Date(prev.timestamp).getTime() + 1).toISOString() };
      keys.forEach((k) => (gapRow[k] = null));
      out.push(gapRow);
    }
    out.push(cur);
  }
  return out;
}

export function SmartGraph({ schema, data, maxPoints = 300, rollups }: SmartGraphProps) {
  const { metrics, chartData } = useMemo(() => {
    const ms = assignAxes(introspectSchema(schema));
    // Build chart rows: copy timestamp + each metric as a flat key for Recharts
    const base = decimate(data, maxPoints).map((r) => {
      const row: any = { timestamp: r.timestamp, ...(r.data || r) };
      ms.forEach((m) => {
        const v = getValue(r.data || r, m.path);
        if (v !== null) {
          row[m.key] = v;
        }
      });
      return row;
    });
    const withGaps = insertGaps(base, ms.map((m) => m.key));
    return { metrics: ms, chartData: withGaps };
  }, [schema, data, maxPoints]);

  // Pick up to 6 series to keep readable; prefer scalar + vector axes first
  const series = metrics.filter((m) => m.kind === 'scalar' || m.kind === 'vector').slice(0, 6);
  const units = Array.from(new Set(series.map((s) => s.unit || '—')));

  const colors = ['#2b8a3e', '#1971c2', '#e8590c', '#a61e4d', '#5c940d', '#7048e8'];

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" tickFormatter={(v) => new Date(v).toLocaleTimeString()} />
          <YAxis yAxisId="left" />
          {units.length > 1 && <YAxis yAxisId="right" orientation="right" />}
          <Tooltip labelFormatter={(v) => new Date(v as string).toLocaleString()} />
          <Legend />
          {/* Percentile band from server rollups (p10-p90) and avg line, if provided */}
          {rollups && rollups.length > 0 && (
            <>
              {/* Render as additional series keys on left axis */}
              {/* We map rollups by timestamp to band values; Recharts ReferenceArea needs x1/x2; for simplicity, draw as invisible lines won't work for band. Skip band if complex; use ReferenceLine min/max p10/p90? Instead approximate by lines for p10/p90 */}
              {/* p10 and p90 lines act as a visual band boundary */}
              <Line key="p10" type="monotone" data={rollups} dataKey="p10" yAxisId="left" stroke="#94d2bd" dot={false} strokeDasharray="4 4" isAnimationActive={false} />
              <Line key="p90" type="monotone" data={rollups} dataKey="p90" yAxisId="left" stroke="#94d2bd" dot={false} strokeDasharray="4 4" isAnimationActive={false} />
              <Line key="avg" type="monotone" data={rollups} dataKey="avg" yAxisId="left" stroke="#0a9396" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            </>
          )}
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              yAxisId={s.axis === 'right' ? 'right' : 'left'}
              stroke={colors[i % colors.length]}
              dot={false}
              strokeWidth={2}
              isAnimationActive={false}
              connectNulls={false}
            />
          ))}
          {/* Threshold overlays when unit known */}
          {Array.from(new Set(series.map((s) => s.unit).filter(Boolean) as string[])).flatMap((u, idx) =>
            (THRESHOLDS[u] || []).map((v) => (
              <ReferenceLine key={`${u}-${v}`} y={v} yAxisId={idx === 0 ? 'left' : 'right'} stroke="#adb5bd" strokeDasharray="4 4" />
            ))
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SmartGraphInspector({ schema }: { schema?: RJSFSchema }) {
  const m = assignAxes(introspectSchema(schema));
  return (
    <div className="text-xs rounded-md border p-3 bg-muted/30">
      <div className="font-medium mb-2">Detected metrics</div>
      {m.length === 0 ? (
        <div className="text-muted-foreground">No metrics found in schema.</div>
      ) : (
        <ul className="grid grid-cols-2 md:grid-cols-3 gap-1">
          {m.map((x) => (
            <li key={x.path} className="text-muted-foreground">
              <span className="font-mono">{x.key}</span> · {x.kind} · unit: {x.unit || '—'} · axis: {x.axis || 'left'}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
