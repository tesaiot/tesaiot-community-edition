/**
 * TESAIoT API Client — Community Edition
 *
 * Connects to a self-hosted Community Edition install. CE gates device and
 * telemetry reads behind JWT (email/password), so this client logs in and sends
 * a Bearer token — it does NOT use a static API key for reads. No secret is
 * committed; credentials come from Vite env vars.
 *
 * Licensed under Apache License 2.0
 * Copyright TESAIoT Platform contributors
 */

// Vite exposes import.meta.env.*; fall back to CE localhost defaults.
const env = (import.meta as unknown as { env?: Record<string, string> }).env ?? {};

const API_CONFIG = {
  // CE edge (nginx/APISIX). Default to the local install.
  // Same-origin under `npm run dev` so requests go through the Vite proxy.
  // CE answers a preflight 200 but sends no access-control-allow-origin, so a
  // direct cross-origin call from the dev server is blocked by the browser —
  // which is what the proxy is for. A built bundle keeps an absolute default.
  baseUrl: env.VITE_API_BASE_URL || (env.DEV ? '' : 'https://localhost'),
  // Demo credentials for the JWT login (set these in .env; never commit real ones).
  email: env.VITE_ADMIN_EMAIL || '',
  password: env.VITE_ADMIN_PASSWORD || '',
  // A pre-obtained JWT may be supplied instead of email/password.
  token: env.VITE_JWT || '',
  // Kept for backward compat with the demo UI; unused on CE (reads are JWT-only).
  apiKey: '',
};

// Types for telemetry data
export interface TelemetryPoint {
  timestamp: string;
  time: string;
  temperature?: number;
  humidity?: number;
  pressure?: number;
  ai_confidence?: number;
  ai_anomalyScore?: number;
  ai_prediction?: 'normal' | 'warning' | 'anomaly';
  [key: string]: string | number | undefined;
}

export interface AIResult {
  timestamp: string;
  confidence: number;
  anomaly_score: number;
  prediction: 'normal' | 'warning' | 'anomaly';
  model_version?: string;
  latency_ms?: number;
}

export interface DeviceInfo {
  device_id: string;
  name: string;
  device_type?: string;
  status?: string;
}

/** Obtain (and cache) a JWT: use a supplied token, else log in with email/password. */
async function ensureToken(): Promise<string> {
  if (API_CONFIG.token) return API_CONFIG.token;
  if (!API_CONFIG.email || !API_CONFIG.password) {
    throw new Error(
      'CE reads require authentication. Set VITE_ADMIN_EMAIL/VITE_ADMIN_PASSWORD (or VITE_JWT).'
    );
  }
  const res = await fetch(`${API_CONFIG.baseUrl}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: API_CONFIG.email, password: API_CONFIG.password }),
  });
  if (!res.ok) throw new Error(`Login failed (${res.status})`);
  const data = await res.json();
  API_CONFIG.token = data.token;
  return API_CONFIG.token;
}

/** Fetch helper with Bearer (JWT) authentication. */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = await ensureToken();
  const response = await fetch(`${API_CONFIG.baseUrl}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error (${response.status}): ${error}`);
  }
  return response.json();
}

/**
 * Fetch telemetry for a device from CE's unified telemetry endpoint.
 * (CE has no /telemetry/{id}/query; it exposes /telemetry/unified/{id}.)
 * startDate/endDate are accepted for signature compatibility.
 */
export async function fetchTelemetryData(
  deviceId: string,
  _startDate: string,
  _endDate: string,
  limit: number = 1000
): Promise<TelemetryPoint[]> {
  const endpoint = `/api/v1/telemetry/unified/${deviceId}?limit=${limit}`;
  try {
    const res = await apiFetch<{ data_points?: Record<string, unknown>[] }>(endpoint);
    const points = res.data_points || [];
    return points.map((p) => {
      const ts = String(p.timestamp ?? '');
      return { ...p, timestamp: ts, time: ts } as TelemetryPoint;
    });
  } catch (error) {
    console.error('Failed to fetch telemetry data:', error);
    throw error;
  }
}

/**
 * AI inference results. CE excludes the AI/analytics module, so telemetry carries
 * no ai_* fields (has_ai_data is false); this returns an empty list and the AI
 * overlay degrades gracefully. Kept for signature compatibility.
 */
export async function fetchAIResults(
  deviceId: string,
  limit: number = 100
): Promise<AIResult[]> {
  const endpoint = `/api/v1/telemetry/unified/${deviceId}?limit=${limit}`;
  try {
    const res = await apiFetch<{ data_points?: TelemetryPoint[] }>(endpoint);
    return (res.data_points || [])
      .filter((point) => point.ai_confidence !== undefined)
      .map((point) => ({
        timestamp: point.timestamp,
        confidence: point.ai_confidence || 0,
        anomaly_score: point.ai_anomalyScore || 0,
        prediction: point.ai_prediction || 'normal',
        latency_ms: point.ai_latency as number | undefined,
      }));
  } catch (error) {
    console.error('Failed to fetch AI results:', error);
    return [];
  }
}

/** Fetch the device list (CE returns a bare array of device objects). */
export async function fetchDevices(): Promise<DeviceInfo[]> {
  try {
    const data = await apiFetch<DeviceInfo[] | { devices: DeviceInfo[] }>('/api/v1/devices/');
    const list = Array.isArray(data) ? data : data.devices || [];
    return list.map((d) => ({
      device_id: d.device_id,
      name: d.name || d.device_id,
      device_type: d.device_type,
      status: d.status,
    }));
  } catch (error) {
    console.error('Failed to fetch devices:', error);
    throw error;
  }
}

/** Update API configuration (baseUrl, email/password, token). */
export function configureApi(config: Partial<typeof API_CONFIG>) {
  Object.assign(API_CONFIG, config);
}

export default {
  fetchTelemetryData,
  fetchAIResults,
  fetchDevices,
  configureApi,
};
