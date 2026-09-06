/**
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 *
 * The pure parts of the MQTT stream hook. The example shipped a `test` script
 * and a vitest config and no tests at all, so nothing here was ever checked —
 * including the broker default, which .env.example still pointed at a cloud
 * listener (8085/WSS) that does not exist on Community Edition.
 */

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_BROKER_URL,
  parsePayload,
  parseTopic,
  validateCredentials,
} from './useMQTTStream';

describe('DEFAULT_BROKER_URL', () => {
  it('is the listener Community Edition actually serves', () => {
    // CE publishes MQTT-over-WebSocket on 8083. 8085/WSS is cloud-only.
    expect(DEFAULT_BROKER_URL).toBe('ws://localhost:8083/mqtt');
  });
});

describe('validateCredentials', () => {
  it('accepts a device id and its password', () => {
    expect(validateCredentials('sensor-1', 'a-password')).toBe(true);
  });

  it.each([
    ['', 'a-password'],
    ['sensor-1', ''],
    ['', ''],
  ])('refuses (%j, %j)', (u, p) => {
    expect(validateCredentials(u, p)).toBe(false);
  });
});

describe('parseTopic', () => {
  it('reads the device id out of device/<id>/telemetry', () => {
    expect(parseTopic('device/sensor-1/telemetry')).toEqual({
      deviceId: 'sensor-1',
      sensorType: 'default',
    });
  });

  it('keeps a multi-segment sensor type intact', () => {
    expect(parseTopic('device/sensor-1/telemetry/env/temp')).toEqual({
      deviceId: 'sensor-1',
      sensorType: 'env/temp',
    });
  });

  it('does not invent a device id for a topic that has none', () => {
    expect(parseTopic('telemetry').deviceId).toBe('unknown');
  });
});

describe('parsePayload', () => {
  it('flattens the CE telemetry envelope so the chart sees metrics directly', () => {
    const body = JSON.stringify({
      device_id: 'sensor-1',
      timestamp: '2026-09-06T00:00:00Z',
      data: { temperature: 25.5, humidity: 60 },
    });

    expect(parsePayload(Buffer.from(body))).toEqual({
      temperature: 25.5,
      humidity: 60,
      timestamp: '2026-09-06T00:00:00Z',
    });
  });

  it('passes through a flat payload unchanged', () => {
    const body = JSON.stringify({ temperature: 21 });
    expect(parsePayload(Buffer.from(body))).toEqual({ temperature: 21 });
  });

  it('keeps unparseable bytes instead of throwing into the message handler', () => {
    expect(parsePayload(Buffer.from('not json'))).toEqual({ raw: 'not json' });
  });
});
