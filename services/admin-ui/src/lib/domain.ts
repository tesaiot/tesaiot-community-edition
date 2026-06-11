/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 *
 * Domain helpers for the self-host Community Edition. The build is fully
 * domain-agnostic: a self-hoster sets DOMAIN once (e.g. iot.acme.com) and the
 * UI derives every public host/origin/cookie-scope from the browser's actual
 * `window.location` at runtime. There are NO hardcoded tesaiot.dev/.com
 * literals here — the same image works on any domain without a rebuild.
 */

/**
 * Returns the current host the UI is served from (window.location.hostname),
 * falling back to 'localhost' in non-browser contexts (SSR/tests).
 */
export function currentHost(): string {
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return window.location.hostname;
  }
  return 'localhost';
}

/**
 * Computes the parent/registrable domain to scope a cross-subdomain SSO cookie
 * to, derived from the actual host the UI runs on. Examples:
 *   admin.iot.acme.com -> .iot.acme.com   (share with ide.iot.acme.com, ...)
 *   iot.acme.com       -> .acme.com
 *   acme.com           -> .acme.com
 *   localhost          -> undefined       (cookies can't take a domain attr on localhost)
 *   127.0.0.1          -> undefined       (raw IPs can't carry a domain attr)
 *
 * Returns `undefined` when a domain attribute must NOT be set (localhost / IP);
 * callers should then omit `domain=` so the cookie is host-only.
 */
export function ssoCookieDomain(host: string = currentHost()): string | undefined {
  // No domain attribute for localhost or raw IPv4/IPv6 addresses.
  if (host === 'localhost' || /^[\d.]+$/.test(host) || host.includes(':')) {
    return undefined;
  }
  const parts = host.split('.');
  if (parts.length < 2) {
    return undefined;
  }
  // Use the last two labels (registrable domain) so siblings under it share
  // the cookie. For deeper hosts this still yields a leading-dot parent domain.
  const parent = parts.slice(-2).join('.');
  return `.${parent}`;
}

/**
 * True when `hostname` is the operator's own host or a subdomain of it.
 * Used to gate post-login redirects to the operator's external services
 * (e.g. ide.acme.com) without allowing arbitrary external hosts.
 *
 * Compares against the registrable domain of the current host so that, on
 * admin.iot.acme.com, redirects to ide.iot.acme.com / acme.com are permitted.
 */
export function isSameSiteHost(hostname: string, self: string = currentHost()): boolean {
  if (!hostname) return false;
  if (hostname === self) return true;
  const base = ssoCookieDomain(self); // e.g. '.acme.com' (leading dot) or undefined
  if (!base) {
    // localhost / IP: only exact host matches are allowed.
    return hostname === self;
  }
  const bare = base.slice(1); // 'acme.com'
  return hostname === bare || hostname.endsWith(base); // base already has the leading dot
}
