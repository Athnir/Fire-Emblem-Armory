# Mystery of the Emblem (FE3) game files

Read from the user's own cartridge image: `Fire Emblem - Monshou no Nazo (J) (V1.1).smc` (Super Famicom, revision 1.1, the one the
translation patch is made for; 3 MB, no copier header, CRC32 A427B7E6). The image stays on the user's PC (default path in
`scripts/fe3_rom.py`, or set `FE3_ROM`) and is never committed; only data built from it is. The cartridge is LoROM: `$BB:AAAA` is file
offset `(BB & 0x7F) * 0x8000 + (AAAA & 0x7FFF)`. Data is little-endian.

No disassembly of FE3 was available, so every table below was found by tracing the game in Mesen 2 (a new game to Chapter 1, its
work RAM watched and dumped) and reading the code that uses it (`scripts/fe4_asm.py`'s disassembler, run with the LoROM mapping). The
translation patch's public build files (`FE3_buildfiles_v1.2.zip`, from [fe3-translation](https://github.com/RobertTheSable/fe3-translation))
gave the addresses of its own text tables and its text encodings.

## Names (`scripts/fe3_names.py`)

English names are the translation patch's (`FE3_patches_v1.2.zip` next to the ROM: RPGuy96 and VincentASM's translation, Quirino's
update, Robert of Normandy's current project). `Translation_Only_E.ips` is applied in memory and only its text is read, by the ROM's own
ids; nothing patched is written.

- Characters (by name id) and classes (by class id): the menu tables at `$F0:8000` and `$F0:889C` (u16 pointers, bank `$F0`; the menu
  font's u16 codes, 0xFFFF ends, 0xFFFD a new line). The class menu shows 7 letters ("ArmrKnt"); they're spelled out as the patch's
  class roll and descriptions spell them ("Armor Knight"), and the women's classes of a pair (Knight 6, Mage 0x17, Bishop 0x18) get
  "(F)": their weapons differ.
- Items: the storage messages at `$8E:8C4A` (u16 pointers, bank `$E7`; "Iron Sword was sent to the storage."), one per item id, give
  the patch's full names (its menu shows "Iron" with a sword icon). "Staff" is dropped from the staves' ("Heal Staff").
- Chapter headings and titles: the status screen's at `$F0:A352` ("Book 1 Chapter 1" / "Marth Embarks"; the user's call over the save
  list's "Endgame" names); objectives at `$F0:AFA6`. Book 1's last is its Chapter 20, and Book 2's last four maps (chapters 41-44)
  are all its "Final Chapter", so the app numbers them part 1 to part 4. The map ids keep the old names (`fe3-1-endgame`,
  `fe3-2-e1`, `fe3-2-e2-1` to `-3`).

## Items (`scripts/build-fe3-items.py` -> `src/data/fe3/fe3Weapons.ts`)

14 bytes per item at `$88:A6E9`, from id 0 (the Iron Sword): +0 type (a bit each: 1 sword, 2 lance, 4 bow, 8 staff, 0x10 tome, 0x20
item, 0x40 axe, 0x80 breath; 0 a ballista; the Levin Sword is 0x11), +2 weapon level (bit 7 set: a lock, the low bits its number),
+3 Mt (a staff's own id), +4 Hit (a staff's EXP), +5 Crit, +6 Wt, +8 uses (0xFF never breaks), +9 u16 price in tens, +11 range in the
low nibble (9 = 1, A = 2, B = 1-2, C = 3-10), +12 the class list it's usable by, +13 its effectiveness list.

- **Hit** (`$83:B400` and on): Skill x 2 + the weapon's Hit (held at 140) − the target's avoid (Speed + Luck + terrain + support
  bonus), held between 0 and 100. The roll (`$93:EA87`): a random byte times 100, the high byte (0-99, not evenly: some numbers come up 3
  times in 256, the rest twice); a hit when it's at or below the displayed hit (`$83:B836`).
- **Damage** (`$83:B4D7`, `$83:B52E`): Str + Mt (the game has no Magic stat), against Def; a weapon whose type has the tome bit (the
  tomes and the Levin Sword) against Res, with no terrain avoid for its target (`$83:B418`); a breath against nothing, unless its
  target fights with a breath too. Dark Breath halves its opponent's attack (`$83:B15E`). Your unit's tome strikes do nothing to the
  Shadow Dragon (class 0x2A, `$83:B111`).
- **Effectiveness** (`$83:B380`, `$83:B395`): Mt (held at 33) is tripled; the attack is held at 99. The lists: u16 pointers at
  `$88:A633` by the item's +13 (60 entries, the weapons), each a list of class ids ended by FF. None against a unit holding Iote's
  Shield or the Lightsphere (`$83:B364`, the flags `$83:C11F` sets from its item slots).
- **Locks** (`$83:EF20`): a weapon whose level has bit 7 set is for the name ids in its list (u16 pointers at `$88:A48E`, ended by
  FF). Otherwise the unit's weapon level must reach it.
- **Who can use it** (`$83:EEB4`): every item has its own list of class ids (u16 pointers at `$88:A4B1`, by +12, ended by FF). The Lady
  Sword's is the women's Knight and the Dancer; Resire's the women's Mage and Bishop.
- **Weapons the battle code treats by id**: the Devil Sword and Axe turn on your unit wielding them when a 0-99 roll is below 21 − Luck,
  never a foe's nor one holding the Lightsphere (`$83:B1A3`); the Levin Sword's attack is its Mt alone (`$83:B4B4`); the Mercurius Sword, Gradivus and Parthia double the EXP (`$83:C102`,
  held at 99); a unit holding Imhullu can be hurt only by Starlight (`$83:B28D`); Dulam leaves 1 HP (`$83:B720`); Resire restores its
  damage to the wielder (`$83:B8CD`).
- **Dragonstones** (the user's call: each stone with the breath its dragon fights with): the stones at `$83:84A6` make the classes at
  `$83:849F` (`$93:D305`), each class fighting with its breath at `$83:84AD` (`$93:D2C4`; a Divine Dragon's Mist Breath is Ice Breath
  before chapter 21). Using one (`$83:CF72`) costs a use, doubles HP and max HP (held at 52) and lasts 5 turns plus a random 0 to half
  the user's Luck (the menu's count, FF; a foe's AI sets its own). The breaths aren't listed on their own. Medeus's Earthstone is
  foe-only; no unit carries the Darkstone.
- **Ballistae** (type 0): the Shooters' (class 0x23, Mov 0 at `$88:906C` + 9 a class + 3), foe-only.
- **Broken weapons** (`$83:C054`): a sword, lance, bow or axe whose uses run out becomes the Broken one of its type (a tome or staff is
  used up), so each is listed from each book's first chapter. Aum's second record (5 uses where the first has 1) is "Aum (5 uses)",
  on the maps too.
- **Selling** (`$87:9540`): half the value of the uses left, in tens (the price is kept in tens), rounded down, at least 10; an item
  whose +11 has bit 7 set can't be sold (the Falchion and Starlight, which have no price either).
- **Staves** (handlers at `$83:C4F3`, by item): Heal restores 10 + its user's Str, Mend 20 + Str, Recover the target's max HP,
  Fortify 10 + Str to every ally; MagShield gives Res +7; Hammerne skips a weapon with no price or full uses; Silence stops tomes
  (Imhullu aside) and staves for both armies. The rest of what each does, and their ranges, are Serenes Forest's (its Mystery of the
  Emblem staves page), matched to the ROM's level, uses and price first, in the app's own words. The ROM's Again costs 10000; Serenes
  says 9980.

## Battle and supports (`scripts/build-fe3-supports.py`)

- **No weapon triangle**: nothing in the hit or damage code looks at the two weapons' types against each other.
- **Supports** (`$83:B9E1`): every unit within 3 steps, of either army (a pseudo-class, 0x2E, that pays 1 everywhere) adds the bonus of
  each entry of `$88:CD31` (giver name id, receiver name id, bonus; ended by FF) naming it as giver, and 10 if it's of the same side
  and carries the Geosphere (items 0x3C or 0x6B; `$83:BA41` asks the side for the Geosphere alone). The total goes to hit, avoid, crit
  and crit avoid. Avoid (Speed + Luck + terrain + the bonus) and crit avoid are 8-bit sums: 128 or more wraps to 0, and each is held
  at 100 (`$83:B451`, `$83:B5B8`).
- **Terrain healing** (`$93:DF10`, at the start of a phase): a unit carrying the Lifesphere (0x6C) is healed fully; one on a terrain id
  of groups 0 or 1 of the list at `$88:CB7A` (castle gates, thrones, forts) recovers 3 + a random 0-6 HP.
- **Chapter 6** (`$83:B96E`, run before every strike's roll at `$83:B82B`): while the battle's enemy-side unit (its name id at
  `$0764`) is Minerva, Palla, Catria or Est (0x1E, 0x2F, 0x1C, 0x2A), every strike misses, theirs too.

## Maps (`scripts/build-fe3-maps.py`)

- **Chapters**: the chapter number (`$07DF`: Book 1 is 1-20, Book 2 21-40, Endgame 1 41, Endgame 2's three parts 42-44) picks the map
  index (`$07CE`) through the byte table at `$84:8C15`. Everything else is by map index.
- **Header** (`$8A:8000`, 8 bytes per map; `$93:E5C1`): +0 graphics, +1 tileset, +2 the last column, +3 the last row. The cursor never
  goes onto column or row 0, nor past last − 1 (`$83:D822` and on), so the playable map is the stored one without its outer ring.
- **Altars** (terrain 98, 155): no unit moves onto one, but the Endgame places its Earth Dragons there (and its spawns bring more): the
  summoning sigil's code, its stats kept.
- **Grid** (`$89:CAB1`, 3 bytes per map: a long pointer whose bank byte is stored less 0xA4): compressed; the game's decompressor
  (`$80:8F18`, run by `scripts/fe4_cpu.py`) gives 32 x 32 u16 cells, the low 10 bits the metatile. The terrain of each metatile is the
  tileset's table (`$8A:81F8`, a long pointer per tileset, 1024 bytes): one of 162 terrain ids.
- **Map art** (`scripts/fe3_art.py`; traced at `$83:8851`-`$83:8A72` and checked against Mesen's VRAM and CGRAM in 14 chapters
  covering all 12 graphics sets): by graphics set (header +0), `$89:C9A3` its 4bpp tiles (compressed; tiles 0-447 reach VRAM),
  `$89:C9C7` tiles 448-511 (animated, 8 frames of `$800`), `$89:CB6E` its metatiles (compressed, 1024 x 4 BG map entries); by tileset
  (+1), `$89:C9EB` its palette (palette 0 then `$94:D080`, 5-7 `$95:F800`; colours `$37`/`$38` cycle through 16 frames at `$89:CA4E`
  + `$3000`, drawn at each one's most frequent). Each table is long pointers whose bank byte is stored less a constant (+`$9D`,
  +`$97`, +`$A2`, +`$CB`). Each map's colours (`fills`): the median of each code's tiles, softened as the Tellius minimaps' are. Walls
  ("Blocked") are drawn as what they are (`wall_kinds`): a small building over a village's entrance the village's (`w2`), one over a
  castle gate on open ground a castle drawn whole round its gate (`ca`-`ci`), any other a castle's walls (`w0`) in its map's stone.
  Tiles drawn as their art shows them, keeping the stats of what the game calls them (`tile_looks`, the first three games' review,
  2026-11-13): walls whose art is black (median lightness at most 0.02, its 90th percentile at most 0.12: no brickwork lit) and the
  near-black walls joined to them (0.06, 0.2) are the void (`wy`: the Book 2 Endgame's dark); a map whose peaks are mostly black has
  them as a cave's rock (`wt`: Book 2 Chapter 12); floors at most 0.6 as light as the map's floors' median are another level (`ge`),
  where there are six or more and the median is at least 0.15 (Book 2 Chapter 6's dark halls; not the Endgames, dark all over);
  graphics set 2's metatiles `$1A9` and `$1AA` are a skull in the sand (`decor` bones: Book 2 Chapter 11). Every kind on a map takes
  its colour, one tile or many (Book 2 Chapter 10's lone path tile).
- **Terrain names**: the first line of each id's terrain window (the patch's table at `$F0:B08E`, u16 pointers in bank `$F0`), the four
  it shortens to fit in full (Corridr, Drawbrg, Waterfl, Mount). Walls are "Blocked". A code whose tiles the game names otherwise
  on a map says so, and one with several names there lists the tiles with each (Book 1's Chapter 8: Cliff, Corridor; the Endgame's
  Altar under Medeus). The window's other lines are labels, not the tables: an opened chest leaves a floor its window calls Recover
  (Avo 30), but the healing routine reads only groups 0 and 1, so it doesn't heal.
- **Terrain stats**: avoid per class (long pointers at `$88:C29E`; fliers point at an all-0 row), movement costs per class (long
  pointers at `$88:B383`, 162 bytes, 0xFF can't enter). No Def from terrain, and no terrain avoid against a tome or the Levin Sword (the
  hit routine leaves it out for a weapon whose type has the tome or staff bit, `$83:B418`). Classes with the same cost row are one
  movement group (23). Codes go by what the tables say: plains Avo 5 (`tv`); floors closed to cavaliers, paladins and pegasus and dragon
  knights (`tn`, `by` with Avo 30; flying dragons enter), two open floors on no map (`ta`); pillars Avo 20 closed to mounts (`bh`),
  Book 1's Chapter 8's Avo 30 open to them (`b3`); a castle gate heals (`ol`), its flanks don't (`ou`, Avo 30 in Book 2's Chapters 12
  and 13: `bv`); rubble is rough ground (`tm`, 2 a tile); houses are stood in (`ot`); tunnels Avo 25 (`tp`). A map using a variant of
  a code that works differently from the game-wide one gets it as a terrain override; a map with two variants of one code is allowed
  only where they differ for movement groups none of its units belong to (Book 1's Chapter 8 pillars).
- **Units**: 19-byte records ($83:DCC1): +0 character, +1 class, +2 level, +3 name id (the name shown), +4 row, +5 column, +6 the class
  it changes into, +7 portrait, +8..+11 weapon slots, +12/+13 item slots, +14 u16 gold, +16..+18 AI. Lists ended by FF:
  - `$89:8000` (u16 by map): placed as the chapter loads ($93:E4A7), all foes.
  - `$88:8000` (u16 by map): the chapter's list, loaded by character by its scripts (the first record with that character).
  - `$88:9D6D`: the units the spawn slots bring in.
  What a foe has in its item slots, and its gold, are what it leaves when it falls (`$83:AE1B` stores them as the battle's spoils): the
  drops. Generic foes share character 0x45; their name id is their army's ("Galder"), one that three or more of a chapter's units
  share and none of your army has. A name whose every unit wears a person's own portrait is that person's several versions, not an
  army: Gharnef's five doubles in Book 1's Chapter 18 (name 0x60, his portrait 0x4E) are named foes.
- **Bosses**: the game's own list of boss name ids at `$93:FEB5` (checked by the loader at `$83:DF7D`), for both books. A talk recruit
  on it is the chapter's boss only when no one else on the list is (Sheena; not Lorenz in Book 1's Chapter 16).
- **Your army's starting tiles** (`$89:C45C`, u16 by map): [count] then [row][column] pairs. Marth stands on the first.

## Events (`scripts/fe3_events.py`)

Scripts are byte commands dispatched by `$87:81C9` through the table at `$87:81E1` (51 commands; lengths and meanings in
`fe3_events.py`). Jumps are u16 within the script's bank. Where a script starts, by kind (`$83:8EC8` runs them at a phase's start):

- **Turn events** (`$8C:A11C`, u16 by map): [turn u16][phase][script u24]..., ended by FFFF. The first that matches the turn and phase
  runs ($87:9B68). Turn 0 runs as the chapter loads; turn 1's for your phase is the opening scene.
- **Area events** (`$8B:802E`): [who][column from][to][row from][to][script u24], ended by FF: who FC is any of your units, FD any
  enemy, FE anyone, else that character. Run after a unit moves.
- **Character events** (`$8B:85E0`): [character][script u24]..., ended by FF: run at a phase's start once that character is gone.
- **Spawn slots** (command 0x1C: [slot][count][chance %][column][row][reinforcement unit]): at the start of every phase but yours
  ($87:9DB2), each slot with a count left rolls its chance and, if its tile is free, brings in its unit and counts down. The maps make
  one group of the slots one event fills alike (the same count, odds and stop: Book 1's Chapter 8's turn 15 fills eight), and one of
  what an event loads at once; an area event's groups show its area, held to the playable grid.
- **Tile events** (`$8C:917C`, 10 bytes: [map][who: 0 your army, FF anyone][column][row][condition][kind][event id u16][u16]): kind 0
  a house, 1 a shop (its SHOP command: [shop][type: 0 armory, 1 vendor, 2 secret shop]), 2 the arena, 3 a village, 4 the seize tile,
  8 a secret shop (on an ordinary tile). Their scripts: u16 pointers at `$8C:8004` by event id (bank `$8C`). A record whose condition
  isn't met is skipped; of the seize records, the last one met wins.
- **Chests, doors and drawbridges** (`$8C:9AD3`, the same format): kind 7 a chest (its script gives the item or gold), 5 a door, 6 a
  drawbridge. The record's last u16 is the metatile written onto its tile once it's opened (FFFF: none; `$83:C8C5`), before its script
  runs. A door opens for a Thief (class 0x13) of either army (`$83:E776`; the AI uses the same check, `$82:8DE4`) or a unit holding a
  Door Key (0x58, `$83:ED91` -> `$83:E79F`); a drawbridge lowers for a Thief (`$83:E626`) or a Bridge Key (0x5A, `$83:E64F`).
- **Map changes**: SET_TILE (command 0x21: [flag][column][row][metatile u16]; flag 0 skips a tile a unit stands on, `$87:A079`) writes
  one tile; SHOW (command 0x05: [number]; `$83:F204`) writes a block change from the table at `$89:CBA0`: 3 bytes per number, a u16
  address and its bank stored less 0xA6. A change is a list of blocks, each a 3-byte header (column 5 bits, row 5, width - 1 5, height
  - 1 5, then a bit saying another block follows, read at `$83:F287`) and width x height u16 metatiles. The opening's changes are made
  before the battle (Book 2's Chapter 20 shows its whole castle, SHOW 0x10); the rest are previewed with what sets them off (a door,
  drawbridge or chest opened, a village visited, an area entered, a turn, a death, a talk). A seize tile's script runs as the chapter
  ends, so its changes are no battle's. A tile no unit can enter that a change makes walkable is a closed room's, drawn under its roof
  (`ws`): the cells a door's or a script's change lifts (Book 1's Chapter 15 cells, the throne rooms of Book 2's Chapters 6, 14, 16, 17
  and 20 and Endgame 2's first part).
- **Hidden items** (`$8C:9FDE`, 7 bytes: [map][column][row][condition][item][u16]; `$83:9D95`): found by a unit that waits on the tile
  or one next to it (not diagonally); a thief always finds it, anyone else on a roll below its Luck.
- **Talks** (`$8B:89C6`, 6 bytes: [map][talker name][target name][condition][event id u16]): scripts at `$8B:8A93` by event id. A
  talk whose script swaps a unit for a record of the chapter's list (command 0x0D: [?][the record's character][the unit's character])
  recruits the unit it takes off: the target, or the talker where a foe starts the talk (Book 1's Chapter 11: Catria and Palla talk to
  Marth). What joins is the record swapped in, by its own name (Book 2's Chapter 6: the foe called Navarre joins as Samuel).
- **A scene's cast**: what an event loads (command 0x0C) and takes off again (0x0B) never stands on the map (Book 2's Chapter 1:
  Ogma and Catria; Chapter 3: two Pallas; Chapter 14: Gotoh's scene records). What joins, or is given, during or after a battle counts
  from the next chapter (the last chapter's from itself); ITEM with unit FF gives it to the unit acting (`$87:9AF5`): Marth, who
  seizes.
- **Conditions** (`$87:AAA7`): a long pointer per number at `$8C:A04F`, each a list ended by FF of [type][byte] (type 1 alone takes a
  u16): type 0 the acting unit holds the item, 1 the flag is clear, 2 the character is on the map, 3 it's in your army and alive, 4
  your army holds the item, 5 the chapter is at least the number (`$87:ABA7`; no condition uses it). A record's condition byte 0
  names an empty list and FF none at all (`$83:E53F` skips the check). A flag a condition wants clear is named by what sets it: the
  opening sets Book 1's Chapter 8 flag 4 and Marth's talk with Maria clears it (so Minerva's talk waits for Maria to join); deaths set
  Book 2's Chapter 17 flag 18 (Sheena's talk lasts until Samson or any Soldier or Archer falls); a flag only the talk itself sets is
  its once-only flag. What an opening places on a condition (IF_FLAG, IF_PRESENT) is found by playing it again with the check turned
  the other way: Catria and Palla only with Minerva in your army (Book 1's Chapter 11), Rickard only if Julian didn't talk to him in
  Chapter 5, Jeorge only if he wasn't defeated there (Book 2's Chapters 6 and 8: flags carried from Chapter 5).
- **Who leaves**: a script after the opening that takes a unit off (REMOVE) says when: on a turn (Book 1's Chapter 6 four on turn 2;
  Gharnef in Chapter 12 on turn 4, so he only passes through, a named foe, and his Falchion, which he can't be made to drop before,
  isn't a source there), in a talk (Lorenz goes with Marth's) or once someone falls (the Earth Dragons with Medeus).
- **Events' items**: what an area, death or turn event hands out, and on what (IF_NO_ITEM, TAKE_ITEM): Hardin's death trades the five
  spheres for the Binding Shield (Book 2's Chapter 20, `$8B:8919`), and Book 2's Chapter 14 gives the Lightsphere, and the Starsphere
  for the twelve star shards. The Endgame opens on Book 2's Chapter 20's second seize record, condition 11: your army holds the
  Binding Shield (the first, with none, ends the game: BOOK_END).
- **Shops** (`$8C:9044`): 8 item ids per shop, padded with FE.
- **Paths** (command 0x09: four u16 pointers to [op][value] lists ended by FFFF): op 0 picks the unit, 2 its direction (0 left,
  1 right, 2 up, 3 down), 5 moves it by pixels (16 a tile), FF 02 sets it down where its walk ends, FF 03 leaves it walking on: a
  unit still walking when the camera scrolls keeps its place on the screen, so it lands that much further along the map (Caeda in
  Chapter 1).

## AI (`scripts/fe3_ai.py`)

A unit record's +16..+18 are its AI (copied to the unit's +0x18, +0x1A and +0x1C, `$83:DD53`). Each enemy phase a unit runs its
decision script, then, if that settles nothing, its movement script (the driver at `$82:8000`, states 4 and 5). Only a decision
attacks: every movement command ends with action 0x0B, wait (`$82:970F`).

- **Decision scripts** (AI1; u16 pointers 3 bytes apart at `$88:C46C`, bank `$88`; `$82:85B1`): a byte below 0x10 is an attack
  decision with one operand (`$82:8AA8`), 0x10 and 0x11 are attack decisions too, 0x14 [chance] attacks only that % of the time, 0x12
  ends the script, and 0x13 [character][talk][0] walks the unit to that character, while it's on the map, and starts that talk
  (`$82:8711`; the talk id is the talk table's). Script 0x02 is a lone 0x12: a unit with it never attacks (the thieves, Pyrathi, Book
  2's waiting armies). An AI1 of FF is no AI.
- **Movement scripts** (AI2; u16 pointers 3 bytes apart at `$88:C5E1`; `$82:8C63`, commands at `$82:8CCE`): 0 [n] back n bytes;
  1 [name][moves] hold while a unit of that name is on the map (`$93:D52E`); 2 [class group][moves] advance on the nearest unit of the
  group, FF any (`$82:90EE`; the class groups at `$88:CBD4`); 3 [moves] stay (it heads for its own tile); 4 [group][moves] the nearest
  tile of a terrain group by its class's movement costs, leaving out tiles another unit stands on (`$82:91AB`); 5 [column][row][moves]
  go to that tile, then the next command (`$82:9040`); 6 [n][0] run leave script n (u16 pointers at `$8B:91F7`: a walk off the map,
  then REMOVE; Book 1's Chapter 8's script 25 opens a door instead, SET_TILE); 7 [0] use a staff (`$82:8E6C`); 8 [n][0] loot: the
  nearest village (terrain group 3) or chest (group 9) it can reach, razed (action 0x17, `$83:9A34`) or emptied (action 9), and after n
  chests, or with none left, the next command (`$82:8D2F`); 9 a Manakete's change. [moves] is how far it may move in a turn: 0 holds
  it still.
- **Terrain groups** (`$88:CB7A`, FF-ended lists of terrain ids, the table ended by an empty one; `$82:9834`): 0 castle tiles and
  thrones, 1 forts, 2 tunnels, 3 villages, 4 shops, the arena, altars and floor 156, 5 houses, 6 mountains, 7 bridges (terrain 4 alone), 8 forests and
  pillars, 9 chests, 10 drawbridges, 11 doors, 12 plains. A boss's AI takes it back to the nearest castle tile (Gazzak, whom Chapter
  1's opening walks out of his castle); a throne under a closed room's roof is read under the roof.
- **New AI** (event command 0x18 [AI1][AI2][AI3][character]...FF, `$87:9BC0`): every unit of each character on the map, FE every
  enemy, gets the AI from the start of its scripts. The maps say what sets it off: a turn, an area, a death, a talk or a village visit
  (Book 2's Chapter 18: Marth's visit sends the Wolfguard off the map). Generic foes share character 0x45, so one command can reach a
  whole army (the Book 1 Endgame's foes stop moving and attacking once Medeus is defeated).
- **Looters**: a unit whose movement script loots gets the torch badge; a village names the looters on the map at the start that can
  raze it. Chests a closed room hides count as goals (Book 1's Chapter 15, Book 2's Chapter 14).

Checked against outside sources in `src/logic/__tests__/fe3.test.ts`: every chapter's starting foes against the Fire Emblem Wiki's
rosters (four headline figures disagree with their own rosters; the tests say which), its bosses against the wiki's chapter list
(Tiki, a talk recruit, isn't on the game's boss list), Chapter 1's armory against Serenes Forest's shop list, and the wiki's "dropped
by" items, which are the item slots.

Not confirmed:
- Which deaths lose the game besides Marth's: the defeat check wasn't traced (no chapter has a death event for Marth; the death
  routine's flag for name 0, `$83:AECB`, only keeps a fallen Marth's items from the spoils, `$93:E8E2`).
- The staves' ranges are Serenes Forest's; the staff targeting code wasn't traced.
- Spawn slot counts: Book 1's Chapter 4 slots hold 16 each; the Fire Emblem Wiki says 17.
- The openings' walks are played as described above; positions match the game in Chapter 1 (its work RAM at the first turn), the
  rest weren't checked in the emulator.
- Three flags no chapter's script sets: 17 (Book 2's Astram waits on it in Chapters 8 and 16), 19 (Catria and Palla in Book 1's
  Chapter 11) and 24 (Book 2's Chapter 19 closes its village at (26, 3) while it's set); the maps say so under unconfirmed.
