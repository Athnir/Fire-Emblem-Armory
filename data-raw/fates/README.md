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

## Weapon effects checked in the game

The weapon texts are Serenes Forest's, set against the game's own descriptions; where the two differ or the game says too little,
the user checked in the game (2026-10-31):
- The Bronze Axe can't crit, though its item record lacks the flag every other bronze and brass weapon has (+0x40 bit 0): the
  forecast shows no crit chance. The game's behaviour wins, so it keeps the no-crit icon.
- Dragonstone+ can't make follow-up attacks (a forecast against a much slower foe gives one attack), though its description,
  unlike the Dragonstone's, doesn't say so.
- After-combat penalties (the Silver weapons, the stones' "+" forms and the like) take 2 from each stat named every fight, stacking
  down to -99, and recover 1 a turn (a skill makes it 2). A stat pushed below 0 counts as 0.
- The Blessed weapons heal 10 HP at the start of each turn (up to full HP).
- The Yato's final forms: against Dragonskin their damage is cut by a quarter instead of halved (the Omega Yato's 37 came to 27
  against Anankos, a Parasol's 26 to 13). Their stat bonuses count from the inventory (the game's own breakdown says "Omega Yato
  (Inventory) +4").
- The Raider weapons' stripping is only a look: what they do is +3 effective Spd for follow-ups.
- The Cupid Bow heals the foe 20% of its HP after combat; the Hoe takes away terrain bonuses on both sides.
- The killer weapons' 4x critical damage is the wikis' figure, which the user trusts; it hasn't been read in the code.

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
- Serenes' "Armourslayer" and "Short Bow" are the game's "Armorslayer" and "Mini Bow" (prices match); the script maps them.
- Not in any file we have: when each paralogue opens (the children's need their parents married) and the chapters the Yato
  evolves in (`src/data/weapons/fatesGifts.ts`, from the Fire Emblem Wiki, which agree with the chapter titles in the files).

## My Castle's ally gifts and Lottery Shop (`scripts/build-fates-items.py`, `scripts/build-fates-castle.py`)

Read in the program (the code dump, base 0x100000) and checked live with Citra's GDB stub: predicted items for Kaze (Conquest),
Takumi (Revelation) and Keaton's birthday, stat boosts for Nina, Odin and Keaton, and a Lottery draw all came out as predicted.

- The item table (GameData.bin, 104-byte records counted from the IID pointer; the program's item objects start 8 bytes earlier,
  so its offsets are 8 more): +0x50 and +0x51 are the item's gate in Hoshido's and Nohr's ally-gift pools (signed, -1 = not in
  it); +0x52..+0x55 are four more pools of the same picker (gates 0, 15 and 27) whose caller (0x3a8b2c) isn't identified;
  +0x56 and +0x57 are its rank (1-5, 0 = not a prize) in the Dawn and Dusk lotteries. `gameItems.ts` carries the gift gates and
  lottery ranks (`allyGift`, `lottery`).
- A "!" event (castle event records, class 0x6a0e70) holds a type byte (+4), the person (+8), a partner (+0xc) and a random seed
  (+0x10), not an item. Types: 1 stat boost, 2 weapon exp, 3 item, 4 gold, 5 food, 6 ore, 7 support boost, 8 birthday (dispatch
  0x431f8c). Saved events are rolled 20/30/30/20% as stat boost / food / item / support (0x43110c). A birthday runs the stat
  boost, weapon exp and item steps in turn on its seed (Keaton's was 0). Gift requests ("give a gift") aren't these events.
- An item event (0x431d7c) seeds the generator with the record's seed (0x44abdc: an MT-style fill of a xorshift128 state, then
  20 draws) and calls the picker 0x430e5c: the route byte (game state +0x2e) gives Hoshido's pool on Birthright, Nohr's on
  Conquest and a 50/50 draw on Revelation; every item whose gate is from 0 to the game state's +0x30 is eligible (0x4319f0), and
  one is drawn uniformly. Reloading gives the same item; a later chapter can give another.
- The game state's +0x30 is the highest progress number of any story chapter cleared (the chapter record's signed byte +0x12;
  0x1b7300 only raises it, for records whose +9 is 0). Paralogues (-1, Mozu's 7) and DLC maps (0) never lower it. The numbers
  run 1-9 through Chapter 10, then 11, 12, 14, 15, 17, 18, 20, 22 ... 38 (Chapter 26), 40 (27, 28), the same on every route;
  `scripts/build-fates-castle.py` writes them to `fatesCastle.ts`. So gate 13 opens in the castle before Chapter 14 and gate 21
  before Chapter 19. Read live: 12 before Conquest 13, 38 before Revelation 27.
- Stat boost (0x431140): two different stats, the first of Str..Res uniformly, the second of the six others. Weapon exp
  (0x431780): +2 in every weapon type the unit has a rank in. A scouting map's glinting spots (map::MapSequenceInformal,
  0x369580) roll gold / ore / item / weapon exp at 20/30/30/20% (0x4310d4) and run the same event steps, so their items come from
  the same pools and gates.
- The Lottery Shop (0x3c62a4, prize roll 0x4dc220) draws from a seed it keeps in the castle data and saves the next one each
  play. Its level (opens after Chapters 7, 13 and 19: `castle_building.bin`'s `KID_クジ引き屋_1..3`) gives an item 30 / 50 / 70%
  of the time, else food or ore (50/50, uniformly among those whose byte +1 is 0 or the lottery's: 1 Dawn, 2 Dusk) in amounts 1-2,
  1-3 or 2-3. An item draws a rank by the level's weights (0x4dc040: 60/30/10/0/0, 35/40/20/5/0, 0/35/40/20/5), then an item of
  that rank uniformly. The ball is wood for food or ore, silver for an item under 4000 gold, gold from 4000. There's no chapter
  gate. A route's Lottery Shop offers its own lottery: Dawn on Birthright, Dusk on Conquest, both on Revelation (seen in the
  game; the menu code isn't read).

## Challenge battles (`scripts/build-fates-challenges.py` -> `src/data/maps/fatesChallenges.ts`)

- A scouted challenge is fought on a chapter's or paralogue's map. `Scripts/Encount.cmb` loads the chapter's terrain and its
  terrain script, then its encounter placement file `<code>E` and places `Player` (flags 4), `Mob00` (0x44) and `Mob01`
  (0x84). The files: `Dispos/A002E`-`A006E`, `Dispos/A/A007E`-`A026E`, `C006E` and the Revelation pack's `C007E`-`C022E`,
  `C024E`, `C026E`, `Dispos/X001E`-`X022E`; Conquest has none. Every slot is blank (`PID_無し`): the game picks the units.
- Which maps can be scouted is the chapter record's (GameData.bin `CID_*`, 28 bytes): byte +0x14 is its route mask (1
  Birthright, 2 Conquest, 4 Revelation; the encounter list takes a chapter whose bit the route has, 0x3d3164), and +0x18's
  0x100 bit (byte +0x19) is set on exactly the chapters with challenges, but for Chapter 2 (Castle: Reception Room): it has
  `A002E` without the bit. The game's list on a cleared Revelation file matched the app's 44 exactly (the user's check). Conquest
  has no scouting. A challenge
  goes by its scout name, the chapter's location.
- It isn't a rerun of the chapter but a map of its own on the chapter's: everything in it spent (the user's check in-game:
  every breakable broken, every chest, door and village used up, every Dragon Vein gone, Revelation 10's snow cleared). Read
  live in Revelation 20's (the trick list at `[0x6d7fec]`, each node's kind at +0xc and state at +0x16): every vein, area
  and village trick was in state 2 at once, the shiny spots in state 1; and on the map object `[0x6d73e8]` (terrain grid at
  +0x408, one byte a tile, 32 a row, an index into the terrain file's type list) all 68 `空／橋` tiles were `橋`, every
  bridge down at once where the chapter swaps them every few turns. Chapter 3's 13 were too. So the app gives each tile its
  second state (`spent` in `gameTerrain.ts`: the `／` part, else the `｜` part, read as the map's own terrain type of that
  name), and every foe tile and shiny spot is then on open ground, where the chapter's own map has walls on Paralogue 20's
  and most of Revelation 10's. Revelation 11's too: all 62 `平地／竹槍` tiles were `竹槍` (the
  game's "Spikes": a plain's costs, -10% HP a turn; the app's `de`), out for good, and its door open. Paralogue 14's
  (Rhajat's) matched the app's map to the tile: all 167 `毒沼配置／平地` tiles plain, and its `村` a `閉じ村` (a closed village:
  every village closes). And Birthright 18's, 21's and 24's, loaded on the Revelation file by pointing Chapter 3's record
  name (its chapter record's +0, the `CID_` string the battle loads by: ev::ChapterGetName, and 0x54424c for the encounter
  file) at theirs and scouting Bottomless Canyon N.: all 33 of 18's tiles acid bog, all 271 of 21's lava and its 20 bridges
  down, all 438 of 24's sky tornadoes, each to the tile the app's.
- Each map's two foe groups are encounters of their own, kept on the chapter's record in the encounter list `[0x6d92f8]`
  (records of 0x44 bytes: +4 the chapter, groups at +0xc and +0x28, 0x1c bytes each: +0/+1 set while it's there, +4 its
  make-up, +8 its level, +0x14 its seed). A new encounter (0x4187cc) goes to a free group, either one when both are free (a
  coin flip), the other when one is taken: a battle with one boss has either group, a dual-boss battle both. Seen live in
  Chapter 3's: one dual boss, two battles on Mob01 alone, one on Mob00 alone.
- How many foes a group fields, its boss included (0x417b98, from the group's seed, `+0x2d` the difficulty): n = its slots on
  Lunatic, n - 2 on Normal and Hard (n - 3 from 16 slots), then rand(n / 3 + 1) fewer, at least 1.
- Placing them (0x39ef4c, an RNG seeded with the same seed): the boss on the group's first slot; slots 1 to n - 1 shuffled (slot
  i swaps with 1 + rand(n - 1), i from 1 up); then each foe in turn on the next slot (0x39e8f4: a taken tile sends it to the
  nearest open one; a slot no unit can enter is skipped). A foe placed while two or more are left is paired with the next one
  on rand(100) < 50 (the boss) or 25 (the others), and the pair skips a slot. Replayed with the seeds read live, this gave all
  four Chapter 3 battles (unit records 0x140 bytes, tile at +0xf4/+0xf5 counted from the top) to the tile: 8 and 7 foes (both
  bosses paired), 10, 7 and 8. Revelation 22's Mob01 has two slots on one tile, (16, 6).
- The shiny spots are the terrain script's trick kind 14 (`args x, y, 1, 1, 14`, no handler code), two per map; the tile check
  (0x3822e4 -> 0x369518) looks for a trick of kind 13 or 14 on the unit's tile. They're fixed: both were live on exactly their
  script tiles in Paralogue 16's and Chapter 3's. A spot rolls gold / ore / item / weapon exp (20/30/30/20%, 0x4310d4) and runs
  the same event steps as an ally's "!", so its item comes from the ally-gift pools and gates.

## Revelation 10's snow

- Most of Izumo is `TID_氷／平地`, `氷／建物` and `氷／壁` (the game's "Ice"), which no unit can enter. In the chapter it's snow
  that hides what's under it: a unit of yours that attacks it clears that tile and the four beside it, and foes can't (the
  user's account; the script's loops of `ev::TrickTryTst` / `ev::TrickSet` over every tile aren't decoded). The map previews
  all of it cleared, its second state.

## What each Dragon Vein changes (`scripts/build-fates-terrain.py`)

A vein is a terrain-script handler with trick kind 11; its 8th argument is a string naming the corners of the areas (kind 12
tricks) it changes, in the script's own top-down coordinates ('3, 3, 5, 3, 6, 3'). The vein's preview is every tile in those
areas with a '／' second state, each looked up as the map's own terrain of that name where it has one (Revelation 16's flame walls
die down to Canyon, Paralogue 2's moat dries to Moat Bed, Conquest 25's Chamber turns into its Avo -20 form, Revelation 25's
locks to Darkness). Revelation 12's last vein names all four areas. Conquest 17's nine veins all name the one area covering the
whole map, so each shows every tile there that changes: unclear what one vein does in the game (to check). Revelation 21's veins
only flip a flag and play the map model's colour animation (`Mcl_colorA`): its red and blue areas are in the 3D model alone.

## Who the map's units are (`scripts/build-fates-units.py`)

- A chapter's Person file has 152-byte records: PID, FID (a portrait of its own), AID, MPID (the name), and at +0x24 the class
  number. GameData.bin's class table has 128-byte records (JID, FID, MJID pointers) with the class's number at +0x10. A unit whose
  name is only its army's (`MPID_暗夜兵` "Nohrian", `MPID_透魔兵` "Vallite", `MPID_謎の兵` "Invader"...) goes by its class, as the
  game shows it.
- Talks are script handlers of kind 0x617 (the low 12 bits): the speaker's PID ('' for anyone in your army, as Conquest 16's
  suspects), then the listener's. What the talk does is its `UnitTransferByIndex(unit, force)`: force 0 recruits (Takumi to
  Azura in Birthright 10, Benny and Charlotte to Elise in Revelation 14), force 2 makes the unit green (Arthur and Effie to
  Corrin in Birthright 23).
- Your units' gear: Corrin's from every chapter's Player group; a unit's from the Player group it first turns up in on the route
  without having joined before (the prologue's line-ups, Kaden in Birthright 12); and what a recruit brings in the chapter they
  join (a Support group's unit, a green unit the script hands to force 0, a foe a talk recruits). The later Player groups list
  units with preset gear (Azura with a Bronze Lance from Birthright 6, though she has the Brass Naginata she joined with: the
  user's screenshot in Birthright 10) that the game only gives a unit it has to create.
- Capture: a boss you can capture has a record of its own in GameData.bin's character table whose PID is `PID_捕獲_<name>`
  ("capture"), the unit that joins from the prison; its MPID (+0xC) is the boss's. There are thirteen: Daniela, Haitaka,
  Kumagera, Lloyd, Llewelyn, Nichol, Candace, Tarba, Funke, Daichi, Gazak, Senno and Zhara, the same thirteen as the Fire Emblem
  Wiki's Prisoner page. Story bosses (Kotaro, Kilma, Iago, Hans, Zola) have no such record. They're marked outside the DLC (the
  xenologues turn capture off) and the shared prologue (no one can capture yet).
- Anankos's two breaths are both "Dragon Breath": `IID_透魔竜のブレス１` (Mt 30, range 1-3, A) is "Dragon Breath (1-3)" in the
  app; `２` (Mt 20, range 1-5, S) is the one the head uses (checked in-game on Normal). The Heirs of Fate maps' copies of the
  royals' weapons (`IID_E035_ジークフリート`...) read as the weapon they copy, stat for stat the same, except `IID_E040_スカディ`,
  which has the Fujin Yumi's stats: "Skadi (Heirs of Fate)".

## When reinforcements arrive (`scripts/fates_arrivals.py`, `scripts/fates_schedule.py`)

- Each turn handler (kinds 0x10 and 0x13: first turn, last turn, phase) is run in a small interpreter for every difficulty and
  every turn up to 99. `ev::DifficultyGet` and `ev::TurnGet` are answered; anything else unknown forks both ways and makes the
  arrival conditional. A conditional arrival's guard is the flags read before its `ev::Dispos`, put down to what sets them: an
  area handler, a turn handler (or the group that handler placed: "once Group 1-1 has arrived"), and the terrain script's
  villages, doors and Dragon Veins (Revelation 13's two veins bring its reinforcements). Groups placed one after another with
  nothing read between them share one guard.
- Every handler that places a group adds to what's said of it (Birthright 10's Group 2 comes on Lunatic's turns 6 and 9, from
  two handlers). A group the script places on some difficulties only has its units on those alone (Revelation 24's extra
  groups, and the Birthright groups its scripts bring on Hard and Lunatic only).
- A turn step that would carry on past turn 99 is a cycle: "every 48th turn from turn 11 (11, 59…)".
- Opcode 0x4e has no operand: it stands alone between statements. Read as taking two bytes it ran on into the next
  instruction, which hid the groups Revelation 24's doors place just after one.
- A function handler has a name (the header's fifth word points at it: `ev::IsBoss2Appear`). An area handler covering the whole
  map (-1, -1, -1, -1) whose last argument names one runs after every action and acts when the function says so; what those
  check varies too much to put in words, so the ones that place groups are worded by hand (below).
- A group's name is matched whole ('Reinforce_01' isn't 'Reinforce_01_1': Revelation's Endgame keeps Reinforce_01 to _03, which
  nothing places). A group only turn handlers name that no turn and difficulty places is left out too: Conquest's Endgame picks
  its second set (Reinforce31 to 66) from turn 8 by `(turn - 4) / 4 % 4` (which six) and `% 6` (which one of them), and the two
  always have the same parity, so 32, 34, 36, 41, 43, 45, 52, 54, 56, 61, 63 and 65 never arrive; the other twelve come once
  every 48 turns.

## Anankos's summons

- Revelation's Endgame (C028): handler 17 places Reinforce_01_1 to _8 on turn 1, player phase. Handler 18 runs every enemy
  phase: it counts the enemy army (`ev::ForceUnitGetCount`) less the bosses still standing (both claws, then the head, then the
  core) and calls the summon function (handler 7) twice while fewer than 7 stand, once at 7. Handler 7 walks the summon cursor
  (`増援番号`, 1 to 8), calling handler 6 with that point's group and PID for the stage; handler 6 places it only if the PID's unit
  is nowhere on the map, so each point holds one unit at a time. The stage (`ステージ`) starts at 1: handler 10 (both claws
  defeated: `ボス１−１撃破` and `ボス１−２撃破`, set when `PID_C028_ボス１_１` and `１_２` die) places Reinforce_Boss_Second, the
  head, and adds 1; handler 11 (the head, `PID_C028_ボス２`, defeated) places Reinforce_Boss_Final, the core, and adds 1.
- The Heirs of Fate finale (DLC 8e, E000) works the same way with seven points, from turn 3, two summons while fewer than 8
  stand and one while fewer than 12. Points 1, 4 and 5 keep their stage-1 group, 2 and 3 have one per stage, and 6 and 7 change
  at stage 3. When the second claw falls, `竜脈オープン` is set; the next check (handler 62, its condition `竜脈演出判定`) opens
  the Dragon Veins at (4, 7) and (16, 7) and asks for the brothers, whom the next enemy phase places (Reinforce_Ryoma and
  Reinforce_Marx).
- `fates_arrivals.summons` runs the summon function once per stage (its first argument set to the stage) for each group's
  stages; the map notes say the rest.

## Arrivals read by hand (`WHEN` in `scripts/build-fates-units.py`)

- DLC 8c (E039): ReinforceShen / ReinforceSume come from whole-map handlers 18 / 20, whose conditions (17 / 19) wait for `シェンメイ死亡`
  / `スメラギ死亡`, set by death handlers 32 / 33: the defeated Arete or Sumeragi is replaced by a green copy. The Faceless: each
  enemy phase, handler 14 calls handler 13 for each side whose flag is set (Arete's death the right, Sumeragi's the left,
  `PID_E039_パラディン`'s, of the turn-3 group, the centre); on every other call it sets aside ReinforceNos (`ev::Dispos` flag 256:
  one Faceless) and places it on that side's marker group (ReinforcePosL / C / R, flag 520, whose units are `PID_無し`), so the
  markers show the Faceless. The Stoneborn: from the first enemy phase after either death, a counter places both golem groups
  when it's 2 modulo 3.
- Paralogue 22 (X022): handlers 7 and 8 (turns 5 and 7, enemy phase) place the groups unless `思考変化離脱` is set. Whole-map
  handler 10 sets it (and turns every foe to fleeing) once its condition, handler 9 (`IsEscaped`), holds: Nina is no longer in
  the enemy army and no `PID_X022_シーフ離脱` Outlaw is left.
- Revelation 24 (C024): the flag `発見` (discovered) is set by handler 10 (a patrol, `PID_C024_巡回１`, `４`, `５`, `８` or `９`, able
  to attack), handlers 49 to 53 (a fight with one), whole-map handler 15 on Hard and Lunatic (any foe acting while able to attack:
  `IsFind`), and the terrain script's doors at (21, 8), (6, 17) and (13, 27) opened before the other half of their pair; nothing
  sets it once the door at (16, 27) is open (`扉３−右`). Handler 11, each enemy phase, places Reinforce04_1 on discovery,
  05_1 / 06_1 once discovered with door 1 / 2 open, the 0N_2 groups once an area handler (12 to 14: Hard and Lunatic, while
  discovered) has set its trigger, and 07_1 / 07_2 once door 3's right / left half was opened first.
- Revelation's Endgame and DLC 8e: the boss forms (above), and DLC 8e's brothers.

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

