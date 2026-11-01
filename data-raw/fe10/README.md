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
- `DivineData` holds the affinity bonuses in Path of Radiance's layout (9 rows of 12 bytes: a name pointer, then Atk, Def,
  Hit, Avoid, Crit and Crit avoid, stored doubled; read through main.dol 0x8010b250). `scripts/build-fe10-supports.py` writes
  `src/data/supports/fe10Supports.ts` from it and `RelianceParam`. In battle (0x800282a0 -> 0x8002fab0 -> 0x8002fc64) a unit
  has one partner (0x8012e3a4 reads a single field), counted within 3 tiles and in the same army while both are alive: both
  rows x the pair's level are added and halved once, a half rounded up (0x80119760: (doubled sum + 1) >> 1).

## The hit roll (`DATA/sys/main.dol`)

- The random numbers are the GBA games' generator: three 16-bit words at r13-0x6a70. `0x80089c88`
  returns `(n x next) >> 16`; `0x80089d68` draws one number 0-99 and checks it against a chance;
  `0x80089de8` draws two and checks their average, rounded down.
- The attack routine `0x8002ff14` returns 0x6e (hit), 0x6f (critical) or 0x70 (miss). Past a few forced
  outcomes, it rolls hit (unit +0x452) with the two-number check and crit (+0x458) with the one-number
  one: 2RN hit, 1RN crit. Path of Radiance's is the same (`0x801a8a28`, helpers `0x8000cd88` and
  `0x8000ce68`).

## The weapon triangle and leadership (`scripts/build-triangles.py` -> `src/data/fe10/fe10Triangle.ts`)

- `3SukumiData`: a count (27), then 12-byte rows `(attacking type string, defending type string, Mt, Hit, 0, 0)`. `main.dol`
  0x80112980 loads it; 0x80112a3c looks a pair up, first turning flame, thunder and wind into `elemental` when the other side has
  light or dark. Every row is worth 1 Mt and 10 Hit either way: sword > axe > lance > sword, fire > wind > thunder > fire, and
  light > dark > elemental > light.
- 0x8002a8a4 sets both sides' values. It skips the triangle when the difficulty byte (`lbz 0x11` of the settings at 0x80060728) is 2,
  which is Hard (see Difficulties below): the North American Hard mode is the Japanese Maniac, so the triangle is off on Hard.
- The attack routine (0x8002f220) adds the Mt (+0x474) before an effective weapon's Mt is tripled. Hit adds +0x476.
- A weapon flagged `revatr` (bit 0x400 of the item's second runtime flag word, 0x80110000) reverses both sides; no item has it.
- Unconfirmed: it's also skipped when either weapon has bit 0x80 of that word (set somewhere other than the attribute list) or when
  the battle bytes +0x47b / +0x47d are set.
- Leadership (0x8002f9d0): the unit's army's commander is found by 0x80127b68 (same army, flag 0x100 at +0x10c, not 0x08). Their
  stars (`PersonData`'s byte after the skill pointers, runtime +0x21: Caineghis, Dheginsea and Ashera 5, Ike and Elincia 3) are
  multiplied by 5 and added to hit and avoid. There's no distance check, and the other army's stars aren't subtracted. Armies 5
  and 6 get none (which those are hasn't been identified). Daunt (0x80124bc0) is separate: -5 hit and crit for each foe with it
  within 1-3 tiles. Weapon rank isn't used in hit, attack or crit.

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
  `Shop/shopitem_n.bin`, `_h` and `_m` are the same file but for a build timestamp (`2007/01/11 19:19:34`, `19:18:46` and
  `19:20:16`), so the bases sell the same on every difficulty; the generator reads `_n` and `_h`, which match.
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

## Difficulties (`main.dol`)

- The difficulty byte (0x80429455, `lbz 0x11` of the settings 0x80060728 returns): the new-game menu sets 0 for Easy, 1 for
  Normal and 2 for Hard; 3 is never set. The app names them Easy, Normal and Hard, as the game does.
- The scripts' tests (0x8009940c-0x800994b0, registered by name at 0x8009bcd4): `Normal()` is true on 0 only, so on Easy (the
  Japanese release's Normal), `Hard()` on 1 only (Normal), `Maniac()` on 2 only (Hard), and `Easy()` on 3, so never. The chapter
  scripts call only `Normal()` (143 times); `Hard()` and `Maniac()` appear only in `startup.cmb`'s *SetMode helpers. An
  `if (Normal()) {...} else {...}` gives the else-branch to Normal and Hard (Part 1 Ch.8's turn 2: `z06_n` on Easy, else `z03_h`).
- Placement records: `DisposRank`, `InstantDisposRank`, `JoinRank` and the other *Rank helpers complete a group's name with `_n`
  on 0 (and 3), `_h` on 1 and 2, and `_c` on 4 (0x8010de10). There's no `_m` and no `dispos_m.bin`: Easy reads `dispos_n`, and
  Normal and Hard both read `dispos_h`.
- The *SetMode helpers (`startup.cmb` handlers 523-528: `DisposSetMode`, `InstantDisposSetMode`, `DisposFirstSetMode` and the
  rest) take a group and a flag for each difficulty, `DisposSetMode(group, Easy, Normal, Hard)`: each returns early when
  `Normal()` holds and the first flag is 0, `Hard()` and the second, or `Maniac()` and the third, and otherwise places the group
  with the matching *Rank helper. All 64 calls in the chapter scripts are `DisposSetMode` with flags 0, 1, 1 (Normal and Hard)
  or 1, 0, 0 (Easy): Part 1 Ch.2's `z02`/`z03`, Ch.4's `z01`/`z02` and Ch.8's `z01` never come on Easy; Ch.6's `z02a` comes on
  turn 3 on Normal and Hard and turn 5 on Easy; Endgame (2)'s waves have Easy calls of their own (`z02` on turns 4 and 6 rather
  than 3 and 6, `z07` on 11 and 12 rather than 11, 13 and 15, `z08`/`z09` only on 12), and Endgame (3)'s dragons come on Easy
  only from its turn-3 `DisposRank`.
- Hard's levels: 0x80092c84 reads a chapter record's +0x85, +0x86, +0x87 or +0x88 for difficulty byte 3, 0, 1 or 2 (the record
  starts with the chapter's id, `C0101`, 4 bytes before its `MCTppnn` label). Every story chapter has 0, 0, 0 and 2, so Hard alone
  adds 2 levels (the test map `MCT0000` has 4, 5, 0 and 6). The placement code (0x8011d880) calls 0x8011f70c for a unit whose
  record has bit 0 of its flags (the u16 at +2) set, its stats rolled from growths; that adds the bonus only in army 1 (the
  foes) and holds the level at the class's highest: `min(level + bonus, cap)`. The cap is the runtime class's +0xfb, set as
  `JobData` loads (0x8010a7d4): 40 when the class's skill list (its count at +0x35, the list from +0x40) holds `SID_ANIMALIZE`,
  the laguz, and 20 for the other classes. No record starts above its cap. 1,986 foe records in the story's `dispos_h` have the
  flag; most bosses don't (Pugo doesn't), and the cap holds 42 of them under +2 (Lv 19 and 20 in 20-level classes: in Part 2
  Ch.1, Ch.3 and Endgame, Part 3 Ch.9, Ch.12 and Endgame, Ike, Titania and Shinon in Part 3 Ch.13, and Ashera and her auras).
  The map gives one entry with Normal's level first, `Lv 3 (Hard 5)`, and shows the picked difficulty's.
- Goals: each chapter record has a goal block per difficulty, read at +0x24 on Easy (and byte 3), +0x44 on Normal and +0x64 on
  Hard (0x80092d04). Normal's and Hard's are the same in every record; Easy's differs in Part 1 Ch.1, Ch.2, Ch.3 and Ch.5,
  Part 2 Ch.2 and Part 3 Ch.3, which the map's goals note.
- A unit's entries merge where every difficulty places it alike but for its level; what it can't be disarmed of keeps them apart
  (Ike's Ragnell in Part 3 Ch.13 is `/L` in `dispos_n` only), and so does where an arriving unit comes in from.

## Maps (`scripts/build-fe10-maps.py`)

- `zmap/bmapPPNN/map.cmp` (LZ10, then a `pack` archive like Path of Radiance's) holds `map.bin`, a pointer-relocated
  file whose tables are named after the folder (`bmap0101:mapdata`, `:panelindex`, `:uniquepanel`, ...). `mapdata`
  bytes 2 and 3 are the width and height, and byte 17 the border (see the playable grid below); `panelindex` is a u16 per
  tile (rows from the top) into `uniquepanel`'s
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
  torch events are its supplies: the chapter is won when all their flags are set. Each set of supplies is the
  tiles whose events set the same flag (`FlameA` to `FlameF`), and the map shows each set as an objective.
- The AI sequences named in a unit's AI (+84 in the placement file) are named 280-byte tables in
  `Cp/cp_data.cms`; one that moves its unit to a tile holds it at +92 (x, y as two halves). Part 3 Ch.3's horses
  (`SEQ_0304_HORSEMOVE_1` to `_4`) each run for their own exit this way, not the nearest one.
- Tile event 45 is an exit for units whose AI escapes: `SEQ_..._ESCAPE` in the placement file (Part 1's looting
  Thieves) or `UnitSetCpMoveSeq(..., 'SEQ_ESCAPEMOVE')` in the script (Ch.7's prisoners, Heather).
- The terrain table in `FE10Data.cms`: 16-byte records (name, `MT_` label, pointer, index); each points at 44 bytes:
  Avoid, Def and Res for ground units, then the same for fliers (0 but on clouds: fliers get no terrain bonus),
  healing %, a flag byte, three pointers (effect and sounds), and the cost for each of 23 movement types (255:
  can't enter; the 24th byte is 0 in every record). A class's movement type is `JobData` +52 (its Mov is +53).
  The flag byte (+7) is a bit field. Bit 0x01: no unit may end its move there (main.dol 0x80113428 copies it into a per-tile
  table; 0x80067d74 refuses such a tile before it looks at who's on it, and placement, dropping a carried unit, the range
  overlay and the AI check it too), though a unit whose cost allows can cross. It's set on buildings and objects, trees,
  fences and outer walls, cliffs, lava and falling rock, the abyss and waterfalls, chests, the ballista and onager tiles and
  healing jars (fliers only), and on ledges and low cliffs (everyone); a flier can land on a rock, a hole, a pond or the sea.
  0x08 costs 1 with SID_CLIMBER, 0x40 marks a healing jar's source, 0x02 and 0x04 go with the edge masks.
- The chapter table (`ChapterData`: a count, then 180-byte records): the chapter's id (`C0101`), the `MCTppnn` label, map folder
  and script, then three 32-byte blocks at +0x24, +0x44 and +0x64 for Easy, Normal and Hard, each with the win condition at +0
  and the lose conditions at +12 to +24. +0x85 to +0x88 are the levels each difficulty adds to the auto-levelled foes (see
  Difficulties: Hard's, +0x88, is 2 in every story chapter). The generator counts from the label, 4 bytes in, so these are its
  +129 to +132, and its +136 (the record's +0x8c) is 0 on the maps with no preparations screen (Part 1's Prologue to Ch.2,
  Part 2's Prologue to Ch.2).
- `dispos_n.bin` (Easy), `dispos_h.bin` (Normal and Hard: the Japanese Hard and Maniac) and `dispos_c.bin`
  (every difficulty): named groups of a count byte, 3 more bytes, then 104-byte units: +0 an id (u16), +2 flags (u16; bit 0:
  auto-levelled, see Difficulties), +4 PID, +8 JID, +12 where the unit comes from (x, y), +14 where it stands (x, y), +16 level,
  +17 side (0 yours, 1 enemy, 2 other armies), +32 affinity, +36 seven item slots (`/D` drops, `/L` can't be taken), +64 five
  skills, +84 its AI.
- The scripts (`Scripts/CPPNN.cmb`) are Path of Radiance's format, with two differences: op 0x37 calls another
  handler by number, and `?47` stores into a variable (`load` pushes its address, `var` its value). They test only
  `Normal()`, which is true on Easy alone. A group named without a suffix (`DisposRank('bmap0102_teki')`) gets the
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
- The playable grid is the map file's own (`border()`): `mapdata` byte 17 is a border width, in from every edge. The loader
  (main.dol 0x8013625c) keeps it at the map's +0xb0; 0x8011337c sets the grid's limits from it, x and y from the width up to
  the size less the width; 0x801135c0 bars the outer side of every tile along those limits, and the move search (0x801166b8)
  never steps past them, so no unit enters or leaves the grid. Each map is cut to it, and units placed outside it only watch
  (Part 3 Ch.10's Valtome and his guard). Part 1 Ch.6's two maps share one file, so each keeps the part fireemblemwod.com's
  overviews give (`SECTIONS`).
- The file disagrees with the grids fitted before: Part 3 Ch.4 is 2 rows shorter and Ch.6 a column wider than the user's
  in-game counts (both rows are plains and cliffs past the border; the column is river, reeds and cliff), and Part 1 Ch.3,
  Part 1's Endgame and Part 2's Endgame are a column or a row less than fireemblemwod.com's overviews. The file is used. Every
  other grid fitted before agrees with it.
- The edge tables (`maplink`, `maplinkAt`, `maplinkAbs`, loaded at main.dol 0x80136c34): 2 bytes, a u16 count, then
  (x, y, sides) triples. Each tile keeps a u16 of side flags (the grid's +0x508e, 64 tiles to a row). As the map loads every
  side is open to ground units (0x1 left, 0x2 right, 0x4 down, 0x8 up) and the map's outer edges are shut to everyone (0x10,
  0x20, 0x40, 0x80; 0x80113bb4), as are the playable grid's (0x801135c0). `maplink`'s byte replaces a named tile's flags: its
  low nibble the sides a ground unit may cross, its high nibble the sides no unit may cross (never set on the disc).
  `maplinkAbs`, on no map, opens or shuts sides to everyone; `maplinkAt` sets a third set (0x100 to 0x800). Movement
  (0x80115848) checks the side a unit leaves by: a ground unit needs it open, a unit with SID_FLY (0x801153dc) only needs it
  not shut. The third set is read only by two searches ordinary movement doesn't use: one over the whole grid through a
  neighbour visitor (0x80171a30, 0x800395f4) and one that first opens it on the tiles of type-4 entries in a list of its own
  (0x80116098, 0x80066130). What they're for isn't traced (unconfirmed: the AI's), so the map doesn't draw the set.
- Fences: each side a ground unit can't cross between two tiles it could walk (now, or once a door opens or a wall breaks):
  46 on 11 maps, every one shut from both sides. All but Part 2 Ch.1's (two tiles fenced in beside the stable) lie between two
  ledge tiles, so a unit crosses a ledge but can't run along it. Fliers cross them all.
- `UnitCheckLiveByPID(PID) ; jz ; InstantDisposRank(A) ; jmp ; InstantDisposRank(B)` places group A while the
  character lives and B if they died earlier (Part 3 Ch.6: Lethe or Kezhda, Mordecai or a Tiger). Group B
  stays off the map; the unit in group A says who would stand there instead. Reinforcements work the same way
  (Part 3 Ch.13: Ike's companions, each with a Tiger or Cat in their place).
- An army's soldiers can be named for their country, with a portrait of their own (`PID_PHOENICIS`, Tibarn's
  hawks; `PID_KILVAS`, the ravens). A PID placed 3 or more times in one group is a soldier, never a character.
- The Endgame is five chapter records, `MCT0407a` to `MCT0407e` (maps `bmap0407a`-`e`). The `lmap01`-`12`
  records are titled 'dummy' and their scripts aren't on the disc: terrain only, not battles. Radiant Dawn has
  no trial maps.
- The Tower's floors: 回復床 heals 10% with Avo +15, 防御床 Def +10, 防御床２倍 Def +15 Avo +5, 魔防床 Res +10, and
  防御床３ Def +10 Avo +15 (its number is kept: other numbered floors are the same terrain). Fliers get these too.
- A handler called with values on the stack (op 0x37) gets them as its variables 00, 01, ...: Endgame (4) and
  (5) pass each turn's spirits to the handler that warps them in (`DisposWarp(var 00)`), while the enemy has
  fewer than 30 units (`UnitGetBelongCount`).
- `GameGetRound()` gates arrivals to a second or later playthrough (Endgame (5)'s Lehran, who also needs the
  flag Endgame (2) sets from 1-11 and 3-7).
- Placement calls: `DisposWarp` (enemies warping in) and `DisposContinue`, `DisposFirst` and their variants
  place groups too.
- Fog the files don't flag: a map whose torches are lit as it loads (Part 4 Ch.1) is treated as fog, and says
  that's inferred.
- `UnitCheckLiveByPID(PID) ; jz ; Dispos(group)` (or `PelleasIsAlive()`) right before a placement, in the
  handler's own code, places the group only while that character lives. A check inside a handler it calls
  doesn't count (Part 3 Ch.6's waves call a dialogue handler that checks Lyre).
- A named unit a turn or death event warps or escapes off the map leaves mid-chapter (Part 4 Ch.3's Lekain on
  turn 6); a death event for the unit itself means it can't be killed, only driven off.
- Part 3 Ch.9's houses: tile event 55 calling `BuildEventFlame` (`BuildInstTorch`, then `SetBomber(5)`) is a
  house an arsonist (AI `SEQ_NEARESTTORCHMOVE_ARSON`) sets alight; event 59 (`BuildEventExtinction`) puts it
  out. The tiles of one house share a flag. A turn event switching green units to `..._TORCHMOVE` sends them to
  put fires out.
- An every-action event that walks units off once `ForceGetCount(enemy)` drops to the number it stores first
  (Part 3 Ch.10's Valtome, at 7) marks them as leaving; the rout doesn't need them.
- A `_child` group placed onto another group's unit is carried (Leanne on Tibarn, Part 3 Ch.11).
  `BMSetLoseTerm` in a mid-chapter event adds a lose condition (Tibarn dies, once he's arrived).
- A PID made of an army's name plus a class (`PID_GALIA_TIGER` for `MPID_GALIA`) is a generic soldier, as a foe
  or a green unit.
- A chapter record's second win label (+4 in each difficulty's block) is another way to win: 'Defeat boss' on
  Part 2's Endgame and Part 3 Ch.5 and Ch.13.
- 'Defeat enemies' maps end on an every-action check of `GetNumDiedEnemies()`, with Easy's count behind
  `Normal()` (the Japanese Normal is the English Easy): Part 3 Ch.6, 46 (36), and Ch.12, 40 (30). Part 3's
  Endgame also ends once deaths on every side add up to 80.
- `SID_HERO` given in the setup can be the enemy's commander (Sigrun, Part 3 Ch.12): only your own units count.
- Summoners (Part 4 Ch.5's Izuka) call up laguz with their class's skill; the script has no trace of it.

Checked against fireemblemwod.com's walkthrough (the tests hold the turns): reinforcement turns, win and lose
conditions, mandatory units and items agree, except these, still to check in-game:
- Part 1 Ch.9: WoD has the last waves on turns 5, 6, 8 and 10; the script places them on turns 5, 7 and 9
  (`DisposSetMode`, which matches WoD on every other chapter).
- Part 3 Ch.12: WoD has the two Falcon Knights on turn 4; the script, on turn 5 and not on Easy.
- Endgame (1): the script adds a turn-10 wave of Generals. (Part 1 Ch.6's first map repeats a Pegasus wave on turn 5, which
  WoD doesn't list: that call is Easy's alone, its `DisposSetMode` flags 1, 0, 0, so WoD's Normal agrees.)
- Boss levels: WoD's often differ from the files' by a level or two either way, with no pattern.
- Starting enemy counts: WoD's minimaps can't be counted reliably without looking at each image, so only the
  first eight maps' are in the tests.
- Burning floor: `SetLava(x, y, shown, 100, damage)`, registered as the map loads, sets a tile burning. Part 3
  Ch.8 has 62 that do 10 damage to a unit starting its turn there (code `dd`); three more do none and are
  scenery.

## Chapter fields for the spoiler block (`scripts/build-fe10-items.py`)

- Each weapon carries `shopAt` / `forgeAt` (and, in Radiant Dawn, `bargainAt`): the map ids behind the `shop` / `forge` /
  `bargain` text, by difficulty; `baseAt`, the chapters whose base conversation gives it (script handler kind 14: Jill's
  Brave Axe and Tarvos in Radiant Dawn); and `giftAt`, the chapters whose own script hands it over outside a chest or
  village (`UnitGetItemShowing(Sub)`, `MindGetItem`, or a quiet `UnitAddItem` in an `Opening` handler: Ike's Ragnell).
  Handler kinds 4 and 5 are chests, villages and buried or random treasure, which the map data lists.
  A gift before the battle (a base conversation, an opening) is that chapter's; one at its end or from an event during it is
  the next chapter's; a handler another calls (opcode 0x37) is read through its caller (Part 4 Ch.4's opening calls the one
  that sends Tormod's items to the convoy and hands him Arcfire, Bolganone and Meteor).
  `kitAt` is the chapter each unit's gear is yours from, counted once, where the unit first joins in story order: its first
  roster (`bmapPPCC_mikata_n`/`_h`/`_c` and the lettered or numbered variants), a group a join call adds (`JoinRank`,
  `SallyAddByGroupRank`, `Join`: a base conversation's recruits), a group the battle places on your side outside the rosters
  (Lehran in Endgame (5), with the Ashera Staff), or a hand-over (`UnitTransferToForceByPID(pid, 0)`); one during the battle
  (a talk, the end) is yours from the next chapter. The rosters are developer-start templates: every chapter's battle setup
  first calls `EvDevStart(map, roster)`, and they list the gear a unit should have by then, not what you carry (Micaiah's list
  a Thani from Part 1 Ch.3, a base conversation's gift before Part 1's Endgame; the endgame's give Micaiah a Rexaura, which
  Lekain drops). Later rosters only place a unit you already have. The opening's and ending's casts (`_op01_mikata_c`,
  `_ed01_mikata_c`) and anything placed inside a cutscene (`REventStart` to `REventEnd`) are no one's.
- What can be had (`obtainable()`): sold, bargained, forged, handed over, brought by a unit when it joins (`kit()`), dropped,
  or disarmed from a foe the battle places. A weapon only scenes' casts, rosters or test maps carry is codes-only and left out
  (the Slim Lance); one no placement file holds at all is a foe's by other means and stays foe-only (Lekain's Judge).
- Steal lines: any foe can be disarmed of a weapon except a `sealsteal` one, Ashera's, and one in a `/L` slot, which the maps
  write as the unit's `locked` list (the Black Knight's Alondite; Ike's Ragnell in Part 3 Ch.13 is `/L` in `dispos_n` only).
- Drops are not here: the app reads them from the map data, which holds only units you can see. The placement files also
  list cutscene units (Petrine carries her Flame Lance in the chapter 7 files), so they can't say when a drop is available.
