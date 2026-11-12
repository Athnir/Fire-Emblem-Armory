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

- The item attribute bits and weapon effects are The Blazing Blade's, plus effect 5 (petrifies). The magic swords work as The Blazing
  Blade's (the weapon setup 0x0802A872, half Str and no crits 0x0802ADD2, the target's defence 0x0802AA44, the triangle reading the
  battle's type at 0x0802C7D2); the Wind Sword is 0xA1.
- **Effectiveness triples Mt** (with the triangle's +1 or −1, the attack routine at 0x0802AABC), but **doubles it** for the eight items
  0x3E, 0x85, 0x87, 0x8E, 0x91-0x94 (the legendary weapons: their `effectiveMultiplier`). The Stone tome's attack is set to 0
  (0x0802AB5E).
- Monster weapons (claws, fangs, eyes) are their own category; they're outside the triangle.

## Terrain

- FE7's 65 terrain ids. Terrain 35 is a gate with 30 Avoid where terrain 11 has 20, so it has its own code, `bv` (FE7's two gates are
  the same). Houses and inns are `ot`, as in FE6 and FE7.
- 14 movement types (`MOVE_NAMES` in the maps generator). The Gorgon Eggs have no movement row at all and never move, so they're no
  movement type.

- **Walls by kind** (`scripts/gba_walls.py`, shared by the three GBA games): the walls no unit enters are drawn by what they are on
  the map, by look at the real art of every wall tile each tileset puts on a map (the chapter record's graphics, palette, tile config
  and map, drawn the way the game builds the map): castle, ruins, temple, sandstone, snow, wood; a roof (34), the void around some maps
  (0, unnamed); a village's houses and walls (46, unnamed) and a ship's sides (61), which fliers cross, have codes of their own. A
  wall (26, 27, 63) takes its tileset's kind, or its chapter's where the chapter's palette makes the same tiles another kind; a
  building of 44 (unnamed, rare: a castle on an outdoor map) takes its entrance's kind, a gate or throne a castle's, a village, house
  or shop a village's, through the village's 46 around it. Only snags stay plain walls (fallen trees until broken).
  The Sacred Stones' tilesets (+4): 1, 14, 24, 46, 60, 80, 121 castle (the outdoor sets' walls and the castle halls), 66 sandstone
  (Scorched Sand), 95 temple (the Final Chapter), 108 ruins (Lagdou, Ephraim's Chapter 10), 136 ruins (the Tower of Valni); Chapter 14
  (Jehanna's Hall, tileset 60) sandstone.

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
  state's bit 0x40; bit 5 of its byte 0x42 picks the other two nibbles: clear, +0x14's low one, set, +0x15's. The new-game menu
  (0x080A9250, its choices top to bottom: Easy, Normal, Hard) sets that bit for its second and third choices through 0x08030CF4, so
  the clear one is Easy's.
- **Hard's growth the level doesn't show:** the game levels a unit that isn't yours, where its record's byte 3 has bit 0 set (0x08017C8C),
  from its class's growths in HP, Str, Skl, Spd, Def, Res and Lck (0x08017FC4); a generic in a promoted class (character above 0x3F, no
  boss: 0x08017C36 levels the others another way) gets 19 extra levels' worth on Hard, 9 on Easy and Normal (0x08037B44). The maps
  that have one say so on Hard. A random monster's class is picked as it's made, so the Tower's and the Ruins' say nothing.

## Events (`scripts/fe8_events.py`)

The event data has 20 pointers: turn, talk, location and misc events; four lists for selection and tutorial events; traps, and the
extra traps on Hard; your army's deploy tiles on Normal and on Hard (the same group in every chapter); three choices of your army and
three of the enemies for a skirmish on the chapter's map; the opening and ending scenes.

- **Map changes** (the chapter record's +0xB; `scripts/gba_doors.py`): 0x2720 makes one, 0x2721 undoes it (0xFFFF: the one at the
  tile in s11), counted only while the chapter's own map is loaded (0x25 loads a scene's map). A door (type 8) opens the change
  under its tile. The opening's are made before the battle: Chapter 2's razed village, Chapter 8's flooded path, Ephraim's Chapter
  11's phantom ship (put down after the map reloads, 0x25 0x3E); a change only beside a village (its 0 tiles) doesn't close it,
  so Eirika's Chapter 9 keeps its Dragonshield village. Rooms under their roofs (Eirika's Chapter 14) are closed until a door
  opens them.
- **Turns' changes, in turn order** (`gba_doors.in_turn_order`): a change a turn's script makes (`turn` on it) is made on the map
  as the turns before left it, its patch the tiles it changes from that, so the app steps through the map's states. An undo of a
  change an earlier script made puts the map's own tiles back over its rectangle: Ephraim's Chapter 11's turn 2 undoes the
  opening's ship (change 0) and draws it alongside yours (change 1), its turn 3 lowers the gangplanks (2), its turn 5 sails
  L'Arachel's ship in (3), Dozla and L'Arachel arriving on its deck.
- **Cracked walls and snags** (0x0802E3D2): as The Blazing Blade's, the wall HP at the chapter record's +0x2C, a snag 20.
- **Traps** (the event data's traps, and the extra traps on Hard; loader 0x08037840, the record The Blazing Blade's): 1 a ballista;
  4 a fire tile (0x0802E314, 10 damage: the decompilation's fire tile applies -10); 5 a gas vent (0x0802E330: facing, and a 3); 7
  an arrow launcher (0x0802E350: a column, its countdown and interval, and a 10); 8, 9 and 11 other traps; 12 a Gorgon egg's
  hatching (0x08037928, Chapter 18's 24 eggs, which are on the map as units). The countdown runs down once a turn (0x0802E9A8) and
  the trap goes off when it runs out, then reloads from its interval (0x0802E9D0). Ruins 9's Hard list adds 20 fire tiles. Not
  traced: which phase a countdown ticks on, what a gas vent's gas and an arrow launcher's arrows do. The arrow launcher's case in
  the loader runs on into the egg's (no break), with its own bytes: what that makes wasn't traced either.
- **End scenes:** a script that goes to a chapter (0x2A) stages the end; whoever it places (Chapter 4's Eirika, Seth, L'Arachel, Dozla
  and Rennac; Lyon in Chapter 18 and the Final) is that scene's cast, so the maps leave it out.
- **Defeat quotes** (0x089ECD4C, read at 0x0808472C; `scripts/gba_bosses.py`): 12 bytes, character (u16), route, chapter (0xFF any), the
  flag the death sets (u16), text, event. 31 set flag 2, each in its own chapter, which names the map's boss: Beran (not Selena) in
  Ephraim's Chapter 10, Aias (not the Pablo who arrives) in Eirika's 13, a Cyclops in Ephraim's 12 (a "defeat the boss" map:
  Caellach passes through). A seize map has none; its tie goes to the unit on the seize tile (Morva over Riev in Chapter 20).
- **Army names:** 'Monster' (27 characters), 'Enemy' (103) and Chapter 5's 'Bandit' are shared by characters without portraits, so their
  units go by class, bosses too (the Tower's and the Ruins' bosses: an Entombed, a Gorgon, a Draco Zombie).
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

- **Skirmishes** (`skirmish_maps`): the world map's monsters fight at a node whose chapter's event data has line-ups (+0x30, +0x34,
  +0x38 your deploy tiles; +0x3C, +0x40, +0x44 the enemies): Za'ha Woods, Adlas Plains, Teraz Plateau, Hamill Canyon, Bethroen,
  Za'albul Marsh, Narube River and Neleras Peak (a chapter, and line-ups, on each route) and Melkaen Coast (chapter 57, a map no story
  chapter uses). One index the world map keeps (0x03005280 + 0xC9, by its +0xCC) picks both the deploy tiles (0x08083348) and the
  enemies (0x080833B0), so each line-up is a map of its own. In a skirmish 0x080BD068 gives 2 (the node's battle isn't its story's):
  no village, chest, door or shop event runs (0x080840C4 skips them); fog comes half the time, vision 3 (0x08030E54); and one
  opening and one ending play at every location in place of the chapter's (0x089FFC30 for +0x48, 0x080153FC; 0x089FFD64 for +0x4C,
  0x080832A8). The opening (`skirmish_setup`) queues each location's chapter with a script and calls a lookup (0x089FFC0C) that
  runs this chapter's: it calls 0x089EE84C with five weights on the queue (50, 25, 15, 5, 5), which picks a share by them from a
  random 0-99 (0, 40, 60, 80 or 100%) for the unit loader (0x2B variant 1), then queues the map changes to make. Back in the
  opening, 0x27 with 0xFFFD makes the queued changes in order (0x0800F2D4) and 0x2C variant 3 loads the line-up: of its units with
  bit 14 it places (their number × the share + 50) / 100, picked at random (0x0800F914), so a line-up's other units always come
  (three at most locations; Melkaen Coast's seven; Neleras Peak's 15, and all 37 of its first). The changes made are the
  destroying ones, which the story never makes for houses and shops (`destroyed`): villages, houses, shops and the arena to Ruins
  (terrain 37), snags to bridges, doors open; a village's closed gate, under its ruins, isn't made (Chapter 4's 0-2 of 0-5, 7's 0
  of 0-1, 24's 0-3, 6 and 7, 26's 0, 1 and 4; all of 11's and 17's / 30's). Hamill Canyon, Neleras Peak and Melkaen Coast have no changes; Neleras Peak's script also turns the fog off
  (0x29 with 0). The ending only sets s2 to a chapter for 0x2A. They're side maps, listed after the Tower and the Ruins, and the
  story chapter played on the same map says so. Each opens with its location (the chapter played there cleared; at the route's
  end where the route plays no chapter there, Melkaen Coast's on both; when the world map starts sending monsters isn't read). The
  other chapter records past the story (56, 58-60, 63-78) are scene maps, mostly one screen (15 by 10).

- **A recruit for gold:** a talk that calls the shared script at 0x089EEAAC with a character in s3 and a price in s4 offers that
  character for gold: it asks, compares your gold (0x19 variant 8) with the price, makes the character yours (0x34 variant 2) and
  takes the price (0x37 variant 2, 0x080105F8). Rennac in Chapter 14: free with L'Arachel, 9,980 gold with Eirika or Ephraim (s4 =
  0x26FC).
- **When gifts and gear count** (the weapon page's spoiler block): an end scene's gift is yours from the next chapter (kind
  `event-later`), as are a talk's gift mid-battle (`talk-later`) and what a foe a talk recruits carries (`kit-later`); an opening's
  gift (`gift`) from its own chapter. The Prologue's opening gives Eirika her Rapier (0x37 in the script at 0x089EF060), so it's hers
  on both routes; on Easy the opening makes the tutorial's script the chapter's tutorial step (0x0B variant 1, 0x08083DD8) and ends,
  and the tutorial's scripts reach the same script, so Easy has Normal's gift (hands_to_tutorial).
- **Groups and when they come** (`gba_maps.one_per_arrival`, shared with the other two games): what one event places on each
  difficulty is one group, a unit only some difficulties have marked; the same units on the same tiles from events of their own are
  one group whose time lists each, per difficulty ('Turns 4, 6 and 8'); groups that come at the same moment, set off the same way, are
  one; the same units placed twice at once stay two. An area is checked after each unit's action (0x08084330, from your units' and the
  AI's code) against that unit's tile alone (0x08083AA4); its script may call SIDE_CHECK (0x089EE1B8: the acting unit's side, 0x33
  variant 5, against s2) or CHAR_CHECK (0x089EE19C: its character, 0x2E variant 1) and otherwise clear its own flag: one of your
  units, or one character (Eirika in Chapter 1), else a unit of any army. Command 0x02's variant bit 3 sets, its low bits pick a
  script's own bits (0) or event flags (1): only variants 1 and 9 touch flags (0x0800D670). A flag's group names the events that set
  it (calls followed); an event waiting on no flag whose script checks that a character is gone (0x33 variant 0) unlocks the Tower's
  floor 7 spawns: 'once the Elder Bael and 3 random monsters are defeated'.
- **Looters and leavers** (`scripts/gba_ai.py`, the same engine in all three games): a unit's second AI byte (record +0x11, copied to
  the unit at 0x0803C266; scripts from 0x085A9138) picks a movement script; command 0x10 goes for the nearest village it can reach
  (terrain 3, 0x24 and 0x37) and, for a unit holding a Chest Key, or a Lockpick with its class's lockpick ability (bit 2), a chest
  (0x21); 0x17 makes for the nearest of the chapter's escape points (0x085A8188 / 0x085A828C: foes', then other armies', per chapter)
  and leaves the map. Second AI byte 0x04 loots, then attacks; 0x05 loots, then leaves; 0x0C only leaves; 0x11 waits a turn, then
  becomes 0x04. A random monster's AI isn't said. A looter gets the torch badge and says what it goes for (only what the map has); one
  that leaves names its exits (`goesTo`, staircases among them); a village names the looters on the map at the start that can raze it.
  A unit the script takes off the map isn't given the AI's exit as well.
- **Stealing and the gem badge** (`gba_maps.mark_steals`): a thief takes only items. Every steal routine tests an item with one
  check, type (item record +7) == 9 (0x08017054): the target list (0x08025BA0, an enemy-army unit, +0xB & 0xC0 == 0x80, whose Speed,
  +0x16, is no higher than the thief's), the Steal menu (0x08024304, which reads the target's items from +0x1E and greys out the rest)
  and the steal itself (0x08024348); never a weapon, staff or monster weapon. A foe holding a rare one it doesn't drop gets the gem
  badge and a "Steal:" line: an item kept for something lasting (its use, item record +0x1E, isn't 0x1E-0x28 or 0x33-0x35: the keys,
  the Lockpick, healing and curing, the Torch) that no armory or vendor sells, the world map towns' included (a secret shop's stock
  still counts as rare). A recruit (Amelia) brings its items along: not marked.

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
