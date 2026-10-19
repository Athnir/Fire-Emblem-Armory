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

## The forge

- `shop/shopitem_{n,h,m}.bin` (Easy/Normal, Hard, and the Japanese release's Maniac): a block of words
  at 0x20 (header `size, data size, pointer count, name count`), then the offsets of the words that are
  pointers, then `(data offset, name offset)` pairs naming each table, then the names. `WSHOP_ITEMS_Cnn`
  and `ISHOP_ITEMS_Cnn` are the base's weapon and item shops, `FSHOP_ITEMS_Cnn` the forge's base weapons
  as `(IID or 0, material)` pairs. `nn` is the chapter's file number (`MCTnn` in `common.m`: 09 is
  Ch.8, 29 is Ch.27-2, 31 the Endgame). A chapter with empty shops has no base (Ch.27-2).
- The price is in the program, not the data: `sys/main.dol`, function 0x8001c284. It takes the base
  item, its uses and the steps forged (Mt +1, Hit +5, Crit +3, Wt -1 each) and works on a value per
  stat: Mt, Hit, Crit + 10, and 23 - Wt. Each forged stat adds
  `uses x price per use x |new value^2 - old value^2| / old value^2`; the sum is multiplied by 2.5 and
  truncated (single-precision floats). The caller (0x801b15f4) adds the base weapon's price.
- The limits (Mt +5, Hit +25, Crit +9, Wt -5 but not below 1) are from Serenes Forest's forging page.
  Its costs match the formula except two Wt entries one digit off (Slim Lance 855G, Iron Axe 614G;
  the formula gives 885G and 619G).

`scripts/build-fe9-items.py` adds each base weapon's forge chapters; `src/logic/fe9Forge.ts` does the price.
