# Fire Emblem Armory

A Fire Emblem companion, game by game: pick a game and get its weapons and forging, true hit
calculator, weapon triangle and maps together. Everything runs client-side and works offline once installed.

- **Fire Emblem: Mystery of the Emblem** (from the Japanese cartridge, with the English names of its translation patch: RPGuy96's and
  VincentASM's translation, Quirino's update and Robert of Normandy's current project, [fe3-translation](https://github.com/RobertTheSable/fe3-translation)):
  weapons and where each turns up in both books (drops and what foes carry included), true hit (its own scaled roll), supports, and
  every map of Book 1, Book 2 and the Endgame with its units, reinforcements and spawn points, recruits, chests, villages, houses,
  doors, shops, secret shops and hidden items. The game has no weapon triangle, so it has no triangle tab. Every table and event command
  was traced in the clean cartridge (Mesen and the game's own code); the patch's build files gave its text tables' addresses.
- **Fire Emblem: Genealogy of the Holy War** (from the Japanese cartridge, with Lil' Nordion's English names): weapons and
  where each turns up, true hit, the weapon triangle and leadership, and every chapter's map with its castles, villages and
  reinforcements.
- **Fire Emblem: Thracia 776** (from the Japanese cartridge, with Lil' Manster's English names): weapons and where each turns up
  (what foes carry included, since any foe can be captured), true hit, the weapon triangle, leadership and Charm, supports, and every
  chapter's and gaiden chapter's map with its units, reinforcements, recruits, chests, villages, doors, shops, escape points and when
  each gaiden chapter opens. The Lil' Manster team's public build files ([fe776br](https://github.com/famitino/fe776br), with Zane
  Avernathy's disassembly) and his [VoltEdge](https://github.com/ZaneAvernathy/VoltEdge) library named the tables, the event commands
  and the game's routines; each one used was checked in the clean cartridge. Lil' Manster's menu names are drawn from its own letter
  tiles, matched against the shapes of its team's font.
- **Fire Emblem: The Binding Blade** (from the Japanese cartridge, with the FE6 Localization patch's English names): weapons and
  where each turns up on both routes, true hit, the weapon triangle, supports, and every chapter's, gaiden chapter's and trial
  map's map with its units on Normal and Hard, reinforcements, recruits, chests, villages, shops and the desert's buried items.
- **Fire Emblem: The Blazing Blade** (from the North American cartridge): weapons and where each turns up in Lyn's, Eliwood's and
  Hector's stories, true hit, the weapon triangle, supports, and every chapter's map in each story with its units on Normal and Hard,
  reinforcements, recruits, chests, villages, shops and the gaiden chapters' conditions.
- **Fire Emblem: The Sacred Stones** (from the North American cartridge): weapons and where each turns up on Eirika's and Ephraim's
  routes (the world map towns' shops included), true hit, the weapon triangle, supports, and every chapter's, the Tower of Valni's and
  the Lagdou Ruins' maps with their units on Easy, Normal and Hard (each generic foe's level per difficulty), reinforcements, recruits,
  chests, villages, shops, the desert's buried items and the rewards an end scene gives on a condition. The FE8 decompilation project
  ([fireemblem8u](https://github.com/FireEmblemUniverse/fireemblem8u)) named the event commands; each one used was checked in the game's
  code.
- **Fire Emblem Fates** (done): every weapon's stats, effects, route availability and prices, forge
  ranks to +7, maps of every chapter, paralogue and DLC map, and what each support partner gives.
- **Fire Emblem: Path of Radiance** (in progress): every weapon's stats and rules, the forge (costs
  worked out the way the game does, and which chapters offer each base weapon), every chapter's map
  (units on Easy/Normal and Hard, reinforcements and when they come, chests, villages, doors and goals),
  true hit and supports.
- **Fire Emblem: Radiant Dawn** (in progress): every weapon's stats and rules, shops and bargains, the
  forge (costs the way the game works them out, and the Coin cards), true hit (checked in the game's
  code), supports and every chapter's map.

**Live app:** https://athnir.github.io/Fire-Emblem-Armory/

## Where the data comes from

- **The game's own files**, dumped from a copy of the game and its downloads (never shipped or
  committed; only data derived from them is). Every map's terrain, units, item drops, reinforcement
  timing, objectives, chests, villages and Dragon Veins, every terrain's costs, and every weapon's
  stats, ranks, prices and effectiveness. The generators are in `scripts/` and the formats in `data-raw/fates/README.md`,
  `data-raw/fe3/README.md`, `data-raw/fe4/README.md`, `data-raw/fe5/README.md`, `data-raw/fe6/README.md`, `data-raw/fe7/README.md`, `data-raw/fe9/README.md` and `data-raw/fe10/README.md`. Path of Radiance's forge prices follow the game's own price routine.
- **[Fire Emblem Wiki](https://fireemblemwiki.org/)**: chapter pages and minimaps, used to check
  enemy counts and for notes the files don't spell out, plus the Tellius games' affinity tables.
- **[Serenes Forest](https://serenesforest.net/fire-emblem-fates/)**: Mystery of the Emblem's and Thracia 776's staff effects (and
  Mystery of the Emblem's staff ranges and shop lists, checked against the game's), Thracia 776's weapon descriptions, shop
  stock, forging costs (and Path of Radiance's forge limits, Radiant Dawn's support rules), the My Castle rank-reward table and Fates' support bonus and pair-up tables.
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
