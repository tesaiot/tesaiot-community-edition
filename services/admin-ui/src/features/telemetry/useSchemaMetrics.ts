/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Schema introspection utilities for Smart Graphs
 * Extracts metrics from RJSF JSON Schema following TESA Data Schema Assistant patterns.
 */
import type { RJSFSchema } from '@rjsf/utils';

export type MetricKind = 'scalar' | 'vector' | 'state' | 'boolean';

export interface Metric {
  path: string;         // e.g., "temperature" or "pm2_5.value" or "acceleration.x.value"
  key: string;          // display key without nesting, e.g., "temperature" or "pm2_5"
  label: string;        // human label
  unit?: string;        // best-effort unit string
  kind: MetricKind;
  group?: string;       // for vectors (e.g., "acceleration")
  axis?: 'left' | 'right';
  category?: string;    // optional: environmental, air_quality, electrical, etc.
}

type SchemaProps = Record<string, any>;

function titleCase(id: string): string {
  return id.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

function unitFromProp(prop: any): string | undefined {
  if (!prop) return undefined;
  if (typeof prop.default === 'string') return prop.default;
  if (typeof prop.default === 'number') return String(prop.default);
  if (Array.isArray(prop.enum) && prop.enum.length === 1) return String(prop.enum[0]);
  return undefined;
}

// Try to pair a value key with its *_unit sibling in a flat schema
function findSiblingUnit(key: string, props: SchemaProps): string | undefined {
  const u = props[`${key}_unit`] || props[`${key}Unit`] || props[`${key}Units`];
  return unitFromProp(u);
}

export function introspectSchema(schema?: RJSFSchema): Metric[] {
  if (!schema || typeof schema !== 'object') return [];
  const props: SchemaProps = (schema as any).properties || {};
  const metrics: Metric[] = [];

  // Helper: add scalar metric
  const addScalar = (key: string, unit?: string) => {
    metrics.push({
      path: key,
      key,
      label: titleCase(key),
      unit,
      kind: 'scalar'
    });
  };

  // First/Second pass combined: complex objects
  Object.entries(props).forEach(([k, v]: [string, any]) => {
    if (!(v?.type === 'object' && v.properties)) return;
    const p = v.properties as SchemaProps;

    // A) Vector3 where each axis is an object with {value, unit}
    const isObjVector = ['x', 'y', 'z'].every((c) => p[c]?.type === 'object' && p[c]?.properties?.value);
    if (isObjVector) {
      ['x', 'y', 'z'].forEach((axis) => {
        const unit = unitFromProp(p[axis].properties?.unit);
        metrics.push({ path: `${k}.${axis}.value`, key: `${k}_${axis}`, label: `${titleCase(k)} ${axis.toUpperCase()}`, unit, kind: 'vector', group: k });
      });
      return;
    }

    // B) Canonical single value object {value, unit}
    if (p.value) {
      const unit = unitFromProp(p.unit);
      metrics.push({ path: `${k}.value`, key: k, label: titleCase(k), unit, kind: 'scalar' });
      return;
    }

    // C) Vector/object-of-numbers (e.g., accel:{x:number,y:number,z:number})
    const axes = ['x', 'y', 'z'];
    const isNumVector = axes.every((c) => p[c] && (p[c].type === 'number' || p[c].type === 'integer'));
    if (isNumVector) {
      axes.forEach((axis) => {
        metrics.push({ path: `${k}.${axis}`, key: `${k}_${axis}`, label: `${titleCase(k)} ${axis.toUpperCase()}`, kind: 'vector', group: k });
      });
      return;
    }

    // D) Generic object with numeric leaves -> expose each numeric subkey
    Object.entries(p).forEach(([subKey, subProp]: [string, any]) => {
      if (subProp?.type === 'number' || subProp?.type === 'integer') {
        metrics.push({ path: `${k}.${subKey}`, key: `${k}_${subKey}`, label: `${titleCase(k)} ${titleCase(subKey)}`, kind: 'scalar' });
      }
    });
  });

  // Third pass: flat numeric fields with *_unit pair
  Object.entries(props).forEach(([k, v]: [string, any]) => {
    if (k === 'timestamp') return;
    if (v?.type === 'number' || v?.type === 'integer') {
      const unit = findSiblingUnit(k, props);
      addScalar(k, unit);
    }
  });

  // Fourth pass: states
  Object.entries(props).forEach(([k, v]: [string, any]) => {
    if (v?.type === 'boolean') {
      metrics.push({ path: k, key: k, label: titleCase(k), kind: 'boolean' });
    } else if (Array.isArray(v?.enum)) {
      metrics.push({ path: k, key: k, label: titleCase(k), kind: 'state' });
    }
  });

  // Deduplicate by path
  const seen = new Set<string>();
  const deduped = metrics.filter((m) => {
    if (seen.has(m.path)) return false;
    seen.add(m.path);
    return true;
  });

  // Fallback unit inference when schema lacks explicit units
  function inferUnitByKey(key: string): string | undefined {
    const k = key.toLowerCase();
    if (/(^|_)temp(erature)?(_|$)/.test(k)) return '°C';
    if (/(^|_)humid(ity)?(_|$)/.test(k)) return '%RH';
    if (/(^|_)pressure(_|$)/.test(k)) return 'hPa';
    if (/^accel(_[xyz])?$/.test(k) || /(^|_)accel(eration)?(_|$)/.test(k)) return 'm/s²';
    if (/^gyro(_[xyz])?$/.test(k) || /(^|_)gyro(scope)?(_|$)/.test(k)) return '°/s';
    if (/(^|_)rssi(_|$)/.test(k)) return 'dBm';
    if (/(^|_)battery(_level)?(_|$)/.test(k)) return '%';
    if (/(^|_)voltage(_|$)/.test(k)) return 'V';
    if (/(^|_)current(_|$)/.test(k)) return 'A';
    if (/(^|_)power(_|$)/.test(k)) return 'W';
    if (/(^|_)pm2_5(_|$)/.test(k) || /(^|_)pm10(_|$)/.test(k)) return 'μg/m³';
    if (/(^|_)co2(_|$)/.test(k)) return 'ppm';
    if (/(^|_)step(_count)?(_|$)/.test(k)) return 'steps';
    if (/(^|_)speed(_|$)/.test(k)) return 'm/s';
    if (/(^|_)(altitude|height|distance|range)(_|$)/.test(k)) return 'm';
    if (/(^|_)lux(_|$)|(^|_)light(_|$)/.test(k)) return 'lux';
    if (/(^|_)aqi(_|$)/.test(k)) return 'AQI';
    return undefined;
  }

  deduped.forEach((m) => {
    if (!m.unit) {
      const inferred = inferUnitByKey(m.key) || inferUnitByKey(m.path);
      if (inferred) m.unit = inferred as any;
    }
  });

  return deduped;
}

// Simple unit-based axis assignment (temperature/humidity common on left, different physical unit on right)
export function assignAxes(metrics: Metric[]): Metric[] {
  const byUnit: Record<string, Metric[]> = {};
  metrics.forEach((m) => {
    const u = m.unit || '—';
    byUnit[u] = byUnit[u] || [];
    byUnit[u].push(m);
  });
  const units = Object.keys(byUnit);
  if (units.length <= 1) return metrics.map((m) => ({ ...m, axis: 'left' }));
  const [leftUnit, ...rest] = units;
  const withAxes: Metric[] = [];
  units.forEach((u, idx) => {
    byUnit[u].forEach((m) => withAxes.push({ ...m, axis: idx === 0 ? 'left' : 'right' }));
  });
  return withAxes;
}

// Naive decimation: pick every k-th point to cap size
export function decimate<T>(arr: T[], maxPoints = 300): T[] {
  if (arr.length <= maxPoints) return arr;
  const step = Math.ceil(arr.length / maxPoints);
  const out: T[] = [];
  for (let i = 0; i < arr.length; i += step) out.push(arr[i]);
  return out;
}
