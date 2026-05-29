// fitness/src/sw.js
const CACHE_NAME = 'niuyeye-fitness-v6';
const ASSETS = [
  './',
  './index.html',
  './logo.png',
  './style.css',
  './theme.css',
  './manifest.json',
  './sections/dashboard.html',
  './sections/assessment.html',
  './sections/training.html',
  './sections/nutrition.html',
  './sections/recovery.html',
  './sections/consult.html',
  './js/app.js',
  './js/features/dashboard.js',
  './js/features/assessment.js',
  './js/features/training.js',
  './js/features/nutrition.js',
  './js/features/recovery.js',
  './js/features/consult.js',
  './js/features/exercise-db.js',
  './js/lib/agentClient.js',
  './js/lib/calculator.js',
  './js/lib/training.js',
  './js/lib/nutrition.js',
  './js/lib/recovery.js',
  './js/lib/consult.js',
  './js/lib/db.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return response;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
