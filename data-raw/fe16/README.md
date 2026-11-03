# Fire Emblem: Three Houses (FE16) game files

Read from the user's own dumps in `Documents\FE Games\Switch dumps\NSP` (nxdumptool, from their console, keys in `~/.switch`): the
cartridge's base game (`[010055D009F78000][v0][BASE]`), the 1.2.0 update (`[010055D009F78800][v327680][UPD]`) and the six DLC
packages (`[010055D009F7900n][DLC]`). `scripts/fe16_extract.py` copies what the Armory reads into `data-raw/fe16/romfs/` and
`data-raw/fe16/dlc/` (git-ignored, never committed). Only data built from them is in the repo.

Field names follow the Three Houses Research Team's templates and tools (github.com/three-houses-research-team: `010-binary-templates`,
`bsic`), each checked against the files here; what they leave unknown is read in the program (`romfs/main.bin`, the update's `main`
NSO decompressed and relocated, loaded at 0).

## Containers

- **The update's RomFS** is a patch (NCA section crypt type 4, BKTR) over the base game's: a relocation table says which ranges of the
  merged image are the update's own and which the base's, and a subsection table gives each range of the update's data its counter
  generation (`scripts/switch_nsp.py`'s `patched_reader`). The merged image passes the RomFS's own SHA-256 hash tree (master hash and
  sampled data blocks).
- **The archive**: `DATA0.bin` indexes `DATA1.bin` in 32-byte records (u64 offset, u64 size, u64 stored size, u64 compressed); files
  go by number. A compressed file is Koei's chunked zlib: u32 chunk size (0x10000), u32 chunk count, u32 total, a u32 stored size per
  chunk, then from the next 0x80 boundary each chunk as u32 length + zlib stream (or, when compression wouldn't shrink it, the chunk as
  it is, its stored size its own length), each on a 0x80 boundary.
- **The update's files**: `patch4/INFO0.bin` lists the archive files it replaces (0x120-byte records: u64 number, u64 size, u64 stored
  size, u64 compressed, then the path of the replacement, `rom:/patch1/...` to `rom:/patch4/...`); `INFO1.bin` the files it adds
  (0x118 bytes: the same without the number); `INFO2.bin` the two counts. The paths name the files: 0 `msgdata.bin`, 6
  `fixed_data.bin`, 10 `fixed_stagedata.bin`, 11 `fixed_classdata.bin`, 12 `fixed_persondata.bin`, 22 `fixed_scenario.bin`, 30
  `fixed_shopdata.bin`, 83 on `common/scenario/bmap/SC00_00.bai`... (`romfs/<n>.bin` is file n as the game reads it, the update's
  copy where it has one.)
- **DLC**: each package has its own DATA0/DATA1, numbered 0-1059 on their own (not the base game's numbers); each number is filled by
  one package.
- **Data files** (`fe16_data.py`): u32 section count, then (u32 offset, u32 size) per section. A table section opens with 0x40 bytes:
  u32 magic 0x16121900, u32 record count, u32 record size; its records follow.
- **Text** (file 0): the same container, one section per language (0 Japanese, 1 English as the US release has it, 2 English (EU), ...),
  each four Koei `XL` tables: 'XL', u16 version, u16 size (low 16 bits), u16 columns, u16 count, u16 entry size, u32 header size, u32 -,
  then a u32 offset per string from the header's end, UTF-8 NUL-terminated. Table 1 (15397 strings) holds the names: person p at
  1157 + p, class c at 3453 + c, map m (the battle maps) at 957 + m, weapon w at 3756 + w and its description at 4256 + w, terrain t at
  5502 + t.

## Tables

- **Weapons** (`fixed_data.bin` section 0, 500 x 24 bytes): +2 / +3 its two effects' values, +4 an extra effect, +5 type (0 sword,
  1 lance, 2 axe, 3 bow, 4 gauntlets; crest stones and monster weapons too), +6 rank, +7 max range, +8 model, +9 crest (86 none), +10
  min range, +11 uses, +12 status it inflicts (96 none; 6 poison on the Venin weapons), +13 icon, +14 effective against (bits:
  1 infantry, 2 armour, 4 cavalry, 8 fliers, 16 dragons, 32 monsters), +15 0x40 broken, 0x80 crest stone, +16 Mt, +17 Hit, +18 Crit,
  +19 Wt, +20 / +21 two effects, +22 0x01 magic, 0x02 against Res, 0x04 leaves 1 HP, 0x08 not fliers, 0x10 no follow-up, 0x20 strikes
  twice (brave weapons and gauntlets), 0x40 / 0x80 relic. Weapon 0 is Unarmed; 1-5 the broken weapons; 6 the Iron Sword.
  Item numbers elsewhere are global: a weapon is its number + 10 (a person's starting items), + 11 in a unit's slots (0 there is empty).
- **Classes** (`fixed_classdata.bin` section 0, 100 x 118): +69 the class's tier (0 Noble and Commoner, 1 beginner, 2 intermediate,
  3 advanced, 4 master, 6 unique), +77 movement type, +78 the movement type dismounted, +79 its main weapon type (0 sword, 1 lance,
  2 axe, 3 bow, 4 gauntlets, 5 reason, 6 faith, 7 dark magic).
- **Persons** (`fixed_persondata.bin` section 0, 1201 x 80): +18 u16 the name shown (a person number: generic foes share names, person
  164's is 112, "Thief"), +26 its class. Section 6 (45 x 14): the playable characters' starting items (u16 -, then six global item
  numbers): Byleth an Iron Sword and a Vulnerary (1000), Edelgard an Iron Axe, Dimitri an Iron Lance, Claude an Iron Bow.
- **Scenarios** (`fixed_scenario.bin` section 0, 100 x 46): +14 0-2, +15 chapter (23 a paralogue, 24 an auxiliary battle, 25 DLC),
  +31 the victory condition, +32 map (a battle map number), +33-35 the foes' level on Normal, Hard and Maddening, +40-44 the defeat
  conditions. Scenario 0 is the Prologue, 1-11 Chapters 1-11 (all houses), 12 the other routes' Chapter 12 and 31 Crimson Flower's.
  The battle's title is text table 1's string of the same number ("A Skirmish at Dawn").
  Section 1 (11 x 3): by weapon type (0 sword .. 4 gauntlets), the weapons a unit with no items is given: Iron, Steel, Silver.
- **Terrain** (`fixed_stagedata.bin` section 0, 128 x 14): +4 Prt, +5 Rsl, +6 Avoid (signed), +7 HP healed per turn in percent (signed:
  a loss), +8 a breakable's HP, +10 its cost category (a column of section 1: 16 movement types x 16 categories, 255 impassable).

## Battles

- **Grids** (archive files 365 on: map m is 365 + m): u16 0, u16 0xFE17, then the playable area's bounds as u8 x1, y1, x2, y2 in
  half-tiles (the size is (x2 - x1) / 2 by (y2 - y1) / 2), then 32 x 32 tiles of two bytes, rows from the top: the terrain at the
  start, and the terrain after the tile changes (a door opened, a wall broken, a bridge laid).
- **Units** (`SCxx_yy.bai`, the first of each scenario's two files from 83): u32 0x2717, two u32, then three u32 offsets (from 0x18)
  of three tables of 100 records of 44 bytes, one per house (Black Eagles, Blue Lions, Golden Deer): +0 u16 person + 1, +4 u16 class
  + 1, +6 six u16 item slots (global + 1), +18 u16 which slots drop, +20 five abilities + 1, +25 x, +26 y, +27 facing, +28 a fixed level
  (0: the scenario's), +29 army (0 yours, 1 enemy, 2 green), +30 1 placed only by the script, +31 movement, +33 rank (0 the commander, 1 or 2 a
  sub-commander, 3 the rest), +34 battalion
  + 1, +35 its level, +36 / +37 two spells + 1, +38 a combat art, +39 gender. A script names a unit as table x 100 + record.
- **Scripts** (`SCxx_yy.bsi`, the second): u32 magic, u32, u32 event count, ..., the event offsets from 0x38. Each event: number, a
  trigger (u32 kind and three parameters: 2000 a check after each action, 12000 the battle's start, 13000 your phase's start, 15000 a
  unit selected...), then conditions and actions, each a u32 code and its u32 arguments (`bsic`'s list; every battle script parses
  to its event's own counts). The difficulty is a condition (140: 0 Normal, 1 Hard, 2 Maddening): the Prologue spawns Kostas and six
  Ruffians on Normal, and other records on Hard and Maddening.

## Mechanics read in the program

- **Hit** is two numbers (`0x5bb8a0`): the battle's random number (an LCG, x * 1103515245 + 12345, its own seed at `0x21c9a84`) taken
  twice, each (x >> 16) mod 100, a hit when their average, rounded down, is below the hit chance; the chance (`0xd9560`) is clamped to
  0-100 first, as the forecast shows it. The modulo makes 0-35 a little likelier than 36-99 (656 and 655 in 65,536), which raises the
  true hit by up to 0.04 points (a displayed 50 hits 50.54% of the time): counted over every state of the generator (all 2^32), the
  same to four decimals as two independent numbers with those weights. **Crit** is one number (`rand(100)`, `0x5bb810`), a crit when
  it's below the crit chance; a crit triples the damage (`0xdc1ec`).
- **Supports**: `0xd9330` adds a pair's bonuses by support level to hit (+0xb0 of the battle unit), avoid (+0xb4), crit (+0xb8) and
  crit avoid (+0xbc) from the pair's record.

- **Placing a unit** (`0x19e0..`, the unit tables' loader): its level is the scenario's for the difficulty, one lower for a
  sub-commander (rank 1 or 2) and two lower for the rest (rank 3), at least 1 (units of some persons take another level). A unit
  with no items (all six slots empty) whose class's main weapon type is physical (0-4) is given that type's default weapon from
  `fixed_scenario.bin` section 1: Iron, or Steel once its level plus its class tier's bonus (`0x1aa9170` on: +1 beginner, +5
  intermediate, +8 advanced, +10 master and above) reaches 19, Silver from 31 (`0x1a271a8`, `0x1a271ac`). The Prologue's Ruffians
  (level 1, a beginner class) get the Iron Sword, as Fire Emblem Wiki has them.

- **Effectiveness** (`0xd99a0`, called by the damage routine): the weapon's effectiveness (`0x402840`: byte +14 low, byte +15 high)
  against the defender's class type bits (class +81: 1 infantry, 2 armour, 4 cavalry, 8 fliers, 16 dragons, 32 monsters; checked
  one type at a time by `0x412d50`), less what the defender nullifies (`0xdd6e0`): a match in +14 is level 2, a match in +15's low
  bits level 1. The attack (`0xc3e70`, at `0xc404c`) multiplies the weapon's Mt by 3.0 at level 2 and 2.0 at level 1 (the larger of
  the weapon's and the second source's, never both), truncated. No weapon sets +15's low bits: effective weapons triple Mt.

## What the app builds (White Clouds so far)

- `scripts/build-fe16-items.py`: the weapons (fixed_data.bin section 0), with crest stones and other monster weapons as Monster.
- `scripts/build-fe16-maps.py`: the Prologue and Chapters 1 to 11 (Chapters 1 and 7 once per house: their foes are the other houses;
  the rest every house plays alike). A battle's start is its unit table's unscripted records plus what the start's events place,
  remove and walk (the conditions a start can know: difficulty, house, the start itself, other start events); later events that place
  units are the reinforcements, their time read from their conditions; events after the battle ends (EndMission, and what waits for
  it) are the end scene and place no one. A student the start tests 'is recruited' for is replaced by a soldier of their class on the
  same tile: a stand-in. The armory's stock is open from Chapter 1 by its level; starting gear comes from persondata section 6.
- `scripts/fe16_hit_table.py`: the true hit table.

## Unconfirmed

- What raises the armory's level (the stock's three columns); the app names the level, from Chapter 1.
- Chapter 2: the files place six Fighters on Normal and Hard (records 25-30); Fire Emblem Wiki counts five.
- Chapter 4: the two start groups and the turn-7 / turn-5 arrivals hang on event flag 61, set in the Blue Sea Moon monastery script
  (file 342) when "The Goddess's Rite of Rebirth" (quest 42-44, by house) is marked 4; what that state means in play.
- The Creator swords' max range byte is 150; the app shows 1-2 (Fire Emblem Wiki: 2 for Byleth only, 1 and Wt 19 for anyone else).
- The levels of named units met as foes (the loader has other paths for some persons); the app shows the general rule's.
- Whether Steal can take a weapon; whether fliers get terrain bonuses (not traced yet).
- The meaning of ranks 1 and 2 (both one level under the commander) and of SpawnUnit130's arguments.
