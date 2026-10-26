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

## The weapon triangle and weapon rank bonuses (`scripts/build-triangles.py` -> `src/data/weapons/fatesTriangle.ts`)

Both tables are in `GameData.bin`, found from the program code. The code was read from a memory dump of the running game (Azahar), so
its addresses are noted here but not re-read by the script:
- The header's word at +0x3c points to the rank thresholds (251, 161, 96, 51, 21, 1: weapon experience for S down to E;
  `0x5090bc` turns experience into a rank index, 0 = S).
- +0x40 points to the rank bonuses: 8 weapon types (sword, lance, axe, dagger, bow, tome, staff, stone; each Hoshidan type counts as
  its pair) x 6 ranks from S down x 2 signed bytes. The attack routine (0x5341a0) adds the first byte and the hit routine
  (0x532ddc: weapon Hit + (3 x Skl + Lck) / 2) adds the second. For staves, the healing routine adds the first and the staff's hit
  the second. Both routines skip it when the unit is at a triangle disadvantage.
- +0x44 points to the triangle's worth by rank (S 2 Atk / 20 Hit, A 1/15, B 1/10, C 0/10, D 0/5, E 0/5), followed by an 8 x 8
  matrix of +1 / -1 / 0 (attacking type x 8 + defending type, read at 0x347abc). Swords and tomes beat axes and bows; axes and bows
  beat lances and daggers; lances and daggers beat swords and tomes. Staves and stones are outside it.
- 0x347a68 stores the matrix value per side. A weapon with the item skill `ISID_3すくみ反転` (the "Reverses the weapon triangle"
  weapons) makes it -1 for its side and flips the other's; a negative result is doubled, so one reaver gives -2 / +2 and two cancel.
- 0x3499e0 (attack) and 0x3490a4 (hit): the value x the table's attack or hit for the rank of the advantaged side's weapon (the unit's
  own when the value is positive, the foe's when negative).

## My Castle shops and buildings (`scripts/build-fates-shops.py`)

- `castle/` in the cartridge romfs (copied next to the other files; its `.bch` models aren't needed) holds My Castle's data:
  `castle_building.bin.lz` (every building's levels, each level's unlock chapter per route at +0x34 Birthright, +0x38 Conquest and
  +0x3c Revelation of the level's record, plus model and sound names), `castle_join.bin.lz` (when the NPCs who aren't recruited
  join the castle: Felicia and Jakob from Chapter 15 on every route, Izana A18 / B22, Fuga C18, Yukimura A22, Flora B18 / C22),
  `CastlePerson.bin` (each person's food titles and accessory likes), `castle_food` and `castle_gemstone`.
- `src/data/weapons/fatesShops.ts`: the chapter each building level opens after is read from `castle_building.bin.lz`
  (Armouries and stores 6, 13, 20; Smithy 8, 14, 20), and the script checks Serenes Forest's tables agree. What each shop
  stocks at levels 1 to 3 (a number, or unlimited) isn't in any file we have, so it still comes from Serenes Forest's Dawn
  Armoury, Dusk Armoury, Rod Store, Staff Store and Smithy pages (needs a network connection).
- Not found in any file: what allies give in My Castle (the "!" gifts: the Raider weapons, named weapons, joke weapons) and what
  unlocks each by chapter. The wiki only says "obtained at random from a pool of possible items"; the unlock rules are probably
  in the program.
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

