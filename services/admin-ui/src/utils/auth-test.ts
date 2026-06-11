/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { AuthTokenManager } from './auth-token-manager';
import { tesaApi } from '@/services/api/tesaApi';

export class AuthTester {
  /**
   * Test token storage and retrieval
   */
  static testTokenStorage() {
    console.group('🔧 Testing Token Storage');
    
    // Clear any existing tokens
    AuthTokenManager.clearTokens();
    
    // Test token setting
    const testToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token';
    AuthTokenManager.setToken(testToken);
    
    // Verify retrieval
    const retrievedToken = AuthTokenManager.getToken();
    console.log('✅ Token storage/retrieval:', retrievedToken === testToken ? 'PASS' : 'FAIL');
    
    // Test auth header
    const authHeader = AuthTokenManager.getAuthHeader();
    console.log('✅ Auth header format:', authHeader === `Bearer ${testToken}` ? 'PASS' : 'FAIL');
    
    // Test validation
    const isValid = AuthTokenManager.hasValidToken();
    console.log('✅ Token validation:', isValid ? 'PASS' : 'FAIL');
    
    // Show debug info
    console.log('🔍 Debug Info:', AuthTokenManager.getDebugInfo());
    
    console.groupEnd();
  }

  /**
   * Test API authentication headers
   */
  static async testApiAuthentication() {
    console.group('🌐 Testing API Authentication');
    
    try {
      // Test with valid token
      const testToken = localStorage.getItem('jwt_token');
      if (testToken) {
        console.log('📡 Testing API call with existing token...');
        
        // Try a simple API call that requires authentication
        const response = await tesaApi.getFast('/api/v1/user/me');
        console.log('✅ API call with auth:', response ? 'PASS' : 'FAIL');
      } else {
        console.log('⚠️ No token found for API testing');
      }
    } catch (error: any) {
      console.log('❌ API authentication test failed:', error.message);
      
      // Check if it's a 401 error (expected if not logged in)
      if (error.message.includes('401') || error.message.includes('Authentication')) {
        console.log('ℹ️ This is expected if user is not logged in');
      }
    }
    
    console.groupEnd();
  }

  /**
   * Test SSE authentication
   */
  static testSSEAuthentication() {
    console.group('📡 Testing SSE Authentication');
    
    const token = AuthTokenManager.getToken();
    if (token) {
      // Create a test SSE URL with authentication
      const testUrl = new URL('/api/v1/realtime/stream/test', window.location.origin);
      testUrl.searchParams.set('token', token);
      testUrl.searchParams.set('auth', `Bearer ${token}`);
      testUrl.searchParams.set('_t', Date.now().toString());
      
      console.log('✅ SSE URL construction:', testUrl.toString());
      console.log('✅ Token in URL:', testUrl.searchParams.has('token') ? 'PASS' : 'FAIL');
      console.log('✅ Auth param in URL:', testUrl.searchParams.has('auth') ? 'PASS' : 'FAIL');
    } else {
      console.log('⚠️ No token found for SSE testing');
    }
    
    console.groupEnd();
  }

  /**
   * Run all authentication tests
   */
  static runAllTests() {
    console.group('🧪 Running All Authentication Tests');
    console.log('🚀 Starting comprehensive authentication tests...');
    
    this.testTokenStorage();
    this.testApiAuthentication();
    this.testSSEAuthentication();
    
    console.log('✨ All authentication tests completed');
    console.groupEnd();
  }

  /**
   * Check current authentication status
   */
  static checkAuthStatus() {
    console.group('📊 Current Authentication Status');
    
    const hasToken = AuthTokenManager.hasValidToken();
    const token = AuthTokenManager.getToken();
    const debugInfo = AuthTokenManager.getDebugInfo();
    
    console.log('🔐 Has valid token:', hasToken ? '✅ YES' : '❌ NO');
    console.log('📏 Token length:', token?.length || 0);
    console.log('🔍 Storage debug:', debugInfo);
    
    // Check localStorage directly
    const jwtToken = localStorage.getItem('jwt_token');
    const accessToken = localStorage.getItem('access_token');
    
    console.log('📦 localStorage jwt_token:', jwtToken ? `✅ ${jwtToken.length} chars` : '❌ Not found');
    console.log('📦 localStorage access_token:', accessToken ? `✅ ${accessToken.length} chars` : '❌ Not found');
    
    console.groupEnd();
  }
}

