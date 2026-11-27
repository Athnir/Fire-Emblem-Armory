# The final pass: maps to check in the game

Maps the review can't settle from the files and the pictures to hand, which the user will load in the game. Their games are frozen
until then (CLAUDE.md, "Frozen so far"): once a map here is checked, unfreeze it with the user's OK, fix it, and freeze the game again.

| Game | Map | What to check | The user's note |
| --- | --- | --- | --- |
| Awakening | Champions of Yore 1, 2 and 3 (`fe13-dlc1` to `fe13-dlc3`) | Which village look the game gives its villages, zoomed in or zoomed out; the renders show them too small to tell | "Can't see the villages properly", "Village zoom needs to be checked" |
| Awakening | Lost Bloodlines 1, 2 and 3 (`fe13-dlc7` to `fe13-dlc9`) | The same: the villages' look | "I'm not sure if it's the zoomed in or out type village" |
| Awakening | Rogues & Redeemers 1 and 2 (`fe13-dlc13`, `fe13-dlc14`) | The same: the villages' look | "same note as 3" |
| Fates | Paralogue 16, Abducted (`fe14-x16`) | The whole map against the game: the render's overgrown halls are hard to read | "Map image issues" |
| Fates | Museum Melee (`fe14-dlc-6b`) | The rest of the map against the game (its Exit tiles a purple pad and its sky the void since 2026-11-26) | "will wan to look at manually for this map for the rest" |
| Fates | Paralogue 16's challenge (`fe14-x16-challenge`) | Its stairs, with Paralogue 16 above | "Check" |
| Fates | Paralogue 22 and its challenge (`fe14-x22`, `fe14-x22-challenge`) | Its stairs: (9, 3) to (9, 4), (19, 3) to (19, 4), (2, 24) to (3, 24), (22, 24) to (23, 24) and its openings | kept for the manual check; "Check" |
| Three Houses | Silver Snow 26 (`fe16-26-ss`; Verdant Wind 26 the same stage) | The whole map against the game: its neon lights make the photos too odd to grade by | "will have to manually load the map" |
| Three Houses | Crimson Flower 37 (`fe16-37-cf`) | Which of its houses stand and which are in ruins (all in ruins now) | "Can load manually if needed" |
| Gaiden | Its forts, every map (the fort tile, $DA: 103 tiles on 40 maps) | Draw them as the supply tile (`nd`: a fort's numbers, a grain sack before a crate), as Echoes' supplies, which remake them, are drawn since its review of 2026-11-25; Gaiden is frozen, so it waits for this pass | "lets make a supply tile variant for the fort that we can use for 2 and 15, will replace them in 2 in the final run but they are not really fort tiles" |
| Engage | Tempest Trials, final stage, maps 1 to 6 (`fe17-c000-1-1` to `fe17-c000-6-1`) | Each map against the game: all six cards show map 1's emulator photos (one set, taken once) and its colours; each map's grid is its own already (its opening script takes islands and bridges away), its sky the void since 2026-11-26 | "will need to manually go through each level of this map to get the correct version of the map, i think you grabbed the first floor version for all of them" |
| Engage | Tempest Trial, Verdant Plain, map 4 (`fe17-c001-4-1`) | The whole map against the game | "manual" |
| Engage | Fell Xenologue 5, The Fell Heir (`fe17-e005`) | The whole map against the game | "manual" |
| Engage | Fell Xenologue 6, Seven Bracelets (`fe17-e006`) | The whole map against the game (marked good) | "manual" |
| Engage | Divine Paralogue, The Doting Sister, and its skirmish (`fe17-g005`, `fe17-g005-sk`) | Its bridges (drawn whole since 2026-11-26) and the rest of the map against the game | "bridge issues. manually check", "manual" |
| Engage | Divine Paralogue, The Shepherd Exalt (`fe17-g006`) | The whole map against the game, its altars too | "manual" |
| Engage | Chapter 7, Dark Emblem (`fe17-m007`) | The whole map against the game | "seems off, i will look at it manually ingame" |
| Engage | Chapter 18, The Cold Voyage (`fe17-m018`) | Its wooden blocks (the game's Ship, drawn in the ship's wood): crates on the decks rather than the ships' walls | "will have to manually check this one, the wood blocks are for decortave crates insted of boat walls" |
| Engage | Chapter 19, The Dead Town (`fe17-m019`) | Its houses, (10, 17) first | "village gore (10, 17) , will check manually" |
| Engage | Paralogue, The Caring Princess (`fe17-s013`) | The whole map against the game, its ship and dais | "will look at manually" |
| Engage | Paralogue, The Connector (`fe17-s015`) | The whole map against the game | "manual" |

## Checked in the game

| Game | Map | What the user saw | Done |
| --- | --- | --- | --- |
| Radiant Dawn | Part 3 Ch.1, Laguz and Beorc (`fe10-3-1`) | "ch.1 plains are cobble" (2026-11-26, through a chapter jump: `scripts/fe10_jump.py`) | Its plain paving (`PLAIN_AS`) |
| Radiant Dawn | Part 3 Ch.7, Rivals Collide (`fe10-3-7`) | "7 is all dirt", "just make sure that you can see the difference between the river and the dirt tiles" (2026-11-26) | Its plain dirt (`PLAIN_AS`), its river a muddy riverbed a clear step darker (`FILL_FIXES`) |
| Three Houses | Chapter 9 (`fe16-9`) | Its ruins (varied tile to tile since 2026-11-26) against the game | "manual" |

## The look-over's checks (2026-11-26)

What the look-over's fixes read from the files and code but couldn't play: each is in the apps as the files say it, to check in the
game when the chapter comes up.

| Game | Where | What to check |
| --- | --- | --- |
| Shadow Dragon and the Blade of Light | Chapter 16's villages | Whether a first recruit who has died still blocks the other village (3:$8D6D passes over a record whose +0x12 is 0xFF) |
| Shadow Dragon and the Blade of Light | The enemy-phase recruits (Minerva, Catria, Palla, Est) | That a recruit that attacks fights before it joins (traced in code) |
| Mystery of the Emblem | Book 1 Chapter 3, Navarre | His HP after Caeda's talk: the swap copies max HP too, so likely 19/19, not "out of 20" (the Roster's note and its test's override) |
| Genealogy | Chapter 9, Altena | With Finn dead, Leif's talk with Altena isn't offered (read from the opening script only) |
| Genealogy | Chapter 2, Chulainn | Whether he joins right after the arena win or at the next castle entry |
| Genealogy | Chapter 6, Iuchar and Iucharba | That the second brother's talk is gone once the first has joined (one shared flag) |
| The Blazing Blade | Cog of Destiny | The timing of its area-held reinforcements, pass by pass |
| The Blazing Blade | Hector's 31x, Karla | What happens when one of the duel's two falls |
| The Sacred Stones | Ephraim's Chapter 15 | Whether the chapter is lost if Eirika falls (unconfirmed, as before) |
| New Mystery | Chapter 1, Gordin or Draug | That a deployment slot with flag 0x80 brings its unit in (answer Yes at Prologue III and look for Gordin) |
| Awakening | Paralogue 10, Severa | Whether she walks to Holland from the start (her AI) or only after Chrom's or Cordelia's talk (the wiki) |
