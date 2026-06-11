/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { SyncStatus, SyncStatusType, UseAutoSyncOptions, UseAutoSyncReturn } from '@/components/ui/bdh-data-grid/types';

const DEFAULT_POLLING_INTERVAL = 30000; // 30 seconds

/**
 * Create initial sync status
 */
function createInitialStatus(): SyncStatus {
  return {
    status: 'idle',
    lastSyncedAt: null,
    error: undefined,
    isConnected: false,
    isSyncing: false,
  };
}

/**
 * useAutoSync Hook
 *
 * @example
 * ```tsx
 * const sync = useAutoSync({
 *   enabled: true,
 *   mode: 'polling',
 *   pollingInterval: 30000,
 *   onDataRefresh: async () => {
 *     const response = await fetch('/api/devices');
 *     return response.json();
 *   }
 * });
 *
 * // Display sync status
 * {sync.isSyncing && <Spinner />}
 * {sync.lastSyncedAt && <span>Last updated: {formatDate(sync.lastSyncedAt)}</span>}
 * ```
 */
export function useAutoSync<TData>(
  options: UseAutoSyncOptions<TData>
): UseAutoSyncReturn {
  const {
    enabled = false,
    mode = 'polling',
    pollingInterval = DEFAULT_POLLING_INTERVAL,
    wsEndpoint,
    onDataRefresh,
    onStatusChange,
  } = options;

  // State
  const [status, setStatus] = useState<SyncStatus>(createInitialStatus);
  const [isPaused, setIsPaused] = useState(false);

  // Refs
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  // Update status and notify
  const updateStatus = useCallback(
    (updates: Partial<SyncStatus>) => {
      setStatus((prev) => {
        const next = { ...prev, ...updates };
        onStatusChange?.(next);
        return next;
      });
    },
    [onStatusChange]
  );

  // Perform data refresh
  const refresh = useCallback(async () => {
    if (!onDataRefresh || !mountedRef.current) return;

    updateStatus({
      status: 'syncing',
      isSyncing: true,
    });

    try {
      await onDataRefresh();

      if (mountedRef.current) {
        updateStatus({
          status: 'idle',
          lastSyncedAt: new Date(),
          error: undefined,
          isSyncing: false,
        });
      }
    } catch (error) {
      if (mountedRef.current) {
        updateStatus({
          status: 'error',
          error: error instanceof Error ? error.message : 'Sync failed',
          isSyncing: false,
        });
      }
    }
  }, [onDataRefresh, updateStatus]);

  // Start polling
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Initial fetch
    refresh();

    // Set up interval
    pollingIntervalRef.current = setInterval(() => {
      if (!isPaused && mountedRef.current) {
        refresh();
      }
    }, pollingInterval);
  }, [pollingInterval, refresh, isPaused]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // Connect WebSocket
  const connectWebSocket = useCallback(() => {
    if (!wsEndpoint) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      wsRef.current = new WebSocket(wsEndpoint);

      wsRef.current.onopen = () => {
        if (mountedRef.current) {
          updateStatus({
            status: 'connected',
            isConnected: true,
            error: undefined,
          });
        }
      };

      wsRef.current.onclose = () => {
        if (mountedRef.current) {
          updateStatus({
            status: 'disconnected',
            isConnected: false,
          });

          // Attempt reconnection after 5 seconds
          if (enabled && !isPaused) {
            setTimeout(() => {
              if (mountedRef.current && enabled && !isPaused) {
                connectWebSocket();
              }
            }, 5000);
          }
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('[useAutoSync] WebSocket error:', event);
        if (mountedRef.current) {
          updateStatus({
            status: 'error',
            error: 'WebSocket connection error',
            isConnected: false,
          });
        }
      };

      wsRef.current.onmessage = (event) => {
        if (mountedRef.current) {
          // Trigger data refresh when message received
          refresh();
        }
      };
    } catch (error) {
      console.error('[useAutoSync] Failed to connect WebSocket:', error);
      updateStatus({
        status: 'error',
        error: 'Failed to connect WebSocket',
        isConnected: false,
      });
    }
  }, [wsEndpoint, enabled, isPaused, updateStatus, refresh]);

  // Disconnect WebSocket
  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Pause sync
  const pause = useCallback(() => {
    setIsPaused(true);
    stopPolling();
    disconnectWebSocket();
    updateStatus({
      status: 'idle',
      isSyncing: false,
    });
  }, [stopPolling, disconnectWebSocket, updateStatus]);

  // Resume sync
  const resume = useCallback(() => {
    setIsPaused(false);
    if (enabled) {
      if (mode === 'polling' || mode === 'both') {
        startPolling();
      }
      if (mode === 'websocket' || mode === 'both') {
        connectWebSocket();
      }
    }
  }, [enabled, mode, startPolling, connectWebSocket]);

  // Effect: Start/stop sync based on enabled state
  useEffect(() => {
    if (!enabled || isPaused) {
      stopPolling();
      disconnectWebSocket();
      return;
    }

    if (mode === 'polling' || mode === 'both') {
      startPolling();
    }

    if ((mode === 'websocket' || mode === 'both') && wsEndpoint) {
      connectWebSocket();
    }

    return () => {
      stopPolling();
      disconnectWebSocket();
    };
  }, [enabled, mode, isPaused, startPolling, stopPolling, connectWebSocket, disconnectWebSocket, wsEndpoint]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopPolling();
      disconnectWebSocket();
    };
  }, [stopPolling, disconnectWebSocket]);

  return {
    status,
    refresh,
    pause,
    resume,
    isConnected: status.isConnected,
    isSyncing: status.isSyncing,
    lastSyncedAt: status.lastSyncedAt,
  };
}

export default useAutoSync;
