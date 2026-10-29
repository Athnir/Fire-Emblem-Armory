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
- Chapter headings and titles: the status screen's at `$F0:A352` ("Book 1 Chapter 1" / "Marth Embarks"); objectives at `$F0:AFA6`.

## Items (`scripts/build-fe3-items.py` -> `src/data/fe3/fe3Weapons.ts`)

14 bytes per item at `$88:A6E9`, from id 0 (the Iron Sword): +0 type (a bit each: 1 sword, 2 lance, 4 bow, 8 staff, 0x10 tome, 0x20
item, 0x40 axe, 0x80 breath; 0 a ballista; the Levin Sword is 0x11), +2 weapon level (bit 7 set: a lock, the low bits its number),
+3 Mt (a staff's own id), +4 Hit (a staff's EXP), +5 Crit, +6 Wt, +8 uses (0xFF never breaks), +9 u16 price in tens, +11 range in the
low nibble (9 = 1, A = 2, B = 1-2, C = 3-10), +12 the class list it's usable by, +13 its effectiveness list.

- **Hit** (`$83:B400` and on): Skill x 2 + the weapon's Hit (held at 140) − the target's avoid (Speed + Luck + terrain + support
  bonus), held between 0 and 100. The roll (`$93:EA87`): a random byte times 100, the high byte (0-99, not evenly: some numbers come up 3
  times in 256, the rest twice); a hit when it's at or below the displayed hit (`$83:B836`).
- **Effectiveness** (`$83:B380`, `$83:B395`): Mt (held at 33) is tripled; the attack is held at 99. The lists: u16 pointers at
  `$88:A633` by the item's +13 (60 entries, the weapons), each a list of class ids ended by FF.
- **Locks** (`$83:EF20`): a weapon whose level has bit 7 set is for the name ids in its list (u16 pointers at `$88:A48E`, ended by
  FF). Otherwise the unit's weapon level must reach it.
- **Who can use it** (`$83:EEB4`): every item has its own list of class ids (u16 pointers at `$88:A4B1`, by +12, ended by FF). The Lady
  Sword's is the women's Knight and the Dancer; Resire's the women's Mage and Bishop.
- **Weapons the battle code treats by id**: the Devil Sword and Axe turn on their wielder when a 0-99 roll is below 21 − Luck
  (`$83:B1B7`); the Levin Sword's attack is its Mt alone (`$83:B4B4`); the Mercurius Sword, Gradivus and Parthia double the EXP (`$83:C102`,
  held at 99); a unit holding Imhullu can be hurt only by Starlight (`$83:B28D`); Dulam leaves 1 HP (`$83:B720`); Resire restores its
  damage to the wielder (`$83:B8CD`).
- Left out: the ballistae, the dragons' breath, the broken weapons, and everything that isn't a weapon or staff. Aum's second record
  (5 uses where the first has 1) is "Aum (5 uses)".
- The staves' effects and ranges aren't in the records: they're Serenes Forest's (its Mystery of the Emblem staves page), matched to the
  ROM's level, uses and price first, in the app's own words. The ROM's Again costs 10000; Serenes says 9980.

## Battle and supports (`scripts/build-fe3-supports.py`)

- **No weapon triangle**: nothing in the hit or damage code looks at the two weapons' types against each other.
- **Supports** (`$83:B9E1`): every unit of the same side within 3 steps (a pseudo-class, 0x2E, that pays 1 everywhere) adds the bonus of
  each entry of `$88:CD31` (giver name id, receiver name id, bonus; ended by FF) naming it as giver, and 10 if it carries the Geosphere
  (items 0x3C or 0x6B). The total goes to hit, avoid, crit and crit avoid.
- **Terrain healing** (`$93:DF10`, at the start of a phase): a unit carrying the Lifesphere (0x6C) is healed fully; one on a terrain id
  of groups 0 or 1 of the list at `$88:CB7A` (castle gates, thrones, forts) recovers 3 + a random 0-6 HP.
- **Chapter 6** (`$83:B96E`): an attack on Minerva, Palla, Catria or Est (name ids 0x1E, 0x2F, 0x1C, 0x2A) always misses.

## Maps (`scripts/build-fe3-maps.py`)

- **Chapters**: the chapter number (`$07DF`: Book 1 is 1-20, Book 2 21-40, Endgame 1 41, Endgame 2's three parts 42-44) picks the map
  index (`$07CE`) through the byte table at `$84:8C15`. Everything else is by map index.
- **Header** (`$8A:8000`, 8 bytes per map; `$93:E5C1`): +0 graphics, +1 tileset, +2 the last column, +3 the last row. The cursor never
  goes onto column or row 0, nor past last − 1 (`$83:D822` and on), so the playable map is the stored one without its outer ring.
- **Grid** (`$89:CAB1`, 3 bytes per map: a long pointer whose bank byte is stored less 0xA4): compressed; the game's decompressor
  (`$80:8F18`, run by `scripts/fe4_cpu.py`) gives 32 x 32 u16 cells, the low 10 bits the metatile. The terrain of each metatile is the
  tileset's table (`$8A:81F8`, a long pointer per tileset, 1024 bytes): one of 162 terrain ids, named in the patch's terrain text.
- **Terrain stats**: avoid per class (long pointers at `$88:C29E`; fliers point at an all-0 row), movement costs per class (long
  pointers at `$88:B383`, 162 bytes, 0xFF can't enter). No Def from terrain. Classes with the same cost row are one movement group (23).
  A map using a variant of a code that works differently from the game-wide one gets it as a terrain override; a map with two variants
  of one code is allowed only where they differ for movement groups none of its units belong to (Book 1's Chapter 8 pillars).
- **Units**: 19-byte records ($83:DCC1): +0 character, +1 class, +2 level, +3 name id (the name shown), +4 row, +5 column, +6 the class
  it changes into, +7 portrait, +8..+11 weapon slots, +12/+13 item slots, +14 u16 gold, +16..+18 AI. Lists ended by FF:
  - `$89:8000` (u16 by map): placed as the chapter loads ($93:E4A7), all foes.
  - `$88:8000` (u16 by map): the chapter's list, loaded by character by its scripts (the first record with that character).
  - `$88:9D6D`: the units the spawn slots bring in.
  What a foe has in its item slots, and its gold, are what it leaves when it falls (`$83:AE1B` stores them as the battle's spoils): the
  drops. Generic foes share character 0x45; their name id is their army's ("Galder").
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
  ($87:9DB2), each slot with a count left rolls its chance and, if its tile is free, brings in its unit and counts down.
- **Tile events** (`$8C:917C`, 10 bytes: [map][who: 0 your army, FF anyone][column][row][condition][kind][event id u16][u16]): kind 0
  a house, 1 a shop (its SHOP command: [shop][type: 0 armory, 1 vendor, 2 secret shop]), 2 the arena, 3 a village, 4 the seize tile,
  8 a secret shop (on an ordinary tile). Their scripts: u16 pointers at `$8C:8004` by event id (bank `$8C`). A record whose condition
  isn't met is skipped; of the seize records, the last one met wins.
- **Chests, doors and drawbridges** (`$8C:9AD3`, the same format): kind 7 a chest (its script gives the item or gold), 5 a door, 6 a
  drawbridge.
- **Hidden items** (`$8C:9FDE`, 7 bytes: [map][column][row][condition][item][u16]; `$83:9D95`): found by a unit that waits on the tile
  or one next to it (not diagonally); a thief always finds it, anyone else on a roll below its Luck.
- **Talks** (`$8B:89C6`, 6 bytes: [map][talker name][target name][condition][event id u16]): scripts at `$8B:8A93` by event id. A
  talk whose script swaps the target for a record of the chapter's list (command 0x0D) recruits it.
- **Conditions** (`$87:AAA7`): u16 pointers at `$8C:A04F` by 3 x number, each a list of [type][u16] ended by FF: type 0 the unit
  holds the item, 1 the flag is clear, 2 the character is on the map, 3 it's in your army and alive, 4 your army holds the item, 5
  the chapter is at most the number.
- **Shops** (`$8C:9044`): 8 item ids per shop, padded with FE.
- **Paths** (command 0x09: four u16 pointers to [op][value] lists ended by FFFF): op 0 picks the unit, 2 its direction (0 left,
  1 right, 2 up, 3 down), 5 moves it by pixels (16 a tile), FF 02 sets it down where its walk ends, FF 03 leaves it walking on: a
  unit still walking when the camera scrolls keeps its place on the screen, so it lands that much further along the map (Caeda in
  Chapter 1).

Checked against outside sources in `src/logic/__tests__/fe3.test.ts`: every chapter's starting foes against the Fire Emblem Wiki's
rosters (four headline figures disagree with their own rosters; the tests say which), its bosses against the wiki's chapter list
(Tiki, a talk recruit, isn't on the game's boss list), Chapter 1's armory against Serenes Forest's shop list, and the wiki's "dropped
by" items, which are the item slots.

Not confirmed:
- Which deaths lose the game besides Marth's (the defeat check wasn't traced).
- The Endgame's condition also asks for event flag 18 to be clear. Nothing in Book 2's Chapter 20 sets it (Chapter 17 uses it for
  Sheena's talk), so it's taken to be cleared between chapters; the notes say only "if your army holds the Binding Shield".
- The staves' ranges are Serenes Forest's; the staff targeting code wasn't traced.
- Spawn slot counts: Book 1's Chapter 4 slots hold 16 each; the Fire Emblem Wiki says 17.
- The openings' walks are played as described above; positions match the game in Chapter 1 (its work RAM at the first turn), the
  rest weren't checked in the emulator.
- Flags carried from earlier chapters (who died where) are taken to be clear: Book 2's Chapter 8 shows Jeorge and Astram, who come only
  if they lived.
