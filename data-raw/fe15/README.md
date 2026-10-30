# Fire Emblem Echoes: Shadows of Valentia (FE15) game files

Read from the user's own dump in `Documents\FE Games`: the cartridge image `Fire Emblem Echoes Shadows of Valentia.3ds` (North American,
CTR-P-AJJE, decrypted: its NCCH has the NoCrypto flag; partition 0 at 0x4000). `scripts/fe15_extract.py` copies what the Armory reads into
`data-raw/fe15/romfs/` (git-ignored, never committed): the romfs's `Data/`, `GameData/`, `Scripts/`, `map/`, `GlobalMap/`, the English text
`m/@NOA_EN/`, `params.bin.lz`, the exploration fields' placement files `field/*.bin.lz` (not their models), and the program (`code.bin`:
the exefs `.code`, BLZ-decompressed, loaded at 0x100000). Only data built from them is in the repo. The user has no DLC for this game.

## Containers

- **`.lz`**: a 0x13 header, then LZ11 (`scripts/fates_lz.py`).
- **Binary data files**: Awakening's layout (`scripts/fe13_bin.py`), but Echoes' tables describe themselves (`scripts/fe15_bin.py`): each
  file opens with `MOD_<table>` (a field count, then per field a name, a type name, minimum, maximum and step) and its records follow
  `DAT_<table>`, one label per record. Types: `str` and `ptr` (4 bytes), `s8` / `u8`, `s16` / `u16`, `u32`, `f32`; records are packed in
  field order. Event files label only each sequence's first row (`Table(..., every=True)` reads them all).
- **Text** (`m/@NOA_EN/*.bin.lz`): label -> UTF-16 string (`scripts/fates_text.py`). Places and people are in `Name`, items in `Item`,
  skills and arts in `Skill`, classes in `Job`.
- **Scripts** (`Scripts/*.cmb`): Fates' bytecode (`scripts/fates_cmb.py`). Handler kinds Echoes uses: 0x05 flags, 0x07 load
  (`ChapterSetWinRuleDestroyBoss`: defeat the boss, else rout), 0x08 setting (DefaultMapSetting), 0x0b the opening scene, 0x0d the
  closing scene, 0x10 / 0x12 a turn's phase (first, last, phase), 0x13 reinforcements (first turn, last turn, phase 1 = enemy: the
  handler names the group and a shared routine places it), 0x14 a condition, 0x15 a terrain tile (`_Terrain.cmb`), 0x17 a battle talk,
  0x1a a death quote, 0x1b a defeat count, 0x1c a talk, 0x27 a medal.

## Tables (`scripts/fe15_data.py`)

- **Item** (`Data/Item.bin`): the fields by name (`種類` kind: 1 sword, 2 lance, 3 axe, 4 bow, 5 black magic, 6 white magic, 7 monster,
  8 valuable, 9 shield, 10 ring, 11 provision, 12 headgear, 13 / 14 silver / gold marks, 15 other; `威力` Mt, `重さ` Wt, `命中` Hit,
  `必殺` Crit, `回避` Avoid, `必殺回避` crit avoid, `内射程` / `外射程` range, the stat bonuses, `スキル1-4` (#2: a second set) the skills it
  gives, `戦技1-4` the combat arts it teaches, `練成` its forge list, `進化` its evolution list). `フラグ`: 0x02 a class's unarmed default
  or an illusory hero's weapon (not an item; the monsters' weapons carry it too), 0x80 a lord's own with 0x20 Alm's or 0x40 Celica's
  (matching Serenes Forest's "Alm only" / "Celica only").
  - **Forge lists** (`錬成`, `RID_<weapon>`): [name, count, pointer] to 10-byte rows: u16 silver marks, u16 gold marks, s8 Mt, s8 Wt,
    u8 Hit, u8 Crit. The first row is the weapon's value in marks (Serenes Forest's exchange table gives half); each further row is a
    star: what it costs and the weapon's total bonuses at it (all checked against Serenes Forest's forging tables).
  - **Evolutions** (`進化`, `EID_<weapon>`): 12-byte rows [target IID, u16 silver, u16 gold, u8 stars needed, 3 unused]. Each Rusted copy
    is its own item (`IID_錆びた剣_勇者` becomes the Brave Sword): the outcome is fixed when it's made.
  - Two shields name arts no skill has (`SID_G.物理半減`, `SID_G.魔法半減`, with a stray dot; the table's are `SID_G物理半減` and
    `SID_G魔法半減`). Kept as the game has them.
- **Skill** (`Data/Skill.bin`): a combat art's `経験値` is the weapon mastery that teaches it, `消費HP` its HP cost, `威力増減` /
  `命中増減` / `回避増減` / `必殺増減` / `射程増減` its bonuses, `回数` its hits, `攻撃率` its attack percentage, `特効` (+0x37) the class
  kinds it's effective against (2 horseback, 4 armour, 8 fliers, 32 Terrors: a class's `種別`).
- **Job** (`Data/Job.bin`): `武器` the weapon types (bits 2 sword, 4 lance, 8 axe, 16 bow, 32 black magic, 64 white magic, 128 monster,
  0x100 items), `種別` the class kinds, `移動タイプ` the movement row, `基本装備1-2` the weapon it fights with when nothing is equipped.
- **Person** (`Data/Person.bin`): `フラグ` 0x01 generic, 0x02 named; `LV`; `所持アイテム` what they carry when they join; `落下アイテム`
  and `落下率` what a foe drops at random, and how often (a percentage as stored: 0.09 is 0.09%, as Fire Emblem Wiki gives).
- **Chapter** (`Data/Chapter.bin`): the world map's nodes: `種類` 2 a battle, 3 a place or dungeon, 4 a path; `章` the act; `ルート` 1 Alm,
  2 Celica; `上/左/下/右連結` its links. **Field** (`Data/Field.bin`): a dungeon floor's encounter field, and each field's terrain and
  placement files.
- **Terrain** (`Data/Terrain.bin`): `コスト` the cost category (a column of `地形コスト`: 0 none, 1 sky, 2 floor, 3 forest, 4 desert,
  5 bulwark, 6 mountain, 7 river, 8 lava, 9 hill), `回避` Avoid, `回復` HP healed (or lost) each turn. No terrain gives Def.

## Battles (`scripts/build-fe15-maps.py`)

- **Grid** (`Data/Terrain/<map>.bin`): a 0x20 header, then u32 width, height and the playable window x1, y1, x2, y2 ([x1, x2) x [y1, y2),
  from the top left), then 32 x 32 tile ids. The window is the wiki's size for every map.
- **Units** (`Data/Dispos/<map>.bin`): groups of [name, count, pointer] to 96-byte records: +0 PID, +6 team (0 yours, 1 enemy, 2 green),
  +7 level (0: the person's own), +10 u16 flags (0x01 Normal, 0x02 / 0x04 Hard, 0x10 the boss, or the lord's slot), +12 start x, y and +14
  end x, y (0, 0: none), +20 its one item, +24 bit 0 the item drops, +32 its army, then the AI. The setting places Player, Enemy and the
  NPC groups (plus any group its load or setting handler names); the opening scene's Event groups are actors. A Reinforce group with no
  tiles (Zofia Castle's Slayde, Rigel Plains' Zeke) joins later: the map names them in its notes.
- **Dungeons**: a floor's wandering foes (`Data/Encount/<floor>.bin`: chance, the act from which they appear, the rare-monster flag, the
  group in the field's placement file) start a battle on the floor's encounter field. `Scripts/Encount.cmb` sets your units on Player
  (Player_Good when you strike first; the foes then lose 5-19% of their HP) and the foes on one of five formations (EnemyU, UL, UR, L, R);
  a group with its own tiles (a gatekeeper, the amiibo ordeals' guards) stands on them. A foe's `ダンジョンID` names its record in
  `Data/Dungeon.bin`'s `敵情報`, whose `スクリプト` is the battle script: the amiibo ordeals' guards run `Scripts/戦場_amiibo.cmb` (no
  wandering foes; the same first strike), which on turn 1 takes the item drop off any guard already beaten (its death sets
  `G_戦神の試練_<n>` / `G_女神の試練_<n>`), so each guard's item drops once. Boss battles: the Brigand Boss, Berkut, the three
  royal chambers, Thabes' two gatekeepers.
- **Cemeteries**: Group1-5 are layouts; the battle setup in the program picks one (not decoded).

## Sources of items

Dungeon chests and glinting finds (`Data/Access.bin`: per floor, 76-byte records: +0 the part, +4 kind 1 chest / 10 find, +8 the item),
barrels, pots, boxes and grass (`Data/Dungeon.bin`'s DG_<floor>: container -> a DL_ list of [item, weight]), drops (a placement's drop
flag; a person's random drop with its rate), what foes carry (an item or their class's own weapon), villagers' and the story's gifts
(`Data/Event/<place>.bin`'s アイテム入手, with the act the calls leading to it need) and the scripts' ItemGain, who joins carrying what
(the lords from their army's first map, the rest from the events' 仲間入り), and evolving at a blacksmith (the Forest Village's,
the Mountain Village's, Rigel Village's, the Sage's Hamlet's and Furia Harbor's), counted from when both the weapon and a blacksmith
are reached. A place's sources count from the next chapter after the battle beside it on the world map; an act's start (Ram Village,
the Priory) from that act's first battle. The amiibo dungeons' sources sit behind their own switch. Left out: the 7-Eleven quest's Seven
Sword and Eleven Shield (a Japanese promotion), the illusory heroes' weapons, the classes' unarmed defaults and the spells.

## Mechanics checked in the program (`scripts/fe15_code.py`)

- Hit (`0x30c7d8`, also `0x30c568`): one number 0-9999 (the game RNG, `0x63be78`) against the displayed hit x 100, from 50 up plus
  40/3 x hit x sin((hit - 50) x 180 x 0.02 degrees): Fates' curve. The displayed hit is the side's hit (weapon Hit with its forge, `0x466268`,
  plus a stat and skills, `0x45207c`) minus the other side's avoid, plus the art's, held between 0 and 100 (`0x2eede8`).
- Effectiveness (`0x2f0aa0`): a weapon effective against the target adds its Mt twice more (x3); an art effective against it adds its own
  Mt bonus twice more (the weapon's Mt isn't tripled).
- Terrain (`0x32066c`, `0x32114c`): healing and damage are HP, not a percentage (5 HP, at least 1 left).
- Support points (`params.bin`'s tuning values, `scripts/build-fe15-supports.py`): +1 for being deployed together, +1 for fighting 1 or
  2 tiles from the partner (0 at 3 or 4), +2 for a staff used on the partner, at most 20 in a battle.
- No weapon triangle: no triangle table in the data, and the hit and attack routines above have no triangle step.

## Not confirmed

- The story's order in Acts 3 and 4: both armies' battles run at once; the map list and the spoiler block put Alm's first.
- When a cemetery's layout is picked, and where and when Zofia Castle's and Rigel Plains' tile-less foes come in.
- Support bonuses: their 3-tile range and how ranks stack are Serenes Forest's.
- A weapon's mark value traded in at a blacksmith for half: Serenes Forest's exchange table.
- The Sage's and Hexlock Shields' misnamed arts: what the game does with them.
- The amiibo ordeals on Hard: Fire Emblem Wiki gives their foes higher levels (+1 in the first guard's room up to +5 in the last), but
  their placement records serve both difficulties and the rule that raises them isn't found in the program yet, so the maps give the
  placement files' levels.
