// Este arquivo transforma o site num App instalável
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Instalado com sucesso!');
});

self.addEventListener('fetch', (e) => {
    // No futuro podemos fazer o app funcionar até sem internet aqui!
}); 