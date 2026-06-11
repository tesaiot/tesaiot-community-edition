/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useContext } from 'react';
import { AuthContext } from '@/auth/context/auth-context';

/**
 * Hook to access the TESA authentication context
 * This connects to the real TESA authentication system
 */
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (!context || context === null || context === undefined) {
    // Enhanced error handling: provide fallback instead of throwing in production
    console.warn('useAuth called outside of AuthProvider context. Returning safe defaults.');
    
    // Return a safe fallback to prevent crashes
    return {
      // Core authentication state
      user: undefined,
      isLoading: false,
      isAuthenticated: false,
      
      // Authentication methods (no-ops for safety)
      login: async () => { console.warn('login called outside auth context'); return { success: false }; },
      logout: () => { console.warn('logout called outside auth context'); },
      register: async () => { console.warn('register called outside auth context'); return { success: false }; },
      checkAuth: async () => { console.warn('checkAuth called outside auth context'); },
      
      // User management
      updateUser: async () => { console.warn('updateUser called outside auth context'); return { success: false }; },
      getUser: async () => null,
      verify: async () => { throw new Error('Authentication not available'); },
      
      // Additional utilities
      isAdmin: false,
      auth: undefined,
      
      // Password management
      requestPasswordReset: async () => { throw new Error('Authentication not available'); },
      resetPassword: async () => { throw new Error('Authentication not available'); },
      resendVerificationEmail: async () => { throw new Error('Authentication not available'); },
      
      // Token management
      saveAuth: () => { console.warn('saveAuth called outside auth context'); },
      setUser: () => { console.warn('setUser called outside auth context'); },
      setLoading: () => { console.warn('setLoading called outside auth context'); },
    };
  }

  return {
    // Core authentication state
    user: context.user,
    isLoading: context.loading,
    isAuthenticated: !!context.auth?.access_token,
    
    // Authentication methods
    login: context.login,
    logout: context.logout,
    register: context.register,
    checkAuth: context.verify, // Add checkAuth that maps to verify
    
    // User management
    updateUser: context.updateProfile,
    getUser: context.getUser,
    verify: context.verify,
    
    // Additional utilities
    isAdmin: context.isAdmin,
    auth: context.auth,
    
    // Password management
    requestPasswordReset: context.requestPasswordReset,
    resetPassword: context.resetPassword,
    resendVerificationEmail: context.resendVerificationEmail,
    
    // Token management
    saveAuth: context.saveAuth,
    setUser: context.setUser,
    setLoading: context.setLoading,
  };
}