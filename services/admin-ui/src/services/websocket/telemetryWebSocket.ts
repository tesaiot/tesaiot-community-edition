/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface TelemetryMessage {
  type: 'device_telemetry' | 'subscribed' | 'unsubscribed' | 'error';
  deviceId?: string;
  deviceIds?: string[];
  timestamp: string;
  data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  organization_id?: string;
  source?: string;
  data_source?: string;
}

export interface TelemetryWebSocketConfig {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onTelemetry?: (message: TelemetryMessage) => void;
}

const DEFAULT_CONFIG: Required<TelemetryWebSocketConfig> = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000,
  onConnect: () => {},
  onDisconnect: () => {},
  onError: () => {},
  onTelemetry: () => {},
};

export class TelemetryWebSocket {
  private ws: WebSocket | null = null;
  private config: Required<TelemetryWebSocketConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;
  private subscribedDevices: Set<string> = new Set();
  private telemetryCallbacks: Map<string, Set<(data: TelemetryMessage) => void>> = new Map();
  private connectionCallbacks: Set<() => void> = new Set();

  constructor(config: TelemetryWebSocketConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const token = localStorage.getItem('jwt_token') || localStorage.getItem('access_token');
    const baseUrl = `${protocol}//${host}/ws`;

    if (token) {
      return `${baseUrl}?token=${encodeURIComponent(token)}`;
    }
    return baseUrl;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.createWebSocket();
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.cleanup();
  }

  subscribeToDevice(deviceId: string, callback: (data: TelemetryMessage) => void): () => void {
    // Add callback for this device
    if (!this.telemetryCallbacks.has(deviceId)) {
      this.telemetryCallbacks.set(deviceId, new Set());
    }
    this.telemetryCallbacks.get(deviceId)!.add(callback);

    // Subscribe on WebSocket if connected
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.sendSubscription([deviceId]);
    } else {
      // Store for subscription when connected
      this.subscribedDevices.add(deviceId);
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.telemetryCallbacks.get(deviceId);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.telemetryCallbacks.delete(deviceId);
          this.subscribedDevices.delete(deviceId);
          this.sendUnsubscription([deviceId]);
        }
      }
    };
  }

  onConnectionChange(callback: () => void): () => void {
    this.connectionCallbacks.add(callback);
    return () => {
      this.connectionCallbacks.delete(callback);
    };
  }

  private sendSubscription(deviceIds: string[]): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    deviceIds.forEach(id => this.subscribedDevices.add(id));

    const message = {
      type: 'subscribe',
      deviceIds: Array.from(this.subscribedDevices),
      timestamp: new Date().toISOString(),
    };

    console.log('[TelemetryWS] Subscribing to devices:', message.deviceIds);
    this.ws.send(JSON.stringify(message));
  }

  private sendUnsubscription(deviceIds: string[]): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    const message = {
      type: 'unsubscribe',
      deviceIds,
      timestamp: new Date().toISOString(),
    };

    console.log('[TelemetryWS] Unsubscribing from devices:', deviceIds);
    this.ws.send(JSON.stringify(message));
  }

  private createWebSocket(): void {
    try {
      const url = this.getWebSocketUrl();
      console.log('[TelemetryWS] Connecting to:', url.replace(/token=[^&]+/, 'token=***'));

      this.ws = new WebSocket(url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('[TelemetryWS] Failed to create WebSocket:', error);
      this.config.onError(error as Error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('[TelemetryWS] Connected');
      this.reconnectAttempts = 0;
      this.config.onConnect();
      this.startHeartbeat();

      // Re-subscribe to all devices
      if (this.subscribedDevices.size > 0) {
        this.sendSubscription(Array.from(this.subscribedDevices));
      }

      this.connectionCallbacks.forEach(cb => cb());
    };

    this.ws.onclose = (event) => {
      console.log('[TelemetryWS] Disconnected:', event.code, event.reason);
      this.config.onDisconnect();
      this.stopHeartbeat();
      this.connectionCallbacks.forEach(cb => cb());

      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (event) => {
      console.error('[TelemetryWS] Error:', event);
      this.config.onError(new Error('WebSocket connection error'));
    };

    this.ws.onmessage = (event) => {
      try {
        const message: TelemetryMessage = JSON.parse(event.data);

        if (message.type === 'device_telemetry' && message.deviceId) {
          // Notify device-specific callbacks
          const callbacks = this.telemetryCallbacks.get(message.deviceId);
          if (callbacks) {
            callbacks.forEach(callback => {
              try {
                callback(message);
              } catch (error) {
                console.error('[TelemetryWS] Callback error:', error);
              }
            });
          }

          // Also notify global handler
          this.config.onTelemetry(message);
        } else if (message.type === 'subscribed') {
          console.log('[TelemetryWS] Subscription confirmed:', message.deviceIds, 'source:', message.data_source);
        } else if (message.type === 'error') {
          console.error('[TelemetryWS] Server error:', message);
        }
      } catch (error) {
        console.error('[TelemetryWS] Failed to parse message:', error);
      }
    };
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[TelemetryWS] Max reconnection attempts reached');
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(1.5, this.reconnectAttempts),
      30000
    );

    this.reconnectAttempts++;
    console.log(`[TelemetryWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.createWebSocket();
    }, delay);
  }

  private cleanup(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Singleton instance
let wsInstance: TelemetryWebSocket | null = null;

export function getTelemetryWebSocket(): TelemetryWebSocket {
  if (!wsInstance) {
    wsInstance = new TelemetryWebSocket();
  }
  return wsInstance;
}

export function disconnectTelemetryWebSocket(): void {
  if (wsInstance) {
    wsInstance.disconnect();
    wsInstance = null;
  }
}
