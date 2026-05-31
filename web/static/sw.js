// Minimal service worker — installability + offline fallback
// v4.0-part-2 Sprint 8.2: skipWaiting + orientation unlock — cache bust v10
const CACHE = 'fas-v10';
const CORE = ['/'];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).catch(() => {}));
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k !== CACHE).map(k => caches.delete(k))
        )).then(() => self.clients.claim())
    );
});

// Sprint 8.2 — Page'den SKIP_WAITING mesajı gelirse yeni SW'yi hemen aktive et
self.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
    // Network-first, fallback to cache on offline
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
