# Fire Emblem: Shadow Dragon and the Blade of Light (FE1) game files

Read from the user's own dump of the Switch release (2020), the Famicom original of 1990 with Nintendo's English translation:
`Fire Emblem_ Shadow Dragon and the Blade of Light [0100A12011CC8000][v0][BASE].nsp` in `Documents\FE Games\Switch dumps\NSP`, dumped
from the console with nxdumptool. The game has no update or DLC. `scripts/fe1_extract.py` writes what the Armory reads into
`data-raw/fe1/rom/` (git-ignored, never committed); only data built from it is in the repo.

## The package (`scripts/switch_nsp.py`)

- **NSP**: a PFS0 (the package) holding the game's NCAs (Program, Control, Manual, Meta), its ticket and certificate.
- **NCA**: the first 0xC00 bytes are AES-XTS with the console's `header_key` (Nintendo's tweak: the 0x200-byte sector number,
  big-endian). The content key is the title key (`~/.switch/title.keys`, by the header's rights id, decrypted with `titlekek_<master
  key revision>`) for a digital game, else the NCA's own key area (decrypted with `key_area_key_<application|ocean|system>_<revision>`,
  the third key). Sections (start/end in 0x200 units at +0x240) are AES-CTR: the counter's upper 8 bytes are the section header's
  +0x140 reversed, the lower 8 the offset / 16, big-endian. A PFS0 section's data starts past its hash table (header +0x40); a
  RomFS's files are its last IVFC level.
- **NSO** (the ExeFS's `main`, `sdk`, `subsdk0`): text, rodata and data segments, each LZ4 when its flag says so, placed at their memory
  offsets, and its relative relocations (R_AARCH64_RELATIVE, from the MOD0 header's dynamic section) applied as if loaded at 0, so a
  pointer in its data is the offset of what it points at (`nso_image()`). The keys and the reader were checked against hactool: the
  same bytes, file for file.
- The keys are the user's own, from Lockpick_RCM on their console (`~/.switch/prod.keys`, `title.keys`): never in the repo.

## What's in the program

The Program NCA has no RomFS: everything is in `main` (`data-raw/fe1/rom/main.bin`, as it sits in memory: text 0x0, rodata 0x55000,
data 0xCA000; `subsdk0` is the graphics driver).

- **The cartridge** (in the data segment): a record `FA5J` (the game's code; it also names the save file, `FA5J_FA5J.sram`), the
  Japanese title in Shift-JIS (ファイアーエムブレム　暗黒竜と光の剣), the emulator's settings at +0x3C (16 bytes: +3 the mapper, 0x0A =
  MMC4; +5 PRG banks of 16 KB; +6 CHR banks of 8 KB), then the cartridge whole: 256 KB of program (PRG, 16 banks, the last fixed at
  $C000, its reset vector $C075) and 128 KB of graphics (CHR), and `FA5J` again. `fe1_extract.py` writes it out as `fe1.nes` with an
  iNES header (mapper 10, battery-backed RAM) for reading and for Mesen. PRG CRC32 2078DCE4, CHR CRC32 8118B30B. It runs as it is in
  Mesen 2, in Japanese.
- **The English text** (`scripts/fe1_names.py`): the cartridge still draws its Japanese; the Switch side recognises each string as the
  NES draws it and draws its English over it. Two tables do that:
  - the dictionary (252 entries of 32 bytes: {length, pointer to the key in the NES's encoding, the Japanese in UTF-8, text number});
    a key is the string's first `length` codes as drawn on the line, without the voicing marks (0x0F ゛, 0x1F ゜) that go on the line
    above. Item names are keyed whole (てつのつるぎ), class names by their first three codes (ソシアル ナイト);
  - the English (294 entries of 16 bytes: {u32 text number, u64 pointer to the UTF-8}): people, armies, classes, items, terrain,
    places, menu words. Lines are templates ("<$DATA_NAME2> was promoted and became a <$DATA_OCCUPATION>.", `@` a line break), their
    values taken from the NES's memory as it runs.
  A name is looked up by the longest key it starts with. The NES's text codes: hiragana 0x00-0x2F and katakana 0x30-0x5F in 五十音
  order (0x0F ゛, 0x1F ゜, 0x3F ー), small kana and kanji tiles above that, 0xEF ends a string.

## The cartridge (`scripts/fe1_rom.py`)

MMC4: bank n at $8000-$BFFF, bank 15 fixed at $C000-$FFFF. Addresses below are bank:$addr.

- **Names** (u16 pointers to strings, bank 15): items at $DAD5 (by item number), classes at $DA1F (class − 1), your characters at
  $DE2B (character − 1), foes at $DFA4 (character & 0x7F − 1: a boss's name, or a generic foe's army), terrain at $E5F1 (16 types:
  Grassland, Pillar, Forest, Desert, Mountain, Bridge, Village, Fortress, Castle, River, Sky, Sea, Floor, Stairs, Arena, Wall).
  82 of the 92 items have English; the others are the dragons' forms (no stats), two orbs, a telescope and the Fire Emblem itself.
- **Items** (bank 15, an array of 92 per field, by item number): Mt $D657, weapon level $D6B3 (bit 7: a lock), Wt $D70F, Hit $D76B,
  Crit $D7C7, price in tens $D823, uses $D87F (255: never breaks), effectiveness $D8DB (an index into the u16 pointers at $D937 to
  lists of class numbers ended by FF; 0 none).
- **Units in memory** (27 bytes; your army in battery RAM from $6A90, the foes from $7078): +0 character (foes: 0x80 + the foe name
  number), +1 class, +2 level, +3 max HP, +4 HP, +5 EXP (a foe: what it's worth), +6 status, +7 Str, +8 Skill, +9 weapon level,
  +10 Spd, +11 Luck, +12 Def, +13 Move, +15 Res, +16 row, +17 column (from the top left), +19..+22 items (item number + 1, 0 none),
  +23..+26 their uses (a foe's +22..+26: its AI). +15 is Res (its bit 7 a flag).
- **Your units each chapter brings** (bank 8, u16 pointers at $8490 by chapter − 1): lists of whole 27-byte records ended by a 0
  character. Chapter 1's is the starting army.
- **Foes** (bank 8, u16 pointers at $8AA3 by chapter − 1; the chapter number is $7674): 11-byte records ended by a 0 character:
  [character][class][level][item][item][row][column][AI ×4]. The loader ($BB85) builds each record from its class's base stats
  (u16 pointers at $EC04 by class − 1: Str, Skill, weapon level, Spd, Luck, Def, Move, HP, EXP): every stat but Luck and Move gains
  (level − 1) / 2, HP three times that, EXP the level − 1; the chapter's first foe (its boss) is worth 10 more.
- **Maps** (15:$D385): chapters 1-13 in bank 2, 14-25 in bank 9 (chapter − 13), each by the u16 pointers at that bank's $8000.
  Uncompressed: [last row][last column][2 bytes] then each row's graphic tiles. Loaded into battery RAM from $72AF, 32 to a row (row
  pointers at 15:$ED3D); a unit stands on its tile as a marker (class × 2, | 1 for a foe) and keeps the tile under it in its +6.
- **Terrain** (bank 15): a graphic tile's terrain code is the table at $E828 (codes 0-21; 14 and 31 mark units). By code: the avoid
  bonus $EBD8 (22 bytes), the battle's terrain name $EBEE (22 bytes, into the 16 names), the movement costs per class (u16 pointers
  at $E9C8 by class − 1, 22 bytes each, 255 can't enter; the dragons, classes 23 and 24, have none). The battle (6:$ADAF) takes the
  defender's tile under it (+6) through $E828, then $EBD8 and $EBEE; a Pegasus Knight or Dracoknight (classes 3, 5) always counts as
  code 13 (Sky: no bonus). No terrain gives Def.
- **The battle block** (6:$AD8B; $0304 + 2 × field + side): the unit's +0..+12 (character, class, level, max HP, HP, EXP, tile, Str,
  Skill, weapon level, Spd, Luck, Def), $0310 the terrain's avoid bonus, $0320 the item, $0322 the terrain name, $0326 Res (+15 &
  0x7F). Seen in a battle in Mesen: Cain on Grassland (avoid 5) against a Pirate in the Sea (avoid 30).

Not confirmed:
- Whether the cartridge differs from the Famicom original (no published checksum of the original was found to compare against).
