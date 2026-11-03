# Fire Emblem Engage (FE17) game files

Read from the user's own dumps in `Documents\FE Games\Switch dumps\NSP` (nxdumptool, from their console, keys in `~/.switch`): the
digital base game (`[0100A6301214E000][v0][BASE]`) and the 2.0.0 update (`[0100A6301214E800][v327680][UPD]`). The Expansion Pass's
content (the Divine Paralogues, Fell Xenologue, its emblems and items) is in the update itself; the two DLC packages
(`[0100A6301214F001]`, `[0100A6301214F002]`) are only its licences. `scripts/fe17_extract.py` copies what the Armory reads into
`data-raw/fe17/romfs/` (git-ignored, never committed). Only data built from them is in the repo.

Field names are the game's own: every data table names its fields, and the program's metadata names its types, enums and methods.

## Containers

- **The update's RomFS** is a patch (BKTR) over the base game's, read together by `scripts/switch_nsp.py` (as Three Houses').
- **Asset bundles** (`scripts/unity_bundle.py`): Engage is a Unity 2020.3.18 game whose data sits in Addressables bundles under
  `Data/StreamingAssets/aa/Switch/`, one asset each. A bundle is UnityFS (format 7): its blocks info and blocks LZ4/LZ4HC-compressed;
  inside, a serialized file (version 22) whose objects are read through the type trees it carries (the strings type trees share are
  Unity's own list, `COMMON`). Each asset is a TextAsset (`m_Script`: the data) or, for the terrain grids, a MonoBehaviour.
- **Data tables** (`fe_assets_gamedata/<name>.xml.bundle` -> `romfs/gamedata/<name>.xml`, `fe17_data.book`): XML books, each sheets of
  a header (`<Param Name="日本語" Ident="Field" Type="..."/>`) and rows of the same fields. Paths in the bundles end `Patch3/...`: the
  update's last version of each. `gamedata/dispos/<map>.xml` is each battle's units.
- **Terrain grids** (`fe_assets_gamedata/terrains/mapterrain_<map>.bundle` -> `romfs/terrains/*.json`): a MapTerrain object: `m_X`,
  `m_Z`, `m_Width`, `m_Height` (the map's window) and `m_Terrains`, 32 x 32 terrain ids (`TID_平地`...) by z * 32 + x, z counting up
  from the bottom row; `m_Layers` (`App.MapTerrain.LayerData`: X, Y, W, H, Group, Attr), what stands over the grid at the start:
  doors, rickety walls, junk, fences and roofs, a group's opening together (Chapter 15's doors and the roofs of their rooms); and
  `m_Overlaps` (X, Y, Attr), what lies over single tiles at the start: Dragon Vein fog, water, stone pillars, flames and frost, and
  miasma.
- **Scripts** (`fe_assets_scripts/<name>.txt.bundle` -> `romfs/scripts/*.lua`): each battle's Lua source, run by MoonSharp (the
  program's `MoonSharpAD.dll`): Lua 5.2 with doubles for numbers, `!=` for `~=`, Japanese names, bit32. Its parser lets an `if`
  stand where `elseif` goes after a block a `return` ended (g001's and g004's `ボスのPIDを取得` rely on it). `scripts/fe17_lua.py` runs
  them.
- **Text** (`fe_assets_message/us/usen/<name>.bytes.bundle` -> `romfs/message/*.msbt`): MSBT (UTF-16): LBL1 labels (`MIID_IronSword`)
  and TXT2 strings; control tags are 0x0E (u16 group, type, size, params) and 0x0F (closing). The data tables name text by label.
- **The program** is IL2CPP: its code the update's `main` NSO (`romfs/main.bin`, decompressed and relocated, loaded at 0), its names
  `Data/Managed/Metadata/global-metadata.dat` (version 27). `scripts/il2cpp.py` reads the metadata (types, methods, fields, enum
  constants) and finds each method's code through its assembly's code generation module (a record starting with a pointer to the
  module's name, `Assembly-CSharp.dll`, then its method count and pointer table, indexed by each method's token row less one).

## Tables

- **Chapters** (`chapter.xml`, sheet チャプター, 92 rows): `Cid` (`CID_M001`), `Dispos`/`Terrain`/`Field` (a `*` means the chapter's
  own name), `NextChapter`, `GmapSpot...` (its place on the world map: `GmapSpotOpenCondition` the chapter that opens it), `Reward`,
  `HoldLevel`, `Flag` (`App.ChapterData.Flags`: 1 Sally, 2 CanBack, 4 Sight (fog), 8 Kizuna, 16 Hub, 32 Gmap, 64 Continue, 128 Serious,
  256 Casual, 512 Challenge, 1024 Relay, 2048 Versus, 4096 TestMap, 8192 Opposition, 16384 HighRankItem, 32768 CanSlope),
  `RecommendedLevel`. M000 is the Prologue, M001-M026 Chapters 1-26 (`MCID_M026_PREFIX` 'Chapter 26', the last), S001-S015 the
  paralogues ('Paralogue'), G001-G006 the Divine Paralogues (DLC, 'Divine Paralogue'), E001-E006 Fell Xenologue (DLC, 'Fell Xenologue
  1'...), C001-C006 (and C000) the Tempest Trials (`MID_CHALLENGE_*`; sheet やり込み lists each trial's stages, opening with Chapter 11
  or 13), N001-N006 the Relay Trials' maps (`MID_RELAY_*`; a Tempest Trial's fourth stage is fought on one), V001-V002 the versus maps.
  Names: `MCID_<cid>_PREFIX` ('Chapter 4'), `MCID_<cid>` ('A Land in Bloom'), `MCID_<cid>_PLACE`.
- **Units** (`dispos/<map>.xml`): rows in groups (a row naming `Group` starts one: Player, Enemy, Ally, then the script's own:
  `Event1`, `Reinforcement0`...). `Pid` (person), `Force` (0 yours, 1 foe, 2 green), `Flag` (`App.DisposData.Flags`: 1 Normal, 2 Hard,
  4 Maddening (`Lunatic`), 8 Create, 16 Leader (the boss), 32 NotMove, 64 Edge, 128 Pos (a deployment tile), 256 Must (forced), 512
  Fix (on its tile), 1024 Guest), `DisposX`/`DisposY` its tile (x across, y up from the bottom row, 0-based), `AppearX`/`AppearY`
  where it walks in from, `LevelN`/`LevelH`/`LevelL`, `Jid` (class; empty: the person's), `Item1.Iid`..`Item6.Iid` with
  `ItemN.Drop`, `Sid`, `Gid` (an emblem it's bound to), `HpStockCount` (revival stones), `AI_*`.
- **Items** (`item.xml`, sheet アイテム, 661 rows): `Iid`, `Name`/`Help` (text labels), `Kind` (`App.ItemData.Kinds`: 1 Sword,
  2 Lance, 3 Axe, 4 Bow, 5 Dagger, 6 Magic, 7 Rod, 8 Fist (Arts), 9 Special, 10 Tool...), `UseType`, `WeaponAttr` (1 Fire, 2 Thunder,
  3 Wind, 4 Ice, 5 Light, 6 Dark), `Endurance` (uses; 255 none), `Power`, `Weight`, `RangeI`/`RangeO`, `Hit`, `Critical`, `Avoid`,
  `Secure` (dodge), `Enhance.*`, `Price`, `WeaponLevel` (E-S), `Flag` (`App.ItemData.Flags`: 1 Rarity, 2 NotTrade, 4 CanUse, 8
  OnlyChapter, 16 OnlyEnemy, 32 OnlyMale, 64 OnlyFemale, 128 Engage, 256 IgnoreWeaponLevel, 512 Unpublic, 65536 ReverseAttribute (the
  magic weapons that hit Res), 524288 RangeTarget...), `EquipSids` (skills the weapon carries: effectiveness `SID_鎧特効`, brave
  `SID_２回行動`, smash `SID_スマッシュ`...), `HighRankItem`. Other sheets: 錬成 (refining), 進化 (evolving), 武器レベル (weapon
  levels), 相性 (the triangle), 報酬 (reward pools).
- **Shops** (`shop.xml`): 武器屋 (armory), 道具屋 (item shop), 蚤の市 (flea market), アクセサリー屋: rows naming a `Condition`
  (`M004`, `M011,CC_マージカノン`) start a block of stock: `Iid` and `Stock` (-1 unlimited).

## Mechanics read in the program

- **Hit** (`App.BattleMath`): `_IsProbabilityHit` draws one number 0-9999 (`App.Random.Game`) and hits when it's below
  `GetHitRatio10000(hit)`: hit x 100 below 51 and at 100, else hit x 100 + (40/3) x hit x sin((0.02 x hit - 1) x 180 deg) in single
  precision, truncated (`0x1e8d200`). Fates' hybrid: the same at every displayed hit 0-100 as the app's `hybrid-fates`.
- **Script events** (`App.ScriptMap.EventEntry*`): each makes an inspector (`App.TurnInspector`...) holding the function, the
  arguments and a condition. `App.MapInspector.IsCondition`: none, true; a boolean, itself; a function, its result; a string, a
  variable's name: the event runs while that variable doesn't hold the done value.
- **Script events, played** (`scripts/fe17_events.py`): the program places a battle's `Player`, `Enemy` and `Ally` groups itself
  (its own string literals; the skirmishes' `Player0` and `Mob00`), calls the script's `MapDispos` hook, `Startup` (the events
  registered) and `MapOpening`. Turn events (`EventEntryTurn`, `...TurnAfter`, `...TurnEnd`: function, first turn, last turn, the
  phase's army, condition, the function's arguments; -1 any turn) run at their phase on their turns while their condition holds.
  Coordinates are the units' and terrain's own (x across, z up from the bottom row, 0-based); a village is visited from the tile in
  front of its door (`TID_民家入口`, the house's own tiles impassable). A placement's `AppearX`/`AppearY` of 0, 0 (most rows) means
  it appears on its tile; anything else is where it walks in from. `UnitTransfer` moves a unit to another army (Chapter 2's opening
  sends Lumera to the foes).
- **When each group comes** (`build-fe17-maps.py`'s `arrivals`): the turns are played to 40 with nothing else happening, which gives
  each group every turn it comes on ("Every third turn from 13", "Turns 6, 12 and 13"; a step seen three times that reaches turn 40
  goes on). Then each of the chapter's events is brought about on its own (`Battle.happen`: the unit that sets it off, the one it
  acts on, a defeated unit leaving the map, then your units' end-of-action events), and so is each unit's AI starting
  (`AiGetActive`), each set of like events at once (Chapter 22's eleven emblem talks), a unit standing where a condition reads its
  tile (the tiles where it holds: Chapter 9's forts, Chapter 22's rings), and tiles emptied or held where a condition reads who stands
  on them (Chapter 11's escape tiles): what that places at once comes "when" it happens, what the turns then place comes so many phases
  after it (the same cause brought about five turns later moves it as far; four, on a turn picked as odd or even: Fell Xenologue 3),
  or on its own turns "once" it has happened, and what it keeps from coming is "until" it happens. An event whose condition reads only
  the script's own variables, the difficulty and the turn, and doesn't hold, can't happen then.
- **Terrain** (`terrain.xml`): Def, Avoid and healing per tile, with army-specific Def and Avoid (`PlayerDefense`...: miasma, -20 for
  your units and +20 for foes), `MoveFirst` (Mov at the start of a move: frost +2, quicksand -3), `Hp_N/H/L` and `Destroyer`
  (`App.TerrainData.Destroyers`: 2, foes only) for what can be broken, `Flag` (`App.TerrainData.Flags`: 1 Door, 1024 Roof, 16384
  FlyEnable...). Healing is HP, not a share (`App.MapSequenceTurnBeginEffect.ProcTerrainHeal`: the tile's and its overlap's `Heal`
  added, handed to `App.Unit.PlaySetHeal`; damage the same, from a negative `Heal`), and a flier is healed or hurt only on a tile
  flagged FlyEnable (`App.TerrainData.IsFlyEnable`). An overlap's numbers add to its tile's (`App.BattleDetail.CalcAvoid`: the
  terrain's Avoid, then the overlap's), and its move cost adds to the tile's (`App.TerrainCostData.GetCost`: `MoveCost` on foot and
  horseback, `FlyCost` for fliers and dragons).
- **Map changes the scripts make** (`TerrainSet` after the opening): the tiles one moment sets are a change, timed as a group is
  (Chapter 16's tide every other turn, Chapter 22's ring pedestals as each set of emblems appears, Chapter 26 once Sombron falls,
  the Lonely Heir's sky castle once its switches are held); one that puts tiles back as they started is said with the change it
  undoes. A razed village's house turns to ruins, both buildings no unit enters, so it's no change on the map.
- **Doors and breakables**: each layer group is a change, previewed as the tiles under it. A door (Flag Door) is attacked down by its
  HP, or a Thief opens it with the Door command (the class's `SID_鍵開け`; the game's tutorial: "A thief can use the Door command to
  unlock a door instead of destroying it"); rickety walls, junk and fences are attacked down; Paralogue 5's wall only foes break.
  A roof (Flag Roof, impassable) closes its room until its group's door opens.
- **Weapon skills** (`skill.xml`): a weapon's effects are the skills it carries. An effectiveness skill names its target by
  `Efficacy` (2 cavalry, 4 armour, 8 flying, 16 dragon, 64 corrupted) and its multiplier by `EfficacyValue` (3); others are actions
  (`ActNames`, `ActOperations`, `ActValues`: 行動回数 x 2 strikes twice, 吹き飛ばし Smash, 手番回数 = min(手番回数, 1) no follow-up,
  ユニット攻撃力 = (力+魔力)/2 the Arts' attack...).
- **Forging** (`item.xml`): 錬成 (refining) gives each weapon (`RID_<item>`: the item's id with IID_ for RID_,
  `App.ItemRefineData.Iid2Rid`) five levels, each with its Mt, Wt, Hit and Crit added in all at that level (`App.UnitItem.GetPower`
  adds the level's row to the item's) and the Iron, Steel, Silver and gold the step to it costs (`App.UnitItem.GetNextRefineData`: the
  next level's row); only the 92 base weapons have one. 進化 (evolving) turns a weapon (`EID_<item>`) into others for Iron, Steel,
  Silver and gold. The smithy opens once Chapter 5 is cleared (hubarea.xml).
- **Looters** (`ai.xml`: each AI routine a list of commands; a placement's `AI_*` slots name the routines and their parameters,
  `pos(x,z)` tiles): `AI_MV_TreasureToEscape` goes for the chest in its first field (command 94), then switches its mind to
  `AI_MI_Escape` and leaves by the tile in its third (96); `AI_MV_VillageToAttack` goes for its village (95), razing it, then switches
  its attack to `AI_AT_Attack`; `AI_MV_Escape` leaves by its tile; `AI_AT_Null` never attacks; `AI_AC_Turn` waits for its turn. A
  script's `AiSetSequence` (slots `AI_ORDER_*`: 0 cause, 1 mind, 2 attack, 3 move) changes them: an event that does is said on the unit
  (Chapter 4's bandit turns to the other village once its own is visited). A village names the raiders on the map at the start.
- **Engage weapons** (`god.xml` sheet 成長表: each emblem's growth table, `EngageItems` for any unit and a column for each unit type,
  `EngageCooperations`... named by the game's `MBSID_` text: Backup, Cavalry, Covert, Armored, Flying, Mystical, Qi Adept, Dragon):
  an emblem's weapons at each bond level, wielded only while engaged (the item's Engage flag), never sold. An emblem is yours from the
  chapter after the battle whose script creates it (`UnitCreateGodUnit`/`GodUnitCreate`: Marth in Chapter 1, Celica with Céline in 4)
  or whose placements bring it with a unit who joins (Roy with Diamant in 8), or whose bond scene does (`m003_kizuna`: Sigurd); a Divine
  Paralogue's after it (`神竜の章_紋章士加入`), Edelgard, Dimitri and Claude's on the Somniel once Chapter 6 is cleared. A weapon above
  the emblem's bond cap (`LevelCap`, 11 for the story's twelve) comes once its paralogue lifts it (`紋章士外伝_レベルキャップ開放`:
  The Hero-King for Marth); Emblem Alear's Oligoludia (bond 20, cap 11, nothing lifts it) is left out.
- **The triangle** (`item.xml` sheet 相性): each weapon kind's bits name the kinds it beats (bit n kind n; 10-19 the same kinds
  reversed): swords beat axes, axes lances, lances swords, Arts bows, knives and tomes.

- **Supports** (`reliance.xml` sheet 支援効果; `App.SupportCalculator`): six types (デフォルト, バランス, 命中, 必殺, 回避, 必殺回避),
  each four rows (levels C, B, A and the ring: `App.RelianceData.Level` 1-4, 4 named APlus, "Ring Rank" in the text) of Hit, Crit,
  Avoid and Dodge. `Range` 1: each ally on a tile beside the unit with a support with it adds its own type's row at the pair's level
  (`App.UnitReliance.TryGetSupportData` takes the partner's person's SupportCategory), summed (`RangeFunction`).

- **Battle formulas** (`calculator.xml` sheet 共通): attack is Str or Mag (by the attack's kind) + weapon Mt x 武器特効 (3 when
  effective); hit Dex x 2 + Lck / 2 + weapon Hit + support Hit; avoid attack speed x 2 + Lck / 2 + weapon and support and terrain
  Avoid; crit Dex / 2 + weapon and support Crit; dodge Lck + weapon and support Dodge; attack speed Spd - max(Wt - Bld, 0); a
  follow-up at 5 more attack speed; 相性補正 (the triangle) 0 for advantage and disadvantage alike.

- **Divine Paralogues** (G001-G006, `dispos/g00n.xml`): two more columns, `LevelMin` and `LevelMax`, give each row a band (0-0: every
  level); a tile holds a row per band, weakest first (`App.MapDispos.CreateDlcGodDisposTeam`). A foe's level is the map's average
  level plus its person's own less 1 (`App.Unit.CreateDlcGodEnemy`), and its row is placed where that falls in its band
  (`App.DisposData.CanDispos`). The average (`App.MapSituation.AverageLevel`, set as the map's units load: `App.MapSequence.LoadDispos`)
  is `App.GmapUtil.GetAverageLevel`: `CalcEncountRank` (each of your units' `Level` plus `InternalLevel`, Vander's only once three of
  your units have an internal level of 10 or more (`GetVandreLevel`), the highest so many averaged, rounded, plus 2), then 5 less on
  Normal, 2 less on Hard, 1 more on Maddening, held between 1 and 99. The maps show the lowest band, each foe's note what it becomes at
  the others, and the foes only higher bands place as groups.

- **Skirmishes** (`dispos/<map>e.xml`, `scripts/<map>_encount.lua`): one per location whose file has foes (m021e is an empty stub):
  `Player0` the deployment tiles, `Mob00` dummy persons (`PID_ダミー`) the game fills when the skirmish starts
  (`App.MapDispos.CreateEncountDisposTeam`), the Leader flag on one; the classes from the location's pools (chapter.xml
  `EncountJobs`, each an encount.xml 敵兵種 `EJid` with its `Jobs`). When a skirmish appears, one of the location's pools is drawn
  (`App.EncountMob.SetRandomEncountJob`) and its rank (`App.GmapUtil.GetEncountRank`: `CalcEncountRank` over as many of your units as it
  has deployment slots, drawn between their average plus 2 and another figure from their levels, `App.Random.GetMinMax`). Each foe's
  class is one of the pool's, another where that class can't stand on its tile (`App.Unit.CalcEncountJob`: `IsNoMove`); its level the
  rank, the leader's more (`App.Unit.CalcEncountLevel`); its weapon its type's of a tier by rank (敵装備: Iron to 8, Steel from 13,
  Silver from 19, a share of Brave from 27; 武器カテゴリ: each tier's weapons and the thrown extras). The rank's other figure, the
  leader's bonus and how Enchanters and Mage Cannoneers enter the pools aren't traced to the end. A skirmish appears on the world map
  once its location is cleared.

- **Tempest Trials** (chapter.xml sheet やり込み): six trials, each opening once its `UnlockCid` is cleared; stages 1 and 2 are fought
  on one of the trial's four maps (`Stage1`, `Stage2`: CID_C00n_1-4, the fourth on a Relay Trial's field), stage 3 on one of six
  maps every trial shares (CID_C000_1-6). Each map has two line-ups (`Player0` with `Mob00`, `Player1` with `Mob10`; C000_3-6 one),
  their foes dummy slots like a skirmish's (Vicious Volcano's third map has a Phantom Wyrm of its own). The Armory gives a map per
  line-up (The Sacred Stones' rule); how the game picks a stage's map and line-up isn't traced.

## Checked against Fire Emblem Wiki

- **Starting foes** (`src/logic/__tests__/fe17.test.ts`): every story chapter's count on each difficulty matches the wiki's chapter
  page, counting what the opening places (Chapter 10's nineteen; Chapter 2's Lumera, sent to the foes by its opening); so do the
  paralogues', the Divine Paralogues' (the wiki's counts are the lowest army level band's) and Fell Xenologue's. Fell Xenologue is
  entered from the Somniel's Ancient Well (the wiki), which opens once Chapter 6 is cleared (hubarea.xml).
- **Reinforcement totals**, each group counted as often as it comes, match the wiki's where every group's turns are fixed (Chapters
  2, 4, 8, 12, 24 and 25, whose waves come every turn of a span: 28, 83 and 123; Paralogues 10 and 11; Fell Xenologue 2). The wiki
  doesn't count the waves that go on as long as the battle does (Chapter 22's every third turn from 13, Chapter 23's every other
  turn from 19, Paralogues 6 and 14), and counts Chapter 10's four Illusory Doubles, which Hyacinth's Emblem Lyn makes with Call
  Doubles in battle (no placement of the script's).

## Unconfirmed

- A terrain's battle prohibition (`Prohibition`, `App.TerrainData.Prohibitions`: All on Chapter 15's walkway floor, Ground on some
  stairs) isn't traced in the program: those tiles are drawn as the floor and stairs everyone crosses.
- A shop list's condition (`M004`) is read as "once that chapter is cleared": the Somniel's facilities open the same way
  (hubarea.xml), and the wiki says clearing Chapter 4 opens the armory and item shop. Not traced in the program.

