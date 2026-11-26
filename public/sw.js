const SHELL_CACHE = 'tenga-app-shell-v1'
const SHELL_URLS = ['/', '/manifest.webmanifest', '/icons/tenga-icon.svg']
const API_PATH = /^\/api(?:\/|$)/i
const STATIC_ASSET_PATH = /^\/assets\/[^/]+\.(?:js|css|svg|png|webp|woff2?)$/i

function isSameOriginPublicGet(request, url) {
  return request.method === 'GET'
    && url.origin === self.location.origin
    && !API_PATH.test(url.pathname)
    && !request.headers.has('authorization')
}

function isPublicStaticResponse(response, contentType) {
  if (!response || !response.ok || response.type !== 'basic') return false
  const cacheControl = response.headers.get('cache-control') || ''
  if (/\b(private|no-store|no-cache)\b/i.test(cacheControl)) return false
  return (response.headers.get('content-type') || '').toLowerCase().includes(contentType)
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE)
    let shellDocument
    await Promise.all(SHELL_URLS.map(async (path) => {
      try {
        const request = new Request(new URL(path, self.location.origin), { credentials: 'omit' })
        const response = await fetch(request)
        const contentType = path.endsWith('.webmanifest') ? 'json' : path.endsWith('.svg') ? 'image/svg+xml' : 'text/html'
        if (isPublicStaticResponse(response, contentType)) {
          if (path === '/') shellDocument = await response.clone().text()
          await cache.put(path, response)
        }
      } catch {
        // The application remains usable online if a shell asset could not be cached.
      }
    }))
    const assets = [...(shellDocument || '').matchAll(/(?:src|href)=["']([^"']+\.(?:js|css))["']/gi)]
      .map((match) => new URL(match[1], self.location.origin))
      .filter((url) => url.origin === self.location.origin && STATIC_ASSET_PATH.test(url.pathname))
    await Promise.all(assets.map(async (url) => {
      try {
        const request = new Request(url, { credentials: 'omit' })
        const response = await fetch(request)
        const contentType = url.pathname.endsWith('.css') ? 'text/css' : 'javascript'
        if (isPublicStaticResponse(response, contentType)) await cache.put(url, response)
      } catch {
        // A missing build asset must not block application installation.
      }
    }))
    await self.skipWaiting()
  })())
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(keys.filter((key) => key.startsWith('tenga-app-shell-') && key !== SHELL_CACHE)
      .map((key) => caches.delete(key)))
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)
  if (!isSameOriginPublicGet(request, url)) return

  if (request.mode === 'navigate') {
    if (url.pathname !== '/') return
    event.respondWith((async () => {
      try {
        const response = await fetch(request)
        if (isPublicStaticResponse(response, 'text/html') && !url.search) {
          const cache = await caches.open(SHELL_CACHE)
          await cache.put('/', response.clone())
        }
        return response
      } catch {
        const cachedShell = await caches.match('/')
        if (cachedShell) return cachedShell
        return new Response('The app shell is not available offline yet. Reconnect and reload once.', {
          status: 503,
          headers: { 'Content-Type': 'text/plain; charset=utf-8' },
        })
      }
    })())
    return
  }

  if (STATIC_ASSET_PATH.test(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(SHELL_CACHE)
      const cachedAsset = await cache.match(request)
      if (cachedAsset) return cachedAsset
      const publicRequest = new Request(request, { credentials: 'omit' })
      const response = await fetch(publicRequest)
      if (isPublicStaticResponse(response, url.pathname.endsWith('.css') ? 'text/css' : url.pathname.endsWith('.js') ? 'javascript' : url.pathname.endsWith('.svg') ? 'image/svg+xml' : url.pathname.endsWith('.woff') || url.pathname.endsWith('.woff2') ? 'font' : 'image')) {
        await cache.put(request, response.clone())
      }
      return response
    })())
  }
})
