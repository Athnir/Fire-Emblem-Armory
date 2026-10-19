// Electron main process. Kept as plain CommonJS (.cjs) since package.json has "type": "module" —
// Electron's main process loads fine as ESM too, but .cjs sidesteps having to convert require()
// calls (fs/path/http/electron) to import syntax for no real benefit here.
const { app, BrowserWindow } = require('electron')
const http = require('node:http')
const fs = require('node:fs')
const path = require('node:path')

// Serves the built dist/ folder over a local HTTP server rather than loading index.html directly
// via file://. The app's own asset references (icons, portrait art, JS/CSS bundle) are root-relative
// paths (e.g. "/art/...") that only resolve correctly against an http(s) origin — file:// has no
// concept of "root", so those requests would 404. A tiny built-in static server sidesteps needing
// to change the shared Vite `base` config (which the GitHub Pages / PWA deploy targets also use).
const DIST_DIR = path.join(__dirname, '..', 'dist')

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

function startStaticServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(req.url.split('?')[0])
      let filePath = path.join(DIST_DIR, urlPath === '/' ? '/index.html' : urlPath)
      // SPA fallback: any path that doesn't map to a real file (client-side routing, if ever added)
      // serves index.html instead of a bare 404, matching Vite's own dev-server/preview behavior.
      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(DIST_DIR, 'index.html')
      }
      const ext = path.extname(filePath)
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(500)
          res.end('Server error')
          return
        }
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' })
        res.end(data)
      })
    })
    // Port 0 -> OS picks any free port, avoiding collisions with a dev server that might also be
    // running on this machine (e.g. the Vite dev server on 5174 during active development).
    server.listen(0, '127.0.0.1', () => resolve(server.address().port))
  })
}

async function createWindow() {
  const port = await startStaticServer()
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
  win.loadURL(`http://127.0.0.1:${port}/`)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
