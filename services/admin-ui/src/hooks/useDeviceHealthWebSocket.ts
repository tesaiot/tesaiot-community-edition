/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { tesaApi } from '@/services/api/tesaApi';

export interface DeviceHealthWebSocketConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export interface DeviceHealthMessage {
  type: string;
  data: any;
  timestamp: string;
  deviceId?: string;
}

// Device Health Event Types
export const DEVICE_HEALTH_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  HEALTH_UPDATE: 'device:health:update',
  HEALTH_TRENDS: 'device:health:trends',
  ERROR_PATTERN: 'device:error:pattern',
  LOG_NEW: 'device:log:new',
  ALERT: 'device:alert',
  STATUS_CHANGE: 'device:status:change',
  METRIC_UPDATE: 'device:metric:update',
  ANOMALY_DETECTED: 'device:anomaly:detected'
} as const;

export type DeviceHealthEventType = typeof DEVICE_HEALTH_EVENTS[keyof typeof DEVICE_HEALTH_EVENTS];

class DeviceHealthWebSocket {
  private ws: WebSocket | null = null;
  private config: Required<DeviceHealthWebSocketConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;
  private messageQueue: DeviceHealthMessage[] = [];
  private subscribers: Map<string, Set<(data: any) => void>> = new Map();
  private subscriptionId: string | null = null;

  constructor(config: DeviceHealthWebSocketConfig = {}) {
    const defaultUrl = tesaApi.getDeviceHealthWebSocketUrl();
    
    this.config = {
      url: config.url || defaultUrl,
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      heartbeatInterval: config.heartbeatInterval || 30000,
      onConnect: config.onConnect || (() => {}),
      onDisconnect: config.onDisconnect || (() => {}),
      onError: config.onError || (() => {})
    };
  }

  connect(deviceIds?: string[]): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.createWebSocket(deviceIds);
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.cleanup();
  }

  subscribe(eventType: string, callback: (data: any) => void): () => void {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set());
    }
    this.subscribers.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscribers.get(eventType);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscribers.delete(eventType);
        }
      }
    };
  }

  send(type: string, data: any): void {
    const message: DeviceHealthMessage = {
      type,
      data,
      timestamp: new Date().toISOString()
    };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for later
      this.messageQueue.push(message);
    }
  }

  private async createWebSocket(deviceIds?: string[]): Promise<void> {
    try {
      // Subscribe to device health updates if deviceIds provided
      if (deviceIds && deviceIds.length > 0) {
        const result = await tesaApi.subscribeToDeviceHealth(deviceIds);
        this.subscriptionId = result.subscriptionId;
      }

      // Add authentication token to WebSocket URL
      const token = localStorage.getItem('jwt_token') || localStorage.getItem('access_token');
      const url = new URL(this.config.url);
      if (token) {
        url.searchParams.set('token', token);
      }
      if (this.subscriptionId) {
        url.searchParams.set('subscriptionId', this.subscriptionId);
      }

      this.ws = new WebSocket(url.toString());
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create Device Health WebSocket:', error);
      this.config.onError(error as Error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('Device Health WebSocket connected');
      this.reconnectAttempts = 0;
      this.config.onConnect();
      this.startHeartbeat();
      this.flushMessageQueue();
      this.notifySubscribers(DEVICE_HEALTH_EVENTS.CONNECT, { connected: true });
    };

    this.ws.onclose = () => {
      console.log('Device Health WebSocket disconnected');
      this.config.onDisconnect();
      this.stopHeartbeat();
      this.notifySubscribers(DEVICE_HEALTH_EVENTS.DISCONNECT, { connected: false });
      
      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (event) => {
      console.error('Device Health WebSocket error:', event);
      const error = new Error('Device Health WebSocket connection error');
      this.config.onError(error);
      this.notifySubscribers(DEVICE_HEALTH_EVENTS.ERROR, { error: error.message });
    };

    this.ws.onmessage = (event) => {
      try {
        const message: DeviceHealthMessage = JSON.parse(event.data);
        this.notifySubscribers(message.type, message.data);
      } catch (error) {
        console.error('Failed to parse Device Health WebSocket message:', error);
      }
    };
  }

  private notifySubscribers(eventType: string, data: any): void {
    const callbacks = this.subscribers.get(eventType);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in subscriber callback for ${eventType}:`, error);
        }
      });
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping', { timestamp: Date.now() });
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift();
      if (message) {
        this.ws.send(JSON.stringify(message));
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max Device Health WebSocket reconnection attempts reached');
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds
    );

    this.reconnectAttempts++;
    console.log(`Scheduling Device Health WebSocket reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      this.createWebSocket();
    }, delay);
  }

  private async cleanup(): Promise<void> {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // Unsubscribe from device health updates
    if (this.subscriptionId) {
      try {
        await tesaApi.unsubscribeFromDeviceHealth(this.subscriptionId);
      } catch (error) {
        console.error('Failed to unsubscribe from device health:', error);
      }
      this.subscriptionId = null;
    }

    this.messageQueue = [];
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Hook implementation
export function useDeviceHealthWebSocket(deviceIds?: string[], config?: DeviceHealthWebSocketConfig) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<DeviceHealthMessage | null>(null);
  const wsRef = useRef<DeviceHealthWebSocket | null>(null);

  useEffect(() => {
    // Create WebSocket instance
    wsRef.current = new DeviceHealthWebSocket({
      ...config,
      onConnect: () => {
        setIsConnected(true);
        config?.onConnect?.();
      },
      onDisconnect: () => {
        setIsConnected(false);
        config?.onDisconnect?.();
      },
      onError: (error) => {
        config?.onError?.(error);
      }
    });

    // Connect with device IDs
    wsRef.current.connect(deviceIds);

    // Subscribe to all messages for lastMessage
    const unsubscribe = wsRef.current.subscribe('*', (message) => {
      setLastMessage({
        type: '*',
        data: message,
        timestamp: new Date().toISOString()
      });
    });

    // Cleanup
    return () => {
      unsubscribe();
      wsRef.current?.disconnect();
    };
  }, []);

  const subscribe = useCallback((eventType: string, callback: (data: any) => void) => {
    if (!wsRef.current) {
      console.warn('WebSocket not initialized');
      return () => {};
    }
    return wsRef.current.subscribe(eventType, callback);
  }, []);

  const send = useCallback((type: string, data: any) => {
    if (!wsRef.current) {
      console.warn('WebSocket not initialized');
      return;
    }
    wsRef.current.send(type, data);
  }, []);

  return {
    isConnected,
    lastMessage,
    subscribe,
    send,
    EVENTS: DEVICE_HEALTH_EVENTS
  };
}