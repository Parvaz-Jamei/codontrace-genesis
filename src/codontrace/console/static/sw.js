const CACHE_NAME = 'genesis-console-atlas-v3';
const STATIC_ASSETS = ['/', '/index.html', '/simulation.html', '/manifest.webmanifest', '/assets/icon-192.png', '/assets/icon-512.png'];
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).catch(() => undefined));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith('genesis-console-') && key !== CACHE_NAME) await caches.delete(key);
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (url.origin !== self.location.origin || request.method !== 'GET') return;
  if (url.pathname.startsWith('/api/')) { event.respondWith(fetch(request)); return; }
  const navigation = request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html');
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    if (navigation) {
      // Network first: a fresh deployment must not show the old menu on first visit.
      try { const response = await fetch(request); if (response.ok) await cache.put(request, response.clone()); return response; }
      catch { return (await cache.match(request)) || new Response('Console unavailable offline', {status: 503}); }
    }
    const cached = await cache.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok && response.type === 'basic') await cache.put(request, response.clone());
    return response;
  })());
});
