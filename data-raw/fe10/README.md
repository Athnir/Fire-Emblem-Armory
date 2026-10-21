# Radiant Dawn (FE10) game files

Extracted from the user's own disc with Dolphin (Properties > Filesystem > Extract Entire Disc). It's a
Wii disc, so the dump has a `DATA` partition (the game) and an `UPDATE` one (system update, unused).
The files stay on the user's PC and are never committed; only data built from them is.

Wii files are big-endian, like the GameCube's.

- `DATA/files/FE10Data.cms` is the main data, LZ10-compressed (`scripts/fe9_files.lz10` reads it) into
  the same pointer-relocated layout as Path of Radiance's `FE8Data.bin`: header `size, data size,
  pointer count, name count`, data at 0x20, then the pointer offsets, then `(data offset, name offset)`
  pairs naming the tables. Tables include `ItemData`, `JobData`, `PersonData`, `SkillData`,
  `TerrainData`, `ChapterData`, `3SukumiData` (weapon triangle), `RelianceData` (who can support whom),
  `RelianceParam`, `KiznaData` (bonds), `BioData` and `DivineData`.
- `RelianceParam` (16 bytes): `32 64 96 97` the support points each level needs in total (C 50, B 100,
  A 150); `0f 1e 03 05 04 01 02` points per action for a middling pair (15 for being deployed together,
  3 for starting a turn adjacent, 5 for carrying, 4 for a staff or Sacrifice, 1 for a shove; 30 and 2
  not yet placed); `02 01 00 ff fe` how much more or less each of the five kinds of pair gets.
- The affinity bonuses aren't stored as a table (the code works them out); they're the Fire Emblem
  Wiki's and Serenes Forest's, which agree.

## The hit roll (`DATA/sys/main.dol`)

- The random numbers are the GBA games' generator: three 16-bit words at r13-0x6a70. `0x80089c88`
  returns `(n x next) >> 16`; `0x80089d68` draws one number 0-99 and checks it against a chance;
  `0x80089de8` draws two and checks their average, rounded down.
- The attack routine `0x8002ff14` returns 0x6e (hit), 0x6f (critical) or 0x70 (miss). Past a few forced
  outcomes, it rolls hit (unit +0x452) with the two-number check and crit (+0x458) with the one-number
  one: 2RN hit, 1RN crit. Path of Radiance's is the same (`0x801a8a28`, helpers `0x8000cd88` and
  `0x8000ce68`).
