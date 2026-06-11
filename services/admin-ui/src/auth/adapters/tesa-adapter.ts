/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { AuthModel, UserModel } from '@/auth/lib/models';
import { ssoCookieDomain } from '@/lib/domain';
import axios from 'axios';

const canonicalizeRole = (role?: string): string => {
  if (!role) return 'user';
  const map: Record<string, string> = {
    org_admin: 'organization_admin',
    org_user: 'user',
  };
  return map[role] || role;
};

// Dynamically determine API URL based on current host
const getApiUrl = () => {
  let baseURL = import.meta.env.VITE_API_URL || '';
  
  // If VITE_API_URL is 'auto', use the current window location
  if (baseURL === 'auto') {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // If accessed through port 80/443 (NGINX), use same origin
    if (!port || port === '80' || port === '443') {
      baseURL = ''; // Empty string means same origin
    } else {
      baseURL = `${protocol}//${hostname}:${port}`;
    }
  }
  // If no explicit URL or it's localhost, use current host
  else if (!baseURL || baseURL.includes('localhost')) {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // If accessed through port 80/443 (NGINX), use same origin
    if (!port || port === '80' || port === '443') {
      baseURL = ''; // Empty string means same origin
    } else {
      // Otherwise use the current port
      baseURL = `${protocol}//${hostname}:${port}`;
    }
  }
  
  return baseURL;
};

const API_URL = getApiUrl();

/**
 * TESA authentication adapter that connects to the TESA IoT Platform API
 */
export const TesaAdapter = {
  /**
   * Login with email and password
   */
  async login(email: string, password: string): Promise<AuthModel> {
    console.log('TesaAdapter: Attempting login to TESA API');

    try {
      const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
        email: email,
        password: password,
      });

      if (response.data.success && response.data.token) {
        console.log('TesaAdapter: Login successful');
        
        // Store token in axios defaults and localStorage with enhanced sync
        const token = response.data.token;
        if (!token || token.trim() === '') {
          throw new Error('Empty token received from server');
        }
        
        // Ensure token is stored in all possible locations for consistency
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        localStorage.setItem('jwt_token', token);
        localStorage.setItem('access_token', token); // Fallback storage
        
        // Also set as cookie for API requests that expect it
        document.cookie = `access_token=${token}; path=/; secure; samesite=strict; max-age=86400`;

        // Set tesa_token cookie for cross-subdomain SSO (BENTO IDE, BDH AI, etc.)
        // SameSite=Lax allows the cookie to be sent on top-level navigations between subdomains.
        // Cookie scope is derived from the actual host the UI runs on (self-host
        // DOMAIN-agnostic): on localhost / raw IP no domain attribute is set so the
        // cookie is host-only; on a real domain it is scoped to the registrable parent.
        const cookieDomain = ssoCookieDomain();
        const domainAttr = cookieDomain ? ` domain=${cookieDomain};` : '';
        document.cookie = `tesa_token=${token}; path=/;${domainAttr} secure; samesite=lax; max-age=86400`;
        
        // Clear any old tokens that might cause conflicts
        localStorage.removeItem('auth_token');
        
        console.log('Auth adapter: Token stored successfully, length:', token.length);
        console.debug('Auth adapter: Token sync completed across all storage locations');
        
        return {
          access_token: response.data.token,
          refresh_token: response.data.token,
        };
      }

      throw new Error('Invalid response from server');
    } catch (error: any) {
      console.error('TesaAdapter: Login error:', error);
      
      if (error.response?.status === 401) {
        throw new Error('Invalid username or password');
      } else if (error.response?.status === 503) {
        throw new Error('Database unavailable');
      } else if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK' || !error.response) {
        throw new Error('API server not reachable. Please check if the server is running.');
      }
      
      throw new Error(error.response?.data?.error || 'Login failed');
    }
  },

  /**
   * Register a new user
   */
  async register(email: string, password: string, name: string): Promise<AuthModel> {
    try {
      const response = await axios.post(`${API_URL}/api/v1/auth/register`, {
        username: email,
        password: password,
        name: name,
      });

      return {
        access_token: response.data.access_token,
        refresh_token: response.data.refresh_token || response.data.access_token,
      };
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Registration failed');
    }
  },

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<UserModel | null> {
    try {
      // Check if we have a stored token first - try multiple storage locations
      const storedToken = localStorage.getItem('jwt_token') || 
                         localStorage.getItem('access_token') || 
                         localStorage.getItem('auth_token');
      
      if (!storedToken || storedToken.trim() === '') {
        console.log('TesaAdapter: No valid stored token, user not authenticated');
        return null;
      }
      
      // Validate JWT token before making API call
      try {
        const tokenParts = storedToken.split('.');
        if (tokenParts.length !== 3) {
          console.log('TesaAdapter: Invalid token format, clearing storage');
          this.clearAllTokens();
          return null;
        }
        
        // Decode and check token expiration
        const tokenPayload = JSON.parse(atob(tokenParts[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        
        if (tokenPayload.exp && tokenPayload.exp < currentTime) {
          console.log('TesaAdapter: Token expired, clearing storage');
          this.clearAllTokens();
          return null;
        }
      } catch (tokenError) {
        console.log('TesaAdapter: Failed to validate token, clearing storage');
        this.clearAllTokens();
        return null;
      }
      
      // Always set/update the token in axios headers for consistency
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      
      // Ensure token is synced across all storage locations
      if (localStorage.getItem('jwt_token') !== storedToken) {
        localStorage.setItem('jwt_token', storedToken);
      }
      if (localStorage.getItem('access_token') !== storedToken) {
        localStorage.setItem('access_token', storedToken);
      }
      
      const response = await axios.get(`${API_URL}/api/v1/user/me`);
      
      // Debug: Log the actual response
      console.log('TesaAdapter getCurrentUser response:', {
        organization_id: response.data.organization_id,
        role: response.data.role,
        email: response.data.email
      });
      
      const canonicalRole = canonicalizeRole(response.data.role);

      // Return all user data including organization info
      const userData = {
        id: response.data.id || '1',
        email: response.data.email || response.data.username,
        name: response.data.name || response.data.username,
        is_admin: response.data.is_admin || canonicalRole === 'super_admin' || canonicalRole === 'organization_admin',
        created_at: response.data.created_at || new Date().toISOString(),
        // Include additional fields needed by dashboard
        role: canonicalRole,
        organization_id: response.data.organization_id,
        organizationId: response.data.organization_id, // Add camelCase version for compatibility
        organization: response.data.organization,
        permissions: response.data.permissions,
        // Map avatar field to pic for UserModel compatibility
        pic: response.data.avatar || response.data.pic || '',
        avatar: response.data.avatar || '', // Keep both for compatibility
      };
      
      console.log('TesaAdapter returning user data:', {
        organization_id: userData.organization_id,
        role: userData.role
      });
      
      return userData;
    } catch (error: any) {
      console.log('TesaAdapter: Failed to get user info:', error?.response?.status);
      
      // If token is invalid, clear all token storage locations
      if (error?.response?.status === 401) {
        this.clearAllTokens();
      }
      
      return null;
    }
  },

  /**
   * Update user profile
   */
  async updateUserProfile(userData: Partial<UserModel>): Promise<UserModel> {
    try {
      const response = await axios.put(`${API_URL}/api/v1/auth/profile`, userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Profile update failed');
    }
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    try {
      await axios.post(`${API_URL}/api/v1/auth/forgot-password`, { email });
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Password reset request failed');
    }
  },

  /**
   * Reset password with token
   */
  async resetPassword(password: string, password_confirmation: string): Promise<void> {
    try {
      await axios.post(`${API_URL}/api/v1/auth/reset-password`, {
        password,
        password_confirmation,
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Password reset failed');
    }
  },

  /**
   * Resend verification email
   */
  async resendVerificationEmail(email: string): Promise<void> {
    try {
      await axios.post(`${API_URL}/api/v1/auth/resend-verification`, { email });
    } catch (error) {
      // Ignore for now
    }
  },

  /**
   * Logout
   */
  async logout(): Promise<void> {
    try {
      await axios.post(`${API_URL}/api/v1/auth/logout`);
    } catch (error) {
      // Ignore logout errors
    } finally {
      // Clear all token storage on logout
      this.clearAllTokens();
    }
  },

  /**
   * OAuth login (not implemented for TESA)
   */
  async signInWithOAuth(provider: string): Promise<void> {
    throw new Error('OAuth login not supported in TESA platform');
  },
  
  /**
   * Helper method to clear all token storage locations
   */
  clearAllTokens(): void {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('auth_token');
    delete axios.defaults.headers.common['Authorization'];
    // Clear cross-subdomain SSO cookies (BENTO IDE, BDH AI, etc.)
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; samesite=strict';
    const cookieDomain = ssoCookieDomain();
    const domainAttr = cookieDomain ? ` domain=${cookieDomain};` : '';
    document.cookie = `tesa_token=; path=/;${domainAttr} expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; samesite=lax`;
    console.log('TesaAdapter: Cleared all tokens from storage');
  },
};
