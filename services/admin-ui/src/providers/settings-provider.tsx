/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

'use client';

/* eslint-disable @typescript-eslint/no-explicit-any */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { APP_SETTINGS } from '@/config/settings.config';
import { Settings } from '@/config/types';

type Path = string;

type SettingsContextType = {
  getOption: <T = any>(path: Path) => T;
  setOption: <T = any>(path: Path, value: T) => void;
  storeOption: <T = any>(path: Path, value: T) => void;
  settings: Settings;
  isInitialized: boolean;
};

const SettingsContext = createContext<SettingsContextType | undefined>(
  undefined,
);

const LOCAL_STORAGE_PREFIX = 'app_settings_';

// Utility to safely access localStorage
const isBrowser = () => typeof window !== 'undefined';

function getFromPath(obj: any, path: string): any {
  return path.split('.').reduce((acc, part) => acc?.[part], obj);
}

function setToPath(obj: any, path: string, value: any): Settings {
  const keys = path.split('.');
  const lastKey = keys.pop()!;
  const lastObj = keys.reduce((acc, key) => (acc[key] ??= {}), obj);
  lastObj[lastKey] = value;
  return { ...obj };
}

function storeLeaf(path: string, value: unknown) {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(
      `${LOCAL_STORAGE_PREFIX}${path}`,
      JSON.stringify(value),
    );
  } catch (err) {
    console.error('LocalStorage write error:', err);
  }
}

function getLeafFromStorage(path: string): any {
  if (!isBrowser()) return undefined;
  try {
    const item = localStorage.getItem(`${LOCAL_STORAGE_PREFIX}${path}`);
    return item ? JSON.parse(item) : undefined;
  } catch (err) {
    console.error('LocalStorage read error:', err);
    return undefined;
  }
}

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  // Initialize with a stable default to prevent null context value
  const [settings, setSettings] = useState<Settings>(() => 
    structuredClone(APP_SETTINGS)
  );
  const [isInitialized, setIsInitialized] = useState(false);

  // Load settings from localStorage after mount
  useEffect(() => {
    if (!isBrowser()) {
      setIsInitialized(true);
      return;
    }

    try {
      const init = structuredClone(APP_SETTINGS);
      const localStorageKeys = Object.keys(localStorage)
        .filter((key) => key.startsWith(LOCAL_STORAGE_PREFIX));
      
      localStorageKeys.forEach((key) => {
        try {
          const path = key.replace(LOCAL_STORAGE_PREFIX, '');
          const value = getLeafFromStorage(path);
          if (value !== undefined) {
            setToPath(init, path, value);
          }
        } catch (error) {
          console.warn(`Failed to load setting from localStorage key "${key}":`, error);
        }
      });
      
      setSettings(init);
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error);
      // Keep the default settings if localStorage loading fails
    } finally {
      setIsInitialized(true);
    }
  }, []); // Empty dependency array to run once on mount

  const getOption = useCallback(
    <T,>(path: string): T => {
      return getFromPath(settings, path) as T;
    },
    [settings],
  );

  const setOption = useCallback(<T,>(path: string, value: T) => {
    setSettings((prev) => setToPath({ ...prev }, path, value));
  }, []);

  const storeOption = useCallback(<T,>(path: string, value: T) => {
    setSettings((prev) => {
      const newSettings = setToPath({ ...prev }, path, value);
      storeLeaf(path, value);
      return newSettings;
    });
  }, []);

  // Memoize context value to prevent unnecessary re-renders and ensure it's never null
  const contextValue = useMemo(
    () => ({ getOption, setOption, storeOption, settings, isInitialized }),
    [getOption, setOption, storeOption, settings, isInitialized],
  );

  // Ensure we always provide a valid context value, never null
  const safeContextValue: SettingsContextType = contextValue || {
    getOption: <T,>(path: string): T => getFromPath(structuredClone(APP_SETTINGS), path) as T,
    setOption: () => {},
    storeOption: () => {},
    settings: structuredClone(APP_SETTINGS),
    isInitialized: false,
  };

  return (
    <SettingsContext.Provider value={safeContextValue}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => {
  const ctx = useContext(SettingsContext);
  
  // Enhanced null/undefined check for better error handling
  if (!ctx || ctx === null || ctx === undefined) {
    // PRODUCTION FIX: Provide fallback instead of throwing error
    console.warn('useSettings called outside of SettingsProvider context or context is null. Using fallback settings.');
    
    // Create a stable fallback object
    const fallbackSettings = structuredClone(APP_SETTINGS);
    
    return {
      getOption: <T = any>(path: string): T => {
        try {
          return getFromPath(fallbackSettings, path) as T;
        } catch (error) {
          console.warn(`Failed to get setting at path "${path}":`, error);
          return undefined as T;
        }
      },
      setOption: <T = any>(path: string, value: T) => {
        console.warn('setOption called outside of SettingsProvider context. Changes will not persist.');
      },
      storeOption: <T = any>(path: string, value: T) => {
        console.warn('storeOption called outside of SettingsProvider context. Changes will not persist.');
      },
      settings: fallbackSettings,
      isInitialized: false,
    };
  }
  return ctx;
};
