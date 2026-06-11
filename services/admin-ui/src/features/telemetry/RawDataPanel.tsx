/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, {useEffect, useMemo, useRef, useState} from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { formatLocalDateTime } from '@/utils/dateFormatting';
import { Download, Pause, Play, Filter, Copy, Layers } from 'lucide-react';

interface RawDataPanelProps {
  data: Array<any>;
  className?: string;
}

function flattenObject(obj: any, prefix = '', out: Record<string, any> = {}): Record<string, any> {
  if (obj == null) return out;
  Object.entries(obj).forEach(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      flattenObject(v, key, out);
    } else {
      out[key] = v;
    }
  });
  return out;
}

function toCSV(rows: any[]): string {
  if (!rows.length) return '';
  const keys = Array.from(rows.reduce((acc: Set<string>, r: any) => {
    Object.keys(r).forEach(k => acc.add(k));
    return acc;
  }, new Set<string>()));
  const header = keys.join(',');
  const body = rows.map(r => keys.map(k => {
    const val = r[k];
    if (val == null) return '';
    const s = String(val).replace(/"/g, '""');
    return /[",\n]/.test(s) ? `"${s}"` : s;
  }).join(',')).join('\n');
  return `${header}\n${body}`;
}

export function RawDataPanel({ data, className }: RawDataPanelProps) {
  const [filter, setFilter] = useState('');
  const [flatten, setFlatten] = useState(true);
  const [frozen, setFrozen] = useState(false);
  const snapshotRef = useRef<any[]>([]);

  // Maintain a snapshot when frozen
  useEffect(() => {
    if (!frozen) snapshotRef.current = data;
  }, [data, frozen]);

  const working = frozen ? snapshotRef.current : data;

  const filtered = useMemo(() => {
    const src = Array.isArray(working) ? working : [];
    if (!filter.trim()) return src;
    const q = filter.toLowerCase();
    return src.filter((r) => {
      const base = r.data ? { ...r, ...r.data } : r;
      try {
        return JSON.stringify(base).toLowerCase().includes(q);
      } catch {
        return false;
      }
    });
  }, [working, filter]);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'telemetry_raw.json';
    a.click();
  };

  const exportCSV = () => {
    const rows = filtered.map((r) => {
      const base = r.data ? { ...r, ...r.data } : r;
      const flat = flatten ? flattenObject(base) : base;
      return { timestamp: r.timestamp, ...flat };
    });
    const csv = toCSV(rows);
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'telemetry_raw.csv';
    a.click();
  };

  const copyJSON = (obj: any) => {
    navigator.clipboard?.writeText(JSON.stringify(obj, null, 2)).catch(() => {});
  };

  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1">
          <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter (key/value substring)" />
          <Filter className="absolute right-2 top-2.5 h-4 w-4 text-muted-foreground" />
        </div>
        <Button variant="outline" size="sm" onClick={() => setFlatten(v => !v)} title="Toggle flatten">
          <Layers className="h-4 w-4 mr-2" /> {flatten ? 'Flattened' : 'Nested'}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setFrozen(v => !v)} title="Freeze live updates">
          {frozen ? <Play className="h-4 w-4 mr-2" /> : <Pause className="h-4 w-4 mr-2" />} {frozen ? 'Resume' : 'Freeze'}
        </Button>
        <Button variant="outline" size="sm" onClick={exportJSON} title="Export JSON">
          <Download className="h-4 w-4 mr-2" /> JSON
        </Button>
        <Button variant="outline" size="sm" onClick={exportCSV} title="Export CSV">
          <Download className="h-4 w-4 mr-2" /> CSV
        </Button>
      </div>

      <div className="rounded-md border bg-muted/20 max-h-[520px] overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="px-3 py-2 w-[220px]">Time</th>
              <th className="px-3 py-2">Payload</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((rec, idx) => {
              const base = rec.data ? { ...rec, ...rec.data } : rec;
              const flat = flatten ? flattenObject(base) : base;
              // Remove heavy fields for chip view
              delete (flat as any).data;
              return (
                <tr key={`${rec.timestamp}-${idx}`} className="border-t">
                  <td className="px-3 py-2 whitespace-nowrap align-top">
                    <div className="font-mono text-xs">{formatLocalDateTime(rec.timestamp)}</div>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(flat).filter(([k]) => (
                        k !== 'timestamp' && k !== 'device_id' && k !== 'id' && k !== '_id' && k !== 'metadata'
                      )).slice(0, 20).map(([k, v]) => (
                        <Badge key={k} variant="secondary" className="text-xs font-normal">
                          <span className="text-muted-foreground">{k}:</span>&nbsp;{String(v)}
                        </Badge>
                      ))}
                      <Button variant="ghost" size="sm" className="h-6 px-2" onClick={() => copyJSON(rec)} title="Copy JSON">
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-muted-foreground" colSpan={2}>No data</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

