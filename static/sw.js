// Service worker mínimo (habilita PWA / "instalar na tela inicial").
// Estratégia: network-first, sem cache agressivo (dados de ponto devem ser sempre atuais).
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', function(e){
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
