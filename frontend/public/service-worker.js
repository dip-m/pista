// Service Worker for Pista PWA
const CACHE_NAME = 'pista-v1';
const RUNTIME_CACHE = 'pista-runtime-v1';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.log('Cache install error:', err);
        // Don't fail installation if some assets fail to cache
      });
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => {
            return cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE;
          })
          .map((cacheName) => {
            return caches.delete(cacheName);
          })
      );
    })
  );
  // Take control of all pages immediately
  return self.clients.claim();
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.open(RUNTIME_CACHE).then((cache) => {
      return fetch(event.request)
        .then((response) => {
          // Cache successful responses
          if (response && response.status === 200) {
            // Clone the response because it can only be consumed once
            cache.put(event.request, response.clone());
          }
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return cache.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // If not in cache and network failed, return offline page or error
            if (event.request.destination === 'document') {
              return cache.match('/').then((indexPage) => {
                return indexPage || new Response('Offline', { status: 503 });
              });
            }
            return new Response('Offline', { status: 503 });
          });
        });
    })
  );
});

// Handle background sync (for offline message queuing)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages() {
  // This would sync queued messages when connection is restored
  // Implementation depends on your message queueing strategy
  console.log('Syncing messages...');
}
