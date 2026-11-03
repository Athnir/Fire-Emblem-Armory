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
- **One difficulty per game, picked in the bar beside the game** (remembered per game on the device; a game with one has no
  choice). Every page shows only that difficulty's data: its maps' units, arrivals and layout, its bases' stock and forge, and the
  maps' lines for drops and gear, which carry their difficulties (`difficulties` on a source) rather than naming them in their
  words. A weapon none of whose sources hold on it isn't listed. Changing it keeps the page and map you're on; a map played on
  fewer difficulties than the game has (The Blazing Blade's Lyn's story) shows its own and says so ("Normal only").
- **Finish one game across every tab before starting the next.** Fortune's Weave is skipped (too new for
  solid data).
- **Notes state data, not observations or strategy.** "Elise is ill" and how reinforcements arrive are data;
  "watch out for the archers" is not.
- **No per-map source notes.** Sources are listed once, in the README.
- **The armory is a datasheet: everything the game has goes in,** even content behind something the user may lack (Echoes' amiibo
  dungeons, Fates' amiibo items) and DLC they don't own. DLC missing from the user's files is never obtained: it's taken from the wikis
  (Fire Emblem Wiki first) and replaced by the files' own data once they can be read. The app never says which data is read from the
  game's files and which isn't (a map drawn less fully speaks for itself); the READMEs keep the sources. A DLC map the
  wikis give no tiles for (Echoes' DLC: no gridded maps found) waits for the files.
- **SpotPass teams stay out:** only the units, and what they carry, that the game gives in play or through its DLC go in (the user's
  call for Awakening's bonus teams).

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
  `fe15_code.py` (Awakening's helpers on Echoes' program). Shadow Dragon (FE11, the DS cartridge): `scripts/nds_rom.py` reads the cartridge
  (NitroFS, LZ10/LZ11, the BLZ program), `fe11_extract.py` copies what's read into `data-raw/fe11/rom` (git-ignored), `fe11_data.py` reads
  its database and text (Awakening's container), `fe11_cmb.py` its scripts (an older version of Fates' bytecode, its own opcodes). Shadow
  Dragon and the Blade of Light (FE1, the Switch release, digital: the user's NSP from nxdumptool in `Documents\FE Games\Switch dumps`,
  decrypted with their own console's keys in `~/.switch`, never in the repo): `scripts/switch_nsp.py` reads the package (NCA, PFS0, RomFS,
  NSO), `fe1_extract.py` writes its program and the Famicom cartridge inside it into `data-raw/fe1/rom` (git-ignored), `fe1_rom.py` reads
  the cartridge (MMC4) and `fe1_names.py` names everything from the Switch program's own English (its dictionary of the cartridge's
  Japanese strings). Three Houses (FE16, the user's cartridge base, the 1.2.0 update and six DLC packages as NSPs, read
  together: the update's RomFS is a BKTR patch over the base's): `scripts/fe16_extract.py` copies the archive's files (DATA0/DATA1, the
  update's INFO0 replacing some), the program and the DLC's small files into `data-raw/fe16` (git-ignored); `fe16_data.py` reads the
  tables (field names from the Three Houses Research Team's templates, each checked against the files), the text, the grids, the unit
  tables and the battle scripts (`bsic`'s command list, every script parsing to its own counts). What the ROM
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
  weapons; FE6's reaver only reverses the triangle, FE7's and FE8's reverse and double it. FE6's Light Brand deals a flat 10 damage
  from 2 tiles away (no crits); FE7's and FE8's magic swords are always fought against Res, and are magic (half Str, no crits, in the
  magic triangle) only from 2 tiles away, the Runesword at any range. Thracia 776 triples Mt like FE6, but its
  triangle gives only the winner +5 hit and avoid (as FE4's does), and hit is one roll held between 1 and 99. Mystery of the Emblem has
  no triangle at all, triples Mt (held at 33), and rolls hit with a random byte scaled to 0-99, a hit at or below the displayed hit
  (so a displayed 0 still lands 1.17% of the time). Awakening is 2RN like the Tellius games, triples Mt (the triangle's attack isn't),
  gives fliers no terrain bonus, and only swords, lances and axes are in its triangle, worth more with the advantaged side's rank.
  Echoes rolls hit as Fates does (one 0-9999 number, curved from 50 up), has no weapon triangle, triples an effective weapon's Mt (an
  effective art triples only its own Mt bonus), and its terrain heals and hurts by HP, not a percentage. Shadow Dragon and the Blade of
  Light rolls hit with a random byte × 2 / 5 held at 100 (a hit at or below the displayed hit, never at 0), triples an effective
  weapon's Mt, has no weapon triangle and no supports, and its fliers always fight as if in the sky (no Avoid from terrain).
  Three Houses rolls hit with two numbers averaged (rounded down), each a 16-bit random value mod 100 (so 0-35 come up slightly more:
  its own true hit table, counted over the generator's whole period), crit with one, and a crit triples damage; an effective weapon's
  Mt is tripled (`0xd99a0`); it has no weapon triangle; a foe with empty item slots is given its class's Iron, Steel or Silver weapon by
  level (`0x19e41c`).
  Shadow Dragon triples an effective weapon's Mt (an Iote's Shield the defender holds cancels what it covers), has a weapon triangle
  (sword, lance and axe; Hit 5 to 10 and Atk 1 at A by the advantaged side's rank, the loser losing as much and its own rank bonus) and
  weapon rank bonuses, all read in the battle overlay's code; it rolls hit with two numbers averaged (2RN), and its forge (each stat
  either way: Mt, Hit, Crit and Wt) prices each stat by triangular steps of the weapon's price (`src/logic/fe11Forge.ts`). Who may use
  an item is its equip check's (lock bits against the person's, class's and placement's attributes), never the help text.
- **Anything not confirmed goes under `unconfirmed`, not stated as fact.**

## Weapons & forging

- **List only what the player can get:** sold, forged, given, in a chest, village or hidden spot, dropped,
  carried by a recruit, or stealable.
- **Your units' gear counts once, from the chapter each unit first joins** (`kitAt` on a weapon in Path of Radiance and Radiant
  Dawn, `kit` in Fates): the weapon page says nothing about it, the weapon simply turns up in the list at the right chapter. In Path
  of Radiance (`build-fe9-items.py`'s `kit()`) the deployment roster a unit first appears in (`bmapNN_mikata_c`), a group placed on
  your side, a `Join()` from the shared roster (Calill, in a base conversation) or a unit an opening hands over is yours from that
  chapter; a recruit who joins during the battle (a talk, or the chapter's end: Haar by Jill's talk in Ch.23, Geoffrey after Ch.24)
  is yours from the next. A laguz brings its class's strike. The rosters an opening places only when a chapter is started from the
  debug menu with no army (`_mikata_n`/`_h`/`_m`, `always_dbg`) and a cutscene's `_event` groups are no one's. Radiant Dawn's
  chapter rosters (`bmapPPCC_mikata_n`/`_h`) are developer-start templates (`EvDevStart`) with the gear a unit should have by
  then, not what you carry (Micaiah's list a Thani from Part 1 Ch.3; it's a base conversation's gift before Part 1's Endgame):
  a unit's gear counts only at its first roster, join (`JoinRank`, `SallyAddByGroupRank`, a group the battle places on your
  side: Lehran in Endgame (5)) or hand-over (`build-fe10-items.py`'s `kit()`), never from a scene's cast (`_op`, `_ed`).
- **A foe's gear is on the map:** tapping a foe's tile says what it carries on the chosen difficulty (Fates, from the placement
  files: an item slot's flag word leaves it off the difficulties whose byte is 0xFF; Awakening, each slot's level per difficulty,
  which leaves it off, steps a foe's weapon up its series or forges it, as the program's item loader does).
- **Foe-only weapons are listed, marked as not available to the player** (the red X icon, a note on the page and a
  "Hide foe-only" switch), with the foes who carry them: Ashnard's Gurgurant, Rewarp, Alondite, Radiant Dawn's Judge (Ashera's own),
  Fates' Kukris, Bölverk, Skadi, rocks and saws. A boss's weapon only counts where the boss is a unit you can see on the map. In Fates they come from the
  game's item table (`src/data/weapons/foeOnly.ts`) and each map unit's `carries` (the placement files' non-drop item slots).
  Lilith's Astral weapons and Draconic Rage (Corrin's own dragon-form attack) aren't a foe's, so they're in no list.
- **Leave out:**
  - weapons fixed to the map (ballistae, onager, fire orb); Shadow Dragon's ballistae are items a Ballistician carries, so they're
    listed (a Ballista category);
  - attacks a boss's AI makes on the spot, never in anyone's slots (Radiant Dawn's other Judges: Ashera's map-wide attacks and
    silence and paralysis waves, Sephiran's and Dheginsea's map-wide attacks, Lekain's silence wave);
  - codes-only items.
- **Steal rules are per game:**
  - PoR: unequipped weapons whose weight is at least 1 under the thief's Str. A foe's second weapon counts.
    A silenced foe's lone tome counts once they use an item (Rexaura). A weapon no base sells or forges says which foes it can
    be stolen from ("Steal from Warrior"); common ones don't, so the list stays short.
  - RD: everything can be disarmed except `/L` slots, `sealsteal` items and Ashera's. A weapon no base sells, bargains or forges
    says which foes it can be taken from ("Steal from Myrmidon": the Venin weapons), never one locked to its unit (each map unit's
    `locked`: the Black Knight's Alondite; Ike's Ragnell in Part 3 Ch.13 on Easy, the files leaving it unlocked on Normal/Hard).
  - A weapon only a cutscene's cast or a roster's template carries (Radiant Dawn's Slim Lance) is codes-only: left out.
  - Thracia 776: capturing a foe takes everything it holds, so what a foe one of your units can capture carries is a source
    ("capture to take it"). Not every foe can be captured (traced in the code: `data-raw/fe5/README.md`): its Con, its own plus its
    class's base held at 20, must be below the captor's (a mounted foe's counts as 20 until Sleep or a script's Dismount knocks it
    off), so a foe at 20 never can be, nor one whose skills bar it (Fred, Olwen, Kempf, Saias, Ishtar, Altena, Bharat). A thief's
    Steal takes any item, weapons included, from a foe slower than the thief, when it weighs less than the thief's Con (both held
    at 20), so a foe capture can't take is robbed instead where a thief could be ("a thief with more than 12 Spd can steal it":
    Gustav's Adept Manual, Bharat's Thrud's Scroll). What neither can take is foe-only (the Loptrian Fang, at Con 20 and Wt 20;
    Chapter 5's Shadow Sword, whose arena door takes Mareeta away when it opens).
  - Mystery of the Emblem: no stealing; a foe drops what's in its item slots (and its gold), never its weapon slots.
  - Awakening: no stealing (its skill list, SkillData's RSID_ names, has no steal skill); a foe drops what its placement record marks
    to drop.
  - Echoes: no stealing; a foe drops its one item when its placement record marks it, and its person record can drop another at random
    (with its rate), said in the foe's note without the drop badge (the user's call). The monsters' claws, fangs and breath are their
    classes' own weapons: listed foe-only.
  - Shadow Dragon: no stealing (its text has no Steal command); a foe drops what its placement record marks to drop.
  - Shadow Dragon and the Blade of Light: no stealing; a defeated foe drops its second item to the unit that beats it, never the one it
    fights with (Gradivus and the Falchion are Camus's and Gharnef's second items).
- **Awakening's random items are listed as such:** event tiles (a random item from the game's event-tile pool, from the first chapter
  that has event tiles), travelling merchants (a location's extras and the rare items, "sometimes sold"), and the DLC maps whose foes the
  game picks at random ("Random foe" on the map, as The Sacred Stones' random monsters). What the world map's skirmish foes can drop
  is left out for now (the user's call: no file read so far gives it, `data-raw/fe13/README.md`); once it's found, it counts as one
  general line ("Dropped by skirmish foes"), never each drop table's or foe's own. Renown
  rewards and DLC sources sit behind their own switches on the weapon page, like Fates' visit and battle rewards.
- **Echoes' items come from exploring, not shops** (the game has no gold): dungeon chests and glinting finds, the random pools of
  barrels, pots and boxes ("sometimes", with the chance), villagers' and the story's gifts, recruits' items, drops, and evolving at a
  blacksmith (a weapon, or a Rusted item: each copy becomes its own weapon), counted from when both the weapon and a blacksmith are
  reached. A place counts from the next chapter after the battle beside it on the world map. A game with no shops has no stock filter.
  The amiibo dungeons' sources sit behind "Show amiibo items", the DLC's (Fire Emblem Wiki's: `scripts/fe15_dlc.py`, from Act 1,
  when the world map's Connect menu opens) behind "Show DLC items".
- **A shop that stays open once reached** (The Sacred Stones' world map towns, Awakening's shops at each location) counts from the
  chapter after its town's, for the rest of the route; a shop on a tile no unit can enter isn't one.
- **Each copy of a weapon is counted once.** A unit's starting items are a source in the chapter it first joins a story or route,
  never again where a script only loads it back onto the map (FE7's openings reload your units every chapter without
  preparations; the loader reuses the unit, so it's no new copy). Alternatives count once each (10A or 10B; either version of a
  split chapter). What a foe holds is only said for a weapon nothing else gives (the GBA games' thieves can't steal weapons).
  Tested per game (`fe7.test.ts`: no one joins a story twice). Every game with routes (FE8, Three Houses) does the same.
- **"Where it turns up" is one row per way of getting it, per story or route, with the chapters in a row:** "Sold at the armory
  (Eliwood's story): Ch.12, Ch.13, Ch.14", never a line per shop (`src/logic/sourceRows.ts`; a game with routes names them in
  its config's `routeName`). Where a game's maps are places you can go back to (The Sacred Stones' and Awakening's world maps), a
  shop or merchant goes by its town instead: a fixed place, not a step in the story (the user's call).
- **Fates' weapon page lists the maps that give a weapon under "On the maps"**, one line per chest, village or foe ("Birthright 26:
  Xander · Dropped by Maid"), a foe placed on every difficulty once, and the list folds away behind its heading past five lines.
- **Items the game gives one name get their own entries:** Ganglari is Corrin's Chapter 2 sword (7 Mt, E) and, as "Ganglari (reward)",
  the 16 Mt Battle Points reward that costs HP; Fujin Yumi has a "(Bronze form)" in Heirs of Fate; Shadow Dragon's weaker Falchion,
  Chapter 24x's gift, is "Falchion (24x)". The generators suffix the second
  (`build-fates-items.py`, `build-fates-units.py`, `build-fates-chapters.py`), so a kit or drop can't mix them up.
- **No flavour descriptions.** Only what the weapon does, in its datasheet (the Bamboo Yumi gets none).
- **What a weapon does is read from the game's code, not its description or a wiki:** Path of Radiance's Flame Lance and Bolt
  Axe deal magic damage because of their second type, which also puts them in the magic triangle; Radiant Dawn's white dragons'
  Breath is magic the same way (second type `neutral`, outside the triangle; its magic swords' second types are physical); a
  description that disagrees with the code loses (the Runesword heals the full damage).
- **Hidden growth changes go on the datasheet** (Path of Radiance's weapons change a Fixed-mode level-up's growths): shown here,
  and in the Unit Planner later.
- **A laguz's own attacks are listed like weapons** (Path of Radiance: claws, breath and beaks, in a "Strike" category, named by
  their class where the game gives several one name: "Claw (Lion)", "Beak (Tibarn)"), with no price and no forge. Radiant Dawn's
  come from each class (JobData +0x1c), one entry per family, named by race and whether it's the royals' Great form even when
  one unit has it, for consistency (the user's call): "Fang (Lion)", "Great Fang (Lion)", "Great Talon (Hawk)"; the black
  dragons' two plain Breaths go by class ("Breath (Dragon King)"). Their higher forms (rank S and SS) are in their rules, and the
  map's gear lists them (a laguz moves up a form as its Strike rank rises from attacking, the slowest rank to raise, and a regular
  family never becomes the Great one: the user, in the game). Ashera's Judge is a strike by its game type, so it's under Strike
  too, but it's in her slots, not her class's: its page names who carries it.
- **Radiant Dawn's cards (Spectre, Reaper, Daemon) are listed in a Card category of their own:** items that attack, never
  equipped, with Mag plus their Mt against Res; what the code does with them (no counter, no triangle, not for magic users) is in
  their rules.
- **Effectiveness says when it applies:** Path of Radiance's beast, dragon and bird targets are transformed laguz only.
- **Effects are pixel icons:**
  - Effectiveness shows its target: helm (armour), dragon head, wing, horse head (horseback), lion head
    (Tellius beast laguz), monster, a cracked wall (breakable doors and walls: Path of Radiance's axes), a ballista (Shadow Dragon's
    Ballisticians).
  - Brave has its own icon, and might boosts use one up arrow.
  - "No crits" and "no skills" always go together.
- **Effective weapons show their boosted Mt.**
- **Foe-only classes are left out of class lists** (Stoneborn).

## Maps: the chapter lists

- **The main dropdown is the story as everyone plays it**, including chapters that unlock automatically and
  can't be skipped once unlocked (the GBA games' X chapters).
- **The second dropdown holds what's optional:** post-game maps and chapters you can skip once they're
  unlocked: Fates' paralogues (Mozu's, the children's recruitments), DLC, and trial maps; Echoes' battles the world map lets you
  leave unfought (another way on, no move check needing them), Act 6 and the amiibo ordeals (the user's call). Of two alternatives
  where only one is fought (Echoes' two deserts before Grieth's Citadel), one stays in the story and the other is listed here, both
  saying so.
- **Fates' challenge battles are a third dropdown ("Challenges"), a list of their own:** a rerun of every chapter's or
  paralogue's map the game lets you scout (its chapter record's flag and route mask, not just an encounter file: Chapter 2
  has one but can't be scouted), on Birthright and Revelation (Conquest has none). A chapter's
  challenge opens once that chapter is cleared; a paralogue's opens with the paralogue (the app can't know it was cleared).
  Each goes by its scout name, the chapter's location ("Cemetery in a Deeprealm" for Rhajat's), never the chapter's title.
  It isn't a rerun but a map of its own on the chapter's, with everything spent: every tile in its second state at once (every
  bridge down, every vein's and the chapter's changes made, every breakable broken, every door, chest and village used up,
  Revelation 10's snow cleared), nothing left to trigger. It shows its start tiles, both foe groups at once (each
  outlined in its own colour and numbered, "Group 1" and "Group 2": a battle has one group, either one, or both in a
  dual-boss battle), each group's boss tile (paired half the time) and how many foes it fields per difficulty, and the two
  shiny spots (fixed tiles, with what they can give). A group's foes fill its tiles in a random order: no sections within it.
- **A world map's skirmishes are never in the story's list** (the user's call). Each goes by its location and opens with it (a
  chapter's once the chapter is cleared, a paralogue's with the paralogue; at the route's end where the route plays no chapter
  there). Awakening's Risen skirmishes are a list of their own, in a dropdown of their own like Fates' challenges: the chapter's own
  grid (scripts/Encount.cmb) with its <key>E file's start tiles and two groups of Risen the game fills (outlined), and the travelling
  merchant's tiles, used in place of a group. The Sacred Stones' are optional grind maps, so side maps, listed with the Tower of
  Valni and the Lagdou Ruins ("Skirmish: Za'ha Woods, line-up 1"), and the story chapter whose map they're fought on says so. Each is
  one of a location's three line-ups (its deploy tiles go with each) on the chapter's map destroyed, like Fates' scout maps (the
  user, in the game): the changes the game's skirmish opening makes (villages, houses and shops in ruins, snags cleared, doors
  open), nothing on it doing anything, fog half the time unless that opening turns it off, and the monsters a line-up may leave
  out saying so, with the share of them the opening places. Echoes' dungeons' skirmishes (the battles their wandering foes start)
  are a list of their own too (the user's call), each opening with the first story battle after its dungeon.
- **Three Houses' routes are the route select** (Crimson Flower, Silver Snow, Azure Moon, Verdant Wind), each listing its house's
  White Clouds chapters first; its auxiliary battles (the repeatable side battles of free days) are a third dropdown of their own,
  'Auxiliary battles', like Awakening's skirmishes, and Cindered Shadows (the DLC's side story) is a route of its own, its battles as
  its chapters (both the user's calls).
- **Engage's lists** (the user's calls): Fell Xenologue (the DLC's side story, its own cast) is a story of its own, its battles as
  its chapters (a story select, like Cindered Shadows' route); the Tempest Trials are a dropdown of their own (the Relay Trials, online
  co-op maps, are left out); its skirmishes are a dropdown of their own, as Awakening's.
- **When it's unclear which list a map belongs in, ask.**
- Leftover or test maps on the disc (RD's `lmap`, tutorials, debug maps) aren't listed.

## Maps: terrain

- **Terrain codes are two characters** (`scripts/terrain_codes.py`, which also writes `src/data/maps/terrainCodes.ts`).
  The first is the group: `t` terrain, `b` bonus, `h` healing, `d` damage, `w` wall or blocked, `o` object, `s` changes
  during the chapter, `e` an effect laid over a tile whose own numbers still count under it (Engage's Dragon Vein terrain and
  miasma); the second numbers it (a-z, 0-9). Each code means one thing in every game; a new kind of tile
  gets a new code in its group, and each game maps its own tiles onto the codes there.
- **Draw terrain as the game treats it, not as it looks.**
  - An icon means a tile you can stand on that has stats (trees, Fates pillars, forts).
  - Anything no unit can enter is a wall, whatever it depicts: Tellius pillars, Fates Ch.5 rubble, PoR
    Ch.17 roofs as rubble. Where a wall looks like something others cross, it gets an icon of its own so the two can't be
    mixed up: Fates' indoor rubble that stops fliers too (Birthright's Endgame), Revelation 10's ice to dig through.
    A tile no unit can move onto that the game still places units on keeps its stats, since they count for the unit placed
    there (Awakening's sigils, where foes appear, under the summoning sigil's code; Grima's Ire, colour only like a throne).
  - Each kind of tile that works differently gets its own icon, even under one name: Fates' castle gate, old gate and the
    Rainbow Sage's gateway (Avo +10 only); thick wood (fliers only) apart from woods; the GBA games' houses and inns (`ot`: Avo 10
    like a village, but no looter goes for them) apart from villages, which include the tiles the game calls Ruins that village
    events stand on and looters raid (terrain 55, not the rough ground of 37).
  - Plain tiles (ground, void, bridge, building) are colour only.
  - A throne has no icon: a boss nearly always sits on it, and the two would clash. A tile that works exactly like another uses
    its icon (Fates' Cushion is a fort in all but looks); a floor covering most of a map gets its icon as a small badge (the
    Tower's floors, Ryoma's healing hall).
  - Terrain that works the same is merged (all mountains; stone and wood bridges), unless the map's colours tell the kinds
    apart (Path of Radiance keeps river, sea and pond, and trail and coast, apart: the user's call), and stairs keep their icon
    even where they play as plain.
  - **A map starts as the game lays it out.** Where a map has a layer the game puts over closed rooms, houses, doors, goal tiles,
    rocks and trap lids at the start (Path of Radiance's map.bin `Roof` layer; the GBA games' rooms drawn under a roof that a map
    change lifts: Sue's chapter in The Binding Blade; Shadow Dragon's room grid, Chapters 17x and 19), the map shows it, and whatever opens it (a door, a razed village, a rock
    rolling, a pit sprung, a script on a turn or an area) previews the tiles under it. An opening's map changes are made before
    the battle (The Binding Blade's Chapter 1 starts with its raided village in ruins). A dark room under its roof is closed to everyone, fliers included, until a door into it opens (the user,
    in the game). Fix this wherever it turns up.
  - **Hidden traps** (Path of Radiance Ch.23's pits) show their marker and preview one by one or all at once.
  - **Traps that go off on their own** (the GBA games' fire tiles, gas vents and arrow launchers) are marked on their tiles and say
    when they go off and what they do; what isn't traced goes under the map's unconfirmed notes. The GBA games' ballistae stand on
    ordinary ground, fired by an Archer or Sniper standing on them (class ability 0x80).
  - **A tile a unit can cross but not stop on says so** (Path of Radiance's terrain records, byte 7: fliers fly over buildings,
    roofs, trees, fences and holes but can't land; a village house is Building under its roof, the user confirmed in the game).
    Radiant Dawn's byte 7 is a bit field whose 0x01 is the same rule, but its holes and rocks are landable and its ledges can't
    be stopped on by anyone; tiles one name joins but this rule parts get codes of their own (RD's rock, abyss / waterfall).
  - **The playable grid is the game's own where the map file stores it** (a border width in from every edge: Path of Radiance's
    map.bin `mapextra` byte 5, Radiant Dawn's `mapdata` byte 17), not a fit from screenshots, and it wins over an in-game count
    too (the user's call: Radiant Dawn's Part 3 Ch.4 and Ch.6). Maps that share one file keep each section's own part.
  - **Fences and barricades come from the game's edge table** (Path of Radiance's and Radiant Dawn's `maplink`): a side ground
    units can't cross says so, and that fliers can, unless the table binds fliers too. Radiant Dawn's are mostly the sides
    between two ledge tiles (no running along a ledge); its `maplinkAt` is a set ordinary movement never reads, so it isn't
    drawn.
- **Stats and movement costs come from the game's own terrain table**, per movement type, fliers
  included. Fliers' access to forest differs by game.
- **Crop each map to its playable grid** (the map file's own where it stores one; otherwise fireemblemwod.com's gridded
  overviews, then the user's in-game check). Units off the grid are spectators and are dropped.
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
  - a skull for the chapter's own boss (whose defeat wins it, where the script says so: Path of Radiance's Muarim); a boss who
    only passes through (the Black Knight in Ch.11 and Ch.24) is a named foe there. The GBA games say whose fall it is: each
    character's death quote names the flag its death sets per chapter, and flag 2 is the boss's (`scripts/gba_bosses.py`). A boss
    whose death doesn't set it there (Kishuna arriving in Aion's chapter, Selena where Beran is the boss), or whom the script takes
    off the map before the chapter ends (Narcian and Zephiel in The Binding Blade's Chapter 13), is a named foe; on a seize map a tie
    goes to the unit on the seize tile. Where the game flags two bosses and each withdraws when the other falls (Echoes' Zofia Castle:
    Desaix and Slayde), both get the skull (the user's call). Genealogy of the Holy War is won by seizing, never by a defeat: every
    castle's holder gets the skull, not only the last castle's (the user's call);
  - a red soldier for named foes, playable characters who fight you included (Fates' Benny and Charlotte in Revelation 14),
    except in Fates' joke grinding maps, where the whole cast turns up as foes (Beach Brawl, Royal Royale);
  - a plain red dot for common ones;
  - a badge for item droppers;
  - a small torch badge for looters, units that go for villages and chests (every game), whose note says what they do and, where
    they leave the map after, the exits they head for; Radiant Dawn's arsonists (Part 3 Ch.9), who make for houses to set them
    alight, carry it too, with a legend line of their own. The GBA games' come from each unit's movement AI, read in the program
    (`scripts/gba_ai.py`: what its script goes for, chests only for a unit holding a key or a lockpick it can use, a turn's wait first,
    and the chapter's escape points for those that leave); a unit the AI only sends off the map says so, with its exits, and no badge,
    and a village names the looters on the map at the start that can raze it. Awakening's come from each placement's AI slots
    (`data/AIData.bin` defines each routine, its parameters the placement's fields: a thief's chest, then its exit; a raider's
    village), and a green unit's AI gives its goal (a tile, a unit to go for or talk to, holding still); Shadow Dragon's from each
    placement's AI slots too (+0x28-+0x44: a thief's chest and exit, a raider's village); Echoes' from each placement's four routines
    (+36-+72, `GameData/AIData.bin`: a turn or a foe in reach it waits for, a unit, tile or terrain it heads for, a unit it attacks
    first);
  - a foe whose AI has a pattern of its own says what it does (the user's call): one that chases a particular unit names it ("Goes
    for Emmeryn"), read from its AI (Awakening's routines that target a person, every game's like them);
  - a foe arriving later (a reinforcement) is an orange ring, or, if it's named or the boss, that marker's shape in orange (an
    orange soldier, a skull outlined in orange), so a named foe or boss is marked as one whenever it turns up.
  - a unit that covers several tiles (Three Houses' monsters: 2 by 2, the largest 3 by 3, read from the game's monster table) has
    its marker stretched over its whole square, badges at the square's corners, and tapping any of its tiles shows it; a monster
    with several health bars has a pip for each along the bottom of its marker (the user's call).
  - Fates capture badge: capturable bosses and named foes only, a small badge like the drop badge: the bosses the game keeps a
    prisoner record for (`PID_捕獲_…` in GameData.bin), outside the DLC. Never anyone playable on any route, and generics
    aren't marked.
  - a small gem badge (top-left) for a foe holding something rare that you can take from it and it doesn't drop, said in its line
    ("Steal: Energy Ring"; Thracia 776: "Capture to take: …") (the user's call). Taken the game's own way: a thief's Steal (the
    GBA games, Path of Radiance, Radiant Dawn, Three Houses), or in Thracia 776 capturing it, which takes weapons too. Rare: an item
    kept for something lasting (a stat booster, a promotion or skill item, a gem or coin to sell, something that works while held)
    that no shop keeps in stock (a one-off bargain, or a secret shop behind a Member Card, doesn't make it common), or, where the
    game lets weapons be taken, a weapon no shop, bargain or forge offers (the weapon page's "Steal from" lines); Thracia's shops sell
    so few weapons that a weapon or staff there counts only when fewer than 15 capturable foes in the whole game hold it (the user's
    call: the Master weapons and the magic swords, not every soldier's Javelin). Thracia marks only a foe one of your units can
    capture (its Con, Sleep for a mounted one, reaching it). Never an item used
    up for a moment (keys, lockpicks, healing, torches, mines), what the foe drops, what the game won't let go (the GBA games' thieves
    take only items; Path of Radiance's foes keep the accessory they wear and a lone weapon; Radiant Dawn's `/L` slots, `sealsteal`
    items and Ashera's), a recruit (who brings its items along), or anything on a trial map (nothing taken there is kept). A game
    with no way to take a foe's items (or only its gold: Genealogy's Steal) has none.
- **Green units:** the person icon is only for named ones, to draw the eye to them. Generic green units
  (another army's soldiers, villagers, RD 3-3's horses) are a plain green dot, like common foes in red.
- **Yellow units:** a partner army that fights on your side under the game's control, which the chapter's lord gives general
  orders with the Direct command, all of it at once (the user; both games have the command) (Path of Radiance's army 3: Lethe
  and Mordecai in Ch.9, Ch.10's prisoners once talked to; Radiant Dawn's army 3, the "Partner" army), is drawn the same way in
  yellow, arriving ones too, and says whether and when it joins.
- **Green units say what they do:** talk to recruit (with whom), where they leave the map, and their own
  destination when the AI fixes one (RD 3-3's horses). A foe who can be talked to says so too, and what the talk does ("Recruit:
  talk with Azura", or Fates' Arthur and Effie in Birthright 23, who turn green): read from the chapter scripts' talk events.
  Everything a talk does is said: a squad that turns green with its leader (The Binding Blade's Klein and the four Archers are noted
  on both), a talk that clears the chapter or opens another (The Blazing Blade's Fargus; Nino's talk with Jaffar opens 26x, found by
  playing the chapter's end with the talk's flag), a recruit for gold ("Recruit: talk with L'Arachel, or with Eirika for 9,980
  gold"), and what a coded talk asks first ("once Klein is yours, after an earlier talk while Klein was still a foe").
- **A unit the game names only by its army goes by its class** ("Fighter", "Maid"), as the game shows it, never the army's name
  ("Nohrian", "Invader", "Vallite"): on the map, in a pair-up, and in what drops an item. Green and yellow soldiers too (Radiant
  Dawn's "Crimea" and "Daein" are Lance Paladins, Halberdiers and the rest); a name for a role stays ("Prisoner"). A boss is no
  exception (The Sacred Stones' "Monster" bosses are an Entombed, a Gorgon...). An army's name is one several characters share, at
  least one without a portrait (a person's several versions all have one): the GBA games, and Awakening's person files (+12) with
  each DLC map's own. A label several share that all have one is a role's, and stays on a plain marker, where someone carries it
  without one elsewhere (Awakening's villagers), else one person's several records (Chapter 23's two Validars); a DLC map's heroes
  have no label at all, so they're people.
- **Stand-ins:** a unit the game places only when a character is gone (died, or left that army) is that character's
  stand-in, never a second unit on the same tile. One toggle per map swaps every stand-in in at once. Genealogy of the Holy War's
  Generation 2 substitutes (Creidne for Larcei...) are their children's stand-ins; a child and its substitute share one item, so it's
  one line ("Carried by Larcei or Creidne on joining"), and the weapon page groups its rows by generation (the user's call).
- **Neutral armies** (Genealogy of the Holy War's third relation: an army neither hostile nor friendly to yours) get a marker colour
  of their own, matched to the game's, and turn red or green when a script turns them; each unit's note says when (the user's call).
- **Shown on the map:** the lord's start ("Lord's start", with the lord named in the text), forced
  deployments (fixed tile or not), and joiners.
- **Difficulties:** one entry where they're the same. Never repeat identical text per difficulty. Where only a level changes (The
  Sacred Stones' generic foes gain or lose the chapter's levels per difficulty; Path of Radiance's, 2 more on Easy; Radiant Dawn's,
  2 more on Hard; The Blazing Blade's, where a difficulty's own group gives another), the unit's data says its Normal level with the
  others beside it ("Lv 3 (Easy 1, Hard 6)"), and the map shows the picked difficulty's ("Lv 1" on Easy). Growth a difficulty gives
  that the shown level doesn't count (The Binding Blade's Hard levels, The Blazing Blade's Hector Hard, the 19 levels a promoted foe
  gets on Hard in FE7 and FE8, Awakening's Hard and Lunatic levels and raised weapon ranks) is a note shown on that difficulty only
  (`notesOn`), read from the code; what every difficulty gives (Awakening's promoted generics' 19 levels) is a plain note.
- **A difficulty gets its own entry in the bar only where its data differs** (checked in the files and the code); otherwise it
  stays bundled with the one it shares everything with ("Easy / Normal"). Path of Radiance's Easy opens with its own placement
  records and levels, so it's its own. Radiant Dawn's Hard shares Normal's placement records but adds 2 levels to the auto-levelled
  foes, so its Easy, Normal and Hard are each their own. Awakening's Lunatic+ is Lunatic's data with foes' extra skills, which the maps
  don't show, so it's one entry: "Lunatic / Lunatic+".
- **One group per arrival:** what one handler places at one time is one group (Jill and her Wyvern Riders), and the same group
  placed at different times on different difficulties is one group whose time says each ("Turn 3 (Hard: turn 2)"). In the GBA games
  (`gba_maps.one_per_arrival`): what one handler places on each difficulty is one group, a unit only some difficulties have marked
  so; the same units on the same tiles placed by handlers of their own are one group whose time lists each ("Turns 4, 6 and 8, your
  phase"), per difficulty; groups that come at the same moment, set off the same way, are one; the same units placed twice at once
  (The Binding Blade's Chapter 5 lists one Hard event twice) stay two.
- **Shadow Dragon's maps** are the grid inside its one-tile border. The opening scene is played out (Dispos, moves, warps, removals;
  what a scene moves between UnitStackPush and UnitStackPop goes back), so units stand where it leaves them. A gaiden chapter says what
  opens it, from the end of the chapter before. A reinforcement an area brings shows the area; one a turn handler places on several
  turns is one group with its turns. Its six modes (Normal, Hard, Brutal, Savage, Fiendish, Merciless) are each an entry in the bar:
  they don't move or add units, but a foe shows the picked mode's weapons, each mode's growth and weapon-rank floor are notes on that
  mode, and the prologue is Normal's only (the Hard modes' army joins in Chapter 1).
- **Echoes' dungeons**: each battle field a dungeon's wandering foes use is one map. Its groups are the five formations an encounter's
  foes can take (plain "Encounter foe" markers) and the fixed encounters on their own tiles (gatekeepers); each other encounter's line-up
  is a note on the difficulties it holds on, with its chance (a shared group's pick) and the act it appears from, which under the
  spoiler block it waits for. These groups are how the battle starts, so the block keeps them. The amiibo ordeals have no wandering
  foes, only their guards (each one's item drops once, as their script has it). The dungeon's boss battles are maps of their own. A
  cemetery's first battle (in the story) has its first layout on the tiles of its Enemy records; the layouts that gather there again
  after a battle, with the game's figures, are the groups of its skirmish map (the third list), as are the Dragon's Maw's returning
  Necrodragons. An army the world map's node holds from the start (`Data/Chapter.bin`) with no tiles of its own (Zofia Castle's Slayde,
  Rigel Plains' Zeke) stands on the Enemy group's empty records from the start.
- **Random monsters** (The Sacred Stones' Tower of Valni and Lagdou Ruins: the game picks their class, level and items as the floor
  loads) are shown where they stand as "Random monster", with nothing about what they are or carry.
- **A reward an end scene gives only on a condition** says the condition, read from the script's own checks (FE8: "if all three
  'Renais Cit.' units survive"). A gift is under only the checks whose branch holds it: one that guards a scene or a join before the
  gifts doesn't make them conditional (Awakening's Paralogue 22), and stacked thresholds each say their own ("if Inigo defeats 3 or
  more foes and survives"). Who a gift goes to is said where the script hands it to a unit ("to Tiki").
- **A choice the chapter asks** (Awakening's Paralogue 13: whose offer you take) says what each answer does, read from its branches:
  the armies it turns (on the map and on each unit), the groups it brings ("if you accept Gyral's offer or turn both offers down"),
  the drops it clears and the reward it sets.

## Maps: events and objectives

- **An end scene's cast is never a unit on the battle map:** a script that goes on to the next chapter only stages its scene
  (The Sacred Stones' Chapter 4 ends with Eirika, L'Arachel and Dozla; Lyon speaks in Chapter 18's), so it brings no joiners or
  groups, and nothing it carries counts.
- **Reinforcements are fixed by each chapter's script:** say when they come, and what stops them where the game checks it (The
  Binding Blade's Hard-only groups and any script that tests the boss's flag: "until Dory is defeated"). A script handler that calls another (Path of
  Radiance's opcode 0x37) is followed, so what the callee does counts for the caller. An area's group says the phase it comes
  in ("At the start of the next player phase after one of your units enters the marked area"). The GBA games check an area right
  after each unit acts, against that unit's tile, any army's: the group comes at once, "As soon as one of your units stops in the
  marked area" where its script goes on only on your phase (or for one character: "As soon as Eirika stops...") and waits again
  otherwise, "a unit of any army" where it doesn't. A time names what sets it off (a seize point Roy seizes, a door opened, the
  areas whose flag a group waits on, drawn), read through scripts that set the flag and the checks' code; only what can't be read
  says "After an event in the chapter".
  - Only the Fates grinding maps (Boo Camp, Ghostly Gold, Museum Melee, Beach Brawl, Royal Royale) are
    random. There, show only the spawn points and where those enemies head. A script that summons one of its own groups at random
    (Echoes' The Creation) shows each group, saying how it's picked and what holds it back, as the script checks it (a check that
    names another person holds nothing back: the game's own, kept).
- **Anything that reshapes the map previews before and after**, one at a time (Revelation 10's snow is dug a tile at a time, as in
  the game, the foes under it showing as their tiles clear, or cleared all at once):
  - Dragon Veins;
  - breakables (they become what the game has under them; RD 2-E's becomes a ledge; the GBA games' cracked walls, with the
    chapter's wall HP, and snags, 20 HP, which clear onto their bridge, drawn as fallen trees, not cracks);
  - the GBA games' doors and scripted map changes (`scripts/gba_doors.py`: a door opens the change under its tile; a script's says
    what sets it off: a turn, an area, a talk); Echoes' doors (a battle's terrain script sets a door trick over a door tile: any unit
    beside it opens it, and a door tile with no trick never opens, which the map says) and its scripts' floor changes (the royal
    chambers' earthquakes and moving supplies);
  - boulder paths, traced off the map unless the rock breaks first;
  - torches, including ones lit from the start;
  - RD clouds, by turn and phase.
- **Objectives:**
  - Seize, escape, arrive and defend are the blue outline.
  - Any other kind gets its own look (RD 3-3's supplies to burn: a sacks icon with an orange outline).
  - Exit tiles say who leaves by them; drop the exit if nobody uses it.
- **Chest, village and hidden contents come from the scripts**; hidden areas show their dig zone.
- **Fog of war** shades what's unseen; torches show what they light. Fog that only some difficulties have shows on those
  only (Path of Radiance's Ch.5, on Hard; The Blazing Blade's Living Legend, on Hector Hard). Fog a script brings in or lifts on a
  turn says so in the notes, the map shaded as fogged (The Blazing Blade's A Grim Reunion from turn 3, The Binding Blade's Chapter 14
  lifting on turn 26).
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
  the chapter's own on the picked difficulty, since it changes from base to base; gifts and map sources are kept once reached.
- **Only what you can actually see in the chapter:** a boss's weapon counts only where the boss is a unit on the map
  (Petrine's Flame Lance is on the Great Bridge, not in Ch.7 where she is a cutscene), never from a placement file. What a
  foe who arrives mid-chapter (a reinforcement) carries or drops is listed from the chapter after the one it arrives in, when
  it's been seen. A weapon you can only steal counts as seen once a foe carrying it is (as a drop does). Not listed under the
  block: a foe's spare weapon that's sold or forged anyway. A side map (a paralogue, a DLC map) is played before the chapter it
  opens at, so what arrives or is handed over on it counts from that chapter, as its chests do (`turnsUpAt`); one that opens with
  the story's last chapter (Awakening's Paralogues 18-23) still shows what it gives.
- **Gear and gifts count from the first base you have them at:** a recruit's own weapons from the chapter after the battle they
  join in, or from the chapter whose opening or base hands them over; a script's gift from the chapter it runs before (a base
  conversation, an opening), or from the next when it comes at a chapter's end or from an event during it (Rhys's Mend after
  Ch.6, the Ashera Staff after Ch.22). What a chapter's setup gives a unit it places on another side (Shinon's Brave Bow in
  Ch.18, Gatrie's spare lance in Ch.13) is that unit's, not a gift: a foe's drop is on the map. The GBA games mark the next
  chapter with a kind ending in `-later`: an end scene's gift (`event-later`: Durandal, the legendary weapons), a talk's gift
  (`talk-later`: Lilina's Thunder), a foe a talk recruits (`kit-later`: Joshua's Killing Edge); an opening's gift is `gift`, from
  its chapter (The Sacred Stones' Prologue Rapier, Eirika's on every route; Easy's tutorial hands over the same one). Genealogy of
  the Holy War's home castle is open mid-chapter, but a recruit who joins during a chapter, and a talk's gift, still count from the
  next one, so nothing at a chapter's start gives away who joins later (the user's call).
- **A buying price is only said while a shop of yours stocks the weapon** (before that, just what it sells for). The Tellius
  games keep their Price tile: their sale price is worked out from it (half the price of the uses left).
- **Descriptions say only what applies by this chapter:** "Bought at the base's armory: Chapter 9", "Given in a base
  conversation before Part 3, Chapter 6". Nothing is said where a base doesn't sell it.
- **A map shows only how it starts:** no reinforcement groups and no joiners, friend or foe, and none of the notes or
  weapon sources that give them away (a foe that arrives later, "arrives with Group 3"). Units placed on the map,
  forced deployments and objects stay.
- **Side maps** (trial maps and the like) open once the story is cleared: with its last chapter. Echoes' Act 6 opens with the Final
  Battle, the amiibo dungeons with Act 3, every other map outside its story with the first story battle after it. Its Acts 3 and 4
  run both armies at once; the list puts Alm's battles first where the game allows it: in Act 4, Alm reaching the Dragon's Maw before
  Duma Tower is cleared springs its trap and shuts his road on, so Celica's Act 4 comes between (`data-raw/fe15/README.md`).
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
- **My Castle's rank rewards and amiibo items are static collectibles**, like Tarvos: listed from the chapter after Chapter 6
  (the castle opens), any number of times. Allies' gifts and the Lottery Shop's prizes open by chapter (below). The story's
  gifts come with a chapter (Yato's forms: Fire Emblem Wiki). DLC maps and their rewards open after Chapter 6 (the Dragon's
  Gate), paralogues by chapter.
- **A child's paralogue opens the chapter after their fixed parent joins your army for good** (the other parent is whoever you
  marry): Soleil follows her father Laslow (joins in Conquest 12, so Chapter 13), Shigure his mother Azura (Conquest 9, so 10).
  Joins are read from the game's chapter files (`scripts/build-fates-joins.py`: scripts that hand a unit over, Support groups,
  the Player groups) and checked against Serenes Forest's recruitment pages in a test; nothing opens before Chapter 7 (the
  castle). Jakob joins in 6 or only after 15 depending on Corrin's gender, so his son Dwyer's waits for the later date.
  Mozu's (Paralogue 1) opens after Chapter 8 (Gamer Guides), not confirmed in-game.
- **Fates' weapon page leaves three things off until a switch is ticked:** "Show visit & battle rewards" (a weapon whose only
  source is a My Castle Battle Points or Visit Points reward; one with any other way to get it, allies' gifts and the Lottery Shop included, is
  listed normally, and its reward lines only appear once the switch is ticked),
  "Show DLC items" (DLC weapons and what only the DLC maps carry), and, as ever, foe-only ones ("Hide foe-only" is a hide
  switch). The new-weapon count in the bar counts only what the list shows by default.
- **Your own units' starting gear is yours from the chapter they appear in** (Fates): Chapter 1's Bronze Sword, Gunter's lance and
  Felicia's / Jakob's dagger and Heal from Chapter 2, Corrin's Yato from the chapter the placement files give it (6 on
  Birthright and Conquest, 13 on Revelation). It comes from each chapter's Player groups where a unit first turns up, and from
  what a recruit brings in the chapter they join (a Support group, a green unit handed over, a foe a talk recruits: Keaton's
  Beastrune in Conquest 14). Later Player groups list units with preset gear the game never hands over (Azura's Bronze Lance in
  Birthright 6, Benny's Blessed Lance in Conquest 21): that doesn't count (`kit` on the map).
- **No filler lines for "not available":** where a shop doesn't stock something, the page says nothing at all, so a blank can't
  hint at what comes later.
- **Allies' gifts open by their gate:** the item table puts each gift (the joke, Raider and named weapons, the Harp Yumi,
  Berserker's Axe) in Hoshido's pool, Nohr's, or both, with a gate. Birthright's allies give from Hoshido's pool, Conquest's from
  Nohr's, Revelation's from both (a coin flip per gift); who the ally is doesn't matter. A gift is listed from the castle visit
  after the first story chapter whose progress number reaches its gate (gate 0 from Chapter 7, 13 from 14, 21 from 19), and says
  "Given by allies in My Castle". Decoded in the program and checked live (`data-raw/fates/README.md`). Birthdays give from the
  same pools and aren't listed separately.
- **The Lottery Shop's prizes say the levels that give them, not the odds:** each prize is in one lottery, Dawn (Birthright and
  Revelation) or Dusk (Conquest and Revelation), with a rank; a rank comes up at some levels only (rank 1 at levels 1 and 2,
  ranks 2 and 3 at any level, 4 at 2 and 3, 5 at 3). A prize is listed from the chapter after the first level that gives it
  opens (levels open after Chapters 7, 13 and 19), and under the spoiler block only the levels open by then are named.
- **Generated data carries the chapters:** `shopAt` / `bargainAt` / `forgeAt` (map ids behind the shop text), `baseAt`
  (base conversations: script handler kind 14) and `giftAt` (a script's gift outside chests and villages, or a quiet
  handover in a chapter's `Opening` or at its end; a handler another one calls is read through its caller, at the caller's
  time). Every id must be a chapter of the story (tested in
  `src/logic/__tests__/spoiler.test.ts`).

## Build and offline

- **Each game is its own file** (`src/games/<id>.ts`, loaded by `load()` in `src/games/index.ts` when the game is first
  picked), so the app's main file stays small and a change to one game doesn't re-download the others. Shared screens must
  not import a game's data directly; pass it in.
- **Every file is precached** so each game works offline without being opened first. The PWA plugin's per-file limit is
  4 MiB (`vite.config.ts`); a game's file passing it means splitting that game further. `scripts/check-precache.mjs` runs
  after the build and fails if a script or stylesheet is missing from the offline list.
- **Updates come only from the user's tap** (the user's call): the header's "Check for updates" looks for a new version, and a found
  one waits until a second tap on "Update now" switches to it and reloads (`src/components/UpdateButton.tsx`, the PWA plugin's
  `registerType: 'prompt'`). The app never checks, offers or reloads on its own, so a stray tap or a deploy never changes the page
  under you.
- **A deploy that fails is urgent:** GitHub Pages stays on the last good build (the Tower maps were missing for days).

## Look and layout

- **Icons are the app's own 10×10 pixel sprites** (NES Zelda look) in `src/icons/sprites.ts`, never emoji.
  Each should look like the thing, be distinct from the others, and not be overdone. The legend uses the
  same icons as the map.
- **Everything fits a phone screen.** Tapping a weapon scrolls to its datasheet.
- **Wording works for every game** ("Lord's start", not "Corrin's start").

## Process

- **Build the base from the data first; the user then checks in-game.** Their corrections become rules here.
- **In a review, whatever needs the user's in-game check is noted to them and set aside;** what data dives and careful checks of
  the files and code can settle is done first.
- **Check counts against outside sources in the tests** (enemy totals per map, wiki or fireemblemwod.com),
  with every exception explained.
- **Back each rule with a test where it can be checked** (e.g. no pillar icon on a tile no one can enter;
  only grinding maps spawn at random).
- **Before calling a map done, look at it in the browser.**
- **Commit and push each finished step.** End commit messages with the co-author line.
