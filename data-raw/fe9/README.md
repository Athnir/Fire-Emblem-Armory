# Path of Radiance (FE9) game files

Extracted from the user's own disc (NA, GFEE01) with Dolphin: right-click the game, Properties >
Filesystem > Extract Entire Disc. The files stay on the user's PC (default path in
`scripts/fe9_files.py`, or set `FE9_FILES`) and are never committed; only data built from them is.

GameCube files are big-endian.

- `Mess/*.m` (text): header `size, data size, 0, count`; text at 0x20; then `count` pairs of
  `(text offset, label offset)`; then the labels (`MIID_IRONSWORD` -> "Iron Sword").
- `FE8Data.bin` (main data): data at 0x20, pointers are offsets from there. Items are 96-byte records:
  - 0 `IID_`, 4 `MIID_` (name label), 8 `MH_I_` (description label), 12 weapon type
    (`sword`, `rod`, `flame`...), 20 rank (`E`-`S`, `N` = one character only);
  - 24-44 rule flags (`twice`, `poison`, `crit0`, `infinity`, `sealcrit`, `heroonly`...),
    48-52 effectiveness (`fly`, `armor`, `knight`, `beast`, `dragon`, `alize`), 56 effect id
    (`EID_LIGHT...` marks a light tome; staves share the `rod` type);
  - 64 price per use (u16), 66 uses, 67 Mt, 68 Hit, 69 Wt, 70 Crit, 71-72 range (255 = Mag/2),
    74 weapon EXP, 75-82 stat bonuses (HP, Str, Mag, Skl, Spd, Lck, Def, Res).

Generator: `scripts/build-fe9-items.py` writes `src/data/fe9/fe9Weapons.ts`. It was checked against
Serenes Forest's FE9 weapon tables; where they differ (Venin Lance's rank, Rescue's weapon EXP) the
game data wins.

## Rules found in the program (`sys/main.dol`)

- Effectiveness: weapon targets and class attributes are bit sets built from the same names (mage 1,
  fly 2, knight 4, armor 8, alize 0x10 = laguz, human 0x20, beast 0x40, dragon 0x80, bird 0x100). When
  they overlap (0x80092dc4), the weapon's Mt is doubled (0x801a9084: `slwi 1`), forging included.
- Selling (0x801941dc) pays half of price per use x uses left, rounded down; items with the `valuable`
  flag are refused.

## The forge

- `shop/shopitem_{n,h,m}.bin` (Easy/Normal, Hard, and the Japanese release's Maniac): a block of words
  at 0x20 (header `size, data size, pointer count, name count`), then the offsets of the words that are
  pointers, then `(data offset, name offset)` pairs naming each table, then the names. `WSHOP_ITEMS_Cnn`
  and `ISHOP_ITEMS_Cnn` are the base's weapon and item shops, `FSHOP_ITEMS_Cnn` the forge's base weapons
  as `(IID or 0, material)` pairs. `nn` is the chapter's file number (`MCTnn` in `common.m`: 09 is
  Ch.8, 29 is Ch.27-2, 31 the Endgame). A chapter with empty shops has no base (Ch.27-2).
- The price is in the program, not the data: `sys/main.dol`, function 0x8001c284. It takes the base
  item, its uses and the steps forged (Mt +1, Hit +5, Crit +3, Wt -1 each) and works on a value per
  stat: Mt, Hit, Crit + 10, and 23 - Wt. Each forged stat adds
  `uses x price per use x |new value^2 - old value^2| / old value^2`; the sum is multiplied by 2.5 and
  truncated (single-precision floats). The caller (0x801b15f4) adds the base weapon's price.
- The limits (Mt +5, Hit +25, Crit +9, Wt -5 but not below 1) are from Serenes Forest's forging page.
  Its costs match the formula except two Wt entries one digit off (Slim Lance 855G, Iron Axe 614G;
  the formula gives 885G and 619G).

`scripts/build-fe9-items.py` adds each base weapon's forge chapters; `src/logic/fe9Forge.ts` does the price.

## Maps

`scripts/build-fe9-maps.py` writes `src/data/fe9/fe9Maps.ts` and `fe9Terrain.ts`. Chapter file `Cnn` (and
`MCTnn`, `bmapNN`) is the chapter before it in the game's numbering: 01 the Prologue, 02 Ch.1, 29 Ch.27-2,
31 the Endgame.

- `zmap/bmapNN/*.cmp` are Nintendo LZ10 (`0x10`, 24-bit size) around a `pack` archive (`'pack'`, u16
  count, then 16-byte entries: 0, name offset, data offset, size). `fe9_files.lz10` / `unpack`.
- `map.cmp` -> `map.bin`, pointer-relocated like the shop files. `mapcapacity` starts with the width and
  height (u16s); `panelindex` is one u16 per tile (top row first) into `uniquepanel`, 12-byte records
  whose third word points at the tile's terrain name (`平地２` is a variant of `平地`, Plain).
- Terrain: FE8Data.bin has a table of 12-byte records (name, `MT_` label, stats pointer) starting at
  `移動不可`. Stats: avoid, Def, ..., heal % (byte 6), then one movement cost per movement type (15, 255 =
  can't enter). A class's movement type is byte 66 of its 100-byte `JID_` record; types with the same
  costs everywhere form the nine groups Serenes Forest lists.
- `dispos.cmp` -> `dispos_n.bin` (Easy/Normal), `_h` (Hard), `_m` (the Japanese Maniac), `_c` (every
  difficulty). Named groups: a count byte, then 108-byte units: 0 PID, 4 JID, 12-24 weapons, 28-40 items,
  44-60 skills, 76-88 AI, 92 where it comes from (x, y), 94 where it stands (x, y), 96 level, 97 side
  (0 player, 1 enemy, 2-3 other armies), 104-107 a drop flag per item slot. Coordinates count from the
  top-left (0, 0); the app counts from the bottom-left (1, 1).
- Chapter script (`Scripts/Cnn.cmb`, read by `fe9_cmb.py`): `FinalDisposition` places the starting
  groups; `mikata_c` holds your deployment tiles; `UnitForcedSallyByPID` names must-deploy units. Turn
  events (trigger kind 3: first turn, last turn, phase 0 player / 1 enemy / 2 ally) and area events
  (kind 4: x1, y1, x2, y2, 0 player / 1 enemy) bring in `z##`/`zoen` groups; `Normal()`/`Hard()` checks
  limit some to one difficulty. Tile events (kind 5: x, y, type) are villages (9, `MindGetItem`), doors
  (11), chests (12), seize (13), escape (14), arrive (41) and bandits razing a village (37).
- The chapter table in FE8Data.bin (96-byte records from `MCT01`) gives each chapter's win (`MW_`) and
  lose (`ML_`) labels, an extra loss and Easy's own turn limits; `BMSetTerm` in the script changes them
  section by section (Ch.17).

- Fences are 3D models, not terrain: `mapbuilddesc` lists the models (name pointers), `mapbuildinst` places
  them in 12-byte records (x, y, rotation in the top two bits, model index). A `fence_*` model stands on
  the tile's west (0x00), east (0x80), north (0x40) or south (0xC0) side.
- Tile corner heights: each `uniquepanel` record starts with four signed u16 corner heights, shared with
  the neighbouring tiles.
- Talks (trigger kind 8) name both speakers by PID string offset; a talk recruits whoever it passes to
  `UnitTransferToForceByPID`. `UnitEscapeByPID` in the openings removes units before the battle (Nasir
  in Ch.11); `UnitCheckLiveByPID` branches in FinalDisposition choose between groups (Gatrie or a
  soldier in Ch.13). `SetFragile(x, y, HP)` makes a door or wall breakable; `SetRock(x, y, direction,
  id)` places Ch.25's boulders. Their rolling paths aren't in the data files, so they follow Serenes
  Forest's falling-rocks diagram (its start tiles match the script's).
- Hidden items (only Ch.15's desert): an area event (kind 4) that rolls `GetRnd(101)` against the unit's
  Skill (Thieves and Assassins always win) and gives an item with `MindGetItem`. A one-tile area that sets
  a flag a later event tests before `UnitTransferToForceByPID` is Stefan's spot (Lethe or Mordecai must
  reach it first; he brings the Vague Katti).
- Ch.17 is four sections on one map: `Opening18_2`-`_4` start each later section (new enemies, the goal
  via `BMSetTerm`, your chosen reinforcements via `mikata_zoen_0N`), and the reinforcement handlers test
  the `セクションN` flags. The app shows each section as its own map. A handler with no section flag
  belongs to whichever section's grid its units land in (Tibarn's hawks, in section 4).
- How much of the map is playable isn't in `map.bin` (the terrain runs on past the edge). Each map is
  cropped to the grid that fireemblemwod.com's in-game overview shots draw over the usable tiles
  (`PLAYABLE` in `build-fe9-maps.py`), fitted to game coordinates by matching the shots' unit markers.
  Units parked off that grid only watch (Haar and his wyverns in Ch.11). Maps whose shot has no grid
  lines (Ch.10, Ch.15, Ch.23, Ch.27-2), and a few edges the fit read a tile off, were set by hand from
  the game; the Prologue keeps the old crop (every tile a unit can walk to).
- A map with no prep screen (no `FinalDisposition`) is set up by its opening scene. Its `event` groups
  are only in the scene (Ena in Ch.27-2), and an opening's `InstantDisposSetMode(mikata_*)` puts your
  units on fixed tiles (Mist beside Ike in Ch.27-2; Oscar, Boyd and Titania in Ch.1).
- Ch.17's sections 3 and 4: Ike carries Leanne throughout, so she isn't drawn. The ruins' building
  tiles are shown as rubble (the same costs: fliers only).

Checked against the Fire Emblem Wiki's enemy counts; the exceptions are listed in
`src/logic/__tests__/fe9Maps.test.ts`.
