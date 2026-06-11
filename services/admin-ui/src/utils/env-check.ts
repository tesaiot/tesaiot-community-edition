/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export const isTestEnvironment = (): boolean => {
  return (
    process.env.NODE_ENV === 'test' ||
    typeof window !== 'undefined' && window.location.hostname === 'localhost' ||
    process.env.VITEST === 'true' ||
    process.env.JEST_WORKER_ID !== undefined
  );
};

export const isProductionEnvironment = (): boolean => {
  return process.env.NODE_ENV === 'production';
};

export const isDevelopmentEnvironment = (): boolean => {
  return process.env.NODE_ENV === 'development';
};

/**
 * Conditional execution wrapper for test-only code
 */
export const testOnly = <T>(testCode: () => T, fallback?: T): T | undefined => {
  if (isTestEnvironment()) {
    return testCode();
  }
  return fallback;
};

/**
 * Production-safe import wrapper for test dependencies
 */
export const safeTestImport = async <T>(
  moduleName: string,
  fallback?: T
): Promise<T | undefined> => {
  if (isTestEnvironment()) {
    try {
      const module = await import(moduleName);
      return module;
    } catch (error) {
      console.warn(`Failed to import test module ${moduleName}:`, error);
      return fallback;
    }
  }
  return fallback;
};