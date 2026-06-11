/*
 * TESA IoT Platform - Service Worker
 * Copyright (c) 2025 Associate Professor Wiroon Sriborrirux (BDH Corp.)
 * 
 * Prevents serving outdated JavaScript files through intelligent caching
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

// Install event - cache essential assets
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Only cache essential assets during install
      return cache.addAll([
        '/',
        '/index.html'
      ]);
    }).then(() => {
      // Skip waiting and activate immediately
      return self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
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
    }).then(() => {
      // Take control of all clients immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
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
  const strategy = getCachingStrategy(url.pathname);
  
  switch (strategy) {
    case 'no-cache':
      event.respondWith(networkOnly(request));
      break;
    case 'cache-first':
      event.respondWith(cacheFirst(request));
      break;
    case 'network-first':
      event.respondWith(networkFirst(request));
      break;
    default:
      event.respondWith(staleWhileRevalidate(request));
  }
});

// Message event - handle commands from the main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
      })
    );
  }
  
  // NEW: Handle self-destruction command
  if (event.data && event.data.type === 'SELF_DESTRUCT') {
    console.log('Service Worker: Self-destruct command received');
    event.waitUntil(
      Promise.all([
        // Clear all caches
        caches.keys().then(cacheNames => 
          Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)))
        ),
        // Unregister self
        self.registration.unregister()
      ]).then(() => {
        console.log('Service Worker: Self-destruct completed');
        // Notify main thread that cleanup is complete
        self.clients.matchAll().then(clients => {
          clients.forEach(client => {
            client.postMessage({ 
              type: 'CLEANUP_COMPLETE',
              timestamp: Date.now()
            });
          });
        });
      })
    );
  }
});

// Determine caching strategy based on URL
function getCachingStrategy(pathname) {
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

// Network only strategy
async function networkOnly(request) {
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

// Cache first strategy
async function cacheFirst(request) {
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

// Network first strategy
async function networkFirst(request) {
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

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
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