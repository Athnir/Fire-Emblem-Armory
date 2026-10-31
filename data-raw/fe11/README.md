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
  `fe11_data.text()` reaches it by the plain spelling too. A few strings (the Goddess Icon's and Seraph Robe's names; the help text
  of Barrier, Hammerne and Aum) are drawn with special glyph codes the text can't spell.
- **Scripts** (`script/*.cmb`, `scripts/fe11_cmb.py`): an older version (dated 2006-10-24) of Fates' bytecode, with its own header
  and opcodes. A handler: its name, its code, its trigger (+0xc: argument count << 16 | type) and its arguments. Types: 0x03 / 0x17 a
  turn (first turn, last turn, phase: 0 player, 1 enemy), 0x04 an area (x1, y1, x2, y2, whose unit: 0 yours, 1 the enemy's), 0x05 a
  tile (x, y, kind), 0x08 a talk (two people, by string offset; the second argument offset 0 is a real string), 0x09 a battle talk,
  0x0b a death; and named ones (MapBegin, Opening, Ending, ChapterNext). Opcodes: 0x19 / 0x1a / 0x1b numbers, 0x1c / 0x1d strings,
  0x38 a call (name, argument count), 0x20 discard, 0x01 / 0x02 a local / argument, 0x07 / 0x0a an address, 0x47 assign, 0x29 not,
  0x22-0x32 comparisons (0x31 '<'), 0x3a jump, 0x3c-0x3e conditional jumps, 0x39 return, 0x45 the end.

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
- **Terrain** (16 bytes): its name label, its battle background, its row of TerrainCategory (Avoid, Def, ?, heal %) and its column of
  TerrainCost (25 rows of 32: a cost per terrain column, 0xff impassable).

## Maps (`scripts/build-fe11-maps.py`)

- **Grid** (`map/<chapter>`): +0xc width, +0xd height, +0x10 the terrain grid (32 x 32 Terrain ids). Every grid has a one-tile border
  no unit enters: the map is the tiles inside it (the wiki's sizes, all 34 chapters checked).
- **Units** (`dispos/<chapter>`): groups of [name, records, count]; 80-byte records: +0 person, +2 class, +4 x, y where it enters, +6
  x, y where it stands ((0, 0): where it enters), +8 team, +9 level, +0x10 five items (an item and a flag byte: 0x01 drops), +0x24 flags
  (0x100 the boss). `MapBegin` places 'mikata' (your deployment slots) and 'first' (the foes); the opening scene places more and moves
  units (`play()` runs MapBegin and the opening straight through: Dispos places a group, a unit fetched into a local is moved or taken
  off, a warp-in is a copy for the scene). Groups named e01 / ev... are the scenes' actors. A turn handler placing a group is a
  reinforcement; an area handler places one itself or sets a flag the turn handlers check.
- **Tiles** (`script/<chapter>_ter.cmb`): handlers (x, y, kind): 5 a door, 6 a chest (TreasureGet), 7 a drawbridge, 8 a village
  (ItemGet, MoneyGet, or a recruit walking out), 9 a house, 10 an armory and 11 a vendor (Goods; GoodsLimit a limited stock), 12 the
  secret shop (a VIP Card), 14 the tile to seize.
- **Recruits**: a talk handler that hands a unit over (UnitTransfar); both of a unit's recruiting talks are listed (Lorenz: Caeda or
  Marth).
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
- The Hard modes' foes (arm9 0x203a3e0, read in passing): a foe's weapon steps up by its +0x3a tier (Iron 0, Steel 1, Silver 2, Brave
  3; 0x7e special weapons forged instead, 0x7f never) as the mode rises. Not used yet.
- The weapon triangle and rank bonuses (overlay 00, 0x21c6ef0, called as every battle is set up): WeaponDeadlock's row for the two
  weapons' types adds its (hit, attack) pair by the advantaged side's rank; the advantaged side also gets its own rank bonus, the
  disadvantaged side loses as much and gets none.

## Not confirmed

- The Hard modes: the placement records hold one level per unit; how the game raises foes on Hard isn't read, so the maps are Normal's.
- Forging: that it opens in Chapter 4 at the battle preparations' armory, one weapon per chapter, and what can be forged (weapons with a
  price) are Serenes Forest's.
- Reinforcements a turn handler places "every turn" run under the handler's own checks (counters, flags): the maps say when they start
  (the areas) but not every condition.
