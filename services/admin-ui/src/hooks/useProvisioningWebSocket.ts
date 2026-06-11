/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

interface ProvisioningProgress {
  session_id: string;
  progress: number;
  current_device: number;
  total_devices: number;
  successful: number;
  failed: number;
  skipped: number;
  status: 'processing' | 'completed' | 'failed';
}

interface KeyGenerationStatus {
  operation_id: string;
  status: 'started' | 'completed' | 'failed';
  device_id: string;
  key_type: string;
  serial_number?: string;
  error_message?: string;
  progress: number;
}

interface DeviceDiscovery {
  device_id: string;
  device_name?: string;
  device_type?: string;
  organization_id: string;
  discovery_method: string;
  timestamp: string;
}

interface ProvisioningNotification {
  id: string;
  type: 'provisioning';
  category: string;
  subtype: string;
  title: string;
  message: string;
  status: 'unread' | 'read';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  metadata: any;
  actions: Array<{
    label: string;
    action: string;
    variant: string;
  }>;
}

interface ProvisioningWebSocketData {
  type: 'provisioning_progress' | 'key_generation_status' | 'device_discovery' | 'notification' | 'connected';
  session_id?: string;
  operation_id?: string;
  organization_id?: string;
  organizationId?: string; // For 'connected' messages
  consumer?: any; // For 'connected' messages
  data?: ProvisioningProgress | KeyGenerationStatus | DeviceDiscovery | ProvisioningNotification;
  features?: string[]; // For 'connected' messages
  timestamp: string;
}

interface ProvisioningWebSocketHook {
  // Connection state
  isConnected: boolean;
  error: Error | null;
  
  // Latest data
  latestProgress: ProvisioningProgress | null;
  latestKeyStatus: KeyGenerationStatus | null;
  latestDiscovery: DeviceDiscovery | null;
  latestNotification: ProvisioningNotification | null;
  
  // History
  progressHistory: ProvisioningProgress[];
  keyStatusHistory: KeyGenerationStatus[];
  discoveryHistory: DeviceDiscovery[];
  notificationHistory: ProvisioningNotification[];
  
  // Controls
  clearHistory: () => void;
  reconnect: () => void;
  
  // Session-specific data
  getSessionProgress: (sessionId: string) => ProvisioningProgress | null;
  getOperationStatus: (operationId: string) => KeyGenerationStatus | null;
}

export function useProvisioningWebSocket(
  wsUrl: string | null,
  options: {
    maxHistorySize?: number;
    reconnectInterval?: number;
    reconnectAttempts?: number;
  } = {}
): ProvisioningWebSocketHook {
  const {
    maxHistorySize = 100,
    reconnectInterval = 3000,
    reconnectAttempts = 5
  } = options;

  // State for different types of data
  const [latestProgress, setLatestProgress] = useState<ProvisioningProgress | null>(null);
  const [latestKeyStatus, setLatestKeyStatus] = useState<KeyGenerationStatus | null>(null);
  const [latestDiscovery, setLatestDiscovery] = useState<DeviceDiscovery | null>(null);
  const [latestNotification, setLatestNotification] = useState<ProvisioningNotification | null>(null);
  
  // History arrays
  const [progressHistory, setProgressHistory] = useState<ProvisioningProgress[]>([]);
  const [keyStatusHistory, setKeyStatusHistory] = useState<KeyGenerationStatus[]>([]);
  const [discoveryHistory, setDiscoveryHistory] = useState<DeviceDiscovery[]>([]);
  const [notificationHistory, setNotificationHistory] = useState<ProvisioningNotification[]>([]);
  
  // Maps for quick lookup
  const sessionProgressMap = useRef<Map<string, ProvisioningProgress>>(new Map());
  const operationStatusMap = useRef<Map<string, KeyGenerationStatus>>(new Map());

  // WebSocket connection
  const { data, error, isConnected, reconnect } = useWebSocket<ProvisioningWebSocketData>(
    wsUrl,
    {
      reconnect: true,
      reconnectInterval,
      reconnectAttempts
    }
  );

  // Process incoming WebSocket data
  useEffect(() => {
    if (!data) return;

    const processData = (wsData: ProvisioningWebSocketData) => {
      try {
        // Validate message structure
        if (!wsData.type || !wsData.timestamp) {
          console.warn('Invalid WebSocket message structure:', wsData);
          return;
        }
        
        // 'connected' messages don't have data field, which is expected
        if (wsData.type !== 'connected' && !wsData.data) {
          console.warn('Invalid WebSocket message structure - missing data:', wsData);
          return;
        }

        // Validate timestamp
        const messageTimestamp = new Date(wsData.timestamp);
        if (isNaN(messageTimestamp.getTime())) {
          console.warn('Invalid timestamp in WebSocket message:', wsData.timestamp);
          return;
        }

        // Check if message is too old (more than 5 minutes)
        const now = new Date();
        const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
        if (messageTimestamp < fiveMinutesAgo) {
          console.warn('Ignoring old WebSocket message:', wsData);
          return;
        }

        switch (wsData.type) {
          case 'connected':
            break;
            
          case 'provisioning_progress':
            const progressData = wsData.data as ProvisioningProgress;
            
            // Validate progress data
            if (!progressData.session_id || 
                typeof progressData.progress !== 'number' ||
                progressData.progress < 0 || progressData.progress > 100) {
              console.warn('Invalid progress data:', progressData);
              return;
            }

            setLatestProgress(progressData);
            setProgressHistory(prev => {
              const newHistory = [...prev, progressData];
              return newHistory.slice(-maxHistorySize);
            });
            
            // Update session map
            sessionProgressMap.current.set(progressData.session_id, progressData);
            break;

          case 'key_generation_status':
            const keyStatusData = wsData.data as KeyGenerationStatus;
            
            // Validate key status data
            if (!keyStatusData.operation_id || 
                !keyStatusData.device_id ||
                !['started', 'completed', 'failed'].includes(keyStatusData.status)) {
              console.warn('Invalid key status data:', keyStatusData);
              return;
            }

            setLatestKeyStatus(keyStatusData);
            setKeyStatusHistory(prev => {
              const newHistory = [...prev, keyStatusData];
              return newHistory.slice(-maxHistorySize);
            });
            
            // Update operation map
            operationStatusMap.current.set(keyStatusData.operation_id, keyStatusData);
            break;

          case 'device_discovery':
            const discoveryData = wsData.data as DeviceDiscovery;
            
            // Validate discovery data
            if (!discoveryData.device_id || !discoveryData.organization_id) {
              console.warn('Invalid discovery data:', discoveryData);
              return;
            }

            setLatestDiscovery(discoveryData);
            setDiscoveryHistory(prev => {
              const newHistory = [...prev, discoveryData];
              return newHistory.slice(-maxHistorySize);
            });
            break;

          case 'notification':
            const notificationData = wsData.data as ProvisioningNotification;
            
            // Validate notification data
            if (!notificationData.id || 
                !notificationData.title || 
                !notificationData.message ||
                notificationData.type !== 'provisioning') {
              console.warn('Invalid notification data:', notificationData);
              return;
            }

            setLatestNotification(notificationData);
            setNotificationHistory(prev => {
              const newHistory = [...prev, notificationData];
              return newHistory.slice(-maxHistorySize);
            });
            break;

          default:
            console.warn('Unknown provisioning WebSocket message type:', wsData.type);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error, wsData);
      }
    };

    processData(data);
  }, [data, maxHistorySize]);

  // Connection monitoring and error recovery
  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;

    if (error && !isConnected) {
      // Log connection errors for debugging
      console.error('Provisioning WebSocket error:', error);
      
      // Clear latest data when disconnected to prevent stale data
      setLatestProgress(null);
      setLatestKeyStatus(null);
      setLatestDiscovery(null);
      setLatestNotification(null);

      // Auto-reconnect after delay if not already reconnecting
      reconnectTimer = setTimeout(() => {
        reconnect();
      }, reconnectInterval);
    }

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
    };
  }, [error, isConnected, reconnect, reconnectInterval]);

  // Periodic connection health check
  useEffect(() => {
    if (!isConnected || !wsUrl) return;

    const healthCheckInterval = setInterval(() => {
      // Send a ping message to check connection health
      // This is handled by the underlying WebSocket implementation
      console.debug('WebSocket health check - connection status:', isConnected);
    }, 30000); // Check every 30 seconds

    return () => {
      clearInterval(healthCheckInterval);
    };
  }, [isConnected, wsUrl]);

  // Clear all history
  const clearHistory = useCallback(() => {
    setProgressHistory([]);
    setKeyStatusHistory([]);
    setDiscoveryHistory([]);
    setNotificationHistory([]);
    sessionProgressMap.current.clear();
    operationStatusMap.current.clear();
  }, []);

  // Get session-specific progress
  const getSessionProgress = useCallback((sessionId: string): ProvisioningProgress | null => {
    return sessionProgressMap.current.get(sessionId) || null;
  }, []);

  // Get operation-specific status
  const getOperationStatus = useCallback((operationId: string): KeyGenerationStatus | null => {
    return operationStatusMap.current.get(operationId) || null;
  }, []);

  return {
    // Connection state
    isConnected,
    error,
    
    // Latest data
    latestProgress,
    latestKeyStatus,
    latestDiscovery,
    latestNotification,
    
    // History
    progressHistory,
    keyStatusHistory,
    discoveryHistory,
    notificationHistory,
    
    // Controls
    clearHistory,
    reconnect,
    
    // Session-specific data
    getSessionProgress,
    getOperationStatus
  };
}

// Hook for monitoring specific provisioning session
export function useProvisioningSession(
  wsUrl: string | null,
  sessionId: string | null
): {
  progress: ProvisioningProgress | null;
  isConnected: boolean;
  error: Error | null;
  reconnect: () => void;
} {
  const { 
    latestProgress, 
    getSessionProgress, 
    isConnected, 
    error, 
    reconnect 
  } = useProvisioningWebSocket(wsUrl);

  const [sessionProgress, setSessionProgress] = useState<ProvisioningProgress | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSessionProgress(null);
      return;
    }

    // Check if the latest progress is for our session
    if (latestProgress?.session_id === sessionId) {
      setSessionProgress(latestProgress);
    } else {
      // Try to get from history
      const progress = getSessionProgress(sessionId);
      setSessionProgress(progress);
    }
  }, [latestProgress, sessionId, getSessionProgress]);

  return {
    progress: sessionProgress,
    isConnected,
    error,
    reconnect
  };
}

// Hook for monitoring key generation operations
export function useKeyGenerationMonitor(
  wsUrl: string | null,
  operationId: string | null
): {
  status: KeyGenerationStatus | null;
  isConnected: boolean;
  error: Error | null;
  reconnect: () => void;
} {
  const { 
    latestKeyStatus, 
    getOperationStatus, 
    isConnected, 
    error, 
    reconnect 
  } = useProvisioningWebSocket(wsUrl);

  const [operationStatus, setOperationStatus] = useState<KeyGenerationStatus | null>(null);

  useEffect(() => {
    if (!operationId) {
      setOperationStatus(null);
      return;
    }

    // Check if the latest status is for our operation
    if (latestKeyStatus?.operation_id === operationId) {
      setOperationStatus(latestKeyStatus);
    } else {
      // Try to get from history
      const status = getOperationStatus(operationId);
      setOperationStatus(status);
    }
  }, [latestKeyStatus, operationId, getOperationStatus]);

  return {
    status: operationStatus,
    isConnected,
    error,
    reconnect
  };
}