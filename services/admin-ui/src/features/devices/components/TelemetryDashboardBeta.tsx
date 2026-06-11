/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Real-time Telemetry Dashboard
 * Schema-driven Smart Graph with automatic schema inference fallback.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RJSFSchema } from '@rjsf/utils';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { authFetch } from '@/utils/auth-fetch';
import { useTelemetryWebSocket } from '@/hooks/useTelemetryWebSocket';
import { SmartGraph, SmartGraphInspector } from '@/features/telemetry/SmartGraph';
import { RawDataPanel } from '@/features/telemetry/RawDataPanel';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { formatTelemetryData } from '@/utils/telemetry-formatter';
import { AqiGauge } from '@/features/telemetry/AqiGauge';
import { cn } from '@/lib/utils';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface Device { id: string; device_id: string; name: string; status: string; type: string; telemetrySchema?: { schema?: RJSFSchema } }

interface TelemetryDashboardBetaProps {
  devices: Device[];
  className?: string;
  isTabActive?: boolean;
  showTitle?: boolean;
}

const buildSchemaFromSample = (sample: any): RJSFSchema => {
  const properties: Record<string, any> = {};
  if (!sample || typeof sample !== 'object') {
    return { type: 'object', properties };
  }

  Object.entries(sample).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === 'number') {
      properties[key] = { type: 'number' };
    } else if (typeof value === 'boolean') {
      properties[key] = { type: 'boolean' };
    } else if (Array.isArray(value)) {
      const numeric = value.filter((item) => typeof item === 'number');
      if (numeric.length) {
        properties[key] = { type: 'array', items: { type: 'number' } };
      }
    } else if (typeof value === 'object') {
      const child = buildSchemaFromSample(value);
      if (child.properties && Object.keys(child.properties).length > 0) {
        properties[key] = { type: 'object', properties: child.properties };
      }
    }
  });

  return { type: 'object', properties };
};

export function TelemetryDashboardBeta({ devices, className, isTabActive = true, showTitle = true }: TelemetryDashboardBetaProps) {
  const [deviceId, setDeviceId] = useState<string | undefined>(devices?.[0]?.device_id || devices?.[0]?.id);
  const device = useMemo(() => devices?.find(d => (d.device_id || d.id) === deviceId) || devices?.[0], [devices, deviceId]);
  const schema: RJSFSchema | undefined = device?.telemetrySchema?.schema as any;

  const [telemetryData, setTelemetryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [bands, setBands] = useState<Array<{ timestamp: string; avg?: number; p10?: number; p90?: number }>>([]);
  const [range, setRange] = useState<'1h' | '24h' | '7d'>('1h');
  const lastRequestRef = useRef(0);

  const effectiveSchema = useMemo(() => {
    const hasSchema = schema && Object.keys((schema as any)?.properties || {}).length > 0;
    if (hasSchema) {
      return schema;
    }

    const sampleRecord = [...telemetryData].reverse().find((record) => {
      const src = record?.data || record;
      return src && typeof src === 'object' && Object.keys(src).length > 0;
    });
    if (sampleRecord) {
      const generated = buildSchemaFromSample(sampleRecord.data || sampleRecord);
      if (generated.properties && Object.keys(generated.properties).length > 0) {
        return generated;
      }
    }

    return schema;
  }, [schema, telemetryData]);

  // WebSocket live updates (append-head, cap to 200)
  const { subscribeToDevice, unsubscribeFromDevice } = useTelemetryWebSocket({
    onDeviceTelemetry: (deviceId: string, data: any) => {
      if (!device) return;
      if ((device.device_id || device.id) !== deviceId) return;
      const record = { timestamp: new Date().toISOString(), ...(typeof data === 'object' ? data : { value: data }), data };
      setTelemetryData((prev) => [...prev, record].slice(-200));
    }
  });

  const fetchInitial = useCallback(async () => {
    if (!device) return;
    const now = Date.now();
    if (now - lastRequestRef.current < 900) return;
    lastRequestRef.current = now;
    setLoading(true);
    try {
      const res = await authFetch(`/api/v1/devices/${device.device_id || device.id}/telemetry?limit=100`);
      if (res.ok) {
        const data = await res.json();
        const raw = Array.isArray(data?.telemetry) ? data.telemetry : [];
        const arr = formatTelemetryData(raw) as any[];
        // Ensure ascending time for charts
        const sorted = [...arr].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        setTelemetryData(sorted);
      }
      // Try server rollups only when feature flag enabled (avoid 404 noise otherwise)
      try {
        const { isFeatureEnabled } = await import('@/config/features.config');
        if (isFeatureEnabled('TELEMETRY_HISTORICAL_QUERY')) {
          const to = Date.now();
          const from = range === '1h' ? to - 60 * 60 * 1000 : range === '24h' ? to - 24 * 60 * 60 * 1000 : to - 7 * 24 * 60 * 60 * 1000;
          const resolution = range === '1h' ? '1m' : range === '24h' ? '5m' : '1h';
          // Pick first 1–2 numeric metrics from schema for demo
          const baseSchema = schema && Object.keys((schema as any)?.properties || {}).length > 0 ? schema : null;
          const metrics = baseSchema
            ? Object.keys((baseSchema as any).properties).filter((k) => k !== 'timestamp').slice(0, 2)
            : [];
          if (metrics.length > 0) {
            const q = new URLSearchParams({ deviceId: String(device.device_id || device.id), from: String(from), to: String(to), resolution, metrics: metrics.join(',') });
            const r2 = await authFetch(`/api/v1/telemetry/query?${q.toString()}`);
            if (r2.ok) {
              const body = await r2.json();
              // Flexible parsing: array; or {items:[...]}; or items[].series.<metricKey>
              const rows: any[] = Array.isArray(body) ? body : Array.isArray(body?.items) ? body.items : [];
              const mapped = rows.map((x: any) => {
                if (x.avg !== undefined || x.p10 !== undefined || x.p90 !== undefined) {
                  return { timestamp: x.timestamp, avg: x.avg, p10: x.p10, p90: x.p90 };
                }
                if (x.series && typeof x.series === 'object') {
                  const firstKey = Object.keys(x.series)[0];
                  const s = x.series[firstKey] || {};
                  return { timestamp: x.timestamp, avg: s.avg, p10: s.p10, p90: s.p90 };
                }
                return null;
              }).filter(Boolean);
              setBands(mapped);
            } else {
              setBands([]);
            }
          } else {
            setBands([]);
          }
        } else {
          setBands([]);
        }
      } catch {
        setBands([]);
      }
    } finally {
      setLoading(false);
    }
  }, [device, range, schema]);

  useEffect(() => {
    if (!device) return;
    const id = device.device_id || device.id;
    subscribeToDevice(id);
    fetchInitial();
    return () => unsubscribeFromDevice(id);
  }, [device, subscribeToDevice, unsubscribeFromDevice, fetchInitial]);

  const header = useMemo(() => (
      <div className="flex items-center justify-between">
        <div>
          {showTitle && <h2 className="text-2xl font-bold">Real-time Telemetry</h2>}
          <p className="text-muted-foreground">Schema-driven Smart Graph preview</p>
        </div>
        <div className="flex items-center gap-2">
          {devices?.length > 1 && (
            <Select value={deviceId} onValueChange={setDeviceId}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select device" />
              </SelectTrigger>
              <SelectContent>
                {devices.map((d) => (
                  <SelectItem key={d.device_id || d.id} value={String(d.device_id || d.id)}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" size="sm" onClick={() => setShowDebug(v => !v)}>
            {showDebug ? 'Hide Debug' : 'Show Debug'}
          </Button>
          <Button variant="outline" size="sm" onClick={() => fetchInitial()} disabled={loading}>
            <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} /> Refresh
          </Button>
        </div>
      </div>
  ), [showTitle, loading, fetchInitial, showDebug, deviceId, devices]);

  return (
    <div className={cn('space-y-4', className)}>
      {header}
      <div className="flex items-center gap-2">
        <div className="text-sm text-muted-foreground">Range</div>
        <Select value={range} onValueChange={(v: any) => setRange(v)}>
          <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="1h">Last 1h</SelectItem>
            <SelectItem value="24h">Last 24h</SelectItem>
            <SelectItem value="7d">Last 7d</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {showDebug && (
        <Card>
          <CardHeader>
            <CardTitle>Debug: Parsed Metrics & Sample</CardTitle>
            <CardDescription>Use this to verify schema detection</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted/40 p-3 rounded overflow-auto max-h-64">
              {JSON.stringify({ schemaKeys: Object.keys((schema as any)?.properties || {}), sample: telemetryData[0] }, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Inspector</CardTitle>
          <CardDescription>Auto-detected metrics from the device schema</CardDescription>
        </CardHeader>
        <CardContent>
          {effectiveSchema && Object.keys((effectiveSchema as any)?.properties || {}).length > 0 ? (
            <SmartGraphInspector schema={effectiveSchema} />
          ) : (
            <div className="text-sm text-muted-foreground">
              No telemetry fields detected yet. Once the device sends telemetry we will infer the schema automatically.
            </div>
          )}
        </CardContent>
      </Card>
      {(() => {
        const latest = telemetryData[0] || {};
        const src = latest.data || latest;
        let aqi: number | null = null;
        if (typeof src?.aqi === 'number') aqi = src.aqi;
        else if (typeof src?.aqi?.value === 'number') aqi = src.aqi.value;
        else if (typeof src?.air_quality === 'string') {
          const map: Record<string, number> = { excellent: 25, good: 50, moderate: 100, unhealthy_sensitive: 125, unhealthy: 175, very_unhealthy: 250, hazardous: 400 };
          aqi = map[src.air_quality] ?? null;
        }
        return aqi != null ? (
          <Card>
            <CardHeader>
              <CardTitle>Air Quality</CardTitle>
              <CardDescription>US EPA banded AQI gauge</CardDescription>
            </CardHeader>
            <CardContent>
              <AqiGauge value={aqi} />
            </CardContent>
          </Card>
        ) : null;
      })()}
      <Tabs defaultValue="graph" className="mt-2">
        <TabsList>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="raw">Raw Data</TabsTrigger>
        </TabsList>
        <TabsContent value="graph">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Smart Graph</CardTitle>
                  <CardDescription>Unit-aware series and overlays (downsampled)</CardDescription>
                </div>
                {(() => {
                  const latest = telemetryData[0] || {};
                  const src = latest.data || latest;
                  let aqi: number | null = null;
                  if (typeof src?.aqi === 'number') aqi = src.aqi;
                  else if (typeof src?.aqi?.value === 'number') aqi = src.aqi.value;
                  else if (typeof src?.air_quality === 'string') {
                    const map: Record<string, number> = { excellent: 25, good: 50, moderate: 100, unhealthy_sensitive: 125, unhealthy: 175, very_unhealthy: 250, hazardous: 400 };
                    aqi = map[src.air_quality] ?? null;
                  }
                  if (aqi == null) return null;
                  const band = aqi <= 50 ? { label: 'Good', cls: 'bg-green-100 text-green-700' } :
                               aqi <= 100 ? { label: 'Moderate', cls: 'bg-yellow-100 text-yellow-700' } :
                               aqi <= 150 ? { label: 'USG', cls: 'bg-orange-100 text-orange-700' } :
                               aqi <= 200 ? { label: 'Unhealthy', cls: 'bg-red-100 text-red-700' } :
                               aqi <= 300 ? { label: 'Very Unhealthy', cls: 'bg-purple-100 text-purple-700' } :
                                            { label: 'Hazardous', cls: 'bg-rose-100 text-rose-700' };
                  return (
                    <Badge className={cn('text-xs px-2 py-1', band.cls)}>
                      AQI {aqi.toFixed(0)} · {band.label}
                    </Badge>
                  );
                })()}
              </div>
            </CardHeader>
            <CardContent>
              {telemetryData.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No telemetry samples available yet. Once the device sends data, graphs will appear automatically.
                </div>
              ) : (
                <SmartGraph schema={effectiveSchema} data={telemetryData} rollups={bands} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="raw">
          <RawDataPanel data={telemetryData} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
