/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { AuthTokenManager } from '@/utils/auth-token-manager';

export const downloadCertificateBundle = async (
  deviceId: string,
  fileName?: string
): Promise<void> => {
  const token = AuthTokenManager.getToken();
  
  if (!token) {
    console.error('[downloadCertificateBundle] No token available');
    throw new Error('No authentication token found');
  }
  
  const url = `/api/v1/certificates/devices/${deviceId}/certificate/download/bundle`;
  
  console.log('[downloadCertificateBundle] Downloading:', {
    deviceId,
    tokenLength: token.length,
    tokenPreview: token.substring(0, 20) + '...'
  });
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    console.error('[downloadCertificateBundle] Download failed:', {
      status: response.status,
      statusText: response.statusText,
      url
    });
    throw new Error('Download failed');
  }
  
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = fileName || `${deviceId}-certificates.zip`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
};

/**
 * Copy cURL command to clipboard
 * @param method - HTTP method
 * @param path - API path
 * @param baseUrl - Base URL for the API
 * @returns Promise that resolves when copied
 */
export const copyCurlCommand = async (
  method: string,
  path: string,
  baseUrl: string
): Promise<void> => {
  const curlCommand = `curl -X ${method} ${baseUrl}${path} \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json"`;
  
  await navigator.clipboard.writeText(curlCommand);
};

/**
 * Execute an API request
 * @param endpoint - API endpoint configuration
 * @param params - URL parameters
 * @param body - Request body (for POST/PUT requests)
 * @param baseUrl - Base URL for the API
 * @returns Promise with API response
 */
export const executeApiRequest = async (
  endpoint: any,
  params: Record<string, string>,
  body: string,
  baseUrl: string
): Promise<{
  status: number;
  headers: Record<string, string>;
  data: any;
  timing: number;
}> => {
  const token = AuthTokenManager.getToken();
  let url = endpoint.path;
  
  // Replace path parameters
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url = url.replace(`{${key}}`, value);
    });
  }
  
  const startTime = Date.now();
  
  try {
    const response = await fetch(baseUrl + url, {
      method: endpoint.method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: endpoint.method !== 'GET' && body ? body : undefined
    });
    
    const timing = Date.now() - startTime;
    const data = await response.json();
    
    return {
      status: response.status,
      headers: Object.fromEntries(response.headers.entries()),
      data,
      timing
    };
  } catch (error: any) {
    return {
      status: 0,
      headers: {},
      data: { error: error.message },
      timing: 0
    };
  }
};

/**
 * Format bytes to human readable size
 * @param bytes - Number of bytes
 * @returns Formatted string with size unit
 */
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
