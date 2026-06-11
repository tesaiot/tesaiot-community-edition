/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface NotificationOptions {
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  duration?: number; // milliseconds, 0 = no auto-hide
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Simple console-based notification for now
// Can be replaced with toast notifications or other UI components
export function showNotification(options: NotificationOptions) {
  const { type, title, message, action } = options;
  
  // Log to console
  const logMethod = type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'log';
  console[logMethod](`[${type.toUpperCase()}] ${title}: ${message}`);
  
  // If there's an action and we're in a browser environment
  if (action && typeof window !== 'undefined') {
    // Create a simple notification banner
    const existingBanner = document.getElementById('version-notification-banner');
    if (existingBanner) {
      existingBanner.remove();
    }
    
    const banner = document.createElement('div');
    banner.id = 'version-notification-banner';
    banner.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
      z-index: 9999;
      display: flex;
      align-items: center;
      gap: 16px;
      max-width: 400px;
      animation: slideIn 0.3s ease-out;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = 'flex: 1;';
    content.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
      <div style="font-size: 14px;">${message}</div>
    `;
    banner.appendChild(content);
    
    if (action) {
      const button = document.createElement('button');
      button.textContent = action.label;
      button.style.cssText = `
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s;
      `;
      button.onmouseover = () => {
        button.style.background = 'rgba(255, 255, 255, 0.3)';
      };
      button.onmouseout = () => {
        button.style.background = 'rgba(255, 255, 255, 0.2)';
      };
      button.onclick = () => {
        action.onClick();
        banner.remove();
      };
      banner.appendChild(button);
    }
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.innerHTML = '×';
    closeButton.style.cssText = `
      background: none;
      border: none;
      color: white;
      font-size: 24px;
      cursor: pointer;
      padding: 0;
      margin-left: 8px;
      line-height: 1;
    `;
    closeButton.onclick = () => banner.remove();
    banner.appendChild(closeButton);
    
    // Add animation keyframes
    if (!document.getElementById('notification-animations')) {
      const style = document.createElement('style');
      style.id = 'notification-animations';
      style.textContent = `
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(banner);
    
    // Auto-hide if duration is specified
    if (options.duration && options.duration > 0) {
      setTimeout(() => {
        if (document.getElementById('version-notification-banner') === banner) {
          banner.remove();
        }
      }, options.duration);
    }
  }
}