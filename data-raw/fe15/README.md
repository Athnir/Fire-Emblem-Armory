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
  royal chambers, Thabes' two gatekeepers, and Fear Mountain Shrine's statue of Duma (`Dng_迷路_恐山のほこら１` asks "Test yourself
  in battle?" and runs `DungeonBattle('戦場_恐山のほこら_像')`: the shrine's first encounter field with Player and 恐山１の像; winning
  sets `G_恐山のほこら１_ドーマ像_撃破済み`, and the statue then gives Duma's Lance and fights no more). What a boss battle's foes
  carry, and what a dungeon's script gives for winning it, count on that battle's map.
- **The lists**: the story (the battles everyone fights), the optional battles (those the world map lets you leave unfought: another
  way on in `Data/Chapter.bin`'s links and no move check in `Scripts/GMAP.cmb` needing them won; Act 6; the amiibo ordeals) and the
  skirmishes (every dungeon's wandering foes' fields), the user's calls. Of the deserts before Grieth's Citadel one is fought: once
  either army falls, GMAP sends the other to the citadel (`GMapEscape`), so the Southern Desert is optional. Each map outside the
  story opens with the first story battle after it on the world map (`fe15Opens.ts`), Act 6 with the Final Battle, the amiibo
  dungeons with Act 3.
- **Story order**: Acts 3 and 4 run both armies at once, Alm's battles first where the game allows it. In Act 4, Alm reaching the
  Dragon's Maw before Duma Tower is cleared springs its trap (GMAP `IsMoveAfterDra`) and shuts the road on to Rigel Falls until
  `G_ドーマの塔4_クリア` is set (`ev::DraOpen`), so Celica's Act 4 comes between Alm's Dragon's Maw and Rigel Falls. Act 6 waits on
  a request: its world map announces "A foreign trading ship has arrived at Zofia Harbor." and keeps Archanea Seaway 1 shut until
  quest 40 (`G_SUB_40遙かなる遠き大地`) is taken.
- **Cemeteries and the Dragon's Maw** (`Data/Chapter.bin`'s 配置 table: a DID_ record per world-map node, its count and a list of
  28-byte entries [dispos, group, target, 0, kind, act, figure, level]): kind 1 is the army a node holds from the start (a cemetery's
  first layout: Group1 at Novis and the mountain graveyard, Group5 at the swamp graveyard; a castle's Enemy and Reinforce groups), kind
  3 an army that gathers there again after a battle (a cemetery's layouts, each with a figure: 100 at Novis, 20 or 30 elsewhere), kind 2
  the army a level brings (the Dragon's Maw Interior: 竜の火口.cmb's closing handler raises its level by one each win in Act 4, at most
  5, with `SpotSetDisposLevel`, and levels 1-5 bring 7, 10, 13, 16 and 20 Necrodragons, figures 100, 100, 50, 30, 10). These armies'
  records have no tiles: they take the battle's Enemy records' (PID-less ones at a cemetery). The mountain graveyard's setting also
  places a request's Revenant (SUB29ゾンビ with the Red Tricorn, SUB33ゾンビ with the Duma Carving) on a later battle while its
  request is open, by a counter and a saved random number. A first battle is in the story; the later ones are a skirmish map.
- **Encounter picks**: an encounter in a group (`グループ`) is one pick among the group's, the empty picks (`DID_なし`) included, so its
  chance is its figure (`出現率`) over the group's; one in no group is there at its figure, or (`出現フラグ` a request's `G_SUB_…配置`)
  while that request is open. A line from a later act (`出現章`) waits for that act under the spoiler block (`notesOn` with `from`).

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

## Downloadable content (not in the user's files)

The user has no DLC, so `scripts/fe15_dlc.py` transcribes it from Fire Emblem Wiki ("Downloadable content in Fire Emblem Echoes: Shadows
of Valentia" and each weapon's and map's page), to be replaced by the DLC's own files when they can be read. Eight weapons: Fernand's,
Clair's and Clive's Lances, Python's Bow and Lukas's Shield (Rise of the Deliverance's rewards), and the Trainee's Lance, Wayward Lance and
Warrior's Sword (given with Cipher Companions' recruits). A wiki forge row's "worth" is the mark value plus every star's cost so far and
its stats are totals (the cartridge's Steel Lance and Blessed Lance read the same way), so `build-fe15-items.py` turns them into each
star's cost and bonus. Their arts are the cartridge's own (Skill.bin by English name), each checked against the SP the wiki gives; Armor
Disruptor, Heaven or Hell and Solo Triangle Attack are only the DLC's. The rewards count from Act 1's first battle (the DLC is played
from the world map's Connect menu: Prima Games' and Twinfinite's guides) behind "Show DLC items". Left out: the Ancient Ring (Clair holds
it only during Flight from the Ruins) and the DLC's non-weapon items. Not drawn: the DLC's 22 maps (the wikis have no tiles for them;
Cipher Legends I and II replay Ram Valley and Novis Cemetery with new units).

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
- Hard levels (`0x42df34`): a placed unit's level is its record's +7 (0: its person's `LV`), plus the record's +8 when the difficulty
  byte is 1 (Hard; +9 for a 2, which every record leaves at 0). The amiibo ordeals' guards carry +1 to +5 by room this way, as Fire
  Emblem Wiki gives. A summoned unit's level is its summoner's person +0x27 (`召喚レベル`), plus +0x28 (`召喚ハード`) on Hard
  (`0x458ae8`). The unit setup (`0x355834`) also adds a battle variable, `配置レベル差`, which no script sets. No read of the
  difficulty byte touches a stat, so Hard changes levels and placements only.

## Not confirmed

- Everything about the DLC (above): the wiki's, not read from files.

- Act 3's order: both armies' battles run at once and nothing in the world map's script orders them; the lists put Alm's first.
- How an army's records pair with a battle's Enemy records (taken in record order), what the cemeteries' and the Dragon's Maw's figures
  do (a chance or a weight), and how an encounter group's pick is made (read as weights from the table): not traced in the program.
- When a cemetery's layout is picked, and where and when Zofia Castle's and Rigel Plains' tile-less foes come in.
- Support bonuses: their 3-tile range and how ranks stack are Serenes Forest's.
- A weapon's mark value traded in at a blacksmith for half: Serenes Forest's exchange table.
- The Sage's and Hexlock Shields' misnamed arts: what the game does with them.
