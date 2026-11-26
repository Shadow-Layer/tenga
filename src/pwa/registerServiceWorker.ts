export async function registerServiceWorker(): Promise<void> {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return
  if (!window.isSecureContext) return
  try {
    await navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, {
      scope: import.meta.env.BASE_URL,
    })
  } catch (error) {
    console.warn('Tenga app-shell offline support could not be registered.', error)
  }
}
