/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { AuthTokenManager } from './auth-token-manager';

export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  // Use AuthTokenManager to get token from any location (jwt_token, access_token, etc.)
  const token = AuthTokenManager.getToken();
  
  if (!token) {
    console.error('[authFetch] No authentication token found for request:', url);
    throw new Error('No authentication token found');
  }

  // Keep URLs as-is when accessed through NGINX (port 80/443)
  // Only add hostname for absolute paths without domain
  let fullUrl = url;
  if (url.startsWith('/api/') && !window.location.port && window.location.protocol === 'https:') {
    // Already proxied through NGINX, use as-is
    fullUrl = url;
  } else if (url.startsWith('/')) {
    // For development or direct access
    fullUrl = url;
  }

  // Merge headers with auth token
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
  };

  // Add Content-Type if not present and body exists
  // IMPORTANT: Do NOT set Content-Type for FormData - browser sets it automatically
  // with correct multipart/form-data boundary
  if (options.body && !headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Debug logging for certificate downloads
  if (url.includes('certificate/download')) {
    console.log('[authFetch] Certificate download request:', {
      url: fullUrl,
      tokenLength: token.length,
      tokenPreview: token.substring(0, 20) + '...',
      headers: headers
    });
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
  });

  // Log 401 errors with more detail
  if (response.status === 401) {
    console.error('[authFetch] 401 Unauthorized:', {
      url: fullUrl,
      tokenLength: token.length,
      tokenPreview: token.substring(0, 20) + '...',
      responseHeaders: Object.fromEntries(response.headers.entries())
    });
  }

  return response;
}

export default authFetch;