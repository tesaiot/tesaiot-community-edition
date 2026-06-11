/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  AlertTriangle,
  BellRing,
  CalendarClock,
  Cpu,
  Globe,
  Key,
  Lock,
  MemoryStick,
  Radio,
  RefreshCw,
  Shield,
  ShieldCheck,
  Wifi,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { tesaApi } from '@/services/api/tesaApi';
import { InfrastructureMetrics } from './components/InfrastructureMetrics';

type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

type HeroMetricVariant = 'emerald' | 'amber' | 'cyan';

interface HeroMetricContent {
  primary: string;
  tertiary?: string;
  helper?: string;
}

interface HeroMetric extends HeroMetricContent {
  title: string;
  icon: LucideIcon;
  variant: HeroMetricVariant;
}

interface ServiceCard {
  name: string;
  status: ServiceStatus;
  uptime?: string;
  metrics?: {
    cpu?: number;
    memory?: number;
    requests?: number;
    errors?: number;
  };
}

interface AlertItem {
  title: string;
  description?: string;
  severity?: string;
  timestamp?: string;
}

interface CertificateWatchItem {
  device: string;
  expiresAt?: string;
  daysRemaining: number | null;
}

interface SuccessRates {
  apiSuccess: number | null;
  mqttSuccess: number | null;
}

interface ThroughputStats {
  totalDevices: number;
  throughputAvg: number;
  throughputMax: number;
  totalMessages: number;
  apiRequestsPerMin: number;
  mqttPerMin: number;
  httpsPerMin: number;
}

interface TelemetryDailyStats {
  daily: {
    total_messages: number;
    total_devices: number;
    avg_per_hour: number;
    peak_hour: {
      hour: string | null;
      messages: number;
    };
  };
  hourly_breakdown: Array<{
    hour: string;
    timestamp: string | null;
    messages: number;
  }>;
  live: {
    msg_per_min: number;
    active_devices: number;
    window_minutes: number;
  };
  protocol_mix: {
    mqtt: number;
    mqtt_per_day: number;
    https: number;
    https_per_day: number;
    ws: number;
  };
  last_updated: string;
}

const HERO_STYLES: Record<HeroMetricVariant, { gradient: string; iconBg: string; ring: string }> = {
  emerald: {
    gradient: 'from-emerald-500/15 via-emerald-500/5 to-emerald-500/0',
    iconBg: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    ring: 'ring-emerald-500/20',
  },
  amber: {
    gradient: 'from-amber-500/15 via-amber-500/5 to-amber-500/0',
    iconBg: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    ring: 'ring-amber-500/20',
  },
  cyan: {
    gradient: 'from-cyan-500/15 via-cyan-500/5 to-cyan-500/0',
    iconBg: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400',
    ring: 'ring-cyan-500/20',
  },
};

const STATUS_BADGE: Record<ServiceStatus, string> = {
  healthy: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  degraded: 'text-amber-600 bg-amber-50 border-amber-200',
  down: 'text-rose-600 bg-rose-50 border-rose-200',
  unknown: 'text-slate-600 bg-slate-50 border-slate-200',
};

const SEVERITY_BADGE = (severity?: string) => {
  const label = severity?.toLowerCase();
  if (!label) return 'bg-muted text-muted-foreground';
  if (['critical', 'high', 'error'].includes(label)) {
    return 'bg-rose-500/15 text-rose-600 dark:text-rose-300';
  }
  if (['warning', 'medium'].includes(label)) {
    return 'bg-amber-500/15 text-amber-600 dark:text-amber-300';
  }
  if (['info', 'low'].includes(label)) {
    return 'bg-sky-500/15 text-sky-600 dark:text-sky-300';
  }
  return 'bg-muted text-muted-foreground';
};

const formatNumber = (value: number): string => {
  if (!Number.isFinite(value)) return '0';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
};

const safeNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : fallback;
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : fallback;
  }
  return fallback;
};

const toArray = <T,>(value: unknown): T[] => {
  if (Array.isArray(value)) {
    return value as T[];
  }
  if (value && typeof value === 'object' && Array.isArray((value as any).items)) {
    return (value as any).items as T[];
  }
  return [];
};

const normalizeStatus = (value?: string): ServiceStatus => {
  const lowered = value?.toLowerCase();
  if (!lowered) return 'unknown';
  if (['healthy', 'up', 'ok', 'running', 'available', 'connected', 'online'].includes(lowered)) {
    return 'healthy';
  }
  if (['degraded', 'warning', 'partial', 'maintenance'].includes(lowered)) {
    return 'degraded';
  }
  if (['down', 'critical', 'error', 'offline'].includes(lowered)) {
    return 'down';
  }
  return 'unknown';
};

const formatTimestamp = (value?: string): string => {
  if (!value) return 'Timestamp unavailable';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
};

const formatTimeOfDay = (value: string | null): string | null => {
  if (!value) return null;
  try {
    return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (error) {
    return null;
  }
};

const daysUntil = (timestamp?: string): number | null => {
  if (!timestamp) return null;
  const expiry = new Date(timestamp).getTime();
  if (Number.isNaN(expiry)) return null;
  const now = Date.now();
  const diff = Math.round((expiry - now) / (1000 * 60 * 60 * 24));
  return diff;
};

const formatDurationFromSeconds = (value: number): string | null => {
  if (!Number.isFinite(value)) return null;
  const totalSeconds = Math.max(0, Math.floor(value));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const segments: string[] = [];
  if (days) segments.push(`${days}d`);
  if (hours) segments.push(`${hours}h`);
  if (!days && minutes) segments.push(`${minutes}m`);
  if (!days && !hours && !minutes) segments.push(`${seconds || 0}s`);
  if (!segments.length) segments.push('0s');
  return segments.slice(0, 2).join(' ');
};

const formatRelativeTimestamp = (value: unknown): string | undefined => {
  let date: Date | null = null;
  if (value instanceof Date) {
    date = value;
  } else if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return undefined;
    const parsed = Date.parse(trimmed);
    if (!Number.isNaN(parsed)) {
      date = new Date(parsed);
    }
  } else if (typeof value === 'number' && Number.isFinite(value)) {
    if (value > 1e12) {
      date = new Date(value);
    } else if (value > 1e9) {
      date = new Date(value * 1000);
    }
  }

  if (!date || Number.isNaN(date.getTime())) return undefined;
  const diffSeconds = Math.round((Date.now() - date.getTime()) / 1000);
  const absSeconds = Math.abs(diffSeconds);
  const duration = formatDurationFromSeconds(absSeconds);
  if (!duration) return undefined;
  return diffSeconds >= 0 ? `${duration} ago` : `in ${duration}`;
};

const resolveUptimeReadable = (value: unknown): string | undefined => {
  if (value === null || value === undefined) return undefined;

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed || trimmed.toLowerCase() === 'n/a') return undefined;
    const numeric = Number(trimmed);
    if (Number.isFinite(numeric) && numeric >= 0) {
      const duration = formatDurationFromSeconds(numeric > 1e11 ? numeric / 1000 : numeric);
      return duration ?? undefined;
    }
    const relative = formatRelativeTimestamp(trimmed);
    if (relative) return `Last check ${relative}`;
    return trimmed;
  }

  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    const duration = formatDurationFromSeconds(value > 1e11 ? value / 1000 : value);
    return duration ? duration : undefined;
  }

  if (value instanceof Date) {
    const relative = formatRelativeTimestamp(value);
    return relative ? `Last check ${relative}` : undefined;
  }

  if (typeof value === 'object') {
    const secondsCandidate =
      (value as any)?.uptime_seconds ??
      (value as any)?.uptimeSeconds ??
      (value as any)?.seconds ??
      (value as any)?.duration ??
      (value as any)?.value ??
      (value as any)?.total_seconds;
    const stringCandidate =
      (value as any)?.uptime_text ??
      (value as any)?.text ??
      (value as any)?.display ??
      (value as any)?.label;

    const duration = resolveUptimeReadable(secondsCandidate);
    if (duration) return duration;

    if (typeof stringCandidate === 'string') {
      const fromString = resolveUptimeReadable(stringCandidate);
      if (fromString) return fromString;
    }
  }

  return undefined;
};

const formatServiceUptime = (entry: any, systemMetrics: any): string | undefined => {
  if (!entry) return undefined;
  const uptimeSources: unknown[] = [
    entry.uptime,
    entry.uptime_text,
    entry.metrics?.uptime,
    entry.performance?.uptime,
    entry.uptimeSeconds,
    entry.uptime_seconds,
    entry.metrics?.uptime_seconds,
    entry.performance?.uptime_seconds,
    systemMetrics?.uptime,
  ];

  for (const candidate of uptimeSources) {
    const readable = resolveUptimeReadable(candidate);
    if (readable) {
      const normalized = readable.trim();
      if (/^last check/i.test(normalized) || /^uptime/i.test(normalized)) {
        return normalized;
      }
      return `Uptime ${normalized}`;
    }
  }

  const lastCheckSources: unknown[] = [
    entry.last_check,
    entry.lastCheck,
    entry.last_checked,
    entry.lastChecked,
    entry.last_seen,
    entry.lastSeen,
    entry.lastHealthy,
    entry.lastHealthyAt,
    entry.last_healthy,
    entry.last_healthy_at,
    systemMetrics?.last_check,
    systemMetrics?.lastCheck,
  ];

  for (const candidate of lastCheckSources) {
    const relative = formatRelativeTimestamp(candidate);
    if (relative) {
      return `Last check ${relative}`;
    }
  }

  return undefined;
};

const TelemetrySparkline: React.FC<{ values: number[]; loading: boolean }> = ({ values, loading }) => {
  if (loading) {
    return <Skeleton className="h-32 w-full" />;
  }

  if (!values.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-md border border-dashed border-muted-foreground/30 text-sm text-muted-foreground">
        Awaiting telemetry trend data
      </div>
    );
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const spread = max - min || 1;
  const path = values
    .map((point, index) => {
      const x = values.length === 1 ? 100 : (index / (values.length - 1)) * 100;
      const y = 100 - ((point - min) / spread) * 100;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <svg viewBox="0 0 100 100" className="h-32 w-full overflow-visible text-primary">
      <defs>
        <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.4" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L 100,100 L 0,100 Z`} fill="url(#spark-fill)" stroke="none" opacity={0.6} />
      <path
        d={path}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

interface HeroMetricCardProps extends HeroMetric {}

const HeroMetricCard: React.FC<HeroMetricCardProps & { loading: boolean }> = ({
  title,
  primary,
  tertiary,
  helper,
  icon: Icon,
  variant,
  loading,
}) => {
  const styles = HERO_STYLES[variant];

  return (
    <Card className={cn('relative overflow-hidden border border-border/60 transition-opacity', loading && 'opacity-70')}>
      <div className={cn('absolute inset-0 bg-gradient-to-br', styles.gradient)} aria-hidden="true" />
      <CardContent className="relative flex flex-col gap-4 p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <h3 className="text-3xl font-semibold tracking-tight text-foreground">
              {loading ? <Skeleton className="h-8 w-24" /> : primary}
            </h3>
          </div>
          <div className={cn('rounded-full p-3 ring-1', styles.iconBg, styles.ring)}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          {loading ? (
            <Skeleton className="h-4 w-32" />
          ) : (
            tertiary && <span className="font-medium text-foreground/80">{tertiary}</span>
          )}
          {loading ? <Skeleton className="h-4 w-40" /> : helper && <p>{helper}</p>}
        </div>
      </CardContent>
    </Card>
  );
};

const SERVICE_ALIAS: Record<string, string> = {
  'Api Gateway': 'API Gateway',
  'Tesa Caches': 'TESAIoT Caches',
  'Tesaiot Caches': 'TESAIoT Caches',
  'Redis Cache': 'TESAIoT Caches',
  'Telemetry': 'Telemetry Ingest',
  'Telemetry Ingest': 'Telemetry Ingest',
  'Mqtt Broker': 'MQTTS Broker',
  'Mqtts Broker': 'MQTTS Broker',
  'Monitoring': 'Monitoring',
  'Pki Server': 'PKI Server',
  'Vault Pki': 'PKI Server',
  'Databases': 'Databases',
  'MongoDB': 'Databases',
  'Timescaledb': 'TimescaleDB',
  'TimescaleDB': 'TimescaleDB',
};

const SystemHealthCard: React.FC<ServiceCard> = ({ name, status, uptime, metrics }) => (
  <Card className="border-border">
    <CardHeader className="pb-3">
      <CardTitle className="flex flex-wrap items-center justify-between gap-3 text-base">
        <span>{name}</span>
        <span className={cn('ml-2 flex-shrink-0 rounded-full border px-3 py-1 text-xs', STATUS_BADGE[status])}>
          {status === 'healthy' ? 'Healthy' : status === 'degraded' ? 'Degraded' : status === 'down' ? 'Down' : 'Unknown'}
        </span>
      </CardTitle>
      <CardDescription>{uptime ?? 'Uptime data unavailable'}</CardDescription>
    </CardHeader>
    {metrics && (
      <CardContent className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        {metrics.cpu !== undefined && (
          <div className="flex items-center gap-1">
            <Cpu className="h-3 w-3" /> CPU {metrics.cpu.toFixed(1)}%
          </div>
        )}
        {metrics.memory !== undefined && (
          <div className="flex items-center gap-1">
            <MemoryStick className="h-3 w-3" /> Mem {metrics.memory.toFixed(1)}%
          </div>
        )}
        {metrics.requests !== undefined && (
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" /> Req {metrics.requests}
          </div>
        )}
        {metrics.errors !== undefined && (
          <div className="flex items-center gap-1 text-rose-500">
            <AlertTriangle className="h-3 w-3" /> Err {metrics.errors}
          </div>
        )}
      </CardContent>
    )}
  </Card>
);

const OperationalDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [throughputStats, setThroughputStats] = useState<ThroughputStats>({
    totalDevices: 0,
    throughputAvg: 0,
    throughputMax: 0,
    totalMessages: 0,
    apiRequestsPerMin: 0,
    mqttPerMin: 0,
    httpsPerMin: 0,
  });
  const [serviceCards, setServiceCards] = useState<ServiceCard[]>([]);
  const [hasDetailedServiceData, setHasDetailedServiceData] = useState(false);
  const [heroMetrics, setHeroMetrics] = useState<{
    platformHealth: HeroMetricContent;
    activeAlerts: HeroMetricContent;
    secureDevices: HeroMetricContent;
  }>({
    platformHealth: {
      primary: '--',
      tertiary: 'Awaiting data',
      helper: 'Monitoring critical services',
    },
    activeAlerts: {
      primary: '0',
      tertiary: 'All clear',
      helper: 'No active alerts detected',
    },
    secureDevices: {
      primary: '--',
      tertiary: 'Awaiting sync',
      helper: 'Valid certificates data not available',
    },
  });
  const [protocolMix, setProtocolMix] = useState({ mqtt: 0, https: 0, ws: 0 });
  const [telemetryTrend, setTelemetryTrend] = useState<number[]>([]);
  const [telemetryDailyStats, setTelemetryDailyStats] = useState<TelemetryDailyStats | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertItem[]>([]);
  const [certificateWatchlist, setCertificateWatchlist] = useState<CertificateWatchItem[]>([]);
  const [successRates, setSuccessRates] = useState<SuccessRates>({ apiSuccess: null, mqttSuccess: null });
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [securityScore, setSecurityScore] = useState<number | null>(null);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const detailedLoadInFlight = useRef(false);

  const { user } = useAuth();
  const isPlatformAdmin = user?.role === 'platform_admin';

  const loadDetailedSystemHealth = useCallback(async () => {
    if (detailedLoadInFlight.current) return;
    detailedLoadInFlight.current = true;

    try {
      const detail = await tesaApi.getRealtimeSystemHealthDetailed().catch(() => null);
      if (!detail) return;

      const detailedServices = toArray<any>(detail.services ?? []);
      const detailedCards: ServiceCard[] = detailedServices
        .map((service) => {
          const displayName = (service.display_name || service.name || service.key || '').trim() || 'Service';
          const status = normalizeStatus(service.status);
          const metricsRaw = service.metrics ?? {};
          const cpuValue = safeNumber(metricsRaw.cpu, NaN);
          const memoryValue = safeNumber(metricsRaw.memory, NaN);
          const requestsValue = metricsRaw.requests !== undefined ? safeNumber(metricsRaw.requests, NaN) : undefined;
          const errorsValue = metricsRaw.errors !== undefined ? safeNumber(metricsRaw.errors, NaN) : undefined;
          const hasMetrics = [cpuValue, memoryValue, requestsValue, errorsValue].some((value) =>
            Number.isFinite(value ?? NaN),
          );

          return {
            name: displayName,
            status,
            uptime: service.uptime ?? service.uptime_label ?? service.last_check ?? undefined,
            metrics: hasMetrics
              ? {
                  cpu: Number.isFinite(cpuValue) ? cpuValue : undefined,
                  memory: Number.isFinite(memoryValue) ? memoryValue : undefined,
                  requests: Number.isFinite(requestsValue ?? NaN) ? requestsValue : undefined,
                  errors: Number.isFinite(errorsValue ?? NaN) ? errorsValue : undefined,
                }
              : undefined,
          } satisfies ServiceCard;
        })
        .filter((card) => card.name);

      if (detailedCards.length) {
        setServiceCards((previous) => {
          const cardsMap = new Map(previous.map((card) => [card.name, card]));
          detailedCards.forEach((card) => cardsMap.set(card.name, card));
          return Array.from(cardsMap.values()).slice(0, 6);
        });
        setHasDetailedServiceData(true);
      }

      const statusCounts = detailedCards.reduce(
        (acc, card) => {
          acc[card.status] = (acc[card.status] ?? 0) + 1;
          return acc;
        },
        { healthy: 0, degraded: 0, down: 0, unknown: 0 } as Record<ServiceStatus, number>,
      );
      const totalServices = detailedCards.length;
      const healthyCount = statusCounts.healthy ?? 0;
      const degradedCount = statusCounts.degraded ?? 0;
      const downCount = statusCounts.down ?? 0;
      const serviceHealthPercentRaw = totalServices
        ? (healthyCount / totalServices) * 100
        : NaN;

      const detailSuccessRateRaw = safeNumber(
        detail.success_rate ??
          detail.platform_health_score ??
          detail.successRate ??
          detail.metrics?.success_rate ??
          NaN,
        NaN,
      );

      const metricsSource = detail.system_metrics ?? {};
      const cpuMetric = safeNumber(
        metricsSource.avg_cpu_usage ?? metricsSource.cpu_usage ?? metricsSource.total_cpu_usage ?? NaN,
        NaN,
      );
      const memoryMetric = safeNumber(
        metricsSource.avg_memory_usage ?? metricsSource.memory_usage ?? metricsSource.total_memory_usage ?? NaN,
        NaN,
      );
      const helperText = Number.isFinite(cpuMetric) || Number.isFinite(memoryMetric)
        ? [
            Number.isFinite(cpuMetric) ? `CPU ${Math.round(cpuMetric)}%` : null,
            Number.isFinite(memoryMetric) ? `MEM ${Math.round(memoryMetric)}%` : null,
          ]
            .filter(Boolean)
            .join(' • ')
        : undefined;

      const normalizedOverallStatus: ServiceStatus = downCount
        ? 'down'
        : degradedCount
          ? 'degraded'
          : healthyCount
            ? 'healthy'
            : 'unknown';

      const serviceHealthPercent = Number.isFinite(serviceHealthPercentRaw)
        ? Math.round(serviceHealthPercentRaw)
        : NaN;
      const detailSuccessPercent = Number.isFinite(detailSuccessRateRaw)
        ? Math.round(detailSuccessRateRaw)
        : NaN;

      const blendedPercent = Number.isFinite(serviceHealthPercent)
        ? Number.isFinite(detailSuccessPercent)
          ? Math.min(detailSuccessPercent, serviceHealthPercent)
          : serviceHealthPercent
        : detailSuccessPercent;

      setHeroMetrics((prev) => {
        const primary = Number.isFinite(blendedPercent)
          ? `${Math.round(blendedPercent)}%`
          : normalizedOverallStatus === 'healthy'
            ? 'Healthy'
            : normalizedOverallStatus === 'degraded'
              ? 'Degraded'
              : normalizedOverallStatus === 'down'
                ? 'Down'
                : prev.platformHealth.primary;

        return {
          ...prev,
          platformHealth: {
            primary,
            tertiary: totalServices
              ? `${healthyCount}/${totalServices} services healthy`
              : prev.platformHealth.tertiary,
            helper: helperText ?? prev.platformHealth.helper,
          },
        };
      });

      const endpointMetrics = toArray<any>(detail.endpoints ?? detail.endpoint_metrics ?? []);
      const findSuccessRate = (matcher: (value: string) => boolean) => {
        const target = endpointMetrics.find((endpoint) => {
          const name = (endpoint.endpoint ?? endpoint.name ?? '').toString().toLowerCase();
          return matcher(name);
        });
        return safeNumber(
          target?.success_rate ??
            target?.successRate ??
            target?.delivery_success_rate ??
            target?.success ??
            NaN,
          NaN,
        );
      };

      const apiSuccess = findSuccessRate((name) => name.includes('api') || name.includes('metrics'));
      const mqttSuccess = findSuccessRate((name) => name.includes('mqtt'));

      setSuccessRates((prev) => ({
        apiSuccess: Number.isFinite(apiSuccess) ? Math.round(apiSuccess) : prev.apiSuccess,
        mqttSuccess: Number.isFinite(mqttSuccess) ? Math.round(mqttSuccess) : prev.mqttSuccess,
      }));
    } catch (error) {
      console.warn('Failed to load detailed system health', error);
    } finally {
      detailedLoadInFlight.current = false;
    }
  }, [setHeroMetrics]);

  const refreshDashboard = useCallback(async () => {
    try {
      setLoading(true);

      const analyticsPromise = isPlatformAdmin
        ? tesaApi.getPlatformAdminAnalytics().catch(() => ({}))
        : Promise.resolve({});

      // Add security analytics call for Security Posture panel
      const securityAnalyticsPromise = tesaApi.getFast('/api/v1/dashboard/realtime/security-analytics?time_range=24h')
        .catch(() => ({}));

      // Add telemetry daily stats call for improved Telemetry Throughput panel
      const telemetryDailyPromise = tesaApi.getFast('/api/v1/dashboard/realtime/telemetry-daily')
        .catch(() => null);

      const [statsRes, iotResRaw, apiResRaw, systemResRaw, analyticsRes, securityAnalyticsRes, telemetryDailyRes] = await Promise.all([
        tesaApi.getFast('/api/v1/dashboard/stats').catch(() => ({})),
        tesaApi.getFast('/api/v1/dashboard/realtime/iot-metrics').catch(() => ({})),
        tesaApi.getFast('/api/v1/dashboard/realtime/api-gateway').catch(() => ({})),
        (isPlatformAdmin
          ? tesaApi.getRealtimeSystemHealth()
          : tesaApi.getFast('/api/v1/dashboard/system/health')
        ).catch(() => null),
        analyticsPromise,
        securityAnalyticsPromise,
        telemetryDailyPromise,
      ]);

      const iotMetrics = (iotResRaw?.iot_metrics ?? iotResRaw) as any;
      const apiMetrics = apiResRaw as any;
      const systemMetrics = systemResRaw as any;

      const totalDevicesReported = safeNumber(
        (statsRes as any)?.totalDevicesAllOrgs ??
          (statsRes as any)?.totalDevices ??
          (statsRes as any)?.total ??
          0,
      );
      const activeDevicesReported = safeNumber(
        (statsRes as any)?.activeDevices ?? (statsRes as any)?.active_devices ?? 0,
      );
      const activeDevicesTelemetry = safeNumber(
        iotMetrics?.active_devices ?? iotMetrics?.activeDevices ?? 0,
      );
      const totalDevices = totalDevicesReported || activeDevicesReported || activeDevicesTelemetry;

      const throughputAvg = safeNumber(
        iotMetrics?.throughput_avg ??
          iotMetrics?.messages_per_minute ??
          iotMetrics?.throughput?.avg ??
          iotMetrics?.ingest_rate?.per_minute ??
          0,
      );
      const throughputMax = safeNumber(
        iotMetrics?.throughput_max ?? iotMetrics?.throughput?.max ?? throughputAvg,
      );
      const totalMessages = safeNumber(
        iotMetrics?.total_messages ??
          iotMetrics?.message_count?.last_hour ??
          iotMetrics?.message_count ??
          0,
      );
      const apiRequestsPerMin = safeNumber(
        apiMetrics?.requests_per_minute ??
          apiMetrics?.requests_per_min ??
          apiMetrics?.request_rate ??
          apiMetrics?.summary?.requests_per_minute ??
          0,
      );

      const protocolSource =
        iotMetrics?.protocol_mix ??
        iotMetrics?.transport_breakdown ??
        {};
      const mix = {
        mqtt: safeNumber(
          protocolSource?.mqtt_per_minute ??
            protocolSource?.mqtt ??
            protocolSource?.mqtts ??
            protocolSource?.mtls ??
            0,
        ),
        https: safeNumber(
          protocolSource?.https_per_minute ??
            protocolSource?.https ??
            protocolSource?.http ??
            0,
        ),
        ws: safeNumber(
          protocolSource?.ws_per_minute ??
            protocolSource?.ws ??
            protocolSource?.websocket ??
            protocolSource?.websockets ??
            0,
        ),
      };
      const mixTotal = mix.mqtt + mix.https + mix.ws;
      const mqttPerMin = mix.mqtt || (mixTotal > 0 ? Math.round((mix.mqtt / mixTotal) * throughputAvg) : 0);
      const httpsPerMin = mix.https || (mixTotal > 0 ? Math.round((mix.https / mixTotal) * throughputAvg) : 0);

      setThroughputStats({
        totalDevices,
        throughputAvg,
        throughputMax,
        totalMessages,
        apiRequestsPerMin,
        mqttPerMin,
        httpsPerMin,
      });
      setProtocolMix(mix);

      // Set telemetry daily stats if available
      if (telemetryDailyRes && telemetryDailyRes.success !== false) {
        setTelemetryDailyStats(telemetryDailyRes as TelemetryDailyStats);
      }

      const serviceAlias: Record<string, string> = {
        api: 'API Gateway',
        gateway: 'API Gateway',
        cache: 'TESAIoT Caches',
        redis: 'TESAIoT Caches',
        database: 'Databases',
        mongodb: 'Databases',
        telemetry: 'Telemetry Ingest',
        vault: 'PKI Server',
      };

      const rawServices = (() => {
        const collection = systemMetrics?.services ?? systemMetrics?.data;
        if (Array.isArray(collection)) {
          return collection;
        }
        if (collection && typeof collection === 'object') {
          return Object.entries(collection).map(([key, value]) =>
            value && typeof value === 'object' ? { key, ...value } : { key, status: value },
          );
        }
        return [];
      })();

      const services = rawServices
        .map((entry: any) => {
          const key = entry.key || entry.name || entry.service || 'Service';
          const keyLower = key?.toLowerCase?.() ?? key;
          const rawName = (entry.name || entry.service || serviceAlias[keyLower] || key)
            .toString()
            .replace(/[_-]/g, ' ')
            .replace(/\b\w/g, (token) => token.toUpperCase());
          const name = SERVICE_ALIAS[rawName] ?? rawName;
          const metricSource = entry.metrics || entry.performance;
          const uptimeLabel = formatServiceUptime(entry, systemMetrics);
          const metricSet = metricSource && typeof metricSource === 'object'
            ? {
                cpu: metricSource.cpu !== undefined ? safeNumber(metricSource.cpu, NaN) : undefined,
                memory: metricSource.memory !== undefined ? safeNumber(metricSource.memory, NaN) : undefined,
                requests:
                  metricSource.requests !== undefined
                    ? safeNumber(metricSource.requests)
                    : metricSource.connections !== undefined
                      ? safeNumber(metricSource.connections)
                      : undefined,
                errors: metricSource.errors !== undefined ? safeNumber(metricSource.errors) : undefined,
              }
            : undefined;
          const normalizedMetrics =
            metricSet &&
            Object.values(metricSet).some((value) => typeof value === 'number' && Number.isFinite(value))
              ? metricSet
              : undefined;

          return {
            name,
            status: normalizeStatus(
              entry.status ?? entry.state ?? entry.health ?? (typeof entry === 'string' ? entry : undefined),
            ),
            uptime: uptimeLabel,
          metrics: normalizedMetrics,
        } satisfies ServiceCard;
        })
        .filter(Boolean)
        .reduce<ServiceCard[]>((acc, card) => {
          if (!acc.find((existing) => existing.name === card.name)) {
            acc.push(card);
          }
          return acc;
        }, []);

      const timescale = systemMetrics?.databases?.timescaledb ?? iotMetrics?.databases?.timescaledb;
      if (timescale && typeof timescale === 'object') {
        services.push({
          name: 'TIMESCALEDB',
          status: normalizeStatus(timescale.status || timescale.state),
          uptime: formatServiceUptime(timescale, systemMetrics),
          metrics: {
            cpu: safeNumber(timescale.cpu, NaN),
            memory: safeNumber(timescale.memory, NaN),
            requests: safeNumber(timescale.connections ?? timescale.queries_per_minute ?? 0),
            errors: safeNumber(timescale.errors, NaN),
          },
        });
      }

      if (!services.length) {
        services.push(
          { name: 'API Gateway', status: 'unknown' },
          { name: 'TESAIoT Caches', status: 'unknown' },
          { name: 'Telemetry Ingest', status: 'unknown' },
          { name: 'MQTTS Broker', status: 'unknown' },
          { name: 'Monitoring', status: 'unknown' },
          { name: 'PKI Server', status: 'unknown' },
          { name: 'Databases', status: 'unknown' },
          { name: 'TimescaleDB', status: 'unknown' },
        );
      }

      if (!hasDetailedServiceData) {
        setServiceCards((previous) => {
          const meaningfulFast = services.some((card) => card.status !== 'unknown');
          if (!meaningfulFast && previous.length) {
            return previous;
          }
          return services.slice(0, 6);
        });
      }

      const trendCandidates = [
        iotMetrics?.throughput_trend,
        iotMetrics?.trend?.messages_per_minute,
        iotMetrics?.trend?.ingest_per_minute,
        iotMetrics?.history?.messages_per_minute,
        iotMetrics?.messages_per_minute,
      ];
      const telemetrySamples = (trendCandidates.find((value) => Array.isArray(value) && value.length) ?? [])
        .map((sample: any) => {
          if (typeof sample === 'number') return sample;
          if (sample && typeof sample === 'object') {
            if (typeof sample.rate === 'number') return sample.rate * 60;
            if (typeof sample.messages === 'number') return sample.messages;
          }
          const numeric = Number(sample);
          return Number.isFinite(numeric) ? numeric : 0;
        })
        .filter((value: number) => Number.isFinite(value));
      setTelemetryTrend(telemetrySamples);

      const incidentsRaw = toArray<any>(
        analyticsRes?.recent_issues ??
          analyticsRes?.recent_incidents ??
          analyticsRes?.alerts?.recent ??
          analyticsRes?.recentAlerts ??
          analyticsRes?.recent_incidents ??
          iotMetrics?.recent_alerts ??
          [],
      );
      const incidents: AlertItem[] = incidentsRaw.slice(0, 5).map((item) => {
        const metadata = item.metadata ?? {};
        return {
          title:
            item.title ||
            item.name ||
            item.alert ||
            item.summary ||
            item.source ||
            item.message ||
            'Alert',
          description: item.description || item.detail || item.message || metadata.description,
          severity: item.severity || item.level || item.priority || item.status,
          timestamp: item.timestamp || item.occurred_at || item.created_at || item.createdAt,
        };
      });
      setRecentAlerts(incidents);

      const certificateRaw = toArray<any>(
        analyticsRes?.certificate_watchlist ??
          analyticsRes?.certificates?.watchlist ??
          analyticsRes?.certificates?.expiring ??
          analyticsRes?.certificates?.upcoming_expiry ??
          analyticsRes?.certificateExpiring ??
          analyticsRes?.expiringCertificates ??
          [],
      );
      const certificates: CertificateWatchItem[] = certificateRaw.slice(0, 5).map((item) => {
        const daysValue = safeNumber(
          item.days_remaining ??
            item.daysRemaining ??
            item.renew_in_days ??
            item.certificate_days_left ??
            item.expires_in_days ??
            NaN,
          NaN,
        );
        const daysRemaining = Number.isFinite(daysValue) ? Math.round(daysValue) : daysUntil(item.expires_at ?? item.expiry);
        return {
          device: item.device || item.name || item.common_name || item.subject || 'Device',
          expiresAt: item.expires_at || item.expiry || item.not_after || item.expirationDate,
          daysRemaining,
        };
      });
      setCertificateWatchlist(certificates);

      const statusCounts = services.reduce<Record<ServiceStatus, number>>((acc, service) => {
        acc[service.status] = (acc[service.status] ?? 0) + 1;
        return acc;
      }, { healthy: 0, degraded: 0, down: 0, unknown: 0 });

      const telemetryService =
        systemMetrics?.services?.telemetry ??
        analyticsRes?.services?.telemetry ??
        analyticsRes?.services?.ingest;

      const overallHealthSource =
        systemMetrics?.system_metrics?.overall_health ??
        telemetryService?.status ??
        telemetryService?.state ??
        telemetryService?.health ??
        (statusCounts.down
          ? 'down'
          : statusCounts.degraded
            ? 'degraded'
            : statusCounts.healthy
              ? 'healthy'
              : 'unknown');

      const normalizedHealth = normalizeStatus(overallHealthSource);
      const platformScoreRaw = safeNumber(
        systemMetrics?.services?.telemetry?.health_score ??
          analyticsRes?.platform_health?.score ??
          analyticsRes?.infrastructure_metrics?.platformHealthScore ??
          analyticsRes?.infrastructure_metrics?.overall_health_score ??
          iotMetrics?.success_rate,
        NaN,
      );
      const platformScore = Number.isFinite(platformScoreRaw) && platformScoreRaw > 0
        ? Math.round(platformScoreRaw)
        : null;
      const healthTertiary = services.length
        ? `${statusCounts.healthy ?? 0}/${services.length} services healthy`
        : 'Awaiting data';

      const avgCpu = safeNumber(
        systemMetrics?.system_metrics?.avg_cpu_usage ??
          analyticsRes?.resource_utilization?.avg_cpu ??
          NaN,
        NaN,
      );
      const avgMemory = safeNumber(
        systemMetrics?.system_metrics?.avg_memory_usage ??
          analyticsRes?.resource_utilization?.avg_memory ??
          NaN,
        NaN,
      );
      const healthHelper =
        Number.isFinite(avgCpu) && Number.isFinite(avgMemory)
          ? `CPU ${Math.round(avgCpu)}% • MEM ${Math.round(avgMemory)}%`
          : activeDevicesTelemetry && totalDevices
            ? `Active devices (1h): ${activeDevicesTelemetry}/${totalDevices}`
            : 'Monitoring critical services';

      const alertCounts = incidents.reduce(
        (acc, alert) => {
          const severity = (alert.severity ?? '').toLowerCase();
          if (['critical', 'high', 'error'].includes(severity)) acc.critical += 1;
          else if (['warning', 'medium'].includes(severity)) acc.warning += 1;
          else acc.info += 1;
          return acc;
        },
        { critical: 0, warning: 0, info: 0 },
      );
      const activeAlertCount = incidents.length;
      const mostRecentAlert = incidents[0]?.timestamp ?? null;
      const alertSummary = activeAlertCount
        ? `${alertCounts.critical} critical • ${alertCounts.warning} warning`
        : 'All clear';
      const alertHelper = activeAlertCount
        ? `Latest update ${mostRecentAlert ? formatTimestamp(mostRecentAlert) : 'just now'}`
        : 'No active alerts detected';

      const secureDevicesSource =
        analyticsRes?.secure_devices ??
        analyticsRes?.secureDevices ??
        iotMetrics?.secure_devices ??
        iotMetrics?.secureDevices ??
        null;
      let secureDevicesCount = 0;
      let recentRenewals = 0;
      if (Array.isArray(secureDevicesSource)) {
        secureDevicesCount = secureDevicesSource.length;
      } else if (typeof secureDevicesSource === 'number') {
        secureDevicesCount = secureDevicesSource;
      } else if (secureDevicesSource && typeof secureDevicesSource === 'object') {
        secureDevicesCount = safeNumber(
          secureDevicesSource.total ??
            secureDevicesSource.count ??
            secureDevicesSource.secure ??
            secureDevicesSource.devices ??
            secureDevicesSource.valid ??
            0,
        );
        recentRenewals = safeNumber(
          secureDevicesSource.recently_renewed ??
            secureDevicesSource.renewals_last_7d ??
            secureDevicesSource.renewals_last_30d ??
            0,
        );
      }
      if (!secureDevicesCount && incidentsRaw.length) {
        secureDevicesCount = incidentsRaw.filter((item) => {
          const status = String(
            item.certificate_status ?? item.security_state ?? '',
          ).toLowerCase();
          return ['valid', 'active', 'secure'].includes(status);
        }).length;
      }

      const secureDevicesPrimary = secureDevicesCount ? String(secureDevicesCount) : totalDevices ? '0' : '--';
      const secureDevicesTertiary = secureDevicesCount
        ? `${secureDevicesCount} devices with valid certificates`
        : totalDevices
          ? `${totalDevices} devices awaiting certificate sync`
          : 'Awaiting sync';
      const secureDevicesHelper = secureDevicesCount
        ? recentRenewals > 0
          ? `${recentRenewals} renewals in last 7 days`
          : 'Vault issued certificates up to date'
        : totalDevices
          ? 'Sync with Vault to validate enrolled devices'
          : 'Valid certificates data not available';

      const meaningfulFastTotal = (statusCounts.healthy ?? 0) + (statusCounts.degraded ?? 0) + (statusCounts.down ?? 0);
      const meaningfulFastStatus = meaningfulFastTotal > 0;
      const serviceHealthPercent = meaningfulFastStatus
        ? Math.round(((statusCounts.healthy ?? 0) / meaningfulFastTotal) * 100)
        : null;

      setHeroMetrics((prev) => {
        const next: typeof prev = {
          platformHealth: prev.platformHealth,
          activeAlerts: { primary: String(activeAlertCount ?? 0), tertiary: alertSummary, helper: alertHelper },
          secureDevices: { primary: secureDevicesPrimary, tertiary: secureDevicesTertiary, helper: secureDevicesHelper },
        };

        if (!hasDetailedServiceData && (meaningfulFastStatus || platformScore !== null || Number.isFinite(avgCpu) || Number.isFinite(avgMemory))) {
          next.platformHealth = {
            primary:
              platformScore !== null
                ? `${platformScore}%`
                : serviceHealthPercent !== null
                  ? `${serviceHealthPercent}%`
                  : meaningfulFastStatus
                    ? normalizedHealth === 'healthy'
                      ? 'Healthy'
                      : normalizedHealth === 'degraded'
                        ? 'Degraded'
                        : normalizedHealth === 'down'
                          ? 'Down'
                          : prev.platformHealth.primary
                    : prev.platformHealth.primary,
            tertiary: meaningfulFastStatus ? healthTertiary : prev.platformHealth.tertiary,
            helper: healthHelper,
          };
        }

        return next;
      });

      // Use security analytics response for accurate security score
      const securityData = securityAnalyticsRes as any;
      const defenseScore = safeNumber(
        securityData?.defense_in_depth?.overall_score ??
          securityData?.security_score ??
          analyticsRes?.defense_in_depth?.overall_score ??
          analyticsRes?.security?.overall_score ??
          analyticsRes?.security?.score ??
          analyticsRes?.security_score ??
          analyticsRes?.security?.security_score ??
          NaN,
        NaN,
      );
      setSecurityScore(Number.isFinite(defenseScore) ? Math.round(defenseScore) : null);

      // Extract security alerts from security analytics response
      const securityAlerts = toArray<any>(securityData?.alerts ?? []);
      if (securityAlerts.length > 0) {
        const mappedSecurityAlerts: AlertItem[] = securityAlerts.slice(0, 5).map((alert) => ({
          title: alert.title || alert.message || alert.type || 'Security Alert',
          description: alert.description || alert.details || '',
          severity: alert.severity || alert.level || 'warning',
          timestamp: alert.timestamp || alert.created_at || new Date().toISOString(),
        }));
        // Merge with existing alerts, security alerts first
        setRecentAlerts((prev) => {
          const combined = [...mappedSecurityAlerts, ...prev.filter(a =>
            !mappedSecurityAlerts.some(sa => sa.title === a.title)
          )];
          return combined.slice(0, 5);
        });
      }

      // Extract certificate watchlist from security analytics if available
      const certWarnings = toArray<any>(securityData?.certificate_warnings ?? []);
      if (certWarnings.length > 0) {
        const mappedCertWatchlist: CertificateWatchItem[] = certWarnings.slice(0, 5).map((cert) => ({
          device: cert.device_id || cert.device || cert.common_name || 'Unknown Device',
          expiresAt: cert.expires_at || cert.not_after || cert.expiry_date || null,
          daysRemaining: cert.days_remaining ?? cert.days_until_expiry ?? null,
        }));
        setCertificateWatchlist(mappedCertWatchlist);
      }

      const apiSuccessRate = safeNumber(
        apiMetrics?.success_rate ??
          apiMetrics?.successRate ??
          apiMetrics?.uptime_percent ??
          apiMetrics?.summary?.success_rate ??
          NaN,
        NaN,
      );
      const mqttSuccessRate = safeNumber(
        iotMetrics?.delivery?.mqtt?.success_rate ??
          iotMetrics?.delivery?.mqtt?.successRate ??
          iotMetrics?.mqtt_success_rate ??
          iotMetrics?.success_rate ??
          NaN,
        NaN,
      );
      setSuccessRates((prev) => ({
        apiSuccess:
          Number.isFinite(apiSuccessRate) && (!hasDetailedServiceData || apiSuccessRate > 0 || prev.apiSuccess === null)
            ? Math.round(apiSuccessRate)
            : prev.apiSuccess,
        mqttSuccess:
          Number.isFinite(mqttSuccessRate) && (!hasDetailedServiceData || mqttSuccessRate > 0 || prev.mqttSuccess === null)
            ? Math.round(mqttSuccessRate)
            : prev.mqttSuccess,
      }));

      setLastUpdated(new Date().toISOString());
      setMaintenanceMode(false);
      void loadDetailedSystemHealth();
    } catch (error) {
      console.warn('Operational dashboard fallback:', error);
      setServiceCards([]);
      setTelemetryTrend([]);
      setProtocolMix({ mqtt: 0, https: 0, ws: 0 });
      setRecentAlerts([]);
      setCertificateWatchlist([]);
      setHeroMetrics({
        platformHealth: {
          primary: '--',
          tertiary: 'Unavailable',
          helper: 'Service telemetry not reachable',
        },
        activeAlerts: {
          primary: '0',
          tertiary: 'All clear',
          helper: 'Alert data unavailable',
        },
        secureDevices: {
          primary: '--',
          tertiary: 'Unavailable',
          helper: 'Device inventory not reachable',
        },
      });
      setSecurityScore(null);
      setSuccessRates({ apiSuccess: null, mqttSuccess: null });
      setMaintenanceMode(true);
    } finally {
      setLoading(false);
    }
  }, [isPlatformAdmin, loadDetailedSystemHealth]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const throughputSummary = useMemo(() => {
    if (!telemetryTrend.length) {
      return { avg: 0, max: 0, min: 0 };
    }
    const avg = telemetryTrend.reduce((sum, value) => sum + value, 0) / telemetryTrend.length;
    const max = Math.max(...telemetryTrend);
    const min = Math.min(...telemetryTrend);
    return { avg, max, min };
  }, [telemetryTrend]);

  const heroCards: HeroMetric[] = useMemo(
    () => [
      {
        title: 'Platform Health Score',
        primary: heroMetrics.platformHealth.primary,
        tertiary: heroMetrics.platformHealth.tertiary,
        helper: heroMetrics.platformHealth.helper,
        icon: ShieldCheck,
        variant: 'emerald',
      },
      {
        title: 'Active Alerts',
        primary: heroMetrics.activeAlerts.primary,
        tertiary: heroMetrics.activeAlerts.tertiary,
        helper: heroMetrics.activeAlerts.helper,
        icon: BellRing,
        variant: 'amber',
      },
      {
        title: 'Secure Devices',
        primary: heroMetrics.secureDevices.primary,
        tertiary: heroMetrics.secureDevices.tertiary,
        helper: heroMetrics.secureDevices.helper,
        icon: Lock,
        variant: 'cyan',
      },
    ],
    [heroMetrics],
  );

  const lastUpdatedDisplay = useMemo(() => formatTimeOfDay(lastUpdated), [lastUpdated]);

  const protocolBreakdown = useMemo(() => {
    // Use daily stats if available, otherwise fall back to real-time protocolMix
    const dailyMix = telemetryDailyStats?.protocol_mix;
    const mqtt = dailyMix?.mqtt ?? protocolMix.mqtt;
    const https = dailyMix?.https ?? protocolMix.https;
    const ws = dailyMix?.ws ?? protocolMix.ws;
    const total = mqtt + https + ws;

    return [
      { label: 'MQTTS', value: mqtt, color: 'bg-emerald-500 dark:bg-emerald-400' },
      { label: 'HTTPS', value: https, color: 'bg-sky-500 dark:bg-sky-400' },
      { label: 'MQTT WebSocket', value: ws, color: 'bg-purple-500 dark:bg-purple-400' },
    ]
      .filter((entry) => entry.value > 0)
      .map((entry) => ({
        ...entry,
        percentage: total > 0 ? Math.round((entry.value / total) * 100) : 0,
      }));
  }, [protocolMix, telemetryDailyStats]);

  const alertSummary = useMemo(() => {
    const counts = recentAlerts.reduce(
      (acc, alert) => {
        const severity = (alert.severity ?? '').toLowerCase();
        if (['critical', 'high', 'error'].includes(severity)) acc.critical += 1;
        else if (['warning', 'medium'].includes(severity)) acc.warning += 1;
        else acc.info += 1;
        return acc;
      },
      { critical: 0, warning: 0, info: 0 },
    );
    const total = recentAlerts.length;
    const mostRecent = recentAlerts[0]?.timestamp;
    return {
      total,
      summary: total ? `${counts.critical} critical • ${counts.warning} warning` : 'All clear',
      helper: total ? `Latest update ${mostRecent ? formatTimestamp(mostRecent) : 'just now'}` : 'No active alerts detected',
    };
  }, [recentAlerts]);

  return (
    <div className="space-y-10 px-4 py-8 sm:px-6 xl:px-10">
      {maintenanceMode && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/95 backdrop-blur">
          <div className="rounded-lg border border-border bg-card px-8 py-6 text-center shadow-lg">
            <h2 className="text-lg font-semibold">System maintenance in progress</h2>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              We temporarily lost contact with the platform services—this often happens during deploys. Please try again in a moment.
            </p>
            <div className="mt-4 flex items-center justify-center gap-3">
              <Button variant="default" onClick={() => void refreshDashboard()}>
                Retry
              </Button>
              <Button variant="outline" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            </div>
          </div>
        </div>
      )}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Operational Overview</h1>
          <p className="text-muted-foreground max-w-2xl">
            Real-time snapshot of telemetry throughput, platform reliability, and security posture across the TESA IoT stack.
          </p>
          {lastUpdatedDisplay && (
            <p className="text-xs text-muted-foreground">
              Last updated at <span className="font-medium text-foreground/80">{lastUpdatedDisplay}</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs uppercase tracking-wide">
            Secure Production Cluster
          </Badge>
          <Button variant="outline" size="sm" onClick={refreshDashboard} disabled={loading} className="gap-2">
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {heroCards.map((card) => (
          <HeroMetricCard key={card.title} {...card} loading={loading} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-12">
        <div className="space-y-6 xl:col-span-8">
          <Card className="border-border/70">
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <CardTitle>Telemetry Throughput</CardTitle>
                <CardDescription>Secure ingest across MQTTS, MQTT over WebSocket, and HTTPS (24h)</CardDescription>
              </div>
              <Badge variant="secondary" className="w-fit text-xs font-medium">
                {telemetryDailyStats
                  ? `${formatNumber(telemetryDailyStats.daily.total_messages)} msg today`
                  : `${formatNumber(throughputStats.mqttPerMin + throughputStats.httpsPerMin)} msg/min live`
                }
              </Badge>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Hourly sparkline (24 bars) */}
              <TelemetrySparkline
                values={
                  telemetryDailyStats?.hourly_breakdown?.length
                    ? telemetryDailyStats.hourly_breakdown.map((h) => h.messages)
                    : telemetryTrend
                }
                loading={loading}
              />
              <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
                <div>
                  Today <span className="font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.daily.total_messages ?? throughputStats.totalMessages)}
                  </span> msg
                </div>
                <div>
                  Peak Hour <span className="font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.daily.peak_hour?.messages ?? throughputSummary.max ?? 0)}
                  </span> msg/hr
                  {telemetryDailyStats?.daily.peak_hour?.hour && (
                    <span className="text-xs ml-1">({telemetryDailyStats.daily.peak_hour.hour})</span>
                  )}
                </div>
                <div>
                  Now <span className="font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.live.msg_per_min ?? (throughputStats.mqttPerMin + throughputStats.httpsPerMin))}
                  </span> msg/min
                  <span className="text-xs ml-1 text-emerald-500">⚡</span>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border border-border/70 p-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Devices enrolled</span>
                    <Wifi className="h-4 w-4 text-emerald-500" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.daily.total_devices ?? throughputStats.totalDevices)}
                  </p>
                  {telemetryDailyStats?.live.active_devices !== undefined && telemetryDailyStats.live.active_devices > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {telemetryDailyStats.live.active_devices} active now
                    </p>
                  )}
                </div>
                <div className="rounded-lg border border-border/70 p-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>MQTTS throughput</span>
                    <Radio className="h-4 w-4 text-sky-500" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.protocol_mix.mqtt_per_day ?? throughputStats.mqttPerMin)}
                    <span className="ml-1 text-sm font-normal text-muted-foreground">
                      {telemetryDailyStats ? 'msg/day' : 'msg/min'}
                    </span>
                  </p>
                </div>
                <div className="rounded-lg border border-border/70 p-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>HTTPS throughput</span>
                    <Globe className="h-4 w-4 text-purple-500" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-foreground">
                    {formatNumber(telemetryDailyStats?.protocol_mix.https_per_day ?? throughputStats.httpsPerMin)}
                    <span className="ml-1 text-sm font-normal text-muted-foreground">
                      {telemetryDailyStats ? 'req/day' : 'req/min'}
                    </span>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-border/70">
              <CardHeader>
                <CardTitle className="text-base">Protocol Mix</CardTitle>
                <CardDescription>
                  Secure transport split ({telemetryDailyStats ? 'last 24h' : 'last refresh'})
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {protocolBreakdown.length ? (
                  protocolBreakdown.map((entry) => (
                    <div key={entry.label} className="space-y-2">
                      <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        <span>{entry.label}</span>
                        <span>{Math.min(100, Math.max(0, entry.percentage))}%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted">
                        <div
                          className={cn('h-2 rounded-full transition-all', entry.color)}
                          style={{ width: `${Math.min(100, Math.max(0, entry.percentage))}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-muted-foreground/30 p-6 text-center text-sm text-muted-foreground">
                    Awaiting protocol analytics from ingestion service
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/70">
              <CardHeader>
                <CardTitle className="text-base">Reliability Snapshot</CardTitle>
                <CardDescription>Last validation cycle across API Gateway & MQTT broker</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: 'API Gateway Success', value: successRates.apiSuccess },
                  { label: 'MQTTS Delivery Success', value: successRates.mqttSuccess },
                ].map((item) => (
                  <div key={item.label} className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{item.label}</span>
                      <span className="font-medium text-foreground">
                        {item.value ?? '--'}
                        {item.value !== null ? '%' : ''}
                      </span>
                    </div>
                    <Progress value={item.value ?? 0} className="h-2" />
                  </div>
                ))}
                <p className="text-xs text-muted-foreground">
                  Success rate thresholds <span className="font-medium text-foreground">≥ 98%</span> keep incident response in the green zone.
                </p>
              </CardContent>
            </Card>
          </div>

          <Card className="border-border/70">
            <CardHeader>
              <div>
                <CardTitle>System Health</CardTitle>
                <CardDescription>Core services monitored via Prometheus health endpoints</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {serviceCards.map((card) => (
                  <SystemHealthCard key={card.name} {...card} />
                ))}
              </div>
              {!serviceCards.length && (
                <div className="rounded-md border border-dashed border-muted-foreground/30 p-6 text-center text-sm text-muted-foreground">
                  Service telemetry unavailable – check Prometheus bridge or API permissions.
                </div>
              )}
            </CardContent>
          </Card>

          {/* DigitalOcean Infrastructure Metrics */}
          <InfrastructureMetrics
            refreshInterval={60000}
            showCharts={true}
            compact={false}
          />
        </div>

        <div className="space-y-6 xl:col-span-4">
          <Card className="border-border/70">
            <CardHeader>
              <div>
                <CardTitle>Security Posture</CardTitle>
                <CardDescription>Aggregated from vulnerability scans & certificate policy checks</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-muted">
                  <div className="text-2xl font-bold text-foreground">{securityScore ?? '--'}</div>
                  <div className="absolute text-[10px] font-medium uppercase text-muted-foreground">Score</div>
                </div>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    <span>{alertSummary.summary}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-primary" />
                    <span>{alertSummary.helper}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CalendarClock className="h-4 w-4 text-primary" />
                    <span>{recentAlerts.length ? 'Active alert monitoring enabled' : 'All clear in the last 24 hours'}</span>
                  </div>
                </div>
              </div>
              <Separator />
              <div className="space-y-2 rounded-lg border border-border/70 p-3 text-sm">
                <p className="font-medium text-foreground">Security Center</p>
                <p className="text-muted-foreground">
                  Review policies, certificates, and incident response playbooks with deeper context.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
              <CardDescription>Last 5 security or operational incidents</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentAlerts.length ? (
                recentAlerts.map((alert, index) => (
                  <div key={`${alert.title}-${index}`} className="rounded-lg border border-border/70 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="line-clamp-1 font-medium text-foreground">{alert.title}</span>
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium capitalize', SEVERITY_BADGE(alert.severity))}>
                        {alert.severity ?? 'unknown'}
                      </span>
                    </div>
                    {alert.description && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{alert.description}</p>
                    )}
                    {alert.timestamp && (
                      <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        <CalendarClock className="h-3 w-3" /> {formatTimestamp(alert.timestamp)}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-green-500/30 bg-green-50/50 dark:bg-green-950/20 p-6 text-center">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 mb-3">
                    <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">All Clear</p>
                  <p className="text-xs text-muted-foreground mt-1">No incidents detected in the last 24 hours</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Certificate Expiry Watchlist</CardTitle>
              <CardDescription>Devices that need certificate renewal within 30 days</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {certificateWatchlist.length ? (
                certificateWatchlist.map((item, index) => (
                  <div key={`${item.device}-${index}`} className="flex flex-col gap-1 rounded-lg border border-border/70 p-3 text-sm">
                    <span className="font-medium text-foreground">{item.device}</span>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <CalendarClock className="h-3 w-3" /> {item.expiresAt ? formatTimestamp(item.expiresAt) : 'No expiry metadata'}
                      </span>
                      <Badge variant="outline" className="text-xs font-medium">
                        {item.daysRemaining !== null ? `${item.daysRemaining} days` : 'TBC'}
                      </Badge>
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-green-500/30 bg-green-50/50 dark:bg-green-950/20 p-6 text-center">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 mb-3">
                    <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">All Certificates Valid</p>
                  <p className="text-xs text-muted-foreground mt-1">No certificates approaching expiry within 30 days</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default OperationalDashboard;
