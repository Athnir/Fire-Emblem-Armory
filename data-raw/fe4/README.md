# Genealogy of the Holy War (FE4) game files

Read from the user's own cartridge image: `Fire Emblem - Seisen no Keifu (J).smc` (SNES, Japanese, HiROM, 4 MB, no copier
header, CRC32 DC0D8CF9). The image stays on the user's PC (default path in `scripts/fe4_rom.py`, or set `FE4_ROM`) and is never
committed; only data built from it is. Read the clean file only, never a fan-translated one.

The SNES address `$XX:YYYY` is file offset `(XX & 0x3F) * 0x10000 + YYYY`. Data is little-endian. The fuller breakdown (text
encoding, classes, movement costs, what isn't found yet) is in `FE Games\notes\FE4 Genealogy - notes.md`, next to the ROM.

## Items: pointer table 0x3E9D0

One u16 per item id (0x00-0x88), an offset counted from 0x3E9D0 itself. Weapons and staves are 19 bytes:

| Offset | Field |
| --- | --- |
| +0 | Item id |
| +1 | Kind: 0 weapon, 1 staff, 2 ring |
| +2 | Uses |
| +3 | Price (u16; 65535 = not for sale) |
| +5 | Holy weapon id (0 = not a holy weapon) |
| +6 | Staff effect id |
| +7 | Rank: 0 A, 1 B, 2 C, 0xFF holy |
| +8 | Skills it grants: 0x01 Steal, 0x08 Prayer, 0x10 Critical, 0x20 Life, 0x40 Elite |
| +0xA | Type: 0 sword, 1 lance, 2 axe, 3 bow, 4 staff, 5 fire, 6 thunder, 7 wind, 8 light, 9 dark |
| +0xB | Mt (255 on Hell) |
| +0xC, +0xD | Hit, Wt |
| +0xE, +0xF | Range, min and max |
| +0x10 | Effective against: 0x01 horseback, 0x02 fliers (every bow), 0x08 armour |
| +0x11, +0x12 | Special effect and its argument: 1 casts a spell (argument is its item id), 2 drains HP and casts, 3 drains HP, 4 brave, 5 siege (long range, can't be countered, Mov drops to 0), 6 status (4 silence, 5 sleep, 6 berserk), 7 halves the foe's attack (Loputousu), 8 negates it (Narga), 9 Hell, 0x0A women only |

Rings are 10 bytes (ids 0x6A-0x79) and aren't in the weapon list.

## English names: `scripts/fe4_names.py`

Every English name is Lil' Nordion's (1.01, the translation patch Serenes Forest hosts). The patch zip sits next to the ROM
(`Documents\FE Games\Lil-Nordion 1.01.zip`, or set `FE4_PATCH`); `scripts/bps.py` applies it in memory to the clean ROM (it checks
both checksums) and only its name tables are read. Nothing patched is written or committed; every number still comes from the
clean ROM.

- The patch keeps the ROM's pointer tables and moves the strings to bank $50: items at $8D:9402 (by item id), classes at $8D:9892
  (by class id), playable characters at $8D:920D (by the character record's name index, 63 names). Text: A-Z from 0x10, a-z from
  0x2A, 0xBF space, 0x44-0x49 `. , ? ! ' -`, 0x89 á, 0x9B ó, 0x9E ö, 0xA3 ü.
- Castles: the patch's labels at $50:4A00; `PLACES` pairs each with the ROM's kana name (the ROM's own place-name list), and the
  build checks each spelling is in the patch.
- Bosses and other foes have no name table in either version. They're named from Serenes' boss and NPC tables (see Units), then
  spelt as the patch's dialogue spells them: the official name or Serenes' own where the dialogue uses it (in the patch's
  capitalisation: DiMaggio), or `BOSS_SPELLINGS` in the maps generator, each read in context ("You and Gerald are in charge") and
  checked to be in the patch. Names the dialogue never uses stay Serenes'.

## `scripts/build-fe4-items.py` -> `src/data/fe4/fe4Weapons.ts`

- Every number is the ROM's and every name the patch's. The holy weapons' stat bonuses and the staves' effects come from Serenes
  Forest (`/genealogy-of-the-holy-war/inventory/*`): the bonus table and staff effects haven't been found in the ROM. (The 16-byte
  records at 0x389E3-0x38AB0 hold each holy blood's *growth* bonuses, not the weapon's.)
- Serenes' tables are in the ROM's order, apart from the "Broken X" and "Empty Book" stubs, which the ROM keeps apart. Each row is
  matched to the next ROM item that agrees on Mt, Hit, Wt, range, rank, price and uses, in order, and the build fails if any row
  finds none. All 103 rows match; the three ROM ids it skips (85-87) are empty books.
- Left out: the broken stubs, empty books, the ballistae's arches (fixed to the map), the items Serenes lists as unused (Silence
  Sword, Charm Staff, Thief Staff) and rings.
- Not confirmed yet: whether the bows' fliers flag works as the table says (Serenes doesn't mention it), and what "effective" does
  to damage (Serenes says it counts as a critical). Both wait for the battle code to be read.

## Chapter maps: `scripts/build-fe4-maps.py` -> `src/data/fe4/fe4Maps.ts`, `fe4Terrain.ts`

The ROM keeps maps compressed with the game's own routine ($80:AA02, an LZ and run-length scheme that also unpacks graphics). It was
found by tracing a chapter load in Mesen 2 (`--testrunner` with a Lua script that presses buttons to reach the Prologue, then logs
which ROM and work-RAM addresses the load touches). `scripts/fe4_cpu.py` is a small 65816 interpreter that runs that routine on the
ROM, so the generator reads the data itself; its output was checked byte for byte against Mesen's work RAM. `scripts/fe4_asm.py`
disassembles the program code.

- **Chapter records:** twelve 3-byte pointers at $88:9FC3 (file 0x89FC3) lead to 27-byte records (Prologue, Chapters 1-10, the Final
  Chapter). A record holds: +0 the compressed map, +3 the metatile graphics, +6 the tile graphics, +21 the width and +23 the height
  (each in units of 16 tiles), +24 the compressed terrain table. Chapters 2 and 8 share Chapter 0's graphics, and the Final Chapter
  shares Chapter 5's.
- **Map:** 64 x 64 u16, one per 16 x 16 tile. The low 10 bits index a metatile; the higher bits are flags not read yet. The Prologue
  uses only its first 32 rows (the rest repeat one tile). The terrain table is one byte per metatile.
- **Terrain ids** (names from Serenes Forest's terrain page, checked against what the tiles look like in its chapter map pictures
  and against the movement table): 0 Peak, 1 Deep forest, 2 Cliff, 3 Plain, 4 Forest, 5 Sea, 6 River, 7 Mountain, 8 Desert,
  9 Castle defence, 12 Castle gate, 13 Castle wall, 14 Sand, 15 Bridge, 18 Village, 22 Church, 24 Tower, 25 Road. Ids 10, 11, 16, 17,
  19-21 and 23 are in the tables but on no map.
- **Costs:** $03:987D, 15 movement types x 26 ids (0x80 = no entry); fifteen types fall into eleven columns. Road and bridge hold 0
  for every walker, shown as Serenes' 0.7. Avoid is the signed byte at 0x39A25 + id (the notes' 0x39A21 was four bytes early).
- **Classes:** the ROM keeps each class's base stats one 31-byte slot early (class i's sit in slot i-1; the first five knights share
  theirs), so the page's class examples pair the movement type of slot i with Serenes' row i. Serenes' order is the ROM's.

Unconfirmed: the Def bonus Serenes' damage formula mentions for terrain (no table found, so the page shows Avoid only); whether
Road and Bridge cost 0.7 or 0 in the game's code; what the map's high bits mean.

## Units: `scripts/build-fe4-maps.py`

- **Unit lists:** 57 u16 offsets at $81:C000 (file 0x1C000) lead to lists of 8-byte records, each list ended by 0xFFFF:
  `[unit id u16][x][y][flag][group][army][order]`, with x counted from the left and y from the top (tile (1, 1) is the bottom left
  in the app: X = x + 1, Y = height - y). Checked: placed on the maps, 1,168 of 1,232 generic foes stand on tiles their class can
  enter, and the rest are bosses on the Castle defence tile and ballistae.
- **Which chapter a list belongs to:** each chapter's opening loads its first lists (`4A nn` in the opening script, or in a scene
  it runs). The build reads them from the scripts and checks them against what the game was seen loading (`OPENING_LISTS`, from
  `python scripts/fe4_mesen.py lists 0 11`, which forces each chapter through the chapter number at $7E:0D6A). A chapter owns its
  opening lists and every list up to the next chapter's first; the others arrive later (see Events).
- **Chapter scripts:** every chapter has an 8-byte header `[chapter u16][opening script][event table]` (3-byte pointers; the opening
  script follows the header; found by scanning for that shape). `scripts/fe4_cpu.py` can step through a script with the interpreter's
  own skip entry ($86:83F0), which every command handler answers by moving past its operands. The opening script's
  `4b army x` commands name the armies and `4d relation army other` set how they stand: relation 1 is hostile to your army (army 0),
  2 friendly, 3 neutral. A unit's army is its record's byte 6.
- **The unit id** indexes the character table (u16 count*2 at 0x3AE00-ish: `0x38000 + [0x38002]`, then u16 offsets from there, id 1 upward).
  Four kinds, by their first byte: 3 is a generic foe (13 bytes: id, previous id, class at +5, level at +7, three item ids at +10),
  0 and 2 are named characters (38 bytes: class at +9, level at +10; 0 are the ones you recruit, 2 the named foes and NPCs), 1 is
  a 12-byte record used twice. Item ids are the weapon table's.
- **Names:** playable characters (kind 0, and kind 1: the second generation's children, name index at +5) by the patch's name
  table. A foe is named from Serenes Forest's boss and NPC tables when its class and level match a row and the unit is a leader
  (flag 1, 254 or 255) or a named record; where more units fit than names, only flagged leaders take the name. Everyone else is
  their class. The match uses Serenes' class names (kept from its class table); the page shows the patch's.
- **Not read yet:** your own army's placements (army 0; the page shows the home castle as the lord's start), and the named
  characters' items and holy blood. Serenes lists two Level 20 Axe Fighters for the Prologue while the game also has a Level 20
  Warrior in Evans, so the one named Gerald may be the other.

## Events: `scripts/fe4_events.py`, used by `scripts/build-fe4-maps.py`

- **Chapter header:** `[chapter u16][opening script][event table]` (3-byte pointers), found by its self-reference.
- **Event table:** commands of the event interpreter ($86:83D8). First, pairs of `[condition][action]` up to `20 66 66`. A condition
  is `[opcode][flag][args]`; each opcode stands for a trigger kind the game raises with its values ($0EBC, then $0EBD-$0EC3; found at
  each `STA $0EBC`): 0x02 an army seizes a castle (army, location), 0x04 / 0x15 / 0x16 a talk (from, to; 0xFFFF anyone), 0x07 a unit
  enters a castle (unit, location), 0x0A a unit visits a village or castle, 0x0B a unit reaches an area (unit, x1 y1 x2 y2), 0x0D a
  battle between two units, 0x0F a unit is defeated. The flag byte: 0xFF none; below 0x80 the entry fires once and sets that flag;
  0x80 + n needs flag n. Once one entry fires the rest are skipped.
- **Blocks** after `20 66 66`: `21 turn phase a b` (0xFF any; the phase is an army's number) opens a block closed by `25 66 66`;
  `29 n` (flag set), `2A n` (clear), `2C ... FF` (all set), `2D ... FF` (any set) open one closed by `2E 66 66`; `27 n` sets a flag.
- **Actions:** `30 [flag] [u16 n]` runs scene n (3-byte pointers at $8F:E8BF, 562 scenes); `31` / `32` show text.
- **Scenes** run on their own interpreter ($91:A5E2, handlers at $91:A50A). `FD` ends a step, `FFFF` the scene; 0x01 ends, 0x02
  jumps, 0x03-0x06 jump conditionally, 0x4B sets a flag (`4B 01 n`). Scene opcodes 0x4A and 0x4D run one event command inline:
  `4A nn` loads unit list nn, `49 id` puts a unit on the map, `53 id army` moves a unit to an army (army 0: it joins you),
  `57` / `58 [unit] [instance]` hands over an item. Command lengths come from running each handler on `scripts/fe4_cpu.py`
  (calls into other banks stepped over, the four move slots at $7E:17C4 read as free); the walk follows jumps. Every scene the
  tables use walks to its end. Two event commands step past fewer bytes in their skip entry than when run (0x34; 0x5F when its
  fifth operand byte is 0x0B), which the walker corrects.
- **Item instances:** the game tracks every physical item; scripts hand out instance numbers, counted from 1, whose item type is
  the byte at 0x3F489 + n - 1 (140 of them). Checked against Serenes' item-locations page: the Prologue's village gives the Speed
  Ring, Chapter 2's the Bargain Ring and Armour Cutter (the patch's Bargain Bracelet and Ironbane Sword).
- **Locations:** each chapter's data (3-byte pointers at $86:C760) leads to its castles and villages: `[id][name][kind][x][y]`, kind
  0 a castle (on the castle tile; location 0 is your home castle), 2 a village. A village holds 5000 gold (the per-kind record at
  $87:F453, which also gives the footprint a visit checks: x - 1 to x + 1 and the row above).
- **What the page says:** each later group's arrival (the block or trigger whose scene loads it, its flags traced back to what sets
  them: a seize, a talk, a defeat, another group's arrival); the castle whose seizing runs the chapter's ending scene (event command
  0x78) as the win; castles, villages and their items; hidden finds (area triggers that hand over an item); talks that give items or
  recruit; who joins and when (`49` in turn blocks).
- **Lose conditions** (the lord defeated, or the home castle seized) are Serenes' (its introduction page); the game over isn't read
  in the code yet.
- A trigger's action can set a flag itself (`27 n`): Chapter 5's ambush waits on Sigurd talking to Ida. Unit list 40 (Asaello
  alone, in Chapter 8's range) is loaded by no script or scene, so it's left out as leftover data.
- **Where units are put:** scene op 0x24 walks a unit `[unit u16][00][x1][y1][x2][y2]...`; the inline event command 0x50 sets its
  tile `[unit u16][FF][x][y]` ((0, 0): none given); a unit in a list loaded with the scene on your side (army 0) stands where its
  record says. Joiners are the playable units a block's scene puts on the map (event command 0x49), walking in from where 0x24
  starts them; the starting units are those the opening places (the rest start in the home castle). A substitute and the child it
  stands in for share a tile and an entry ("Deimne / Lester"). The second generation's openings also move Sigurd's id, which is
  left out from Chapter 6 on.
- **Not read yet:** the arena.

## True hit

One roll, read in the game's code: the hit routine ($84:E564) takes the attacker's accuracy less the defender's avoid (less Prayer's
bonus when the defender has the skill and 10 HP or less: 10 x (11 - HP), as Serenes' skills page says), clamps it to 0-100 and calls
$84:EF9C once, which draws one number 0-99 from the random table ($80:A73A) and hits when it's lower. Skill activations use the same
roll. So the displayed hit is the true hit (`hitSystem: '1rn'`).

## Supports: `scripts/build-fe4-bonuses.py` -> `src/data/fe4/fe4Bonuses.ts`

The game has no support levels. The Supports tab shows what stands in for them, read from the battle code (addresses in the script):
units of the same army within 3 tiles give +10 hit and avoid for each one with Charisma (skill 0x0C: Lachesis, its only holder in
Serenes' base-stats page, has that bit alone at +0x1C of her record), +10 for a lover, and the commander's leadership by stars
(0, 0, 10, 20, 30, 40); the lord gets their own. The weapon triangle gives the advantaged side +20 hit and avoid. Accuracy itself is
weapon Hit + 2 x Skl; avoid is terrain + Luck + 2 x attack speed ($84:FD00, $84:FD4C). Not read yet: the critical bonuses Serenes
lists for an adjacent lover or sibling (+20 crit).

## Where items turn up: `src/data/fe4/fe4ItemSources.ts` (from `scripts/build-fe4-maps.py`)

Each item's sources by chapter, for the weapon page and the spoiler block (a weapon is listed from the first chapter it turns up in):
- **Shop:** the home castle's location record ends in a pointer to its stock, item instances up to 0xFF (`shop_stock`). Checked
  against every "Vendor" entry on Serenes' item-locations page. Chapters 0, 5 and 11 have none.
- **Drops:** a foe's record holds two carried item *types* and one dropped item *instance*: at +10 in a generic record (kind 3),
  at +0x23 in a named one (kind 2). Every drop matches Serenes' list (Philip's Return Ring, Jacoban's Thunder Sword, Hilda's
  Bolganone, Ishtar's Life Ring...). A drop from a foe that arrives mid-chapter counts from the next chapter.
- **Visits, castles, hidden finds, talks:** the scenes behind the event triggers (`57` / `58` hand an instance to a unit).
- **Kit:** what a playable unit carries when the scripts bring it in (event command `49` or `53 ... 00`): item instances at +0x23
  in a first-generation record (kind 0), +9 in a child's (kind 1). Inherited items aren't modelled: a child's own record is used.
- Not read: the arena's prizes, and whether the pawn shop or inheritance adds sources. Seven weapons have no source read
  (Gungnir, Valflame, Meteor, Blizzard, Hel, Loptous, the Berserk Staff), so the spoiler block never lists them.
