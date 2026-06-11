/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { formatDistanceToNow } from 'date-fns';

/**
 * Format a date to relative time with proper null/undefined handling
 * @param date - The date to format (can be null, undefined, string, or Date)
 * @returns Formatted relative time string or "Never" for null/undefined
 */
export function formatRelativeTime(date: Date | string | null | undefined): string {
  // Handle null or undefined
  if (!date) {
    return 'Never';
  }

  try {
    // Convert to Date object if it's a string
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    // Check if it's a valid date
    if (isNaN(dateObj.getTime())) {
      return 'Never';
    }
    
    // Check if date is Unix epoch (1970-01-01) or very close to it
    // This handles cases where null/undefined was converted to 0 timestamp
    if (dateObj.getTime() < 86400000) { // Less than 1 day from epoch
      return 'Never';
    }
    
    return formatDistanceToNow(dateObj, { addSuffix: true });
  } catch (error) {
    console.error('Error formatting date:', error);
    return 'Never';
  }
}

/**
 * Format a date to relative time with timezone indicator
 * @param date - The date to format (can be null, undefined, string, or Date)
 * @returns Formatted relative time string with timezone or "Never" for null/undefined
 */
export function formatRelativeTimeWithTimezone(date: Date | string | null | undefined): string {
  // Handle null or undefined
  if (!date) {
    return 'Never';
  }

  try {
    // Convert to Date object if it's a string
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    // Check if it's a valid date
    if (isNaN(dateObj.getTime())) {
      return 'Never';
    }
    
    // Check if date is Unix epoch (1970-01-01) or very close to it
    if (dateObj.getTime() < 86400000) { // Less than 1 day from epoch
      return 'Never';
    }
    
    // Get relative time
    const relativeTime = formatDistanceToNow(dateObj, { addSuffix: true });
    
    // Get timezone abbreviation using browser's timezone detection
    // This automatically shows the user's local timezone (PST, EST, JST, GMT+7, etc.)
    const timezone = Intl.DateTimeFormat(undefined, {
      timeZoneName: 'short'
    }).formatToParts(dateObj).find(part => part.type === 'timeZoneName')?.value || 'Local';

    return `${relativeTime} (${timezone})`;
  } catch (error) {
    console.error('Error formatting date with timezone:', error);
    return 'Never';
  }
}

/**
 * Format a date to local time string with proper null/undefined handling
 * @param date - The date to format (can be null, undefined, string, or Date)
 * @returns Formatted local time string or "Never" for null/undefined
 */
export function formatLocalDateTime(date: Date | string | null | undefined): string {
  // Handle null or undefined
  if (!date) {
    return 'Never';
  }

  try {
    // Convert to Date object if it's a string
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    // Check if it's a valid date
    if (isNaN(dateObj.getTime())) {
      return 'Never';
    }
    
    // Check if date is Unix epoch (1970-01-01) or very close to it
    if (dateObj.getTime() < 86400000) {
      return 'Never';
    }
    
    // Format with browser's local timezone
    let formatted = dateObj.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
    
    // Display browser's native timezone (PST, EST, JST, GMT+7, etc.)
    // Previously converted to ICT for Thailand, now shows user's actual timezone
    
    return formatted;
  } catch (error) {
    console.error('Error formatting local date:', error);
    return 'Never';
  }
}

/**
 * Get tooltip text for date display (exact timestamp in local timezone)
 * @param date - The date for tooltip
 * @returns Formatted tooltip text
 */
export function getDateTooltipText(date: Date | string | null | undefined): string {
  if (!date || !isValidDate(date)) {
    return 'Device has never connected to the platform';
  }
  
  const formattedDate = formatLocalDateTime(date);
  return `Last seen: ${formattedDate}`;
}

/**
 * Check if a date is valid and not null/undefined
 * @param date - The date to check
 * @returns true if date is valid, false otherwise
 */
export function isValidDate(date: Date | string | null | undefined): boolean {
  if (!date) {
    return false;
  }
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return !isNaN(dateObj.getTime()) && dateObj.getTime() > 86400000; // After Unix epoch
  } catch {
    return false;
  }
}

/**
 * Format data rate for display
 * @param messagesPerMinute - Number of messages per minute
 * @param isOnline - Whether device is online
 * @returns Formatted data rate string
 */
export function formatDataRate(messagesPerMinute: number | undefined, isOnline: boolean): string {
  if (!isOnline || messagesPerMinute === undefined || messagesPerMinute === null) {
    return '-';
  }
  
  // Handle very high rates
  if (messagesPerMinute >= 60) {
    const messagesPerSecond = (messagesPerMinute / 60).toFixed(1);
    return `${messagesPerSecond} msg/sec`;
  }
  
  // Handle normal rates
  if (messagesPerMinute >= 1) {
    return `${messagesPerMinute} msg/min`;
  }
  
  // Handle low rates (less than 1 per minute)
  if (messagesPerMinute > 0) {
    const minutesPerMessage = Math.round(1 / messagesPerMinute);
    return `1 msg/${minutesPerMessage}min`;
  }
  
  return '0 msg/min';
}

/**
 * Get tooltip text for data rate
 * @param messagesPerMinute - Number of messages per minute
 * @param isOnline - Whether device is online
 * @returns Tooltip text for data rate
 */
export function getDataRateTooltip(messagesPerMinute: number | undefined, isOnline: boolean): string {
  if (!isOnline) {
    return 'Device is offline - no data transmission';
  }
  
  if (messagesPerMinute === undefined || messagesPerMinute === null) {
    return 'Data rate information not available';
  }
  
  if (messagesPerMinute === 0) {
    return 'No telemetry messages received in the last minute';
  }
  
  if (messagesPerMinute >= 60) {
    const messagesPerSecond = (messagesPerMinute / 60).toFixed(2);
    return `High frequency: ${messagesPerSecond} messages per second (${messagesPerMinute} messages per minute)`;
  }
  
  if (messagesPerMinute >= 1) {
    return `Receiving ${messagesPerMinute} telemetry messages per minute`;
  }
  
  const minutesPerMessage = Math.round(1 / messagesPerMinute);
  return `Low frequency: approximately 1 message every ${minutesPerMessage} minutes`;
}