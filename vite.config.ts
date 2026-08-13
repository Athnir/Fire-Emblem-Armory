import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(() => ({
  // GitHub Pages serves this project at a sub-path (github.io/<repo-name>/), not the domain root.
  base: process.env.GITHUB_PAGES ? '/Fire-Emblem-Fates-Armory/' : '/',
  server: {
    host: true,
    port: process.env.PORT ? Number(process.env.PORT) : 5174,
  },
  preview: {
    host: true,
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
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
        ],
      },
    }),
  ],
}))
