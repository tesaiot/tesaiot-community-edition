/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Centralized token management utility.
 *
 * Storage model (hardened 2026-06):
 * - ONE canonical storage location: localStorage['jwt_token'].
 * - Legacy locations ('access_token', 'auth_token' localStorage keys and the
 *   JS-written 'access_token' cookie) are READ for backwards compatibility
 *   and migrated to the canonical key, but never written anymore. Nothing in
 *   this repo (nginx, APISIX, the API) reads the JS-written cookie, so the
 *   cookie write was removed — it only widened the XSS exposure surface.
 *
 * NOTE: tokens in localStorage remain readable by any XSS payload. The real
 * fix is server-set HttpOnly cookies, which requires an API change and is
 * intentionally out of scope here.
 */
export class AuthTokenManager {
  /** Canonical storage key - the ONLY key this manager writes. */
  private static readonly PRIMARY_KEY = 'jwt_token';
  /** Legacy keys: read + cleared, never written. */
  private static readonly LEGACY_KEYS = ['access_token', 'auth_token'];
  private static readonly TOKEN_KEYS = [
    AuthTokenManager.PRIMARY_KEY,
    ...AuthTokenManager.LEGACY_KEYS,
  ];

  /**
   * Get cookie value by name (legacy compatibility read only)
   */
  private static getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      const cookieValue = parts.pop()?.split(';').shift();
      return cookieValue || null;
    }
    return null;
  }

  /**
   * Get the current valid token from storage.
   * Canonical key first; legacy locations are migrated when hit.
   */
  static getToken(): string | null {
    const canonical = localStorage.getItem(this.PRIMARY_KEY);
    if (canonical && canonical.trim() !== '') {
      return canonical;
    }

    // Legacy localStorage keys (older sessions): migrate to the canonical key
    for (const key of this.LEGACY_KEYS) {
      const token = localStorage.getItem(key);
      if (token && token.trim() !== '') {
        localStorage.setItem(this.PRIMARY_KEY, token);
        return token;
      }
    }

    // Legacy JS-written cookie (older sessions): migrate, do not re-write
    const cookieToken = this.getCookie('access_token');
    if (cookieToken && cookieToken.trim() !== '') {
      localStorage.setItem(this.PRIMARY_KEY, cookieToken);
      return cookieToken;
    }

    return null;
  }

  /**
   * Store token in the single canonical location.
   */
  static setToken(token: string): void {
    if (!token || token.trim() === '') {
      console.warn('AuthTokenManager: Attempting to store empty token');
      return;
    }

    localStorage.setItem(this.PRIMARY_KEY, token);

    console.debug('AuthTokenManager: Token stored successfully, length:', token.length);
  }

  /**
   * Clear all tokens from storage (canonical + legacy locations)
   */
  static clearTokens(): void {
    this.TOKEN_KEYS.forEach(key => {
      localStorage.removeItem(key);
    });
    // Clear the legacy JS-written cookie if an old session left one behind
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    console.debug('AuthTokenManager: All tokens cleared');
  }

  /**
   * Sync token into the canonical storage location
   */
  static syncToken(): string | null {
    const token = this.getToken();
    if (token) {
      this.setToken(token);
    }
    return token;
  }

  /**
   * Check if a valid token exists
   */
  static hasValidToken(): boolean {
    const token = this.getToken();
    return !!(token && token.trim() !== '');
  }

  /**
   * Get token for HTTP Authorization header
   */
  static getAuthHeader(): string | null {
    const token = this.getToken();
    return token ? `Bearer ${token}` : null;
  }

  /**
   * Validate token format (basic check)
   */
  static isValidTokenFormat(token: string): boolean {
    if (!token || token.trim() === '') return false;

    // Basic JWT format check (has 3 parts separated by dots)
    const parts = token.split('.');
    return parts.length === 3;
  }

  /**
   * Get debug information about stored tokens
   */
  static getDebugInfo(): Record<string, any> {
    const info: Record<string, any> = {};

    this.TOKEN_KEYS.forEach(key => {
      const token = localStorage.getItem(key);
      info[key] = token ? {
        exists: true,
        length: token.length,
        valid: this.isValidTokenFormat(token),
        preview: `${token.substring(0, 20)}...`
      } : { exists: false };
    });

    info.primary_token = this.getToken();
    info.has_valid_token = this.hasValidToken();

    return info;
  }
}

// Export convenience functions
export const getToken = () => AuthTokenManager.getToken();
export const setToken = (token: string) => AuthTokenManager.setToken(token);
export const clearTokens = () => AuthTokenManager.clearTokens();
export const hasValidToken = () => AuthTokenManager.hasValidToken();
export const getAuthHeader = () => AuthTokenManager.getAuthHeader();
export const syncToken = () => AuthTokenManager.syncToken();
