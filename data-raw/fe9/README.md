# Path of Radiance (FE9) game files

Extracted from the user's own disc (NA, GFEE01) with Dolphin: right-click the game, Properties >
Filesystem > Extract Entire Disc. The files stay on the user's PC (default path in
`scripts/fe9_files.py`, or set `FE9_FILES`) and are never committed; only data built from them is.

GameCube files are big-endian.

- `Mess/*.m` (text): header `size, data size, 0, count`; text at 0x20; then `count` pairs of
  `(text offset, label offset)`; then the labels (`MIID_IRONSWORD` -> "Iron Sword").
- `FE8Data.bin` (main data): data at 0x20, pointers are offsets from there. Items are 96-byte records:
  - 0 `IID_`, 4 `MIID_` (name label), 8 `MH_I_` (description label), 12 weapon type
    (`sword`, `rod`, `flame`...), 20 rank (`E`-`S`, `N` = one character only);
  - 24-44 rule flags (`twice`, `poison`, `crit0`, `infinity`, `sealcrit`, `heroonly`...),
    48-52 effectiveness (`fly`, `armor`, `knight`, `beast`, `dragon`, `alize`), 56 effect id
    (`EID_LIGHT...` marks a light tome; staves share the `rod` type);
  - 64 price per use (u16), 66 uses, 67 Mt, 68 Hit, 69 Wt, 70 Crit, 71-72 range (255 = Mag/2),
    74 weapon EXP, 75-82 stat bonuses (HP, Str, Mag, Skl, Spd, Lck, Def, Res).

Generator: `scripts/build-fe9-items.py` writes `src/data/fe9/fe9Weapons.ts`. It was checked against
Serenes Forest's FE9 weapon tables; where they differ (Venin Lance's rank, Rescue's weapon EXP) the
game data wins.
