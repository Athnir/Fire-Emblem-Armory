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

- Items: u16 pointers at `$B0:8FC3` (bank `$B0`); classes `$89:8000` (bank `$89`, ids 1-0x77); characters `$86:DA4D` (bank `$86`, ids
  0-0x156).
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
- **Stealing** (`$87:B517`, `$83:9745`): an item is stealable when its weight is below the thief's Con.

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
- **Shops**: the definition's pointer is the shop: its tile, then up to seven u16 items. Armory, vendor or secret shop by the tile's
  terrain; the secret shop needs a Member Card.
- **Chests** (`VANILLA_CHEST`): a tile, a u16 item and the script that gives it. Some chests are random: their item is one the map's
  units carry (`$8C:B9C7`).
- **Gaiden chapters**: each end script adds to the chapter number to skip its gaiden chapter; the condition before it is phrased in
  `GAIDEN` and tested against the script (Chapter 2: no village destroyed; 4: every civilian escapes; 12: fewer than 20 turns; 14:
  three of the city's houses visited). Chapter 15's exit picks 16A (west, or the church) or 16B.
- **Defeat**: Leif's death; Ced's in Chapter 23 (the death-quote handler, `$99:807C`); and in Chapters 9, 13, 14 and 20 an enemy
  reaching a tile (an enemy-phase event there calls the game over, `$80:C29D`).

Checked against outside sources in `src/logic/__tests__/fe5.test.ts`: every chapter's starting enemy count against the Fire Emblem
Wiki's (all match but Chapter 6, 26 against the wiki's 25, and Chapter 13, 39 against 38: the openings load exactly the groups the
wiki's rosters list), and the defeat conditions.

Not confirmed:
- Which deaths lose the game besides Leif's and Ced's (the game-over check wasn't traced past the death-quote handler).
- That a thief also needs more Speed than the target to steal (the Fire Emblem Wiki says so; only the Con check was read).
- The staves' range: 1-10 as the item records give it (Serenes says "All"); the staff targeting code wasn't traced.
- The gaiden conditions of Chapters 8, 11, 21 and 24 are phrased from their checks and the Fire Emblem Wiki, but tested only in part.
- Villages the brigands destroy, and other map changes by tile-change id, aren't drawn yet.
- Marty in Chapter 8: shown where the opening puts him when he's out of your army; what he carries is whatever he had when he left.
- Shadow Spear, Gáe Bolg, Gungnir, Bolganone, Valflame, Mjölnir, Aura and Loptous turn up in no shop, chest, gift or unit the player
  can reach (cutscene units carry some; the Fire Emblem Wiki lists Aura as unused), so they're not listed.
