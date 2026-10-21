# Fire Emblem Armory: the ruleset

Rules settled with the user while building Fates, Path of Radiance and Radiant Dawn. Follow them for every
new game, so the same fixes don't have to be caught again. When the user settles a new rule, add it here.

## Scope

- **Game data only.** Weapons, forging, shops, maps, true hit, and what supports do. Anything about specific
  units (affinities, who supports whom, growths, builds) belongs in the partner Unit Planner
  (`../Fates App`), not here. Units on a map are fine: they're chapter data.
- **One game picker; every tool for that game sits in the same tabs** (Weapons & forging, True hit, Maps,
  Supports). No extra menus or tool-picker steps.
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
- **Everything generated comes from a re-runnable script**; fix the generator, never the output. Formats go
  in `data-raw/<game>/README.md`.
- **The game wins.** When the data contradicts a wiki or memory, say so plainly and point to the file. Bugs
  are kept as the game has them (Florete is physical; Conquest 11's "forts" are gates).
- **Check mechanics in the program code for each game; never assume they match another game.** Effective Mt is
  ×2 in PoR and ×3 in RD. Brave strikes twice on both phases in Tellius. Beast and horseback targets are
  separate in Tellius. Healing jars reach only the 4 orthogonal tiles. Height gives +2 Mt and +50 Hit.
- **Anything not confirmed goes under `unconfirmed`, not stated as fact.**

## Weapons & forging

- **List only what the player can get:** sold, forged, given, in a chest, village or hidden spot, dropped,
  carried by a recruit, or stealable.
- **Leave out:**
  - foe-only weapons (Ashnard's);
  - weapons fixed to the map (ballistae, onager, fire orb);
  - codes-only items;
  - a foe's lone weapon that can't be stolen.
- **Steal rules are per game:**
  - PoR: unequipped weapons whose weight is at least 1 under the thief's Str. A foe's second weapon counts.
    A silenced foe's lone tome counts once they use an item (Rexaura).
  - RD: everything can be disarmed except `/L` slots, `sealsteal` items and Ashera's.
- **No flavour descriptions.** Only what the weapon does, in its datasheet (the Bamboo Yumi gets none).
- **Effects are pixel icons:**
  - Effectiveness shows its target: helm (armour), dragon head, wing, horse head (horseback), lion head
    (Tellius beast laguz), monster.
  - Brave has its own icon, and might boosts use one up arrow.
  - "No crits" and "no skills" always go together.
- **Effective weapons show their boosted Mt.**
- **Foe-only classes are left out of class lists** (Stoneborn).

## Maps: terrain

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
- **Shown on the map:** the lord's start ("Lord's start", with the lord named in the text), forced
  deployments (fixed tile or not), and joiners.
- **Difficulties:** one entry where they're the same. Never repeat identical text per difficulty.

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

## True hit and supports

- **True hit:** the hit system is checked in the game's code (Fates' own hybrid formula, Tellius 2RN).
- **Supports:** only what a support gives per level, and how it rounds and stacks. No pairings.

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
