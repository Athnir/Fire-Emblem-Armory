# Fire Emblem Armory: the ruleset

Rules settled with the user while building Fates, Path of Radiance and Radiant Dawn. Follow them for every
new game, so the same fixes don't have to be caught again. When the user settles a new rule, add it here.

## Scope

- **Game data only.** Weapons, forging, shops, maps, true hit, and what supports do. Anything about specific
  units (affinities, who supports whom, growths, builds) belongs in the partner Unit Planner
  (`../Fates App`), not here. Units on a map are fine: they're chapter data.
- **One game picker; every tool for that game sits in the same tabs** (Weapons & forging, True hit, Weapon triangle,
  Maps, Supports). No extra menus or tool-picker steps. A game with nothing like supports has no Supports tab
  (`supports: null`); FE4's lover, Charisma and the like are a unit's own, so they're the Unit Planner's.
- **Finish one game across every tab before starting the next.** Fortune's Weave is skipped (too new for
  solid data).
- **Notes state data, not observations or strategy.** "Elise is ill" and how reinforcements arrive are data;
  "watch out for the archers" is not.
- **No per-map source notes.** Sources are listed once, in the README.
- **Only what the user owns.** Missing DLC is left out (or taken from wikis later), never obtained.

## Data sources

- **The game's own files first** (the user's dumps), then fireemblemwod.com / Serenes / the wikis for what
  the files lack, and minimaps or screenshots last.
- **Never commit or push dumped game files.** Only data derived from them goes in the repo.
- **Japanese-only games:** read the data from the clean Japanese files, never a fan-patched ROM. English names come from the
  community translation patch Serenes Forest hosts (Lil' Nordion for FE4, Lil' Manster for FE5, the FE6 Localization patch's
  `.ups` for FE6; they sit next to the ROMs in `Documents\FE Games`): the patch is applied in memory and only its name tables
  (FE6: its text, by the ROM's text ids) are read, by the ROM's own ids. Nothing patched
  is written or committed. Where the patch has no table (FE4's bosses), its dialogue's spelling is used; Serenes Forest, then
  fireemblemwod.com, then the wikis fill what the patch lacks.
- **Cartridge games (FE4 first):** read from the user's own ROM image in `Documents\FE Games` (outside the repo; `*.smc`, `*.gba`
  and the rest are git-ignored), with the readers in `scripts/fe4_rom.py` and the names in `scripts/fe4_names.py` (FE6:
  `scripts/fe6_rom.py`, `scripts/fe6_names.py`, and `scripts/fe6_events.py`, which plays the chapter scripts the way the engine
  does, so units stand where the openings leave them; FE7 and FE8, the English ROMs: `scripts/gba_rom.py` for both, `fe7_events.py` /
  `fe8_events.py` (FE8's event engine is another: u16 commands with slots, named from the fireemblem8u decompilation and checked in the
  code), `gba_maps.py` for what their maps generators share; FE5: `scripts/fe5_rom.py`, `fe5_names.py` (Lil' Manster draws its names
  from letter tiles, matched to its font's shapes) and `fe5_events.py`, named from the Lil' Manster build files and VoltEdge and checked
  in the clean ROM; FE3: `scripts/fe3_rom.py`, `fe3_names.py` (the translation patch's menu tables and its storage messages for full item
  names) and `fe3_events.py`, every table traced in Mesen and the game's code, with no disassembly to go by). Awakening (FE13, the
  3DS cartridge and DLC, decrypted): `scripts/fe13_extract.py` copies what's read into `data-raw/fe13/romfs` (git-ignored), with
  `fe13_bin.py` / `fe13_data.py` for its data files, `fe13_events.py` for its scripts (Fates' bytecode) and `fe13_code.py` for checking
  mechanics in its program. Echoes (FE15, the 3DS cartridge, decrypted; no DLC owned): `scripts/fe15_extract.py` into `data-raw/fe15/romfs`
  (git-ignored), `fe15_bin.py` for its self-describing tables (each file's `MOD_` block names its fields), `fe15_data.py`, and
  `fe15_code.py` (Awakening's helpers on Echoes' program). What the ROM
  doesn't give us yet (holy weapon bonuses, staff effects) is Serenes', each row checked against the ROM's own numbers so it can't
  land on the wrong item, and the README says which.
- **Everything generated comes from a re-runnable script**; fix the generator, never the output. Formats go
  in `data-raw/<game>/README.md`.
- **The game wins.** When the data contradicts a wiki or memory, say so plainly and point to the file. Bugs
  are kept as the game has them (Florete is physical; Conquest 11's "forts" are gates).
- **Check mechanics in the program code for each game; never assume they match another game.** Effective Mt is
  ×2 in PoR and ×3 in RD. Brave strikes twice on both phases in Tellius. Beast and horseback targets are
  separate in Tellius. Healing jars reach only the 4 orthogonal tiles. Height gives +2 Mt and +50 Hit. The GBA games share an engine
  lineage but not every rule: effective Mt is ×3 in FE6, ×2 in FE7 (with the triangle's Mt), ×3 in FE8 but ×2 for its legendary
  weapons; FE6's reaver only reverses the triangle, FE7's and FE8's reverse and double it. Thracia 776 triples Mt like FE6, but its
  triangle gives only the winner +5 hit and avoid (as FE4's does), and hit is one roll held between 1 and 99. Mystery of the Emblem has
  no triangle at all, triples Mt (held at 33), and rolls hit with a random byte scaled to 0-99, a hit at or below the displayed hit
  (so a displayed 0 still lands 1.17% of the time). Awakening is 2RN like the Tellius games, triples Mt (the triangle's attack isn't),
  gives fliers no terrain bonus, and only swords, lances and axes are in its triangle, worth more with the advantaged side's rank.
  Echoes rolls hit as Fates does (one 0-9999 number, curved from 50 up), has no weapon triangle, triples an effective weapon's Mt (an
  effective art triples only its own Mt bonus), and its terrain heals and hurts by HP, not a percentage.
- **Anything not confirmed goes under `unconfirmed`, not stated as fact.**

## Weapons & forging

- **List only what the player can get:** sold, forged, given, in a chest, village or hidden spot, dropped,
  carried by a recruit, or stealable.
- **Your units' gear in Path of Radiance and Radiant Dawn** is what the 'mikata' (your side) groups of each chapter's placement file
  carry (`kitAt` on a weapon, from `build-fe9-items.py` / `build-fe10-items.py`): a recruit's own weapon or a starting kit, listed
  from that chapter and kept. The same goes for Fates' `kit`: the weapon page says nothing about it, the weapon simply turns up in
  the list at the right chapter.
- **A foe's gear is on the map:** tapping a foe's tile says what it carries (Fates, from the placement files).
- **Foe-only weapons are listed, marked as not available to the player** (the red X icon, a note on the page and a
  "Hide foe-only" switch), with the foes who carry them: Ashnard's Gurgurant, Rewarp, Alondite, Fates' Kukris, Bölverk, Skadi,
  rocks and saws. A boss's weapon only counts where the boss is a unit you can see on the map. In Fates they come from the
  game's item table (`src/data/weapons/foeOnly.ts`) and each map unit's `carries` (the placement files' non-drop item slots).
  Lilith's Astral weapons and Draconic Rage (Corrin's own dragon-form attack) aren't a foe's, so they're in no list.
- **Leave out:**
  - weapons fixed to the map (ballistae, onager, fire orb, Ashera's siege forms of Judge);
  - codes-only items.
- **Steal rules are per game:**
  - PoR: unequipped weapons whose weight is at least 1 under the thief's Str. A foe's second weapon counts.
    A silenced foe's lone tome counts once they use an item (Rexaura).
  - RD: everything can be disarmed except `/L` slots, `sealsteal` items and Ashera's.
  - Thracia 776: any item lighter than the thief's Con, and any foe can be captured and its items taken, so what foes carry is a
    source ("capture to take it") and no weapon is foe-only.
  - Mystery of the Emblem: no stealing; a foe drops what's in its item slots (and its gold), never its weapon slots.
  - Awakening: the Steal skill takes items, not weapons (Serenes Forest); a foe drops what its placement record marks to drop.
  - Echoes: no stealing; a foe drops its one item when its placement record marks it, and its person record can drop another at random
    (with its rate). The monsters' claws, fangs and breath are their classes' own weapons: listed foe-only.
- **Awakening's random items are listed as such:** event tiles (a random item from the game's event-tile pool, from the first chapter
  that has event tiles), travelling merchants (a location's extras and the rare items, "sometimes sold"), and the DLC maps whose foes the
  game picks at random ("Random foe" on the map, as The Sacred Stones' random monsters). Renown rewards and DLC sources sit behind
  their own switches on the weapon page, like Fates' visit and battle rewards.
- **Echoes' items come from exploring, not shops** (the game has no gold): dungeon chests and glinting finds, the random pools of
  barrels, pots and boxes ("sometimes", with the chance), villagers' and the story's gifts, recruits' items, drops, and evolving at a
  blacksmith (a weapon, or a Rusted item: each copy becomes its own weapon), counted from when both the weapon and a blacksmith are
  reached. A place counts from the next chapter after the battle beside it on the world map. A game with no shops has no stock filter.
  The amiibo dungeons' sources sit behind "Show amiibo items".
- **A shop that stays open once reached** (The Sacred Stones' world map towns, Awakening's shops at each location) counts from the
  chapter after its town's, for the rest of the route; a shop on a tile no unit can enter isn't one.
- **Each copy of a weapon is counted once.** A unit's starting items are a source in the chapter it first joins a story or route,
  never again where a script only loads it back onto the map (FE7's openings reload your units every chapter without
  preparations; the loader reuses the unit, so it's no new copy). Alternatives count once each (10A or 10B; either version of a
  split chapter). What a foe holds is only said for a weapon nothing else gives (the GBA games' thieves can't steal weapons).
  Tested per game (`fe7.test.ts`: no one joins a story twice). Every game with routes (FE8, Three Houses) does the same.
- **"Where it turns up" is one row per way of getting it, per story or route, with the chapters in a row:** "Sold at the armory
  (Eliwood's story): Ch.12, Ch.13, Ch.14", never a line per shop (`src/logic/sourceRows.ts`; a game with routes names them in
  its config's `routeName`).
- **Items the game gives one name get their own entries:** Ganglari is Corrin's Chapter 2 sword (7 Mt, E) and, as "Ganglari (reward)",
  the 16 Mt Battle Points reward that costs HP; Fujin Yumi has a "(Bronze form)" in Heirs of Fate. The generators suffix the second
  (`build-fates-items.py`, `build-fates-units.py`, `build-fates-chapters.py`), so a kit or drop can't mix them up.
- **No flavour descriptions.** Only what the weapon does, in its datasheet (the Bamboo Yumi gets none).
- **Effects are pixel icons:**
  - Effectiveness shows its target: helm (armour), dragon head, wing, horse head (horseback), lion head
    (Tellius beast laguz), monster.
  - Brave has its own icon, and might boosts use one up arrow.
  - "No crits" and "no skills" always go together.
- **Effective weapons show their boosted Mt.**
- **Foe-only classes are left out of class lists** (Stoneborn).

## Maps: the chapter lists

- **The main dropdown is the story as everyone plays it**, including chapters that unlock automatically and
  can't be skipped once unlocked (the GBA games' X chapters).
- **The second dropdown holds what's optional:** post-game maps and chapters you can skip once they're
  unlocked: Fates' paralogues (Mozu's, the children's recruitments), DLC, and trial maps.
- **When it's unclear which list a map belongs in, ask.**
- Leftover or test maps on the disc (RD's `lmap`, tutorials, debug maps) aren't listed.

## Maps: terrain

- **Terrain codes are two characters** (`scripts/terrain_codes.py`, which also writes `src/data/maps/terrainCodes.ts`).
  The first is the group: `t` terrain, `b` bonus, `h` healing, `d` damage, `w` wall or blocked, `o` object, `s` changes
  during the chapter; the second numbers it (a-z, 0-9). Each code means one thing in every game; a new kind of tile
  gets a new code in its group, and each game maps its own tiles onto the codes there.
- **Draw terrain as the game treats it, not as it looks.**
  - An icon means a tile you can stand on that has stats (trees, Fates pillars, forts).
  - Anything no unit can enter is a wall, whatever it depicts: Tellius pillars, Fates Ch.5 rubble, PoR
    Ch.17 roofs as rubble.
  - Plain tiles (ground, void, bridge, building) are colour only.
  - Terrain that works the same is merged (all mountains; stone and wood bridges).
- **Stats and movement costs come from the game's own terrain table**, per movement type, fliers
  included. Fliers' access to forest differs by game.
- **Crop each map to its playable grid** (fireemblemwod.com's gridded overviews, then the user's in-game
  check). Units off the grid are spectators and are dropped.
- **Flag uncertain tiles for a manual check; don't discard them** (RD cells under a roof that lifts).
- **Coordinates:** bottom-left is (1, 1), y counts up. Convert each source once, on entry.
- **Fences** run along tile sides (`walls`). Ledges have the chevron icon and say what height gives.

## Maps: units

- **Units come from the game's placement files and the opening scripts.**
  - Units the pre-battle script places are included (PoR Ch.7's boss).
  - Units that leave before the battle are removed (Nasir, Ch.11), and so are units carried for the whole
    map (Leanne).
  - Scripted pre-battle walks are applied.
- **Enemy markers:**
  - a skull for the boss;
  - a red soldier for named foes;
  - a plain red dot for common ones;
  - a badge for item droppers.
  - Fates capture badge: capturable bosses and named foes only. Never anyone playable on any route, and
    generics aren't marked.
- **Green units:** the person icon is only for named ones, to draw the eye to them. Generic green units
  (another army's soldiers, villagers, RD 3-3's horses) are a plain green dot, like common foes in red.
- **Green units say what they do:** talk to recruit (with whom), where they leave the map, and their own
  destination when the AI fixes one (RD 3-3's horses).
- **Stand-ins:** a unit the game places only when a character is gone (died, or left that army) is that character's
  stand-in, never a second unit on the same tile. One toggle per map swaps every stand-in in at once.
- **Shown on the map:** the lord's start ("Lord's start", with the lord named in the text), forced
  deployments (fixed tile or not), and joiners.
- **Difficulties:** one entry where they're the same. Never repeat identical text per difficulty. Where only a level changes (The
  Sacred Stones' generic foes gain or lose the chapter's levels per difficulty), the unit says its Normal level with the others beside
  it ("Lv 3 (Easy 1, Hard 6)").
- **Echoes' dungeons**: each battle field a dungeon's wandering foes use is one map. Its groups are the five formations an encounter's
  foes can take (plain "Encounter foe" markers) and the fixed encounters on their own tiles (gatekeepers); each other encounter's line-up
  is a note, with its chance and the act it appears from. The dungeon's boss battles are maps of their own. A cemetery's layouts are its
  groups (one fills it each time). A Reinforce group the placement file gives no tile (Zofia Castle's Slayde) is named in the notes.
- **Random monsters** (The Sacred Stones' Tower of Valni and Lagdou Ruins: the game picks their class, level and items as the floor
  loads) are shown where they stand as "Random monster", with nothing about what they are or carry.
- **A reward an end scene gives only on a condition** says the condition, read from the script's own checks (FE8: "if all three
  'Renais Cit.' units survive").

## Maps: events and objectives

- **Reinforcements are fixed by each chapter's script:** say when they come.
  - Only the Fates grinding maps (Boo Camp, Ghostly Gold, Museum Melee, Beach Brawl, Royal Royale) are
    random. There, show only the spawn points and where those enemies head.
- **Anything that reshapes the map previews before and after**, one at a time:
  - Dragon Veins;
  - breakables (they become what the game has under them; RD 2-E's becomes a ledge);
  - boulder paths, traced off the map unless the rock breaks first;
  - torches, including ones lit from the start;
  - RD clouds, by turn and phase.
- **Objectives:**
  - Seize, escape, arrive and defend are the blue outline.
  - Any other kind gets its own look (RD 3-3's supplies to burn: a sacks icon with an orange outline).
  - Exit tiles say who leaves by them; drop the exit if nobody uses it.
- **Chest, village and hidden contents come from the scripts**; hidden areas show their dig zone.
- **Fog of war** shades what's unseen; torches show what they light.
- **The map's info panels can sit beside the map or below it** (a switch, remembered on the device), so wide maps (RD's
  bridges, every FE4 map) get the full width.

## True hit, the weapon triangle and supports

- **True hit:** the hit system is checked in the game's code (Fates' own hybrid formula, Tellius 2RN).
- **A game with no weapon triangle (Mystery of the Emblem) has no Weapon triangle tab** (`triangle: null`).
- **Weapon triangle tab:** who beats whom, what the advantage is worth and what the other side loses, whether weapon rank
  scales it (Fates), its special effects (RD turns it off on Hard; Fates' reavers flip and double it; a disadvantaged Fates
  unit loses its rank bonus), the game's weapon rank bonuses, and leadership stars where the game has them (FE4, RD), with
  a calculator. Every number from the game's own files or code (`scripts/build-triangles.py`, FE4's
  `build-fe4-bonuses.py`); who has how many stars is unit data and isn't shown.
- **Supports:** only what a support gives per level, and how it rounds and stacks. No pairings.

## Spoiler block

A global switch (header, any game) that lets someone play along without being told what's ahead.

- **On: the app opens on a blank field** ("Choose a game…"), not on a game. Each game starts at its first chapter;
  **Proceed** opens the next one, **Back** undoes it, and **Jump to** names chapters without their titles.
  Progress is kept per game on the device.
- **A weapon is listed from the first chapter it turns up in, and stays listed after.** It turns up when a base sells,
  bargains or forges it, a base conversation gives it (Jill's Brave Axe, Tarvos: weapons you can get that no shop
  sells), the story hands it over (Ragnell), or the map holds it: chests, villages, buried items and the drops of foes
  standing on the map at the start. Ragnell is absent before the chapter that gives it and listed from then on.
  Weapons turning up for the first time get a "new" mark; categories with nothing yet are hidden.
- **Each chapter says what its own base does with each weapon:** "shop" (the base's stock), "limited" (Radiant Dawn's
  bargains: one to buy), or neither, and a stock filter (any / shop here / limited here / not in the shop here). Stock is
  the chapter's own, since it changes from base to base; gifts and map sources are kept once reached.
- **Only what you can actually see in the chapter:** a boss's weapon counts only where the boss is a unit on the map
  (Petrine's Flame Lance is on the Great Bridge, not in Ch.7 where she is a cutscene), never from a placement file. What a
  foe who arrives mid-chapter (a reinforcement) carries or drops is listed from the chapter after the one it arrives in, when
  it's been seen. Not listed under the block: a recruit's own weapon and a foe's spare weapon.
- **A buying price is only said while a shop of yours stocks the weapon** (before that, just what it sells for).
- **Descriptions say only what applies by this chapter:** "Bought at the base's armory: Chapter 9", "Given in a base
  conversation before Part 3, Chapter 6". Nothing is said where a base doesn't sell it.
- **A map shows only how it starts:** no reinforcement groups and no joiners, friend or foe, and none of the notes or
  weapon sources that give them away (a foe that arrives later, "arrives with Group 3"). Units placed on the map,
  forced deployments and objects stay.
- **Side maps** (trial maps and the like) open once the story is cleared. Echoes' Act 6 opens after the Final Battle, the amiibo
  dungeons with Act 3. Its Acts 3 and 4 run both armies at once; the list puts Alm's battles before Celica's (`data-raw/fe15/README.md`'s
  "Not confirmed" says so: you may play them in any order).
- **A game with no chapter order yet** is held back under the block, not shown in full. Turn the block off to see it.
- **A game whose story splits (Fates) asks which route you're on** when the shared chapters run out (Proceed as
  Birthright / Conquest / Revelation); the route can be changed in the bar. Only that route's chapters, paralogues and
  weapons are ever shown, and the route select on the weapon page goes away.
- **A story can split more than once** (The Binding Blade: 10A or 10B after Chapter 9, Ilia or Sacae after 16x; The Blazing Blade:
  Lyn's story, then Eliwood's or Hector's, each split at Lloyd or Linus and at Kenneth or Jerme). Each split is
  asked when it's reached ("Proceed to Chapter 10A"), the bar keeps one route select per split passed, and changing an earlier
  choice drops the later ones. Without the block, the map page lists every route's chapters in turn.
- **Chapters the game opens only on conditions** (the gaiden chapters, a route's chapters) say when in the map's notes, read
  from the end scripts' checks ("Opens if Chapter 12 is cleared within 20 turns with Elffin alive").
- **Fates' buildings open by chapter, not by one flat list.** A level opens once its chapter is *completed*, so on the next
  chapter: the Armouries and the Rod / Staff Stores at Chapters 6, 13 and 20; the Smithy at 8, 14 and 20 (the game's own
  `castle_building.bin`). Until the Smithy is up the weapon page says nothing about forging; level 1 forges to +2, level 2 to
  +4, level 3 to +7, and the forge table and level picker stop there. Shops stock what Serenes' tables give for the
  level they're on (unlimited, or a quantity: "limited" tag), and a weapon is listed from the first level that stocks it.
- **My Castle's ally items, rank rewards and amiibo items are static collectibles**, like Tarvos: listed from the chapter
  after Chapter 6 (the castle opens), any number of times. The story's gifts come with a chapter (Yato's forms: Fire
  Emblem Wiki). DLC maps and their rewards open after Chapter 6 (the Dragon's Gate), paralogues by chapter.
- **A child's paralogue opens the chapter after their fixed parent joins your army for good** (the other parent is whoever you
  marry): Soleil follows her father Laslow (joins in Conquest 12, so Chapter 13), Shigure his mother Azura (Conquest 9, so 10).
  Joins are read from the game's chapter files (`scripts/build-fates-joins.py`: scripts that hand a unit over, Support groups,
  the Player groups) and checked against Serenes Forest's recruitment pages in a test; nothing opens before Chapter 7 (the
  castle). Jakob joins in 6 or only after 15 depending on Corrin's gender, so his son Dwyer's waits for the later date.
  Mozu's (Paralogue 1) opens after Chapter 8 (Gamer Guides), not confirmed in-game.
- **Fates' weapon page leaves three things off until a switch is ticked:** "Show visit & battle rewards" (a weapon whose only
  source is a My Castle Battle Points or Visit Points reward; one with any other way to get it, the Treasure pool included, is
  listed normally, and its reward lines only appear once the switch is ticked),
  "Show DLC items" (DLC weapons and what only the DLC maps carry), and, as ever, foe-only ones ("Hide foe-only" is a hide
  switch). The new-weapon count in the bar counts only what the list shows by default.
- **Your own units' starting gear is yours from the chapter they appear in** (Fates): Chapter 1's Bronze Sword, Gunter's lance and
  Felicia's / Jakob's dagger and Heal from Chapter 2, Corrin's Yato from the chapter the placement files give it (6 on
  Birthright and Conquest, 13 on Revelation). It comes from each chapter's Player groups (`kit` on the map).
- **No filler lines for "not available":** where a shop doesn't stock something, the page says nothing at all, so a blank can't
  hint at what comes later.
- **Allies' gifts are said:** the weapons the allies in My Castle hand out (a "!" over their head, once enough time has passed:
  the joke weapons, the Raider and named weapons, the Harp Yumi; the game's `isMyCastle` set, 86 of them) say "Given by an ally in
  My Castle." Under `unconfirmed`: which chapter unlocks each one. No file or source we have says (the wiki says only "obtained at
  random from a pool"), so they're all listed from Chapter 7, when the castle opens. The user's Birthright game had an ally give
  Setsuna's Yumi by Chapter 10 and suspects some are locked until later chapters (their Camilla's Axe never came). A claimed
  "Camilla's Axe after Chapter 22" from a web search summary could not be traced to a page, so it's not used.
- **Generated data carries the chapters:** `shopAt` / `bargainAt` / `forgeAt` (map ids behind the shop text), `baseAt`
  (base conversations: script handler kind 14) and `giftAt` (a script's gift outside chests and villages, or a quiet
  handover in a chapter's `Opening`). Every id must be a chapter of the story (tested in
  `src/logic/__tests__/spoiler.test.ts`).

## Build and offline

- **Each game is its own file** (`src/games/<id>.ts`, loaded by `load()` in `src/games/index.ts` when the game is first
  picked), so the app's main file stays small and a change to one game doesn't re-download the others. Shared screens must
  not import a game's data directly; pass it in.
- **Every file is precached** so each game works offline without being opened first. The PWA plugin's per-file limit is
  4 MiB (`vite.config.ts`); a game's file passing it means splitting that game further. `scripts/check-precache.mjs` runs
  after the build and fails if a script or stylesheet is missing from the offline list.
- **A deploy that fails is urgent:** GitHub Pages stays on the last good build (the Tower maps were missing for days).

## Look and layout

- **Icons are the app's own 10×10 pixel sprites** (NES Zelda look) in `src/icons/sprites.ts`, never emoji.
  Each should look like the thing, be distinct from the others, and not be overdone. The legend uses the
  same icons as the map.
- **Everything fits a phone screen.** Tapping a weapon scrolls to its datasheet.
- **Wording works for every game** ("Lord's start", not "Corrin's start").

## Process

- **Build the base from the data first; the user then checks in-game.** Their corrections become rules here.
- **Check counts against outside sources in the tests** (enemy totals per map, wiki or fireemblemwod.com),
  with every exception explained.
- **Back each rule with a test where it can be checked** (e.g. no pillar icon on a tile no one can enter;
  only grinding maps spawn at random).
- **Before calling a map done, look at it in the browser.**
- **Commit and push each finished step.** End commit messages with the co-author line.
