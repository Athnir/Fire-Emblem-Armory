# Fire Emblem Gaiden (FE2): data formats

Read from the user's cartridge image, `Documents\FE Games\Fire Emblem Gaiden.nes` (iNES, mapper 10 MMC4, 16 PRG banks of 16 KB, 128 KB
CHR), which has an English fan translation patched in: no clean Japanese ROM is to hand, so the data is read from it (the user's call).
The patch changes text and its pointers and leaves the tables alone: every weapon's numbers match Serenes Forest's Gaiden tables but
three (below), checked in `src/logic/__tests__/fe2.test.ts`. Nothing is written to the ROM; nothing read from it is committed but the
data the scripts derive.

Addresses are bank:$addr, bank 15 fixed at $C000-$FFFF. A far call is `lda #bank / sta $4A (function) / jsr $CA94`.

Scripts: `scripts/fe2_rom.py` (the Unit Planner's reader: banks and the patch's text), `scripts/fe2_data.py` (every table below),
`scripts/build-fe2-items.py` (weapons, shields, rings), `scripts/build-fe2-maps.py` (terrain, battles, item sources).

## Names

The patch's menus squeeze names into four or five tiles ("Her" Sword, "Knight" for the Knight Killer) and garble some ("'r[0f]ti[0f]-"
is Desaix), so the app goes by Shadows of Valentia's official names where the remake has the person, class or item (the user's call):
- Items by the Japanese name each shares with Echoes' own item ids (`IID_<name>` in its Data/Item.bin, the names from its English
  text), Serenes Forest giving Gaiden's Japanese: 流星, 太陽 and 月光 (the "Star", "Sun" and "Moon" lances) are the remake's Astra, Sol
  and Luna (a sword and a bow there), 暗黒の剣 the Shadow Sword, いかづちの剣 the Lightning Sword, ナイトキラー Ridersbane, 手やり the
  Javelin, the せいなる items Blessed, 竜の盾 the Dracoshield, 魔封じの盾 the Hexlock Shield.
- Playable characters as the Unit Planner names them. Named foes (their own numbers, the record's +0 & $7F, names at 15:$DFBA) are
  matched by battle, class, level and items to Serenes Forest's boss list and named as Fire Emblem Wiki's Gaiden pages name them.
- Classes as Fire Emblem Wiki's Gaiden classes: a foe of a class Gaiden shares with a monster is that monster (a foe Pegasus Knight is
  a Gargoyle, Falcon Knight a Necrodragon, Priestess a Revenant, Mage an Arcanist, Saint a Bonewalker, Cleric a Mogall, Sage a Cantor,
  Fighter the Fell God, Villager a Brigand); a generic foe goes by its class.
- Places keep the translation's names, spaces put back ("Ram Vall", "Theif Woods"): they're what the game shows. Spells too ("Dora",
  "Excaliber"): Echoes keeps its spells outside its item and skill tables, so no Japanese id matches them.

## Items (bank 15, parallel arrays by item number 0-58)

| Field | Address | Read by |
|---|---|---|
| name | 15:$DCAD (u16) | the menus |
| Mt | 15:$D9B9 | 9:$8270 (damage) |
| personal byte (bit 7: the character in the low bits alone) | 15:$D9F4 | 15:$F498 |
| Wt | 15:$DA24 | 9:$8241 (attack speed = Spd - Wt) |
| Hit | 15:$DA54 | 9:$81BC |
| Crit | 15:$DA84 | 9:$83EA |
| effectiveness index -> class list ($FF ends) | 15:$DAB4 -> 15:$DAE4 | 9:$8298 |
| range bits (0x02 beside, 0x04 two tiles, 0x20 any distance) | 15:$DAFD | 6:$A65D |
| special (10: heals its holder 5 HP each turn) | 15:$DB38 | 3:$9185, 9:$8949 |
| shields and their Def | 15:$F538 / 15:$F53D | 9:$83A7 |

Items 2-10 are lances, 11-19 swords (19 the Tentacle), 20-22 bows, 23-46 spells (learned by level, never held: not listed), 48-53
shields, 54-58 rings; 0 is the unarmed strike and 1 a bow class's own bow. No uses, prices or ranks. Who may use (15:$F4AD): below
15:$F50C's first bound anyone; each range its class list at 15:$F512 (lances: classes 1-7 and 22, a Soldier not the Javelin or the
Gradivus, 15:$F46F; swords: 8, 9, 10, 11, 21, 14; bows: 13, 12, 20 and 21, Alm with the Hero flag $744A).

Rules read in the code: the effective lists (Blessed weapons: classes 3, 5, 11, 17, 18, the monsters' and, against your units, the
Priestesses', Pegasus and Falcon Knights', Saints' and Clerics'; bows: 3 and 5; Ridersbane: 1, 4, 7), Mt x3 on an effective strike
(9:$825E: Str + 3 x Mt); the Luna (item 10) held makes its holder's weapon hit 100 (9:$8207); the Shadow Sword in your units' hands, not
a Dread Fighter's, beside the foe: once its first strike hits, a roll at or below 20 - Lck turns it on the wielder for Str + 13 - its
own Def (9:$8564); the Lightning Sword deals 15 less the foe's Res, no Str (9:$826C); the Falchion's wielder strikes back in a battle
with Eyeball (9:$8A63); the Blessed Shield's Def +13 only against monsters, the Dracoshield's +13 Def and +13 Res, the Hexlock
Shield's spell hit 10; the Angel Ring's Lck 40 in battle (and doubled level-up gains), the Speed Ring's Spd 40 and Mov +5 (6:$BB22),
the Mage Ring's spell range 5, the Prayer Ring's crit 100 at half HP.

Serenes Forest differs in three places, and the game wins: the Falchion's Hit is 100 in the table (Serenes: 80); the Lightning Sword
deals 15 less Res (Serenes: always 15); the Tentacle (item 19) is Mt 12, Hit 80, beside the foe only (Serenes: 10, 90, 1-8). The
Tentacle is no one's item: Duma's battle setup picks it (9:$8CC8: at 52 HP or more the Tentacle, 178 in 256, or Eye Beam; below 52,
Eyeball). The Gradivus heals its holder too (special 10), which Serenes leaves out.

## Battle (bank 9; the battle block $0304 + 2 x field + side)

- Hit (9:$81B0): Skl + weapon Hit - (the target's terrain avoid + its attack speed), held 0-100; spells (9:$8219): spell Hit - (Spd +
  Lck). The roll (9:$84E2 -> 9:$85CC): r = (100 x a random byte) >> 8 (the multiply at 15:$C6C9), a hit when r < hit (9:$8506);
  crit when r <= crit. A displayed h lands ceil(2.56 h) times in 256 (`byteBelowTrueHit` in src/logic/trueHit.ts).
- Damage (9:$825E): Str + Mt - Def (+ shield), x3 on a crit, held at 60 (a crit at 120); a Falcon Knight of yours against classes 5,
  11, 3, 18, 17 deals 3 x Str and its weapon's Mt isn't added (9:$8336). Crit (9:$83D8): ((Skl + Lck) / 2 + weapon Crit) / 2; foes crit
  only in classes 10, 8, 9 and 3.
- No weapon triangle and no supports (the triangle attack and Alm and Celica's special attack are a unit's).

## Battle maps (2:$8000, u16 pointers by map: 1-48 the world map's battle nodes, 49-80 the towns' and dungeons' fields)

- [last row][last column][2 unused] then RLE: a byte below $2E is a count followed by the tile, any other one tile; $FF ends. The outer
  ring can't be entered (6:$9708): the playable grid is the rest.
- Terrain: a tile's code 15:$E8DE (your units) / 15:$E9DE (the foes': the same but for unit markers and tile $E7, a mountain to you and
  castle wall to them). Avoid 15:$ECEE by code; movement costs u16 at 15:$EADE by class - 1 (classes 1-22; 255 no entry). Codes: 0 plain,
  1 forest (40), 2 sand, 3 shallows, 4 mountain (30), 5 peak, 6 floor, 7 water, 8 castle floor (20), 9 wall, 10 pillar (30), 11 stairs,
  12 castle top, 13 doors and gates (no one enters), 15 fort (40), 16 swamp, 17 grave (60), 18-20 floor; fliers (classes 3 and 5)
  fight on code 13 (no avoid, 6:$ABAD).
- The turn's start (3:$90F0): a unit on tile $DA (every code-15 tile) recovers 5 HP (3:$9114); on code 16 it loses 5, never below 1
  (3:$9143), unless it's a Pegasus or Falcon Knight or a foe Revenant, Bonewalker, Mogall or Duma; a unit holding an item of special 10
  recovers 5 (3:$9185).
- Tiles (8:$AB11, u16 by map - 1 -> four u16 pointers -> [count][column, row]...): Alm's army stands on list 0 (then 1), its foes on
  2 / 3; Celica's army on 2 / 3, its foes on 0 / 1 (8:$9E33). Foe group 0 takes list A, group 1 list B; a lone group overflows from A
  into B.

## Armies (bank 8)

- Records (8:$A2FF): [person | $80][class][level][item][flags][spells]; generic foes are templates (8:$9A5A, u16 pointers).
  Compositions (8:$93C2, u16 pointers): [count] then entries, below $80 a template's index, else an inline record; at most 20 placed
  (8:$A26A). A caster's spells: its +10 bits over its class's foes' list (15:$E1C9, by class order 15:$F459).
- The chapters' armies (8:$9EBB): compositions 8:$9291 and nodes 8:$9299, u16 by chapter 1-4 (chapter 5 reuses 4's). Plus one random
  army (8:$9D38): 8:$92F7 + 8 x rand(5) + 2 x (chapter - 1) = [composition, node] (Chapter 2's is always composition 8 at node 8).
- The world map: 81 nodes, names 11:$B821, neighbours 15:$EF94 (u16 by node - 1, ended by bit 7); a town or dungeon node (49+) enters
  room 13:$B98C[node - 49]. Which army fights where is the story's: Chapter 1 Alm's, 2 Celica's, and in 3 and 4 each its own half (the
  chapters' tables and the towns each army reaches, the Unit Planner's joins).
- Death events (15:$F18D, [foe][kind][value]): kind 0 sets a spawn point's level ($6D93[v >> 3] = v & 7) or a pending army ($6D2C:
  Desaix's death sends composition 32, Tatarrah's, to node 32); 1 a town's flag event; 2 takes a foe off the battle (list v at 15:$F20C:
  Slayde and Desaix each when the other falls, Barth's Brigands with him, Delthea when Tatarrah falls, Jedah when Mogall #87 does); 3 a
  march (8:$A484).
- Monster spawn points (8:$9F0A): nine, each with a town node (15:$F11B), a world node (15:$F124) and by level a [composition, chance %]
  (8:$931F[x] + 2 x (level - 1)); said on the world node's map.
- Guests (15:$F150 / 15:$F16B -> 15:$F178): playable characters on your side at a battle node.
- Drops: a foe's held item always drops to the unit that beats it (6:$AA4B). A foe holding nothing may drop 15:$F225's item for its
  kind ([foe | $80][chance][item]): two rolls, both under the chance, in Chapters 1-4, while the chapter's count of such drops is below
  15:$F23E's (2, 4, 7, 10).

## Towns and dungeons (bank 13)

- Rooms: objects 13:$BD70 (u16 by room - 1, rooms 1-50: [x][y][kind][value], kind 0 a chest, value the item), stairs 13:$BA50, edges
  10:$BD8F. A room's place is the town or dungeon node whose entry room reaches it in the fewest steps.
- Encounters (8:$935B: [composition][second composition or $FF], field 8:$939B): started on entering a room (13:$BA01) or stepping on its
  tiles (13:$8FF9), once per visit; encounter 22 is the battle with Duma (both armies). Each is listed with its place, fought by the army
  whose side of the field its foes fit (Regal Castle's rooms leave the other army one or two tiles) and opening after the battle beside
  its place on the world map.
- No shops or gold: nothing sells or buys.

## Not confirmed

- Terrain names: the codes are named from a render of the battle tiles with stand-in colours (the palettes weren't traced).
- Rooms several places reach (Rigel's dungeons, the towers by Regal Castle and Doma's Swamp): a chest or encounter there is put at the
  nearest place; which place the game means (the Falchion's and the Gradivus's chests, said at the Dragon Tower) wants an in-game check.
- Encounters 5, 8, 12, 16 and 18 are in no room's table (13:$BA01, 13:$8FF9): left out; whether something else starts them is open.
- Encounter 0 (undead) is placed at the Liberation HQ by that rule.
- The Blessed Ring: nothing tests it but the turn's healing.
- A random drop's two rolls are taken as independent (the second reseeds from $36, 6:$AA91).
