const CACHE_NAME = "aksa-sacco-v3";
const ASSETS_TO_CACHE = [
  "/",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/maskable-512.png",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        }),
      );
    }),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return (
        cachedResponse ||
        fetch(event.request)
          .then((response) => {
            return response;
          })
          .catch(() => {
            // Optional fallback for offline navigation
            if (event.request.mode === "navigate") {
              return caches.match("/");
            }
          })
      );
    }),
  );
});
