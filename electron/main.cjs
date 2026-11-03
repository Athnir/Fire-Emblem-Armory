// Electron main process. Kept as plain CommonJS (.cjs) since package.json has "type": "module" —
// Electron's main process loads fine as ESM too, but .cjs sidesteps having to convert require()
// calls (fs/path/electron) to import syntax for no real benefit here.
const { app, BrowserWindow, protocol, session } = require('electron')
const fs = require('node:fs/promises')
const path = require('node:path')

// Serves the built dist/ folder from the app's own address, app://armory/, rather than loading index.html directly
// via file://. The app's own asset references (icons, the JS/CSS bundle) are root-relative paths (e.g. "/assets/...")
// that only resolve against an origin with a root — file:// has none, so those requests would 404 — and this keeps
// the shared Vite `base` config (which the GitHub Pages / PWA deploy targets also use) unchanged.
// The address must also stay the same from one launch to the next: the page keeps its settings (the game, each game's
// difficulty, the spoiler block's progress) per address. A local HTTP server on a new port every launch, as this used,
// forgot them all, and its offline service worker stored another full copy of the app each time. This scheme isn't
// allowed service workers (the page's registration fails quietly and the update button stays hidden): the files are
// already on disk, and a new version comes with a new build of the app.
const DIST_DIR = path.join(__dirname, '..', 'dist')
const ORIGIN = 'app://armory'

protocol.registerSchemesAsPrivileged([
  // standard: parsed like http (a host, root-relative paths); secure: a secure context like https; supportFetchAPI and
  // corsEnabled: the page's module scripts (Vite's crossorigin <script type="module">) and its dynamic imports load
  // through it.
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
])

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.webmanifest': 'application/manifest+json',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

async function serve(request) {
  let filePath = null
  try {
    filePath = path.join(DIST_DIR, decodeURIComponent(new URL(request.url).pathname))
  } catch {
    // A malformed address falls back to the page, like a missing file.
  }
  // SPA fallback: any path that doesn't map to a real file inside dist/ (client-side routing, if ever added) serves
  // index.html instead of a bare 404, matching Vite's own dev-server/preview behavior.
  const inside = filePath !== null && filePath.startsWith(DIST_DIR + path.sep)
  const stat = inside ? await fs.stat(filePath).catch(() => null) : null
  if (!stat || stat.isDirectory()) filePath = path.join(DIST_DIR, 'index.html')
  const data = await fs.readFile(filePath)
  return new Response(data, { headers: { 'Content-Type': MIME_TYPES[path.extname(filePath)] || 'application/octet-stream' } })
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    title: 'Fire Emblem Armory',
    icon: path.join(DIST_DIR, 'icons', 'icon-512.png'),
    autoHideMenuBar: true,
  })
  // index.html's own <title> otherwise overwrites the BrowserWindow title above as soon as the
  // page loads (they're kept in sync content-wise, but the page's title updates asynchronously
  // after load and would win the race without this).
  win.on('page-title-updated', (event) => event.preventDefault())
  win.loadURL(`${ORIGIN}/`)
}

app.whenReady().then(async () => {
  protocol.handle('app', serve)
  // Builds before app://armory/ left a service worker and a full copy of the app behind for every launch, each at its
  // own port, and the HTTP cache held what each port served. This build uses none of them (app:// responses aren't
  // HTTP-cached, and the page fetches nothing from the web), so clearing them all on start takes nothing it needs.
  await session.defaultSession.clearStorageData({ storages: ['serviceworkers', 'cachestorage'] })
  await session.defaultSession.clearCache()
  createWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
