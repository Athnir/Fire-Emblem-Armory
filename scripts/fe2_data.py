"""
Fire Emblem Gaiden's (FE2) tables, read from the user's cartridge image (scripts/fe2_rom.py), and the names the app gives them.

Every table is in data-raw/fe2/README.md with its address (bank:$addr, bank 15 fixed at $C000-$FFFF). The ROM has the English fan
translation patched in (the user's call: no clean Japanese ROM is to hand); its menus squeeze names into four or five tiles, so the app
goes by Shadows of Valentia's official names where the remake has the person, class or item (each item by the Japanese name it shares
with Echoes' own item ids, IID_<name>), else the translation's spelling.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe2_rom import FIXED, Rom  # noqa: E402

R = Rom()

# --- Items (bank 15, parallel arrays by item number) ---
ITEMS = 59
WEAPON_ITEMS = 48            # 0-47 have the Wt, Hit, Crit, effectiveness and personal bytes
ITEM_NAMES, ITEM_MT, ITEM_OWN, ITEM_WT, ITEM_HIT, ITEM_CRIT = 0xDCAD, 0xD9B9, 0xD9F4, 0xDA24, 0xDA54, 0xDA84
ITEM_EFF, EFF_LISTS, ITEM_RANGE, ITEM_SPECIAL = 0xDAB4, 0xDAE4, 0xDAFD, 0xDB38
SHIELDS, SHIELD_DEF = 0xF538, 0xF53D
WEAPON_BOUNDS, WEAPON_LISTS = 0xF50C, 0xF512
# The Japanese name each item shares with Shadows of Valentia's (Echoes' IID_<name>) and the remake's English for it; Serenes Forest's
# Gaiden tables give the Japanese. The remake keeps the names but not always the kind: its Astra is a sword and its Luna a bow.
ITEM_SOV = {
    2: ('鋼の槍', 'Steel Lance'), 3: ('銀の槍', 'Silver Lance'), 4: ('手やり', 'Javelin'), 5: ('聖なる槍', 'Blessed Lance'),
    6: ('ナイトキラー', 'Ridersbane'), 7: ('グラディウス', 'Gradivus'), 8: ('流星', 'Astra'), 9: ('太陽', 'Sol'), 10: ('月光', 'Luna'),
    11: ('鋼の剣', 'Steel Sword'), 12: ('銀の剣', 'Silver Sword'), 13: ('勇者の剣', 'Brave Sword'), 14: ('暗黒の剣', 'Shadow Sword'),
    15: ('いかづちの剣', 'Lightning Sword'), 16: ('聖なる剣', 'Blessed Sword'), 17: ('ファルシオン', 'Falchion'),
    18: ('王家の剣', 'Royal Sword'), 19: ('触手', 'Tentacle'), 20: ('鋼の弓', 'Steel Bow'), 21: ('聖なる弓', 'Blessed Bow'),
    22: ('銀の弓', 'Silver Bow'), 48: ('革の盾', 'Leather Shield'), 49: ('鋼の盾', 'Steel Shield'), 50: ('銀の盾', 'Silver Shield'),
    51: ('聖なる盾', 'Blessed Shield'), 52: ('魔封じの盾', 'Hexlock Shield'), 53: ('竜の盾', 'Dracoshield'), 54: ('聖なる指輪', 'Blessed Ring'),
    55: ('天使の指輪', 'Angel Ring'), 56: ('速さの指輪', 'Speed Ring'), 57: ('魔道の指輪', 'Mage Ring'), 58: ('祈りの指輪', 'Prayer Ring'),
}
# The spells (23-46) are learned by level, never held; their names are the remake's where it has them, else the translation's.
SPELL_SOV = {23: 'Fire', 24: 'Thunder', 25: 'Blizzard', 26: 'Excalibur', 27: 'Aura', 28: 'Seraphim', 29: 'Nosferatu', 30: 'Ragnarok',
             31: 'Miasma', 32: 'Swarm', 33: 'Death', 34: 'Medusa', 35: 'Recover', 36: 'Restore', 37: 'Invoke', 38: 'Eye Beam',
             39: 'Eyeball', 40: 'Recover', 41: 'Physic', 42: 'Nosferatu', 43: 'Warp', 44: 'Restore', 45: 'Illusion', 46: 'Rescue'}


def item_menu_name(i, full=True):
    """The translation's menu name (four or five tiles and the kind's icon word); `full` steps back a byte where the patch's pointer
    starts a letter in (the Hand Lance's "and", Libro's "ibro")."""
    p = R.u16(FIXED, ITEM_NAMES + 2 * i)
    if full and R.u8(FIXED, p - 1) != 0xEF and 0x45 <= R.u8(FIXED, p - 1) <= 0x83:
        p -= 1
    return R.string(FIXED, p, icons=True).strip()


def item_name(i):
    return ITEM_SOV[i][1] if i in ITEM_SOV else item_menu_name(i)


def effective_classes(index):
    """The classes an effectiveness index (15:$DAB4) covers: a list ended by $FF (u16 pointers at 15:$DAE4)."""
    if not index:
        return []
    p, out = R.u16(FIXED, EFF_LISTS + 2 * index), []
    while (c := R.u8(FIXED, p)) != 0xFF:
        out.append(c)
        p += 1
    return out


def items():
    shields = list(R.read(FIXED, SHIELDS, 5))
    shield_def = list(R.read(FIXED, SHIELD_DEF, 5))
    out = []
    for i in range(ITEMS):
        e = {'id': i, 'name': item_name(i), 'menu': item_menu_name(i), 'mt': R.u8(FIXED, ITEM_MT + i), 'range': R.u8(FIXED, ITEM_RANGE + i),
             'special': R.u8(FIXED, ITEM_SPECIAL + i)}
        if i < WEAPON_ITEMS:
            e.update(own=R.u8(FIXED, ITEM_OWN + i), wt=R.u8(FIXED, ITEM_WT + i), hit=R.u8(FIXED, ITEM_HIT + i),
                     crit=R.u8(FIXED, ITEM_CRIT + i), eff=effective_classes(R.u8(FIXED, ITEM_EFF + i)))
        if i in shields:
            e['shield_def'] = shield_def[shields.index(i)]
        out.append(e)
    return out


def weapon_users():
    """[(first item, last item, classes)] (15:$F4AD): items below the first bound anyone uses; each next range has its class list."""
    bounds = list(R.read(FIXED, WEAPON_BOUNDS, 6))
    out = []
    for k in range(5):
        p, cls = R.u16(FIXED, WEAPON_LISTS + 2 * k), []
        while (c := R.u8(FIXED, p)) != 0xEF:
            cls.append(c)
            p += 1
        out.append((bounds[k], bounds[k + 1] - 1, cls))
    return out


# --- People and classes ---
CHAR_RECORDS = (8, 0x90E2)   # 12 bytes by character - 1: +0 its record's own number, +1 class, +2 level, +3 HP ... +11 item
FOE_NAMES, CLASS_NAMES, CLASS_FOE_NAMES = 0xDFBA, 0xDB73, 0xDC2E
# The remake's names for the playable characters (the Unit Planner's, checked there against Echoes' own).
SOV_NAMES = {1: 'Alm', 2: 'Celica', 3: 'Mycen', 4: 'Nomah', 5: 'Lukas', 6: 'Kliff', 7: 'Tobin', 8: 'Gray', 9: 'Clair', 10: 'Clive',
             11: 'Clive', 12: 'Forsyth', 13: 'Mae', 14: 'Silque', 15: 'Genny', 16: 'Boey', 17: 'Kamui', 18: 'Valbar', 19: 'Mathilda',
             20: 'Python', 21: 'Leon', 22: 'Atlas', 23: 'Jesse', 25: 'Sonya', 26: 'Deen', 27: 'Saber', 28: 'Luthier', 29: 'Delthea',
             30: 'Tatiana', 31: 'Catria', 32: 'Palla', 33: 'Est', 34: 'Zeke'}
# The foes' own numbers (a record's +0 & $7F, names at 15:$DFBA): the translation's names are four or five tiles and often garbled
# ("'r[0f]ti[0f]-" is Desaix, "Threi" Slayde); each named foe is matched by its battle, class, level and items to Serenes Forest's
# boss list and named as Fire Emblem Wiki names Gaiden's characters, by the remake. Deen, Sonya, Delthea and Zeke fight you first.
FOE_SOV = {1: 'Desaix', 2: 'Grieth', 3: 'Dolth', 4: 'Nuibaba', 5: 'Rudolf', 6: 'Jedah', 8: 'Deen', 9: 'Magnus', 10: 'Jerome',
           11: 'Zeke', 14: 'Marla', 15: 'Tatarrah', 16: 'Jamil', 17: 'Delthea', 18: 'Gazelle', 19: 'Slayde', 20: 'Mikhail',
           21: 'Lawson', 22: 'Barth', 23: 'Blake', 24: 'Shizas', 26: 'Wolff', 27: 'Desaix', 28: 'Zakson', 29: 'Sonya', 30: 'Garth',
           39: 'Duma', 40: 'Mueller', 41: 'Garcia', 42: 'Hestia', 43: 'Xaizor', 44: 'Gharn'}
# The foes named by their army or kind, not a person: generic foes (49-70 name classes, 71-88 monsters) go by their class.
FOE_PEOPLE = set(FOE_SOV)
# Classes (1-23 have bases; 24 is a name only), as the remake names them; a foe of a class Gaiden shares with a monster is that monster
# (Fire Emblem Wiki's Gaiden classes: a foe Priestess is a Revenant, a foe Mage an Arcanist...).
SOV_CLASSES = {1: 'Cavalier', 2: 'Knight', 3: 'Pegasus Knight', 4: 'Paladin', 5: 'Falcon Knight', 6: 'Soldier', 7: 'Gold Knight',
               8: 'Mercenary', 9: 'Myrmidon', 10: 'Dread Fighter', 11: 'Priestess', 12: 'Archer', 13: 'Sniper', 14: 'Villager',
               15: 'Mage', 16: 'Mage', 17: 'Saint', 18: 'Cleric', 19: 'Sage', 20: 'Bow Knight', 21: 'Fighter', 22: 'Baron',
               23: 'Hero', 24: 'Princess'}
FOE_CLASSES = {**SOV_CLASSES, 3: 'Gargoyle', 5: 'Necrodragon', 11: 'Revenant', 14: 'Brigand', 15: 'Arcanist', 16: 'Witch',
               17: 'Bonewalker', 18: 'Mogall', 19: 'Cantor', 21: 'Fell God'}
FLIERS = (3, 5)              # Pegasus and Falcon Knights (as foes Gargoyles and Necrodragons): battle terrain code 13, no avoid


def character(ch):
    bank, base = CHAR_RECORDS
    return R.read(bank, base + 12 * (ch - 1), 12)


def foe_menu_name(foe):
    p = R.u16(FIXED, FOE_NAMES + 2 * ((foe & 0x7F) - 1))
    return R.string(FIXED, p).strip() if 0xC000 <= p < 0xFF00 else None


def foe_name(rec):
    """A foe record's name: the person where it's one, else its class."""
    n = rec[0] & 0x7F
    return FOE_SOV.get(n) or FOE_CLASSES.get(rec[1], f'class {rec[1]}')


def is_person(rec):
    return (rec[0] & 0x7F) in FOE_PEOPLE


# --- Terrain (15:$E8DE your units' tile -> code, 15:$E9DE the foes', 15:$ECEE avoid, 15:$EADE costs by class - 1) ---
TERRAIN_CODES = 22


def tile_codes(foes=False):
    return list(R.read(FIXED, 0xE9DE if foes else 0xE8DE, 256))


def terrain_avoid():
    return list(R.read(FIXED, 0xECEE, TERRAIN_CODES))


def move_costs(cls):
    return list(R.read(FIXED, R.u16(FIXED, 0xEADE + 2 * (cls - 1)), TERRAIN_CODES))


# --- Battle maps (2:$8000 u16 pointers by map: 1-48 the world map's battle nodes, 49-80 the dungeons' and towns' fields) ---
def battle_map(n):
    """(rows, columns, grid) of map n, the grid's outer ring included (no unit can enter it, 6:$9708)."""
    p = R.u16(2, 0x8000 + 2 * n)
    rows_m1, cols_m1 = R.read(2, p, 2)
    o, tiles = R.off(2, p) + 4, []
    while (x := R.prg[o]) != 0xFF:
        if x < 0x2E:
            tiles += [R.prg[o + 1]] * x
            o += 2
        else:
            tiles.append(x)
            o += 1
    rows, cols = rows_m1 + 1, cols_m1 + 1
    assert len(tiles) == rows * cols, (n, len(tiles), rows, cols)
    return rows, cols, [tiles[r * cols:(r + 1) * cols] for r in range(rows)]


def deploy_lists(n):
    """Map n's four tile lists (8:$AB11 u16 by map - 1 -> four u16 pointers -> [count][column, row]...; lists may share bytes):
    Alm's army stands on lists 0 (then 1) and its foes on 2 / 3; Celica's army on 2 / 3 and its foes on 0 / 1 (8:$9E33)."""
    p, out = R.u16(8, 0xAB11 + 2 * (n - 1)), []
    for k in range(4):
        q = R.u16(8, p + 2 * k)
        out.append([tuple(R.read(8, q + 1 + 2 * j, 2)) for j in range(R.u8(8, q))])
    return out


# --- Foe armies ---
COMPOSITIONS, TEMPLATES = 0x93C2, 0x9A5A
N_COMPOSITIONS = (0x9474 - COMPOSITIONS) // 2
MOVE_CHANCE = 0x9241


def template(i):
    return bytes(R.read(8, R.u16(8, TEMPLATES + 2 * i), 6))


def composition(c):
    """Composition c's foes, as 6-byte records [person | $80][class][level][item][flags][spells]: [count] then entries, an entry below
    $80 a template's index (8:$9A5A), else an inline record. The placement loop stops at 20 (8:$A26A; composition 66 claims 62)."""
    p = R.u16(8, COMPOSITIONS + 2 * c)
    n, q, out = R.u8(8, p), p + 1, []
    for _ in range(min(n, 20)):
        b = R.u8(8, q)
        if b >= 0x80:
            out.append(bytes(R.read(8, q, 6)))
            q += 6
        else:
            out.append(template(b))
            q += 1
    return out


def chapter_groups(ch):
    """[(composition, node)] placed as chapter ch starts (8:$9EBB: 8:$9291 / 8:$9299, u16 by chapter 1-4; chapter 5 reuses 4's)."""
    ch = min(ch, 4)
    comps, p = [], R.u16(8, 0x9291 + 2 * (ch - 1))
    while (c := R.u8(8, p)) != 0xFF:
        comps.append(c)
        p += 1
    nodes = list(R.read(8, R.u16(8, 0x9299 + 2 * (ch - 1)), len(comps)))
    return list(zip(comps, nodes))


def random_groups(ch):
    """The chapter's random group (8:$9D38): one of five [composition, node] at 8:$92F7 + 8 * r + 2 * (chapter - 1); node 0 none."""
    return [tuple(R.read(8, 0x92F7 + 8 * r + 2 * (min(ch, 4) - 1), 2)) for r in range(5)]


def spawn_points():
    """The nine monster spawn points (8:$9F0A): [town node (15:$F11B), world node (15:$F124), [(composition, chance %) by level]]:
    level L reads the pair at 8:$931F[x] + 2 * (L - 1) (lists share bytes; the death events set the levels)."""
    towns, nodes = list(R.read(FIXED, 0xF11B, 9)), list(R.read(FIXED, 0xF124, 9))
    out = []
    for x in range(9):
        p = R.u16(8, 0x931F + 2 * x)
        out.append((towns[x], nodes[x], [tuple(R.read(8, p + 2 * k, 2)) for k in range(8)]))
    return out


def dungeon_encounters():
    """[(composition, second composition or None, map)] for encounters 0-31 (8:$935B, map 8:$939B); a composition with bit 7 is
    picked at random from 8:$93BB's list."""
    out = []
    for e in range(32):
        a, b = R.read(8, 0x935B + 2 * e, 2)
        out.append((a, None if b == 0xFF else b, R.u8(8, 0x939B + e)))
    return out


def random_encounter_list():
    p = R.u16(8, 0x93BB)
    return list(R.read(8, p + 1, R.u8(8, p)))


# --- The world map ---
N_NODES = 81


def node_name(n):
    return R.string(11, R.u16(11, 0xB821 + 2 * (n - 1)))


def adjacent(n):
    out, p = [], R.u16(FIXED, 0xEF94 + 2 * (n - 1))
    while (b := R.u8(FIXED, p)) < 0x80:
        out.append(b)
        p += 1
    return out


def entry_room(node):
    return R.u8(13, 0xB98C + node - 49)


# --- Rooms (towns and dungeons): objects 13:$BD70, stairs 13:$BA50, exits 10:$BD8F ---
def room_objects(room):
    """[(x, y, kind, value)]: kind 0 a chest (value: the item), 1 a spring, 2 a sign; rooms 1-50 have a list."""
    if room > (R.u16(13, 0xBD70) - 0xBD70) // 2:
        return []
    p, out = R.u16(13, 0xBD70 + 2 * (room - 1)), []
    while R.u8(13, p) != 0xEF:
        out.append(tuple(R.read(13, p, 4)))
        p += 4
    return out


def room_stairs(room):
    if room > (R.u16(13, 0xBA50) - 0xBA50) // 2:
        return []
    p, out = R.u16(13, 0xBA50 + 2 * (room - 1)), []
    while R.u8(13, p) != 0xEF:
        out.append(tuple(R.read(13, p, 5)))
        p += 5
    return out


def room_exits(room):
    """The room's four edges (10:$BD8F): 0 none, 1-49 the world-map node it leads out to, 50+ room value - 50."""
    return list(R.read(10, 0xBD8F + 4 * (room - 1), 4))


def rooms_from_nodes():
    """{room: {world-map node: rooms walked from its entry room}}: from each town or dungeon node's entry room, over its stairs and
    edges (some rooms are reached from several places: Rigel's dungeons share theirs)."""
    reach = {}
    for node in range(49, N_NODES + 1):
        r0 = entry_room(node)
        dist, q = {r0: 0}, deque([r0])
        while q:
            r = q.popleft()
            reach.setdefault(r, {})[node] = dist[r]
            for t in [s[2] for s in room_stairs(r)] + [v - 50 for v in room_exits(r) if v >= 50]:
                if t not in dist and 0 < t < 128:
                    dist[t] = dist[r] + 1
                    q.append(t)
    return reach


def nearest_nodes(reach_of_room):
    """The world nodes a room is nearest to (its place), from rooms_from_nodes()'s entry."""
    if not reach_of_room:
        return []
    best = min(reach_of_room.values())
    return sorted(n for n, d in reach_of_room.items() if d == best)


def room_encounters():
    """Encounters started on entering a room (13:$BA01: [room][encounter | flags][bit]) and on stepping on its tiles (13:$8FF9)."""
    on_entry, p = [], 0xBA01
    while R.u8(13, p) != 0xEF:
        room, enc, bit = R.read(13, p, 3)
        on_entry.append((room, enc & 0x7F, bit))
        p += 3
    on_step, p = [], 0x8FF9
    while R.u8(13, p) != 0xEF:
        on_step.append((R.u8(13, p), R.u8(13, p + 1)))
        p += 2
    return on_entry, on_step


# --- Other item sources ---
def random_drops():
    """[(foe, chance %, item)] (15:$F225): a foe holding nothing may drop the item, two rolls both under the chance, in chapters 1-4
    while the chapter's count of such drops is under 15:$F23E's."""
    out, p = [], 0xF225
    while R.u8(FIXED, p) != 0xFF:
        out.append(tuple(R.read(FIXED, p, 3)))
        p += 3
    return out, list(R.read(FIXED, 0xF23E, 4))


def guests():
    """[(battle node, [guests])] (15:$F150, 15:$F16B -> lists at 15:$F178): playable characters fighting on your side there."""
    out, x = [], 0
    while (node := R.u8(FIXED, 0xF150 + x)) != 0xFF:
        k, people = R.u8(FIXED, 0xF16B + x), []
        if k:
            q = R.u16(FIXED, 0xF178 + 2 * (k - 1))
            while R.u8(FIXED, q) != 0xFF:
                people.append(R.u8(FIXED, q))
                q += 2
        out.append((node, people))
        x += 1
    return out


def death_events():
    """[(foe, kind, value)] (15:$F18D): kind 0 a spawn point's level or a pending spawn, 1 a town's flag event, 2 the listed foe
    leaves the battle (15:$F20C), 3 a march (8:$A484)."""
    out, p = [], 0xF18D
    while R.u8(FIXED, p) != 0xFF:
        out.append(tuple(R.read(FIXED, p, 3)))
        p += 3
    return out


if __name__ == '__main__':
    for e in items():
        print(e['id'], e['name'], '|', e['menu'], {k: e[k] for k in ('mt', 'wt', 'hit', 'crit', 'range', 'special') if k in e})
