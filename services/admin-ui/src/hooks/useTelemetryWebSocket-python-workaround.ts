/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TEMPORARY WORKAROUND - Python WebSocket Service Direct Connection
 * This is a modified version of useTelemetryWebSocket that connects directly
 * to the Python WebSocket service for testing while Rust service is being debugged.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// Same interfaces as original file
interface TelemetryData {
  temperature: number;
  humidity: number;
  pressure: number;
  battery: number;
  rssi: number;
  uptime: number;
  location?: {
    lat: number;
    lng: number;
  };
}

interface WebSocketMessage {
  type: string;
  timestamp: string;
  [key: string]: any;
}

interface DeviceTelemetryMessage extends WebSocketMessage {
  type: 'device_telemetry';
  deviceId: string;
  data: TelemetryData;
}

interface MetricsUpdateMessage extends WebSocketMessage {
  type: 'metrics_update';
  organizationId: string;
  data: {
    devicesOnline: number;
    messagesPerSecond: number;
    activeConnections: number;
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    recentActivity: {
      type: string;
      message: string;
      severity: string;
    };
  };
}

interface SecurityEventMessage extends WebSocketMessage {
  type: 'security_event';
  event: {
    id: string;
    type: string;
    severity: string;
    timestamp: string;
    source: string;
    description: string;
    resolved: boolean;
  };
}

type TelemetryMessage = DeviceTelemetryMessage | MetricsUpdateMessage | SecurityEventMessage;

interface TelemetryWebSocketOptions {
  enabled?: boolean;
  onMessage?: (message: TelemetryMessage) => void;
  onDeviceTelemetry?: (deviceId: string, data: TelemetryData) => void;
  onMetricsUpdate?: (metrics: MetricsUpdateMessage['data']) => void;
  onSecurityEvent?: (event: SecurityEventMessage['event']) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
}

export function useTelemetryWebSocket(options: TelemetryWebSocketOptions = {}) {
  const {
    enabled = true,
    onMessage,
    onDeviceTelemetry,
    onMetricsUpdate,
    onSecurityEvent,
    reconnect = true,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastMessage, setLastMessage] = useState<TelemetryMessage | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const subscribedDevices = useRef<Set<string>>(new Set());
  const isReconnecting = useRef(false);
  const consecutiveFailures = useRef(0);
  const firstFailureTs = useRef<number>(0);

  // Keep latest callbacks/options in refs to avoid re-creating connect()
  const callbacksRef = useRef({ onMessage, onDeviceTelemetry, onMetricsUpdate, onSecurityEvent });
  useEffect(() => {
    callbacksRef.current = { onMessage, onDeviceTelemetry, onMetricsUpdate, onSecurityEvent };
  }, [onMessage, onDeviceTelemetry, onMetricsUpdate, onSecurityEvent]);
  const reconnectCfgRef = useRef({ reconnect, reconnectInterval, reconnectAttempts });
  useEffect(() => {
    reconnectCfgRef.current = { reconnect, reconnectInterval, reconnectAttempts };
  }, [reconnect, reconnectInterval, reconnectAttempts]);

  // Simple console log throttling to avoid flooding
  const lastLogTs = useRef<number>(0);
  const suppressedCount = useRef<number>(0);
  const logThrottleMs = 8000;

  function throttledLog(level: 'log' | 'warn' | 'error', ...args: any[]) {
    const now = Date.now();
    if (now - lastLogTs.current > logThrottleMs) {
      const prefix = suppressedCount.current > 0 ? ` (suppressed ${suppressedCount.current} repeats)` : '';
       
      console[level](...args, prefix);
      lastLogTs.current = now;
      suppressedCount.current = 0;
    } else {
      suppressedCount.current += 1;
    }
  }

  const connect = useCallback(() => {
    // CRITICAL: Don't create a new connection if one already exists
    if (ws.current && (ws.current.readyState === WebSocket.CONNECTING || ws.current.readyState === WebSocket.OPEN)) {
      console.log('[WebSocket] Connection already exists, not creating a new one');
      return;
    }
    
    throttledLog('log', '[WebSocket] WORKAROUND: Connecting directly to Python WebSocket service');

    // Get JWT token for authentication
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      throttledLog('error', '[WebSocket] No JWT token found, cannot authenticate WebSocket connection');
      setError(new Error('No authentication token found'));
      return;
    }
    
    // WORKAROUND: Connect directly to Python WebSocket service port
    // This bypasses NGINX routing and connects directly to the Python service
    // Use appropriate protocol based on current page protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;
    
    // Use nginx proxy instead of direct port connection for better security
    const wsUrl = `${protocol}//${hostname}/ws`;
    
    throttledLog('log', '[WebSocket] WORKAROUND: Direct connection to Python service at:', wsUrl);

    try {
      // Connect without JWT subprotocol as Python service doesn't support it
      // Authentication is handled at nginx level
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        throttledLog('log', '[WebSocket] ✅ Connected to Python WebSocket Telemetry Service');
        setIsConnected(true);
        setIsAuthenticated(true); // Python server doesn't require separate auth handshake
        setError(null);
        reconnectCount.current = 0;

        // Subscribe to devices immediately using Python server protocol
        if (subscribedDevices.current.size > 0) {
          const deviceIds = Array.from(subscribedDevices.current);
          throttledLog('log', '[WebSocket] Subscribing to devices:', deviceIds);
          try {
            // Python server expects: { type: 'subscribe', deviceIds: [...] }
            const subMsg = { type: 'subscribe', deviceIds };
            ws.current?.send(JSON.stringify(subMsg));
            throttledLog('log', '[WebSocket] Subscribe message sent');
          } catch (e) {
            throttledLog('error', '[WebSocket] Failed to send subscribe:', e);
          }
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as any;
          const typeVal = msg.type;

          // Python server message types (string-based)
          if (typeVal === 'subscribed') {
            // Subscription confirmed
            throttledLog('log', '[WebSocket] Subscription confirmed:', msg.deviceIds, 'source:', msg.data_source);
            return;
          }

          if (typeVal === 'pong') {
            // Keep-alive response
            return;
          }

          if (typeVal === 'error') {
            throttledLog('warn', '[WebSocket] Server error:', msg.message || msg);
            return;
          }

          // Handle telemetry data from Python server
          // Python server sends: { type: 'device_telemetry', deviceId: '...', data: {...}, timestamp: '...' }
          let legacyMessage: TelemetryMessage | null = null;

          if (typeVal === 'device_telemetry') {
            const deviceId = msg.deviceId || msg.device_id || '';
            const data = msg.data || {};
            legacyMessage = {
              type: 'device_telemetry',
              deviceId,
              data,
              timestamp: msg.timestamp || new Date().toISOString(),
            } as DeviceTelemetryMessage;
          } else if (typeVal === 'metrics_update') {
            legacyMessage = {
              type: 'metrics_update',
              organizationId: msg.organizationId || msg.organization_id || '',
              data: msg.data || {},
              timestamp: msg.timestamp || new Date().toISOString(),
            } as MetricsUpdateMessage;
          } else if (typeVal === 'security_event') {
            legacyMessage = {
              type: 'security_event',
              event: msg.event,
              timestamp: msg.timestamp || new Date().toISOString(),
            } as SecurityEventMessage;
          } else {
            // Unknown type; log and ignore
            throttledLog('log', '[WebSocket] Received message type:', typeVal);
            return;
          }

          if (legacyMessage) {
            setLastMessage(legacyMessage);

            // Call general handler
            callbacksRef.current.onMessage?.(legacyMessage);

            // Call specific handlers based on message type
            switch (legacyMessage.type) {
              case 'device_telemetry':
                callbacksRef.current.onDeviceTelemetry?.(legacyMessage.deviceId, legacyMessage.data);
                break;
              case 'metrics_update':
                callbacksRef.current.onMetricsUpdate?.(legacyMessage.data);
                break;
              case 'security_event':
                callbacksRef.current.onSecurityEvent?.(legacyMessage.event);
                break;
            }
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err, event.data);
        }
      };

      ws.current.onerror = (event) => {
        throttledLog('error', '[WebSocket] Enhanced WebSocket error:', event);
        setError(new Error('WebSocket connection error - server may be unavailable'));
      };

      ws.current.onclose = (event) => {
        throttledLog('log', '[WebSocket] 🔌 Disconnected from Enhanced WebSocket Service. Code:', event.code, 'Reason:', event.reason);
        setIsConnected(false);
        setIsAuthenticated(false);
        
        const { reconnect: doReconnect, reconnectInterval: baseInterval, reconnectAttempts: maxAttempts } = reconnectCfgRef.current;
        if (!doReconnect) {
          throttledLog('warn', '[WebSocket] Reconnect disabled');
          return;
        }

        // Failure window and cooldown: if >10 failures within 60s, pause 2 minutes
        const now = Date.now();
        if (firstFailureTs.current === 0 || now - firstFailureTs.current > 60_000) {
          firstFailureTs.current = now;
          consecutiveFailures.current = 1;
        } else {
          consecutiveFailures.current += 1;
        }

        if (consecutiveFailures.current > 10) {
          const cooldown = 120_000; // 2 minutes
          throttledLog('warn', `[WebSocket] Too many failures; entering cooldown for ${Math.round(cooldown/1000)}s`);
          if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
          reconnectTimeout.current = setTimeout(() => {
            throttledLog('log', '[WebSocket] Cooldown ended; attempting reconnect');
            consecutiveFailures.current = 0;
            firstFailureTs.current = 0;
            isReconnecting.current = false;
            connect();
          }, cooldown);
          return;
        }

        if (isReconnecting.current) {
          throttledLog('log', '[WebSocket] Reconnect already scheduled; skipping');
          return;
        }

        isReconnecting.current = true;
        reconnectCount.current++;
        const exp = Math.min(30_000, baseInterval * Math.pow(2, Math.min(reconnectCount.current, 5)));
        const jitter = Math.floor(Math.random() * 1000);
        const delay = exp + jitter;
        if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = setTimeout(() => {
          isReconnecting.current = false;
          throttledLog('log', `[WebSocket] Reconnecting in ${Math.round(delay/1000)}s (attempt ${reconnectCount.current})`);
          connect();
        }, delay);
      };
    } catch (err) {
      setError(err as Error);
    }
  }, []);

  const send = useCallback((data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      throttledLog('warn', '[WebSocket] WebSocket is not connected');
    }
  }, []);

  const subscribeToDevice = useCallback((deviceId: string) => {
    subscribedDevices.current.add(deviceId);
    if (isConnected && isAuthenticated) {
      // Python server expects: { type: 'subscribe', deviceIds: [...] }
      const deviceIds = Array.from(subscribedDevices.current);
      const subMsg = { type: 'subscribe', deviceIds };
      throttledLog('log', '[WebSocket] Subscribing to device:', deviceId);
      send(subMsg);
    }
  }, [send, isConnected, isAuthenticated]);

  const unsubscribeFromDevice = useCallback((deviceId: string) => {
    subscribedDevices.current.delete(deviceId);
    if (isConnected && isAuthenticated) {
      // Python server expects: { type: 'unsubscribe', deviceIds: [...] }
      const unsubMsg = { type: 'unsubscribe', deviceIds: [deviceId] };
      throttledLog('log', '[WebSocket] Unsubscribing from device:', deviceId);
      send(unsubMsg);
    }
  }, [send, isConnected, isAuthenticated]);

  const close = useCallback(() => {
    console.log('[WebSocket] Closing connection');
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null; // CRITICAL: Clear the reference so a new connection can be created
    }
    setIsConnected(false);
    // Clear all subscriptions
    subscribedDevices.current.clear();
  }, []);

  const reconnectManually = useCallback(() => {
    close();
    reconnectCount.current = 0;
    connect();
  }, [close, connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      close();
    }
    return () => {
      close();
    };
    // Intentionally depend only on `enabled` to avoid reconnection storms from callback identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Send periodic ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      send({ type: 'ping' });
    }, 30000); // Every 30 seconds

    return () => clearInterval(pingInterval);
  }, [isConnected, send]);

  return {
    isConnected,
    isAuthenticated,
    error,
    lastMessage,
    send,
    subscribeToDevice,
    unsubscribeFromDevice,
    close,
    reconnect: reconnectManually,
  };
}
