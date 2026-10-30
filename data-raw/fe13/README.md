# Fire Emblem Awakening (FE13) game files

Read from the user's own dumps in `Documents\FE Games`: the cartridge image `00040000000A0500_v00.trim.3ds` (North American, title
0004000000 0A0500, decrypted: its NCCH has the NoCrypto flag) and the DLC `Fire_Emblem_-_Awakening_NA_DLC.cia` (decrypted, 26 contents).
`scripts/fe13_extract.py` copies what the Armory reads into `data-raw/fe13/romfs/` (git-ignored, never committed): the romfs's `data/`,
`scripts/`, `map/data/` and English text `m/E/`, the program (`code.bin`: the exefs `.code`, BLZ-decompressed, loaded at 0x100000), and
each DLC content's romfs plus the files inside its `E0xx_MAP.arc` under `dlc/E0xx/`. Only data built from them is in the repo.

The DLC holds 25 maps (E001-E019, E022-E027). That is every map released (25, per the Fire Emblem Wiki); the numbers E020 and E021 were never used, and nothing in the game
or its DLC refers to them.

## Containers

- **`.lz`**: a 0x13 header, then LZ11 (`scripts/fates_lz.py`, shared with Fates).
- **Binary data files** (`scripts/fe13_bin.py`): the 3DS Fire Emblem layout. A 0x20 header (file size, data size, pointer count, label
  count), the data, a list of the data offsets that hold pointers, then labels ([data offset, name offset]) and their names. Pointers and
  labels are relative to the data (file offset 0x20). Strings are Shift-JIS.
- **Text** (`m/E/*.bin.lz`): the same layout; each label names a UTF-16 string (`scripts/fates_text.py`).
- **DLC archives** (`E0xx_MAP.arc`): the same layout again; each label is a file path and points at [name, index, size, offset].
- **Chapter scripts** (`scripts/*.cmb`): Fates' bytecode (`scripts/fates_cmb.py` disassembles both). `scripts/fe13_events.py` lists
  the handler kinds the game uses and plays a handler for a difficulty and turn (DifficultyGet: 0 Normal, 1 Hard, 2 Lunatic).

## GameData (`data/GameData.bin.lz`, `scripts/fe13_data.py`)

Tables by label, each with a `...Num` count:

- **ItemData**, 56 bytes: +0 eight flag bytes, +8 IID, +12 name label, +16 description label, +20 u16 index, +22 u16 price per use
  (worth = price per use × uses), +24 type (0 sword, 1 lance, 2 axe, 3 bow, 4 tome, 5 staff, 6 dragonstone, 7 beaststone, 8 claws,
  9 breath, 10 item), +27 how it's used (1 heals +40 HP, 6 a stat boost that wears off), +28 the weapon experience it needs (the rank:
  WeaponLevelData), +30 a staff's EXP, +31 uses (0 never breaks), +32 Mt, +33 Hit, +34 Crit, +35 / +36 range (0xFE: Mag ÷ 2), +38 3 for
  the legendary weapons, +40 a heal amount, +41..+47 stat bonuses (Str, Mag, Skill, Spd, Lck, Def, Res), +48 the class categories it's
  effective against (the same bits as a class's +90: 0x01 fliers, 0x02 dragons, 0x04 beasts and riders, 0x08 Revenants and Entombed,
  0x10 armour, 0x20 Grima).
  - Flags read from the descriptions and checked against them: +0 0x01 usable, 0x02 strikes twice, 0x04 magic damage (Levin Sword,
    Shockstick, Bolt Axe), 0x08 not forgeable (Mire); +1 0x40 its stat bonuses apply while equipped, 0x80 heals its wielder each turn;
    +2 the skill it gives (0x01 drain, 0x02 Astra, 0x04 Sol, 0x08 Luna, 0x20 Vengeance, 0x40 Despoil, 0x80 swordbreaker); +3 0x01-0x08
    lance-, axe-, bow- and tomebreaker, 0x10 Titania's Axe's, 0x20 the Underdog Bow's; +4 who may use it (0x04 Chrom, 0x08 the lord
    classes, 0x10 myrmidons, 0x20 archers, 0x40 dark mages: a class's +91; 0x80 Marth / Lucina), 0x02 an event-tile item (sells for a
    quarter of its worth); +5 0x01 Walhart, 0x02 Owain.
  - The battle code reads them as the bin lays them out: Mt at +0x20 and Hit at +0x21 (`0x2c4df8`, `0x2d3d60`).
- **JobData**, 128 bytes: +8 JID, +16 name, +24 base stats, +56 maximums, +64 pair-up bonuses, +80 movement type (a TerrainCostData row),
  +81 Mov, +84..+89 the weapon types it uses, +90 / +91 its categories (the JCID_ list's bits: +90 flying, dragon, beast, monster,
  armour, boss, manakete, taguel; +91 lord, myrmidon, archer, dark mage, dancer).
- **ChapterData**, 68 bytes: +0 CID (`CID_001`: the files' key is after `CID_`), +8 / +12 name labels (`MCID_x`, `MCID_x_T` heading,
  `MCID_T_x` location), +16 a child paralogue's parent (whoever must be married), +20 the chapter whose clearing opens it, +32 the
  location's shop (five item indexes), +42 a travelling merchant's ten (0x7FFF: one of the rare items, the program's list at 0x4d6468),
  +64 1 a paralogue, 2 a SpotPass paralogue, 3 the Outrealm Gate.
- **TerrainData**, 28 bytes: TID, name, a pointer into TerrainCategoryData (4 bytes: Def, Avoid, healing %, -), +12 what it becomes
  (a village once visited, a chest once opened), +16 flags (0x20 damages: Hazard, Lava). **TerrainCostData**: 14 rows (movement types)
  of 18 costs, one per terrain category (255: can't enter).
- **WeaponLevelData** (A 91, B 61, C 36, D 16, E 1), **WeaponBonusData** and **WeaponInteractData**: see `scripts/build-triangles.py`.
- **PartnerEnhanceData**: dual support, see `scripts/build-fe13-supports.py`.

Mechanics checked in the program (`scripts/fe13_code.py` finds a class's virtual functions, a label's users and disassembles):

- Hit = the weapon's Hit + (Skill × 3 + Luck) ÷ 2 (+ rank bonus); avoid = (Speed × 3 + Luck) ÷ 2; crit = the weapon's + Skill ÷ 2
  (`0x2d3d00`, `0x2d3d48`, `0x2d3d60`).
- The hit roll (`0x268d8c`): two numbers 0-99 from the battle's random generator, a hit when the hit is above their average; crit is
  one number, and a crit triples the damage.
- Effectiveness (`0x3efb60`): the weapon's Mt is added twice more (×3); the triangle's attack part isn't.
- Terrain (`0x3ef9e4`): a unit with the flying category gets no terrain Def or Avoid.
- The triangle and rank bonuses (`0x3ef214`, `0x3efa50`) and dual support (`0x218dd8`, `0x2aeccc`): in the generators' notes.
- Infinite Regalia's foes (`ev::ForceUnitGainEquipLimitItemForE006`, `0x3b6194`): each gets a random legendary weapon (+38 = 3) of its
  best weapon type, not marked to drop.

## Chapters (`scripts/build-fe13-maps.py`)

- **Grid**: `data/terrain/<key>.bin.lz`: width, height, then 32 × 32 bytes of terrain ids. The outer ring is a border the cursor
  never reaches (units arriving from off the map start on it), so the playable map is the stored one less two in each direction: the
  wiki's sizes for every map. A chapter loads the grid its load handler names (Premonition loads Chapter 23's).
- **Units**: `data/dispos/<key>.bin.lz`: groups of [name, offset, count]; 116-byte records: +0 PID, +16 u16 flags (0x40 Normal, 0x80
  Hard, 0x100 Lunatic, 0x800 boss, 0x02 placed by the game), +20 team (0 yours, 1 enemy, 2 green), +22 start x, y, +24 end x, y (from the
  top left, border included), +28 five items, each [IID, four bytes: +0 bit 0 dropped]. `<key>E.bin` files are the world map's
  skirmishes and aren't used.
- **People**: `data/person/<key>.bin.lz` (the chapter's own) and `static.bin.lz` (the army): +0 SID flags (0x20 losing them loses the
  chapter), +8 PID, +16 JID, +20 name label, +69 level. A DLC hero with no name label is named by its DLC text's `MPID_配信<name>`.
- **Scripts**: kind 0x07 loads (and its win rule: 0x40000 defeat the commander, else rout); 0x0c turn N's phase (third argument 0 player,
  1 enemy); 0x0f reinforcements (first, last turn); 0x10 an area or condition (x1, y1, x2, y2, side, condition name); 0x0a the end of the
  chapter (units placed here join after the battle); 0x12 talks (a target handed over with UnitTransferByIndex is recruited); 0x11 in
  `_Terrain.cmb` tiles: (x, y, kind) 8 village, 14 door, 15 chest, 23 event tile, with ItemGain giving what a village or chest holds.
  A unit a scene takes off again in its own handler (UnitExpulsionByIndex) isn't shown. Dispos's second argument 512 sets a template
  aside and 1028 places the picks (the DLC maps whose foes are random).
- **Lava** (Chapter 18): TrickSet(x, y, 20, 4) in a 0x0d handler turns the islet whose corner is (x, y) to hazard terrain that phase.

## Sources of items

Shops (a location's shop opens once its chapter is won and stays open), travelling merchants (three of a location's extras at random,
one copy each, plus the rare items), chests, villages, drops, what foes carry, what a recruit joins with (the first time each joins),
the story's gifts (ItemGain in a chapter's script), event tiles (a random item from the event-tile pool: items with +4's 0x02, which
match the Fire Emblem Wiki's list), renown rewards (OtherData's 名声アイテム: the item's Japanese name and the renown it needs), and
the DLC maps' foes and rewards. The weapon page hides DLC and renown sources until their switch is on.

Left out: SpotPass and StreetPass teams, bonus teams' shops, the barracks and Outrealm villages (random, and not in these files), and
Double Duel.

## Not confirmed

- The forge's limits and costs (5 steps per stat, 8 in all, Crit up to 50; n(n+1)/4 of the worth for n steps) are Serenes Forest's.
- Dual strike and dual guard rates and pair-up's support-level bonus are Serenes Forest's.
- Reinforcement timing: the script gives the turn; per the Fire Emblem Wiki they arrive at the start of the turn on Normal and at the
  start of the enemy phase on Hard and Lunatic.
- Chapter 18's islets: the script names each by a corner, so the map marks where each is and when it turns, not its tiles.
- Paralogue 16's walls: which opens when isn't decoded.
- The Future Past 3: the wiki says the map is also lost if the green Lucina falls; nothing in its files says so.
- The Falchion's and Exalted Falchion's lock (+4 0x04): the game's description says Chrom only; Serenes Forest lists Marth (Lucina) too.
