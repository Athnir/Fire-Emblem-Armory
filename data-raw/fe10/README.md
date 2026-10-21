# Radiant Dawn (FE10) game files

Extracted from the user's own disc with Dolphin (Properties > Filesystem > Extract Entire Disc). It's a
Wii disc, so the dump has a `DATA` partition (the game) and an `UPDATE` one (system update, unused).
The files stay on the user's PC and are never committed; only data built from them is.

Wii files are big-endian, like the GameCube's.

- `DATA/files/FE10Data.cms` is the main data, LZ10-compressed (`scripts/fe9_files.lz10` reads it) into
  the same pointer-relocated layout as Path of Radiance's `FE8Data.bin`: header `size, data size,
  pointer count, name count`, data at 0x20, then the pointer offsets, then `(data offset, name offset)`
  pairs naming the tables. Tables include `ItemData`, `JobData`, `PersonData`, `SkillData`,
  `TerrainData`, `ChapterData`, `3SukumiData` (weapon triangle), `RelianceData` (who can support whom),
  `RelianceParam`, `KiznaData` (bonds), `BioData` and `DivineData`.
- `RelianceParam` (16 bytes): `32 64 96 97` the support points each level needs in total (C 50, B 100,
  A 150); `0f 1e 03 05 04 01 02` points per action for a middling pair (15 for being deployed together,
  3 for starting a turn adjacent, 5 for carrying, 4 for a staff or Sacrifice, 1 for a shove; 30 and 2
  not yet placed); `02 01 00 ff fe` how much more or less each of the five kinds of pair gets.
- The affinity bonuses aren't stored as a table (the code works them out); they're the Fire Emblem
  Wiki's and Serenes Forest's, which agree.

## The hit roll (`DATA/sys/main.dol`)

- The random numbers are the GBA games' generator: three 16-bit words at r13-0x6a70. `0x80089c88`
  returns `(n x next) >> 16`; `0x80089d68` draws one number 0-99 and checks it against a chance;
  `0x80089de8` draws two and checks their average, rounded down.
- The attack routine `0x8002ff14` returns 0x6e (hit), 0x6f (critical) or 0x70 (miss). Past a few forced
  outcomes, it rolls hit (unit +0x452) with the two-number check and crit (+0x458) with the one-number
  one: 2RN hit, 1RN crit. Path of Radiance's is the same (`0x801a8a28`, helpers `0x8000cd88` and
  `0x8000ce68`).

## Weapons (`ItemData`, `scripts/build-fe10-items.py`)

- Records are variable-length: 0 `IID_`, 4 `MIID_` (name), 8 `MH_I_` (description), 12 and 16 weapon
  type (`sword`, `lance`, `axe`, `bow`, `ballista` = crossbow, `knife`, `flame`, `thunder`, `wind`,
  `light`, `dark`, `rod`, `blow` = laguz strike, `item`), 20 rank (`E`-`S`, `*` = SS, `N` = none needed),
  24-32 effect IDs; 0x24 u16 index, 0x26 u16 price per use, 0x28 Mt, Hit, Crit, Wt, uses, weapon EXP, range
  min, range max (255 = Mag/2); 0x35 the number of attribute strings, 0x36 the number of effectiveness
  targets (`SFXC_`), 0x37 whether a 12-byte stat block follows (HP, Str, Mag, Skl, Spd, Lck, Def, Res, Mov,
  ...; on staves it means something else). The lists start at 0x38.
- Personal weapons are `eqA`-`eqI`; who wields each is whoever has the matching `SID_EQ_` skill in
  `PersonData` (A Ike, B Mist, C Elincia and Renning, D Micaiah, E Sanaki, F Sephiran/Lehran, G Edward,
  H Leonardo, I Nolan). `SID_EQBALLISTA` (Warrior, Reaver, Sniper, Marksman) is what lets a class use
  crossbows, and `SID_EXPANDRANGEO_1` (Marksman only) the +1 range on `expandrange` bows.
- In `main.dol`, the attack routine `0x8002f220` builds attack as the weapon's Mt plus a modifier,
  tripled when the unit's effective flag is set (`0x8002f37c`: x << 2, minus x), then adds Str or Mag,
  except for a `stone` weapon (the Onager) or a crossbow (type 13). An item's rule flags are bits in two
  words at its +0x38 at runtime; `sealcrit` (bit 16) is tested against the attacker's crit.
- Brave weapons strike twice on both phases (the Fire Emblem Wiki: attack-only came with Fates). Sell price
  is half the price of the uses left, as in Path of Radiance.
- Shops: `WSHOP_ITEMS_Cppnn` and `ISHOP_ITEMS_Cppnn` list `(IID, flag)` pairs for the base before
  chapter `MCTppnn`; a non-zero flag is a one-off bargain (Serenes Forest's Bargains lists match). The
  forge (`FSHOP_ITEMS_Cppnn`) lists weapon types and materials (`MIK_SW`, `MDV_IRN`) rather than items.
- Only what you can get is listed: sold or a bargain, offered at the forge, handed over by a chapter
  script (`MindGetItem`, `UnitGetItemShowing(Sub)`, `UnitAddItem`, `GetRndTreasure`, `NetuzoWeapon` in
  `Scripts/C0[1-4]*.cmb`), carried by someone who joins (a PID in any `mikata` group of the story maps,
  `zmap/bmap0[1-4]*` and `emap0[1-4]*`), dropped, or stolen. A placement file (`dispos`, 104-byte units:
  0 PID, 4 JID, 8 item slots from +0x20) marks a slot `IID_X/D` when it drops and `IID_X/L` when it's
  locked to its holder; a locked item, an item flagged `sealsteal`, and anything Ashera carries can't be
  stolen. That leaves out the maps' ballistae and the Onager, Judge, Creiddylad, and the bosses' Rewarp,
  Elsilence and Elsleep.

## The forge

- `FSHOP_ITEMS_Cppnn` is a grid of `(weapon type, material, IID or 0)` triples (`MIK_SW`, `MDV_IRN`,
  `IID_IRONSWORD`): the base weapons that base's forge offers.
- Limits (the forge screen, `main.dol` 0x80219d48 onward): Mt and Wt change by 1 a step, Hit by 5, Crit by
  3, at most 5 steps up or down. A stat can only be lowered while it's above 1, and the forged stat
  getters (0x80110da8-0x80110eb0) keep Mt, Hit and Wt at 1 or more and Crit at 0 or more.
- Cost (0x80112364, called from 0x8022fe80): the base price plus, for each stat,
  `trunc(float(steps²) × (0.1f × price))` in single precision (Hit's steps are its change ÷ 5, Crit's ÷ 3).
  Serenes Forest's example comes out the same: a Silver Sword at +5 Mt, +15 Crit, −2 Wt is 11,520G.
- `FSHOP_CARD_DATA`: a count, then `(name label, bonus, odds)` for each card a Coin can draw. The bonus
  bytes are Mt, Hit, Crit and extra Coins; the odds word's top byte is the chance in %.

## Maps (`scripts/build-fe10-maps.py`)

- `zmap/bmapPPNN/map.cmp` (LZ10, then a `pack` archive like Path of Radiance's) holds `map.bin`, a pointer-relocated
  file whose tables are named after the folder (`bmap0101:mapdata`, `:panelindex`, `:uniquepanel`, ...). `mapdata`
  bytes 2 and 3 are the width and height; `panelindex` is a u16 per tile (rows from the top) into `uniquepanel`'s
  12-byte records, whose +8 names the terrain (`平地２`). Where a roof covers the ground, `roofindex` into `roofpanel` gives the
  terrain on top (`民家` a house, `教会` a church), which is what counts. A plain roof (`屋根`) lifts when what's under
  it is opened (Part 1 Ch.7's cells), so the map shows the floor and flags those tiles to check in-game.
- Healing jars (`回復壷`, flag byte 0x40): at the start of the turn the game checks the 4 tiles beside the unit (not
  the diagonals) for that flag and heals by the jar's % (20) instead of the unit's own tile (`main.dol` 0x800544e4).
- Part 2's Prologue has only sky (`空`) and cloud (`雲`) panels; the 32x32 cloud pattern repeats and drifts one tile
  left each phase (fireemblemwod.com), wrapping round, so the map keeps the whole pattern for its turn selector.
- Fog of war: the scripts turn it on with `SetSight(1)` (Part 1 Ch.9, Part 3's Prologue). Part 2 Ch.2 and Part 3
  Ch.1 have it too (fireemblemwod.com) but set it some other way, not yet found; `mapfog` and the map header don't
  mark it. Torches the setup lights as the map loads (`BuildInstTorch(x, y, radius, 0)`) start lit. Part 3 Ch.3's
  torch events are its supplies: the chapter is won when all their flags are set.
- Tile event 45 is an exit for units whose AI escapes: `SEQ_..._ESCAPE` in the placement file (Part 1's looting
  Thieves) or `UnitSetCpMoveSeq(..., 'SEQ_ESCAPEMOVE')` in the script (Ch.7's prisoners, Heather).
- The terrain table in `FE10Data.cms`: 16-byte records (name, `MT_` label, pointer, index); each points at 44 bytes:
  Avoid, Def and Res for ground units, then the same for fliers (0 but on clouds: fliers get no terrain bonus),
  healing %, a flag byte, three pointers (effect and sounds), and the cost for each of 24 movement types (255:
  can't enter). A class's movement type is `JobData` +52 (its Mov is +53).
- The chapter table: 180-byte records of the `MCTppnn` label, map folder and script, then three 32-byte blocks
  for Easy, Normal and Hard, each with the win condition at +0 and the lose conditions at +12 to +24. At +132,
  +136 is 0 on the maps with no preparations screen (Part 1's Prologue to Ch.2, Part 2's Prologue to Ch.2).
- `dispos_n.bin` (Easy), `dispos_h.bin` (Normal and Hard: the Japanese Hard and Maniac) and `dispos_c.bin`
  (every difficulty): named groups of a count byte, 3 more bytes, then 104-byte units: +4 PID, +8 JID, +12 where
  the unit comes from (x, y), +14 where it stands (x, y), +16 level, +17 side (0 yours, 1 enemy, 2 other armies),
  +32 affinity, +36 seven item slots (`/D` drops, `/L` can't be taken), +64 five skills, +84 its AI.
- The scripts (`Scripts/CPPNN.cmb`) are Path of Radiance's format, with two differences: op 0x37 calls another
  handler by number, and `?47` stores into a variable (`load` pushes its address, `var` its value). They test only
  `Normal()`, which is true on Easy. A group named without a suffix (`DisposRank('bmap0102_teki')`) gets the
  difficulty's (`_n` or `_h`).
- Handler kinds: 3 a turn (first, last, phase), 4 an area (x0, y0, x1, y1, who), 5 a tile (x, y, event: 9 village,
  38 a bandit destroying that village, 11 door, 12 chest, 13 seize, 14 escape, 42 arrive, 45 where units leave the
  map, 55 and 59 lighting and putting out a torch (`BuildInstTorch(x, y, radius, time)`), 58 a breakable wall),
  7 after every action, 8 a talk, 9 a battle conversation, 11 a death, 14 a base conversation.
- The chapter's commander is whoever has `SID_HERO`: Micaiah has it, and Part 2's setups give it to that chapter's
  lead (`UnitAddSkill`). `SetTerrName(x, y, '防衛')` marks a defend tile.
- The battle starts where an opening (`Opening0`, `1`, `2`) calls `MapLoad(map)` or `REventStart(map, 0)`;
  `REventStart(map, 1)` is a cutscene. `SallySetByGroupRank` gives the deployment slots and `UnitForcedSallyByPID`
  who must go. Part 1 Ch.6 is two maps on one: its second section's opening sets `セクションＢ`.
- Buried treasure: `GetRndTreasure(item, flag)` (in `startup.cmb`) rolls 0-100 against a stat of the unit that
  stops there, for your units only. fireemblemwod.com gives that chance as Skill, +60 for the Thief line,
  adjusted by biorhythm (not yet checked against main.dol).
- Each map is cropped to its playable grid (`PLAYABLE`), read from fireemblemwod.com's overviews: the grid
  lines they draw, tied to game coordinates through the starting enemies' markers.
