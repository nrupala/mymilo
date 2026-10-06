/* MyMilo service worker — app-shell caching that respects Cloudflare Access.
 *
 * Page loads (navigations) are NETWORK-FIRST: the Access login completes via
 * redirects that set session cookies, and a cached shell must never swallow
 * that handshake. The fresh shell is cached for offline use (but never the
 * Access login page itself).
 * API calls (/v1/*, /health) always go to the network: chat, routines, and
 * documents are live server state and are never served stale.
 * Static assets are cache-first.
 */
const SHELL_CACHE = 'mymilo-shell-v2';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
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

  // Navigations: network first so the Access login handshake (redirects +
  // session cookies) always completes; fall back to the cached shell offline.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then((res) => {
        if (res.ok && !res.url.includes('cloudflareaccess.com')) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put('/', copy));
        }
        return res;
      }).catch(() => caches.match('/'))
    );
    return;
  }

  // Static assets: cache first.
  event.respondWith(
    caches.match(event.request).then((hit) => {
      const miss = fetch(event.request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || miss;
    })
  );
});
