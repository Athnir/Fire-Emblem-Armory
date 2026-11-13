# Fire Emblem: New Mystery of the Emblem (FE12) game files

Read from the user's own dump in `Documents\FE Games`: the cartridge image `FIREEMBLEM12_VI2J01_01.nds` (Japanese, VI2J revision 1,
clean; its secure area stored decrypted). `scripts/fe12_extract.py` copies what the Armory reads into `data-raw/fe12/rom/` (git-ignored,
never committed), decompressed: `data/`, `dispos/`, `map/` (the grids), `script/`, `m/` (the Japanese text) and `cpu/`, plus the ARM9
program (`arm9.bin`, loaded at 0x02004000) and its overlays (`overlay/<id>_<load address>.bin`). Only data built from them is in the repo.

An earlier dump (`Fire Emblem - Shin Monshou no Nazo - Hikari to Kage no Eiyuu.nds`) had all 119 `script/*.cmb` files zeroed; this
one has them all, and every other file is byte for byte the same.

## English names (`scripts/fe12_names.py`, `scripts/vcdiff.py`)

The Heroes of Shadow translation (`FE12_v3.01.zip` in `Documents\FE Games`, the patch Serenes Forest hosts) ships as `FE12_v3_01.delta`,
a VCDIFF (xdelta3) file with no secondary compression. `vcdiff.py` applies it in memory and checks each target window's Adler-32: all
match but the first 8 MB window, because the patch was made from a dump whose secure area is encrypted (CRC32 B6AF36B5; this one's is
2DA8A814). The text is read through the patched file table: its `m/` files (Awakening's label -> string container, as the game's own),
by the game's labels: MPID_ people (a named person's is MPID_ + its PID's tail, or its face's: PID_WOLEN's face FID_WOLLEN, Warren),
MJID_ classes, MIID_ items, MS_TER_ terrain, MCT chapter titles. The patch packs long names by putting a narrow-spacing code (0x88, a
Shift-JIS lead byte with no character under 0x889F) between their letters; it's dropped. Nothing patched is written.

The patch mostly uses Shadow Dragon's official names (208 of the shared names are the same). The Avatar is "Avatar" on the maps, as
Awakening's are (the patch's default name is Chris). The modes are the patch's: Normal, Hard, Maniac, Lunatic, Reverse Lunatic.

## Containers and tables (`scripts/fe12_data.py`)

`data/FE12Data.bin` is Awakening's container (`scripts/fe13_bin.py`); FooterData holds the counts (403 people, 57 classes, 194 items, 50
forge slots). Shadow Dragon's layouts where the tables match (`data-raw/fe11/README.md`):

- **ItemData** (60 bytes): Shadow Dragon's Item, but +0x18 (Wt) is 0 on every item (nothing in battle reads it), and +0x24 and +0x28
  are u32s: +0x24 0x01 usable, 0x02 brave, 0x04 magic, 0x08 siege, 0x20 a healing staff, 0x40 devil, 0x400 Imhullu's shield, 0x800
  Starlight, 0x1000 the Darksphere, 0x4000 no harm from magic (Magestone, Mage Breath), 0x40000 the Lightsphere, 0x80000 the Iote's
  Shield, 0x100000 opens chests (the Fire Emblem), 0x1000000 the Silver Card, 0x2000000 the VIP Card, 0x4000000 an important item (not
  sold), 0x8000000 stays with its holder, 0x10000000 never wears out; +0x28 0x04 the Elysian Whip, 0x20 stats while held, 0x80 heals each
  turn (the Lifesphere), 0x100 drains, 0x400 the Geosphere, 0x800 ignores Def and Res (Glower), 0x1000 sells for 0, and from 0x10000 the
  equip check's lock bits (below); +0x2b 0x20 barred from a wireless team, 0x40 never forged, 0x80 a forged copy; +0x2c (u16) what it's
  effective against; +0x3a the modes' tier (0-3 Iron to Brave, 0x7c the 1-range breaths, 0x7d and 0x7e special weapons, 0x7f none).
  The forge's 50 records (ItemRefineData, IID_REFINE1-50) follow the item table. The online shop's items (134-173: the Blunt Sword,
  Ember...) are in the table; what the shop sold came from Nintendo's server (+0x29 0x20).
- **PersonData** (92 bytes): +0 PID, +4 face, +8 a generic's army name, +0x14 growths, +0x1c a person's growths for the modes, +0x2c
  attributes (0x01 a woman, 0x02 and 0x04 Marth, 0x08 the princesses, 0x20 Caeda, 0x40 Malicia and Lena, 0x80 Merric, 0x100 Linde,
  0x200 Tiki and Nagi, 0x4000 the Avatar), +0x30 five support slots.
- **JobData** (80 bytes): +0x28 its TerrainCost row, +0x29 Mov, +0x36 kinds (u16: 0x01 dragons, 0x02 Medeus's class, the Shadow Dragon,
  0x04 armour, 0x08 ballisticians, 0x10 horseback, 0x20 fliers, 0x40 manaketes, 0x80 sword fighters (Mercenary, Hero, Myrmidon,
  Swordmaster), 0x100 archers (Archer, Sniper)), +0x38 attributes.
- **MapTableData** (44 bytes, 57 maps): +0 the file, +4 the file it shares (the prologue's B chapters), +8 the title (MCT...), +0x14
  the battle backgrounds' set, +0x15 the goal (0x01 seize, 0x02 rout, 0x04 defeat the boss, 0x08 a person reaching a tile), +0x16 the
  modes' level step, +0x17 the modes' weapon tier, +0x18 the battle preparations' menus (0x01 talk, 0x02 inventory, 0x04 the armory and
  its forge, 0x08 reclassing, 0x10 How's Everyone, 0x20 the Drill Grounds), +0x1c-+0x27 the reclassing limits, +0x2b the par turns.
- **TerrainData** (36 bytes): +0 the name label, +4 a pointer to its TerrainCategory record (Avoid, Def, a Res bonus that's 0
  everywhere, heal %): its cost column is that record's index; +0xc six battle backgrounds. **TerrainCost**: 26 rows of 28 after a
  4-byte header (the row count), a class's row at JobData +0x28, 0xff impassable. A cave plays as a mountain and bones as a plain, so
  they share those codes; the Endgame's altars (no unit enters them; Medeus stands on one and the dragons appear on the others) are the
  summoning sigil's code, as Awakening's.
- WeaponLevel, WeaponBonus (with a staff row: what it adds to healing), WeaponDeadlock: as Shadow Dragon's (`scripts/build-triangles.py`).

## Maps (`scripts/build-fe12-maps.py`)

- **The story**: Prologue I-VIII (bmap201-208; the answer at the end of III, V and VI, a Yes or No to Katarina, picks the next
  chapter's version: Yes sets Ｂに行く and ChapterNext loads bmap204B, 206B or 207B, which share their chapter's grid and placements,
  MapTableData +4, with scripts of their own), Chapters 1-23 (bmap001-023) with the gaiden chapters 3x, 6x, 10x, 13x, 16x and 20x
  (bmap103-120), and the Endgame (bmap024). Chapter 20's ChapterNext goes on (to 20x, or to 21) only once the Binding Shield is
  completed (封印の盾完成: the Fire Emblem with all five orbs, MS020_ED1_A_04), else it calls BadEnd and the game ends. Outside it: the
  Archanean Chronicles (bmap301-304) and the three downloadable chapters (dl001-003; their placements, scripts and text are on the
  cartridge under scrambled names: ajk3at, f9noa4bg, 2invaw9a1 and m/jk3at, 9noa4bg, invaw9a1). bmap025 and bmap101-105's placements
  are Shadow Dragon's, left over (80-byte records). Each grid has Shadow Dragon's one-tile border.
- **Map art**: Shadow Dragon's format (`data-raw/fe11/README.md`, `scripts/ds_art.py`), its `.ta` files LZ11; drawn the same way
  (plains, floors, castle walls in each map's stone, the void, villages' houses, castles whole). The Endgame and Chapter 23 are mostly
  the view beyond the map (`wy`); weather layers (snow, sand, mist) aren't drawn.
- **Placements** (`dispos/`, 88-byte records): +0 person, +2 class, +4 / +6 where it enters / stands, +8 army, +9 level, +0xa its growth
  level, +0x0c attributes OR'd into the unit, +0x10 five items (u16 item, u16 flags), +0x2c flags, +0x30-+0x3c its AI's routines,
  +0x40-+0x4c their parameters. A record's mode gate (+0x2c, overlay 00 0x2205b5c): 0x400 Hard and up, 0x800 Maniac and up, 0x1000
  Lunatic, 0x2000 below Hard, 0x4000 below Maniac, 0x8000 below Lunatic; an item slot's flags (0x204c544): 0x01 drops, 0x04-0x80 the
  same gates, 0x100 never changed by the modes.
- **Scripts**: Shadow Dragon's bytecode (`scripts/fe11_cmb.py`), with opcodes it never used (a switch's 0x44 dup and 0x3b jump if true,
  0x1f, 0x43 increment, 0x21 / 0x24 / 0x26 arithmetic, 0x33 >). Handler types: 0x03 and 0x17 a turn, 0x04 an area, 0x06 a tutorial
  step, 0x08 a talk, 0x09 a battle talk, 0x0b a death (startup.cmb's for Marth and the Avatar set gf_gameover), 0x18 a hidden treasure
  (an area where the unit that finds it gets its item: Chapter 11's desert holds ten). Terrain scripts' tile kinds: 5 a door, 6 a chest,
  7 and 8 a drawbridge, 9 a village, 10 a house, 11 an armory, 12 a vendor, 13 a secret shop (a VIP Card; every item a limited stock,
  GoodsLimit, as many as the chapter's RegistLocalFlags sets), 15 the tile to seize. The battle preparations' armory (overlay 10
  0x22304f0) sells the Iron Sword, Lance, Axe and Bow, Fire and Heal wherever MapTableData +0x18 has 0x04 (Chapter 1 on), and the stat
  boosters after a Lunatic clear.
- **The scenes** (`play()`): Shadow Dragon's, played once per mode: a check of the difficulty (GetHard(): the save's 0 Normal, 3 Hard, 4
  Maniac, 5 Lunatic and Reverse Lunatic) keeps the code it guards from the other modes (Prologue I: on Normal Jagen and the soldier leave
  and come back with the tutorial's steps; from Hard they stay), only the records that hold on the mode are placed (Prologue VI's opening
  walks Normal's Ogma or Draug off the map; he comes back once the rest are beaten), and a map loaded again (MapLoadD) takes the units
  off (Prologue I's scene in Altea Castle, then the training ground). Marth or the Avatar left standing by the opening is yours to move.
  A story flag's check (`a && b` too) tags what it places: a person killed in an earlier chapter (gf_<person>殺害, set by that chapter's
  death handler) has a generic stand in on the same tile (Chapter 8's Astram and Jeorge, 16's Astram, 19's Sedgar and Wolf, and among
  the reinforcements Chapter 9's Astram and 19's Vyland); Chapter 6's Rickard is placed only while neither gf_リカード味方 (recruited) nor
  gf_リカード殺害 is set.
- **Reinforcements** (`explore()`): each turn and area handler is read path by path on each mode. GetHard() is the mode's own value, so
  a check of the difficulty decides even inside `a && b` (Chapter 4: turn 6 on Normal, 6 and 8 on Hard, 5 and 7 on Maniac, 3 and 4 on
  Lunatic); what else a branch tests is kept with the path: a flag, a tile still in its first state (TTIsEnable), a unit on a tile or
  on the map, the turn (GetTurn() against a number: Chapter 22's turns 4, 6 and 8 on Lunatic), a counter (ValueGet) or an army's size.
  A handler another one runs (0x37) is read through; 0x21 stores and keeps the value (`a = b = 1`); a loop over an army's units runs once
  and goes on past it with what its body stores unknown. The paths reaching a Dispos are merged into the fewest terms (a literal both
  ways, a counter's values joined). What a handler places under the same term is one group, the same group on other turns or modes one
  group with each mode's time, and a handler's group that holds more groups on harder modes one group (Chapter 12's area 2). A counter
  the handler steps itself under a flag (エリアカウンタ, ValueInc) counts the phases since that flag was set: its values 0, 1, 2 are the
  first, second, third. What sets a flag is read the same way: an area's handler or the subroutine it runs (Chapter 12's area 1), a
  turn's handler (Chapter 12's area 1 opens on its own on turn 5 on Maniac, turn 2 on Lunatic; Chapter 22's dragons on turn 6, Maniac 5,
  Lunatic 4), a terrain tile (a chest: Chapter 16's treasure room opens the door at (25, 14); Chapter 22's chests run its
  TreasureDragonRush), a death. Chapter 20's turn handler on Hard and up also sets its area flags from turn 6 (Lunatic 4) once its loop
  finds a foe of AI band 1 active (CpuGetBand, CpuGetActive) or none left, said as "the foes' moves". Every chapter's Normal total
  matches Fire Emblem Wiki's (`fe12.test.ts`).
- **Chapter 10x**: each enemy phase, each of Roro's four copies (PID_RORO_1-4) that's gone comes back at its place, on Normal a phase
  late (it first sets 増援N) until 増援猶予廃止 is set; each return steps 出現カウンタ, and at 12 (Hard and up: 20) 増援強化 brings z05 on
  the next two enemy phases, z06a-b on the third, z07a-c on the fourth and z08a-d on each one after (which sets 増援猶予廃止).
- **The Endgame's summons**: from turn 2, each enemy phase while Medeus lives, the turn handler takes the slots of (turn - 1) % 4 (0:
  0 and 2, 1: 1 and 3, 2: 4, 3: 0, 1, 3 and 4; Maniac and up add 3, 4 and 2 to the first three), shifts them by (turn - 1) // 4 % 5 and
  summons at those of its five points (z01-z05) the next dragon of a cycle kept in 増援カウンタ: Fire, Earth, Mage, Ice, Earth, Fire,
  Mage, Earth, Wyvern. Each point's turns repeat every 20 turns. Medeus comes back to life when defeated while any of Nyna, Elice,
  Maria or Lena is still a foe (IsResurrectB and IsResurrect, ForceUnitSafetyGetByPID on army 1; his death handler's MS024_DIE_BOSS_B).
- **Gaiden chapters**: the chapter before ends by setting gf_<n>ｘ分岐 under its checks: cleared by a turn (GetTurn() <=
  GetNormalizeTurn(n): n times 100, 120, 140, 160 or 180% by the mode, Reverse Lunatic's 180, arm9 0x2028510) or another way: 3x by turn
  24, or with at most one of your units fallen in the prologue (Prologue VIII's ChapterNext sets the flag too: the dead force's units
  plus GetResurrectNum); 6x by turn 20 or with Rickard in your army; 10x by turn 15 or with 3 of the 6 foe Clerics still on the map; 13x by turn 20 or with
  no foe escaped; 16x by turn 18 or the Avatar promoted at Lv 5 or higher; 20x by turn 24 or with 3 of Roshea, Wolf, Sedgar, Vyland and
  Midia in your army, and only once the Binding Shield is completed.

## Mechanics checked in the program

- **Hit** (overlay 00 0x21f4fa0): two numbers 0-99 (a Xorshift128, arm9 0x201fe8c) added and halved, rounded down; the strike lands if
  that's below the displayed hit (hit minus the foe's avoid, held 0-100, 0x21f3944): Shadow Dragon's 2RN. Hit (arm9 0x2050408) = weapon
  Hit + Skl + Lck / 2, +5 for a Sniper, +10 for a foe on Lunatic and Reverse Lunatic. Avoid (0x2050640) = attack speed + Lck / 2, +10
  for a Swordmaster. Crit is one number below the displayed crit, rolled only after a hit that does damage, and triples it (0x21f52f0);
  crit (0x205056c) = weapon Crit + Skl / 2 up to Skl 20, then + 10 + (Skl - 20), +5 for a Sniper, +10 for a Berserker.
- **No weight**: attack speed is Spd (0x2050624); a unit strikes twice at 4 more (overlay 00 0x21f35a8), never with a siege weapon.
- **Effectiveness** (overlay 00 0x21f3494): the weapon's +0x2c bits against the defender's class kinds; an Iote's Shield the defender
  holds takes away the fliers' bit; what's left adds the weapon's Mt twice more (x3). A manakete fights as its stone's dragon class.
- **Magic** (arm9 0x20499c0): tomes, staves and +0x24 0x04 weapons use Magic against Resistance, at any range (the Levin Sword too).
- **Devil weapons** (overlay 00 0x21f5128): Shadow Dragon's (a 0-99 roll under 21 - Lck / 2 turns the strike on the wielder).
- **Brave** (+0x24 0x02; the Quick weapons too): every strike is two in a row, on both phases (overlay 00 0x21f5548). **Siege weapons**
  (+0x24 0x08: Swarm, Meteor, the ballistae): the foe can't counter them, they never counter, and their wielder never strikes twice
  (overlay 00 0x21f417c; Shadow Dragon's has the same code at 0x21c8488-0x21c84cc).
- **No damage** (overlay 00 0x21f3600): Imhullu equipped, unless the foe's weapon is Starlight; the Darksphere held, unless the foe holds
  the Lightsphere; the Magestone or Mage Breath, against magic. Glower (+0x28 0x800) ignores Def and Res.
- **Healing staves** (arm9 0x204b004): the staff's HP + Mag / 2 + the staff rank bonus (C +1, B +2, A +3), held at max HP; Fortify heals
  every unit of the army but the user.
- **Never wears out**: +0x24 0x10000000 (+0x27 0x10; arm9 0x20515d0): the Falchion, Imhullu, the breaths, the Fire Emblem.
- **Who may use an item** (the equip check, arm9 0x204f870): the unit's attributes (person +0x2c | class +0x38 | unit +0x90, which the
  placement's +0x0c is OR'd into) against the lock bits (+0x2a): 0x0004 needs 0x02 (the Falchion), 0x0008 0x04 (the Rapier), 0x0010 0x08
  (Aum), 0x0020 0x20 (the Wing Spear), 0x0040 0x40 (Hammerne), 0x0100 0x200 (the Divinestone), 0x0200 the class's archer kind (the
  Longbow), 0x0400 men only (Excalibur), 0x0800 women only (the Lady Sword, Aura, Nosferatu); 0x0001 and 0x0002 let Linde and Merric use
  theirs from rank E. Dragonstones need a manakete (or the Shadow Dragon) class, ballistae a ballistician.
- **The triangle and rank bonuses** (overlay 00 0x21f2a74): Shadow Dragon's; the staff rank bonus adds to healing.
- **Supports** (overlay 00 0x21f2e0c, `scripts/build-fe12-supports.py`): each of a unit's own five partners in its army within 3 steps
  adds by its level: C Hit and Avoid +5, B +10, A +10 and Crit and Crit avoid +5; several add up; the Geosphere adds Crit +10 to every
  ally within 3 (they stack); none in the arena, and the foe's army in the story gets none.
- **The forge** (arm9: shop::RefinePower, RefineHit, RefineCritical; the price at 0x2068c70): Mt +-10 (0 to 30), Hit +-50 (0 to 200),
  Crit +-30 (0 to 50); Shadow Dragon's price over three stats (`src/logic/fe11Forge.ts`). Not staves or items, nor +0x2b 0x40
  weapons, nor a forged copy (0x206debc). Only at the battle preparations' armory (MapTableData +0x18 0x04: Chapter 1 on; 0x2071090
  hides it elsewhere); at most 50 forged weapons at once (0x205501c).
- **The modes** (arm9 0x204c45c, as a placement makes its unit): a record with +0x2c 0x10 (most generic foes) or 0x100 (bosses) gains k
  x MapTableData +0x16 levels of growth (k: Hard 2, Maniac 4, Lunatic and Reverse Lunatic 5) in HP, Str, Mag, Skl, Spd and Lck (Def and
  Res only by the person's own growths for the modes, +0x1c), its shown level unchanged; weapon ranks raised to C, B or A; and its
  weapons step up (0x204c974): the tier T = MapTableData +0x17 - 2 on Hard, - 1 on Maniac, held 0-4; a lower-tier weapon becomes its
  kind's weapon at T (arm9 0x20ff888: Iron, Steel, Silver, Silver, Brave; Fire, Elfire, Bolganone, Bolganone, Thoron), forged Mt +4, Hit
  +20 at T 3; a 0x7d weapon is forged at T 2 (Mt +4; +8 at T 3; Hit +20), a 0x7e one at T 3; on Lunatic the breaths become their 1-2
  range versions; a slot flagged 0x100 never changes, and a dropped item only in the first slot (the foe then keeps a copy that drops).
  Reverse Lunatic is Lunatic's 5 with the global flag 0x400000: when your units attack, the foe strikes first (overlay 00 0x21f56fc),
  and its turn limits are 180%. Casual (fallen units return) is a flag of its own; it changes no data.

## Not confirmed

- That a forge greys out for the rest of the chapter (one weapon per chapter): where the flag it sets is cleared isn't traced.
- Hidden treasure (handler type 0x18): read as found by the unit in its area (MindGetUnit, ItemGet); what about the unit's move sets it
  off isn't traced.
- Nosferatu's drain: its +0x28 0x100 (its help text says it drains) isn't read anywhere the battle code was traced, so the weapon page doesn't say it. The Darksphere's and Lightsphere's effects beyond what's listed are their help texts'.
- The online shop's stock (downloaded) isn't on the cartridge: its items aren't sources yet.
