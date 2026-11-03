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
  from the bottom row.
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
