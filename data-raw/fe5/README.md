# Thracia 776 (FE5) game files

Read from the user's own cartridge image: `Fire Emblem - Thraki 776 (J).smc` (SNES, the retail cartridge dump, 4 MB, no copier header,
CRC32 FC519952, the one Lil' Manster patches). The image stays on the user's PC (default path in `scripts/fe5_rom.py`, or set `FE5_ROM`)
and is never committed; only data built from it is. The cartridge is LoROM: `$BB:AAAA` is file offset `(BB & 0x7F) * 0x8000 +
(AAAA & 0x7FFF)`. Data is little-endian.

Where the tables are and what their fields mean come from the Lil' Manster team's public build files
([famitino/fe776br](https://github.com/famitino/fe776br): Zane Avernathy's and Ultimage's disassembly, Miacis' project) and Zane
Avernathy's [VoltEdge](https://github.com/ZaneAvernathy/VoltEdge) library. They're a map: every table and routine used was checked in the
clean ROM, and where the build files are for the patched game (Lil' Manster moves some tables), the original addresses are used.

## Names (`scripts/fe5_names.py`)

English names are Lil' Manster's (`Lil-Manster-1.08.zip` next to the ROM; the user's choice, as for FE4). The patch is applied in memory
(`scripts/bps.py`) and nothing patched is written. Its menu text is drawn from pre-built tiles: a name is u16 codes ended by 0, each code
a pair of 4-pixel letters found in the table at `$BF:B704` (6 bytes: the code, the upper and lower 8x8 tile, 2bpp, at file offset
0x39CC80). `fe5_names.py` draws each pair and matches its two halves against the shapes of the team's menu font (its own `GLYPHS`
table). Wide letters span cells; three pairs draw "im" and "mm" across cells (`TIED`).

- Items: u16 pointers at `$B0:8FC3` (bank `$B0`, ids 0-0xA7: the item table ends where this one starts, `$B0:80AB` + 23 x 0xA8, and
  its last eight records are the Bargain to Luna manuals); classes `$89:8000` (bank `$89`, ids 1-0x77); characters `$86:DA4D` (bank
  `$86`, ids 0-0x156).
- Chapter titles and objectives are plain text in the patched image (file offset 0x40C353): 35 titles, then the 35 objectives, one
  line each ended by 0x01 (an objective without a full stop runs on to the next line).
- Generic units are named after their army ("Munster", "Friege"): a name three or more characters share, an army or a class name
  counts as generic, and the maps call such a unit by its class.

## Items (`scripts/build-fe5-items.py` -> `src/data/fe5/fe5Weapons.ts`)

23 bytes per item at `$B0:80AB` (item 0 is none): +0 type (low nibble; a magic sword's magic in the high nibble), +1 Mt, +2 Hit, +3 Wt,
+4 uses (signed: -1 never breaks), +5 crit, +6 range (min low nibble, max high), +7 rank (50 = E ... 250 = A; anything else is a
pointer in bank `$B0` to a list of the characters who may wield it, u16 ids ended by 0), +9 effectiveness (pointer to a list of class
ids ended by 0), +0xB stat bonuses (pointer to 8 bytes: Str, Mag, Skl, Spd, Def, Con, Lck, Mov), +0xD cost per use, +0x11 use effect,
+0x12 weapon effect (an offset into the effect routines), +0x13 / +0x14 skills, +0x15 traits (1 ballista, 2 magic at range, 4 weapon,
8 tome, 0x10 staff, 0x20 never breaks, 0x40 can't be sold, 0x80 broken).

- **Price** (`$83:B00D`): uses x cost per use, + 200 for weapons and staves.
- **Effectiveness** (`$83:D347`): the weapon's Mt is added twice more (tripled). A magic sword isn't effective at 1 range (`$83:97AB`).
- **Magic swords** (trait 2, `$83:CF77` on): at 2 range the attack takes the item's second type and counts as a tome: the wielder's
  Magic adds to Mt, the target defends with its Magic (Thracia 776 has no Resistance), and Con doesn't lighten it.
- **Weapon effects**: poison (only when the wielder isn't on your side: `$83:E106` checks the attacker's allegiance), the Devil Axe's
  backfire ((21 - Luck)%), life steal, petrify, Hel's 1 HP, berserk and sleep (neither on a throne or gate).
- **Skills** on items: +0x13 Adept 1, Charm 2, Miracle 8, Vantage 0x10, Accost 0x20, Pavise 0x40, Nihil 0x80; +0x14 Wrath 1, Astra 2,
  Luna 4, Sol 8, Paragon 0x10, Brave 0x40 (strikes twice).
- Bragi's Blade's list of wielders (`$B0:99FA`: Nanna, Diarmuid, Fergus) has no end marker, so it runs on into Light Brand's (Leif):
  Leif can wield it. Valflame's and Loptous' lists are empty. Lil' Manster gives Valflame and Mjölnir rank A and Loptous rank E; the
  clean ROM's locks are used.
- Left out: the ballistae (trait 1), the broken items, and everything that isn't a weapon or staff. Forseti's second record, the same
  tome that never breaks, is "Forseti (unbreakable)".
- The staves' effects aren't in the records: they're Serenes Forest's (its Thracia 776 staves page), matched to the ROM's rank, uses
  and price first, in the app's own words. Serenes gives Return 1810 gold; the ROM's price is 2000.

## Battle (`scripts/build-triangles.py`, `scripts/build-fe5-supports.py`)

- **Hit** (`$83:D3B7`): Skill x 2 + Luck + the weapon's Hit + the hit-and-avoid bonus; avoid (`$83:D3DD`) is terrain + the same bonus +
  Luck + attack speed x 2. The adjusted hit is held between 1 and 99 (`$83:D42C`) and rolled once, against one random number
  (`$83:A791`): true hit is the displayed hit.
- **The hit-and-avoid bonus** (`$83:E2F3`): supports, Charm, leadership, the triangle and terrain's own table (all 0).
- **Triangle**: `$83:DBC4` checks the attacker's type against three signed bytes per type at `$83:DBEF`; `$83:E053` gives only the
  advantaged side +5 (`$83:E071`). Light and dark beat fire, thunder and wind.
- **Leadership** (`$83:E414`): every unit under the same leader with stars adds 3 per star, anywhere on the map. **Charm**
  (`$83:E3EA`): +10 for each charming unit of the same army within 1-3 tiles.
- **Supports** (`$83:E5A5`): 5-byte entries at `$88:80CD` (gets u16, gives u16, bonus u8). A giver alive, on the map and within 3
  tiles adds its bonus (10, or 20 for four pairs) to hit, avoid, crit and crit avoid. No levels.
- **Stealing**: the Steal command (`$87:99B7`) is a unit's with the Steal skill (skills 1, 0x02, the character's or its class's: the
  Thief and Rogue classes, Lara and Perne). Its targets (`$87:99D8`, each tile by `$87:9A1F`) are the foes beside it (`$83:B34F`)
  that aren't ballisticians and whose Spd is below the thief's: both the unit's own plus its class's base, held at 20
  (`$83:90BE`; Spd is +0x0E of the unit buffer, from class base +4 and character +4). The command is offered when the foe or the
  thief holds anything, since the same menu can hand over the thief's items. The menu (`$87:B4A2`) lists all seven of the foe's
  items, weapons included; one can be taken when its weight is below the thief's Con (`$87:B51A` → `$83:9745`, the same Con, held
  at 20). So a foe at Spd 20 can't be robbed, nor an item weighing 20 (the Loptrian Fang, the ballistae) taken.

## Maps (`scripts/build-fe5-maps.py`)

- **Chapters**: 52-byte records at `$84:804A`, in the game's chapter order (1, 2, 2x, 3, 4, 4x, 5 ... 15, 16A, 17A, 16B, 17B, 18 ...
  24x, Final): +9 tileset config, +15 map, +18 map changes, +21 starting positions, +24 objective markers, +35 fog vision.
- **Map**: compressed (the game's own decompressor, `$80:B574`, run by `scripts/fe4_cpu.py`): width, height, then a u16 per tile whose
  top 13 bits are the metatile. The terrain of each metatile is the tileset config's bytes from 0x2000 (`$83:B476` reads `$7F:2010`,
  the config being unpacked to `$7F:0010`).
- **Playable area**: the cursor never reaches column 0 or row 0 (`$83:BDD8` refuses a move onto either), so each map is the stored one
  without them. (The Fire Emblem Wiki gives Chapter 1 as 19 x 21; the code gives 22 x 20.)
- **Terrain**: 44 ids. Each class points (+0x17, +0x19, +0x1B, +0x1D, bank `$86`) at its movement costs, avoid, defence and hit-avoid
  rows. Forts, gates, thrones and churches heal a flat 5 HP (`$83:836E`); the magic floors add 10 Magic. Indoor tiles keep out mounted
  units and fliers (they dismount to enter); the dismounted classes move as infantry.
- **Objective markers** (+24): a colour byte, then [x][y][arrow] entries ended by 0: the escape points.
- **Starting positions** (+21): [x][y] pairs ended by FF.
- **Map changes** (+18, compressed like the map; `fe5_rom.map_changes`): a byte count (the routines read it with AND #$FF, `$84:940E`;
  the byte after it counts the flagged entries, which is why reading a u16 count gave nonsense for Chapters 1, 3, 5, 6, 8x, 11, 11x, 12
  and 12x), then 6-byte entries [data offset u16][x, bit 7 a flag][y][width][height], the offset from the start of the list to a patch
  of u16 cells, rows from the top left (the cell >> 3 is the metatile, as on the map; 0 leaves its tile as it is). The list sits
  unpacked at `$7F:B0F5` (`$84:9260`). What the changes do on the maps is below.

## Map changes (`build-fe5-maps.py`: `map_changes_of`, `build_changes`)

Each change is previewed on the map: the tiles it gives another terrain, and what each becomes. The opening's are made before the
battle, so the map starts with them. 187 in all: 103 doors, 5 drawbridges, 57 houses, villages and churches razed, 10 cracked walls and
12 other changes.

- **Laying them**: the script call TileChangeByID (`$8C:ACD3` -> `$84:92D5` -> `$84:92EA`) writes change *n*'s cells into the map
  (`$7E:81CB`) and the terrain is reloaded from the tileset (`$83:B476`); SingleTileChangeByCoords (`$8C:AADA`) writes one metatile
  (its value is the metatile: 1008 a closed house, 38 an opened chest's floor, 933 a closed door in their tilesets) and reloads the
  terrain too; `$8C:AB17` makes a tile's terrain a door without redrawing it, until the next reload (Chapter 22's bridge, for a moment
  while it's raised). `fe5_events` records them in order (`Run.edits`). The flag (x bit 7) keeps an entry out of the routines that lay
  every change not made yet (`$84:93D8`, `$84:9437`, used by a script in bank `$94`: `$84:92EA` ANDs the entry with `$2B`, 0 from
  TileChangeByID, 0x80 from them); it doesn't change what TileChangeByID does.
- **What sets a change off** is its definition's conditions. A definition with no conditions never runs (`$8C:96D8` refuses one: CPY
  #$0005): such entries in a location list (Chapter 6's wall, Chapter 17B's gates, Chapter 22's bridge), and doors at (0, 0)
  (Chapter 17A's), are there so that reloading a chapter redoes the changes whose flags are set (`$8C:9637`; the scripts skip their
  dialogue while `wEventEngineMapChangeFlag` is set). A change's flag is its id + 0x21 (`$8C:9BF7`).
- **Doors and drawbridges**: a location definition checks the tile in `$7E:4FA0` / `$7E:4FA2`. The Door and Drawbridge commands
  (`$87:819A` and `$87:81B2`, checks `$87:8F14` and `$87:8FF6`) are offered to a unit holding a Door Key or a Bridge Key (`$87:A27F`),
  or with Steal (skills 1, 0x02) and a Lockpick (`$87:A299`), beside a door (terrain 0x20) or drawbridge (0x24) it can see (the
  visibility map, `$7E:8DCB`); they set that tile for each one beside the unit (`$87:8FDA`, `$87:90BF` -> `$83:A7EC`), run the location
  events (`$8C:9CBD`), and spend the key or one use of the Lockpick (`$87:A2BA`, `$87:A2DF`). The keys and the Lockpick do the same from
  the item menu (use effects 26, 28, 30: `$87:BE60`, `$87:BE65`, `$87:BEB8`, done by `$87:C03E`). The **Unlock** staff (use effect 92)
  targets every door, drawbridge and chest on the map its user can see, at any distance (`$87:C3E1`; its 1-10 range isn't used), and
  runs the tile's location events (`$83:F300`, `$83:F34A`). The AI has door-key, chest-key, Lockpick and Unlock actions too (the bits of
  `$7E:4049`, `$8D:D8EB`-`$8D:D95E`). Every door and drawbridge tile on the maps has a definition (tested). A door definition on a tile
  no command targets never runs: Chapter 4's (11, 9)/(12, 9) and Chapter 11x's (1, 16), (5, 16) and (12, 14) are walls (Chapter 4's
  central room opens only in the end scene, which isn't drawn), Chapter 20's west door stands in the unplayable column 0, and Chapter
  12's (11, 2) and Chapter 13's (33, 9) stand on a river and a bridge whose changes write the tiles the map already has.
- **Rooms under a roof** (terrain 21, and the map-edge cells inside Chapter 24's): closed to every unit, fliers included, until a change
  opens them; drawn as closed rooms (`ws`, terrain_codes `X`). A unit a group places on a roof tile is hidden in its room
  (`$83:9620`: state 0x1040) until a change over its tile is made (`$84:95BA`), and its note says so. Three rooms: Chapter 4's upper
  room (its doors), Chapter 24's Kia room and the Final Chapter's throne room.
- **Chests**: the Chest command (`$87:81EA`, check `$87:90DB`) on the chest a unit stands on, with a Chest Key or with Steal and a
  Lockpick, or Unlock. The chest's script lays the floor or road it stands for, which works like the chest tile (the terrain table gives
  them the same costs and bonuses), so an opened chest isn't drawn as a change. A chest definition (VANILLA_CHEST) is a chest on the map
  even where its tile is under a roof (Chapter 24's Kia chest, at (10, 43), in the room that opens).
- **Razing**: an enemy's raze action (AI action 4, `$83:F6F6` -> `$8D:851D`) runs the location events of the house, village or church
  it stands on, or of a cracked wall (terrain 0x26) beside it (`$8D:85CE`), with the cursor there; the definitions that check the enemy
  phase lay ruins or break the wall. 57 razes in 14 chapters. **Cracked walls** have no HP: nothing attacks one, and no command of yours
  breaks one; Chapter 14's four and Chapter 20's six fall only to a foe's raze. Chapter 21x's three have no definition and never break
  (a note says so). The Fire Emblem Wiki (The Onslaught): the gates and chipped walls "can be broken by an enemy that moves to do so ...
  and turns the terrain into wasteland".
- **The openings' changes**: Chapter 2 starts with a village in ruins (the Fire Emblem Wiki: "the one destroyed in the opening
  cutscene"), Chapter 11 with six of its doors open (the trap shuts them), Chapter 11x with its bottom door open; Chapter 3's opening
  opens a door and shuts it again. **Chapter 4's chests**: the opening takes the items of your units on the map (Leif and Lifis; the
  units its group places carry none: `$8C:B82B`, each unit by `$8C:B88F`, skipping dead, disabled, captured and set-aside ones), adds a
  Rapier, a Javelin, a Steel Sword and a Vulnerary (`$8C:B964`), keeps the 16 the game values most (`$8C:B8C0`, by `$83:B234`: items
  first, then staves, then weapons, each by cost per use; the rest are lost) and lays a chest for each on 16 tiles (`$99:9147`, read
  by `$8C:BA4E`) in a random order (`$8C:B98A`; the chest is metatile 0x27). The map draws all 16 as chests; the Fire Emblem Wiki
  (The Dungeon): "anywhere from 4 to 16 chests", with the Javelin, Steel Sword, Rapier and Vulnerary in them. The four are chest
  sources on the weapon page; with that, the Javelin and the Rapier lose their capture lines there (a foe's line is kept only where
  nothing else gives an item: `gba_maps.write_sources`).
- **Other changes**, each saying what sets it off, read from its definition (turn, phase, area, flags and what sets them, a talk) and
  a script check of a named character (played with them gone, it changes nothing: "while Kempf is on the map"): Chapter 6's wall at
  (7, 6); Chapter 11's courtyard trap (Leif, or a unit carrying him, stopping in the area, while Kempf is on the map: six doors shut,
  and each opens again as a door does; drawn as a trap zone; the Fire Emblem Wiki, Fort Dandrum, says the same); Chapter 11x's door
  Oltoph leaves by on turn 30; Chapter 17A's bridges (turns 10 and 15) and its wall at (28, 23); Chapter 17B's eight houses (Leif's
  visit to any closes all eight) and its two gates (once 20,000 gold is paid at the house at (1, 5); the middle one also on the enemy
  phase after you enter the courtyard); Chapter 22's bridge (the Fire Emblem Wiki, Across the River: removed once a unit of yours acts
  on the east bank); Chapter 24's Kia room; the Final Chapter's throne room (`$B9:BAED`: your units on all six magic seals, as your
  phase starts). An event that ends the chapter (Chapter 4's central room) is an end scene: not drawn.
- **Chapter 24's Kia room** opens only on the other army's phase (its definition checks it): on turn 5 that phase, the script picks
  one of four civilians at random (`$B9:B671`: one of the list at `$B9:B6AA`) and gives it movement AI 0x28. The Fire Emblem Wiki:
  "it can only be opened by one of the Civilians; which one can open it is determined randomly from the four boys on turn 5".
- **Capture reach** goes through what the battle's changes open (`ch.patched`), whoever sets them off, and nothing else: a door,
  drawbridge or roof no change opens stays shut.

## Events (`scripts/fe5_events.py`)

Ten long pointers per chapter at `$8C:D561`: opening, turn, talk, location, before-action, shop, battle and after-action definition
lists, the ending script and the preparations groups.

- **Definition lists**: [flag u8][script u24][conditions][FF], ended by FF FF. An entry runs when its conditions hold and its flag is
  clear, and sets the flag (flag 0 never: it runs every time). Conditions are VoltEdge's `EVENTS/Conditions.h`.
- **Scripts**: byte commands (`EVENTS/Main.h`; FC-FF end or pause a script). Command 0x08 / 0x09 is true when the value is *at least*
  the operand (`$8C:8598`), though the library calls it less-than. Most of what a script does is an ASM call (0x1B-0x1D) to the
  engine's routines in `$8C:A0xx-B7xx` (VoltEdge's `EVENTS/Values.h` names them).
- **Units**: groups of 20-byte records ended by a 0 character (layout in `fe5_events.py`); a unit appears at its start tile and walks
  to its second. Allegiance is the top 2 bits of the start x: 0 yours, 0x40 enemy, 0x80 the other army. The class comes from the
  character record (+0x2C). Bit 7 of the level byte marks a boss.
- **Preparations groups**: long pointers ended by a 0 word, each to a group after a 2-byte camera spot; placed before the opening.
- **Shops**: the definition's pointer is the shop: its tile, then up to seven u16 items. The Armory and Vendor commands are offered
  on their own tiles (terrain 26 and 27); on any other tile a shop is the Secret Shop command's, for a unit holding a Member Card
  (item 0x91; `$87:8B59`). The game has one: Chapter 24's, on a door's tile (the door opens onto floor: map change 0), shown on the
  map with a note on its door.
- **Chests** (`VANILLA_CHEST`): a tile, a u16 item and the script that gives it. Chapter 4's chests are random: what your units carry,
  laid by its opening (Map changes, above; `$8C:B9C7` gives the item of the chest opened).
- **Gaiden chapters**: each end script adds to the chapter number to skip its gaiden chapter; the condition before it is phrased in
  `GAIDEN` and tested against the script (Chapter 2: no village destroyed; 4: every civilian escapes; 12: fewer than 20 turns; 14:
  three of the city's houses visited). Chapter 15's exit picks 16A (west, or the church) or 16B.
- **Defeat**: Leif's death; Ced's in Chapter 23 (the death-quote handler, `$99:807C`); and in Chapters 9, 13, 14 and 20 an enemy
  reaching a tile (an enemy-phase event there calls the game over, `$80:C29D`).

## Capture: the foes worth capturing (`steal` on the maps)

Thracia 776 has no drops: capturing a foe takes everything it holds, weapons included. So a foe one of your units can capture is
marked with the rare things it holds (`steal`, and the map set's `takeBy: 'capture'`), in `build-fe5-maps.py`'s `Capture`.

- **The Capture command** (`$87:9B37`) is offered to a unit with a weapon it can use (`$83:965E`) that reaches 1 tile (the range's low
  nibble is 1) beside a foe (`$87:9AA3`, each tile by `$87:9AEF`; the side check `$83:B34F`) that isn't hidden
  (state 0x40), doesn't have the bit that bars capture (skills 2, 0x04, the character's or its class's: the foes Fred, Olwen, Kempf,
  Saias, Ishtar, Altena and Bharat; Ced, Arion, Hannibal and a Reinhardt record the maps never set against you have it too), and whose
  Con is below the captor's.
- **The Con compared** (`$83:A855`): a ballistician's (classes 0x3D, 0x3E, 0x61) and a mounted unit's (the Mount skill and a class in
  the table at `$88:8000`, `$83:A80F`) count as 20; anyone else's is its own plus its class's base, held at 20 (`$83:90BE`). No unit's
  goes past 20, so a mounted captor beats any foe below 20, and a foe at 20 (Raydrik, Liszt, Baldach, Seil, Nicolov, Gustav, Wolfe,
  Zaun, Mus) can't be captured. An autolevelled foe (character byte 0 with bit 7 set) rolls its own Con as it's placed (0-3, then its
  scheme's growth each level, `$83:A970`, `$83:AB5F`): it's judged by the lowest roll.
- **An immortal foe can be captured:** the defender's Immortal skill is skipped during a capture (`$83:D4AC`); that's how Veld can be.
- **A mounted foe** counts as Con 20 until it's knocked off its mount: by sleep (the outcome dispatch `$83:9C70`, outcome 6, runs
  `$83:9E39`, which gives the class its dismounted form from `$88:801C` through `$87:9560`) or by a script's Dismount (`$8C:A203`,
  `$83:AEFA`: Lemay in Chapter 8's opening; Mount, `$8C:A1FA`, puts him back on turn 16). Sleep doesn't take on a throne or gate or
  on an immortal unit (the Sleep Edge's effect `$83:E257` and the status staves' targeting `$87:B930` both check, `$83:AF2B`). So a
  mounted foe is marked only once a Sleep staff, Sleep Edge or Blizzard can be yours: from Chapter 12x (Salem, captured and held at
  Chapter 12's end, joins with his Sleep staff), and not one that stays on a throne or gate (movement AI 3 or 7). The Fire Emblem
  Wiki says the same of Eisenau and Merlock ("a mounted unit before the Sleep staff is available").
- **A foe one of your units can get beside:** walking or flying from your starting tiles (the chapter record's starting positions and
  the units the opening places on your side), one movement type at a time (the class tables' cost rows), through what the battle's
  changes open (Map changes, above); or, once a Warp or Rewarp staff can be yours (from Chapter 8: Chapter 7's end can give one), onto
  any tile beside it some unit can stand on. Unmarked for this: Veld in Chapter 5 (he and Raydrik watch the arena from a walled room) and
  Raydrik's Priest and Galzus in Chapter 6's walled north-west room.
- **A foe an event takes away once captured:** an event whose condition is the foe being held (state 0x10; a foe your unit captures
  is held, 0x800 being a unit of yours carried off, `$83:A131`) and whose script removes or hides it (state 0x440): Mareeta in
  Chapter 5.
- **A foe a talk recruits** isn't marked: its items come with it. One that joins only once captured (Salem in Chapter 12) is.
- "When one of these can be yours" counts the ways of getting it other than taking it from a foe (shops, chests, villages, gifts,
  recruits), from the chapter after the first one that gives it, on the shared story or the same route.

**What a foe carries, on the weapon page** (`foe_source`): what a foe one of your units can capture holds is a source, "capture to
take it". A foe capture can't take is robbed instead where a thief could be: a unit with Steal can be yours by then (one has joined,
or the opening places one on your side), the foe isn't a ballistician, its Spd is below 20 and a thief can get beside it, and the item
weighs less than 20 ("a thief with more than 12 Spd and 6 Con can steal it": more Spd than the foe's, more Con than the item
weighs; an autolevelled foe's Spd is rolled, so just "a thief faster than it"). Gustav's Adept Manual (Chapter 18) and Bharat's Thrud's Scroll (Chapter 20)
come only this way, as the Fire Emblem Wiki says. A thief's reach counts only the thieves among the units the opening places, and
leaves shut a door whose opening takes the foe away: Chapter 5's arena door sets flag 36, and right after the action an event hides
Mareeta (`taken_when_opened`; the wiki: her Shadow Sword is stolen only through a glitch that opens the door without her leaving).
What neither can take is said only where nothing else gives the item ('foe-held': it names who carries a foe-only weapon). Two
weapons are foe-only: the Loptrian Fang (Raydrik and Mus, at Con 20; it weighs 20) and the Shadow Sword.

**What's rare.** A weapon or staff is rare when no shop sells it (Thracia 776 has no forge); an item is rare when it lasts and no shop
keeps it in stock. The shops counted are every armory and vendor of every chapter (a shop definition whose tile is an Armory, 26, or
Vendor, 27, tile: `ordinary_stock`). Thracia 776 has no one-off offers; its one secret shop (Chapter 24's, behind a door, for Member Card
holders: Life, Speed, Skill, Strength and Shield Rings) doesn't make what it sells common. Whether an item lasts is its use effect (+0x11; `$87:AE5A` holds each one's routines): 0 has no Use command (`$87:A34D`)
and works while held (the scrolls, the Member Card); 2-18 raise a stat for good (`$87:BC53`); 20-22 promote (`$87:C09E`); 40-58 teach a
skill (`$87:BD9C`). Used up for a moment, never marked: 24-30 (the keys, the Lockpick), 32-38 (Vulnerary, Pure Water, Torch,
Antitoxin), 102 (Stamina Drink). Ballistae and broken items are left out. Thracia 776's shops never sell the Short Lance, Javelin,
Longsword, Longbow, Battle Axe, Jörmungandr and many more, so "no shop sells it" alone would mark nearly every soldier (785 foes):
a weapon or staff counts only when fewer than 15 capturable foes in the whole game hold it (`FEW_CARRY`, the user's call; the
counts break between 16, Meteor and the Devil Axe, and 12, the Master Lance), which leaves 134 foes: the Master weapons, the
Flame, Wind and Lightning Swords, the Paragon Sword, Armorslayer, Warp, Rescue, Restore, Bolting, Blizzard and the like, beside
the scrolls, manuals and the Luck Ring. A lasting item counts whatever its count.

Checked against outside sources in `src/logic/__tests__/fe5.test.ts`: every chapter's starting enemy count against the Fire Emblem
Wiki's (all match but Chapter 6, 26 against the wiki's 25, and Chapter 13, 39 against 38: the openings load exactly the groups the
wiki's rosters list), and the defeat conditions.

Not confirmed:
- Which deaths lose the game besides Leif's and Ced's (the game-over check wasn't traced past the death-quote handler).
- Steal: that the item a foe has equipped can be taken like the rest (the menu lists every item and checks only its weight; the
  take itself wasn't traced), and that an autolevelled foe's lowest Spd roll is its class's base (as for Con). A steal line says
  what it needs, not whether one of your thieves has it by that chapter (Eisenhau's Greatlance in Chapter 7 needs 19 Con).
- The staves' range: 1-10 as the item records give it (Serenes says "All"); the staff targeting code wasn't traced, but for Unlock's,
  which reaches every door, drawbridge and chest its user can see (`$87:C3E1`).
- The gaiden conditions of Chapters 8, 11, 21 and 24 are phrased from their checks and the Fire Emblem Wiki, but tested only in part.
- Map changes:
  - Where movement AI 0x28 takes the civilian Chapter 24 picks on turn 5 (the Fire Emblem Wiki: to the Kia room's door), and how its
    reaching a wall tile runs the location event there (no raze, door or chest action targets a wall).
  - Which foes raze: the raze action is the AI's action 4 (`$83:F6F6`), but which AI scripts choose it wasn't traced; the changes say
    a foe "can" raze.
  - That after-action events run after any army's units act (Chapter 6's and 17A's walls check no phase and say "a unit"; the call,
    `$83:8A6B`, wasn't traced back).
  - On fog maps, that the Unlock staff needs the tile seen (the visibility map, `$7E:8DCB`, read as the target list is made).
- Marty in Chapter 8: shown where the opening puts him when he's out of your army; what he carries is whatever he had when he left.
- Shadow Spear, Gáe Bolg, Gungnir, Bolganone, Valflame, Mjölnir, Aura and Loptous turn up in no shop, chest, gift or unit the player
  can reach (cutscene units carry some; the Fire Emblem Wiki lists Aura as unused), so they're not listed.
- Capture (the `steal` marks):
  - That a Warp or Rewarp staff can put a unit beside a foe in a walled room wherever it stands (the staves' range wasn't traced):
    from Chapter 8 such foes are marked (Chapter 11x's archers in the murder holes, Chapter 24x's Warp casters, whose chamber the
    Fire Emblem Wiki says the map's warp tiles reach).
  - That a mounted foe never dismounts on its own (the dismount on a tile the mount can't enter, `$83:AD0C`, is called only by the
    starting-position loader, `$8C:AFFB` and `$88:8517`, and a promotion, `$87:C170`): the maps count only sleep and the scripts'
    Dismount.
  - An autolevelled foe's Con is rolled as it's placed; the heaviest (Chapter 22's level-20 Armored Axes) reach 20, and then can't
    be captured, about a quarter of the time.
  - Indoors a mounted captor has to dismount, so there it takes a unit whose own Con beats the foe's; which of your units that is
    (growths, Body Rings) isn't judged.
  - Whether the capture succeeds (the foe brought to 0 HP with the captor's stats halved, or the foe unarmed) isn't judged: a mark
    means the command can be used on it.
  - Only events whose own condition is a foe being held were played for it leaving once captured (Mareeta in Chapter 5); the
    scripts that check `IsUnitHeld` (Salem, Perne, Nicolov, Misha, Lemay) recruit or talk, and take no one away.
