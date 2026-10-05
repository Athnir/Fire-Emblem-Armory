# Fates Armory

A Fire Emblem Fates weapon database and Smithy forge planner: every weapon's stats, effects,
route availability and shop price, plus forge-rank stats and mineral/copy costs up to +7. Everything
runs client-side and works offline once installed.

**Live app:** https://athnir.github.io/Fire-Emblem-Fates-Armory/

## Installing

The live link above is a Progressive Web App (PWA). It installs like a native app straight from the
browser, with no app store needed, and gets its own window, icon and offline access.

### Windows
Either:
- Open the link in **Chrome** or **Edge** → click the **install icon** (a monitor with a down arrow)
  at the right side of the address bar → **Install**, or
- Run the portable `Fates Armory 0.0.0.exe` built by `npm run dist:win` (no installer; just run it).

### Mac / Linux
Open the link in **Chrome** (or another Chromium-based browser) → same install icon in the address
bar → **Install**.

### Android
Open the link in **Chrome** → tap the **⋮ menu** → **Install app** (or **Add to Home screen**,
depending on Chrome version).

### iPhone / iPad
Open the link in **Safari** specifically (not Chrome/Firefox on iOS) → tap **Share** →
**Add to Home Screen**.

## Development

```bash
npm install
npm run dev        # dev server on port 5174, reachable from a phone on the same network
npm run test       # run the test suite
npm run build      # production build (web)
npm run dist:win   # build the Windows portable .exe into release/
```

Pushing to `main` deploys to GitHub Pages via `.github/workflows/deploy-pages.yml`.
