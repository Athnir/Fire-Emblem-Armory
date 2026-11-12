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
| +8 | Attributes (u32): 0x02 magic, 0x08 unbreakable, 0x20 brave, 0x40 the Light Brand's 10 damage from 2 tiles away (below), 0x80 can't be countered (ballistae), 0x100 reaver (read in the battle code at 0x08025A90), 0x400 / 0x800 / 0x1000 / 0x2000 locks (Manaketes, Roy, Myrmidons and Swordmasters, Zephiel) |
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
- **The Light Brand** (0x40, item 8): the weapon setup (0x080246E0) gives it the light type at range 2, which the triangle reads
  (0x08025AA2), and clears the battle's copy of 0x40 at range 1. Where the copy is set, 0x08024A1C runs after the attack, the
  target's defence and supports are in, and sets its attack to 10, the target's defence to 0 and its crit to 0: 10 damage whatever
  the Mt, Str and Def or Res, and the triangle changes only its hit. The target's defence (0x08024844) is Res only for the magic bit
  (0x02), so next to its target the Light Brand is a sword like any other. The Runesword (125) has neither bit: a sword at either range.
- Not confirmed: the other attribute bits, read off the items that carry them (only the magic bit, 0x40 and the reaver bit were traced
  in code). The Poison bow
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
  berserkers climb it), `wn` Valley (Chapter 8x: fliers and dragons only), `om` Armory, `on` Vendor, `oo` Arena, `ot` House
  (Avo 10 like a village, but not on the raiders' terrain list, 0x085C864C, so no looter goes for it).
- Not used: each class's fifth row (+0x44: Brigand +5 on mountains and peaks, Pirate on water, Berserker both, Priest on churches,
  the King on gates and thrones). No code that reads it was found, so it isn't shown.

- **Ground by map** (`scripts/gba_ground.py`, shared by the three GBA games): plain (1), road (2), floor (23), flat (42), glacier
  (47) and deck (62) have the same stats but are codes of their own (`t0`, `tl`, `t1`, `t7`, `t6`, `t3`), and each map gives its own
  colour for its ground and water codes (`fills`): the blend of the five colours its tiles' pixels show most in the chapter's palette
  (a pixel of colour 0 shows bank 0's colour 0), water its blue pixels' average, softened (saturation × 0.75, value × 0.85); water
  within 40 (RGB) of the map's plains is drawn stronger and lighter or darker away from them (The Sacred Stones' River of Regrets: a dry
  yellow riverbed in green grass). Checked against Fire
  Emblem Wiki's screenshot of The Sacred Stones' Chapter 2 (its grass the same teal green, #68c8a0).
- **Buildings drawn whole** (`gba_walls.place_pieces`): each run of village walls (46) and each castle building (44 entered by a
  gate or a throne) is a building, its tiles its pieces by place (`va`-`vi`, `ca`-`ci`: top, middle and front rows, left to
  right), from which sides the building goes on past each; a run three columns per building with an entrance under each middle
  one is several (The Sacred Stones' Chapter 2's two villages). Across the three games villages are mostly 3 x 3 or 3 x 2 and
  castles 3 x 3 or 3 x 2, their entrance or gate in the front's middle.
- **Walls by kind** (`scripts/gba_walls.py`, shared by the three GBA games): the walls no unit enters are drawn by what they are on
  the map, by look at the real art of every wall tile each tileset puts on a map (the chapter record's graphics, palette, tile config
  and map, drawn the way the game builds the map): castle, ruins, temple, sandstone, snow, wood; a roof (34), the void around some maps
  (0, unnamed); a village's houses and walls (46, unnamed) and a ship's sides (61), which fliers cross, have codes of their own. A
  wall (26, 27, 63) takes its tileset's kind, or its chapter's where the chapter's palette makes the same tiles another kind; a
  building of 44 (unnamed, rare: a castle on an outdoor map) takes its entrance's kind, a gate or throne a castle's, a village, house
  or shop a village's, through the village's 46 around it. Only snags stay plain walls (fallen trees until broken).
  The Binding Blade's tilesets (+8): 1, 18, 33, 44, 51, 62, 69, 122, 129, 165, 177 castle, 83 sandstone (Chapters 12x and 14, its
  impassable edge drawn as grass and sand, metatiles below 500, the void), 102 and 115 snow (Ilia: Chapters 18A to 20Ax), 142 temple
  (16x, 24, the Final Chapter).

## Chapters: 0x6637A0, 68 bytes each (`scripts/build-fe6-maps.py`)

- +8 to +0xF are indices into the pointer table at 0x664398 (the map at +0xC, the tile config at +0xB); +0x10 the fog vision (0 =
  no fog); +0x11 how many units you deploy (0: no preparations, the chapter places your army); +0x17 Hard's levels (below); +0x34 the
  goal text; +0x3E the event data; +0x40 the location text. The game's own lookup (0x0802BB0C) starts the record 4 bytes in.
- **Hard's levels:** on Hard every foe gains +0x17 levels' worth of its class's growths in HP, Str, Skl, Spd, Def, Res and Lck
  (0x080178F4 -> 0x08017854), its shown level unchanged: 4 in Chapters 1 and 2 up to 16 in the Final Chapter, 0 on the trial maps.
  Once the starting group is placed (0x0806B604), the pass over the foes (0x0806BAF0) takes a character's own number from the list at
  0x08666C78 where it has one (0 for the 15 characters you can recruit from a foe: Raigh in Chapter 12, Perceval in 13, Douglas and
  Hugh in 16 are starting foes there); a foe an event places gains the chapter's number whatever the list says (0x0800CD3E). The maps
  say both on Hard. A promoted foe the game levels always gets 19 extra levels' worth (0x08017928), on either difficulty.
- **Fog lifting:** Chapter 14's turn-26 script calls 0x0806BFC1, which sets the fog's vision to 0 (0x0801C6C4); no other script
  changes the fog.
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
  0x40 other, 0x80 enemy); **3 the same on Hard only** (0x0806A9DC: the chapter state's Hard bit), while flag 2 (the boss's
  fall: below) is clear; 4 two
  characters talk; 5 a house or seize tile, 6 a village, 7 a chest (the item, or gold << 16 | 0x6F), 8 a door, 10 a shop (0x13
  armory, 0x14 vendor, 0x15 secret shop; the script word points at a u16 item list); 11 an area; 13 a check routine.
- **Flag 2 is the boss's fall:** a death quote (the table at 0x08666598: 16 bytes, character, chapter (0x2D any), text, the flag
  its death sets; read by 0x0806B808, which also sets 0x65, game over, when Roy dies) sets flag 2 for 35 bosses (Dory, Slater,
  Wagner...). So a Hard-only turn event stops once the chapter's boss is defeated, and so does any group whose script skips its
  load once flag 2 is set (`0x22`, Chapter 5's area event); the map says which boss ("until Dory is defeated"), naming every
  boss the chapter places whose death sets it (Chapter 13: Flaer, Narcian or Zephiel). The same table names the map's skull
  (`scripts/gba_bosses.py`): a boss whose death doesn't set flag 2 (Rose and Maggie in Chapter 14, 20B's clan chiefs, Peres in 21)
  or who leaves the map before the chapter ends (Flaer in 12; Narcian and Zephiel in 13, where the returning Narcian holds the
  gate) is a named foe. The trial maps' 'Bandit' is an army name (22 characters share it), so its boss goes by its class.
- **Cracked walls** (terrain 27): 0x08026C66 makes one obstacle at the top of each wall's column, with the chapter record's wall
  HP (+0x1D: it reads +0x19 of the record from 0x086637A4, four bytes on); breaking it makes the map change under its tile. 45 in
  9 chapters, 40 or 100 HP, each previewed broken.
- **Map changes** (the chapter record's +15, an index into the pointer table): 12-byte records up to an id of 0xFF (id, x, y,
  width, height, 3 unused bytes, a pointer to u16 replacement tiles; a 0 tile leaves its tile as it is). Read by
  `scripts/gba_doors.py`, which The Blazing Blade and The Sacred Stones share. A door (type 8) applies the last change whose
  rectangle holds its tile (the lookup at 0x08026E54 keeps the last match, as The Blazing Blade's and The Sacred Stones' do); a scripted door (type 5 with the door command 0x10: Chapter 6's upper rooms) and any other script
  apply the changes at the tiles its `0x2A` commands name. A room drawn under its roof (terrain 34) that a change opens is a
  closed room (`ws`) until then: Chapter 6's eight rooms (Sue waits in one), Chapter 3's throne room (turn 3, enemy phase, as
  Slater arrives) and Chapter 22's temple (an area). An opening's changes are made before the battle (Chapter 1's raided
  village starts as ruins, terrain 37); the rest are previewed with what sets them off (Chapter 5's south-western wall opens
  as one of your units enters the area beside it, on both difficulties; Chapter 17A's shore on turn 6; Chapter 19B's door and
  fence on turn 12).
- **Turns' changes, in turn order** (`gba_doors.in_turn_order`): a change a turn's script makes (`turn` on it) is made on the map
  as the turns before left it, its patch the tiles it changes from that, so the app steps through the map's states.
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
- **Talks:** who can talk to whom, and whether it recruits (side change to yours, 0x2B to 0), turns the character green (0x2B to 64,
  the other army) or only talks. A recruit only on a branch the plain run doesn't take says why: Hugh for gold (by what you hold),
  Cath on the third talk. 0x2B changes every unit of the character (0x0800FDA8), so the other characters a recruit's talk sends green
  are its squad, counted where they first stand and noted on each unit (Klein's four Archers, Thea's four Pegasus Knights, Perceval's
  Cavaliers and Sniper). A coded talk's check asks more first (`check`: a flag, a character still another army's through CHAR_ON_MAP
  or yours through ALIVE): Shanna's three with Thea in 10B and 11A (0x0806BB35/69/9D) talk while Klein is a foe, then recruit once
  Klein is yours after that talk, or only turn Thea green without it. Talks are matched by name, since a foe version of a character
  has its own id.
- **Villages and houses:** the items, gold or recruits their scripts give, per visitor where the script asks who's visiting
  (Chapter 10B). A village the opening closes (map change on it or the tile above: Chapter 1's raided village) is left out; a
  village that closes another says so (Chapter 9's pair, which also picks 10A or 10B).
- **Hidden items** (Chapter 14's sand): area events that give an item. Anyone stopping in the area on your phase: a thief always
  finds it, anyone else when a random number divided by 11 leaves 0 (0x0806D028); the Guiding ring only for Sophia.
- **End of chapter:** items handed to a character (Durandal, the Binding Blade) and who joins (Fa, so her stone counts from the next
  chapter). Each gift is yours from the next chapter (kind `event-later`), as are a talk's gift mid-battle (`talk-later`: Lilina's
  Thunder) and what a foe a talk recruits carries (`kit-later`: Raigh's Nosferatu, Perceval's lance and sword); an opening's gift
  would be `gift`, from its chapter (none here).
- **The story:** the end scripts' "go to chapter" commands and their checks give the gaiden conditions and Chapter 9's split
  (flags 7 and 8: the two north-eastern villages). The 17A / 17B split is a code check (0x0806C5A8); its wording is Serenes
  Forest's (Thea and Juno's EXP against Sue and Sin's).

- **Groups and when they come** (`gba_maps.one_per_arrival`, shared with the other two games): what one event places on each
  difficulty is one group, a unit only some difficulties have marked; the same units on the same tiles from events of their own are
  one group whose time lists each, per difficulty ('Turns 4, 6 and 8'); groups that come at the same moment, set off the same way, are
  one; the same units placed twice at once stay two. An area is checked after each unit's action, any army's (0x0806B500 from
  0x0801B9B2 and 0x0802D2AC), against that unit's tile alone (0x0806ABD0); an area whose script goes on only on your phase
  (YOUR_PHASE, 0x0806C4D9) and otherwise clears its own flag is set off by one of your units, any other by a unit of any army. Coded
  checks read: Chapter 24's six (the enemy phase, one seize point taken and the next not, even or odd turns, and flag 17, which no
  event sets: under the map's unconfirmed notes), Trial 4's (no unit of another army left; that and the Berserker beaten). A flag's
  group names the events that set it, the areas drawn (Chapter 7); seize points, houses, villages, doors and chests by name.
- **Looters and leavers** (`scripts/gba_ai.py`, the same engine in all three games): a unit's second AI byte (record +0xD, copied to
  the unit at 0x08030A92; scripts from 0x085C9748) picks a movement script; command 0x10 goes for the nearest village it can reach
  (terrain 3, 0x24) and, for a unit holding a Chest Key, or a Lockpick with its class's lockpick ability (bit 2), a chest (0x21); 0x17
  makes for the nearest of the chapter's escape points (0x085C86B8 / 0x085C876C: foes', then other armies', per chapter) and leaves
  the map. Second AI byte 0x04 loots, then attacks; 0x05 loots, then leaves; 0x0C only leaves. A looter gets the torch badge and says
  what it goes for (only what the map has); one that leaves names its exits (`goesTo`, staircases among them); a village names the
  looters on the map at the start that can raze it. A unit the script takes off the map isn't given the AI's exit as well.
- **Stealing and the gem badge** (`gba_maps.mark_steals`): a thief takes only items. Every steal routine tests an item with one
  check, type (item record +7) == 9 (0x08016D34), so never a weapon, staff or dragonstone; the target list (0x0802156C) takes any
  enemy-army unit (+0xB & 0xC0 == 0x80) holding such an item, with no Speed check. A foe holding a rare one gets the gem badge and a
  "Steal:" line: an item kept for something lasting (its use, item record +0x1E, isn't 0x20-0x28: the keys, the Lockpick, healing and
  curing, the Torch) that no armory or vendor sells. The crests and stat boosters only the secret shops of Chapters 16 and 21 sell
  still count. Foes drop nothing here, so what they hold is stolen or lost. A recruit (Klein, Hugh) brings its items along and the
  trial maps keep nothing: neither is marked.

Checked against outside sources in `src/logic/__tests__/fe6.test.ts`: every map's starting enemy count against the Fire Emblem
Wiki's chapter data (all 43 match), chests, villages and the sand's finds against Serenes Forest's item-locations page.

## Battle code

- **Weapon triangle** (`scripts/build-triangles.py`): the triangle table's literal at 0x08025A9C (0x085C61C0); +10 hit and +1 Mt,
  the other side −10 and −1. Anima beats light, light beats dark, dark beats anima. A reaver flips it when only one side holds one.
- **Supports** (`scripts/build-fe6-supports.py`): the affinity table at 0x0866350C, eight bytes per affinity (id, Atk, Def, Hit,
  Avoid, Crit, Dodge). For each partner within 3 tiles: both rows times the level (C 1, B 2, A 3), summed, then halved once and
  rounded down (0x08022E3C). Levels at 61, 121 and 201 points; five levels at most per unit.
- **Hit:** two random numbers averaged (2RN), as the true hit page's 2RN system.
