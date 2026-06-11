/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { createContext, useContext } from 'react';
import { AuthModel, UserModel } from '@/auth/lib/models';

// Create AuthContext with types
export const AuthContext = createContext<{
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  auth?: AuthModel;
  saveAuth: (auth: AuthModel | undefined) => void;
  user?: UserModel;
  setUser: React.Dispatch<React.SetStateAction<UserModel | undefined>>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    password_confirmation: string,
    firstName?: string,
    lastName?: string,
  ) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  resetPassword: (
    password: string,
    password_confirmation: string,
  ) => Promise<void>;
  resendVerificationEmail: (email: string) => Promise<void>;
  getUser: () => Promise<UserModel | null>;
  updateProfile: (userData: Partial<UserModel>) => Promise<UserModel>;
  logout: () => void;
  verify: () => Promise<void>;
  isAdmin: boolean;
  hasBDHOrgAdminAccess: boolean;
}>({
  loading: false,
  setLoading: () => {},
  saveAuth: () => {},
  setUser: () => {},
  login: async () => {},
  register: async () => {},
  requestPasswordReset: async () => {},
  resetPassword: async () => {},
  resendVerificationEmail: async () => {},
  getUser: async () => null,
  updateProfile: async () => ({}) as UserModel,
  logout: () => {},
  verify: async () => {},
  isAdmin: false,
  hasBDHOrgAdminAccess: false,
});

// Hook definition
// DEPRECATED: Use '@/hooks/useAuth' instead for null safety
// This export is kept for backward compatibility only
export function useAuth() {
  const context = useContext(AuthContext);
  // Add minimal null safety to prevent crashes
  if (!context) {
    console.warn('useAuth from auth-context.ts called outside AuthProvider. Use @/hooks/useAuth instead.');
    return null;
  }
  return context;
}
