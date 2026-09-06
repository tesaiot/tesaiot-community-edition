/**
 * Unit tests for the Community Edition API client.
 *
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 *
 * These cover the shape the CE port actually has: reads are JWT-authenticated,
 * so every call logs in first and then makes the real request — two fetches,
 * not one — and telemetry comes from /api/v1/telemetry/unified/{id}, which is
 * the endpoint CE exposes.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  configureApi,
  fetchAIResults,
  fetchDevices,
  fetchTelemetryData,
} from '../api/tesaiotApi';

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

const BASE = 'https://localhost:21000';

/** A successful login, so the next queued response is the one under test. */
function queueLogin() {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => ({ token: 'test-jwt' }),
  });
}

function queueJson(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  // token: '' forces the login path; credentials satisfy ensureToken().
  configureApi({
    baseUrl: BASE,
    token: '',
    email: 'admin@localhost',
    password: 'unused-because-fetch-is-mocked',
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('authentication', () => {
  it('logs in before the first read and sends the JWT as a Bearer token', async () => {
    queueLogin();
    queueJson({ data_points: [] });

    await fetchTelemetryData('device-001', '', '');

    expect(mockFetch).toHaveBeenCalledTimes(2);
    const [loginUrl, loginInit] = mockFetch.mock.calls[0];
    expect(loginUrl).toBe(`${BASE}/api/v1/auth/login`);
    expect(loginInit.method).toBe('POST');

    const [, dataInit] = mockFetch.mock.calls[1];
    expect(dataInit.headers.Authorization).toBe('Bearer test-jwt');
  });

  it('reuses the token it already holds instead of logging in again', async () => {
    configureApi({ token: 'preset-jwt' });
    queueJson({ data_points: [] });

    await fetchTelemetryData('device-001', '', '');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain('/api/v1/telemetry/unified/device-001');
    expect(init.headers.Authorization).toBe('Bearer preset-jwt');
  });

  it('reports a failed login as a login failure, not as a data error', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 });

    await expect(fetchDevices()).rejects.toThrow('Login failed (401)');
  });
});

describe('fetchTelemetryData', () => {
  it('asks CE for the unified endpoint with the requested limit', async () => {
    queueLogin();
    queueJson({ data_points: [] });

    await fetchTelemetryData('device-001', '', '', 25);

    const [url] = mockFetch.mock.calls[1];
    expect(url).toBe(`${BASE}/api/v1/telemetry/unified/device-001?limit=25`);
  });

  it('gives every point both timestamp and time', async () => {
    queueLogin();
    queueJson({
      data_points: [{ timestamp: '2026-09-06T00:00:00Z', temperature: 25.5 }],
    });

    const points = await fetchTelemetryData('device-001', '', '');

    expect(points).toHaveLength(1);
    expect(points[0].timestamp).toBe('2026-09-06T00:00:00Z');
    expect(points[0].time).toBe('2026-09-06T00:00:00Z');
  });

  it('surfaces a failed read instead of returning silently empty data', async () => {
    queueLogin();
    queueJson({ detail: 'nope' }, 500);

    // Telemetry propagates: an empty chart and a broken backend must not look
    // the same to the caller. fetchAIResults is the one that swallows, because
    // an install without AI fields is normal rather than an error.
    await expect(fetchTelemetryData('device-001', '', '')).rejects.toThrow('API Error (500)');
  });
});

describe('fetchAIResults', () => {
  it('is empty on an install with no AI fields, which is the CE default', async () => {
    queueLogin();
    queueJson({ data_points: [{ timestamp: '2026-09-06T00:00:00Z', temperature: 25 }] });

    await expect(fetchAIResults('device-001')).resolves.toEqual([]);
  });
});

describe('fetchDevices', () => {
  it('maps the bare array CE returns', async () => {
    queueLogin();
    queueJson([{ device_id: 'sensor-1', name: 'sensor-1' }]);

    const devices = await fetchDevices();

    expect(devices).toHaveLength(1);
    expect(devices[0].device_id).toBe('sensor-1');
  });
});
