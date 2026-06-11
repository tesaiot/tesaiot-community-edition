/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useCallback } from 'react';
import { getActivityLogsWebSocket } from '@/services/websocket/activityLogsWebSocket';
import { WS_EVENT_TYPES } from '@/constants/activityLogs';
import { toast } from 'sonner';

interface UseActivityLogsWebSocketOptions {
  enabled?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  onNewLog?: (log: any) => void;
  onStatsUpdate?: (stats: any) => void;
  onCriticalAlert?: (alert: any) => void;
  onSecurityAlert?: (alert: any) => void;
  showNotifications?: boolean;
}

export function useActivityLogsWebSocket(options: UseActivityLogsWebSocketOptions = {}) {
  const {
    enabled = true,
    onConnect,
    onDisconnect,
    onError,
    onNewLog,
    onStatsUpdate,
    onCriticalAlert,
    onSecurityAlert,
    showNotifications = true
  } = options;

  const wsRef = useRef<ReturnType<typeof getActivityLogsWebSocket> | null>(null);
  const unsubscribeRef = useRef<(() => void)[]>([]);

  const handleCriticalAlert = useCallback((alert: any) => {
    if (showNotifications) {
      toast.error(`Critical Alert: ${alert.message}`, {
        duration: 10000,
        action: {
          label: 'View',
          onClick: () => {
            // Navigate to logs or show alert details
            window.location.hash = '#critical-events';
          }
        }
      });
    }
    onCriticalAlert?.(alert);
  }, [onCriticalAlert, showNotifications]);

  const handleSecurityAlert = useCallback((alert: any) => {
    if (showNotifications) {
      toast.warning(`Security Alert: ${alert.message}`, {
        duration: 8000,
        action: {
          label: 'View',
          onClick: () => {
            window.location.hash = '#security-alerts';
          }
        }
      });
    }
    onSecurityAlert?.(alert);
  }, [onSecurityAlert, showNotifications]);

  useEffect(() => {
    if (!enabled) return;

    const ws = getActivityLogsWebSocket();
    wsRef.current = ws;

    // Configure WebSocket
    ws.connect();

    // Subscribe to events
    const subscriptions: (() => void)[] = [];

    // Connection events
    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.CONNECT, () => {
        if (showNotifications) {
          toast.success('Real-time logs connected');
        }
        onConnect?.();
      })
    );

    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.DISCONNECT, () => {
        if (showNotifications) {
          toast.warning('Real-time logs disconnected');
        }
        onDisconnect?.();
      })
    );

    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.ERROR, (data) => {
        if (showNotifications) {
          toast.error(`WebSocket error: ${data.error}`);
        }
        onError?.(new Error(data.error));
      })
    );

    // Log events
    if (onNewLog) {
      subscriptions.push(
        ws.subscribe(WS_EVENT_TYPES.LOG_NEW, onNewLog)
      );
    }

    if (onStatsUpdate) {
      subscriptions.push(
        ws.subscribe(WS_EVENT_TYPES.STATS_UPDATE, onStatsUpdate)
      );
    }

    // Alert events
    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.CRITICAL_ALERT, handleCriticalAlert)
    );

    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.SECURITY_ALERT, handleSecurityAlert)
    );

    subscriptions.push(
      ws.subscribe(WS_EVENT_TYPES.SYSTEM_ALERT, (alert) => {
        if (showNotifications) {
          toast.info(`System Alert: ${alert.message}`, {
            duration: 5000
          });
        }
      })
    );

    unsubscribeRef.current = subscriptions;

    return () => {
      // Unsubscribe from all events
      subscriptions.forEach(unsubscribe => unsubscribe());
      // Note: We don't disconnect the WebSocket here as it might be used by other components
    };
  }, [
    enabled,
    onConnect,
    onDisconnect,
    onError,
    onNewLog,
    onStatsUpdate,
    handleCriticalAlert,
    handleSecurityAlert,
    showNotifications
  ]);

  const send = useCallback((type: string, data: any) => {
    wsRef.current?.send(type, data);
  }, []);

  const isConnected = useCallback(() => {
    return wsRef.current?.isConnected ?? false;
  }, []);

  return {
    send,
    isConnected,
    ws: wsRef.current
  };
}