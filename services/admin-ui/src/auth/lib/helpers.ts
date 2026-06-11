/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { getData, setData } from '@/lib/storage';
import { AuthModel } from './models';
import { AuthTokenManager } from '@/utils/auth-token-manager';

const AUTH_LOCAL_STORAGE_KEY = `${import.meta.env.VITE_APP_NAME}-auth-v${
  import.meta.env.VITE_APP_VERSION || '1.0'
}`;

/**
 * Get stored auth information from local storage
 */
const getAuth = (): AuthModel | undefined => {
  try {
    // Try the current key first
    let auth = getData(AUTH_LOCAL_STORAGE_KEY) as AuthModel | undefined;
    
    // If not found, try the legacy "undefined" key
    if (!auth) {
      const legacyKey = `undefined-auth-v${import.meta.env.VITE_APP_VERSION || '1.0'}`;
      auth = getData(legacyKey) as AuthModel | undefined;
      
      // If found in legacy location, migrate to new location
      if (auth) {
        setData(AUTH_LOCAL_STORAGE_KEY, auth);
        localStorage.removeItem(legacyKey);
      }
    }
    
    return auth;
  } catch (error) {
    console.error('AUTH LOCAL STORAGE PARSE ERROR', error);
  }
};

/**
 * Save auth information to local storage
 */
const setAuth = (auth: AuthModel) => {
  setData(AUTH_LOCAL_STORAGE_KEY, auth);
  
  // Also sync the access token using the token manager
  if (auth?.access_token) {
    AuthTokenManager.setToken(auth.access_token);
  }
};

/**
 * Remove auth information from local storage
 */
const removeAuth = () => {
  if (!localStorage) {
    return;
  }

  try {
    localStorage.removeItem(AUTH_LOCAL_STORAGE_KEY);
    
    // Also clear all tokens using the token manager
    AuthTokenManager.clearTokens();
  } catch (error) {
    console.error('AUTH LOCAL STORAGE REMOVE ERROR', error);
  }
};

export { AUTH_LOCAL_STORAGE_KEY, getAuth, removeAuth, setAuth };
