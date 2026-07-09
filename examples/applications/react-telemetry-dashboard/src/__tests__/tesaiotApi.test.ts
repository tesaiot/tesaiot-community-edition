/**
 * Unit tests for TESAIoT API Client
 *
 * Copyright (c) 2025 TESAIoT Platform (TESA)
 * Licensed under Apache License 2.0
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('TESAIoT API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe('apiFetch', () => {
    it('should include API key header in requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [] }),
      });

      // Import the module
      const { fetchTelemetryData } = await import('../api/tesaiotApi');

      await fetchTelemetryData('device-001', '2025-01-01', '2025-01-02');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': expect.any(String),
          }),
        })
      );
    });

    it('should throw error on non-OK response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve('Unauthorized'),
      });

      const { fetchTelemetryData } = await import('../api/tesaiotApi');

      await expect(
        fetchTelemetryData('device-001', '2025-01-01', '2025-01-02')
      ).rejects.toThrow('API Error (401)');
    });
  });

  describe('fetchTelemetryData', () => {
    it('should construct correct endpoint URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [] }),
      });

      const { fetchTelemetryData } = await import('../api/tesaiotApi');

      await fetchTelemetryData('device-001', '2025-01-01', '2025-01-02', 500);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('/api/v1/telemetry/device-001/query');
      expect(calledUrl).toContain('start_time=2025-01-01T00:00:00Z');
      expect(calledUrl).toContain('end_time=2025-01-02T23:59:59Z');
      expect(calledUrl).toContain('limit=500');
    });

    it('should return empty array when data is missing', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      const { fetchTelemetryData } = await import('../api/tesaiotApi');

      const result = await fetchTelemetryData('device-001', '2025-01-01', '2025-01-02');
      expect(result).toEqual([]);
    });

    it('should return telemetry data array', async () => {
      const mockData = [
        { timestamp: '2025-01-01T10:00:00Z', temperature: 25.5 },
        { timestamp: '2025-01-01T11:00:00Z', temperature: 26.0 },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockData }),
      });

      const { fetchTelemetryData } = await import('../api/tesaiotApi');

      const result = await fetchTelemetryData('device-001', '2025-01-01', '2025-01-02');
      expect(result).toEqual(mockData);
      expect(result).toHaveLength(2);
    });
  });

  describe('fetchAIResults', () => {
    it('should extract AI fields from telemetry data', async () => {
      const mockData = [
        {
          timestamp: '2025-01-01T10:00:00Z',
          temperature: 25.5,
          ai_confidence: 0.95,
          ai_anomalyScore: 0.1,
          ai_prediction: 'normal',
        },
        {
          timestamp: '2025-01-01T11:00:00Z',
          temperature: 45.0,
          ai_confidence: 0.85,
          ai_anomalyScore: 0.9,
          ai_prediction: 'anomaly',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockData }),
      });

      const { fetchAIResults } = await import('../api/tesaiotApi');

      const result = await fetchAIResults('device-001');
      expect(result).toHaveLength(2);
      expect(result[0].confidence).toBe(0.95);
      expect(result[0].prediction).toBe('normal');
      expect(result[1].anomaly_score).toBe(0.9);
    });

    it('should filter out entries without AI data', async () => {
      const mockData = [
        { timestamp: '2025-01-01T10:00:00Z', temperature: 25.5 },
        {
          timestamp: '2025-01-01T11:00:00Z',
          ai_confidence: 0.85,
          ai_prediction: 'warning',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockData }),
      });

      const { fetchAIResults } = await import('../api/tesaiotApi');

      const result = await fetchAIResults('device-001');
      expect(result).toHaveLength(1);
      expect(result[0].prediction).toBe('warning');
    });
  });

  describe('fetchDevices', () => {
    it('should return device list', async () => {
      const mockDevices = [
        { device_id: 'device-001', name: 'Sensor A' },
        { device_id: 'device-002', name: 'Sensor B' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ devices: mockDevices }),
      });

      const { fetchDevices } = await import('../api/tesaiotApi');

      const result = await fetchDevices();
      expect(result).toEqual(mockDevices);
      expect(result).toHaveLength(2);
    });

    it('should return empty array when devices missing', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      const { fetchDevices } = await import('../api/tesaiotApi');

      const result = await fetchDevices();
      expect(result).toEqual([]);
    });
  });

  describe('configureApi', () => {
    it('should update API configuration', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ devices: [] }),
      });

      const { configureApi, fetchDevices } = await import('../api/tesaiotApi');

      configureApi({ apiKey: 'new_api_key_12345' });
      await fetchDevices();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'new_api_key_12345',
          }),
        })
      );
    });
  });
});
