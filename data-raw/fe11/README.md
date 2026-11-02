# Fire Emblem: Shadow Dragon (FE11) game files

Read from the user's own dump in `Documents\FE Games`: the cartridge image `Fire Emblem - Shadow Dragon.nds` (North American, YFEE).
`scripts/fe11_extract.py` copies what the Armory reads into `data-raw/fe11/rom/` (git-ignored, never committed), decompressed: `data/`,
`dispos/`, `map/` (the grids, not their `.ta` textures), `script/`, `m/` (the English text) and `cpu/`, plus the ARM9 program (`arm9.bin`,
loaded at 0x02000000) and its overlays (`overlay/<id>_<load address>.bin`). Only data built from them is in the repo.

## Containers (`scripts/nds_rom.py`)

- **The cartridge**: NitroFS (the FNT names, the FAT offsets). `data/`, `dispos/`, `m/` and `cpu/` are LZ10 (type 0x10); the map grids
  and scripts are stored as they are. The ARM9 program and overlays are backward-LZ (BLZ) when their flags say so.
- **Binary data** (`data/database`, `dispos/*`, `map/*`, `m/*`): Awakening's container (`scripts/fe13_bin.py`): a 0x20 header, the
  data, a pointer list, then labels naming its tables.
- **Text** (`m/en_*`): labels -> Shift-JIS strings. One label has a full-width letter in it (`MPID_ROＬENSE`, Lorenz's name):
  `fe11_data.text()` reaches it by the plain spelling too. A few strings are drawn with special glyph codes the text can't spell:
  the Swordmaster class's name (its MPID_P_SWORDMASTER spells it), the Goddess Icon's and Seraph Robe's names (given as the game
  draws them, `fe11_data.DRAWN_NAMES`), and the help text of Barrier, Hammerne and Aum. Morzas's name is under MPID_MORZECE, not
  MPID_ + the PID's tail (PID_MOSES).
- **Scripts** (`script/*.cmb`, `scripts/fe11_cmb.py`): an older version (dated 2006-10-24) of Fates' bytecode, with its own header
  and opcodes. A handler: its name, its code, its trigger (+0xc: argument count << 16 | type) and its arguments. Types: 0x03 / 0x17 a
  turn (first turn, last turn, phase: 0 player, 1 enemy), 0x04 an area (x1, y1, x2, y2, whose unit: 0 yours, 1 the enemy's), 0x05 a
  tile (x, y, kind), 0x08 a talk (two people, by string offset; the second argument offset 0 is a real string), 0x09 a battle talk,
  0x0b a death; and named ones (MapBegin, Opening, Ending, ChapterNext). Opcodes: 0x19 / 0x1a / 0x1b numbers, 0x1c / 0x1d strings,
  0x38 a call (name, argument count), 0x37 a call to another handler of the script (its index: bmap023's MapBegin runs handler 9),
  0x20 discard, 0x01 / 0x02 a local / argument, 0x07 / 0x0a an address, 0x03 / 0x09 a value / address through a pointer (an
  element's size after), 0x41 store into a local, 0x47 assign, 0x29 not, 0x22-0x34 comparisons and arithmetic (0x31 '<'), 0x3a
  jump, 0x3d jump if zero (popping), 0x3c 'or' (jump if true keeping the value, else pop it) and 0x3e 'and' (jump if false keeping
  it), each 2-byte offset counted from the byte after the opcode, 0x39 and 0x45 return. A handler runs to the next one's header: code
  after a 0x45 is reached by jumps (bmap015's turn 6, which warps Gharnef out).
- **Playing a scene** (`play()`): Dispos places a group; a unit fetched into a local is moved (UnitMovePos, UnitSetPos,
  UnitWarpAppearance: a warp is a move, Chapter 23's Bishops warping in from the border) or taken off (UnitRemove*);
  UnitStackPush saves every unit and UnitStackPop puts them back (arm9 0x20451ec / 0x20451fc, overlay 00 0x21a323c / 0x21a32c8),
  undoing what a scene moved in between (Michalis back on Chapter 22's seize tile). Both sides of a story flag's check run, each
  placement tagged with its side (the Endgame: Nagi if Chapter 24x was played, else Gotoh, on the same tile). A reinforcement group
  stands where its handler leaves it, and a scene's actor placed and taken off in one handler (Prologue IV's e02) is none.

## Tables (`data/database`, `scripts/fe11_data.py`)

- **Item** (60 bytes): IID, name, help; +0xe price per use (an item's price is that times its uses), +0x10 kind (0 sword, 1 lance,
  2 axe, 3 bow, 4 tome, 5 staff, 6 dragonstone, 7 ballista, 8 item), +0x12 the weapon experience its rank needs, +0x14 uses, +0x15 Mt,
  +0x16 Hit, +0x17 Crit, +0x18 Wt, +0x19 / +0x1a range (0xff: Mag / 2), +0x1b-+0x23 Mov, HP and the stats an item gives (or what using
  it restores), +0x24 flags (0x01 usable, 0x02 brave, 0x04 magic damage, 0x08 a siege weapon, 0x20 a healing staff, 0x40 devil),
  +0x25 (0x04 Imhullu's shield, 0x08 Starlight), +0x2c the classes it's effective against (0x01 dragons, 0x02 Medeus, the Earth Dragon,
  0x04 armour, 0x08 ballisticians, 0x10 horseback, 0x20 fliers, 0x40 Manaketes). Who may use a personal weapon is in its help text
  ("For Marth."). Falchion and Imhullu have variant records (`_FALSE`, `_TINY`): the base record is the weapon page's.
- **Person** (80 bytes): PID, face (a generic has none), name (a generic's is its army's; a named person's is MPID_ + its PID's tail,
  a double's `_FALSE` dropped). **Job** (92 bytes): JID, name, +0x28 its row of TerrainCost, +0x29 Mov, +0x36 the kinds effectiveness
  checks.
- **WeaponLevel**: the experience for A, B, C, D, E (196, 136, 76, 31, 1). **WeaponBonus** / **WeaponDeadlock**: the rank bonuses and
  the weapon triangle (`scripts/build-triangles.py`).
- **MapTbl** (32 bytes): the chapter's file, its title, +8 its goal (1 seize, 2 rout, 3 defend, 4 defeat the boss).
- **Terrain** (16 bytes): its name label, its battle background, a pointer to its TerrainCategory record (Avoid, Def, a Res bonus
  against magic that is 0 everywhere, heal %). Its cost column is that record's index ((pointer - TerrainCategory) / 4: arm9
  0x2038248, read at 0x203826c as TerrainCost[4 + 32 x row + index]; the map's per-tile column grid is filled the same way as it
  loads, overlay 00 0x21a3364), not Terrain +0xc (plains' +0xc is 0, a column no class can enter). TerrainCost: 25 rows of 32 after a
  4-byte header, a class's row at Job +0x28, 0xff impassable. Healing is that % of max HP, rounded up (arm9 0x20381d8): 20 on forts,
  gates and thrones. A flying class gets no terrain bonus, nor does a unit whose foe holds the Lightsphere (item flag 0x10000), nor
  anyone in the arena (overlay 00 0x21c6d84).
- **Terrain codes** (`scripts/terrain_codes.py`): each code's stats are one set in every map (the generator checks it); where one code
  covers several of the game's names on a map (Plain and Floor, Wall and '----'), each tile keeps its own. Houses are standable
  (Avo 5) and never razed (the tile-state routine, overlay 00 0x21d4a7c, only closes or razes villages): `ot`. A ledge (the game's
  name for MS_TER_STONEWALL) is climbed at a cost and gives nothing: `tt`. A castle is a wall to all but fliers: `wx`. The game's
  categories 25-29 (a plain, floor, forest, fort and mountain only the lord can't enter: Chapter 9's and 12x's reinforcement entry
  tiles, a few in Chapters 14, 17x and 20) are `tu`, `b5`, `b6`, `b7`.

## Maps (`scripts/build-fe11-maps.py`)

- **Grid** (`map/<chapter>`): +0xc width, +0xd height, +0x10 the terrain grid (32 x 32 Terrain ids). Every grid has a one-tile border
  no unit enters: the map is the tiles inside it (the wiki's sizes, all 34 chapters checked).
- **Units** (`dispos/<chapter>`): groups of [name, records, count]; 80-byte records: +0 person, +2 class, +4 x, y where it enters, +6
  x, y where it stands ((0, 0): where it enters), +8 team, +9 level, +0x10 five items (an item and a flag byte: 0x01 drops), +0x24 flags
  (0x10 / 0x100: a foe the Hard modes level; 0x100 isn't the boss, arm9 0x203a234 reads it for growth only). `MapBegin` places 'mikata' (your deployment slots) and 'first' (the foes); the opening scene places more and moves
  units (`play()`, below). Groups named e01 / ev... are the scenes' actors. A turn handler placing a group is a reinforcement; an area
  handler places one itself or sets a flag the turn handlers check.
- **AI** (`ai_words`): a placement's +0x28-+0x34 name its four routines (action, mind, attack, move; cpu/database defines each) and
  +0x38-+0x44 their parameters ('pos(x,y)' tiles, a PID). CP_SP_Treasure goes for the chest at the move parameter's first tile and
  leaves by its second (the looter badge); CP_SP_Village goes for the village there, or the nearest, razing it, then leaves by the
  second tile or attacks (the village names its raiders); CP_SP_Talk comes to the person in the mind parameter to talk (Darros,
  Catria, Palla, Xane, Est: to Marth); CP_MV_Position heads for its tile; CP_AT_Person picks its person when it attacks (Chapter
  12's and 12x's Mages: Marth); CP_AC_Area waits for a unit in the rectangle its two tiles make (Chapter 13's Ballisticians),
  CP_AC_Attacked until it's attacked, and CP_AT_Null in the action slot until a script wakes it (CpuSetActive: Chapter 12's
  Heimler, when your units reach its bottom rows); CP_AT_Null as the attack never attacks. What turn and area handlers do to units
  on the map (`unit_effects`): take them off (UnitRemove*, UnitEffectWarpEscape), move them (UnitMovePos, UnitSetPos), turn them into
  another class (UnitDragonTransform: Medeus into an Earth Dragon on turn 1) or wake them.
- **The boss** (the skull): the person whose death handler (type 0x0b) sets ボス死亡 (Chapter 12's Volzhin, Chapter 23's Gharnef);
  where no death sets it, the foe on the seize tile at the start, unless a handler takes it off the map (Prologue IV's Captain; not
  Chapter 15's Gharnef, who warps away on turn 6: UnitEffectWarpEscape, UnitRemoveMustErase). Chapter 23's MapBegin runs handler 9,
  which hands the real Gharnef's PID and items (Imhullu, and a Falchion that drops) to one of its three Gharnefs at random
  (RandomMinMax) and false copies to the others: any of the three may be the boss. A double's false Falchion drops as a Steel Sword
  (overlay 00 0x21cc7c8).
- **Arrivals** (`guarded_calls`): each Dispos's conditions come from the branches around it (a jz covers the code to its target;
  the 'and' jumps before it add theirs): the flags it waits on (an area's: the area; a talk's: once its recruit joins, Prologue IV's
  Knights after Gordin's), ボス死亡 clear (until the boss is defeated), and ValueGet counters: one the turn handler steps and resets
  with its flag is so many phases in a row (Chapter 7: two enemy phases), one the area handler checks is so many times in all (up
  to three), one only the area resets caps the waves (Chapter 17: ten). The groups one handler places under the same conditions are
  one arrival; an arrival made of others' groups (the Endgame's turns 15 and 20) adds its turns to theirs.
- **Tiles** (`script/<chapter>_ter.cmb`): handlers (x, y, kind): 5 a door, 6 a chest (TreasureGet), 7 a drawbridge, 8 a village
  (ItemGet, MoneyGet, or a recruit walking out), 9 a house, 10 an armory and 11 a vendor (Goods; GoodsLimit a limited stock), 12 the
  secret shop (a VIP Card), 14 the tile to seize, 19 Prologue IV's decoy fort.
- **Map changes** (`changes_of`): the scripts' tile natives (arm9 0x2046e50) set a tile's state: TTEnable 0, TTDone 1, TTDestroy 2;
  the tile-state routine (overlay 00 0x21d4a7c-0x21d4b18) makes a done door floor and a closed one a door, a done drawbridge a
  bridge, a done village closed and a destroyed one ruins. A door's TTDone (_TTDone, arm9 0x2045648, through overlay 00 0x21d4e44)
  also opens the rooms on its four sides; RoofOpen opens the room holding its tile. **Rooms**: the map file's +0x14 is a 32 x 32
  room grid (0: none); the loader closes every room (overlay 00 0x21a2834 sets bit 0x80 on its tiles) and the move range (arm9
  0x20e401c) bars a closed room to every unit, fliers included: only Chapters 17x and 19 have rooms. The opening's calls (MapBegin,
  Opening) are made before the battle: Chapter 1's village at (22, 4) is razed (TTDestroy), the Endgame's five side doors start
  open (TTDone) and its turn handlers shut them (TTEnable: turns 3, 3, 5, 6, 7). A turn or area handler's call says when, by its
  turn or area, or by its guards (`cond_words`): a death's flag, a talk's (once its recruit has joined), ForceGetCount(0) == 1 (0x2f is
  ==: Prologue IV's door opens once "All but the prince have been slain?", MS204_EV8_6); a guard that's a flag the handler sets itself
  is its first such phase. A door a scene opens and shuts again (Prologue IV's turn 2) isn't a change. A visit to one tile can change
  another: Chapter 16's two villages close each other (TTDone); Prologue IV's decoy fort (closed in the opening, enabled on the first
  player phase once Gordin has joined) takes the unit that visits it off as dead (UnitRemoveEventDead; Marth is turned back), takes
  the Knights off and opens the door at (17, 19). What names someone not on the map at the start (Gordin) is a note the spoiler block
  leaves out. A key opens a door (a Door Key or the Master Key) or lowers a drawbridge (a Bridge Key or the Master Key), as their help
  texts say (MI_H_DOORKEY, MI_H_BRIDGEKEY, MI_H_THIEFKEY).
- **Talks and joins** (`talks_of`, `ending_of`): a talk handler that hands a unit over (UnitTransfar) recruits it, on the map at the
  start or arriving (Catria, Palla, Est, Gordin); both of a unit's recruiting talks are listed (Lorenz: Caeda or Marth). A talk's 4th
  argument is its done flag: one the opening sets shuts the talk until a handler clears it (Minerva's, once Maria's recruitment
  clears it; Jake's, once the house at (22, 7) is visited). A talk's ItemGet is a gift (Est's Mercurius, taken off her with
  UnitSetItemPutOff, to Marth); a talk that takes its unit off the map and sets a flag the end checks is a join after the battle
  (Ymir). The Ending hands over units (UnitTransfar: Horace, Etzel, 'if alive' where it checks) and gives items (ItemGet: Chapter 4's
  Silver Sword, Chapter 12's Parthia, Chapter 24x's weaker Falchion, IID_FALCHION_TINY: "Falchion (24x)"). A recruit's gear, and
  what a talk or the end gives, count from the next chapter (`kit-later`, `talk-later`, `event-later`); an opening's hand-over from
  its own. A village's reward can need items in hand (Chapter 22: Starlight if Marth carries the Lightsphere and the Starsphere,
  UnitCheckItem, both taken).
- **Gaiden chapters**: the chapter before ends by setting a flag `ChapterNext` checks: 6x, 12x, 17x and 20x open if fewer than 16 of
  your units are alive (ForceGetCountAllPlayerUnit, '<' 16); 24x if the army has neither the Falchion nor Tiki.

## Mechanics checked in the program

- Effectiveness (overlay 00, 0x21c7954): the weapon's +0x2c bits against the defender's class (+0x36); an item of the defender's
  with subtype 6 (Iote's Shield) takes away what its own bits cover; what's left adds the weapon's Mt twice more (x3).
- Attack (0x203d22c): the weapon's Mt plus Strength (Magic for a magic weapon, 0x2038348) plus the rank bonus.
- Hit (overlay 00, 0x21c92c4, used at 0x21c9528): two numbers 0-99 (arm9 0x202000c: lo + rand mod (hi - lo + 1)) added and halved
  (rounded down); the strike lands if that's below the side's hit. That hit (0x21c7da0) is the side's hit minus the foe's avoid, held
  between 0 and 100. Crit is one 0-99 number below the crit (the same routine), and triples the damage.
- The forge (arm9, the shop's forge menu: shop::RefinePower / RefineHit / RefineCritical / RefineWeight, their limits at entries 57-58 of
  each class's table, the price at 0x2056dc0): Mt, Hit and Crit only go up, Mt by 10 (at most 30), Hit by 50 (200), Crit by 30 (50); Wt
  goes 10 either way (1 to 30). With the weapon's price P (price per use x uses) and each stat's step (Mt 1, Hit 5, Crit 3, Wt 1), a
  change of d costs P x q(q+1)/2 for its q whole steps plus the remainder's share of the next step; the forge costs (the four shares +
  P) / 2 (Serenes Forest's worked example, 121,000G, comes out the same). `src/logic/fe11Forge.ts`.
- The Hard modes (the game's names: Normal, Hard, Brutal, Savage, Fiendish, Merciless; arm9 0x2039ff8, as a foe is made). Only foes
  whose record has +0x24 0x10 or 0x100 change. They gain (the mode, 0-5) x MapTbl +0x1c levels of growth (the person's + the class's
  growth, the fraction rounded up at random) in HP, Str, Mag, Skl, Spd and Lck, never Def or Res, their shown level unchanged; their
  weapon ranks rise to C (Hard, Brutal), B (Savage, Fiendish) or A (Merciless). Their weapons (0x203a424): the chapter's tier (MapTbl
  +0x1d) less 1 on Savage and Fiendish, as it is on Merciless, nothing below Savage, held 0-4; a weapon of a lower tier (item +0x3a: 0
  Iron to 3 Brave, by the kind lists at 0x20d4bc0, Fire / Elfire / Bolganone / Thoron for tomes) becomes the kind's weapon of that tier,
  forged at tier 4; a special weapon (0x7e, not +0x2b 0x40) is forged at tier 2 and up on Fiendish and Merciless, or 3 and up on Savage.
  The forge it gets (0x2041294): Mt +4 (+8 at tier 4) and Hit +20. Only the first slot changes if it's a dropped item, and then the game
  gives the foe a copy of the original that still drops (0x203cef8). Every chapter's foes on every mode match Fire Emblem Wiki's mode
  tabs. The prologue is Normal's only (the modes' own descriptions, `MIMH_INTRO` / `MIMH_MAIN`; `gop01` opens Prologue I, `gop02`
  Chapter 1), so on the Hard modes the army joins in Chapter 1. Each mode is an entry in the difficulty bar: a foe is an entry per set
  of items the modes give it, with its modes; a source line holds on the modes its unit does (the Brave weapons only Merciless's
  foes carry, from Chapter 20, are theirs alone); each mode's growth and rank floor are a note on that mode (`notesOn`).
- The weapon triangle and rank bonuses (overlay 00, 0x21c6ef0, called as every battle is set up): WeaponDeadlock's row for the two
  weapons' types adds its (hit, attack) pair by the advantaged side's rank; the advantaged side also gets its own rank bonus, the
  disadvantaged side loses as much and gets none.

## Not confirmed

- Forging: that it opens in Chapter 4 at the battle preparations' armory, one weapon per chapter, and what can be forged (weapons with a
  price) are Serenes Forest's.
- A reinforcement's conditions are read from its handler's branches (`guarded_calls`); a check outside those idioms (flags,
  ValueGet counters, ボス死亡) isn't said.
- Who can open a door or a chest without a key (the thieves, in the earlier games) isn't traced in the code: the doors say only what
  the keys' help texts give.
