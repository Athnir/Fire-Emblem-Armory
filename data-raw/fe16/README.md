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
- **Equipment and items** (`fixed_data.bin` section 5, 50 x 24 bytes, global 600 on; section 6, 200 x 24, global 1000 on; the program's
  lookup `0x40c420` finds a global number's record in sections 0, 5 and 6): +5 the record's type (0-4 the weapon kinds, 5-7 the spells
  in section 1, 8 equipment, 9 an item, 11 a meal), +13 its kind, the icon it shows (equipment: 0 shield, 1 ring, 2 staff, 3 gem;
  items: 4 potion, 5 seal, 6 gold, 7 torch, 8 key, 9 stat booster, 11 dragon sign, 12 and 13 meals), +22 flags (0x40 the regalia's
  icon: the relics, the Seiros and Ochain Shields, the Caduceus and Circe Staves, the house leaders' tokens, the dragon signs, the
  Crest Stone; 0x80 with it on the Crest relics: the Aegis Shield, Thyrsus, Rafail Gem, their Dark copies, the Fetters of Dromi). A
  number in none of the tables (the gifts and ores, 1400 on) gets the weapon table's first record (Unarmed).
- **Classes** (`fixed_classdata.bin` section 0, 100 x 118): +69 the class's tier (0 Noble and Commoner, 1 beginner, 2 intermediate,
  3 advanced, 4 master, 6 unique), +77 movement type, +78 the movement type dismounted, +79 its main weapon type (0 sword, 1 lance,
  2 axe, 3 bow, 4 gauntlets, 5 reason, 6 faith, 7 dark magic).
- **Persons** (`fixed_persondata.bin` section 0, 1201 x 80): +18 u16 the name shown (a person number: generic foes share names, person
  164's is 112, "Thief"), +26 its class. Section 6 (45 x 14): the playable characters' starting items (u16 -, then six global item
  numbers): Byleth an Iron Sword and a Vulnerary (1000), Edelgard an Iron Axe, Dimitri an Iron Lance, Claude an Iron Bow.
- **Scenarios** (`fixed_scenario.bin` section 0, 100 x 46): +14 0-2, +15 chapter (23 a paralogue, 24 an auxiliary battle, 25 DLC),
  +31 the victory condition, +32 map (a battle map number), +33-35 the foes' level on Normal, Hard and Maddening, +36 bit 0 the
  battle's units are each house's own (set on the two mock battles and To War at Gronder, the only battles whose three unit tables
  differ, and on two unused stubs), +40-44 the defeat conditions (text 11906 + n): +41 the Black Eagles' (Silver Snow's from Chapter
  12), +42 the Blue Lions' (Azure Moon's), +43 the Golden Deer's (Verdant Wind's), +44 Crimson Flower's, 0 where that route never fights
  the battle; +40 a version without Byleth's fall. Scenario 0 is the Prologue, 1-11 Chapters 1-11 (all houses), 12-30 the other routes'
  Part II, 31-37 Crimson Flower's, 38-60 the paralogues, 61-85 the auxiliary battles, 86-99 the DLC's. The battle's title is text table
  1's string of the same number ("A Skirmish at Dawn").
- **The story's flow** (`fixed_flow.bin`, file 7): sections 0-3 are the routes as the scripts number them (0 Silver Snow, 1 Azure
  Moon, 2 Verdant Wind, 3 Crimson Flower), section 5 Cindered Shadows; 23 records of 40 bytes, record k chapter k, its +30 the battle
  fought (a scenario; 0xFF none). Crimson Flower plays 31-37 as Chapters 12-18; Silver Snow 12, 13, 14, 15, 16, 20, 22, 24, 26 and 28
  as 12-21 (its record 22 is empty: 21 chapters); Azure Moon 12-17, 21, 23, 25, 27 and 30 as 12-22; Verdant Wind 12-17, 20, 22, 24, 26
  and 29. Each route's chapters match Fire Emblem Wiki's route pages. Section 4 lists the paralogues (10 bytes: +2 and +4 the persons
  it's about, +8 the scenario).
  Section 1 (11 x 3): by weapon type (0 sword .. 4 gauntlets), the weapons a unit with no items is given: Iron, Steel, Silver.
- **Shops** (`fixed_shopdata.bin`, file 30, 13 sections; `fe16_data.shop_stock`). Each stock record names an item, its availability
  (0 not sold, 1 regular stock, 2 limited) and how many the shop holds at each of its levels (0xFF unlimited). The shops' update
  (`0x3de7b0`, which raises the level by the story's progress: the record `0x3d8620` returns names, at +0x19, one whose +9 is the
  level) sets a regular record's stock to its level's amount every time it runs and adds to a limited one only what a higher level
  brings (the armory at `0x3decd8`, the equipment and item shops in `0x3dcc50`: availability +0xc, stock by level from +0x10 and
  +0xd): a limited offer is a one-off, as Fire Emblem Wiki's marketplace page has it ('renewed each month for every item not listed
  as limited'). The shops counted, and how:
  - Section 0 the monastery's armory, weapons (20 bytes: +0 price, +8 u16 weapon, +12 availability, +16-18 stock by level); section 1
    its equipment (16 bytes: +8 u16 equipment, +12 availability, +13-15 stock): regular Leather, Iron and Steel Shields, a limited
    Silver Shield (its other records stock nothing at any level).
  - Section 2 the item shop (16 bytes, as section 1, global 1000 on): regular Vulnerary, Concoction, Antitoxin, Pure Water, Torch,
    Door and Chest Keys, Beginner, Intermediate and Advanced Seals; limited Elixirs and Master Seals (5 each).
  - Section 7 Anna's shop (8 bytes: +0 price, +4 the global item, +6 availability, +7 stock): regular Elixirs, Master Seals and Silver
    Shields; limited (one each) the nine stat boosters, the Hexlock Shield and the Accuracy, Critical, Evasion, Speed, Goddess and
    Prayer Rings. Every record matches Fire Emblem Wiki's item pages ('Anna's Shop (Limited: 1)', Master Seals unlimited).
  - Sections 9-11 the Abyss's Pagan Altar (the Expansion Pass; renown, not gold): weapons (20 bytes: +0 renown, +8 u16 weapon, +12
    availability, +15-17 stock), equipment and items (16 bytes: +4 renown, +8 u16, +10 availability, +12-14 stock): regular
    Beginner, Intermediate and Advanced Seals, Door, Chest and Master Keys and Abyssian Exam Passes; limited Master Seals, the
    Talisman and Hexlock Shields, the six rings, Magic and Healing Staves. They match the wiki's Abyss page (Pagan Altar: 'Limited: 1'
    for the equipment, 'Limited: 5' for the Master Seals).
  - Section 6 the traveling merchants (6 bytes: +0 the global item, +2 0 the southern, 1 the eastern, 2 the dark merchant, +4
    availability, +5 stock) and section 12 (6 bytes, their first 30 goods again: +2 stock, +4 availability): gifts, seeds and ores
    only (global 1400 on), nothing a foe holds.
  - Cindered Shadows' marketplace in the Abyss sells the monastery's level-2 stock (the wiki's Abyss page); no table of its own was
    found, and it adds nothing.
  Section 3 is the battalions, 4 the forge, 5 not items (four groups of ten levels), 8 the Abyss's undertakings (renown 500 to 6,000,
  the last two from Chapter 13).
- **Terrain** (`fixed_stagedata.bin` section 0, 128 x 14): +4 Prt, +5 Rsl, +6 Avoid (signed), +7 HP healed per turn in percent (signed:
  a loss), +8 a breakable's HP, +10 its cost category (a column of section 1: 16 movement types x 16 categories, 255 impassable).
- **Map objects** (`fixed_gimmick.bin`, file 16, section 0: 100 x 7 bytes; `fe16_data.gimmick`): +0/+1 and +4/+5 a tile as y, x (rows from
  the top), +2 the battle map, +3 a kind, +6 bit 0 whether the record asks for the tile changed. The scripts' CheckLeverActivated (510:
  negated, a record) is true when the record's map is the battle's and its tile (+5, +4) has its changed state (the program's tile +0x24
  bit 0) as +6 bit 0 asks (`0x544878`): Search for the Chalice's 84 and 85 are its western (grid (0, 28)) and central (9, 29) Magic Seals,
  terrain 108, as Fire Emblem Wiki has them ('Upon using the Spellbreak Key on the western Magic Seal').

## Battles

- **Grids** (archive files 365 on: map m is 365 + m): u16 0, u16 0xFE17, then the playable area's bounds as u8 x1, y1, x2, y2 in
  half-tiles (the size is (x2 - x1) / 2 by (y2 - y1) / 2), then 32 x 32 tiles of two bytes, rows from the top: the terrain at the
  start, and the terrain after the tile changes (a door opened, a wall broken, a bridge laid).
- **Units** (`SCxx_yy.bai`, the first of each scenario's two files from 83): u32 0x2717, two u32, then three u32 offsets (from 0x18)
  of three tables of 100 records of 44 bytes, one per house (Black Eagles, Blue Lions, Golden Deer): +0 u16 person + 1, +4 u16 class
  + 1, +6 six u16 item slots (global + 1), +18 u16 which slots drop, +20 five abilities + 1, +25 x, +26 y, +27 facing, +28 a fixed level
  (0: the scenario's), +29 army (0 yours, 1 enemy, 2 green, 3 a third army, 4 none), +30 1 placed only by the script, +31 movement,
  +33 rank (0 the commander, 1 or 2 a sub-commander, 3 the rest), +34 battalion
  + 1, +35 its level, +36 / +37 two spells + 1, +38 a combat art, +39 gender. A script names a unit as table x 100 + record.
  A unit of no army (4) never appears, even where an event places it: Chapter 6 fields Fire Emblem Wiki's 26, 28 and 32 foes only
  without its one, and Chapter 1's two extra Player slots are of no army. The battles every house shares keep everything in table 0
  (the other two are blank), each house's leader a record of its own placed by the house's route.
- **Monsters cover a square of tiles**: a class whose +73 indexes the monster table (`fixed_classdata.bin` section 4, 80-byte rows:
  +4 its weapon, +52 its health bars, +56 its size less one) covers that many tiles on a side, its unit's tile the square's top-left (in
  the grid's own rows from the top: the square runs right and down). The size matches Fire Emblem Wiki's for every monster checked
  (Demonic Beast and Giant Crawler 2, the Immaculate One 3, the Hegemon Husk 1, 'taking up only one space'), and with the tile as
  the top-left every monster any battle places stands on ground it can enter (196 of size 2, 7 of size 3); every other corner fails.
  The health bars match Fire Emblem Wiki's for every monster checked (the Experimental Demonic Beast and Giant Wolf two, the Demonic
  Beast three, the Immaculate One four); the app draws them as pips along the bottom of the monster's marker.
- **Scripts** (`SCxx_yy.bsi`, the second): u32 magic, u32, u32 event count, ..., the event offsets from 0x38. Each event: number, a
  trigger (u32 kind and three parameters: 2000 a check after each action, 12000 the battle's start, 13000 your phase's start, 14000 any
  team's phase's start, 15000 a unit selected, 18000 the moment condition 400 tests (`Moments`)...), then conditions and actions, each a
  u32 code and its u32 arguments (`bsic`'s list; every battle script parses
  to its event's own counts). The difficulty is a condition (140: negated, 0 Normal / 1 Hard / 2 Maddening, how it compares: 0 <,
  1 <=, 2 ==, 3 >=, 4 >): the Prologue spawns Kostas and six Ruffians on Normal, and other records on Hard and Maddening. Counts kept
  by the script (CheckVariableValue) compare the same way.
- **The trigger's first parameter is a bit field**: 1 a group head (its events name it as their second parameter), 2 switched off. A
  switched-off event never runs, nor does an event in a switched-off group (each carries the bit too). Read from the data: left out,
  the battles field what Fire Emblem Wiki counts (Chapter 9's 4, 5 and 7 Demonic Beasts, where a switched-off opening event would
  place all nine; Chapter 1's five units of yours, where one would add two Player slots on Normal), and a condition inside one is the
  one `bsic` names 'RivalryoftheHousesUnused'. The check in the program isn't found yet.
- **Reinforcement points**: a unit record of rank 4, 5 or 6 isn't a unit but a point that sends a copy of itself every turn, every
  other turn or every third turn from the turn it's placed, until the script takes it off the map. Read from the data against Fire
  Emblem Wiki, not traced in the program (the loader gives these ranks no level change): Chapter 8's two rank-6 Commoners come 'every
  third turn starting turn 1' (the wiki's 14 villagers at the start, not the files' 16), Legend of the Lake's rank-6 soldiers, placed on
  turns 2, 3 and 4, repeat every third turn, Insurmountable's rank-5 Wyvern Riders come on odd-numbered turns on Normal and its rank-4
  ones every turn on Hard, and Protecting Garreg Mach's two rank-5 Falcon Knights come on odd turns until the fire attack. The copies
  come in two levels under the battle's (the wiki: Chapter 8's Lv 15 of 17, Insurmountable's Lv 29 of 31).
- **Who is in your army**: from Chapter 12 the scripts test 'is recruited' for the route's own students too (Chapter 13 brings each
  route's students back only if recruited), so the maps take each route's house students as in your army (Silver Snow's without
  Edelgard and Hubert) and show a student another house could have taken as a stand-in. CheckDeathStatus (negated, a slot, 4) asks
  whether the unit's person was lost before the battle (Chapter 13's Seteth joins unless he was): the maps take no one as lost.
- **Blue tiles** (MakeMapTilesBlue: a rectangle and whether to mark or clear it): the opening marks the defended locations a foe takes
  to win (Chapters 12 and 14) and the destinations a unit is sent to (Rumored Nuptials' Ingrid); the maps draw them as objectives where
  the battle's conditions name them. Other blue tiles (Fort Merceus' gates, the onager Protecting Garreg Mach's Church Soldier makes for)
  aren't objectives.
- **Paralogues** (scenarios 38-60): the monastery's script (archive file 360) opens and closes each one with
  SetParalogueAvailability (the scenario, 1 or 0), by the chapter the calendar is in (ChapterSelect: negated, a chapter, how it
  compares), the route (the Black Eagles count as Silver Snow, 0, until the routes part) and, for some, a support (Characters: negated,
  two persons, a level, how it compares: Eternal Guardian's Byleth and Rhea, Weathervanes of Fódlan's Annette and Gilbert, Forgotten
  Hero's Byleth and Marianne, each at C), someone alive (DeathFlag: Dividing the World's Hilda) or flags (Legend of the Lake on Crimson
  Flower: 68 and 69, set when Seteth and Flayn fall in its Chapter 15). The flow's paralogue table (section 4) names the persons each
  is about; the maps count them in your army. Every route that fights one alike shares its map; Foreign Land and Sky's scenario sets
  +36 bit 1, and Crimson Flower fights its second unit table (the Church's army). Each paralogue's starting foes match Fire Emblem
  Wiki's on every difficulty.
- **The DLC's battles** (scenarios 86-99) are in the DLC's own archive: scenario s's .bai is DLC file 483 + 2s, its .bsi the next
  (Cindered Shadows' first, A Skirmish in Abyss, is DLC file 655); the base game's files at those numbers are of another kind. The
  maps Cindered Shadows adds (38 the Cathedral, 39 the Abyss, 40 the Underground Arena, 41 Beneath Garreg Mach) have their grids in
  the DLC archive too (file 427 + the map; the base game's 403-405 are 32,408-byte placeholders and its 406 is empty). Cindered
  Shadows' chapters are `fixed_flow.bin` section 5 (record k chapter k: 86-89 Chapters 1-4, none in 5, 90-92 Chapters 6-8), played on
  Normal and Hard (Fire Emblem Wiki's DLC page gives no Maddening, though some of its scripts test it); each battle's starting foes
  match the wiki on both. The DLC's paralogues: Black Market Scheme (93: Balthus and Hapi), A Cursed Relic (94: Yuri and Constance)
  and The Secret Merchant (97: Anna); no script read so far opens them, so their windows are the wiki's. Scenarios 95, 96, 98 and 99
  have no title (98's lose conditions name Jeritza) and aren't built.
- **Who's named**: a person under 100, from 1000 (the DLC's people: the Ashen Wolves, Aelfric, Jeritza, Anna), or a commander or
  sub-commander (ranks 0-2) whose shown name (+18) no other person record shows (Myson, Chilon, Baron Ochs, Verdant Wind's last
  battle's ten ancient heroes, Hegemon Edelgard); every other unit goes by its class.
- **Auxiliary battles** (scenarios 61-85; 81-85 the Expansion Pass's): each has ten 'Player' slots (seven or five in the Expansion
  Pass's) and fifteen foes, four monsters where monsters alone fight. The unit loader works their foes' levels out from your
  progress (`0x19e05c`: scenarios 61-80 and 81-85 take a level from a routine of their own), and Fire Emblem Wiki has their classes
  and items change each time they start, so the maps draw them as random foes where they stand; their commander keeps its record's
  Bullion. Which part of the game offers each is the wiki's list of auxiliary battle maps by location (Part I only: the Outskirts;
  Part II only: Gronder Field, the Chapel Ruins, Zanado, the Rhodos Coast, Ailell, the Tailtean Plains, the Sealed Forest and Conand
  Tower; both: the rest); the spoiler block opens them at Chapter 2, those of Part II at Chapter 13. The rare monster sightings'
  drops are the wiki's too: the King of Fangs a Rusted Sword or Gauntlets, the King of Wings a Rusted Sword or Bow, the King of
  Beasts a Rusted Lance or Axe, each the one forged into a silver weapon, or once the one forged into a legendary weapon (records 96,
  98, 116, 117, 111, 113, 101, 103, 106 and 108).
- **Rewards**: GrantItem to slot 0 is what the battle's end gives you; to a unit's slot, at the start, a foe's weapon by difficulty
  (Insurmountable's Steel Bows), shown with what it carries. A reward that checks a count the script keeps says what it counts where
  every addition waits on one unit's fall (True Chivalry's five villagers); the rest say 'on a count the battle keeps'.
- **The opening's removals**: a unit the map's load takes off (trigger 10000) is out of the battle: the opening scene that hides the
  beasts and walks them back in (Tales of the Red Canyon's) doesn't bring it back (the wiki's 6 foes on Normal).
- **Phases**: an event at a phase's start names the team (StartOfTeamPhase2: 0 yours, 1 the foe, 2 the green army, 3 the third army).
- **Moments**: `0x554920` runs the events for moment n (0-10), setting bit n + 5 of a flags word (the script system's +0x127060) while
  they run; the conditions test these bits and the team whose phase it is (+0x3d42 of the map): IsStartOfPlayerPhase (180),
  IsStartOfEnemyPhase (190) and StartOfTeamPhase2 (410) bit 7, moment 2, fired as a phase begins (`0x189e24`, after moments 0 and 1);
  StartOfTeamPhase (400) bit 12, moment 7, fired by another routine (`0x18bf00`); DidUnitsTurnEnd (540) bit 11, moment 6. The
  runner (`0x550e9c`) walks a list of events and never reads their trigger kind: each kind is a moment's list. In the data each moment's
  condition appears only under its kinds (IsStartOfEnemyPhase under 13999 and 14000, StartOfTeamPhase under 17999 and 18000,
  DidUnitsTurnEnd under 1999 and 2000, besides a few events of kinds 0, 5000 (the lose checks) and 0xFFFFFFFF), but in one branch of
  The Great Bridge Coup's Acheron event (below).
  The maps say condition 400 as during that team's phase.
- **The battle won**: DidCompleteMap (480) holds once the battle's victory is reached; the events it opens are the rewards and the
  closing scene (Ambush in the Arena's Aelfric, Besieged in the Chapel Ruins' Dark Bishops, placed off the grid), never a unit on the map.
- **Doors**: CheckDoorOpened (380) takes a tile, y x 1000 + x (`0x544ec0`), and holds once its terrain is no longer a closed door (17, 72
  or 107).
- **Spawns**: SpawnUnit130 places a record where the record stands; SpawnUnit (600: the record, x, y, facing) brings it in from that
  tile to its own (the Prologue's bandits, Chapter 5's Rogues; `0x5496e0` keeps x x 1000 + y x 10 + facing in the unit's +0xd0 and flags
  it for the spawn). A Walk (140) of a unit not yet on the map, which nothing spawns, puts it where the walk ends: Chapter 2's house
  leader, walked onto (12, 27) of the grid at the start, and Chapter 5's Black Beast, walked onto Miklan's tile once he falls (the battle
  ends when it does).
- **SpawnSpooky** (620: the record, x, y, facing, a flag) puts the unit on the action's own tile, not its record's. The script interpreter
  (`0x5480c0`, x1 the action) sends codes 530-860 through the jump table at `0xd17610` (index code - 530); 620's entry, `0x5497a0`, calls
  `0x54cdf0` and moves on 6 words. That runs in steps (the interpreter's step count at +0x20 of the script state): the first passes the
  action's x and y to `0xa6940`, which fails on a tile outside the playable area (+0x3b18 to +0x3b24 of the map: nothing is placed), keeps
  the tile where the unit can stand on it (`0x9c910`, each tile a large monster covers through `0xae1d0`: its terrain enterable for the
  class's movement type, no other unit on it) and otherwise takes the first tile that passes in squares of widening radius (1 to 31, rows
  from the top, left to right), then moves the unit there (`0x952e0`, `0x9b2c0`) and turns it by the facing (0 keeps its own); the next
  shows it (`0xa75a0`) with an effect, and, where the flag is set, calls `0x98a70`. Every tile a battle names is one its
  unit can stand on and no unit holds at the start, so the maps draw it there. It places: Chapter 10's soldiers and Experimental Demonic
  Beasts once Kronya falls (7, or 9 on Hard and Maddening: with Solon's walk-in, Fire Emblem Wiki's +10 and +13); The Great Bridge Coup's
  Acheron, three Armored Knights and two Paladins (Silver Snow, Azure Moon and Verdant Wind; Acheron at grid (27, 10), his record at
  (28, 10)); Saving Derdriu's Fortress Knights and Heroes once Hilda or the War Master standing in for her falls, and two Falcon Knights
  more on Hard and Maddening (the wiki's tiles, which are the script's); Crimson Flower's Chapter 12 two Golems with Rhea's soldiers (the
  wiki's 12 and 16) and Chapter 14 Nader and two Wyvern Lords with the first enemy phase's landing; Cindered Shadows' Giant Crawler (A
  Skirmish in Abyss), the Magic Seals' groups, the Assassins and the Golems from the southern border (Search for the Chalice), the
  Guardian Golem and the third army's Warlock and Assassin (A Harrowing Escape) and the Verrat beside the Umbral Beast (A Beast in the
  Cathedral). Chapter 6's (the Flame Emperor), Ambush in the Arena's (Aelfric) and Besieged in the Chapel Ruins' (the Dark Bishops) are
  end scenes.
- **Search for the Chalice's Golems**: one on turn 3 (grid (5, 28)) and one on turn 4 ((13, 28)), each at the start of the enemy phase,
  then another on its tile at the start of an enemy phase once the one before it falls: two from each tile on Normal, four on Hard. Each
  event also checks that Simone (record 34) stands and that neither the western nor the central Magic Seal's event (11, 16) has run: what
  stops them ('unless Simone is defeated or the Magic Seal at (10, 1) or (1, 2) is used first'). Fire Emblem Wiki has a Golem on every
  odd and every even turn, endlessly, one at a time.
- **Timing words** (`build-fe16-maps.py`'s `_clause`, `_chain`, `describe`): the time follows the condition tree, read for the
  difficulty, route and army (`_simplify`; a wait for a switched-off event never ends, so The Great Bridge Coup's Lorenz group comes only
  by event 14). What an 'and' needs is said together ('Turn 3, once Bias is defeated'); an 'or' of different kinds is said as alternatives,
  a turn first, then an area, the rest as 'or once ...' ('As soon as one of your units enters the marked area or once the door at (22, 13)
  is opened': Chapter 6's warp nexus); an 'or' of one kind is one clause ('either foe Thief ... or ... is defeated', 'one of your units,
  or Jeralt,'). An event waited for that checks nothing but defeats is said by its defeats, together where they're all needed (Crimson
  Flower's Chapter 12: Rhea 'once Flayn, Seteth and Gilbert are defeated'), as alternatives where one is enough (Saving Derdriu: Hilda's
  two records); an 'or' of waits alone is several ways to one step, each said whole (Ambush in the Arena's waves: 'Turn 4, the enemy
  phase, or once every foe is defeated'); one wait under an 'or' with other checks is that alternative, said by what sets that event off.
  A negated area check is 'once none of your units is left in' it (A Harrowing Escape's first checkpoint); a green unit's defeat names it
  as green; TurnNumber's comparison 3 ('that turn or later') beside another check reads 'from turn N' (Hunting by Daybreak's second
  joiners). Conditions read in the program for this: CheckDeathStatus (80, `0x5462f0` -> `0x556860`: kind 0 the unit on the map with HP
  left, 1 at 0 HP, 2 off the map (+0xd6 bit 5), 3 no such unit, 4 lost before the battle), any condition's first argument negating it
  (`0x545e00`), so a negated kind 0 is a defeat (or a unit the difficulty never places: Reclaiming the Capital's Titanus, Hard and
  Maddening's) and a kind 0 or a negated kind 1 a unit that must stand; TeamMovedIntoRangeOf (280, `0x547200`: a unit of the team other
  than the target that many tiles from it, by Manhattan distance, compared as its fifth argument says); UnitMovedIntoRangeOf (240,
  `0x547020`: two units that many tiles apart or nearer, its fifth argument for farther); DidBattle (360, `0x544e44`: the unit in the
  battle just fought, attacking or attacked); TurnNumber (220, `0x544c68`: the turn, or with its fourth argument the turn less script
  variable n, the fifth, compared as its third says).
- **What stops a one-off arrival** (`_stops`, `_stop_words`): its event (or a step before it, where that step checks something besides
  who stands) needs a unit standing, or another event not yet run: said as 'unless ... first' ('Turn 2, the enemy phase, unless the foe
  Warrior at (3, 20) is defeated first': Besieged in the Chapel Ruins, Fire Emblem Wiki's 'All reinforcements are halted if the Thief
  Leader is defeated'). A defeat that would set off an earlier step the arrival needs that unit standing for can't lead to it, so it isn't
  said (Capturing Derdriu's Wyvern Lord: 'turn 4, your phase, unless Nader is defeated first'). Left out: one of yours that must stand,
  another event that brings any of the same units or leads to one that does (the same group's other way in, said as its own time), one
  that needs this arrival, a step of it, or its copy for another difficulty not to have run (two ways the chapter can go, each the group
  that comes first: Protecting Garreg Mach's), the end scene's, one that names a phase alone, and what can't be said. A reinforcement
  point's copies say what stops them (`point_until`) instead.
- **Looting** (Chapter 11): MoveToRectangleAI580 sends a unit to work in an area; once the tiles it's after are taken
  (InteractedWithTerrain, the tile as y x 100 + x), MoveToRectangleAI sends it to one tile, where MovedCharacterOnTile takes it off
  the map and adds the number of its tiles to a count. The tiles are the Crest Stones in the Holy Tomb's walls (terrain 78), the
  count the stones carried off; the gifts when the battle is won check it.

## Mechanics read in the program

- **Hit** is two numbers (`0x5bb8a0`): the battle's random number (an LCG, x * 1103515245 + 12345, its own seed at `0x21c9a84`) taken
  twice, each (x >> 16) mod 100, a hit when their average, rounded down, is below the hit chance; the chance (`0xd9560`) is clamped to
  0-100 first, as the forecast shows it. The modulo makes 0-35 a little likelier than 36-99 (656 and 655 in 65,536), which raises the
  true hit by up to 0.04 points (a displayed 50 hits 50.54% of the time): counted over every state of the generator (all 2^32), the
  same to four decimals as two independent numbers with those weights. **Crit** is one number (`rand(100)`, `0x5bb810`), a crit when
  it's below the crit chance; a crit triples the damage (`0xdc1ec`).
- **Supports** (`scripts/build-fe16-supports.py`): `0xd9330` adds, for each of the up to three allies in a Linked Attack and the
  attacker's adjutant (`0xd91a0`: the battle unit's partner slots), the pair's bonuses by level: from the pair's own record where the
  support table holds one (`fixed_persondata.bin` section 9: 23 pairs, u16 + u16 persons, then five stats by five levels), else the
  partner's own record (section 8: one per playable character, all alike). The level is the support rank through `0xcea420` (C and C+
  1, B and B+ 2, A and A+ 3, S 4; a pair that can support but has no rank yet 0); a pair that can't support adds nothing
  (`0x41c040`). The stats go to the battle unit's +0xcc, +0xb8, +0xbc, +0xb4 and +0xb0: the hit routine (`0xd9560`) adds +0xb4 (hit),
  the attack sum (`0xd9140`) +0xb0 (attack), +0xbc is avoid, and +0xb8 (crit) and +0xcc are 0 in every record. Hit and avoid +3, +5,
  +7, +10, +15 by level; the 23 pairs' attack +0, +1, +2, +3, +5. A gambit's allies add the program's Gambit Boost instead (attack +1
  to +5, hit +5 to +25: `0x1aa83f8`-`0x1aa8440`). All of it is Fire Emblem Wiki's table. Which allies join (those that could attack the
  target, earlier-deployed first: the wiki) isn't traced.

- **Placing a unit** (`0x19e0..`, the unit tables' loader): its level is the scenario's for the difficulty, one lower for a
  sub-commander (rank 1 or 2) and two lower for the rest (rank 3), at least 1 (units of some persons take another level). A unit
  with no items (all six slots empty) whose class's main weapon type is physical (0-4) is given that type's default weapon from
  `fixed_scenario.bin` section 1: Iron, or Steel once its level plus its class tier's bonus (`0x1aa9170` on: +1 beginner, +5
  intermediate, +8 advanced, +10 master and above) reaches 19, Silver from 31 (`0x1a271a8`, `0x1a271ac`). The Prologue's Ruffians
  (level 1, a beginner class) get the Iron Sword, as Fire Emblem Wiki has them.

- **Steal** (the Thief's ability 159, whose +10 is skill property 61): the action menu (`0x175da4`) asks `0x15dd50` whether the unit
  has property 61 (its five ability slots, its class's and the rest), then lists the targets (`0xca560`): a unit on one of the four
  tiles beside the thief (`0xcba720`), of an army a unit of yours or the green army fights (1, the foe, or 3, the third army), visible
  (`0x9cce0`: not hidden in fog), whose Spd (stat 3 through `0xb0240`; the stats run Str, Mag, Dex, Spd, Lck, Def, Res, Mov, Cha, as
  the stat boosters' +17 has them) is lower than the thief's, strictly, and that holds an item `0x40cb80` allows. The command opens the
  trade screen in steal mode (`0x17dbc0` calls `0x5f34a0` with the flag at +0x415d, 'Select an item to steal.'), whose item list
  (`0x5ef740`) lets the thief take only what `0x40cb80` allows: an item whose record's type (+5) is 8 or more (equipment, an item, a
  meal: never a weapon or a spell, broken or not) and whose +22 lacks 0x40 (no relic or other regalia). Steal never takes a weapon
  (Fire Emblem Wiki: 'Cannot steal weapons or regalia equipment').

- **Effectiveness** (`0xd99a0`, called by the damage routine): the weapon's effectiveness (`0x402840`: byte +14 low, byte +15 high)
  against the defender's class type bits (class +81: 1 infantry, 2 armour, 4 cavalry, 8 fliers, 16 dragons, 32 monsters; checked
  one type at a time by `0x412d50`), less what the defender nullifies (`0xdd6e0`): a match in +14 is level 2, a match in +15's low
  bits level 1. The attack (`0xc3e70`, at `0xc404c`) multiplies the weapon's Mt by 3.0 at level 2 and 2.0 at level 1 (the larger of
  the weapon's and the second source's, never both), truncated. No weapon sets +15's low bits: effective weapons triple Mt.

## What the app builds

- `scripts/build-fe16-items.py`: the weapons (fixed_data.bin section 0), with crest stones and other monster weapons as Monster.
  The Rusted weapons (records 94-117: Mt 0, Hit 30, five of each kind named alike) are named for what the blacksmith forges each
  into: the forge list is `fixed_shopdata.bin` section 4 (12 bytes: +0 price, +4 the weapon forged from, +6 the material, +8 the
  weapon made, +10 the professor level, +11 how much material).
- `scripts/build-fe16-maps.py`: the Prologue and Chapters 1 to 11, then each route's chapters from 12 (`fixed_flow.bin`), once per
  route that fights them, the paralogues (the routes and chapters each opens in: `src/data/fe16/fe16Opens.ts`) and the auxiliary
  battles (a route's own units: its leader, its students, the stand-ins for students it hasn't got). Chapters 1, 4, 7
  and 11 are once per house: the mock battles'
  foes are the other houses, the Blue Lions' copy of one Rite of Rebirth event places two Myrmidons more (Hard and Maddening, flag 61
  unset), and in the Holy Tomb the Black Eagles' leader is the foe's commander. Every other battle the generator checks is the same
  for each house but for the leader beside Byleth, on the same tile ('your house leader'). A battle's start is its unit table's
  unscripted records plus what the start's events place, remove and walk (the conditions a start can know: difficulty, house, the
  start itself, other start events); later events that place units are the reinforcements, their time read from their conditions
  (a chain of events step by step, its areas numbered by step); events after the battle ends (EndMission, and what waits for it) are
  the end scene and place no one. A student the start tests 'is recruited' for is replaced by a soldier of their class on the same
  tile: a stand-in. A leader the lose condition names whom nothing places is a unit you must deploy. The armory's stock is open from
  Chapter 1 by its level; starting gear comes from persondata section 6.
- Forging (`fixed_shopdata.bin` section 4): each recipe is a source for the weapon it makes, 'forged from' its base at the
  blacksmith, with the professor level (+10: an index in E, E+, D, D+ ... S+, as Fire Emblem Wiki's forging table gives them), the
  gold and the material (text 5056 + the material: 64 Smithing Stone, 65 Black-Sand Steel, 66 Wootz Steel, 67 Arcane Crystal, 68
  Mythril, 69 Umbral Steel, 70 Agarthium, 71 Venomstone), from where both the base and the blacksmith can be had (the blacksmith
  opens with the quest 'Forge the Way' in Chapter 5's month: the wiki).
- Rare things to steal (`MapUnit.steal`, `build-fe16-maps.py`'s `rare_steal`): on a foe of the red or third army, what it carries and
  doesn't drop that Steal can take (`fe16_data.stealable`, never a weapon), that lasts (any equipment, which works while equipped; an
  item whose kind, +13, is a seal, gold, a stat booster or a dragon sign, not a potion, torch, key or meal used up for a moment's
  effect) and that no shop keeps in regular stock (a limited offer or Anna's one-each stock doesn't count: Master Seals and Silver
  Shields, which Anna keeps in stock, aren't marked; Energy Drops, Goddess Icons, Seraph Robes, the rings and Hexlock Shields are).
  No foe joins you in any battle (the scripts' ReplaceUnitBAI never turns a foe into a unit of yours), and the auxiliary battles'
  random foes show no items. 52 units are marked: every steal source Fire Emblem Wiki's item pages give for an item the rule counts,
  but Crimson Flower's Flayn (below), with The Face Beneath's Death Knight's Accuracy Ring and The Great Bridge Coup's Acheron's Evasion
  Ring ('Steal from Acheron (reinforcement)'), which the wiki's chapter pages give.
- Recruits' gear: the faculty and knights the monastery's script lets you recruit (file 360's RecruitTalk events, each with the
  chapter it opens from: Catherine 4, Cyril and Shamir 5, Hanneman and Manuela 8, Alois 11) carry their persondata section 6 items
  on joining (Catherine's Thunderbrand).
- `scripts/fe16_hit_table.py`: the true hit table.

## Unconfirmed

- TurnNumber's fourth argument (157 checks) compares the turn less a script variable (`0x544c68`: +0x126958 + 4 x the fifth argument,
  the array CheckVariableValue and IncrementVariable use), and no action read so far stores a turn there: the maps read those turns as
  absolute ('Turn 15'). Fire Emblem Wiki has Combat at Tailtean Plains' Dedue 'fifteen turns after the first wave'.
- Events of one group that each need the other not to have run (Protecting Garreg Mach's, Tales of the Red Canyon's) send the group whose
  time comes first; the maps give each its own time and don't say that one stops the other.

- What raises the armory's level (the stock's three columns); the app names the level, from Chapter 1.
- Chapter 2: the files place six Fighters on Normal and Hard (records 25-30); Fire Emblem Wiki counts five.
- Chapter 4: the two start groups and the turn-7 / turn-5 arrivals hang on event flag 61, set in the Blue Sea Moon monastery script
  (file 342) when "The Goddess's Rite of Rebirth" (quest 42-44, by house) is marked 4; what that state means in play.
- The Creator swords' max range byte is 150; the app shows 1-2 (Fire Emblem Wiki: 2 for Byleth only, 1 and Wt 19 for anyone else).
- The levels of named units met as foes (the loader has other paths for some persons); the app shows the general rule's.
- Whether fliers get terrain bonuses (not traced yet).
- The restock of Anna's shop and the Pagan Altar isn't traced: their availability byte is read as the monastery shops' is (`0x3dcc50`),
  and it matches Fire Emblem Wiki's 'Limited' labels.
- An item's kind 4 (the potion icon) holds the healing and curing items, and also the Crest Stone (regalia: Steal can't take it) and the
  Trade Secret (held only by the auxiliary battles' random foes); neither comes up on a foe the maps show.
- Fire Emblem Wiki gives Crimson Flower's Flayn (Chapters 12 and 15) a Magic Staff in place of the Caduceus Staff once An Ocean View
  is cleared. No script swaps it (perhaps the unit loader, not traced): the maps show her record's Caduceus Staff, which Steal can't
  take.
- SpawnSpooky's flag (its fifth argument; 0 only in Besieged in the Chapel Ruins' end scene, which follows each with a SpawnUnit130):
  what `0x98a70` does with the unit isn't traced.
- Condition 400 (bsic's StartOfTeamPhase, the 18000 events'): which moment `0x18bf00` fires isn't traced; the maps say 'during' the team's
  phase. Fire Emblem Wiki reads as a phase's end where it gives one: Chapter 6's turn-25 loss ('25 turns pass'), Land of the Golden Deer's
  turn-12 win ('survive 12 turns'), A Beast in the Cathedral's Verrat ('at the start of enemy phase 1'), Protecting Garreg Mach's
  Swordmaster ('Turn 1'); Ambush in the Arena's Death Knight comes 'during the enemy phase after the fourth wave of enemies arrives'.
- The Great Bridge Coup's Acheron event (26) is a phase start's (14000) with an 'or': a unit of yours in its areas at the start of the
  enemy phase, or event 14 (Ladislava's defeat, or a battle with Ferdinand or the Imperial General standing in for him) run and
  DidUnitsTurnEnd, a unit's action ended, which a phase start shouldn't see (`Moments`). The maps give only the areas, as Fire Emblem Wiki
  does ('After a unit reaches column 17, or passes the northeast L-shaped wall').
- Saving Derdriu: the script brings the two Falcon Knights on Hard and Maddening (event 56); Fire Emblem Wiki says Maddening only.
- A Harrowing Escape: the third army's Warlock and Assassin come once (SpawnSpooky) with two points of rank 5 walked onto their tiles,
  read as every other turn; Fire Emblem Wiki has a pair every turn. Its Guardian Golem has two events, the SpawnSpooky one and a later
  SpawnUnit130 at the third army's phase (a lever used or units in two areas); the map lists both times.
- A Beast in the Cathedral: the Verrat SpawnSpooky brings (record 60) stands on the tile of one of the five rank-8 Verrats the enemy phase
  places (records 30-34 and 35-39, which may be the Umbral Beast's Manifest Phantom summons: rank 8 isn't traced).
- The meaning of ranks 1 and 2 (both one level under the commander) and of SpawnUnit130's arguments.
- Reinforcement points (ranks 4-6): how the program sends their copies isn't traced; the intervals and the copies' levels are read
  against Fire Emblem Wiki. The wiki adds that a point blocked by a unit standing on it waits for the first turn it's free and counts
  from there.
- Chapter 12 (the other routes'): Fire Emblem Wiki counts three Armored Knights at the start on Normal (four on Hard); the script
  places the third's point, a repeating one, on turn 3, which the wiki's own notes give as when it first comes.
- Event flag 71: set by The Face Beneath's script when your army beats the Death Knight in a battle there (its events 43 and 53), 0
  when he falls otherwise (44 and 54); the Enbarr Infiltration then gives him a Brave Lance in place of the Scythe of Sariel. What
  'beats in battle' (its DidBattle check's argument 2) means in play isn't traced. Flags 47, 63, 64 and 12 (Azure Moon's Fort Merceus,
  Crimson Flower's Tailtean Plains, Forgotten Hero) are set by nothing read so far.
- The Secret Merchant's unit table holds only Byleth, Anna and Jeritza: where Fire Emblem Wiki's other eight units of yours deploy
  isn't read.
- When Cindered Shadows opens under the spoiler block: the maps open it from the start (the title screen offers it apart from the
  story).
- Which days offer each auxiliary battle (the calendar's weekly records and `fixed_freescenariodata.bin` aren't decoded); the
  scenario's +16 byte (2 to 17, rising with the battle's foes' level) may be the chapter each is first offered from, which would put
  Gronder Field's and the Chapel Ruins' in Part I where the wiki has them in Part II alone. How their foes' classes and items are
  picked (`fixed_freescenariodata.bin` section 2, 250 records of 10 bytes, may be the pools).
- Quest rewards (`fixed_lobby_quest.bin` section 0, 151 records of 52 bytes: +32-41 five reward items) hold only weapons other
  sources give (Steel and Silver weapons, a Killer Knuckles+; 56 records hold an Iron Sword as a placeholder); when each quest is
  offered isn't decoded, so quests aren't sources yet. The weapon pages list only the monastery's armory: the Pagan Altar's weapons
  (`fixed_shopdata.bin` section 9: the Venin weapons, the forged + weapons, Killer Axes and Bows...) aren't sources yet.
- Which persons a paralogue needs in your army is read from the flow's paralogue table, not from a check in the program.
- The rewards of The Remire Calamity, Salvation at the Chapel, The Forgotten and Retribution wait on counts whose meaning isn't traced
  (deaths while another unit stands, units reaching tiles): their notes say 'on a count the battle keeps'.
- Verdant Wind's last battle: an Agarthan Assassin withdraws in the opening scene (RemoveFromMap, kind 2), so the map leaves it out;
  Fire Emblem Wiki counts it at the start.
- Where a lose condition names the house leader and nothing places them (Chapters 3, 5 and 10, and the Holy Tomb for the Blue Lions
  and Golden Deer), the app says they must be deployed: read from the lose condition, not from a deployment rule in the program.
- Chapter 11: the script gives the Rusted Bow (forged into a Silver Bow) when no Crest Stone is carried off, and again when 11 to 19
  are; Fire Emblem Wiki gives only the full reward and, for at least half kept, an Advanced Seal.
- Chapter 8 on Hard: the script places a second Armored Knight (record 60) on (12, 15) of the grid, where record 53 already stands;
  the app shows both there, as where the game puts the second isn't traced.
