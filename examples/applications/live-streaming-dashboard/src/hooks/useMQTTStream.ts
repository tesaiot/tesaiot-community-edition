/**
 * MQTT Streaming Hook
 *
 * Manages MQTT-over-WebSocket connection to the CE EMQX broker
 * for real-time telemetry subscription.
 *
 * Features:
 * - Token-based authentication
 * - Automatic reconnection
 * - Message buffering
 * - Connection state management
 *
 * Usage:
 * ```tsx
 * const { isConnected, messages, connect, disconnect } = useMQTTStream({
 *   topic: 'device/+/telemetry/#',
 * });
 * ```
 *
 * @see the Community Edition docs
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import mqtt, { MqttClient, IClientOptions } from 'mqtt';
import type { TelemetryMessage, ConnectionStatus } from '../types';

interface UseMQTTStreamOptions {
  /** Community Edition uses per-device MQTT credentials, not a single API token. */
  username: string;
  password: string;
  /** MQTT client id — on CE the publish/subscribe ACL keys off the device id. */
  clientId?: string;
  brokerUrl?: string;
  topic?: string;
  maxMessages?: number;
}

interface UseMQTTStreamResult {
  status: ConnectionStatus;
  error: Error | null;
  messages: TelemetryMessage[];
  messageCount: number;
  connect: () => void;
  disconnect: () => void;
  clearMessages: () => void;
}

// Community Edition MQTT-over-WebSocket listener (loopback, plain ws).
// Serve the dashboard over http for local use, or front an EMQX WSS listener with
// nginx/APISIX TLS termination and use wss://<host>/mqtt.
const DEFAULT_BROKER_URL = 'ws://localhost:8083/mqtt';
// CE's per-device ACL scopes a device credential to its OWN topic. When no explicit
// topic is provided we subscribe to `device/<username>/telemetry` (built in connect()).
// A wildcard fleet view (device/+/telemetry) needs a privileged/service MQTT account.
const DEFAULT_MAX_MESSAGES = 1000;

/** CE uses per-device username/password — just require both to be present. */
function validateCredentials(username: string, password: string): boolean {
  return Boolean(username) && Boolean(password);
}

/**
 * Parse MQTT topic to extract device ID and sensor type
 *
 * Topic format: device/<device_id>/telemetry/<sensor_type>
 */
function parseTopic(topic: string): { deviceId: string; sensorType: string } {
  const parts = topic.split('/');
  return {
    deviceId: parts[1] || 'unknown',
    sensorType: parts.slice(3).join('/') || 'default',
  };
}

/**
 * Parse message payload (assumes JSON format).
 *
 * CE devices publish the canonical telemetry envelope
 * `{"device_id": ..., "timestamp": ..., "data": {metric: value, ...}}` —
 * flatten the inner `data` object so the chart sees the metrics directly.
 */
function parsePayload(payload: Buffer): Record<string, unknown> {
  try {
    const parsed = JSON.parse(payload.toString());
    if (parsed && typeof parsed === 'object' && parsed.data && typeof parsed.data === 'object') {
      return { ...parsed.data, timestamp: parsed.timestamp };
    }
    return parsed;
  } catch {
    return { raw: payload.toString() };
  }
}

export function useMQTTStream({
  username,
  password,
  clientId,
  brokerUrl = DEFAULT_BROKER_URL,
  topic,
  maxMessages = DEFAULT_MAX_MESSAGES,
}: UseMQTTStreamOptions): UseMQTTStreamResult {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [messages, setMessages] = useState<TelemetryMessage[]>([]);

  const clientRef = useRef<MqttClient | null>(null);

  /**
   * Connect to MQTT broker
   */
  const connect = useCallback(() => {
    // Validate credentials
    if (!validateCredentials(username, password)) {
      setError(new Error('MQTT username and password are required.'));
      setStatus('error');
      return;
    }

    // Don't reconnect if already connected
    if (clientRef.current?.connected) {
      return;
    }

    setStatus('connecting');
    setError(null);

    // CE's ACL keys off the MQTT client id; default it to the device id (username).
    const resolvedClientId = clientId || username;
    // Default to this device's own telemetry topic (CE ACL denies wildcard for
    // per-device credentials).
    const resolvedTopic = topic || `device/${username}/telemetry`;

    const options: IClientOptions = {
      username,
      password,
      clientId: resolvedClientId,
      reconnectPeriod: 5000,
      connectTimeout: 30000,
      keepalive: 60,
      clean: true,
    };

    console.log(`[MQTT] Connecting to ${brokerUrl}...`);
    const client = mqtt.connect(brokerUrl, options);
    clientRef.current = client;

    client.on('connect', () => {
      console.log('[MQTT] Connected successfully');
      setStatus('connected');

      client.subscribe(resolvedTopic, { qos: 1 }, (err, granted) => {
        if (err) {
          console.error('[MQTT] Subscription error:', err);
          setError(new Error(`Subscription failed: ${err.message}`));
        } else {
          console.log('[MQTT] Subscribed to:', granted?.map((g) => g.topic).join(', '));
        }
      });
    });

    client.on('message', (receivedTopic, payload) => {
      const { deviceId, sensorType } = parseTopic(receivedTopic);
      const data = parsePayload(payload);

      const message: TelemetryMessage = {
        deviceId,
        sensorType,
        data: data as Record<string, number | string | boolean>,
        timestamp: new Date(),
        raw: payload.toString(),
      };

      setMessages((prev) => {
        const updated = [...prev, message];
        // Keep only last maxMessages
        return updated.slice(-maxMessages);
      });
    });

    client.on('error', (err) => {
      console.error('[MQTT] Error:', err);
      setError(err);
      setStatus('error');
    });

    client.on('close', () => {
      console.log('[MQTT] Connection closed');
      if (status !== 'error') {
        setStatus('disconnected');
      }
    });

    client.on('reconnect', () => {
      console.log('[MQTT] Reconnecting...');
      setStatus('connecting');
    });
  }, [username, password, clientId, brokerUrl, topic, maxMessages, status]);

  /**
   * Disconnect from MQTT broker
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      console.log('[MQTT] Disconnecting...');
      clientRef.current.end();
      clientRef.current = null;
      setStatus('disconnected');
    }
  }, []);

  /**
   * Clear message buffer
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.end();
        clientRef.current = null;
      }
    };
  }, []);

  return {
    status,
    error,
    messages,
    messageCount: messages.length,
    connect,
    disconnect,
    clearMessages,
  };
}
