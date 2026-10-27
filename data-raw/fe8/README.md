# The Sacred Stones (FE8) game files

Read from the user's own cartridge image: `Fire Emblem - The Sacred Stones (U).gba` (GBA, North American, 16 MB, CRC32 A47246AE). The
image stays on the user's PC (default path in `scripts/gba_rom.py`, or set `FE8_ROM`) and is never committed; only data built from it
is. The game is in English, so every name and title is its own text.

Offsets are file offsets; the game addresses them as 0x08000000 + offset. Data is little-endian. Items, classes, characters, text and
maps are laid out as in The Blazing Blade (`data-raw/fe7/README.md`) and read by the same `scripts/gba_rom.py`. The event engine is a
different one (below). Names for the event commands and for some structures are the FE8 decompilation project's
([FireEmblemUniverse/fireemblem8u](https://github.com/FireEmblemUniverse/fireemblem8u)), used as a map; what the generators rely on was
checked in the ROM's own code at the addresses given.

## Text, items, classes, characters (`scripts/gba_rom.py`)

Text at 0x15D48C, characters at 0x803D30, classes at 0x807110, items at 0x809B10 (206), terrain names at 0x80D374, healing at
0x80C744, the affinity rows at 0x8B05F8: the same formats as The Blazing Blade's.

## Weapons (`scripts/build-gba-items.py` -> `src/data/fe8/fe8Weapons.ts`)

- The item attribute bits and weapon effects are The Blazing Blade's, plus effect 5 (petrifies).
- **Effectiveness triples Mt** (with the triangle's +1 or −1, the attack routine at 0x0802AABC), but **doubles it** for the eight items
  0x3E, 0x85, 0x87, 0x8E, 0x91-0x94 (the legendary weapons: their `effectiveMultiplier`). The Stone tome's attack is set to 0
  (0x0802AB5E).
- Monster weapons (claws, fangs, eyes) are their own category; they're outside the triangle.

## Terrain

- FE7's 65 terrain ids. Terrain 35 is a gate with 30 Avoid where terrain 11 has 20, so it has its own code, `bv` (FE7's two gates are
  the same).
- 14 movement types (`MOVE_NAMES` in the maps generator). The Gorgon Eggs have no movement row at all and never move, so they're no
  movement type.

## Chapters: 0x8B0890, 0x94 bytes each (`scripts/build-fe8-maps.py`)

- +0 the internal name ("L00", "E09", "I10x", "T01", "R01"); +8 the map; +0xB map changes; +0xC the fog vision; +0x14 / +0x15 the
  difficulty level changes (nibbles: Easy's, Hard's, Normal's; below); +0x70 the title (text id, no chapter number); +0x74 the event
  data; +0x88 the goal; +0x8E the character to protect. The +0xD preparations flag is 0 in every chapter: the openings call the
  preparations screen themselves.
- Entries 0-9 are the shared chapters (5 is Ephraim's Chapter 5x, played between 5 and 6, entry 6); 10-22 and 61 Eirika's route
  (61 "Creeping Darkness" is her Chapter 11), 23-35 and 62 Ephraim's (62 "Phantom Ship" is his 11); 21 / 22 and 34 / 35 the two parts of
  the Final Chapter; 36-43 the Tower of Valni's floors; 46-55 the Lagdou Ruins'. The order is the end scripts' (each one's "go to
  chapter", 0x2A); the Chapter 11 maps come in through the world map. 56 (Castle Frelia, after Chapter 1) and 57 (Melkaen Coast) hold no
  battle of the story; 58-60 and 63-78 are empty or the world map's.
- **Difficulty:** as an enemy whose character id is above 0x3B is made, it loses the chapter's Easy or Normal number of levels, or gains
  its Hard number, its stats grown or shrunk with them (0x0800F80A -> 0x080180CC). Named characters (ids 0x01-0x3B) and the Gorgon Egg
  classes (0x34, 0x62) keep theirs. The maps give each generic foe's level on Normal, with Easy's and Hard's beside it. Hard is the play
  state's bit 0x40; which of the other two nibbles is Easy's and which Normal's (chosen by bit 5 of the play state's byte 0x42) is the
  decompilation's naming, not traced further.

## Events (`scripts/fe8_events.py`)

The event data has 20 pointers: turn, talk, location and misc events; four lists for selection and tutorial events; traps, and the
extra traps on Hard; your army's deploy tiles on Normal and on Hard (the same group in every chapter); three choices of your army and
three of the enemies for a skirmish on the chapter's map; the opening and ending scenes.

- **Event lists:** entries as long as their type says (the game's own table at 0x089E84F4: check routine, size in words), ended by a 0
  type. 1 a flag is set; 2 a turn (from byte 8 to byte 9, 0xFF every turn; the phase at +0xA: 0 yours, 0x40 the other army's, 0x80 the
  enemy's; no difficulty condition: the scripts check that); 3 a talk (+0xC: 0 always, 3 once the flag at +0xE is set); 4 a talk with a
  check routine; 5 a tile (command 0x10 a house, 0x11 seize, 0x20 a village's gate); 6 a village (0x10); 7 a chest (the item at +4,
  gold as item 0x77 with the amount in the high half); 8 a door; 10 a shop (0x16 armory, 0x17 vendor, 0x18 secret shop, which checks for
  a Member Card, 0x08083A59); 11 an area; 14 a check routine; 15 / 16 one flag set and another clear. An event runs only while its own
  flag (+2) is clear, so one whose flag the opening sets waits for the event that clears it (Chapter 4's Revenants: an area).
- **Scripts:** a command is a u16 (the command in the high byte, its length in u16s in bits 4-7, a variant in bits 0-3; 0x0800CED0,
  handlers at 0x08591B28); slots s0-s13 hold values, checks answer in s12, branches compare two slots, labels are searched from the
  script's start. The commands followed are listed at the top of `fe8_events.py`.
- **Units:** 20-byte records (character, class, leader, level / side / auto-level, the tile with three flags, the REDA steps the unit
  walks once loaded, items, AI). Bit 12 of the tile makes a random monster in the record's place (0x08017ACC: its class, level and items
  are picked then); bit 13 makes it drop its last item (0x08017CC4: unit state 0x1000); bit 14 lets the loader leave it out at random
  (0x0800F914). The loader leaves out your characters who have died unless the load says otherwise (0x0800F528).
- **A chapter's start:** the opening scene (cutscenes load other chapters' maps, 0x25, and clear everyone afterwards, 0x34 variants
  A-C); where it calls the preparations screen (0x3E), your army goes to the deploy group's tiles (after the lord's, its characters are
  placeholders). Then every turn-1 event on your phase runs.
- **Rewards on a condition:** an end scene is played twice, once as things stand and once with everyone it asks about alive and every
  unit of the other army left; what only the second gives is said with the condition read from its checks (the characters whose death
  loses it, each tried dead in turn; how many of the other army it needs left). Chapter 6's Orion's Bolt, Ephraim's Chapter 10's Knight
  Crest, Chapter 17's Rescue, Chapter 19's Light Brand.
- **Buried items** (Chapter 15's desert): area events that call a shared script (0x089EE61C): a Thief or a Rogue always finds the item,
  anyone else when a random number from 0 to 99 is at most their Luck; only your units (0x089EE1B8).
- **The Tower of Valni and the Lagdou Ruins** are mostly random monsters: shown where they stand, as "Random monster".

## The world map (`world_map_shops` in `scripts/build-fe8-maps.py`)

29 nodes of 0x20 bytes at 0x2060B0 (the decompilation's `GMapNodeData`): the chapter played there on Eirika's and Ephraim's routes (+4,
+5), u16 item lists for an armory, a vendor and a secret shop (+0xC, +0x10, +0x14), the name (+0x1C). A town's shops are a source from
the chapter after its own, on each route that passes through it, for the rest of the game (kind `town-shop-later`).

Checked against outside sources in `src/logic/__tests__/fe8.test.ts`: every story map's starting enemy count, per route and difficulty,
against the Fire Emblem Wiki's chapter data (all match but Chapter 5, where the wiki's 16 leaves out Joshua).

Not confirmed:
- Who the defeat condition names: the route's lord, the other twin where the chapter puts them on its map as yours, and the character
  the chapter record says to protect. The game-over check wasn't traced.
- That a world map town's shops open once its chapter is cleared.
- That a dropping unit drops its last item (as The Blazing Blade's do; FE8's drop code wasn't traced).
- What the random monsters carry and drop, and when the Tower and the Ruins open (shown once the story is cleared). Shadowkiller, Bright
  Lance, Fiendcleaver, Beacon Bow and Alacalibur turn up in no shop, chest, gift or fixed unit, so they're not listed yet.
- Skirmishes (the Creature Campaign's random battles on the world map) aren't shown.
