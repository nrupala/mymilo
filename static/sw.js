/* MyMilo service worker — app-shell caching only.
 *
 * The shell (pages, CSS, manifest, icons) is cached so the app opens
 * instantly and survives flaky networks. API calls (/v1/*, /health)
 * always go to the network: chat, routines, and documents are live
 * server state and are never served stale. If the network is down,
 * API calls fail fast and the page shows its own offline state.
 */
const SHELL_CACHE = 'mymilo-shell-v1';
const SHELL = [
  '/',
  '/static/style.css',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return; // let POSTs (chat etc.) through
  if (url.pathname.startsWith('/v1/') || url.pathname === '/health') return; // live API: network only
  event.respondWith(
    caches.match(event.request).then((hit) => {
      const miss = fetch(event.request).then((res) => {
        if (res.ok && (url.pathname === '/' || url.pathname.startsWith('/static/'))) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || miss;
    })
  );
});
