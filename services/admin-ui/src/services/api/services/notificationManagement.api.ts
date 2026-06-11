/**
 * Notification Management API Service
 *
 * Service class for notification management and user preferences operations.
 * All methods delegate to REST API endpoints for notification CRUD and preferences.
 *
 * @module NotificationManagementApiService
 * @version 2025.10
 * @status Phase 2 - Day 9
 */

import type { AxiosInstance } from 'axios';
import type {
  // Request types
  GetNotificationsParams,
  GetArchivedNotificationsParams,
  UpdateNotificationRequest,
  BulkNotificationActionRequest,
  SendTestNotificationRequest,
  UpdateNotificationPreferencesRequest,
  // Response types
  NotificationListResponse,
  NotificationStatsResponse,
  UnreadCountResponse,
  MarkNotificationReadResponse,
  MarkAllNotificationsReadResponse,
  BulkNotificationActionResponse,
  UpdateNotificationResponse,
  DeleteNotificationResponse,
  ArchivedNotificationListResponse,
  NotificationPreferencesResponse,
  UpdateNotificationPreferencesResponse,
  SendTestNotificationResponse,
} from '../types/notificationManagement.types';

export class NotificationManagementApiService {
  constructor(private api: AxiosInstance) {}

  /**
   * Get notifications with optional filters
   * @param params - Filter parameters (limit, offset, status)
   */
  async getNotifications(
    params?: GetNotificationsParams
  ): Promise<NotificationListResponse> {
    const response = await this.api.get('/api/v1/notifications', { params });
    return response.data;
  }

  /**
   * Get notification statistics
   */
  async getNotificationStats(): Promise<NotificationStatsResponse> {
    const response = await this.api.get('/api/v1/notifications/stats');
    return response.data;
  }

  /**
   * Get unread notification count
   */
  async getUnreadCount(): Promise<UnreadCountResponse> {
    const response = await this.api.get('/api/v1/notifications/unread/count');
    return response.data;
  }

  /**
   * Mark a single notification as read
   * @param notificationId - Notification ID to mark as read
   */
  async markNotificationAsRead(
    notificationId: string
  ): Promise<MarkNotificationReadResponse> {
    const response = await this.api.post(
      `/api/v1/notifications/${notificationId}/read`
    );
    return response.data;
  }

  /**
   * Mark all notifications as read
   */
  async markAllNotificationsAsRead(): Promise<MarkAllNotificationsReadResponse> {
    const response = await this.api.post('/api/v1/notifications/mark-all-read');
    return response.data;
  }

  /**
   * Perform bulk action on notifications
   * @param data - Bulk action request (action type and optional notification IDs)
   */
  async bulkNotificationAction(
    data: BulkNotificationActionRequest
  ): Promise<BulkNotificationActionResponse> {
    const response = await this.api.post('/api/v1/notifications/bulk', data);
    return response.data;
  }

  /**
   * Update notification status
   * @param notificationId - Notification ID to update
   * @param data - Update request (action: read/unread/archive)
   */
  async updateNotification(
    notificationId: string,
    data: UpdateNotificationRequest
  ): Promise<UpdateNotificationResponse> {
    const response = await this.api.put(
      `/api/v1/notifications/${notificationId}`,
      data
    );
    return response.data;
  }

  /**
   * Delete a notification
   * @param notificationId - Notification ID to delete
   */
  async deleteNotification(
    notificationId: string
  ): Promise<DeleteNotificationResponse> {
    const response = await this.api.delete(
      `/api/v1/notifications/${notificationId}`
    );
    return response.data;
  }

  /**
   * Get archived notifications
   * @param params - Pagination parameters
   */
  async getArchivedNotifications(
    params?: GetArchivedNotificationsParams
  ): Promise<ArchivedNotificationListResponse> {
    const response = await this.api.get('/api/v1/notifications/archived', {
      params,
    });
    return response.data;
  }

  /**
   * Get notification preferences
   */
  async getNotificationPreferences(): Promise<NotificationPreferencesResponse> {
    const response = await this.api.get('/api/v1/notifications/preferences');
    return response.data;
  }

  /**
   * Update notification preferences
   * @param preferences - Preferences to update (email, push, webhook, categories, quiet_hours)
   */
  async updateNotificationPreferences(
    preferences: UpdateNotificationPreferencesRequest
  ): Promise<UpdateNotificationPreferencesResponse> {
    const response = await this.api.put(
      '/api/v1/notifications/preferences',
      preferences
    );
    return response.data;
  }

  /**
   * Send test notification
   * @param data - Optional test notification type
   */
  async sendTestNotification(
    data?: SendTestNotificationRequest
  ): Promise<SendTestNotificationResponse> {
    const response = await this.api.post('/api/v1/notifications/test', data);
    return response.data;
  }
}
