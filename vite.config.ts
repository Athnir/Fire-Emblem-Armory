import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(() => ({
  // GitHub Pages serves this project at a sub-path (github.io/<repo-name>/), not the domain root.
  // Gated on an explicit env var (set by .github/workflows/deploy-pages.yml) rather than "is this a
  // production build", because `npm run dist:win` also runs `vite build`, and the Electron app's own
  // local static server (electron/main.cjs) serves dist/ at its root -- the sub-path would 404 there.
  base: process.env.GITHUB_PAGES ? '/Fire-Emblem-Fates-Armory/' : '/',
  // host: true makes the dev server reachable from a phone on the same Wi-Fi; allowedHosts adds the
  // Tailscale MagicDNS name, which Vite otherwise rejects as an unknown Host header.
  // 5174/4174 rather than Vite's 5173/4173 defaults so this can run alongside the Unit Planner.
  server: {
    host: true,
    port: process.env.PORT ? Number(process.env.PORT) : 5174,
    allowedHosts: ['grantpc.tailaa1e6c.ts.net'],
  },
  preview: {
    host: true,
    port: 4174,
    allowedHosts: ['grantpc.tailaa1e6c.ts.net'],
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff,woff2}'],
      },
      manifest: {
        name: 'Fates Armory',
        short_name: 'Armory',
        description: 'Fire Emblem Fates weapon database, forging planner, and route-availability reference',
        theme_color: '#7c3aed',
        background_color: '#16171d',
        display: 'standalone',
        // Relative paths resolve against the manifest's own location, so they work at both the domain
        // root and the GitHub Pages sub-path. If the icon artwork ever changes after the app has been
        // installed on Android, give the files NEW names (e.g. -v2): Chrome's WebAPK minting server
        // keeps its own icon cache that a same-named replacement can sit stuck behind indefinitely.
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: 'icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
}))
