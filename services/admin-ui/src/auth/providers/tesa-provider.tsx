/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { PropsWithChildren, useEffect, useState } from 'react';
import { TesaAdapter } from '@/auth/adapters/tesa-adapter';
import { AuthContext } from '@/auth/context/auth-context';
import * as authHelper from '@/auth/lib/helpers';
import { AuthModel, UserModel } from '@/auth/lib/models';

// Define the TESA Auth Provider
export function AuthProvider({ children }: PropsWithChildren) {
  const [loading, setLoading] = useState(false); // Start with false to avoid infinite loading
  const [auth, setAuth] = useState<AuthModel | undefined>(authHelper.getAuth());
  const [currentUser, setCurrentUser] = useState<UserModel | undefined>();
  const [isAdmin, setIsAdmin] = useState(false);
  const [hasBDHOrgAdminAccess, setHasBDHOrgAdminAccess] = useState(false);

  // Check if user is admin and has BDH Org Admin access
  useEffect(() => {
    setIsAdmin(currentUser?.is_admin === true);
    // Org Admin access is driven solely by the role claim, never by a hardcoded account.
    const isBDHOrgAdmin = currentUser?.role === 'organization_admin';
    setHasBDHOrgAdminAccess(isBDHOrgAdmin);
  }, [currentUser]);

  // Initialize user on mount if auth exists
  useEffect(() => {
    if (auth?.access_token) {
      verify();
    }
  }, []);

  const verify = async () => {
    if (auth) {
      try {
        const user = await getUser();
        setCurrentUser(user || undefined);
      } catch {
        saveAuth(undefined);
        setCurrentUser(undefined);
      }
    }
  };

  const saveAuth = (auth: AuthModel | undefined) => {
    setAuth(auth);
    if (auth) {
      authHelper.setAuth(auth);
    } else {
      authHelper.removeAuth();
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const auth = await TesaAdapter.login(email, password);
      saveAuth(auth);
      const user = await getUser();

      // Debug: Log user data after login
      console.log('TesaProvider login - user data:', {
        email: user?.email,
        role: user?.role,
        organization_id: user?.organization_id,
        full_user: user
      });

      setCurrentUser(user || undefined);

      // Return user for role-based redirect
      return user;
    } catch (error) {
      saveAuth(undefined);
      throw error;
    }
  };

  const register = async (
    email: string,
    password: string,
    password_confirmation: string,
    name: string,
  ) => {
    try {
      const auth = await TesaAdapter.register(email, password, name);
      saveAuth(auth);
      const user = await getUser();
      setCurrentUser(user || undefined);
    } catch (error) {
      saveAuth(undefined);
      throw error;
    }
  };

  const requestPasswordReset = async (email: string) => {
    await TesaAdapter.requestPasswordReset(email);
  };

  const resetPassword = async (
    password: string,
    password_confirmation: string,
  ) => {
    await TesaAdapter.resetPassword(password, password_confirmation);
  };

  const resendVerificationEmail = async (email: string) => {
    await TesaAdapter.resendVerificationEmail(email);
  };

  const getUser = async () => {
    return await TesaAdapter.getCurrentUser();
  };

  const updateProfile = async (userData: Partial<UserModel>) => {
    const baseUser = currentUser ? (currentUser as UserModel) : ({} as UserModel);
    const apiUser = await TesaAdapter.updateUserProfile(userData);
    const normalizedUser = (apiUser && (apiUser as any).user) ? (apiUser as any).user : apiUser;
    const nextUser: UserModel = {
      ...baseUser,
      ...(normalizedUser ?? {}),
      ...userData,
    } as UserModel;

    setCurrentUser(nextUser);
    return nextUser;
  };

  const logout = () => {
    TesaAdapter.logout();
    saveAuth(undefined);
    setCurrentUser(undefined);
  };

  return (
    <AuthContext.Provider
      value={{
        loading,
        setLoading,
        auth,
        saveAuth,
        user: currentUser,
        setUser: setCurrentUser,
        login,
        register,
        requestPasswordReset,
        resetPassword,
        resendVerificationEmail,
        getUser,
        updateProfile,
        logout,
        verify,
        isAdmin,
        hasBDHOrgAdminAccess,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
