# The Binding Blade (FE6) game files

Read from the user's own cartridge image: `Fire Emblem - Fuuin no Tsurugi (J) [!].gba` (GBA, Japanese, game code AFEJ, 8 MB,
CRC32 D38763E1). The image stays on the user's PC (default path in `scripts/fe6_rom.py`, or set `FE6_ROM`) and is never committed;
only data built from it is. Read the clean file only, never a fan-translated one.

Offsets are file offsets; the game addresses them as 0x08000000 + offset. Data is little-endian. The program code was compiled
without optimisation and reads easily as Thumb (capstone). The fuller breakdown is in `FE Games\notes\FE6 Binding Blade - notes.md`,
next to the ROM.

## English names: `scripts/fe6_names.py`

Every English name is the FE6 Localization patch's (v1.2.1, the translation Serenes Forest hosts; `FE6Localization_v1.2.1.ups`
next to the ROM, or set `FE6_PATCH`). `scripts/ups.py` applies it in memory to the clean ROM (it checks all three checksums) and
only its text is read, by the ROM's own text ids. Nothing patched is written or committed; every number still comes from the clean
ROM.

- The patch's text table is at the pointer in 0x013B10 (0x833530). Entries are Huffman-compressed with the ROM's tree layout
  (nodes at 0x0F300C, root pointer at 0x0F6358); bit 31 of an entry means it's stored plain.
- Letters are drawn from the 0x82 page of the system font (glyphs at 0x59027C, indexed by the second byte minus 0x40): A = 0x82A0,
  a = 0x82D0 and so on, read off the glyphs into `CHARS`. A code it doesn't know raises.
- Item names are sentence-case ("Iron sword") and some class names are abbreviated ("Nmd Trooper", "Falcoknight", "Demon Drgn"),
  as the patch has them. The female versions of classes 3, 33, 35 and 64 and items 79, 85 and 102 have no name in the patch.
- Character names are keyed by the record's own id (+4): the table starts at id 1 (Roy). A foe version of a character (ゴンザレスＢ)
  is its own record with the same name.
- Chapter titles are drawn as images, not text, so the story chapters' titles are Serenes Forest's (its translation script page).
  The trial maps' are the patch's. Affinity names (Fire, Thunder, Wind, Ice, Dark, Light, Anima) are the later games' and
  Serenes': the game shows only icons.

## Items: 0x60B648, 32 bytes each (`scripts/build-fe6-items.py` -> `src/data/fe6/fe6Weapons.ts`)

| Offset | Field |
| --- | --- |
| +0, +2 | Name and description text ids |
| +7 | Type: 0 sword, 1 lance, 2 axe, 3 bow, 4 staff, 5 anima, 6 light, 7 dark, 9 item, 0xB dragonstone |
| +8 | Attributes (u32): 0x02 magic, 0x08 unbreakable, 0x20 brave, 0x40 magic at range (Light Brand), 0x80 can't be countered (ballistae), 0x100 reaver (read in the battle code at 0x08025A90), 0x400 / 0x800 / 0x1000 / 0x2000 locks (Manaketes, Roy, Myrmidons and Swordmasters, Zephiel) |
| +0xC | Stat bonuses: signed bytes HP, Str, Skl, Spd, Def, Res, Lck, Mov, Con |
| +0x10 | Effective against: class ids ending in 0 |
| +0x14-+0x18 | Uses, Mt (255 on Eclipse: its effect sets the damage), Hit, Wt, Crit |
| +0x19 | Range: min in the high nibble, max in the low (max 0: 1 to Mag/2) |
| +0x1A | Cost per use; price = uses × cost |
| +0x1C | Rank: E 1, D 51, C 101, B 151, A 201, S 251; 0 is a personal weapon |
| +0x1F | Weapon effect: 1 poison, 2 drains HP, 3 leaves 1 HP, 4 Devil axe (hurts the wielder at 21 − Luck %) |

- Effective Mt is tripled (the attack routine, 0x0802489C). Staves' effect lines are the patch's descriptions.
- Left out: the ballistae (bows with 0x80, fixed to their tiles) and items the patch leaves unnamed. The weapon page also leaves out
  weapons nothing in the game hands out or carries (Poison lance, Poison bow, Fortify: `src/data/fe6/fe6Listed.ts`), and marks the
  ones only foes carry: thieves can't steal weapons and foes drop nothing.
- Not confirmed: the attribute bits read off the items that carry them (only the reaver bit was traced in code). The Poison bow
  has no poison effect in the table.

## Terrain

- 51 terrain ids; names at 0x60D00C (plain strings). Each class (72-byte records at 0x60A0E8) points at its movement cost row
  (+0x34; 255 = can't enter) and its avoid, Def and Res rows (+0x38, +0x3C, +0x40). Every ground class shares the rows at 0x60C978
  (avoid), 0x60C9AB (Def) and 0x60C9DE (Res); fliers' avoid and Def rows (0x60CA11, 0x60CA44) are all 0 and their Res row is the
  ground's. Healing per turn: 0x60CBA9 (Fort 20 %, Gate, Throne and Church 10 %).
- Classes are grouped into the 14 movement types whose cost rows differ (`MOVE_GROUPS` in the maps generator; the build fails if
  a class has a row no group has).
- Codes (`scripts/terrain_codes.py`, `GAME['fe6']`): road, floor and glacier work as plain ground; the village walls work as cliffs
  (fliers only); a tile only fliers enter shows Def and Avoid 0, which is what fliers get. New codes: `bu` Peak (brigands and
  berserkers climb it), `wn` Valley (Chapter 8x: fliers and dragons only), `om` Armory, `on` Vendor, `oo` Arena.
- Not used: each class's fifth row (+0x44: Brigand +5 on mountains and peaks, Pirate on water, Berserker both, Priest on churches,
  the King on gates and thrones). No code that reads it was found, so it isn't shown.

## Chapters: 0x6637A0, 68 bytes each (`scripts/build-fe6-maps.py`)

- +8 to +0xF are indices into the pointer table at 0x664398 (the map at +0xC, the tile config at +0xB); +0x10 the fog vision (0 =
  no fog); +0x11 how many units you deploy (0: no preparations, the chapter places your army); +0x34 the goal text; +0x3E the event
  data; +0x40 the location text. The game's own lookup (0x0802BB0C) starts the record 4 bytes in.
- The map (LZ77) starts with its width and height, then a u16 per tile; tile >> 2 is a metatile, and the tile config's byte at
  0x2000 + metatile is its terrain id.
- Entries: 1-9 are Chapters 1-9; 10-11 are 10A and 11A; 12-16 are 12-16; 17-20 are 17A-20A; 21-24 are 21-24; 25 the Final; 26-27
  10B and 11B; 28-31 17B-20B; 32-38 the gaiden chapters (8x, 12x, 14x, 16x, 20Ax, 20Bx, 21x); 40-44 the trial maps. Entry 0 is the
  tutorial and 39 an event-less copy of Chapter 6's map; neither is listed.

## Events (`scripts/fe6_events.py`)

The event data has seven pointers: turn events, talks, locations, misc (areas and flags), the enemies the chapter starts with, your
army's group (its tiles are where you deploy) and the end-of-chapter script. The next chapter's turn list follows it directly.

- **Event lists:** 12-byte entries ending in a 0 type: u16 type, u16 flag (set once it runs; 0 = can run again), the script, then
  four bytes the type reads. The check per type is a table at 0x08666114: 1 a flag is set; 2 a turn (from, to, phase 0x00 yours,
  0x40 other, 0x80 enemy); **3 the same on Hard only** (0x0806A9DC: the chapter state's Hard bit), while flag 2 is clear; 4 two
  characters talk; 5 a house or seize tile, 6 a village, 7 a chest (the item, or gold << 16 | 0x6F), 8 a door, 10 a shop (0x13
  armory, 0x14 vendor, 0x15 secret shop; the script word points at a u16 item list); 11 an area; 13 a check routine.
- **Units:** 16-byte records ending in an all-zero one: character, class (0 = the character's own), leader, flags (level >> 3,
  side (>> 1) & 3: 0 yours, 1 another army's, 2 the enemy's), start tile, end tile (where it walks to), four items, AI. A
  character's boss flag is bit 0x80 of +0x29.
- **Scripts:** u32 commands, each with a handler and a length in words at 0x085C4164. The ones followed are listed at the top of
  `fe6_events.py` (labels, gotos and their conditions, unit loads and moves, removals, side changes, gifts, gold, flags, map
  changes, the next chapter). A goto to a missing label does nothing; labels can sit after the first "stop" command, so scripts
  are read to their 0x00 end.
- **Check routines** are read from their code (`check()`): Hard mode, a character alive or in your army, the turn past n, the
  phase, your gold over n, a coded talk's two characters, and "any of your units in x1..x2, y1..y2" (0x0806ACEC).
- **The interpreter** (`Run`) plays a script against a `World` (difficulty, flags, who's acting) the way the engine does. A
  chapter's start is its starting enemies, then every turn-1 event on your phase (Hard-only ones on Hard); units end where the
  scripted moves leave them, and units a script removes are gone. The Final Chapter's army is placed by code (0x080124A8), so its
  group's tiles are used with no names.

What the generator reads from them:

- **Reinforcements:** every other turn event, talk, area and location event that loads units, with when it fires (Hard-only
  groups say so per difficulty; coded area checks show their areas). Units a later turn event removes (Zephiel, Narcian in
  Chapter 13) say when they leave.
- **Talks:** who can talk to whom, and whether it recruits (side change to yours). A recruit only on a branch the plain run
  doesn't take says why: Hugh for gold (by what you hold), Cath on the third talk. Talks are matched by name, since a foe version
  of a character has its own id.
- **Villages and houses:** the items, gold or recruits their scripts give, per visitor where the script asks who's visiting
  (Chapter 10B). A village the opening closes (map change on it or the tile above: Chapter 1's raided village) is left out; a
  village that closes another says so (Chapter 9's pair, which also picks 10A or 10B).
- **Hidden items** (Chapter 14's sand): area events that give an item. Anyone stopping in the area on your phase: a thief always
  finds it, anyone else when a random number divided by 11 leaves 0 (0x0806D028); the Guiding ring only for Sophia.
- **End of chapter:** items handed to a character (Durandal, the Binding Blade) and who joins (Fa, so her stone counts from the
  next chapter).
- **The story:** the end scripts' "go to chapter" commands and their checks give the gaiden conditions and Chapter 9's split
  (flags 7 and 8: the two north-eastern villages). The 17A / 17B split is a code check (0x0806C5A8); its wording is Serenes
  Forest's (Thea and Juno's EXP against Sue and Sin's).

Checked against outside sources in `src/logic/__tests__/fe6.test.ts`: every map's starting enemy count against the Fire Emblem
Wiki's chapter data (all 43 match), chests, villages and the sand's finds against Serenes Forest's item-locations page.

## Battle code

- **Weapon triangle** (`scripts/build-triangles.py`): the triangle table's literal at 0x08025A9C (0x085C61C0); +10 hit and +1 Mt,
  the other side −10 and −1. Anima beats light, light beats dark, dark beats anima. A reaver flips it when only one side holds one.
- **Supports** (`scripts/build-fe6-supports.py`): the affinity table at 0x0866350C, eight bytes per affinity (id, Atk, Def, Hit,
  Avoid, Crit, Dodge). For each partner within 3 tiles: both rows times the level (C 1, B 2, A 3), summed, then halved once and
  rounded down (0x08022E3C). Levels at 61, 121 and 201 points; five levels at most per unit.
- **Hit:** two random numbers averaged (2RN), as the true hit page's 2RN system.
