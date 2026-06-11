/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { tesaApi } from '@/services/api/tesaApi';

export interface DeviceHealthSSEConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export interface DeviceHealthSSEMessage {
  event: string;
  data: any;
  id?: string;
  retry?: number;
}

// SSE Event Types (same as WebSocket for consistency)
export const DEVICE_HEALTH_SSE_EVENTS = {
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

export type DeviceHealthSSEEventType = typeof DEVICE_HEALTH_SSE_EVENTS[keyof typeof DEVICE_HEALTH_SSE_EVENTS];

class DeviceHealthSSE {
  private eventSource: EventSource | null = null;
  private config: Required<DeviceHealthSSEConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;
  private subscribers: Map<string, Set<(data: any) => void>> = new Map();
  private lastEventId: string | null = null;

  constructor(config: DeviceHealthSSEConfig = {}) {
    const baseURL = tesaApi.api.defaults.baseURL || '';
    const defaultUrl = `${baseURL}/api/v1/devices/health/stream`;
    
    this.config = {
      url: config.url || defaultUrl,
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      onConnect: config.onConnect || (() => {}),
      onDisconnect: config.onDisconnect || (() => {}),
      onError: config.onError || (() => {})
    };
  }

  connect(deviceIds?: string[]): void {
    if (this.eventSource?.readyState === EventSource.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.createEventSource(deviceIds);
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

  private createEventSource(deviceIds?: string[]): void {
    try {
      // Build URL with authentication and parameters
      const token = localStorage.getItem('jwt_token') || localStorage.getItem('access_token');
      const url = new URL(this.config.url);
      
      if (token) {
        url.searchParams.set('token', token);
      }
      
      if (deviceIds && deviceIds.length > 0) {
        url.searchParams.set('deviceIds', deviceIds.join(','));
      }
      
      if (this.lastEventId) {
        url.searchParams.set('lastEventId', this.lastEventId);
      }

      // Create EventSource
      this.eventSource = new EventSource(url.toString());
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create Device Health SSE connection:', error);
      this.config.onError(error as Error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.eventSource) return;

    this.eventSource.onopen = () => {
      console.log('Device Health SSE connected');
      this.reconnectAttempts = 0;
      this.config.onConnect();
      this.notifySubscribers(DEVICE_HEALTH_SSE_EVENTS.CONNECT, { connected: true });
    };

    this.eventSource.onerror = (event) => {
      console.error('Device Health SSE error:', event);
      
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.config.onDisconnect();
        this.notifySubscribers(DEVICE_HEALTH_SSE_EVENTS.DISCONNECT, { connected: false });
        
        if (!this.isIntentionallyClosed) {
          this.scheduleReconnect();
        }
      } else {
        const error = new Error('Device Health SSE connection error');
        this.config.onError(error);
        this.notifySubscribers(DEVICE_HEALTH_SSE_EVENTS.ERROR, { error: error.message });
      }
    };

    // Handle specific event types
    Object.values(DEVICE_HEALTH_SSE_EVENTS).forEach(eventType => {
      if (eventType === DEVICE_HEALTH_SSE_EVENTS.CONNECT || 
          eventType === DEVICE_HEALTH_SSE_EVENTS.DISCONNECT || 
          eventType === DEVICE_HEALTH_SSE_EVENTS.ERROR) {
        return; // Skip internal events
      }

      this.eventSource!.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          this.lastEventId = event.lastEventId || this.lastEventId;
          this.notifySubscribers(eventType, data);
        } catch (error) {
          console.error(`Failed to parse SSE message for ${eventType}:`, error);
        }
      });
    });

    // Handle generic messages
    this.eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        this.lastEventId = event.lastEventId || this.lastEventId;
        
        // If the data contains a type field, use it as the event type
        if (data.type) {
          this.notifySubscribers(data.type, data.data || data);
        }
      } catch (error) {
        console.error('Failed to parse generic SSE message:', error);
      }
    };
  }

  private notifySubscribers(eventType: string, data: any): void {
    // Notify specific event subscribers
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

    // Notify wildcard subscribers
    const wildcardCallbacks = this.subscribers.get('*');
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach(callback => {
        try {
          callback({ event: eventType, data });
        } catch (error) {
          console.error('Error in wildcard subscriber callback:', error);
        }
      });
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max Device Health SSE reconnection attempts reached');
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
    console.log(`Scheduling Device Health SSE reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      this.createEventSource();
    }, delay);
  }

  private cleanup(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  get isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  get readyState(): number {
    return this.eventSource?.readyState ?? EventSource.CLOSED;
  }
}

// Hook implementation
export function useDeviceHealthSSE(
  deviceIds?: string[], 
  config?: DeviceHealthSSEConfig,
  preferSSE: boolean = false
) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<DeviceHealthSSEMessage | null>(null);
  const sseRef = useRef<DeviceHealthSSE | null>(null);

  useEffect(() => {
    // Skip if WebSocket is preferred and available
    if (!preferSSE && 'WebSocket' in window) {
      return;
    }

    // Create SSE instance
    sseRef.current = new DeviceHealthSSE({
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
    sseRef.current.connect(deviceIds);

    // Subscribe to all messages for lastMessage
    const unsubscribe = sseRef.current.subscribe('*', (message) => {
      setLastMessage({
        event: message.event || '*',
        data: message.data || message,
        id: new Date().getTime().toString()
      });
    });

    // Cleanup
    return () => {
      unsubscribe();
      sseRef.current?.disconnect();
    };
  }, [deviceIds?.join(','), preferSSE]);

  const subscribe = useCallback((eventType: string, callback: (data: any) => void) => {
    if (!sseRef.current) {
      console.warn('SSE not initialized');
      return () => {};
    }
    return sseRef.current.subscribe(eventType, callback);
  }, []);

  return {
    isConnected,
    lastMessage,
    subscribe,
    EVENTS: DEVICE_HEALTH_SSE_EVENTS
  };
}