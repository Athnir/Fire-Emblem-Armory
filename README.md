# Fire Emblem Armory

A Fire Emblem companion, game by game: pick a game and get its weapons and forging, true hit
calculator and maps together. Everything runs client-side and works offline once installed.

- **Fire Emblem Fates** (done): every weapon's stats, effects, route availability and prices, forge
  ranks to +7, maps of every chapter, paralogue and DLC map, and what each support partner gives.
- **Fire Emblem: Path of Radiance** (in progress): every weapon's stats and rules, the forge (costs
  worked out the way the game does, and which chapters offer each base weapon), every chapter's map
  (units on Easy/Normal and Hard, reinforcements and when they come, chests, villages, doors and goals),
  true hit and supports.

**Live app:** https://athnir.github.io/Fire-Emblem-Armory/

## Where the data comes from

- **The game's own files**, dumped from a copy of the game and its downloads (never shipped or
  committed; only data derived from them is). Every map's terrain, units, item drops, reinforcement
  timing, objectives, chests, villages and Dragon Veins, every terrain's costs, and every weapon's
  stats, ranks, prices and effectiveness. The generators are in `scripts/` and the formats in `data-raw/fates/README.md` and
  `data-raw/fe9/README.md`. Path of Radiance's forge prices follow the game's own price routine.
- **[Fire Emblem Wiki](https://fireemblemwiki.org/)**: chapter pages and minimaps, used to check
  enemy counts and for notes the files don't spell out, plus Path of Radiance's affinity table.
- **[Serenes Forest](https://serenesforest.net/fire-emblem-fates/)**: weapon descriptions, shop
  stock, forging costs (and Path of Radiance's forge limits), the My Castle rank-reward table and Fates' support bonus and pair-up tables.
- **[fireemblemwod.com](https://www.fireemblemwod.com/ENG_fe9.htm)**: Path of Radiance's
  in-game overview shots, whose grid lines mark how much of each map is playable, plus its trial map
  overviews, Ch.23's traps and Ch.25's falling-stone routes.

Where the sources disagree, the game's files win.

## Installing

The live link above is a Progressive Web App (PWA). It installs like a native app straight from the
browser, with no app store needed, and gets its own window, icon and offline access.

### Windows
Either:
- Open the link in **Chrome** or **Edge** → click the **install icon** (a monitor with a down arrow)
  at the right side of the address bar → **Install**, or
- Run the portable `Fire Emblem Armory 0.0.0.exe` built by `npm run dist:win` (no installer; just run it).

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
