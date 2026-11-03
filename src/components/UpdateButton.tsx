import { useEffect, useState } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'

type Status = 'idle' | 'checking' | 'downloading' | 'found' | 'latest' | 'failed'

const LABELS: Record<Status, string> = {
  idle: 'Check for updates',
  checking: 'Checking…',
  downloading: 'Downloading update…',
  found: 'Update now',
  latest: 'Up to date',
  failed: "Couldn't check",
}

/** When this version was built (published), in the device's own time. */
const BUILT = new Date(__BUILD_TIME__).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/**
 * Looks for a new version of the app only when tapped (the user's call): the service worker waits with what it downloads
 * (registerType 'prompt'), so nothing changes under you. A found version shows "Update now", and a second tap switches to it and
 * reloads, so one stray tap never reloads the page.
 */
export function UpdateButton() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration>()
  const [status, setStatus] = useState<Status>('idle')
  // `ready`: a new version has downloaded and waits. The browser may have fetched it on its own when the app opened; it's only
  // offered once a tap has looked.
  const {
    needRefresh: [ready],
    updateServiceWorker,
  } = useRegisterSW({ onRegisteredSW: (_url, r) => setRegistration(r) })

  useEffect(() => {
    if (ready && (status === 'checking' || status === 'downloading')) setStatus('found')
  }, [ready, status])

  // "Up to date" and "Couldn't check" go back to the button after a few seconds.
  useEffect(() => {
    if (status !== 'latest' && status !== 'failed') return
    const timer = setTimeout(() => setStatus('idle'), 4000)
    return () => clearTimeout(timer)
  }, [status])

  async function check() {
    if (!registration) return
    if (status === 'found') {
      // The waiting version takes over and the page reloads into it. On a first visit no worker controls the page yet, so the new
      // one has already taken over by itself: a reload is all it needs.
      if (registration.waiting) void updateServiceWorker()
      else window.location.reload()
      return
    }
    setStatus('checking')
    try {
      await registration.update()
    } catch {
      setStatus('failed')
      return
    }
    const coming = registration.installing
    if (coming) {
      setStatus('downloading')
      coming.addEventListener('statechange', () => coming.state === 'redundant' && setStatus('failed'))
    } else if (!registration.waiting) {
      setStatus('latest')
    }
    // A waiting version turns `ready` on (at once, or as soon as it's announced), which shows "Update now".
  }

  // No service worker (the dev server, or a browser without one): nothing to update.
  if (!registration) return null
  const busy = status === 'checking' || status === 'downloading'
  return (
    <button
      type="button"
      onClick={check}
      disabled={busy}
      title={`This version: ${BUILT}`}
      className={`rounded border px-2 py-1 text-sm ${
        status === 'found' ? 'border-emerald-500 bg-emerald-950 text-emerald-200' : 'border-neutral-700 bg-neutral-900 text-neutral-300'
      } ${busy ? 'opacity-70' : ''}`}
    >
      {LABELS[status]}
    </button>
  )
}
