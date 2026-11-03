# Genealogy of the Holy War (FE4) game files

Read from the user's own cartridge image: `Fire Emblem - Seisen no Keifu (J).smc` (SNES, Japanese, HiROM, 4 MB, no copier
header, CRC32 DC0D8CF9). The image stays on the user's PC (default path in `scripts/fe4_rom.py`, or set `FE4_ROM`) and is never
committed; only data built from it is. Read the clean file only, never a fan-translated one.

The SNES address `$XX:YYYY` is file offset `(XX & 0x3F) * 0x10000 + YYYY`. Data is little-endian. The fuller breakdown (text
encoding, classes, movement costs, what isn't found yet) is in `FE Games\notes\FE4 Genealogy - notes.md`, next to the ROM.

## Items: pointer table 0x3E9D0

One u16 per item id (0x00-0x88), an offset counted from 0x3E9D0 itself. Weapons and staves are 19 bytes:

| Offset | Field |
| --- | --- |
| +0 | Item id |
| +1 | Kind: 0 weapon, 1 staff, 2 ring |
| +2 | Uses |
| +3 | Price (u16; 65535 = not for sale) |
| +5 | Holy weapon id (0 = not a holy weapon) |
| +6 | Staff effect id |
| +7 | Rank: 0 A, 1 B, 2 C, 0xFF holy |
| +8 | Skills it grants while equipped ($87:A280): 0x01 Steal, 0x08 Miracle, 0x10 Critical, 0x20 Renewal, 0x40 Paragon (the patch's names) |
| +0xA | Type: 0 sword, 1 lance, 2 axe, 3 bow, 4 staff, 5 fire, 6 thunder, 7 wind, 8 light, 9 dark |
| +0xB | Mt (255 on Hell) |
| +0xC, +0xD | Hit, Wt |
| +0xE, +0xF | Range, min and max |
| +0x10 | Effective against: 0x01 horseback, 0x02 fliers (every bow), 0x08 armour |
| +0x11, +0x12 | Special effect and its argument: 1 a spell from 2 tiles away (its item id), 2 drains HP and the spell, 3 drains HP, 4 brave, 5 siege (can't be countered), 6 status (4 silence, 5 sleep, 6 berserk), 7 halves the foe's attack (Loptous), 8 negates it (Naga), 9 Hel, 0x0A women only |

Rings are 10 bytes (ids 0x6A-0x79) and aren't in the weapon list.

## English names: `scripts/fe4_names.py`

Every English name is Lil' Nordion's (1.01, the translation patch Serenes Forest hosts). The patch zip sits next to the ROM
(`Documents\FE Games\Lil-Nordion 1.01.zip`, or set `FE4_PATCH`); `scripts/bps.py` applies it in memory to the clean ROM (it checks
both checksums) and only its name tables are read. Nothing patched is written or committed; every number still comes from the
clean ROM.

- The patch keeps the ROM's pointer tables and moves the strings to bank $50: items at $8D:9402 (by item id), classes at $8D:9892
  (by class id), playable characters at $8D:920D (by the character record's name index, 63 names). Text: A-Z from 0x10, a-z from
  0x2A, 0xBF space, 0x44-0x49 `. , ? ! ' -`, 0x89 á, 0x9B ó, 0x9E ö, 0xA3 ü.
- Castles: the patch's labels at $50:4A00; `PLACES` pairs each with the ROM's kana name (the ROM's own place-name list), and the
  build checks each spelling is in the patch.
- Bosses and other foes have no name table in either version. They're named from Serenes' boss and NPC tables (see Units), then
  spelt as the patch's dialogue spells them: the official name or Serenes' own where the dialogue uses it (in the patch's
  capitalisation: DiMaggio), or `BOSS_SPELLINGS` in the maps generator, each read in context ("You and Gerald are in charge") and
  checked to be in the patch. Names the dialogue never uses stay Serenes'.

## `scripts/build-fe4-items.py` -> `src/data/fe4/fe4Weapons.ts`

Read from the ROM alone (no network): the item table, the holy weapons' records and the code that uses them.

- **Left out:** rings, items with no uses (the broken stubs and drained tomes a weapon becomes, and the Charm and Thief Staves no one
  has) and the ballistae's arches (uses 255: Ballisticians never move, Mov 0 and movement type 13). The weapon page lists only what
  something gives or a foe carries (`fe4Listed.ts`), so the Silence Edge, which nothing has, isn't shown.
- **Holy weapons:** the records at $83:89E3, 16 bytes per holy id (the item's +5, 1-13): +0 the weapon type, +1 the weapon itself (the
  build checks it), +2..+9 the blood's growth bonuses, +10..+15 Str, Mag, Skl, Spd, Def and Res while it's equipped ($84:A6B6, through
  the offsets at $83:89C9). Holy ids past 13 aren't records ($84:A6CC): the Def and Res routines add 7 for the Safeguard (0x0E) and the
  Barrier Blade (0x0F) themselves ($84:9C8B, $84:9CF7). Rank 0xFF goes to $84:F66E, which allows the weapon only to a unit with its
  Major blood (the record's +1 is the weapon) and some rank in its type; the Valkyrie Staff, holy id 0, is record 11's. Selling refuses
  rank 0xFF ($84:B2DF), so a holy weapon has no price on the page.
- **Effectiveness:** $84:E27F sets the crit rate to 100 when the weapon's +0x10 bits meet the defender's class bits ($83:8016: 0x01 15
  mounted classes, 0x02 pegasi and every wyvern, 0x08 the armours, Baron and Emperor), and a crit doubles the whole attack (Mt + Str or
  Mag) before Def or Res comes off ($84:E6A9-E6C3). No crit lands on a defender with Nihil (skill 0x0E, $84:E699).
- **Effects:** a magic sword from 2 tiles away is swapped for its spell whole ($84:DB25): Mt, Hit, Wt and type are the spell's, Mag
  against Res, in the magic triangle. A status sword, after a hit, has a (30 - the foe's Res)% chance ($84:E8C0-E8CE). Brave doubles
  the strikes ($84:E2FD). A siege weapon can't be countered ($84:D9CF clears the target's weapon); that its user can't move after is
  in no effect-5 check read (unconfirmed, so not said). Loptous halves the foe's attack unless it wields Naga ($84:DAF0-DB21); Hel
  sets HP to 1 ($84:E904); the Lands Sword and Nosferatu drain ($84:EC80); the Prayer Sword is women's ($84:A3E5 = 1, $84:F61E).
  Weapons give skills only while equipped ($87:A2EF, $84:F42A). The skill names are the patch's spellings, checked in its text.
- **Staves:** $87:E86A heals 10 + the caster's Mag (Heal, Physic, Fortify), twice that (Mend), or 80 (Recover: no unit has more HP).
  Status staves land when the caster's Mag beats the target's Res, with no roll ($84:EE51). A cast earns price / uses / 20 + 10
  experience, at most 100 ($84:F99D). The Valkyrie Staff's range is 0-0: it's used in the home castle.
- **Repairs and kills:** repairing costs price x uses spent / uses ($87:E25D), halved with Bargain like a price ($84:B295, $84:B3C3).
  Each copy counts its kills (+5, up to 100: $87:E13D, $87:E163); from 50, a playable unit's weapon (kind < 2, $84:9461) gives crit
  Skl + kills - 50, Critical or not ($84:FD98), as the weapon page says.

## Chapter maps: `scripts/build-fe4-maps.py` -> `src/data/fe4/fe4Maps.ts`, `fe4Terrain.ts`

The ROM keeps maps compressed with the game's own routine ($80:AA02, an LZ and run-length scheme that also unpacks graphics). It was
found by tracing a chapter load in Mesen 2 (`--testrunner` with a Lua script that presses buttons to reach the Prologue, then logs
which ROM and work-RAM addresses the load touches). `scripts/fe4_cpu.py` is a small 65816 interpreter that runs that routine on the
ROM, so the generator reads the data itself; its output was checked byte for byte against Mesen's work RAM. `scripts/fe4_asm.py`
disassembles the program code.

- **Chapter records:** twelve 3-byte pointers at $88:9FC3 (file 0x89FC3) lead to 27-byte records (Prologue, Chapters 1-10, the Final
  Chapter). A record holds: +0 the compressed map, +3 the metatile graphics, +6 the tile graphics, +21 the width and +23 the height
  (each in units of 16 tiles), +24 the compressed terrain table. Chapters 2 and 8 share Chapter 0's graphics, and the Final Chapter
  shares Chapter 5's.
- **Map:** 64 x 64 u16, one per 16 x 16 tile. The low 10 bits index a metatile; the higher bits are flags not read yet. The Prologue
  uses only its first 32 rows (the rest repeat one tile). The terrain table is one byte per metatile.
- **The playable grid** is inside a one-tile border: every movement search starts at $86:AE80, which fills columns 0 and 63 and the top
  and bottom rows (row 31 in the Prologue) with 0xFF, so no unit stands there. The page shows the 62 x 62 grid inside it (the
  Prologue's 62 x 30): X = x and Y = H - 1 - y from the game's 0-based x and y (H = 64, the Prologue's 32). A joiner who walks in
  from the border is shown entering from the edge tile it steps onto.
- **Map changes:** the chapter data's second u16 (its pointer at $86:C760, read by $81:B4A6) leads to 7-byte entries
  `[u16 chapter][flag][x][y][u16 patch]`, the patch `[w][h]` and w x h metatiles (0x8000: left as it is). Event command 0x5C
  ($86:9435 -> $86:C575) puts every entry whose flag is set; what sets the flag says when (the Prologue's bridge goes on turn 1's
  enemy phase and comes back; ramparts open as groups arrive). An opening that sets flags and runs 0x5C makes its changes before
  the battle (Chapter 7 starts with six gates on its plain and road, which flag 0x37 takes away).
- **Razed villages:** a foe on a village's door raids 500 gold ($84:CF33); $87:F030 redraws the village by stage (gold - 1) / 500
  from the patches at $87:F0A4 (four variants, the village's id & 3, nine stages each). At the last stage five of its six tiles are
  Ruins (terrain 19: a plain's costs, Avo 0) and at 0 gold only the door is redrawn ($87:F096, still a Village). Each village has a
  change showing it emptied.
- **Castles and villages are entered from one tile:** after a move $84:C983 sets the unit's location only when it stands on the
  location's entrance, (x + rec[6], y + rec[7]) from the kind's record at $87:F453: a castle's gate two rows below its tile (all 59
  castles have it there), a village's own (bottom-middle) tile. Visits ($84:CDD6) and raids ($84:CF0F) read it. So the seize
  objective is the castle's gate, and a village is one object, on its door.
- **Terrain ids**, named as Lil' Nordion's terrain window draws them: the patch replaces the game's own names ($84:8EFB, Shift-JIS
  through $83:837B) with pictures (`JSL $51:0800`): per id 16 bytes at $50:3000 (+0 the width in tiles) and the name drawn at
  $58:0000 + id x 0x200, 2bpp (colour 2 the letters' ink, 3 their outline). `fe4_names.terrain_names()` checks the list against the
  drawing: each name cut at the columns with no ink, every letter one shape wherever it's drawn, letters that touch read as the
  two side by side. 0 Peak, 1 Thicket, 2 Cliff, 3 Plain, 4 Forest, 5 Sea, 6 River, 7 Mountain, 8 Desert, 9 Castle, 10 Fort, 11 House,
  12 Gate, 13 Rampart, 14 Sand, 15 Bridge, 16 Swamp, 17 Gate (Chapter 7's opening only), 18 Village, 19 Ruins (a razed village's),
  20 Depository, 21 Ruins, 22 Church, 23 Temple, 24 Bragi Tower, 25 Road. Ids 10, 11, 16, 20, 21 and 23 are on no map. Where a code
  joins several names, each map says which tiles have which (`tileNames`).
- **Codes:** by how the game plays them. The river is waded by pirates at the sea's cost (`tg`, as Thracia's); the castle gate is
  where a castle is entered (`o0`, its own code); terrain 17 has a plain's numbers and nothing else, so it's plain; Bragi Tower is a
  peak's (fliers only); Ruins are `tm`.
- **Costs:** $83:987D, 15 movement types x 26 ids (0x80 = no entry); fifteen types fall into eleven columns. A table cost c costs
  the c-th entry of $86:A91A in tenths of a move ([7, 10, 20, 30, 40, 50, 60, 70], read by $86:A8C5; a unit's move is Mov x 10 + 1,
  $84:9D61), so the 0 that road and bridge hold for walkers is 0.7. Avoid is the signed byte at 0x39A25 + id ($83:9A25, the walkers' table); fliers use the
  table at $83:9A3F (picked by the class record's +0x1B through $83:9A21), 0 for every id but the Temple's, so a tile only fliers
  enter (Peak, Cliff, Bragi Tower) gives no one any Avoid.
- **Classes:** the class table starts at $83:8FC5 (pointers at $83:8F35, through $87:A49D), a byte past where the reader counts its
  31-byte slots, so its offsets are one more than they look: bases at +1, the movement type at +0x1A ($87:A689), the Avoid table at
  +0x1B ($87:A6A1). The page's class examples pair the movement type with Serenes' rows, in the ROM's order.
- **Church:** a unit standing on one is healed to full as the turn starts ($84:B094): your units pay 5 gold per HP and heal as far as
  their gold goes (it needs 5, $84:B0F0); other armies pay nothing. Castle healing ($84:AFC9's chain) isn't traced.
- **No Def from terrain:** the battle reads the tile only for Avoid ($84:D843 -> $84:FD4C); Def and Res come from $84:9E23 and
  $84:9E73 with no terrain term.

Unconfirmed: what the map's high bits mean beyond the AI's lock regions (bits 10-15).

## Units: `scripts/build-fe4-maps.py`

- **Unit lists:** 57 u16 offsets at $81:C000 (file 0x1C000) lead to lists of 8-byte records, each list ended by 0xFFFF:
  `[unit id u16][x][y][flag][group][army][order]`, with x counted from the left and y from the top (tile (1, 1) is the bottom left
  in the app, inside the border: X = x, Y = H - 1 - y). Checked: placed on the maps, 1,168 of 1,232 generic foes stand on tiles their class can
  enter, and the rest are bosses on the Castle defence tile and ballistae.
- **Which chapter a list belongs to:** each chapter's opening loads its first lists (`4A nn` in the opening script, or in a scene
  it runs). The build reads them from the scripts and checks them against what the game was seen loading (`OPENING_LISTS`, from
  `python scripts/fe4_mesen.py lists 0 11`, which forces each chapter through the chapter number at $7E:0D6A). A chapter owns its
  opening lists and every list up to the next chapter's first; the others arrive later (see Events).
- **Chapter scripts:** every chapter has an 8-byte header `[chapter u16][opening script][event table]` (3-byte pointers; the opening
  script follows the header; found by scanning for that shape). `scripts/fe4_cpu.py` can step through a script with the interpreter's
  own skip entry ($86:83F0), which every command handler answers by moving past its operands. `4B [army] [def]` creates an army
  ($84:BBD2; one that already exists is made anew: the Final Chapter makes army 1 again for Arion's men) and `4D [relation] [a] [b]`
  sets how two armies stand, both ways round ($84:C1A5): relation 1 is hostile, 2 friendly, 3 neutral (it clears both bits,
  $84:C1DD). A unit's army is its record's byte 6. The opening sets the first armies; an army a later event creates takes that event's
  own `4D` (neutral if none), and the build carries the relations through the turn and flag blocks in the table's order, so each
  arriving list is drawn as its army stands when it comes (Chapter 5's Travant: made neutral in the block before his wyverns land).
- **The unit id** indexes the character table (u16 count*2 at 0x3AE00-ish: `0x38000 + [0x38002]`, then u16 offsets from there, id 1 upward).
  Four kinds, by their first byte: 3 is a generic foe (13 bytes: id, previous id, class at +5, level at +7, three item ids at +10),
  0 and 2 are named characters (38 bytes: class at +9, level at +10; 0 are the ones you recruit, 2 the named foes and NPCs), 1 is
  the second generation's children (12 bytes, 17 of them). Item ids are the weapon table's.
- **Names:** playable characters (kind 0, and kind 1: the second generation's children, name index at +5) by the patch's name
  table. The game keeps no name for anyone else: its name table ($8D:920D) covers the 63 playable characters, and the text code
  that prints a name holds the index under 0x3F ($91:8D56). So a foe is named from Serenes Forest's boss and NPC tables, by what
  the game ties to a unit:
  - the opening narration's pointer at it (`82 nn [unit u16] 00` after the name: Chapter 1's Kinbois is unit 0x48, not Genoa's
    leader 0x5C);
  - its class and level matching a row, when it's a leader (flag 1, 254 or 255), a named record (kind 2), a castle's holder, a unit
    with its own battle quote (trigger 0x0D [0][talker][FFFF][unit]) or one a scripted talk names;
  - where more units fit than names: the flagged leaders, then the one with its own battle quote (Chapter 2's Elliot, 0x66; the
    other Level 15 Duke Knight has none), then the one holding a castle;
  - a named record or talk partner whose level isn't Serenes' takes the chapter's one row of its class left (Eldigan: a Level 25
    Paladin in Chapter 3, 23 on Serenes; Chapter 10's Polemarch).
  Everyone else is their class. The match uses Serenes' class names (kept from its class table); the page shows the patch's.
  Where several bosses share a class and level (Chapter 5's two Level 30 Barons), the one carrying an item Serenes' item table
  lists for a name takes it (Lombard's Helswath); the Final Chapter's three Dark Bishops and three Falcon Knights carry the same
  items and have a battle quote each, so they keep a shared name.
- **Skulls:** every castle a foe holds (the unit on its castle tile, the home castle aside) gives its holder the skull, named or
  not ("Holds Genoa"): the user's call, as Genealogy is won by seizing. A playable character never has one.
- **Children and substitutes:** the game's table at $86:9CA5 gives, from unit id 0x19 on, the id each counts as in a talk check
  ($86:9C95): the children (0x32-0x3F) map to the 14 substitutes the scripts place when a child doesn't exist.
- **Not read yet:** your own army's placements (army 0; the page shows the home castle as the lord's start), and the named
  characters' items and holy blood. Gerald is the Level 20 Axe Fighter on Evans' castle tile, as Serenes lists (the
  dialogue leaves him Evans to hold).

## Events: `scripts/fe4_events.py`, used by `scripts/build-fe4-maps.py`

- **Chapter header:** `[chapter u16][opening script][event table]` (3-byte pointers), found by its self-reference.
- **Event table:** commands of the event interpreter ($86:83D8). First, pairs of `[condition][action]` up to `20 66 66`. A condition
  is `[opcode][flag][args]`; each opcode stands for a trigger kind the game raises with its values ($0EBC, then $0EBD-$0EC3; found at
  each `STA $0EBC`): 0x02 an army seizes a castle (army, location), 0x04 / 0x15 / 0x16 a talk (from, to; 0xFFFF anyone), 0x07 a unit
  enters a castle (unit, location), 0x0A a unit visits a village or castle, 0x0B a unit reaches an area (unit, x1 y1 x2 y2), 0x0C a
  unit stops within n tiles of another (unit, unit, n; both answer the raised kind 3, its check at $86:8A2F), 0x0D a battle between
  two units, 0x0F a unit is defeated. The flag byte: 0xFF none; below 0x80 the entry fires once and sets that flag;
  0x80 + n needs flag n. Once one entry fires the rest are skipped.
- **Blocks** after `20 66 66`: `21 turn phase a b` (0xFF any; the phase is an army's number) opens a block closed by `25 66 66`;
  `29 n` (flag set), `2A n` (clear), `2C ... FF` (all set), `2D ... FF` (any set) open one closed by `2E 66 66`; `27 n` sets a flag.
- **Actions:** `30 [flag] [u16 n]` runs scene n (3-byte pointers at $8F:E8BF, 562 scenes); `31` / `32` show text.
- **Scenes** run on their own interpreter ($91:A5E2, handlers at $91:A50A). `FD` ends a step, `FFFF` the scene; 0x01 ends, 0x02
  jumps, 0x03-0x06 jump conditionally, 0x4B sets a flag of the chapter (`4B [chapter] [flag]`: `4B 00 16` in the Prologue). Scene opcodes 0x4A and 0x4D run one event command inline:
  `4A nn` loads unit list nn, `49 id` puts a unit on the map, `53 id army` moves a unit to an army (army 0: it joins you),
  `57` / `58 [unit] [instance]` hands over an item. Command lengths come from running each handler on `scripts/fe4_cpu.py`
  (calls into other banks stepped over, the four move slots at $7E:17C4 read as free); the walk follows jumps. Every scene the
  tables use walks to its end. Two event commands step past fewer bytes in their skip entry than when run (0x34; 0x5F when its
  fifth operand byte is 0x0B), which the walker corrects.
- **Item instances:** the game tracks every physical item; scripts hand out instance numbers, counted from 1, whose item type is
  the byte at 0x3F489 + n - 1 (140 of them). Checked against Serenes' item-locations page: the Prologue's village gives the Speed
  Ring, Chapter 2's the Bargain Ring and Armour Cutter (the patch's Bargain Bracelet and Ironbane Sword).
- **Locations:** each chapter's data (3-byte pointers at $86:C760) leads to its castles and villages: `[id][name][kind][x][y]`, kind
  0 a castle (on the castle tile; location 0 is your home castle), 2 a village. A village holds 5000 gold (the per-kind record at
  $87:F453, which also gives the village's footprint, x - 1 to x + 1 and the row above, and the entrance: its own tile).
- **What the page says:** each later group's arrival (the block or trigger whose scene loads it, its flags traced back to what sets
  them: a seize, a talk, a defeat, another group's arrival, a unit reaching an area, whose rectangle is drawn), a phase named by how
  its army stands at that point; the castle whose seizing runs the chapter's ending scene (event command 0x78) as the win, and any
  other scene that ends the chapter ("The chapter also ends after Sigurd talks to Ida"); castles, villages and their items; hidden
  finds (area triggers that hand over an item); talks that give items or recruit; who joins and when (`49` in turn blocks, `53` on
  a block or trigger). Units of an army hostile to yours are a group; friendly ones arrive green, neutral ones yellow (they neither
  fight you nor help you), and each unit says when its army turns (a `4D` for it in a later event of the same creation of the army).
- **A scene that ends the chapter** (0x78) only stages its scene: the units it loads or places are its cast, no group on the map,
  and the flags it sets cause nothing on the battle map. A unit a scene places and removes again (0x65) is a cast too (Chapter 8's
  Julius).
- **Talks:** a talk that does something is on the unit talked to (and on the talker when it's someone else's unit): who joins, for
  how much gold (Beowolf's scene takes 10,000 from the talker with `55 FFFF 2710`), what's handed over, an army that turns (`4D`),
  who leaves the map, the chapter ending. 0x15 takes the talker's child or substitute as one ($86:8828), 0x16 both sides
  ($86:8876). A talk between two of your own units stays a note.
- **Departures:** event commands 0x65 and 0x66 take a unit off the map (its own defeat, a scene's cast and an ending aside: a
  block's reaches only the units on the map by then, a trigger's any); trigger 0x1A (A fights B: kind 0x18, raised as a battle
  starts at $84:B981) running command 0x74 withdraws A ("Withdraws after a battle").
- **Lose conditions** (the lord defeated, or the home castle seized): the code has both. A player unit the game marks as the lord
  ($84:A358 = 1) dying ends the game ($81:B0A0-B0AC, reason 0: scenes 0x22E/0x230), and so does army 0 losing its castle
  ($84:BCEC-BCF3, reason 1: scenes 0x22F/0x231).
- A trigger's action can set a flag itself (`27 n`): Chapter 5's ambush waits on Sigurd talking to Ida.
- **`4F [list] [n] [id u16] [id u16]`** loads and places a list, swapping the first unit id for the second when the game's check on n
  holds: Chapter 8's list 40 (Asaello, or Febail) on turn 3 and the refugees' list 39 (Hawk, or Ced). The child is drawn, the
  substitute (the list's own record) their stand-in.
- **Where units are put:** scene op 0x24 walks a unit `[unit u16][mode][x1][y1][x2][y2]...`, mode 1 walking it onto the map from
  off it (Chapter 8's Ishtar on turn 5, one of the army whose phase she comes in); the inline event command 0x50 sets its
  tile `[unit u16][FF][x][y]` ((0, 0): none given); a unit in a list loaded with the scene on your side (army 0) stands where its
  record says. Joiners are the playable units a block's scene puts on the map (event command 0x49), walking in from where 0x24
  starts them; the starting units are those the opening places (the rest start in the home castle). A child and the substitute the
  game places when the child wasn't born share a tile: the child is drawn, the substitute is their stand-in (the map's stand-in
  toggle), and their items are one line ("Carried by Larcei or Creidne on joining"). The second generation's openings also move
  Sigurd's id, which is left out from Chapter 6 on.
- **Not read yet:** the arena.

## True hit

One roll, read in the game's code: the hit routine ($84:E564) takes the attacker's accuracy less the defender's avoid, clamps it to
0-100 and calls $84:EF9C once, which draws one number 0-99 from the random table ($80:A73A) and hits when it's lower. Skill activations
use the same roll. So the displayed hit is the true hit (`hitSystem: '1rn'`), with two exceptions the page names (`hitNote`): a
defender's Miracle at 10 HP or less adds 10 x (11 - HP) avoid in the roll ($84:E575-E5B2) but not to the displayed hit ($84:DA53),
and a Luna or Sol activation skips the roll and hits ($84:E564).

## Weapon triangle and leadership: `scripts/build-fe4-bonuses.py` -> `src/data/fe4/fe4Bonuses.ts`

The game has no support levels, so it has no Supports tab (the user's call: what stands in for them belongs to a unit, so the Unit
Planner). The weapon triangle tab shows the triangle and leadership. All of it is read from the battle code (addresses in the script):
units of the same army within 3 tiles give +10 hit and avoid for each one with Charisma (skill 0x0C: Lachesis, its only holder in
Serenes' base-stats page, has that bit alone at +0x1C of her record), +10 for a lover, and the commander's leadership by stars
(0, 0, 10, 20, 30, 40). The bonus loop skips only units of an army hostile to the commander's ($84:DB9F, through $84:C15F), so
allied and neutral armies' units in reach count, and every army's commander (unit flag 0x100, $84:D990) gets their own. The weapon triangle gives the advantaged side +20 hit and avoid. Accuracy itself is
weapon Hit + 2 x Skl; avoid is terrain + Luck + 2 x attack speed ($84:FD00, $84:FD4C). Not read yet: the critical bonuses Serenes
lists for an adjacent lover or sibling (+20 crit).

## Where items turn up: `src/data/fe4/fe4ItemSources.ts` (from `scripts/build-fe4-maps.py`)

Each item's sources by chapter, for the weapon page and the spoiler block (a weapon is listed from the first chapter it turns up in):
- **Shop:** the home castle's location record ends in a pointer to its stock, item instances up to 0xFF (`shop_stock`). Checked
  against every "Vendor" entry on Serenes' item-locations page. Chapters 0, 5 and 11 have none.
- **Drops and what foes carry:** a foe's record holds two carried item *types* and one dropped item *instance*: at +10 in a
  generic record (kind 3), at +0x23 in a named one (kind 2). Every drop matches Serenes' list (Philip's Return Ring, Jacoban's
  Thunder Sword, Hilda's Bolganone, Ishtar's Life Ring...). Every unit of an army hostile to yours counts, generic or named, and so
  does one of an allied or neutral army that later turns on yours (it can be fought then). A foe standing on the map at the start
  counts in its chapter, one that arrives mid-chapter from the next (`drop-later`, `foe-later`). A unit the scripts take off the map
  on turn 1 that none of your starting tiles is within the longest move (+0x10 of a class record) plus 2 of gives nothing: the
  Prologue's Gandolf leaves on its enemy phase about 40 tiles away, so his Skill Ring is his Chapter 1 drop.
- **Foe-only:** the player only ever owns one of the 140 instances; a foe holds types, and Steal takes only gold ($84:EAD9). So a
  weapon type no instance has never reaches you: Gungnir, Helswath, Valflame, Meteor, Mjölnir, Bolting, Blizzard, Jörmungandr,
  Fenrir, Hel and Loptous (`fe4Listed.ts` marks them). What a foe carries is only said for these (`foe`, `foe-later`).
- **Visits, castles, hidden finds:** the scenes behind the event triggers (`57` / `58` hand an instance to a unit), in their chapter.
- **Talks and events:** a talk's gift (`talk-later`), and one a block or an end scene hands over (`event-later`), count from the next
  chapter, the last chapter's in it. Blocks give three: Chapter 2's Knight Ring at its end (behind flags whose 0x46 checks aren't
  put into words), Chapter 9's Berserk Staff once Galatia is seized and Charlot has spoken to Hannibal (trigger 0x0C: Charlot
  stops next to him), Chapter 10's Heal Bracelet. A gift behind a flag test (scene op 0x08 [chapter][flag], then 0x03 jumping when
  it's set or 0x04 when it's clear) says the condition: Julia's Aura before Isaach is seized, her Nosferatu after (scene 0x1EA).
- **Kit:** what a playable unit carries when it joins (event command `49` or `53 ... 00`, or a list's record on your side, Arden's
  in the Prologue): item instances at +0x23 in a kind 0 record, +9 in a child's (kind 1), counted once, in the first chapter it
  joins. Those the opening places count there; a recruit a trigger or block brings, from the next chapter (`kit-later`).
  Inherited items aren't modelled: a child's own record is used.
- Not read: the arena's prizes, and whether the pawn shop or inheritance adds sources.
