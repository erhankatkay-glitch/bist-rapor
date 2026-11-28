// KATKAY PWA servis çalışanı: uygulama kabuğu önbellekten (çevrimdışı açılır), veri önce ağdan, olmazsa son kayıtlı kopyadan.
const SURUM = "katkay-v1";
const KABUK = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png", "./favicon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SURUM).then(c => c.addAll(KABUK)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== SURUM).map(x => caches.delete(x)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  const veri = u.hostname.endsWith("githubusercontent.com") || u.hostname.includes("binance");
  if (veri) {   // ağ önce; başarısızsa önbellek (sorgu parametresi ?t= yok sayılır)
    const anahtar = u.origin + u.pathname + (u.hostname.includes("binance") ? u.search : "");
    e.respondWith(fetch(e.request).then(r => {
      if (r.ok) { const k = r.clone(); caches.open(SURUM).then(c => c.put(anahtar, k)); }
      return r;
    }).catch(() => caches.match(anahtar)));
    return;
  }
  if (u.origin === location.origin) {   // kabuk: önbellek önce, arkada tazele
    e.respondWith(caches.match(e.request, {ignoreSearch: true}).then(c => {
      const ag = fetch(e.request).then(r => { if (r.ok) { const k = r.clone(); caches.open(SURUM).then(x => x.put(e.request, k)); } return r; }).catch(() => c);
      return c || ag;
    }));
  }
});
