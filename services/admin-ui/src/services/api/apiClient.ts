/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * API Client Service
 * 
 * Centralized API client for making HTTP requests to the backend.
 * Handles authentication, error handling, and request/response interceptors.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { AuthTokenManager } from '@/utils/auth-token-manager';
// import { APIDebugger } from '@/utils/debug-api';  // Moved to /tmp/ for cleanup

/**
 * API configuration
 */
// Dynamically determine API URL based on current host
const getApiUrl = () => {
  let baseURL = import.meta.env.VITE_API_URL || '';
  
  // If no explicit URL or it's localhost, use current host
  if (!baseURL || baseURL.includes('localhost')) {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // If accessed through port 80 (NGINX), use the same origin
    // This ensures API calls go through NGINX proxy at /api/
    if (!port || port === '80' || port === '443') {
      baseURL = ''; // Empty string means same origin
    } else {
      // Otherwise use the current port (e.g., when accessing directly on 5566)
      baseURL = `${protocol}//${hostname}:${port}`;
    }
  }
  
  return baseURL;
};

const API_CONFIG = {
  baseURL: getApiUrl(),
  timeout: 60000, // Increased from 30s to 60s for activity logs endpoint
  headers: {
    'Content-Type': 'application/json'
  }
};

/**
 * Create axios instance with default configuration
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create(API_CONFIG);

  // Request interceptor - add authentication token
  client.interceptors.request.use(
    (config) => {
      // Get token using AuthTokenManager for consistency
      const token = AuthTokenManager.getToken();
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.debug('[apiClient] Request with auth:', config.url);
      } else {
        console.debug('[apiClient] Request without auth:', config.url);
      }

      // Add request ID for tracking
      config.headers['X-Request-ID'] = generateRequestId();
      
      // Debug logging
      // APIDebugger.logRequest(config);  // Debug utility moved to /tmp/

      return config;
    },
    (error) => {
      console.error('Request interceptor error:', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor - handle errors globally
  client.interceptors.response.use(
    (response) => {
      // Successful response
      // APIDebugger.logResponse(response);  // Debug utility moved to /tmp/
      return response;
    },
    async (error: AxiosError) => {
      // Handle different error scenarios
      if (error.response) {
        const status = error.response.status;
        const contentType = error.response.headers?.['content-type'] || '';
        
        // Check if response is HTML instead of JSON
        if (contentType.includes('text/html')) {
          console.error('[apiClient] Received HTML response instead of JSON:', {
            url: error.config?.url,
            status,
            contentType
          });
          
          // Create a proper error object
          const htmlError = new Error(
            status === 401 ? 'Authentication required. Please log in.' :
            status === 403 ? 'Access denied.' :
            status === 404 ? 'Resource not found.' :
            status >= 500 ? 'Server error. Please try again later.' :
            `Unexpected response (${status})`
          );
          (htmlError as any).status = status;
          (htmlError as any).isHtmlResponse = true;
          
          if (status === 401) {
            handleUnauthorized();
          }
          
          return Promise.reject(htmlError);
        }
        
        // Handle JSON responses
        switch (status) {
          case 401:
            // Unauthorized - redirect to login
            handleUnauthorized();
            break;
          case 403:
            // Forbidden - show permission error
            showError('You do not have permission to perform this action');
            break;
          case 404:
            // Not found
            showError('The requested resource was not found');
            break;
          case 429:
            // Rate limited
            showError('Too many requests. Please try again later');
            break;
          case 500:
            // Server error
            showError('An internal server error occurred');
            break;
          default:
            // Other errors
            const message = (error.response.data as any)?.message || 'An error occurred';
            showError(message);
        }
      } else if (error.request) {
        // Request made but no response (includes timeouts)
        console.error('[apiClient] No response received:', error.request);
        if (error.code === 'ECONNABORTED') {
          // Specific handling for timeout errors
          showError('Request timed out. The server may be processing large amounts of data. Please try with smaller date ranges or contact support.');
        } else {
          showError('Unable to connect to the server. Please check your connection');
        }
      } else {
        // Request setup error
        console.error('[apiClient] Request setup error:', error.message);
        showError('An error occurred while setting up the request');
      }

      // APIDebugger.logError(error);  // Debug utility moved to /tmp/
      return Promise.reject(error);
    }
  );

  return client;
};

/**
 * Generate unique request ID for tracking
 */
const generateRequestId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Handle unauthorized responses
 */
const handleUnauthorized = () => {
  console.warn('[apiClient] Handling 401 Unauthorized');
  
  // Clear auth data using AuthTokenManager
  AuthTokenManager.clearTokens();
  localStorage.removeItem('user');
  
  // Only redirect if we're not already on the login page
  if (!window.location.pathname.includes('/login') && 
      !window.location.pathname.includes('/signin') &&
      !window.location.pathname.includes('/auth')) {
    console.log('[apiClient] Redirecting to login...');
    window.location.href = '/login';
  }
};

/**
 * Show error message (in a real app, use toast notifications)
 */
const showError = (message: string) => {
  console.error('API Error:', message);
  // In a real app, show toast notification
  // toast.error(message);
};

/**
 * API client instance
 */
export const apiClient = createApiClient();

/**
 * Convenience methods for common HTTP operations
 */
export const api = {
  get: <T = any>(url: string, config?: any) => 
    apiClient.get<T>(url, config).then(res => res.data),
    
  post: <T = any>(url: string, data?: any, config?: any) => 
    apiClient.post<T>(url, data, config).then(res => res.data),
    
  put: <T = any>(url: string, data?: any, config?: any) => 
    apiClient.put<T>(url, data, config).then(res => res.data),
    
  patch: <T = any>(url: string, data?: any, config?: any) => 
    apiClient.patch<T>(url, data, config).then(res => res.data),
    
  delete: <T = any>(url: string, config?: any) => 
    apiClient.delete<T>(url, config).then(res => res.data),

  // Specialized method for activity logs with extended timeout
  getActivityLogs: <T = any>(params?: any) => 
    apiClient.get<T>('/api/v1/logs/activity', { 
      params, 
      timeout: 90000  // 90 seconds for activity logs
    }).then(res => res.data)
};

/**
 * Set authentication token
 */
export const setAuthToken = (token: string | null) => {
  if (token) {
    AuthTokenManager.setToken(token);
  } else {
    AuthTokenManager.clearTokens();
  }
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = (): boolean => {
  return AuthTokenManager.hasValidToken();
};