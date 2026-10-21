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

## Weapons (`ItemData`, `scripts/build-fe10-items.py`)

- Records are variable-length: 0 `IID_`, 4 `MIID_` (name), 8 `MH_I_` (description), 12 and 16 weapon
  type (`sword`, `lance`, `axe`, `bow`, `ballista` = crossbow, `knife`, `flame`, `thunder`, `wind`,
  `light`, `dark`, `rod`, `blow` = laguz strike, `item`), 20 rank (`E`-`S`, `*` = SS, `N` = none needed),
  24-32 effect IDs; 0x24 u16 index, 0x26 u16 price per use, 0x28 Mt, Hit, Crit, Wt, uses, weapon EXP, range
  min, range max (255 = Mag/2); 0x35 the number of attribute strings, 0x36 the number of effectiveness
  targets (`SFXC_`), 0x37 whether a 12-byte stat block follows (HP, Str, Mag, Skl, Spd, Lck, Def, Res, Mov,
  ...; on staves it means something else). The lists start at 0x38.
- Personal weapons are `eqA`-`eqI`; who wields each is whoever has the matching `SID_EQ_` skill in
  `PersonData` (A Ike, B Mist, C Elincia and Renning, D Micaiah, E Sanaki, F Sephiran/Lehran, G Edward,
  H Leonardo, I Nolan). `SID_EQBALLISTA` (Warrior, Reaver, Sniper, Marksman) is what lets a class use
  crossbows, and `SID_EXPANDRANGEO_1` (Marksman only) the +1 range on `expandrange` bows.
- In `main.dol`, the attack routine `0x8002f220` builds attack as the weapon's Mt plus a modifier,
  tripled when the unit's effective flag is set (`0x8002f37c`: x << 2, minus x), then adds Str or Mag,
  except for a `stone` weapon (the Onager) or a crossbow (type 13). An item's rule flags are bits in two
  words at its +0x38 at runtime; `sealcrit` (bit 16) is tested against the attacker's crit.
- Brave weapons strike twice on both phases (the Fire Emblem Wiki: attack-only came with Fates). Sell price
  is half the price of the uses left, as in Path of Radiance.
- Shops: `WSHOP_ITEMS_Cppnn` and `ISHOP_ITEMS_Cppnn` list `(IID, flag)` pairs for the base before
  chapter `MCTppnn`; a non-zero flag is a one-off bargain (Serenes Forest's Bargains lists match). The
  forge (`FSHOP_ITEMS_Cppnn`) lists weapon types and materials (`MIK_SW`, `MDV_IRN`) rather than items.

## The forge

- `FSHOP_ITEMS_Cppnn` is a grid of `(weapon type, material, IID or 0)` triples (`MIK_SW`, `MDV_IRN`,
  `IID_IRONSWORD`): the base weapons that base's forge offers.
- Limits (the forge screen, `main.dol` 0x80219d48 onward): Mt and Wt change by 1 a step, Hit by 5, Crit by
  3, at most 5 steps up or down. A stat can only be lowered while it's above 1, and the forged stat
  getters (0x80110da8-0x80110eb0) keep Mt, Hit and Wt at 1 or more and Crit at 0 or more.
- Cost (0x80112364, called from 0x8022fe80): the base price plus, for each stat,
  `trunc(float(steps²) × (0.1f × price))` in single precision (Hit's steps are its change ÷ 5, Crit's ÷ 3).
  Serenes Forest's example comes out the same: a Silver Sword at +5 Mt, +15 Crit, −2 Wt is 11,520G.
- `FSHOP_CARD_DATA`: a count, then `(name label, bonus, odds)` for each card a Coin can draw. The bonus
  bytes are Mt, Hit, Crit and extra Coins; the odds word's top byte is the chance in %.
