/* 四级词库 service worker：离线可背 */
const CACHE = "cet4-v14";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css?v=14",
  "./app.js?v=14",
  "./words.md",
  "./manifest.webmanifest",
  "./icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // 导航：网络优先，离线回 index
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const copy = r.clone();
          caches.open(CACHE).then((c) => c.put("./index.html", copy)).catch(() => {});
          return r;
        })
        .catch(() => caches.match("./index.html"))
    );
    return;
  }

  // 词库：网络优先，保证加词后能看到
  if (url.pathname.endsWith("/words.md")) {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const copy = r.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
          return r;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // 静态资源：先给缓存，再后台更新
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const network = fetch(e.request)
        .then((r) => {
          if (r.ok) {
            const copy = r.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
          }
          return r;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
