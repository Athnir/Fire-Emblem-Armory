# The Blazing Blade (FE7) game files

Read from the user's own cartridge image: `Fire Emblem (U) [!].gba` (GBA, North American, game code AE7E, 16 MB, CRC32 2A524221). The
image stays on the user's PC (default path in `scripts/gba_rom.py`, or set `FE7_ROM`) and is never committed; only data built from it
is. The game is in English, so every name and title is its own text.

Offsets are file offsets; the game addresses them as 0x08000000 + offset. Data is little-endian. The game's data and engine grew out of
The Binding Blade's (`data-raw/fe6/README.md`): the same Huffman text, item, class and unit layouts with wider records, the same chapter
record fields 4 bytes earlier, the same LZ77 maps. Its event engine keeps FE6's shape but renumbers every command and checks the story
and difficulty throughout. `scripts/gba_rom.py` reads FE7 and FE8 alike.

## Text, items, classes, characters (`scripts/gba_rom.py`)

- **Text:** a u32 pointer per text id at 0xB808AC; the word before it points to the Huffman tree's root node, the last of the tree's
  nodes (so the tree starts at the root minus 4 × (its right child + 1)). The decoder is FE6's; bit 31 of a pointer means the text is
  stored plain. Characters are single bytes; 0x01 is a line break, other codes below 0x20 control the text box.
- **Items:** 36-byte records at 0xBE222C, ids 1-158 (the id byte at +6 equals the index). FE6's fields at the same offsets, plus the
  weapon EXP at +0x20. Weapon ranks need E 1, D 31, C 71, B 121, A 181, S 251 (the rank byte at +0x1C; 0 is a personal weapon).
- **Classes:** 84-byte records at 0xBE015C. The rows a class points at: movement cost (+0x38), in rain (+0x3C) and snow (+0x40),
  terrain avoid (+0x44), Def (+0x48), Res (+0x4C).
- **Characters:** 52-byte records at 0xBDCE18, indexed by id (id 0 unused). Abilities at +0x28: 0x8000 is the boss flag, 0x4000
  female. The portrait is the u16 at +6 (0 for the generic foes' records: "Bandit", "Black Fang", "Laus").

## Weapons (`scripts/build-gba-items.py` -> `src/data/fe7/fe7Weapons.ts`)

- Attribute bits (+8), the same in FE8: 0x01 weapon, 0x02 magic, 0x04 staff, 0x08 unbreakable, 0x10 unsellable (the legendary weapons),
  0x20 brave, 0x40 magic at range, 0x80 can't be countered (ballistae, Bolting, Purge, Eclipse), 0x100 reaver, 0x200 can't be repaired,
  0x400 Manaketes only, 0x1000 Myrmidons and Swordmasters, 0x4000 Delphi shield (no flier effectiveness), 0x8000 Iron rune,
  0x20000 the target's Def or Res counts as 0 (Luna), 0x40000 Eliwood, 0x80000 Hector, 0x100000 Lyn, 0x200000 Athos.
- Weapon effects (+0x1F), read in the battle code (0x08028F3A and on): 1 poison, 2 drains HP, 3 deals half the target's current HP
  rounded up (Eclipse; FE6's leaves 1 HP), 4 Devil axe (hurts the wielder at 31 − Luck %; FE6's 21).
- **Effectiveness doubles Mt** (FE6 and FE8 triple it): the attack routine at 0x08028B10 adds the triangle's Mt to the weapon's, and
  when the item's effectiveness list (+0x10) names the target's class (0x08016820) shifts the total left by one. A Delphi shield in the
  target's items cancels effectiveness against fliers.
- Left out: the ballistae, and items nothing gives or carries (`src/data/fe7/fe7Listed.ts`).
- Not confirmed: the lock bits, read off the items that carry them; that thieves steal items only (FE8's code checks the item type;
  FE7's steal check wasn't traced). A weapon only foes carry and none drops is marked foe-only.

## Terrain

- 65 terrain ids, FE6's 51 and more (Flat, Wreck, Snag, Sky, Deeps, Ruins, Inn, Barrel, Bone, Dark, Water, Gunnel, Deck, Brace, Mast).
  Names: a u16 text id per terrain at 0xBE50E8.
- Every ground class shares the avoid, Def and Res rows at 0xBE44F9, 0xBE453A, 0xBE457B; fliers' avoid and Def rows (0xBE45BC,
  0xBE45FD) are all 0. Healing: 0xBE47C4 (read at 0x08019B2C; forts 20 %, gates, thrones and churches 10 %).
- 14 movement types (classes whose cost rows match, `MOVE_NAMES` in the maps generator; the build fails on a row no group names).
  Rain and snow rows aren't shown. A cost of 0 (the Fire Dragon, which never moves) counts as can't enter.
- Codes (`scripts/terrain_codes.py`, `GAME['fe7']`): FE6's, plus Sky `wf`, Deeps `wm`, Dark `wd`, and a new `tm` for ruins (cost 2 for
  everyone). Barrels, bones and gunnels work as cliffs; Flat and Deck as plain ground.

## Chapters: 0xC9A200, 0x98 bytes each (`scripts/build-fe7-maps.py`)

- +0 a pointer to the internal name ("T01)00", "01)11h"); +7 the tile config and +8 the map (indices into the pointer table at
  0xC9C9C8); +0xB the map changes; +0xC the fog vision; +0xD 1 when the chapter has preparations (the end of the opening, 0x0800B73D,
  and 0x0803089C); +0x70 / +0x72 the title in Eliwood's / Hector's story ("Ch. 15: Noble Lady of Caelin" / "Ch. 16: …"); +0x78 the event
  data; +0x8C the goal.
- Entries 0-11 are Lyn's story (8 is 7x); 12-47 Eliwood's and Hector's (13 "Another Journey", 18 "Talons Alight", 25 "A Glimpse in
  Time", 33 "Crazed Beast", 41 "The Berserker", 45 "The Value of Life" are Hector's only; 40 "Valorous Roland" Eliwood's only; 31 / 32
  are Chapter 23 against Lloyd / Linus, 35 / 36 Chapter 25 against Kenneth / Jerme; 46 / 47 the two parts of the Final Chapter). 48-64
  are event-only entries (endings), 65 "VS" and 66 "test"; none is listed.
- The map (LZ77) and its terrain work as in FE6. Map changes: 12-byte records (id, x, y, width, height, 3 unused, tiles pointer) up to
  id 0xFF.
- Hector's story numbers its chapters one or two ahead of Eliwood's from Chapter 15; the game's own heading for entry 25 is "Ch. 19x pt
  2" (Serenes Forest and the wikis call it 19xx).

## Events (`scripts/fe7_events.py`)

The event data has 16 pointers: turn, talk, location and misc events; the traps for Lyn's and Eliwood's story and for Hector's
(0x080791F0); the enemies a chapter with preparations starts with, for Eliwood Normal, Eliwood Hard, Hector Normal and Hector Hard
(0x08079214; Lyn's story takes Eliwood's); your army's group in the same order (its tiles are where you deploy, 0x08079280); the opening
and ending scenes.

- **The mode** is the chapter state's (0x0202BBF8) byte 0x1B: 1 Lyn, 2 Eliwood, 3 Hector. Hard is bit 0x40 of its byte 0x14. Byte 0x2B
  bit 0 is cleared when Lyn's story is skipped (0x080A6D68); the scripts check it (0x0807A3B9) to load Lyn's companions or not. The maps
  assume Lyn's story was played.
- **Event lists:** entries as long as their type (the check table at 0x08C9E9A4: routine, size in words), ended by a 0 type. Types: 1 a
  flag is set; 2 a turn, with a condition at +0xC (1 Eliwood Normal, 2 Hector Normal, 3 Eliwood Hard, 4 Hector Hard, 5 Hard); 3 a talk
  (+0xC: 1 Eliwood's story, 2 Hector's, 3 once a flag is set); 4 a talk with a check routine; 5-10 tiles (0x0E house or village, 0x0F
  seize, 0x10 door, 0x12 chest: the item at +4, gold at +6 with the item 0x76; 0x13-0x15 shops); 11 an area; 12 / 13 an area in
  Eliwood's / Hector's story only; 14 a check routine; 15 / 16 once another flag is set.
- **Scripts:** u32 words, the opcode in the low byte (some take an argument in the high half); a handler and length per opcode at
  0x08B90E48. The ones followed are listed at the top of `fe7_events.py`. A goto searches the whole script for its label (0x0800D474);
  0x59 / 0x5A skip the next n commands on a check (the event loop counts them down, 0x0800B454).
- **Units:** FE6's 16-byte records. The loader (0x0800A618) reuses a character's unit when one of yours is loaded and it's already on
  the map; a foe is always a new unit, unless the character is one of yours (then that unit changes side).
- **Routines scripts call** that the generator follows: 0x0807A869 clears every unit that isn't yours, 0x0807A891 only the enemies,
  0x0807A8B9 everything (your units leave the map but stay in the army).
- **A chapter's start:** the opening scene runs at the start of every chapter (0x0801537C). A chapter with preparations then clears every
  unit that isn't yours and loads the enemy group for the story and difficulty (0x0803089C -> 0x08018980). Then every turn-1 event on
  your phase runs; a chapter without preparations lists its opening as a turn-1 event too, and it plays once.
- **Check routines** read from their code: a character is one of your living units (0x08079D40), no enemy is left (0x08079FE9), Lyn's
  story was played, your phase. The gaiden conditions are read from each end script (the checks before each "go to chapter", 0x81; every
  gaiden also asks "Embark on side quest?", and a "no" skips it): 7x and 18x by turn count (0x56: within 15), 32x within 20, 13x a flag
  set by the north-western village, 26x a flag set when Nino talks to Jaffar. Where a condition is a routine of its own (16x's Caelin
  soldiers, 19xx's Nils at level 7 or more and Kishuna defeated, 22x's Hawkeye and EXP over 699, Lloyd or Linus by the lords' levels),
  the numbers are the code's and the wording Serenes Forest's. Kenneth or Jerme: 0x0807D4C1 totals a measure (0x080A01DC) for Guy,
  Dorcas, Bartre and Raven against Erk, Lucius, Renault, Priscilla and Serra (the game's lists at 0x08CB8984, 0x08CB898E); the first
  group's higher total gives Jerme. That the measure is EXP gained is Serenes Forest's.
- **Drops:** as a unit is made (0x08017826), it gets state 0x1000 when its character's or its class's abilities (+0x28) have
  0x08000000; when a unit in that state is defeated its last item goes to your army (0x0802FA22), and the menus mark that item
  (0x0802F5F8). The maps list each foe's drop and the weapon page counts it as a way to get the item.
- **Sources:** a unit's items are counted where it first joins the story (the openings of chapters without preparations load your
  units again; the loader reuses them, so that's no new copy), including a unit the opening loads as yours that then leaves the
  map (Athos in the Final Chapter, with Durandal, Armads, Forblaze and Aureola). 0x0807DBF5, called from that opening when Athos
  isn't in your army yet, adds a Sol Katti to his items (0x08017D34 his unit, 0x08016174 makes the item, 0x08017654 adds it).
  Karel's Wo Dao counts where he's recruited. What a foe holds is listed only for a weapon nothing else gives.
- A unit that arrives on a tile another holds is shown on the nearest free tile; the game picks its own (marked on the map as
  unconfirmed where it happens).

Checked against outside sources in `src/logic/__tests__/fe7.test.ts`: every map's starting enemy count, per story and difficulty,
against the Fire Emblem Wiki's chapter data (all match but Hector Hard's Chapter 27 against Jerme, where the event data's group holds 54
and the wiki says 50).

Not confirmed: who the defeat condition names (Lyn in her story; Eliwood or Hector in theirs). No ability bit marks the lords, and the
game-over check wasn't traced.

## Battle code

- **Weapon triangle** (`scripts/build-triangles.py`): the table at 0x08B9426C (loaded at 0x0802A17C), +15 hit and +1 Mt, the other side
  −15 and −1. Each side holding a reaver calls 0x0802A120, which multiplies all four by −2 unless both sides hold one.
- **Supports** (`scripts/build-gba-supports.py`): FE6's routine at new addresses (the partner walk at 0x08026A18, the rows at
  0x08C9A1C0, the same seven affinities): both rows times the level for each partner within 3 tiles, summed, halved once. Levels at 81,
  161 and 241 points (0x08026690); five levels at most per unit (0x0802696C).
- **Hit:** two random numbers averaged (2RN): 0x08000E84, called once, from the battle code at 0x080285C0.
