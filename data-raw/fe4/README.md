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
