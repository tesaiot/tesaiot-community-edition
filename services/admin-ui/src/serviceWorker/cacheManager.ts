/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

const CACHE_NAME = 'tesa-admin-ui-v1';
const DYNAMIC_CACHE_NAME = 'tesa-admin-ui-dynamic-v1';

// Assets that should use cache-first strategy (fonts, images)
const CACHE_FIRST_PATTERNS = [
  /\.woff2?$/,
  /\.ttf$/,
  /\.eot$/,
  /\.svg$/,
  /\.png$/,
  /\.jpg$/,
  /\.jpeg$/,
  /\.gif$/,
  /\.ico$/
];

// Assets that should use network-first strategy (JS, CSS, API)
const NETWORK_FIRST_PATTERNS = [
  /\.js$/,
  /\.css$/,
  /\.json$/,
  /\/api\//
];

// Assets that should never be cached
const NO_CACHE_PATTERNS = [
  /version\.json$/,
  /build-manifest\.json$/,
  /\.map$/
];

export class CacheManager {
  private static instance: CacheManager;
  
  private constructor() {}
  
  static getInstance(): CacheManager {
    if (!CacheManager.instance) {
      CacheManager.instance = new CacheManager();
    }
    return CacheManager.instance;
  }

  /**
   * Install event - cache essential assets
   */
  async onInstall(event: ExtendableEvent): Promise<void> {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
      caches.open(CACHE_NAME).then(cache => {
        // Only cache essential assets during install
        return cache.addAll([
          '/',
          '/index.html'
        ]);
      })
    );
  }

  /**
   * Activate event - clean up old caches
   */
  async onActivate(event: ExtendableEvent): Promise<void> {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
              console.log('Service Worker: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
    );
  }

  /**
   * Fetch event - implement caching strategies
   */
  async onFetch(event: FetchEvent): Promise<void> {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
      return;
    }
    
    // Skip external requests
    if (!url.origin.includes(self.location.origin)) {
      return;
    }
    
    // Determine caching strategy
    const strategy = this.getCachingStrategy(url.pathname);
    
    switch (strategy) {
      case 'no-cache':
        event.respondWith(this.networkOnly(request));
        break;
      case 'cache-first':
        event.respondWith(this.cacheFirst(request));
        break;
      case 'network-first':
        event.respondWith(this.networkFirst(request));
        break;
      default:
        event.respondWith(this.staleWhileRevalidate(request));
    }
  }

  /**
   * Determine caching strategy based on URL
   */
  private getCachingStrategy(pathname: string): string {
    // Never cache version files
    if (NO_CACHE_PATTERNS.some(pattern => pattern.test(pathname))) {
      return 'no-cache';
    }
    
    // Cache-first for static assets
    if (CACHE_FIRST_PATTERNS.some(pattern => pattern.test(pathname))) {
      return 'cache-first';
    }
    
    // Network-first for dynamic content
    if (NETWORK_FIRST_PATTERNS.some(pattern => pattern.test(pathname))) {
      return 'network-first';
    }
    
    // Default strategy
    return 'stale-while-revalidate';
  }

  /**
   * Network only strategy
   */
  private async networkOnly(request: Request): Promise<Response> {
    try {
      const response = await fetch(request, {
        cache: 'no-store'
      });
      return response;
    } catch (error) {
      return new Response('Network error', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
  }

  /**
   * Cache first strategy
   */
  private async cacheFirst(request: Request): Promise<Response> {
    const cache = await caches.open(CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    try {
      const response = await fetch(request);
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      return new Response('Network error', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
  }

  /**
   * Network first strategy
   */
  private async networkFirst(request: Request): Promise<Response> {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    
    try {
      const response = await fetch(request);
      if (response.ok) {
        // Update cache with fresh response
        cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      // Fall back to cache
      const cachedResponse = await cache.match(request);
      if (cachedResponse) {
        return cachedResponse;
      }
      
      return new Response('Network error', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
  }

  /**
   * Stale while revalidate strategy
   */
  private async staleWhileRevalidate(request: Request): Promise<Response> {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request).then(response => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    });
    
    return cachedResponse || fetchPromise;
  }

  /**
   * Clear all caches
   */
  async clearAllCaches(): Promise<void> {
    const cacheNames = await caches.keys();
    await Promise.all(
      cacheNames.map(cacheName => caches.delete(cacheName))
    );
  }

  /**
   * Update cache with new version
   */
  async updateCache(urls: string[]): Promise<void> {
    const cache = await caches.open(CACHE_NAME);
    
    // Delete old versions
    const keys = await cache.keys();
    await Promise.all(
      keys.map(request => {
        const url = new URL(request.url);
        if (NETWORK_FIRST_PATTERNS.some(pattern => pattern.test(url.pathname))) {
          return cache.delete(request);
        }
      })
    );
    
    // Add new versions
    await cache.addAll(urls);
  }
}

// Export for service worker
export const cacheManager = CacheManager.getInstance();