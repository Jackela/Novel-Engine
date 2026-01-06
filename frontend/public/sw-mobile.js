/**
 * Mobile-Optimized Service Worker
 * ===============================
 * 
 * Provides aggressive caching for mobile devices to reduce bundle sizes
 * and improve performance on slower connections.
 */

const CACHE_NAME = 'novel-engine-mobile-v1';
const STATIC_CACHE = 'novel-engine-static-v1';
const API_CACHE = 'novel-engine-api-v1';

// Mobile-optimized cache configuration
const CACHE_CONFIG = {
  maxAge: {
    static: 7 * 24 * 60 * 60 * 1000, // 7 days
    api: 5 * 60 * 1000, // 5 minutes
    images: 24 * 60 * 60 * 1000, // 24 hours
  },
  maxEntries: {
    static: 50,
    api: 100,
    images: 30,
  }
};

// Files to cache for offline capability
const STATIC_ASSETS = [
  '/',
  '/static/js/main.js',
  '/static/css/main.css',
  '/manifest.json',
  '/favicon.ico'
];

// API endpoints to cache
const API_PATTERNS = [
  /\/api\/v1\/characters/,
  /\/api\/v1\/stories/,
  /\/api\/v1\/campaigns/,
  /\/api\/v1\/health/
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Mobile SW: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Mobile SW: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Mobile SW: Static assets cached');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Mobile SW: Failed to cache static assets:', error);
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', event => {
  console.log('Mobile SW: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(cacheName => {
              return cacheName.startsWith('novel-engine-') && 
                     ![CACHE_NAME, STATIC_CACHE, API_CACHE].includes(cacheName);
            })
            .map(cacheName => {
              console.log('Mobile SW: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('Mobile SW: Cache cleanup complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }

  event.respondWith(handleRequest(event.request));
});

// Request handling with mobile-optimized strategies
async function handleRequest(request) {
  try {
    // Static assets - Cache First strategy
    if (isStaticAsset(request)) {
      return await cacheFirst(request, STATIC_CACHE);
    }
    
    // API requests - Network First with short cache
    if (isAPIRequest(request)) {
      return await networkFirst(request, API_CACHE);
    }
    
    // Images - Cache First with fallback
    if (isImageRequest(request)) {
      return await cacheFirst(request, CACHE_NAME);
    }
    
    // Everything else - Network First
    return await networkFirst(request, CACHE_NAME);
    
  } catch (error) {
    console.error('Mobile SW: Request failed:', error);
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html') || 
             new Response('Offline - Novel Engine unavailable', {
               status: 503,
               statusText: 'Service Unavailable'
             });
    }
    
    // Return error for other requests
    return new Response('Network Error', { status: 503 });
  }
}

// Cache First strategy - good for static assets
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Check if cache is still valid
    const cacheTime = await getCacheTimestamp(request, cacheName);
    const maxAge = getMaxAge(request);
    
    if (Date.now() - cacheTime < maxAge) {
      return cachedResponse;
    }
  }
  
  // Fetch from network and update cache
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      await updateCache(request, networkResponse.clone(), cacheName);
    }
    
    return networkResponse;
  } catch (error) {
    // Return cached version even if expired
    return cachedResponse || Promise.reject(error);
  }
}

// Network First strategy - good for dynamic content
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      await updateCache(request, networkResponse.clone(), cacheName);
    }
    
    return networkResponse;
  } catch (error) {
    // Fall back to cache
    const cachedResponse = await caches.match(request);
    return cachedResponse || Promise.reject(error);
  }
}

// Cache management utilities
async function updateCache(request, response, cacheName) {
  const cache = await caches.open(cacheName);
  
  // Implement cache size limit
  await enforceCacheLimit(cache, cacheName);
  
  // Store with timestamp
  const responseWithTimestamp = new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: {
      ...response.headers,
      'sw-cache-timestamp': Date.now().toString()
    }
  });
  
  await cache.put(request, responseWithTimestamp);
}

// Enforce cache size limits for mobile
async function enforceCacheLimit(cache, cacheName) {
  const keys = await cache.keys();
  const maxEntries = getMaxEntries(cacheName);
  
  if (keys.length >= maxEntries) {
    // Remove oldest entries (simple FIFO for now)
    const entriesToRemove = keys.slice(0, keys.length - maxEntries + 10);
    
    await Promise.all(
      entriesToRemove.map(key => cache.delete(key))
    );
    
    console.log(`Mobile SW: Removed ${entriesToRemove.length} entries from ${cacheName}`);
  }
}

// Get cache timestamp
async function getCacheTimestamp(request, cacheName) {
  const cache = await caches.open(cacheName);
  const response = await cache.match(request);
  
  if (response) {
    const timestamp = response.headers.get('sw-cache-timestamp');
    return timestamp ? parseInt(timestamp) : 0;
  }
  
  return 0;
}

// Helper functions
function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.match(/\.(js|css|woff2?|png|jpg|jpeg|gif|svg|ico)$/);
}

function isAPIRequest(request) {
  const url = new URL(request.url);
  return API_PATTERNS.some(pattern => pattern.test(url.pathname));
}

function isImageRequest(request) {
  const url = new URL(request.url);
  return url.pathname.match(/\.(png|jpg|jpeg|gif|svg|webp)$/);
}

function getMaxAge(request) {
  if (isStaticAsset(request)) return CACHE_CONFIG.maxAge.static;
  if (isAPIRequest(request)) return CACHE_CONFIG.maxAge.api;
  if (isImageRequest(request)) return CACHE_CONFIG.maxAge.images;
  return CACHE_CONFIG.maxAge.static;
}

function getMaxEntries(cacheName) {
  if (cacheName === STATIC_CACHE) return CACHE_CONFIG.maxEntries.static;
  if (cacheName === API_CACHE) return CACHE_CONFIG.maxEntries.api;
  return CACHE_CONFIG.maxEntries.images;
}

// Background sync for mobile
self.addEventListener('sync', event => {
  console.log('Mobile SW: Background sync:', event.tag);
  
  if (event.tag === 'mobile-cache-cleanup') {
    event.waitUntil(cleanupExpiredCaches());
  }
});

// Cleanup expired cache entries
async function cleanupExpiredCaches() {
  const cacheNames = [CACHE_NAME, STATIC_CACHE, API_CACHE];
  
  for (const cacheName of cacheNames) {
    try {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      
      for (const request of keys) {
        const cacheTime = await getCacheTimestamp(request, cacheName);
        const maxAge = getMaxAge(request);
        
        if (Date.now() - cacheTime > maxAge) {
          await cache.delete(request);
          console.log(`Mobile SW: Removed expired cache entry: ${request.url}`);
        }
      }
    } catch (error) {
      console.error(`Mobile SW: Failed to cleanup cache ${cacheName}:`, error);
    }
  }
}

// Message handling for cache management
self.addEventListener('message', event => {
  const origin = event.origin || (event.source && 'url' in event.source ? new URL(event.source.url).origin : null);
  if (origin !== self.location.origin) return;
  if (!event.data) return;

  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(clearAllCaches());
    if (event.ports && event.ports[0]) {
      event.ports[0].postMessage({ success: true });
    }
  }

  if (event.data.type === 'GET_CACHE_STATS') {
    event.waitUntil(getCacheStats().then(stats => {
      if (event.ports && event.ports[0]) {
        event.ports[0].postMessage(stats);
      }
    }));
  }
});

// Clear all caches
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(cacheNames.map(name => caches.delete(name)));
  console.log('Mobile SW: All caches cleared');
}

// Get cache statistics
async function getCacheStats() {
  const stats = {};
  const cacheNames = [CACHE_NAME, STATIC_CACHE, API_CACHE];
  
  for (const cacheName of cacheNames) {
    try {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      stats[cacheName] = keys.length;
    } catch (error) {
      stats[cacheName] = 0;
    }
  }
  
  return stats;
}

console.log('Mobile SW: Service Worker loaded and ready');
