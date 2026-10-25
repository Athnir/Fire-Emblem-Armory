# Raw Fates map data

Pre-processed source data for maps that haven't been built into `src/data/maps/` yet, so building
them later means reading these files instead of re-scraping. Nothing here is shipped in the app.

Sources: the [Fire Emblem Wiki](https://fireemblemwiki.org/) chapter pages and its
[Fates minimaps](https://fireemblemwiki.org/wiki/Category:Fates_maps) (6 px per tile). No images are
stored, only data derived from them.

## `<route>/wiki/<NN>-<Page>.json`

Condensed from each chapter page:

- `victory`, `defeat`, `dims` ([width, height]), `items` (where each item comes from), `vein` (the
  Dragon Vein section, coordinates as the wiki writes them: **rows counted from the top**, so convert
  with `y = height + 1 - row`), `joins` (characters joining or recruitable).
- `initial[difficulty]`: `total` starting enemies (pairs count as two), `faction` (the generic
  enemies' name), and `rows`: only the entries that matter for a map — named units, item droppers
  (`drops`) and pair / position notes ("Stands on a throne", "Paired up together"...). Generic
  enemies without any of those aren't listed individually.
- `reinforcements[difficulty]`: how many arrive. `other`: NPC / allied units.

## `<route>/minimap/<NN>.json`

Read off the minimaps in the browser with the helpers in `scripts/minimap-tools.js`:

- `difficulty[d].red`: `"x,y": pixels` for every tile with an enemy dot (bottom-left is 1,1).
  4 = one unit, 8 = a pair-up; other counts are usually the boss glow bleeding onto a tile.
  `blue` = player starting tiles, `green` = allied NPCs, `glow` = boss-glow centres.
  A difficulty missing from the file uses the next easier one's image (no separate image exists).
- `changes[variant].tiles`: tiles that differ between the normal image and an after-vein (`dv`),
  bridge or traps image.
- `guess`: a first-pass terrain letter per tile (top row first; legend in the file of chapter 13).
  It's a starting point only: every map is checked by eye against its minimap when it's built.

`python scripts/check-raw-maps.py` checks every file parses, sizes match, and each census adds up to
the wiki's enemy total.

## Status

- Conquest 13–27 and Endgame: wiki + minimap data done (2026-10-08); first-pass build in
  `src/data/maps/conquestLate.ts` (2026-10-09), still to be gone over map by map.
- Built into the app: shared chapters (Prologue–5) and all of Conquest (6–Endgame).

## `romfs/` (not in git)

Files dumped from your own copy of the game (cartridge romfs via GodMode9, plus the route and DLC
`.app` files from an emulator's SD folder). They're never committed; only data derived from them is.
Readers in `scripts/`:

- `fates_lz.py`: decompresses `.lz` files (0x13 header + LZ11).
- `ncch_romfs.py`: lists / extracts the romfs of a decrypted `.app`.
- `fates_terrain.py`, `fates_dispos.py`, `fates_text.py`, `fates_tricks.py`, `fates_movecost.py`:
  terrain grids, unit placements, English text, map gimmicks (Dragon Veins) and movement costs.
- `build-fates-terrain.py`: writes `src/data/maps/gameTerrain.ts` (grids, per-map terrain stats and
  each vein's tiles and patch). Prefixes: A = Birthright, B = Conquest, C = Revelation, 000-006 =
  shared chapters, X = paralogues, E = DLC (inside the DLC `.app` files).
- `build-fates-items.py`: writes `src/data/weapons/gameItems.ts` from the item table in
  `GameData.bin` (104-byte records) and each DLC item's own file. The weapon list is tested
  against it: Mt, Hit, Crit, Avoid, Dodge, range, rank, prices, uses, and what each weapon is
  effective against (a bitmask: 1 fliers, 2 dragons, 4 beasts, 8 armour, 16 monsters; weapon-type
  targets come from the item's description).

## My Castle shops and buildings (`scripts/build-fates-shops.py`)

- The cartridge dump has no My Castle building data (it's in the program, not the files we have), so
  `src/data/weapons/fatesShops.ts` is built from Serenes Forest's Dawn Armoury, Dusk Armoury, Rod Store, Staff Store and
  Smithy pages (needs a network connection): the chapter each building level opens after (Armouries and stores 6, 13, 20;
  Smithy 8, 14, 20) and each shop's stock at levels 1 to 3 (a number, or unlimited).
- Serenes' "Armourslayer" and "Short Bow" are the game's "Armorslayer" and "Mini Bow" (prices match); the script maps them.
- Not in any file we have: when each paralogue opens (the children's need their parents married) and the chapters the Yato
  evolves in (`src/data/weapons/fatesGifts.ts`, from the Fire Emblem Wiki, which agree with the chapter titles in the files).

## When characters join (`scripts/build-fates-joins.py`)

- `src/data/maps/fatesJoins.ts` is built from the chapter files for the fixed parents of the children's paralogues: the chapter
  each joins your army for good (a temporary guest isn't counted). Order of evidence: a script that hands the unit to the
  player (`UnitTransferByIndex(unit, 0)`) or a Support (recruit) group, from Chapter 6 on; else the chapter their run of Player /
  Event groups begins in (one missing chapter allowed; a run of only one or two chapters at the end counts as the run before it);
  a recruitable green unit (Ally) just before that run is the chapter. Jakob is left out: he joins in 6 or much later depending
  on Corrin's gender. A test checks every value against Serenes Forest's recruitment pages, and they all agree.
- A child's paralogue opens the chapter after their fixed parent's join (the table of fixed parents is in
  `src/data/maps/fatesStory.ts`; the chapter titles on the child's own page say who to talk to, which is that parent).
- Each story chapter's `kit` (`gameUnits.ts`) is what your own units start it holding: the items of the units in the Player /
  PlayerM / PlayerF groups of the chapter's placement file (Corrin's Bronze Sword in Chapter 1, Gunter's lance and Felicia's /
  Jakob's dagger and Heal from Chapter 2, Corrin's Yato from 6 on Birthright and Conquest and from 13 on Revelation). Paralogue and
  DLC maps aren't kept: they list whichever form of Yato that point of the game has. The spoiler block lists a weapon from the
  chapter it first appears in a kit.
- Foe-only Fates items (Kukris, Bölverk, Skadi, breaths, rocks, saws) come from the item table (`gameItems.ts`, whose
  `category` is the record's type byte at +0x10) minus every weapon on the player's lists (`src/data/weapons/foeOnly.ts`). Each
  map unit's `carries` (`gameUnits.ts`) is the placement files' non-drop item slots (five per unit, a pair's both); the weapon page
  places a foe-only weapon by the foes who carry it, and under the spoiler block from the first chapter whose map shows one at
  the start.

