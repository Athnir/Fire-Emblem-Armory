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
  offsets (`nso_image()`). The keys and the reader were checked against hactool: the same bytes, file for file.
- The keys are the user's own, from Lockpick_RCM on their console (`~/.switch/prod.keys`, `title.keys`): never in the repo.

## What's in the program

The Program NCA has no RomFS: everything is in `main` (`data-raw/fe1/rom/main.bin`, as it sits in memory: text 0x0, rodata 0x55000,
data 0xCA000).

- **The cartridge** (in the data segment): a record `FA5J` (the game's code; it also names the save file, `FA5J_FA5J.sram`), the
  Japanese title in Shift-JIS (ファイアーエムブレム　暗黒竜と光の剣), the emulator's settings at +0x3C (16 bytes: +3 the mapper, 0x0A =
  MMC4; +5 PRG banks of 16 KB; +6 CHR banks of 8 KB), then the cartridge whole: 256 KB of program (PRG, 16 banks, the last fixed at
  $C000, its reset vector $C075) and 128 KB of graphics (CHR), and `FA5J` again. `fe1_extract.py` writes it out as `fe1.nes` with an
  iNES header (mapper 10, battery-backed RAM) for reading and for Mesen. PRG CRC32 2078DCE4, CHR CRC32 8118B30B.
- **The English text**: the Switch side draws every line, from UTF-8 strings with placeholders ("<$DATA_NAME2> was promoted and became
  a <$DATA_OCCUPATION>.", `@` a line break).

Not confirmed:
- Whether the cartridge differs from the Famicom original (no published checksum of the original was found to compare against).
