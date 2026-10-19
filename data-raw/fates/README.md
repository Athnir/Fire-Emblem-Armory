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
