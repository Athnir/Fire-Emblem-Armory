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
  - 16 the second type: what the damage and the triangle go by (0x8001ddc4, 0x801a609c). Fire, thunder, wind or `rod` (light)
    adds Mag and is defended with Res (0x801a90f4, 0x801a9150), so the Flame Lance (fire) and Bolt Axe (thunder) are magic, and the
    Sonic Sword (wind) and Runesword (light) too; the `magsw` flag doesn't decide it;
  - 64 price per use (u16), 66 uses, 67 Mt, 68 Hit, 69 Wt, 70 Crit, 71-72 range (255 = Mag/2, held between 5 and 15 at
    0x8001dd54), 74 weapon EXP, 75-82 stat bonuses (HP, Str, Mag, Skl, Spd, Lck, Def, Res), 85-92 growth changes in the same
    order (signed): a Fixed-mode level-up adds the weapon used in that battle's (0x800357e0).
- Flags read in the program: `stormsw` (the three blades) and `magsw` (the magic swords) clear the wielder's Aether, Astra,
  Luna, Sol, Flare, Colossus, Deadeye, Stun and Lethality at 2 range (0x801a6e6c, 0x801a85f4); `longfar` (the siege tomes) stops
  counters both ways (0x801a99e8), and only the ballistae's `sh` skips the wielder's stat (0x801a90b4); `eqA` / `eqB` need
  SID_EQ_A / SID_EQ_B, which only Rolf and Elincia have; `weakA` can hurt the classes with SID_WEAK_A (the Black Knight, King
  Daein), which take no damage otherwise (0x801a8c60): Ragnell, the lion's claws and the dragons' breath have it.
- Targets also include `doorbreak` (every axe): attacking a breakable door or wall, the program builds a stand-in of a class with
  that attribute (0x801a9c74), so axes deal Mt x2 to them.
- A laguz's attack (type `fang`) comes with its class: FE8Data.bin pairs each laguz class with its weapon (a JID pointer, then an
  IID pointer). Tibarn's and Naesala's classes have beaks of their own; Vortex (`IID_FLUTTER`) belongs to no class and is left out.

Generator: `scripts/build-fe9-items.py` writes `src/data/fe9/fe9Weapons.ts`. The staff "Torch" shares its name with the item
that lights fog, so it's "Torch (staff)". The Prologue's ending takes the Trainer back (C01 handler 19: `UnitDelItem(0)`, then an
Iron Sword), so it's the Prologue's only. It was checked against
Serenes Forest's FE9 weapon tables; where they differ (Venin Lance's rank, Rescue's weapon EXP) the
game data wins.

## Rules found in the program (`sys/main.dol`)

- Effectiveness: weapon targets and class attributes are bit sets built from the same names (mage 1,
  fly 2, knight 4, armor 8, alize 0x10 = laguz, human 0x20, beast 0x40, dragon 0x80, bird 0x100). When
  they overlap (0x80092dc4), the weapon's Mt is doubled (0x801a9084: `slwi 1`), forging included.
- Selling (0x801941dc) pays half of price per use x uses left, rounded down; items with the `valuable`
  flag are refused.

## The weapon triangle (`scripts/build-triangles.py` -> `src/data/fe9/fe9Triangle.ts`)

Not in the data files: `main.dol` 0x801a601c walks 4-byte rows at 0x80297240 (attacking type, defending type, Hit, Mt; a negative
type ends the list) and stores Mt at +0x2c2 and Hit at +0x2c4 of each side. Types are the program's order: sword 0, lance 1, axe 2,
bow 3, flame 4, thunder 5, wind 6, rod 7 (staves and light tomes), knife 8. The rows give sword > axe > lance > sword and
fire > wind > thunder > fire, each worth 10 hit and 1 Mt either way. The attack routine (0x801a904c) adds the Mt before an effective
weapon's Mt is doubled. Weapon rank isn't used anywhere in hit, attack or the triangle.

- A weapon flag (bit 0x80 of the item's second flag word, `revatr`) would reverse it for both sides, but no item has it.
- The routine is skipped when the 1 bit of a battle flag word (+0xcac) is set. Besides 0x800ad678, the four battle setups that
  load only one unit set it (0x801a6fb4, 0x801a7218, 0x801a73e4, 0x801a75dc); the two-unit setups (0x801a7794, 0x801a7a68) clear
  it. The routine also stops when either side has no weapon, so the flag never switches the triangle off between two armed units.
- Laguz strikes (claws, fangs, beaks, breath) aren't among the program's nine weapon types, so they're outside the triangle.

## Supports (`scripts/build-fe9-supports.py` -> `src/data/supports/fe9Supports.ts`)

- `DivineData` in FE8Data.bin (found by name in the file's table directory): a count, then 12-byte rows: the affinity's name
  (`fire` ... `telius`, Earth), then Atk, Def, Hit, Avoid, Crit and Crit avoid, stored doubled (Crit and Crit avoid are 0 for
  every affinity). main.dol reads it at 0x80019da8 and 0x800368c8. The English names are the status screen's (`MDV_FI`...).
- In battle (0x801a8da4) a unit adds (its own row + the partner's row) x the pair's level for every partner on its side within
  3 tiles, then halves the total once (0x8003b8d4): half points from two partners make a whole one. A unit holds at most five
  support levels (0x80036b20).
- `RelianceData`: a count, then per character a PID, an entry count and 8-byte entries (partner PID, the points C, B and A
  need, a pad byte; entries with no PID are blank). Jill and Lethe need 2, 5 and 12; Jill and Mist 1, 4 and 7.
- `KiznaData`: 36 fixed pairs with a bond that needs no support: 23 give both units +5 or +10 Crit while adjacent
  (0x801b8674), 13 make the second unit immune to enemy crits while next to the first (0x801b8550).

## The forge

- `shop/shopitem_{n,h,m}.bin` (Easy and Normal, Hard, and the Japanese release's Maniac; main.dol 0x8016a048 picks
  `_n` on Easy too): a block of words
  at 0x20 (header `size, data size, pointer count, name count`), then the offsets of the words that are
  pointers, then `(data offset, name offset)` pairs naming each table, then the names. `WSHOP_ITEMS_Cnn`
  and `ISHOP_ITEMS_Cnn` are the base's weapon and item shops, `FSHOP_ITEMS_Cnn` the forge's base weapons
  as `(IID or 0, material)` pairs. `nn` is the chapter's file number (`MCTnn` in `common.m`: 09 is
  Ch.8, 29 is Ch.27-2, 31 the Endgame). A chapter with empty shops has no base (Ch.27-2).
- Each weapon's shop chapters (`shop`) come from the armory and item shop tables of every base from
  Ch.8 on. Files 01-08 hold one table copied eight times on each difficulty, the Prologue's included, and only the scripts
  from Ch.8 on set up a base or have base conversations: there's no shop before Ch.8 (the user: no convoy or shop until the
  merchants are rescued in Ch.8; an item over the limit can only be dropped), so the app leaves those tables out.
  Where the maps give it (chests, villages, drops, buried items) is `src/logic/fe9ItemSources.ts`.
- Only what you can get is listed: sold, offered at the forge, handed over by a chapter script (chests,
  villages, gifts, buried items), dropped, carried by someone who joins (below, `kitAt`), or
  stolen. Steal takes anything unequipped (`tut.m` `MS_T11盗む_04`: the thief's Spd and Str each 1 above
  the target's Spd and the item's Wt). A foe with two weapons to fight with unequips one when it uses the
  other, and a silenced foe's tome comes off when it uses an item, so only a lone weapon stays theirs.
  That leaves out the ballistae and Onager, Alondite, Gurgurant, the Venin Edge (always held alone), Wishblade (Bryce's only
  weapon in the Endgame) and Boyd's Prologue Practice Axe. Rexflame and the Venin Lance are held only on a leftover test map
  (`zmap/Map6`) and Rexcalibur only by Soren's preset entries, and no script gives them: codes-only, like the Devil Axe.
- The price is in the program, not the data: `sys/main.dol`, function 0x8001c284. It takes the base
  item, its uses and the steps forged (Mt +1, Hit +5, Crit +3, Wt -1 each) and works on a value per
  stat: Mt, Hit, Crit + 10, and 23 - Wt. Each forged stat adds
  `uses x price per use x |new value^2 - old value^2| / old value^2`; the sum is multiplied by 2.5 and
  truncated (single-precision floats). The caller (0x801b15f4) adds the base weapon's price.
- The limits are in the program too, the same for every weapon and difficulty. The forge's stat window
  (set up at 0x80133fbc) gives each row, in Mt, Hit, Crit, Wt order, a step range of +5 / +5 / +3 / +5
  and -5 / -5 / -3 / -5; its input method (0x80132cfc) raises a row while it's under its maximum and
  lowers it while it's over its minimum and the stat is above its floor (Mt + s > 1, Hit + 5s > 1,
  Crit + 3s > 0). On the Wt row a step lightens while Wt - s > 1, and the negative steps make it heavier.
  So the forge lowers stats as well as raising them: Mt down 5 but never below 1 (Wind and Light, Mt 2,
  drop 1), Hit down 25, Crit only while it's above 0 (the 5 Crit of the Slim Sword, Slim Lance and
  Thunder goes 5, 2, then -1), and Wt up to 5 heavier. The forged weapon's stats are read with floors
  (0x8001d500 Mt at least 1, 0x8001d47c Hit at least 1, 0x8001d3fc Crit at least 0, 0x8001d37c Wt at
  least 1), so a Crit of -1 is 0; the price takes the raw step (Crit + 10 + 3s), so lowering a stat
  costs gold as raising it does. Serenes Forest's forging page has the raising limits only, and its
  costs match the formula except two Wt entries one digit off (Slim Lance 855G, Iron Axe 614G; the
  formula gives 885G and 619G).

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
- `dispos.cmp` -> `dispos_n.bin`, `_h`, `_m` and `_c` (every difficulty). The difficulty byte (0x80330708 + 0xa6) is 0
  Normal, 1 Hard, 2 Maniac, 3 Easy, and the title menu's Easy, Normal and Difficult set 3, 0 and 1 (0x801d5e24). Which
  records a difficulty reads:
  - an opening's `InstantDisposRank(base)` (0x801a1884) completes the name with `_m` on Easy, `_n` on Normal, `_h` on Hard,
    so Easy's openings are the `_m` records (the Japanese release's Maniac, repurposed);
  - startup.cmb's six `*SetMode(n, h, m)` helpers open with `if (NormalOnly())`, a name that exists nowhere, so they take
    `_m` on Easy and Normal alike and `_h` on Hard; most reinforcement waves and Ch.17's later sections come through them.
    On Normal the `_m` battle records match `_n` in tiles, levels, gear and drops (only the stat bonuses differ), so the
    generator reads `_n` there;
  - a group the script names with `_n` behind `Normal()` is Easy's too, since `Normal()` is true on Easy (main.dol 0x800b790c;
    `Hard()` only on Hard, `Maniac()` never on this disc, and `Easy()` and `NormalOnly()` aren't functions: an unknown name
    returns 0, 0x80011d98). No script can tell Easy from Normal.
  Named groups: a count byte, then 108-byte units: 0 PID, 4 JID, 12-24 weapons, 28-40 items, 44-60 skills, 67-74 stat bonuses
  (HP, Str, Mag, Skl, Spd, Lck, Def, Res; lower in `_m` for nearly every foe), 76-88 AI, 92 where it comes from (x, y), 94 where
  it stands (x, y), 96 level, 97 side (0 player, 1 enemy, 2-3 other armies), 98 flags (bit 0: stats rolled from the class's
  growths, every generic foe and no battle boss), 100-103 a flag per weapon slot, 104-107 per item slot (bit 0: dropped; bit 1:
  held only from a second playthrough on, 0x8003edd0 skipping the slot while the playthrough count at 0x80330708 + 0x57 is 1).
  Bit 1 is on bands only: the ones Havetti, Balmer and Kamura drop, and the ones Oscar, Boyd, Rhys, Shinon, Gatrie, Mia,
  Marcia and Jill bring. Coordinates count from the top-left (0, 0); the app counts from the bottom-left (1, 1).
- Easy against Normal: 40 units stand elsewhere or carry other gear (the `_m` openings of Ch.1, 3, 4, 5, 7, 9, 11, 13 and 14),
  and every story chapter's record adds 2 levels (up to 20) to the units with flag bit 0 on Easy (bytes +0x3d to +0x40 hold the
  bonus for Normal, Hard, Maniac and Easy: 0, 0, 2, 2 in the story, all 0 in the trials; 0x8003d70c reads 0x801661cc).
  Easy also gives more experience (FE8Data.bin's `GameData`, Normal/Hard/Maniac/Easy: 30 a fight and 30 a kill against 20,
  40 for a boss against 30; 0x80036248) and 1.5 times the chapter's bonus experience (`AchieveSet`, 0x801b7818). Clearing
  the story opens Trial 1 on Easy, Trials 1-2 on Normal, 1-3 on Hard (0x801e3400); a Game Boy Advance link opens Trial 4
  (The Blazing Blade or The Sacred Stones), 5 (The Blazing Blade) and 6 (The Sacred Stones) (0x801f5544).
- Chapter script (`Scripts/Cnn.cmb`, read by `fe9_cmb.py`): `FinalDisposition` places the starting
  groups; `mikata_c` holds your deployment tiles; `UnitForcedSallyByPID` names must-deploy units. Turn
  events (trigger kind 3: first turn, last turn, phase 0 player / 1 enemy / 2 ally) and area events
  (kind 4: x1, y1, x2, y2, 0 player / 1 enemy) bring in `z##`/`zoen` groups; `Normal()`/`Hard()` checks
  limit some to one difficulty. Tile events (kind 5: x, y, type) are villages (9, `MindGetItem`), doors
  (11), chests (12), seize (13), escape (14), arrive (41) and bandits razing a village (37).
- The chapter table in FE8Data.bin (96-byte records from `MCT01`) gives each chapter's win (`MW_`) and
  lose (`ML_`) labels and an extra loss; +0x24/+0x28/+0x2c are Hard's own goal set (Ch.20's 20 turns) and +0x30-+0x38
  Maniac's, with no Easy set (0x8016614c); +0x3c is the chapter's number and +0x3d-+0x40 the level bonus above.
  `BMSetTerm` in the script changes the goals section by section (Ch.17).

- `mapbuilddesc` lists the 3D models (32-byte records: seven words, the last the flags, then a name pointer); `mapbuildinst`
  places them in 12-byte records (x, y, rotation, model index, the rectangle of tiles it covers x0, y0, x1, y1, a float).
- The top layer: map.bin also has `panelindexRoof`/`uniquepanelRoof`. When a map loads (main.dol 0x80044450), the game lays
  that layer over the tiles of every closed model flagged 0x800 or 0x1000 (not 0x10): goal markers (`ascendancy` Objective,
  `attainment` Target, `secession` Sanctuary, `defense` Defend; they heal 10%), village houses (`house_*`, `bar_*`: Building,
  fliers only, over the Shack no one enters), doors, room roofs (`castleroof_*`, `mansionroof_*`), rocks (Stone over the ground
  they roll from), trap lids (Ch.23's pits: Bridge over a Hole) and Ch.17's ruins. Opening or destroying the model brings back
  the main layer (DoorOpen 0x8019f4a8, BuildDestruction 0x8019eaf4, InstantRoofOpen 0x8019f13c). An opening's
  `InstantRoofOpen` opens one before the battle (Ch.12's gangplank). The app starts each map from the top layer: a door opens
  the room whose roof covers or meets it, a razed village (`BuildDestruction` on the tile below the house) ruins its house. A
  room under its roof is a wall to everyone until then: the table lets fliers onto a roof, but the user found no unit enters a
  closed room.
- Edges: `maplink` (a count, then 3-byte x, y, mask records) gives a tile the sides a ground unit may leave by (0x8 up, 0x4
  down, 0x1 left, 0x2 right; a tile it doesn't name is open all round); fliers ignore it. `maplinkAbs` binds fliers too (Ch.17's
  section walls). The app draws every side a ground unit can't cross between two tiles it could otherwise walk: the fences,
  Ch.20's barricades (`board_dayne_01` models) and the sides of a few bridges. The fence models alone miss some and add some
  that block nothing.
- The playable grid: `mapextra` byte 5 is a border width (main.dol 0x80047af8); the game blocks every move out of the tiles
  that far in from each edge (0x80023a4c). The app crops each map to it, except Ch.17's sections.
- Fog: `SetSight(1, n)`, here in a function the opening calls; Ch.5's runs on Hard only (`if (!Normal())`). Fliers get the
  terrain's second set of bonuses (battle code 0x801a9520), which is zero on every tile the maps use.
- Tile corner heights: each `uniquepanel` record starts with four signed u16 corner heights, shared with
  the neighbouring tiles.
- Opcode 0x37 calls another handler of the same script by its number (the reader still names it `stmt`): Ch.11's talks
  with Zihark each call handler 30, which shows the talk and hands him over. The generator follows these calls when it reads
  what a handler does (`calls_by_difficulty`), and reads only a handler's own calls when it scans every handler, so nothing
  counts twice.
- Talks (trigger kind 8) name both speakers by PID string offset; a talk recruits whoever it passes to
  `UnitTransferToForceByPID(pid, 0)`; one that passes a unit to army 3 makes it a partner unit (Ch.10's prisoners). `UnitEscapeByPID` in the openings removes units before the battle (Nasir
  in Ch.11); `UnitCheckLiveByPID` branches in FinalDisposition choose between groups (Gatrie or a
  soldier in Ch.13). `SetFragile(x, y, HP)` makes a door or wall breakable.
- `SetRock(x, y, direction, id)` is a boulder (Ch.25, Trial 1): (x, y) is the foe who pushes it, and the rock sits on the
  next tile in `direction` (1 left, 2 right, 4 down, 8 up). Its path is the script's own: `TTPMEntry("6622242…")` calls, one per
  rock in its RegistLocationFlags handler, numbered in call order (main.dol 0x80110048); `id` picks one. The rock follows it one
  numpad step a tile (2 down, 4 left, 6 right, 8 up) whatever stands in the way, hits every unit it crosses for 10 damage
  whatever its Def (0x80025f0c), and breaks on the last tile (0x80129ca8, 0x8012a260, 0x80129fa4). None leave the map.
- `SetShooter(x, y, direction, IID)` is a ballista (Ch.19, 23, 24, 25): a bow user on (x, y), a pedestal
  tile, fires the machine on the next tile in `direction`. The machine's terrain (`アーチ`, or `投石器`
  for the Onager) is closed to everyone. `SetPit(x, y)` sets a trap on one of the holes (`穴`) in Ch.23's
  bridge, under its lid: a ground unit that moves onto it falls in and waits out the turn (fireemblemwod.com's Ch.23
  traps page), and the hole stays open after (the user, in the game).
- Hidden items (only Ch.15's desert): an area event (kind 4) that rolls `GetRnd(101)` against the unit's
  Skill (Thieves and Assassins always win) and gives an item with `MindGetItem`. A one-tile area that sets
  a flag a later event tests before `UnitTransferToForceByPID` is Stefan's spot (Lethe or Mordecai must
  reach it first; he brings the Vague Katti).
- Ch.17 is four sections on one map: `Opening18_2`-`_4` start each later section (new enemies, the goal
  via `BMSetTerm`, your chosen reinforcements via `mikata_zoen_0N`), and the reinforcement handlers test
  the `セクションN` flags. The app shows each section as its own map. A handler with no section flag
  belongs to whichever section's grid its units land in (Tibarn's hawks, in section 4).
- Each map is cropped to the game's own playable grid (the border width above). Units parked off it only watch (Haar and
  his wyverns in Ch.11). Ch.17's four sections share one map, so each keeps the part fireemblemwod.com's overview shots and the
  user's check in the game gave (`PLAYABLE` in `build-fe9-maps.py`).
- The trial maps (`zmap/trial_01`-`06`, scripts `C91`-`C96`) have chapter records of their own in
  `FE8Data.bin` (`MTM_TRI_MAPn`, the same layout as `MCTnn`), with their menu text in `MTM_TRI_MAPn_EX`
  and one placement file (`dispos_c`) for every difficulty. The app lists them in a second dropdown.
  Trial 5's reinforcements each wait on a door: a door's tile event (kind 5, subtype 11) sets a flag
  (`扉左下`, bottom-left) that the reinforcement handler tests before placing that door's group.
- A placement unit's bytes 76-88 are its AI routines. `SEQ_LOOTERMOVE` goes for villages and chests; `SEQ_LOOTERMOVE_ESCAPE`
  then leaves by an exit, a tile event of subtype 44. Only looters raze villages (Ch.3's and Ch.20's have none).
- The chapter's own boss is whoever's death handler (kind 11) sets `gf_complete` (Muarim, whose record lacks SID_BOSS). With
  none, the boss skill decides, but a boss who only arrives later in a chapter that has one is a named foe.
- Ch.17's later sections: each opening switches on a unit's place in your army (`var 09; int K; op2f; jz`) and sets it on a
  tile, sometimes walking it on to another; those last tiles are the sections' starts.
- What the handlers don't say in so many words is read by hand (`BY_HAND` in `build-fe9-maps.py`, each entry citing its
  handlers): Ch.10's alarm and its prisoners, Ch.11's Black Knight, Ch.3's, Ch.9's and Ch.12's conditional joiners, Gatrie's
  and Shinon's return (their own levels; Shinon's Brave Bow drops), Naesala and his ravens, Shiharam's talk with Jill, the
  green and yellow units' notes, Ch.24's Geoffrey and Black Knight, Ch.27-2's three ways to win and the Endgame's royal.
- The Prologue has no prep screen and nothing clears its opening scene, so its units stand where the
  scene walks them (`UnitSetPosDirByPID`, `UnitMoveDirByPID`). Boyd is the first opponent; when he
  falls (`ボーレ死亡`) the script hands Greil to the enemy (`UnitTransferToForceByPID`) and walks him in,
  and Boyd turns green.
- The Prologue's Mist is left off the map (`WATCHING` in the generator): she stands beside it the
  whole time, walking over only to hand Ike an item.
- A map with no prep screen (no `FinalDisposition`) is set up by its opening scene. Its `event` groups
  are only in the scene (Ena in Ch.27-2), and an opening's `InstantDisposSetMode(mikata_*)` puts your
  units on fixed tiles (Mist beside Ike in Ch.27-2; Oscar, Boyd and Titania in Ch.1).
- Ch.17's sections 3 and 4: Ike carries Leanne throughout, so she isn't drawn. The ruins' building
  tiles are shown as rubble (the same costs: fliers only).

Checked against the Fire Emblem Wiki's enemy counts; the exceptions are listed in
`src/logic/__tests__/fe9Maps.test.ts`.

## Chapter fields for the spoiler block (`scripts/build-fe9-items.py`)

- Each weapon carries `shopAt` / `forgeAt` (and, in Radiant Dawn, `bargainAt`): the map ids behind the `shop` / `forge` /
  `bargain` text, by difficulty; `baseAt`, the chapters whose base conversation gives it (script handler kind 14: Jill's
  Brave Axe and Tarvos in Radiant Dawn); and `giftAt`, the chapters whose own script hands it over outside a chest or
  village (`UnitGetItemShowing(Sub)`, `MindGetItem`, or a quiet `UnitAddItem` in an `Opening` or end handler: Ike's Ragnell
  in Ch.27-2, the Iron Sword that replaces his Practice Sword after the Prologue). A gift before the battle (a base
  conversation, an opening) is that chapter's; one at the end (kind 1) or from an event during it is the next chapter's
  (Rhys's Mend after Ch.6, the Ashera Staff after Ch.22). A handler another calls (opcode 0x37) is read only through its
  caller (Ch.4's Opening0 calls the one that gives the Regal Sword), and a `UnitAddItem` to a unit the chapter places on
  another side is that unit's (the setup gives Shinon his Brave Bow in Ch.18, and Gatrie a Steel Lance in Ch.13 if he
  came back with no weapon). Handler kinds 4 and 5 are chests, villages and buried or random treasure, which the map data lists.
  `kitAt` is the chapter each unit's gear is yours from, counted once, where the unit first joins: the deployment roster
  it first appears in (`bmapNN_mikata_c`), a group an opening or base places on your side (side 0), a `Join()` from
  zmap/always (Calill, in a base conversation before Ch.20), or a unit an opening hands over (`UnitTransferToForceByPID(pid,
  0)`: Mist and Rolf in Ch.9) are yours from that chapter; one a talk or the chapter's end hands over is yours from the next
  (Haar by Jill's talk in Ch.23; Geoffrey after Ch.24, where the end handler checks his PID and then calls
  `UnitTransferToForce(unit, 0)`). A laguz brings its class's strike (Janaff's and Ulki's beaks). Left out: the rosters an
  opening places only for a chapter started from the debug menu with no army (inside `if (!get("DBG_最初からやってる") &&
  ForceGetCount(5) == 0)`: `bmapNN_mikata_n`/`_h`/`_m` and `always_dbg*`), and a cutscene's `_event` groups (Nasir on
  your side in Ch.12's). The Endgame's royal is counted there (no base follows it).
- Drops are not here: the app reads them from the map data, which holds only units you can see. The placement files also
  list cutscene units (Petrine carries her Flame Lance in the chapter 7 files), so they can't say when a drop is available.

## Checking things in the game: the debug menus (Dolphin)

The retail program keeps two debug menus that a single data word cuts off; three Gecko codes (NTSC-U, GFEE01) bring them back.
They live in Dolphin's `GameSettings/GFEE01.ini`, with cheats turned on. The debug title's code comes too late as a cheat: the
boot script takes its `GOTO` on the first frames, before Dolphin's cheat engine runs (tried on 2026-11-01: the game booted to
the normal title). So that word is written into the program file of a copy of the extracted disc (`main.dol` at file offset
0x280354), which Dolphin boots through its `sys/main.dol`; the copy has the map menu's word (0x283f44) written in too.

- `04283354 00031001`: the debug title. The boot script "GameController" (0x802832fc) skips it with a `GOTO 2` right after
  `LABEL 3` (0x80283354); the code makes that a second `LABEL 3`. Any button opens its menu; Y cycles the difficulty byte
  (0x803307ae, shown as Rank); left/right on the top line walks the 44 chapter records (0 the developers' test map
  `C00`/`Map6`, 1-31 the story, 32-34 `C51`/`C52`/`C58` with no script on the disc, 35-37 the tutorial maps, 38-43 the
  trials); A starts the record as a fresh game (0x800aa078), so the chapter places its debug roster (`bmapNN_mikata_m` on
  Easy and Normal, `_h` on Hard; `trial_0N_mikata_c` in a trial). A trial started this way isn't in trial mode.
- `04286F44 80367790`: the in-map debug menu (Display / Visualize / Event / Game / System), in place of "Guide" in the map
  menu. Its only opener is the developer-list item "Kaneko" (0x80367790), whose list belongs to the map menu's "#C13Debug"
  item, built but left out of the map menu's list (0x80286f40). Game settings edits the difficulty, turn, funds, event
  points, playthrough count and who controls each phase; Clear Map wins the map (0x800a0ab8: the gf_complete call), and the
  chapter after it follows. Its "Chapter" line only shows the chapter (0x80330718) and map folder (0x80330c0c).
- `0428A1C8 80367654`: the unit menu's hidden JID / PID / Funeral items (slot 7 of the list at 0x8028a1ac is filled from a
  pointer nothing sets): JID changes a unit's class.
- The chapter number is the byte at 0x80330718 (the record's +0x3c). Writing it on the save screen after a cleared chapter
  starts that chapter next with your own army; the script is loaded as a chapter starts, so a write at the base is too late.
- Avoid the debug title's Import, Export and Shift MemoryCard File (host-PC and memory card transfers). The debug printf is a
  stub in retail, so the usage and log items show nothing.
