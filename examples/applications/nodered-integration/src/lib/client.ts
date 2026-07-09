/**
 * Minimal TESAIoT HTTP client for the Node-RED nodes (Community Edition).
 *
 * The nodes call `client.get(path, params?)`. On CE the API-key (X-API-KEY) is
 * accepted for telemetry-ingest routes; device/dashboard reads are JWT-only, so
 * for those flows supply a bearer token via the `token` option (e.g. obtained from
 * POST /api/v1/auth/login) instead of, or in addition to, the API key.
 */
export interface TesaiotClientConfig {
  baseUrl: string;
  apiKey?: string;
  /** Optional JWT for read endpoints that CE gates behind @require_auth. */
  token?: string;
  timeoutMs?: number;
}

export interface TesaiotClient {
  get<T = unknown>(path: string, params?: Record<string, unknown>): Promise<T>;
}

export function createTesaiotClient(config: TesaiotClientConfig): TesaiotClient {
  const base = config.baseUrl.replace(/\/+$/, '');
  const timeoutMs = config.timeoutMs ?? 30000;

  return {
    async get<T = unknown>(path: string, params?: Record<string, unknown>): Promise<T> {
      const url = new URL(base + (path.startsWith('/') ? path : '/' + path));
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
        }
      }
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (config.token) headers['Authorization'] = `Bearer ${config.token}`;
      if (config.apiKey) headers['X-API-KEY'] = config.apiKey;

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const res = await fetch(url.toString(), { headers, signal: controller.signal });
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`TESAIoT API ${res.status}: ${body.slice(0, 200)}`);
        }
        return (await res.json()) as T;
      } finally {
        clearTimeout(timer);
      }
    },
  };
}
