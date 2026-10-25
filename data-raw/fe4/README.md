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

## `scripts/build-fe4-items.py` -> `src/data/fe4/fe4Weapons.ts`

- Every number is the ROM's. The English names, the holy weapons' stat bonuses and the staves' effects come from Serenes Forest
  (`/genealogy-of-the-holy-war/inventory/*`): the item names in the ROM are Japanese with kanji pages we don't read yet, and the
  bonus table and staff effects haven't been found in the ROM. (The 16-byte records at 0x389E3-0x38AB0 hold each holy blood's
  *growth* bonuses, not the weapon's.)
- Serenes' tables are in the ROM's order, apart from the "Broken X" and "Empty Book" stubs, which the ROM keeps apart. Each row is
  matched to the next ROM item that agrees on Mt, Hit, Wt, range, rank, price and uses, in order, and the build fails if any row
  finds none. All 103 rows match; the three ROM ids it skips (85-87) are empty books.
- Left out: the broken stubs, empty books, the ballistae's arches (fixed to the map), the items Serenes lists as unused (Silence
  Sword, Charm Staff, Thief Staff) and rings.
- Not confirmed yet: whether the bows' fliers flag works as the table says (Serenes doesn't mention it), and what "effective" does
  to damage (Serenes says it counts as a critical). Both wait for the battle code to be read.
- Where each weapon turns up (shops, chests, drops) waits for the maps, which the ROM keeps compressed.

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
- **Not yet:** units, villages' and castles' rewards, shops, and events; each map's win and lose rules.

Unconfirmed: the Def bonus Serenes' damage formula mentions for terrain (no table found, so the page shows Avoid only); whether
Road and Bridge cost 0.7 or 0 in the game's code; what the map's high bits mean.
