/**
 * Notification Management Types
 *
 * Type definitions for notification management and user preferences operations.
 *
 * @module NotificationManagementTypes
 * @version 2025.10
 * @status Phase 2 - Day 9
 */

// ============================================================================
// Core Notification Types
// ============================================================================

export type NotificationStatus = 'read' | 'unread';
export type NotificationPriority = 'low' | 'medium' | 'high';
export type NotificationAction = 'read' | 'unread' | 'archive';
export type BulkNotificationAction = 'mark_read' | 'mark_unread' | 'delete' | 'archive' | 'archive_all' | 'markAllRead' | 'archiveAll';

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  status: NotificationStatus;
  priority: NotificationPriority;
  archived: boolean;
  created_at: string;
  read_at?: string;
  archived_at?: string;
}

// ============================================================================
// Request Types
// ============================================================================

export interface GetNotificationsParams {
  limit?: number;
  offset?: number;
  status?: 'all' | 'unread' | 'read';
}

export interface GetArchivedNotificationsParams {
  limit?: number;
  offset?: number;
}

export interface UpdateNotificationRequest {
  action: NotificationAction;
}

export interface BulkNotificationActionRequest {
  action: BulkNotificationAction;
  notification_ids?: string[];
}

export interface SendTestNotificationRequest {
  type?: string;
}

// ============================================================================
// Notification Preferences Types
// ============================================================================

export interface QuietHours {
  enabled: boolean;
  start_time: string;
  end_time: string;
  timezone: string;
}

export interface NotificationPreferences {
  email_notifications: boolean;
  push_notifications: boolean;
  webhook_notifications: boolean;
  categories: Record<string, boolean>;
  quiet_hours: QuietHours;
}

export interface UpdateNotificationPreferencesRequest {
  email_notifications?: boolean;
  push_notifications?: boolean;
  webhook_notifications?: boolean;
  categories?: Record<string, boolean>;
  quiet_hours?: QuietHours;
}

// ============================================================================
// Response Types
// ============================================================================

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface NotificationListResponse {
  notifications: Notification[];
  pagination: Pagination;
}

export interface NotificationStatsResponse {
  total: number;
  unread: number;
  read: number;
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface UnreadCountResponse {
  count: number;
}

export interface MarkNotificationReadResponse {
  success: boolean;
  message: string;
  notification_id: string;
  read_at: string;
}

export interface MarkAllNotificationsReadResponse {
  success: boolean;
  message: string;
  marked_count: number;
  read_at: string;
}

export interface BulkNotificationActionResponse {
  success: boolean;
  message: string;
  action: string;
  affected_count: number;
  notification_ids?: string[];
  read_at?: string;
  archived_at?: string;
}

export interface UpdateNotificationResponse {
  success: boolean;
  notification_id: string;
  status?: string;
  archived?: boolean;
  read_at?: string;
  archived_at?: string;
  message: string;
}

export interface DeleteNotificationResponse {
  success: boolean;
  notification_id: string;
  message: string;
}

export interface ArchivedNotificationListResponse {
  notifications: Notification[];
  pagination: Pagination;
}

export interface NotificationPreferencesResponse {
  email_notifications: boolean;
  push_notifications: boolean;
  webhook_notifications: boolean;
  categories: Record<string, boolean>;
  quiet_hours: QuietHours;
}

export interface UpdateNotificationPreferencesResponse {
  success: boolean;
  message: string;
  preferences: NotificationPreferences;
}

export interface SendTestNotificationResponse {
  success: boolean;
  message: string;
  type: string;
  sent_at: string;
}
