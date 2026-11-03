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
  0x20 brave, 0x40 magic sword (below), 0x80 can't be countered (ballistae, Bolting, Purge, Eclipse), 0x100 reaver, 0x200 can't be repaired,
  0x400 Manaketes only, 0x1000 Myrmidons and Swordmasters, 0x4000 Delphi shield (no flier effectiveness), 0x8000 Iron rune,
  0x20000 the target's Def or Res counts as 0 (Luna), 0x40000 Eliwood, 0x80000 Hector, 0x100000 Lyn, 0x200000 Athos.
- Weapon effects (+0x1F), read in the battle code (0x08028F3A and on): 1 poison, 2 drains HP, 3 deals half the target's current HP
  rounded up (Eclipse; FE6's leaves 1 HP), 4 Devil axe (hurts the wielder at 31 − Luck %; FE6's 21).
- **Effectiveness doubles Mt** (FE6 and FE8 triple it): the attack routine at 0x08028B10 adds the triangle's Mt to the weapon's, and
  when the item's effectiveness list (+0x10) names the target's class (0x08016820) shifts the total left by one. A Delphi shield in the
  target's items cancels effectiveness against fliers.
- **Magic swords** (0x40: the Light Brand 0x10, the Runesword 0x11 and the Wind sword 0x99). The weapon setup (0x080288C0) gives
  the Runesword the dark type at any range and the other two the light and anima types at range 2, clearing the battle's copy of 0x40
  at range 1; the triangle reads that type (0x0802A180). Where the copy is set, 0x08028EEC takes half the wielder's Str (rounded down)
  back off the attack and sets crit to 0, so half the Str counts, rounded up, and no crits. The target's defence (0x08028A98) reads the
  item's own attributes, 0x40 or magic meaning Res, so all three are fought against Res at either range.
- Left out: the ballistae, and items nothing gives or carries (`src/data/fe7/fe7Listed.ts`).
- Not confirmed: the lock bits, read off the items that carry them. A weapon only foes carry and none drops is marked foe-only
  (thieves take only items: the steal check, below).

## Terrain

- 65 terrain ids, FE6's 51 and more (Flat, Wreck, Snag, Sky, Deeps, Ruins, Inn, Barrel, Bone, Dark, Water, Gunnel, Deck, Brace, Mast).
  Names: a u16 text id per terrain at 0xBE50E8.
- Every ground class shares the avoid, Def and Res rows at 0xBE44F9, 0xBE453A, 0xBE457B; fliers' avoid and Def rows (0xBE45BC,
  0xBE45FD) are all 0. Healing: 0xBE47C4 (read at 0x08019B2C; forts 20 %, gates, thrones and churches 10 %).
- 14 movement types (classes whose cost rows match, `MOVE_NAMES` in the maps generator; the build fails on a row no group names).
  Rain and snow rows aren't shown. A cost of 0 (the Fire Dragon, which never moves) counts as can't enter.
- Codes (`scripts/terrain_codes.py`, `GAME['fe7']`): FE6's, plus Sky `wf`, Deeps `wm`, Dark `wd`, and a new `tm` for ruins (cost 2 for
  everyone). Barrels, bones and gunnels work as cliffs; Flat and Deck as plain ground. Houses and inns are FE6's `ot` (no looter goes
  for them). Terrain 55, which the game calls Ruins as it does 37, is a village: village events stand on it (Chapter 18x, Eliwood's
  30) and the raiders' terrain list (0x08B97098) has it.

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
- **Hard's growth the level doesn't show:** on Hector Hard every foe gains the chapter record's +0x14 levels' worth (5 in every chapter)
  of its class's growths: an event's foes as they're placed (0x0800A6BC -> 0x08017B4C), a chapter with preparations' starting foes after
  them (0x0807926C -> 0x080799C8; its per-character list at 0x08C9F9EC is empty). The game levels a unit that isn't yours where its
  record's byte 3 has bit 0 set (0x080177E0 -> 0x08017B80); one in a promoted class gets 19 extra levels' worth on Hard, in either
  story, 9 on Normal (0x0803486C). Both raise HP, Str, Skl, Spd, Def and Res, not Lck (0x08017AC0, which reads the unit's class
  whatever class it's passed). The shown level stays the same; the maps say so on Hard. A unit that differs between the difficulties'
  groups only by its level is one entry with both levels ("Lv 8 (Hard 17)").
- **Fog:** 0x9D and 0x9E set the fog's vision (the high half; 0 lifts it, below 0 the record's +0xC: 0x0801DB58, 0x0801DB94). Living
  Legend's turn-1 event sets it on Hector Hard only (condition 4), so that map has fog on Hard; A Grim Reunion's turn-3 event brings fog
  in, Battle before Dawn's turn-16 event lifts it (both stories), and the maps say when.
- **Event lists:** entries as long as their type (the check table at 0x08C9E9A4: routine, size in words), ended by a 0 type. Types: 1 a
  flag is set; 2 a turn, with a condition at +0xC (1 Eliwood Normal, 2 Hector Normal, 3 Eliwood Hard, 4 Hector Hard, 5 Hard); 3 a talk
  (+0xC: 1 Eliwood's story, 2 Hector's, 3 once a flag is set); 4 a talk with a check routine; 5-10 tiles (0x0E house or village, 0x0F
  seize, 0x10 door, 0x12 chest: the item at +4, gold at +6 with the item 0x76; 0x13-0x15 shops); 11 an area; 12 / 13 an area in
  Eliwood's / Hector's story only; 14 a check routine; 15 / 16 once another flag is set.
- **Scripts:** u32 words, the opcode in the low byte (some take an argument in the high half); a handler and length per opcode at
  0x08B90E48. The ones followed are listed at the top of `fe7_events.py`. A goto searches the whole script for its label (0x0800D474);
  0x59 / 0x5A skip the next n commands on a check (the event loop counts them down, 0x0800B454). 0x58 goes on in another script
  (0x0800D91C); 0xCB calls one and comes back after it, keeping one place (+0x34 / +0x38, 0x0800FD7C; the end commands go back to
  it, 0x0800EC40): Hector's 32x finds its group that way, through a type-14 event (a check routine).
- **Map changes** (the chapter record's +0xB; `scripts/gba_doors.py`, as The Binding Blade's): 0x5F / 0x61 / 0x62 / 0x64 make one
  by id (0x0802BD68 writes its tiles, skipping 0s; 0xFFFF the event's own; the 0x8000 flag only drops the record of the change
  before it), 0x60 the one at a tile (0x0802BD0C), 0x63 only redraws. A door (type 8) opens the change under its tile. The opening's
  changes are made before the battle (the ships of Chapter 17 / Hector's 18, the doors standing open in 26 / Hector's 28, the tide of
  26x); the rest are previewed with what sets them off (Night of Farewells' water, turn by turn; the Final's rooms, turns 2-7).
  Rooms under their roofs (terrain 34) are closed until a door opens them: Lyn's Chapter 6, Kenneth's and Jerme's, the Final.
- **Cracked walls and snags** (0x0802BBB8): a wall (terrain 27) is one obstacle at the top of its column with the chapter record's
  wall HP (+0x2C); a snag (51) has 20. Breaking one makes the change under its tile; a snag's clears onto terrain 52, a bridge
  (the game's name) that only the final bosses' movement rows tell apart from the others (code `ts`).
- **Traps** (the event data's fifth list for Lyn's and Eliwood's story, the sixth for Hector's; loader 0x080345EC): 6-byte records up
  to a 0 type: type, x, y, then three bytes. 1 a ballista (the item in byte 3: 65 in 13 chapters, fired by an Archer or Sniper
  standing on it, class ability 0x80); 4 a fire tile (0x0802BB24: countdown byte 4, interval byte 5, and the 10 it keeps, a fire
  tile's damage); 5 a gas vent (0x0802BB40: its facing in byte 3, the countdown and interval, and a 3); 8, 9 and 11 other traps;
  2, 3, 6, 7 and 10 are skipped. A trap's countdown runs down once a turn (0x0802C16A) and it goes off when it runs out, then
  reloads from the interval. Not traced: which phase it ticks on, what the gas does (its 3: reach or damage).
- **End scenes:** a script that goes to a chapter (0x81) stages the end; whoever it places (Lloyd in the Linus chapters, Nergal and
  Limstella in 29x) is that scene's cast, so the maps leave it out, and its gear too.
- **Death quotes** (0x08C9F2EC, read by 0x080796C8; `scripts/gba_bosses.py`): 16 bytes, character, chapter (0x43 any), text, event, the
  flag the death sets. Each chapter's boss sets flag 2 there (47 entries), which is how the map knows its skull: Kishuna arriving in
  Aion's chapter, Cameron where Darin holds the throne, Kishuna leaving 22x are named foes.
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

- **What a talk does:** a talk that recruits no one says what else it does: clears the chapter where its script goes on to the chapter
  the end does (Fargus in 16x and Hector's 17x), or opens another where a flag it sets, its own included, sends one of the chapter's
  end events elsewhere, played with both of the talk present (Nino's talk with Jaffar: its flag 8 sends Chapter 26's turn-16 end to
  26x).
- **When gifts and gear count** (the weapon page's spoiler block): an end scene's gift is yours from the next chapter (kind
  `event-later`), as are a talk's gift mid-battle (`talk-later`) and what a foe a talk recruits carries (`kit-later`); an opening's
  gift (`gift`) from its own chapter. No opening gives an item.
- **Groups and when they come** (`gba_maps.one_per_arrival`, shared with the other two games): what one event places on each
  difficulty is one group, a unit only some difficulties have marked; the same units on the same tiles from events of their own are
  one group whose time lists each, per difficulty ('Turns 4, 6 and 8'); groups that come at the same moment, set off the same way, are
  one; the same units placed twice at once stay two. An area is checked after each unit's action (0x08079140, in your units' and the
  AI's procs at 0x08B93470 and 0x08B96FF8) against that unit's tile alone (0x08078650); one whose script first tests your phase (0x48
  on PLAYER_PHASE) and otherwise clears its own flag is set off by one of your units, any other by a unit of any army. A flag's group
  names the events that set it, by their own flag or a script's 0x76 (calls followed); a check routine on a list of tiles (Hector's
  32x: one of your units on any of nine, 0x0807DBA0) draws them. Hector's and Eliwood's Chapter 22x/23x keep one group waiting on flag
  8, which nothing in the chapter's scripts sets: 'After an event in the chapter'.
- **Looters and leavers** (`scripts/gba_ai.py`, the same engine in all three games): a unit's second AI byte (record +0xD, copied to
  the unit at 0x0803735E; scripts from 0x08B98908) picks a movement script; command 0x10 goes for the nearest village it can reach
  (terrain 3, 0x24 and 0x37, the tiles four maps' villages stand on) and, for a unit holding a Chest Key, or a Lockpick with its
  class's lockpick ability (bit 2), a chest (0x21); 0x17 makes for the nearest of the chapter's escape points (0x08B97100 /
  0x08B971C0: foes', then other armies', per chapter) and leaves the map. Second AI byte 0x04 loots, then attacks; 0x05 loots, then
  leaves; 0x0C only leaves; 0x1F waits a turn, then becomes 0x04. A looter gets the torch badge and says what it goes for (only what
  the map has); one that leaves names its exits (`goesTo`, staircases among them); a village names the looters on the map at the start
  that can raze it. A unit the script takes off the map isn't given the AI's exit as well.
- **Stealing and the gem badge** (`gba_maps.mark_steals`): a thief takes only items. Every steal routine tests an item with one
  check, type (item record +7) == 9 (0x08016D38), so never a weapon, staff or dragonstone; the target list (0x080244AC) takes an
  enemy-army unit (+0xB & 0xC0 == 0x80) whose Speed (+0x16) is no higher than the thief's, holding such an item. A foe holding a rare
  one it doesn't drop gets the gem badge and a "Steal:" line: an item kept for something lasting (its use, item record +0x1E, isn't
  0x1E-0x28 or 0x33-0x35: the keys, the Lockpick, healing and curing, the Torch, Mines and Light Runes) that no armory or vendor
  sells (what only a secret shop sells still counts). A recruit brings its items along: not marked.

Not confirmed: who the defeat condition names (Lyn in her story; Eliwood or Hector in theirs). No ability bit marks the lords, and the
game-over check wasn't traced. What razing does to a village's tiles: the AI's raze (0x08035398) looks up the village's event and its
map change on the tile above the looter (0x08078C14 -> 0x0802BD0C), one row above the gate the village events stand on, so the razed
village isn't previewed until it's seen in the game.

## Battle code

- **Weapon triangle** (`scripts/build-triangles.py`): the table at 0x08B9426C (loaded at 0x0802A17C), +15 hit and +1 Mt, the other side
  −15 and −1. Each side holding a reaver calls 0x0802A120, which multiplies all four by −2 unless both sides hold one.
- **Supports** (`scripts/build-gba-supports.py`): FE6's routine at new addresses (the partner walk at 0x08026A18, the rows at
  0x08C9A1C0, the same seven affinities): both rows times the level for each partner within 3 tiles, summed, halved once. Levels at 81,
  161 and 241 points (0x08026690); five levels at most per unit (0x0802696C).
- **Hit:** two random numbers averaged (2RN): 0x08000E84, called once, from the battle code at 0x080285C0.
