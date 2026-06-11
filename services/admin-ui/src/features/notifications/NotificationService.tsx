/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Notification Service
 * Full-featured notification system with real-time updates
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { tesaApi } from '@/services/api/tesaApi';
import { useAuth } from '@/hooks/useAuth';
import { AuthTokenManager } from '@/utils/auth-token-manager';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'device' | 'system' | 'security';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
  actionLabel?: string;
  metadata?: Record<string, unknown>;
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (id: string) => void;
  clearAll: () => void;
  refreshNotifications: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

type APINotification = {
  id?: string;
  type?: string;
  title?: string;
  message?: string;
  created_at?: string;
  timestamp?: string;
  status?: string;
  actionUrl?: string;
  actionLabel?: string;
  metadata?: Record<string, unknown>;
  priority?: Notification['priority'];
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    // PRODUCTION FIX: Return safe defaults instead of crashing
    console.warn('useNotifications called outside NotificationProvider - using defaults');
    return {
      notifications: [],
      unreadCount: 0,
      markAsRead: () => {},
      markAllAsRead: () => {},
      deleteNotification: () => {},
      clearAll: () => {},
    };
  }
  return context;
};

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  // WebSocket temporarily disabled - uncomment when backend endpoint is available
  // const [ws, setWs] = useState<WebSocket | null>(null);
  const { isAuthenticated, user } = useAuth();
  const notificationsWsEnabled = import.meta.env.VITE_NOTIFICATIONS_WS_ENABLED === 'true';

  // Calculate unread count
  const unreadCount = notifications.filter(n => !n.read).length;

  const mapToNotification = useCallback((raw: APINotification): Notification => ({
    id: raw.id || `notif-${Date.now()}`,
    type: (raw.type || 'info') as Notification['type'],
    title: raw.title || 'Notification',
    message: raw.message || '',
    timestamp: new Date(raw.created_at || raw.timestamp || Date.now()),
    read: (raw.status || 'unread') !== 'unread',
    actionUrl: raw.actionUrl,
    actionLabel: raw.actionLabel,
    metadata: raw.metadata,
    priority: raw.priority || 'medium'
  }), []);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);

  // Handle incoming real-time notification
  const handleIncomingNotification = useCallback((data: APINotification) => {
    const notification = mapToNotification(data);

    setNotifications(prev => [notification, ...prev]);

    // Show toast for high priority notifications
    if (notification.priority === 'high' || notification.priority === 'critical') {
      toast[notification.type === 'error' ? 'error' : notification.type](
        notification.title,
        {
          description: notification.message,
          duration: 5000,
          action: notification.actionUrl ? {
            label: notification.actionLabel || 'View',
            onClick: () => window.location.href = notification.actionUrl!
          } : undefined
        }
      );
    }
  }, [mapToNotification]);

  const establishConnection = useCallback(() => {
    if (!notificationsWsEnabled) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    if (!isAuthenticated) {
      return;
    }

    const token = AuthTokenManager.getToken();
    if (!token) {
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = new URL(`${protocol}//${window.location.host}/ws/notifications`);
    url.searchParams.set('token', token);

    try {
      const websocket = new WebSocket(url.toString());
      wsRef.current = websocket;

      websocket.onopen = () => {
        console.debug('Notification WebSocket connected');
      };

      websocket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string;
            data?: APINotification;
            notifications?: APINotification[];
            message?: string;
          };

          if (payload.type === 'notification' && payload.data) {
            handleIncomingNotification(payload.data);
          } else if ((payload.type === 'init' || payload.type === 'refresh') && Array.isArray(payload.notifications)) {
            setNotifications(payload.notifications.map(mapToNotification));
          } else if (payload.type === 'error') {
            console.warn('Notification stream error', payload.message);
          }
        } catch (err) {
          console.error('Failed to parse notification payload:', err);
        }
      };

      websocket.onerror = (error) => {
        console.error('Notification WebSocket error:', error);
      };

      websocket.onclose = () => {
        wsRef.current = null;
        if (reconnectTimer.current) {
          window.clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
        if (isAuthenticated) {
          reconnectTimer.current = window.setTimeout(establishConnection, 5000);
        }
      };
    } catch (error) {
      console.error('Failed to create notification WebSocket:', error);
    }
  }, [isAuthenticated, handleIncomingNotification, mapToNotification, notificationsWsEnabled]);

  useEffect(() => {
    if (!notificationsWsEnabled) {
      return;
    }
    establishConnection();

    return () => {
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [establishConnection, notificationsWsEnabled]);

  // Load notifications from API
  const refreshNotifications = useCallback(async () => {
    // Only fetch notifications if user is authenticated AND user data is loaded
    if (!isAuthenticated || !user) {
      return;
    }
    
    try {
      const response = await tesaApi.getNotifications();
      const apiNotifications = (response.notifications || []) as APINotification[];
      setNotifications(apiNotifications.map(mapToNotification));
    } catch (error) {
      // Only log errors if we're authenticated (avoid 401 errors on sign-in page)
      if (isAuthenticated && user) {
        console.error('Failed to load notifications:', error);
      }
    }
  }, [isAuthenticated, user, mapToNotification]);

  // Load initial notifications
  useEffect(() => {
    // Only fetch if both authenticated AND user data is loaded
    if (isAuthenticated && user) {
      refreshNotifications();
    }
  }, [refreshNotifications, isAuthenticated, user]);

  // Add notification manually
  const addNotification = useCallback((
    notification: Omit<Notification, 'id' | 'timestamp' | 'read'>
  ) => {
    handleIncomingNotification({
      ...notification,
      id: `notif-${Date.now()}`,
      timestamp: new Date(),
      read: false
    });
  }, [handleIncomingNotification]);

  // Mark notification as read
  const markAsRead = useCallback(async (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
    
    try {
      await tesaApi.markNotificationAsRead(id);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    setNotifications(prev => 
      prev.map(n => ({ ...n, read: true }))
    );
    
    try {
      await tesaApi.markAllNotificationsAsRead();
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  }, []);

  // Delete notification
  const deleteNotification = useCallback(async (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
    
    try {
      await tesaApi.deleteNotification(id);
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  }, []);

  // Clear all notifications
  const clearAll = useCallback(async () => {
    setNotifications([]);
    
    try {
      await tesaApi.clearAllNotifications();
    } catch (error) {
      console.error('Failed to clear notifications:', error);
    }
  }, []);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    refreshNotifications
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

// Helper function to create notification
export const createNotification = (
  type: Notification['type'],
  title: string,
  message: string,
  options?: Partial<Omit<Notification, 'id' | 'type' | 'title' | 'message' | 'timestamp' | 'read'>>
): Omit<Notification, 'id' | 'timestamp' | 'read'> => {
  return {
    type,
    title,
    message,
    ...options
  };
};
