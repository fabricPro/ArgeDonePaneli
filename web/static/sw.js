// Minimal service worker — installability + offline fallback
// v4.0-part-2 Sprint 8.6: PWA shortcuts + manuel yatay buton — cache bust v11
// v3.9: cross-origin isteklere (Supabase görsel CDN, Google Fonts) karışma — cache bust v12
const CACHE = 'fas-v12';
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
    // v3.9 — YALNIZ same-origin isteklere karış. Supabase görsel CDN'i ve Google
    // Fonts gibi cross-origin (özellikle no-cors / opaque) isteklere DOKUNMA;
    // aksi halde mobil/PWA'da görsel fetch'leri sessizce bozulabiliyordu.
    let sameOrigin = false;
    try { sameOrigin = new URL(e.request.url).origin === self.location.origin; }
    catch (_) { return; }
    if (!sameOrigin) return;
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
