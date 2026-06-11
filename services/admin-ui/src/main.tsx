/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import './css/styles.css';
import './css/sidebar-enhancements.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

// Import auth test utility (only in development)
if (import.meta.env.DEV) {
  import('./utils/auth-test');
}

// Global error handler for [object Object] URLs
const originalFetch = window.fetch;
window.fetch = function(...args) {
  const url = args[0];
  if (typeof url === 'string' && (url.includes('[object') || url === '[object Object]')) {
    console.warn('Blocked invalid fetch request:', url);
    return Promise.reject(new Error('Invalid URL: ' + url));
  }
  return originalFetch.apply(this, args);
};

// Intercept image loading errors
if (typeof window !== 'undefined') {
  window.addEventListener('error', (e) => {
    if (e.target && (e.target as any).tagName === 'IMG') {
      const img = e.target as HTMLImageElement;
      if (img.src && (img.src.includes('[object') || img.src.endsWith('[object Object]'))) {
        console.warn('Blocked invalid image load:', img.src);
        img.src = ''; // Clear the invalid source
        e.preventDefault();
      }
    }
  }, true);
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
