/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface SSEOptions {
  enabled?: boolean;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  withCredentials?: boolean;
}

interface SSEHook<T = any> {
  data: T | null;
  error: Error | null;
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastEventId: string | null;
  close: () => void;
  reconnect: () => void;
}

export function useServerSentEvents<T = any>(
  url: string | null,
  options: SSEOptions = {}
): SSEHook<T> {
  const {
    enabled = true,
    reconnect = true,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
    withCredentials = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  
  const eventSource = useRef<EventSource | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const isMounted = useRef(true);

  const connect = useCallback(() => {
    if (!url || !enabled || !isMounted.current) return;

    try {
      setConnectionState('connecting');
      setError(null);

      // Close existing connection
      if (eventSource.current) {
        eventSource.current.close();
      }

      // Create new EventSource connection with enhanced authentication
      const eventSourceUrl = new URL(url, window.location.origin);
      
      // Add authentication token - try multiple storage keys as fallback
      const token = localStorage.getItem('jwt_token') || 
                   localStorage.getItem('access_token') || 
                   localStorage.getItem('auth_token') ||
                   sessionStorage.getItem('jwt_token') ||
                   sessionStorage.getItem('access_token');
      
      if (token && token.trim() !== '') {
        // For SSE, we need to pass the token as a query parameter since 
        // EventSource doesn't support custom headers
        eventSourceUrl.searchParams.set('token', token);
        console.debug('SSE Connection: Using token for', url, 'Token length:', token.length);
      } else {
        console.warn('SSE Connection: No valid token found for', url);
        // Still try to connect without token in case endpoint allows anonymous access
      }

      // Add timestamp to prevent caching issues
      eventSourceUrl.searchParams.set('_t', Date.now().toString());

      eventSource.current = new EventSource(eventSourceUrl.toString(), {
        withCredentials
      });

      eventSource.current.onopen = () => {
        console.log('SSE connected to:', url);
        setIsConnected(true);
        setConnectionState('connected');
        setError(null);
        reconnectCount.current = 0;
      };

      eventSource.current.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
          if (event.lastEventId) {
            setLastEventId(event.lastEventId);
          }
        } catch (err) {
          console.error('Failed to parse SSE message:', err, 'Raw data:', event.data);
        }
      };

      // Handle custom events (like system-health-update, predictive-alerts-update, etc.)
      const handleCustomEvent = (event: MessageEvent) => {
        try {
          // Check if the data is already an object (from error events)
          const parsedData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
          
          // Handle error events specially - check parsedData exists before accessing properties
          if (event.type === 'error' && parsedData && parsedData.error) {
            console.error('SSE error event:', parsedData.error);
            if (parsedData.code === 401) {
              // Authentication error - don't retry immediately
              setError(new Error(parsedData.error));
              setConnectionState('error');
              return;
            }
          }
          
          // Only set data if parsedData is not null/undefined
          if (parsedData !== null && parsedData !== undefined) {
            setData(parsedData);
          }
          
          if (event.lastEventId) {
            setLastEventId(event.lastEventId);
          }
        } catch (err) {
          // Only log parse errors if it's not an authentication error response
          if (!event.data?.includes('Authentication required') && !event.data?.includes('Invalid authentication token')) {
            console.error('Failed to parse custom SSE event:', err);
          }
        }
      };

      // Add listeners for specific event types
      const eventTypes = [
        'system-health-update',
        'predictive-alerts-update', 
        'anomaly-detection-update',
        'resource-optimization-update',
        'defense-update',  // Added for defense-in-depth
        'connected',
        'ping',
        'error'
      ];

      eventTypes.forEach(eventType => {
        eventSource.current?.addEventListener(eventType, handleCustomEvent);
      });

      eventSource.current.onerror = (event) => {
        // Check if the page is unloading - don't log errors during page navigation
        if (document.visibilityState === 'hidden' || window.performance.navigation.type === 1) {
          // Page is being refreshed or navigated away - this is normal
          return;
        }
        
        console.error('SSE error:', event);
        setIsConnected(false);
        setConnectionState('error');
        
        // Enhanced error handling with authentication context
        let errorMessage = 'Connection error occurred';
        const errorDetails = {
          url: eventSourceUrl.toString(),
          readyState: eventSource.current?.readyState,
          readyStateText: eventSource.current?.readyState === 0 ? 'CONNECTING' : 
                         eventSource.current?.readyState === 1 ? 'OPEN' : 
                         eventSource.current?.readyState === 2 ? 'CLOSED' : 'UNKNOWN'
        };
        
        if (eventSource.current?.readyState === EventSource.CLOSED) {
          errorMessage = 'Connection closed by server';
          // Check if this might be a 401 Unauthorized by looking at console errors
          const recentErrors = console.error.toString();
          if (recentErrors.includes('401') || recentErrors.includes('Unauthorized')) {
            errorMessage = 'Authentication failed - token may be expired';
          }
        } else if (eventSource.current?.readyState === EventSource.CONNECTING) {
          // Check if it might be an authentication issue
          const token = localStorage.getItem('jwt_token') || 
                       localStorage.getItem('access_token') ||
                       sessionStorage.getItem('jwt_token');
          if (!token) {
            errorMessage = 'Authentication required - no token found';
          } else {
            errorMessage = 'Failed to connect - possible authentication or network error';
          }
        }
        
        console.warn('SSE Error Details:', errorMessage, errorDetails);
        setError(new Error(errorMessage));
        
        // Attempt reconnection if enabled
        if (reconnect && reconnectCount.current < reconnectAttempts && isMounted.current) {
          const backoffTime = Math.min(reconnectInterval * Math.pow(2, reconnectCount.current), 30000);
          console.log(`SSE reconnecting in ${backoffTime}ms... (attempt ${reconnectCount.current + 1}/${reconnectAttempts})`);
          
          reconnectTimeout.current = setTimeout(() => {
            reconnectCount.current++;
            connect();
          }, backoffTime);
        } else {
          setConnectionState('disconnected');
          if (reconnectCount.current >= reconnectAttempts) {
            console.error('SSE: Max reconnection attempts reached');
          }
        }
      };

    } catch (err) {
      setError(err as Error);
      setConnectionState('error');
    }
  }, [url, enabled, reconnect, reconnectAttempts, reconnectInterval, withCredentials]);

  const close = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    if (eventSource.current) {
      eventSource.current.close();
      eventSource.current = null;
    }
    setIsConnected(false);
    setConnectionState('disconnected');
  }, []);

  const manualReconnect = useCallback(() => {
    close();
    reconnectCount.current = 0;
    connect();
  }, [close, connect]);

  useEffect(() => {
    isMounted.current = true;
    
    if (url && enabled) {
      connect();
    }

    return () => {
      isMounted.current = false;
      close();
    };
  }, [url, enabled, connect, close]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
      close();
    };
  }, []);

  return {
    data,
    error,
    isConnected,
    connectionState,
    lastEventId,
    close,
    reconnect: manualReconnect,
  };
}