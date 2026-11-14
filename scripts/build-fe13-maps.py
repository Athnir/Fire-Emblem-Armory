"""
Builds Fire Emblem Awakening's maps from the user's own dump (data-raw/fe13/romfs, from scripts/fe13_extract.py):
  src/data/fe13/fe13Terrain.ts      terrain stats and movement costs, from GameData's terrain tables
  src/data/fe13/fe13Maps.ts         every chapter's, paralogue's and DLC map's grid, units, reinforcements, joiners, talks, villages,
                                    chests, doors, event tiles and objectives
  src/data/fe13/fe13ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe13-maps.py

Formats are in data-raw/fe13/README.md. Coordinates: the files count from 0 at the top left and keep a one-tile border the cursor never
reaches (units arriving from off the map start on it); the playable map is the stored one without that border, and the app counts from
(1, 1) at the bottom left.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe13_code as C  # noqa: E402
import fe13_data as D  # noqa: E402
import fe13_events as E  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe13_bin import ROMFS  # noqa: E402
from terrain_codes import encode  # noqa: E402
import art_ground  # noqa: E402
import map_pieces  # noqa: E402

GAME, TITLE, SCRIPT = 'fe13', 'Awakening', 'build-fe13-maps.py'
DLC_ROOT = os.path.join(ROMFS, 'dlc')

# Terrain id -> builder letter (terrain_codes.py's 'fe13'), by how the game treats each: its stats and movement column.
# Kinds that work alike but the game names and draws apart keep their own codes (the user's call, as Echoes' by their terrain names):
# plain, waste and floor; a castle, wall or edifice (a fort's or castle's buildings: Regna Ferox's) a castle's, a mast a ship's; a
# ship's hull its side, a building (fliers cross it) a village's houses, bones as bones.
LETTER = {
    0: '#', 1: '.', 2: 'e', 3: 'f', 4: 's', 5: 's', 6: 'm', 7: 'C', 8: 'C', 9: 'C', 10: 'Z', 11: 'j', 12: '9', 13: '4', 14: 'b', 15: 'b',
    16: 'w', 17: 'a', 18: 'a', 19: 'F', 20: 'g', 21: '0', 22: 'v', 23: 'V', 24: '.', 25: 'v', 26: 'V', 27: '.', 28: '8', 29: '0',
    30: '#', 31: 'r', 32: 'l', 33: 'O', 34: 'S', 35: 'p', 36: 't', 37: 'l', 38: 'l', 39: 'l', 40: '0', 41: 'd', 42: 'd', 43: 'c',
    44: 'C', 45: 'X', 46: 'H', 47: 'M', 48: '#', 49: 'I', 50: 'Y', 51: '.', 52: '.', 53: 'C', 54: 'v', 55: '0', 56: '.', 57: 'C',
    58: 'a', 59: '.', 60: 'O', 61: 'f', 62: 'm', 63: 'b', 64: 'v', 65: 'V', 66: '.', 67: 'd', 68: 'b', 69: 'O', 70: 'a',
}
# What the panel calls each letter (the game's own names, merged where the game treats them the same).
LETTER_NAME = {
    '.': 'Plain', 'e': 'Waste', 'O': 'Floor', '0': 'Wall', '4': 'Mast', '9': 'Ship', '8': 'Building', 'j': 'Bones', 'b': 'Bridge', 'f': 'Woods', 's': 'Desert / beach', 'm': 'Mountain', 'w': 'River', 'a': 'Sea / lake',
    'Z': 'Sky', 'M': 'Lava', 'F': 'Fort', 'g': 'Gate', 't': 'Throne', 'S': 'Stairs', 'p': 'Pillar', 'v': 'Village / house',
    'V': 'Closed village / house', 'd': 'Door', 'c': 'Chest', 'C': 'Cliff / peak / building', 'r': 'Rubble',
    'l': 'Fence / partition / supplies', '#': 'Wall', 'X': 'Lava floor', 'H': 'Hazard', 'Y': 'Sigil', 'I': 'Ire',
}
# Tiles no unit can move onto that the game still places units on, who get their Def and Avoid: the Endgame's and two DLC maps'
# sigils, where foes appear, and the Endgame's Ire, Grima's tile.
PLACED_ON = {
    'Y': 'No unit can move onto it; foes appear on it, and a unit placed there gets its Def and Avoid.',
    'I': "No unit can move onto it; Grima is placed on it, and gets its Def and Avoid.",
}
FLIERS = 13  # the movement row every flying class uses (all 1s)
STORY = ['P001', 'P002'] + [f'{n:03d}' for n in range(1, 27)]
PARALOGUES = [f'X{n:03d}' for n in range(1, 24)]
DLC = sorted(d for d in os.listdir(DLC_ROOT) if d.startswith('E')) if os.path.isdir(DLC_ROOT) else []

ITEMS = {it['iid']: it for it in D.items()}
TERRAINS = D.terrains()
TWO_WIDE_DOORS = {9, 10, 11, 16, 18}  # door models whose trick covers x and x+1 (0x2b9d4c), as a wall's (kind 22) always does
LOCKED = 'A locked door: open it with a Door Key or Master Key, or a unit with Locktouch.'
SERIES = C.series_table()
FORGED = re.compile(r' \(forged: [^)]*\)$')
MAIN = D.persons('static')
CHAPTERS = {c['key']: c for c in D.chapters()}
GENERIC_LABELS = set()  # labels several of a chapter's characters share, a role's or an army's: a plain marker (generic_labels)
ARMY_LABELS = set()  # those of them that are an army's name: the unit goes by its class
FACELESS = set()  # every label a character without a portrait carries, anywhere on the cartridge


def item_name(iid):
    it = ITEMS.get(iid)
    name = D.item_name(it) if it else None
    if it and name == 'Ragnell' and it['iid'].endswith('（敵）'):
        return 'Ragnell (enemy)'
    return name


def map_id(key):
    if key == 'P001':
        return 'fe13-premonition'
    if key == 'P002':
        return 'fe13-prologue'
    if key == '026':
        return 'fe13-endgame'
    if key.startswith('X'):
        return f'fe13-par{int(key[1:])}'
    if key.startswith('E'):
        return f'fe13-dlc{int(key[1:])}'
    return f'fe13-{int(key)}'


class Source:
    """Where one map's files are: the cartridge's, or a DLC map's own (each holds its map as E000)."""

    def __init__(self, key):
        self.key = key
        if key.startswith('E'):
            self.base = os.path.join(DLC_ROOT, key)
            self.file = 'E000'
            self.text = D.text('E000', self.base)
        else:
            self.base = ROMFS
            self.file = key
            self.text = {}
        self.script = E.Chapter(os.path.join(self.base, 'scripts', self.file + '.cmb'))
        self.persons = D.persons(self.file, self.base)

    def name(self, label):
        return D.name_of(label) or self.text.get(label) or D.name_of(label, self.base)


def person(src, pid):
    return src.persons.get(pid) or MAIN.get(pid)


AVATAR = ('PID_プレイヤー男', 'PID_プレイヤー女', 'PID_プレイヤー')
DUMMY = 'PID_ダミー'


def unit_name(src, pid):
    if pid in AVATAR:
        return 'Avatar'
    if pid == DUMMY:
        return 'Random foe'
    p = person(src, pid)
    if p and p['name_label']:
        n = src.name(p['name_label'])
        if n:
            return n
    if p and pid.count('_') >= 2:
        # A DLC map's guest heroes have no name label of their own: their names are the DLC text's MPID_配信<name> (or 予約), else
        # the game's own MPID_<name> (Champions of Yore's Marth).
        suffix = pid.split('_', 2)[2]
        for label in (f'MPID_配信{suffix}', f'MPID_予約{suffix}', f'MPID_{suffix}'):
            n = src.name(label)
            if n:
                return n
    # A main character with no record of their own here: MPID_ plus the PID's name.
    return src.name('M' + pid) or pid


def class_name(src, pid):
    p = person(src, pid)
    c = D.class_by_jid().get(p['jid']) if p else None
    return c['name'] if c else None


def level(src, pid):
    p = person(src, pid)
    return p['level'] if p else None


def placed_level(src, u):
    """The level the unit is placed at: the placement's own (+0x15) where it gives one, else the person's (0x2dd940)."""
    return u.get('level') or level(src, u['pid'])


def placed_jid(src, u):
    """The class the unit is placed as: the placement's own (+4) where it gives one, else the person's."""
    p = person(src, u['pid'])
    return u.get('jid') or (p['jid'] if p else None)


def upgrade(it, lv):
    """The weapon a foe's item becomes at a level (0x27c4c0): the series' (+0x19) tier at that level, four at most (two for Flux and
    Nosferatu), where the level is past the item's own tier (+0x1a); series 0 and 11 stay as they are."""
    series, tier = it['series'], it['tier']
    if series in (0, 11) or not lv or lv <= tier or series not in SERIES:
        return it
    tiers = SERIES[series]
    return ITEMS[tiers[min(lv, len(tiers)) - 1]]


def forge_count(it, lv):
    """How many forge steps a foe's weapon gets at a level (0x27c47c): how far the level is past the series' top tier (series 11:
    past the item's own tier), two at most. Each step is Mt +4 and Hit +10 (0x27ce34, 0x27c7c0)."""
    series = it['series']
    if series == 0:
        return 0
    top = it['tier'] if series == 11 else len(SERIES.get(series, [0] * 4))
    return max(0, min(lv - top, 2))


def foe_gear(src, u, di):
    """(carries, drops) for a placement on difficulty di (0 Normal, 1 Hard, 2 Lunatic), as the item loader (0x27cd00) hands them
    out. A slot's byte +5+di is its level there, 0 leaving the item off. On a unit outside your army (person +0x46 not 1), a weapon
    (not a staff or an item) that's the first it carries, or one it doesn't drop, steps up its series to that level and, past the
    top, is forged; a dropped weapon that steps up is carried as the new one, and the old one is added after the rest to drop
    (0x2d1070), where a slot is free."""
    p = person(src, u['pid'])
    outside = not (p and p['raw'][0x46] == 1)
    carries, drops, later = [], [], []
    for slot in u['items']:
        lv = slot['levels'][di]
        it = ITEMS.get(slot['iid'])
        name = item_name(slot['iid'])
        if not lv or not it or not name:
            continue
        first = not carries
        if u['team'] == 1 and outside and (first or not slot['drop']) and it['raw'][24] not in (5, 10):
            up = upgrade(it, lv)
            n = 0 if D.has_isid(up, 'ISID_錬成不可') else forge_count(up, lv)
            if up is not it or n:
                carries.append(D.item_name(up) + (f' (forged: Mt +{4 * n}, Hit +{10 * n})' if n else ''))
                if slot['drop']:
                    later.append(name)
                continue
        carries.append(name)
        if slot['drop']:
            drops.append(name)
    for name in later:
        if len(carries) < 5:
            carries.append(name)
            drops.append(name)
    return carries, drops


def trick_tiles(x, y, kind, models):
    """The file tiles a trick changes (the switch at 0x2b9d10): a wall's (kind 22), and a door's (14) whose model is 9, 10, 11, 16 or
    18, are x and x+1; anything else is its own tile. `models`: {(x, y): its tile handler's model}."""
    if kind == 22 or (kind == 14 and models.get((x, y)) in TWO_WIDE_DOORS):
        return [(x, y), (x + 1, y)]
    return [(x, y)]


def trick_terrain(tid, state):
    """The terrain a tile takes in a trick's state (0x2b968c): 2 its TerrainData +12, 4 its +13, 1 the map's own."""
    if state == 2:
        return TERRAINS[tid]['becomes']
    if state == 4:
        return TERRAINS[tid]['becomes2']
    return tid


def to_app(x, y, h):
    """A file tile (from the top left, border included) -> the app's (from (1, 1) at the bottom left, without the border)."""
    return [x, h - 1 - y]


def playable(x, y, w, h):
    return 1 <= x <= w - 2 and 1 <= y <= h - 2


def grid_rows(w, h, g):
    return [''.join(LETTER[g[y][x]] for x in range(1, w - 1)) for y in range(1, h - 1)]


def tile_names(tiles, w, h):
    """Each code's names on a map, as the game names its tiles (TerrainData's name): the most common first, then the tiles with each
    other name ('Cliff / Peak'), so the legend and the tile panel say what the game says. Closed villages and houses keep the
    code's name (the game calls them '(Village)'), and so does Chapter 18's lava floor."""
    found = defaultdict(lambda: defaultdict(list))
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            tid = tiles[y][x]
            found[LETTER[tid]][TERRAINS[tid]['name']].append(to_app(x, y, h))
    over = {}
    for letter, names in found.items():
        if any(n.startswith('(') for n in names) or letter == 'X':
            # A closed village or house, and Chapter 18's lava floor (the game's "Floor"): the code's name says what matters.
            continue
        order = sorted(names, key=lambda k: (-len(names[k]), k))
        if len(order) == 1 and order[0] == LETTER_NAME[letter]:
            continue
        over[letter] = {'name': ' / '.join(order), **({'tileNames': {k: names[k] for k in order[1:]}} if len(order) > 1 else {})}
    return over


def build_terrain():
    """One entry per letter: name, Def, Avoid, healing and the cost for each movement type (None: can't enter)."""
    terr = D.terrains()
    costs = D.move_costs()
    groups = move_groups()
    info = {}
    for tid, letter in LETTER.items():
        t = terr[tid]
        code = encode(GAME, letter)
        move = {label: (None if costs[row][t['cat']] == 255 else costs[row][t['cat']]) for label, _, row in groups}
        entry = {'name': LETTER_NAME[letter], 'def': t['def'], 'avo': t['avo'], 'heal': t['heal'], 'move': move}
        if t['flags'] & 0x20:
            # TerrainData's flag 0x20 (Chapter 18's hazard and lava): map::ProcTerrainDamage (0x39789c), a step of the phase start
            # (0x45f840) run on the army whose phase it is, takes 10 HP, leaving at least 1, whatever the unit's class.
            fliers_only = all(v is None for k, v in move.items() if k != 'Fliers')
            entry['note'] = ("Only fliers can cross it; a flier on it at the start of its army's phase loses 10 HP, never dropping below 1."
                             if fliers_only else
                             "A unit on it at the start of its army's phase loses 10 HP, never dropping below 1; fliers too.")
        if letter == 'X':
            entry['note'] = 'Chapter 18: islets of it turn to hazard terrain on set turns (tap a flame).'
        if letter in PLACED_ON:
            entry['note'] = PLACED_ON[letter]
        elif all(v is None for v in move.values()):
            entry['def'] = entry['avo'] = entry['heal'] = 0
        if code in info:
            old = info[code]
            same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}
            assert same, (letter, tid, t, old, entry)
        else:
            info[code] = entry
    return info, groups


def move_groups():
    """The game's movement types (a class's +80 picks the row of TerrainCostData), each named by its classes."""
    rows = defaultdict(list)
    for i, c in enumerate(D.classes()):
        if c['name'] and c['name'] not in ('DUMMY', 'Grima', 'Mirage'):
            rows[c['move_type']].append(i)
    out = []
    for row in sorted(rows):
        names = list(dict.fromkeys(D.classes()[i]['name'] for i in rows[row]))
        label = 'Fliers' if row == FLIERS else ', '.join(names[:3]) + (' and others' if len(names) > 3 else '')
        out.append((label, rows[row], row))
    return out


# ---------------------------------------------------------------------------------------------------------------------------------


def label_sets(persons):
    """(shared, armies, faceless) for one person file: the name labels two or more of its characters share, those of them where one
    of the sharers has no portrait (+12: an army's name, as Risen, Plegian, Valmese, a DLC map's Outrealm foes), and every label a
    character without a portrait carries."""
    count, faceless = defaultdict(int), set()
    for p in persons.values():
        label = p['name_label']
        if not label:
            continue
        count[label] += 1
        if not p['fid']:
            faceless.add(label)
    shared = {label for label, n in count.items() if n >= 2}
    return shared, shared & faceless, faceless


def generic_labels():
    """(generic, armies, faceless) across the cartridge's chapter files. A label several of a file's characters share is generic (a
    plain marker) where someone carries it without a portrait, there or anywhere: a soldier's, or a role's (Paralogue 5's three sages
    all have one, but the villagers' label is faceless elsewhere). A person's several records share a label too, every one with a
    portrait (Chapter 23's two Validars, Five-Anna Firefight's Annas): they stay named."""
    shared, armies, faceless = set(), set(), set()
    for f in os.listdir(os.path.join(ROMFS, 'data', 'person')):
        key = f.split('.')[0]
        if key in ('static', 'dual', 'aDebug'):
            continue
        s, a, fl = label_sets(D.persons(key))
        shared |= s
        armies |= a
        faceless |= fl
    return shared & faceless, armies, faceless


def label_kind(src, pid):
    """'army' for a unit the game names only by its army (it goes by its class, a boss too), 'shared' for one whose label others
    share (a plain marker), None for a person. Read against the cartridge's labels and the map's own person file (a DLC map's)."""
    if pid in MAIN or pid in AVATAR or pid == DUMMY:
        return None
    p = person(src, pid)
    label = p['name_label'] if p else None
    if not label:
        return None
    if not hasattr(src, 'labels'):
        src.labels = label_sets(src.persons)
    shared, armies, faceless = src.labels
    if label in ARMY_LABELS or label in armies:
        return 'army'
    if label in GENERIC_LABELS or (label in shared and (label in faceless or label in FACELESS)):
        return 'shared'
    return None


def is_generic(src, pid):
    return label_kind(src, pid) is not None


def display_name(src, pid, jid=None):
    """What a unit is called on the map: its class (the placement's, where it gives one) where the game names it only by its army,
    else its name."""
    if label_kind(src, pid) == 'army':
        c = D.class_by_jid().get(jid) if jid else None
        return (c['name'] if c else class_name(src, pid)) or unit_name(src, pid)
    return unit_name(src, pid)


POS = re.compile(r'pos\((\d+),(\d+)\)')


def ai_fields(param):
    """A placement AI slot's parameters as fields ('pos(5,17),0,pos(20,21)' -> ['pos(5,17)', '0', 'pos(20,21)'])."""
    return re.findall(r'pos\(\d+,\d+\)|[^,]+', param or '')


def ai_behaviour(src, u, h):
    """(words, looter, goes_to, village, unread) for what a unit's placement AI sends it to do, or None where it only fights (+68: the
    action, mind, attack and move slots, each a name data/AIData.bin defines and the placement's parameters, its fields -4, -5, -6...
    there). A thief's AI_MV_TrasureToEscape goes for the chest in field 1, then switches its mind to AI_MI_Escape for the exit in field
    3; AI_MV_Escape and EscapeSlow make for the exit in field 1 and leave (with none given, The Golden Gaffe's and EXPonential Growth's,
    the Fire Emblem Wiki says the south); AI_MI_Village goes for the village in field 1, or any, then switches to AI_AT_Attack; AI_AT_Null
    never attacks. A green unit's AI_MV_Position and AI_MI_Talk give its goal, and AI_AT_Idle with AI_MV_Null holds it still.
    A unit of any army sent after one person (AI_MV_Person: command 0x57 on the PID in field 1) goes for them; one whose attack picks a
    person (AI_AT_Person, and Paralogue 17's AI_AT_X017Enemy: command 0x04 on the PID) targets them when it attacks; 0x05 in
    AI_AT_ExcludePerson and 0x54 in AI_MV_NearestEnemyExcludePerson leave one person out (the user's call: say these patterns). Paralogue
    9's boss (AI_MV_X009Boss) heads for the tile in its field. AI_AC_Turn n wakes it on turn n. `unread` names the part of a routine not
    read, for the map's unconfirmed notes."""
    (ac, ac_p), (mi, mi_p), (at, at_p), (mv, mv_p) = zip(u['ai'], u['ai_params'])
    f = ai_fields(mv_p) or ai_fields(mi_p)

    def who(pid):
        # A soldier the game names by its army goes by its class ('the Archers'); one who shares the unit's own name is 'the other'
        # (Paralogue 22's Aversa, going for the foe Aversa).
        name = display_name(src, pid)
        return f'the {name}s' if is_generic(src, pid) else f'the other {name}' if name == unit_name(src, u['pid']) else name

    def tile(k):
        mm = POS.fullmatch(f[k]) if len(f) > k else None
        return to_app(int(mm.group(1)), int(mm.group(2)), h) if mm else None

    def at_(t):
        return f'({t[0]}, {t[1]})'

    quiet = ', never attacking' if at == 'AI_AT_Null' else ''
    out = None
    if mv == 'AI_MV_TrasureToEscape' and tile(0) and tile(2):
        out = (f'goes for the chest at {at_(tile(0))}, empties it, then makes for {at_(tile(2))} and leaves the map{quiet}', True,
               [tile(2)], None, None)
    elif mv in ('AI_MV_Escape', 'AI_MV_EscapeSlow'):
        out = ((f'makes for {at_(tile(0))} and leaves the map{quiet}', False, [tile(0)], None, None) if tile(0) else
               (f'makes for the south edge of the map and leaves it{quiet}', False, None, None, None))
    elif mi == 'AI_MI_Village':
        target = tile(0)
        what = f'the village at {at_(target)}' if target else 'a village'
        out = ((f'goes for {what} without attacking, razes it, then attacks' if quiet else f'goes for {what}, razing it, then attacks'),
               True, None, target or 'any', None)
    elif u['team'] == 2 and mv == 'AI_MV_Position' and tile(0):
        out = (f'heads for {at_(tile(0))}', False, [tile(0)], None, None)
    elif u['team'] == 2 and mi == 'AI_MI_Talk' and mi_p:
        out = (f'goes to {unit_name(src, mi_p)} to talk', False, None, None, None)
    elif mv == 'AI_MV_Person' and mv_p:
        out = (f'goes for {who(mv_p)}', False, None, None, 'person' if at == 'AI_AT_Person' else None)
    elif at in ('AI_AT_Person', 'AI_AT_X017Enemy') and at_p and at_p != u['pid']:
        # Its attack picks the person; it moves as any foe does (or, with AI_MV_Null, not at all).
        still = 'holds its ground and ' if mv == 'AI_MV_Null' else ''
        out = (f'{still}targets {who(at_p)} when it attacks', False, None, None,
               ('x017', who(at_p)) if at == 'AI_AT_X017Enemy' else 'person')
    elif u['team'] == 2 and at == 'AI_AT_Idle' and mv == 'AI_MV_Null':
        out = ('stays where it stands and never attacks', False, None, None, None)
    elif mv == 'AI_MV_X009Boss' and tile(0):
        # Its own mind routine may change its other slots: whether it attacks isn't said (the map's unconfirmed notes).
        out = (f'heads for {at_(tile(0))}', False, [tile(0)], None, 'x009')
    else:
        # One person left out: of its moves (AI_MV_NearestEnemyExcludePerson), its attacks (AI_AT_ExcludePerson), or both.
        ex_mv = mv_p if mv == 'AI_MV_NearestEnemyExcludePerson' else None
        ex_at = at_p if at == 'AI_AT_ExcludePerson' else None
        if ex_mv and ex_mv == ex_at:
            out = (f'leaves {who(ex_mv)} alone', False, None, None, None)
        elif ex_mv:
            out = (f'never goes for {who(ex_mv)}', False, None, None, None)
        elif ex_at:
            out = (f'never attacks {who(ex_at)}', False, None, None, None)
    if out and ac == 'AI_AC_Turn' and ac_p and ac_p.isdigit() and int(ac_p) > 1:
        out = (f'from turn {ac_p}, {out[0]}',) + out[1:]
    return out


def with_behaviour(src, e, u, h):
    """A unit entry with what its AI sends it to do: a sentence on its note, the torch badge for a looter, the tiles it heads for."""
    b = ai_behaviour(src, u, h)
    if b:
        words, looter, goes, village, unread = b
        e['note'] = add_sentences(e.get('note'), words[0].upper() + words[1:] + '.')
        if unread:
            e['_unread'] = unread
        if looter:
            e['looter'] = True
        if goes:
            e['goesTo'] = goes
        if village:
            e['_raids'] = village
    return e


def unit_entry(src, u, h, gear=None):
    """A placement record -> the app's unit (no difficulties yet), with `gear` (carries, drops) for one difficulty where it's given."""
    pid = u['pid']
    if pid == DUMMY:
        # A spot the game fills with a foe it picks (the Endgame's sigils pick a class at random from the map's templates).
        e = {'type': 'enemy' if u['team'] == 1 else 'ally', 'name': 'Random foe' if u['team'] == 1 else 'Random ally',
             'tile': to_app(*u['end'], h), 'note': 'The game picks this unit at random when it appears.', '_pid': pid}
        if u['team'] != 1:
            e['generic'] = True
        return e
    generic = is_generic(src, pid)
    jid = placed_jid(src, u)
    name = display_name(src, pid, jid)
    if gear:
        items, drops = gear
    else:
        items = [item_name(i['iid']) for i in u['items'] if item_name(i['iid'])]
        drops = [item_name(i['iid']) for i in u['items'] if i['drop'] and item_name(i['iid'])]
    c = D.class_by_jid().get(jid) if jid else None
    cls = c['name'] if c else class_name(src, pid)
    lv = placed_level(src, u)
    # A unit named by its class doesn't say the class again.
    by_class = label_kind(src, pid) == 'army'
    note = ' '.join(x for x in [f'Lv {lv}' if lv else '', '' if by_class else (cls or '')] if x)
    if cls == 'Mirage':
        # Paralogue 22's shadows: ForceUnitTransformForX022 turns each into a copy of one of your units as the battle starts.
        note = 'Takes the form of one of your units as the battle starts'
    if items:
        note += (': ' if note else '') + ', '.join(items)
    if u['team'] == 1:
        kind = 'boss' if u['boss'] else ('enemy' if generic else 'named')
    else:
        kind = 'ally'
    e = {'type': kind, 'name': name, 'tile': to_app(*u['end'], h), 'note': note, '_pid': pid}
    if generic:
        e['_generic'] = True
    if drops and u['team'] == 1:
        e['drops'] = drops
    if items and u['team'] == 1:
        e['carries'] = items
    if kind == 'ally' and generic:
        e['generic'] = True
    return with_behaviour(src, e, u, h)


def unit_entries(src, u, h):
    """A placement record -> its units: one per set of its difficulties that carry the same gear (foe_gear)."""
    if u['pid'] == DUMMY:
        return [with_difficulties(u, unit_entry(src, u, h))]
    by_gear = {}
    for di, dname in enumerate(E.DIFFS):
        if dname in u['difficulties']:
            carries, drops = foe_gear(src, u, di)
            by_gear.setdefault((tuple(carries), tuple(drops)), []).append(dname)
    out = []
    for (carries, drops), ds in by_gear.items():
        e = unit_entry(src, u, h, (list(carries), list(drops)))
        if set(ds) != set(E.DIFFS):
            e['difficulties'] = ds
        out.append(e)
    return out


def merge_same(entries):
    """One entry where entries differ only in their difficulties (a unit each difficulty places with a record of its own)."""
    out, seen = [], {}
    for e in entries:
        key = json.dumps({k: v for k, v in e.items() if k != 'difficulties'}, sort_keys=True, ensure_ascii=False)
        if key in seen:
            first = seen[key]
            if 'difficulties' in first:
                ds = set(first['difficulties']) | set(e.get('difficulties', E.DIFFS))
                if ds == set(E.DIFFS):
                    del first['difficulties']
                else:
                    first['difficulties'] = [d for d in E.DIFFS if d in ds]
            continue
        seen[key] = e
        out.append(e)
    return out


def growth_notes(src, records):
    """(notesOn, notes): what the unit setup (0x2dd940) gives units outside your army (person +0x46 not 1) that their shown level
    doesn't count. On Hard and Lunatic, the person's +0x3c and +0x3d levels' worth of growth more, every gain rounded up on Lunatic
    (0x2ddd50), and a weapon rank of at least WeaponLevelData's C on Hard and A on Lunatic in each type the class uses (0x2dde70);
    on every difficulty, 19 levels more for a promoted generic unit (+0x46 0, class flag SID_上級職)."""
    def phrase(values):
        values = sorted(values)
        return str(values[0]) if len(values) == 1 else ', '.join(map(str, values[:-1])) + f' or {values[-1]}'
    per = {d: [] for d in ('Hard', 'Lunatic')}
    promoted = False
    for u in records:
        p = person(src, u['pid'])
        if not p or p['raw'][0x46] == 1:
            continue
        for d, off in (('Hard', 0x3c), ('Lunatic', 0x3d)):
            if d in u['difficulties']:
                per[d].append(p['raw'][off])
        c = D.class_by_jid().get(placed_jid(src, u))
        if p['raw'][0x46] == 0 and c and c['promoted']:
            promoted = True
    on, notes = [], []
    for d, rank, extra in (('Hard', 'C', ''), ('Lunatic', 'A', ', every stat gain rounded up')):
        if not per[d]:
            continue
        levels = {v for v in per[d] if v}
        growth = (f"{phrase(levels)} more levels' worth of growth than their shown level counts" + (' (some have none)' if 0 in per[d] else '')
                  if levels else '')
        parts = [x for x in (growth, extra.lstrip(', ') if growth else '', f'a weapon rank of at least {rank} in each type their class uses') if x]
        text = f'On {d}, units outside your army have ' + (', '.join(parts[:-1]) + ', and ' + parts[-1] if len(parts) > 1 else parts[0])
        if not growth and d == 'Lunatic':
            text += ', and every stat gain they get is rounded up'
        on.append({'note': text + '.', 'difficulties': [d]})
    if promoted:
        notes.append("A promoted generic unit has 19 more levels' worth of growth than its shown level counts.")
    return on, notes


def groups_items(groups, pid):
    for _, us in groups.items():
        for u in us:
            if u['pid'] == pid:
                return [i['iid'] for i in u['items']]
    return []


def with_difficulties(u, e):
    if set(u['difficulties']) != set(E.DIFFS):
        e['difficulties'] = [d for d in E.DIFFS if d in u['difficulties']]
    return e


LAST_TURN = 30  # how far arrivals() plays an open-ended handler


def turns_text(ts):
    """'Turn 3', 'Turns 4, 7–8', 'Turn 4, and every turn from turn 8': a run reaching LAST_TURN is open-ended."""
    runs, a = [], ts[0]
    for prev, t in zip(ts, ts[1:] + [None]):
        if t != prev + 1:
            runs.append((a, prev))
            a = t
    words = [f'{a}' if a == b else f'{a}–{b}' for a, b in runs if b < LAST_TURN]
    tail = next((a for a, b in runs if b >= LAST_TURN), None)
    if tail is None:
        return ('Turn ' if len(ts) == 1 else 'Turns ') + ', '.join(words)
    every = f'every turn from turn {tail}'
    return (('Turn ' if len(words) == 1 else 'Turns ') + ', '.join(words) + f', and {every}') if words else every[0].upper() + every[1:]


# What an area handler's condition function checks (its last argument), where a group waits on one.
CONDITIONS = {'IsDisposBoss': 'the boss is first defeated', 'IsSerenaTransferEnemy': 'Severa turns against you'}


def condition_fn(ch, hd):
    """The function an area handler's condition names (args[5], the script's own ev::<name>: Paralogue 14's IsVisitMerageVillage),
    or None."""
    name = ch.string(hd['args'][5]) if len(hd['args']) > 5 and hd['args'][5] else None
    return next((f for f in ch.hs if f['k'] == 0 and f['name'] == f'ev::{name}'), None) if name else None


def hidden_spot(hd):
    """An area handler on one tile that gives items when one of your units reaches it: a hidden item (Paralogue 14's Goddess Staff on
    a desert tile, its message a village's)."""
    if hd['k'] != E.AREA:
        return False
    x1, y1, x2, y2 = hd['args'][:4]
    return (x1, y1) == (x2, y2) and x1 >= 0 and bool(E.item_gains(hd))


SIDES = {0: 'to your side', 1: 'against you', 2: 'green'}


def offer_branches(ch, hd, src):
    """The offers a handler makes named units make (E.offers) and what taking each does, Paralogue 13's turn-1 choice: 'cond' ('you
    accept Gyral's offer'; the lord's own question, asked after theirs, turns them all down), 'gerund', 'sides' ({army: side} for
    ev::ForceUnitTransferExchange(a, b), which trades two armies' sides, and ev::ForceUnitTransfer(a, b), which moves army a into b),
    the groups it places and the flags it sets. None where no named unit asks."""
    if not ch.calls(hd, 'ev::DialogYesNo'):
        return []
    bs = E.offers(hd)
    named = [b for b in bs if (p := person(src, b['asker'])) and p['raw'][0x46] == 2]
    if not named:
        return []
    both = 'both offers' if len(named) == 2 else 'every offer'
    ins, out = hd['ins'], []
    for b in bs:
        name = unit_name(src, b['asker'])
        fx = {'asker': b['asker'], 'named': b in named, 'start': b['start'], 'end': b['end'], 'sides': {}, 'groups': [], 'flags': [],
              'cond': f"you accept {name}'s offer" if b in named else f'you turn {both} down',
              'gerund': f"accepting {name}'s offer" if b in named else f'turning {both} down'}
        for k, (pc, n, a) in enumerate(ins):
            if n != 'call' or not b['start'] < pc < b['end']:
                continue
            if a.split('/')[0] in ('ev::ForceUnitTransferExchange', 'ev::ForceUnitTransfer') and ins[k - 2][1] == ins[k - 1][1] == 'int':
                x, y = ins[k - 2][2], ins[k - 1][2]
                fx['sides'][x] = y
                if 'Exchange' in a:
                    fx['sides'][y] = x
            elif a.startswith('ev::Dispos/') and ins[k - 2][1] == 'str':
                fx['groups'].append(ins[k - 2][2].strip("'"))
            elif a.startswith('ev::FlagSet') and ins[k - 1][1] == 'str':
                fx['flags'].append(ins[k - 1][2].strip("'"))
        out.append(fx)
    return out


def add_sentences(note, *sentences):
    """A unit's note with sentences after it, its gear ('Lv 10 Taguel: Beaststone, Elixir') closed with a full stop first."""
    note = (note or '').strip()
    if note and sentences and not note.endswith('.'):
        note += '.'
    return ' '.join([note] + list(sentences)).strip()


def either(conds):
    """'you accept Gyral's offer or turn both offers down': clauses joined with 'or', a 'you' they share said once."""
    if len(conds) > 1 and all(c.startswith('you ') for c in conds):
        return ' or '.join([conds[0]] + [c[4:] for c in conds[1:]])
    return ' or '.join(conds)


def flag_cause(ch, flag, h, src):
    """'the village at (18, 16) is visited', 'Severa talks to Holland or Severa turns against you': what sets a flag, from the handlers
    that set it; None where nothing readable does."""
    out = []
    for hd in ch.hs + ch.ths:
        if flag not in E.flags_set(hd):
            continue
        k, args = hd['k'], hd['args']
        taken = [b['cond'] for b in offer_branches(ch, hd, src) if flag in b['flags']]
        if taken:
            out += taken
        elif k == E.TILE:
            what = E.TILE_KINDS.get(args[2])
            verb = {'village': 'visited', 'door': 'opened', 'chest': 'opened'}.get(what)
            if verb:
                out.append(f'the {what} at {where([args[:2]], h)} is {verb}')
        elif k == E.TALK:
            out.append(f'{unit_name(src, ch.string(args[0]))} talks to {unit_name(src, ch.string(args[1]))}')
        elif k == E.AREA and len(args) > 5 and CONDITIONS.get(ch.string(args[5])):
            out.append(CONDITIONS[ch.string(args[5])])
        elif k == E.AREA and min(args[:4]) >= 0:
            out.append('one of your units enters the marked area' if args[4] != 1 else 'an enemy enters the marked area')
        elif k == E.DEATH:
            out.append(f'{unit_name(src, ch.string(args[0]))} falls')
    return ' or '.join(dict.fromkeys(out)) or None


def dispos_guards(ch, hd, h, src, groups):
    """{group: words} for the groups a handler places only on a condition it checks first, read from its code: a flag (what sets it),
    a turn-1 choice (whose offer you take), the arrival tiles being free (ev::UnitGetByPosition on each), or the foes left
    (ev::ForceUnitGetCount(1) below a number)."""
    ins = hd['ins']
    out = {}
    flags, offered = [], defaultdict(list)
    tiles, count = [], None
    branches = offer_branches(ch, hd, src)
    for k, (pc, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::FlagGet') and ins[k - 1][1] == 'str':
            flags.append(ins[k - 1][2].strip("'"))
        elif n == 'call' and a.startswith('ev::UnitGetByPosition') and ins[k - 2][1] == 'int' and ins[k - 1][1] == 'int':
            tiles.append((ins[k - 2][2], ins[k - 1][2]))
        elif n == 'call' and a.startswith('ev::ForceUnitGetCount') and ins[k - 1][2] == 1:
            # var = ForceUnitGetCount(1) ... var < n (Roster Rescue's last wave: fewer than 49 foes).
            near = ins[k + 1:k + 16]
            lt = next((j for j, x in enumerate(near) if x[1] == 'lt'), None)
            if lt and near[lt - 1][1] == 'int':
                count = near[lt - 1][2]
        elif n == 'call' and a.startswith('ev::Dispos/') and ins[k - 2][1] == 'str':
            group = ins[k - 2][2].strip("'")
            taken = [b['cond'] for b in branches if b['start'] < pc < b['end']]
            if taken:
                # A group an offer places: on each choice that places it (Paralogue 13's both armies' on turning both down).
                offered[group] += [c for c in taken if c not in offered[group]]
                continue
            if group in out:
                continue
            ends = {tuple(u['end']) for u in groups.get(group, [])}
            if tiles and ends and set(tiles[1:]) == ends:
                out[group] = 'unless your units stand on all of its arrival tiles'
            elif count is not None:
                out[group] = f'once fewer than {count} foes are left'
            else:
                # The first flag read with a readable cause (a later one can be the handler's own once-only latch).
                cause = next((c for c in (flag_cause(ch, f, h, src) for f in flags) if c), None)
                if cause:
                    out[group] = f'after {cause}'
    for group, conds in offered.items():
        out[group] = 'if ' + either(conds)
    return out


def arrivals(src, h, groups=None):
    """{group: {difficulty: text}} for every group a handler places after the chapter starts, and the areas that bring them in. A group
    the script places on several turns (Chapter 19's come back) arrives on each of them."""
    ch = src.script
    turns_of = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))  # group -> difficulty -> (phase, conditional) -> turns
    other = defaultdict(dict)
    areas = defaultdict(list)
    turncoats = set()
    gone = set()  # (group, PID): a unit its own handler takes off again (a scene's Gangrel, Excellus warping out)
    for hd in ch.hs:
        k, args = hd['k'], hd['args']
        pids = E.removed_pids(ch, hd)
        if pids:
            for di in range(3):
                gone |= {(g, p) for g, _ in E.run(ch.s, hd, di, 99) for p in pids}
        # A handler that hands every green unit to the enemy (ForceUnitGetFirst(2), then UnitTransferByIndex(unit, 1)): the green
        # units it places are foes (Chapter 17's Event03).
        if [2] in ch.calls(hd, 'ev::ForceUnitGetFirst') and ch.calls(hd, 'ev::UnitTransferByIndex'):
            for di in range(3):
                turncoats |= {g for g, _ in E.run(ch.s, hd, di, 99)}
        if k in (E.REINFORCE, E.TURN, E.TURN2, E.TUTORIAL):
            first, last = args[0], args[1]
            guards = dispos_guards(ch, hd, h, src, groups)
            # Apotheosis's handler counts the waves won (VariableGet('勝利数')) to pick the next.
            waves = any(a == "'勝利数'" for _, n, a in hd['ins'] if n == 'str')
            # The Endgame's sigils: a function the handler calls with the turn works out from it (mod) whether each one spawns.
            schedule = any(n == 'mod' for _, n, a in (x for g in {int(a, 16) for _, n, a in hd['ins'] if n == 'gvar'}
                                                       if E._handler_by_index(ch.s, g) for x in ch.s.disasm(E._handler_by_index(ch.s, g))))
            for di, dname in enumerate(E.DIFFS):
                # A reinforcement handler runs as the player phase starts on Normal and as the enemy phase starts on Hard and Lunatic
                # (its predicate, 0x3b7908); a turn handler names its phase.
                if k == E.REINFORCE:
                    phase = 'player phase' if di == 0 else 'enemy phase'
                else:
                    phase = E.PHASES.get(args[2]) if len(args) > 2 else None
                for t in range(max(first, 1), (last if 0 < last < 9999 else LAST_TURN) + 1):
                    for group, cond in E.run(ch.s, hd, di, t):
                        if waves:
                            # Apotheosis: the handler sends the next wave of its list (by the wins it counts) once the field is clear.
                            other[group][dname] = 'From turn 2, a wave at a time: each comes once the one before it is wiped out'
                        elif schedule and cond:
                            other[group][dname] = (f'From turn {first}, at the start of the {phase}, on the turns its own schedule picks '
                                                   '(the script works it out from the turn number)')
                        elif group in guards and (last < 0 or last >= 9999 or first < last):
                            other[group][dname] = (f'{guards[group][0].upper() + guards[group][1:]}, at the start of the next {phase}'
                                                   if guards[group].startswith('after') else
                                                   f'From turn {first}, {guards[group]}, at the start of the {phase}')
                        elif group in guards:
                            turns_of[group][dname][(phase, guards[group])].add(t)
                        else:
                            turns_of[group][dname][(phase, cond)].add(t)
        elif k == E.AREA:
            x1, y1, x2, y2, side = args[:5]
            rect = None
            if min(x1, y1, x2, y2) >= 0:
                (ax1, ay1), (ax2, ay2) = to_app(x1, y1, h), to_app(x2, y2, h)
                rect = [min(ax1, ax2), min(ay1, ay2), max(ax1, ax2), max(ay1, ay2)]
            for di, dname in enumerate(E.DIFFS):
                for group, cond in E.run(ch.s, hd, di, 1):
                    if rect:
                        other[group][dname] = ('Once an enemy enters the marked area' if side == 1 else
                                               'Once one of your units enters the marked area')
                        if di == 0:
                            areas[group].append({'who': 'enemy' if side == 1 else 'player', 'rect': rect})
                    elif len(args) > 5 and ch.string(args[5]) == 'IsDisposBoss':
                        boss = next((unit_name(src, u['pid']) for gr in groups.values() for u in gr if u['boss']), 'the boss')
                        other[group][dname] = f'Once {boss} is first defeated'
                    elif len(args) > 5 and CONDITIONS.get(ch.string(args[5])):
                        other[group][dname] = f'Once {CONDITIONS[ch.string(args[5])]}'
                    else:
                        other[group][dname] = 'Once a condition in the chapter is met'
        elif k == 0 and hd['index'] not in E.called(ch.s):
            # A function nothing in the script calls (a story scene the engine runs): its groups come during that scene.
            for di, dname in enumerate(E.DIFFS):
                for group, cond in E.run(ch.s, hd, di, 1):
                    other[group].setdefault(dname, 'During a story event')
    out = defaultdict(dict)
    for group, by in turns_of.items():
        for dname, parts in by.items():
            texts = []
            for (phase, cond), ts in sorted(parts.items(), key=lambda kv: min(kv[1])):
                ts = sorted(ts)
                text = turns_text(ts)
                if phase and phase != 'player phase':
                    text += f', {phase}'
                if isinstance(cond, str):
                    text += f', {cond}'
                elif cond:
                    text += ', once a condition in the chapter is met'
                texts.append(text)
            out[group][dname] = '; '.join(texts)
    for group, by in other.items():
        for dname, text in by.items():
            out[group][dname] = f"{out[group][dname]}; {text[0].lower() + text[1:]}" if dname in out[group] else text
    return out, areas, turncoats, gone


def one_per_arrival(reinforcements):
    """One group for what comes at the same moment, set off the same way: groups with the same time and areas are joined (Paralogue
    8's one handler places 24 placement groups at once). A wave or a sigil on its own schedule stays apart."""
    def per(when):
        return when if isinstance(when, dict) else {d: when for d in E.DIFFS}

    out = []
    for g in reinforcements:
        text = json.dumps(g['when'], ensure_ascii=False)
        if 'a wave at a time' in text or 'schedule' in text:
            out.append(g)
            continue
        # A group only some difficulties have joins one that comes at the same moment on each of them (its units keep their own
        # difficulties).
        mine = per(g['when'])
        same = next((o for o in out if o.get('areas') == g.get('areas') and 'schedule' not in json.dumps(o['when']) and
                     set(per(o['when'])) & set(mine) and all(per(o['when'])[d] == mine[d] for d in set(per(o['when'])) & set(mine))),
                    None)
        if same:
            union = {**mine, **per(same['when'])}
            same['when'] = collapse({d: union[d] for d in E.DIFFS if d in union})
            same['units'] = merge_same(same['units'] + g['units'])
            continue
        out.append(g)
    for n, g in enumerate(out, 1):
        g['label'] = f'Group {n}'
    return out


def collapse(by):
    """{difficulty: text} -> one string where every difficulty agrees, else the record (missing difficulties: not there)."""
    texts = set(by.values())
    if len(texts) == 1 and len(by) == len(E.DIFFS):
        return texts.pop()
    return by


def build_map(key, facts=None):
    """A map, and (into `facts`) what it gives: drops, what foes carry, chests, villages, gifts, who joins and with what."""
    facts = facts if facts is not None else defaultdict(list)
    src = Source(key)
    ch = src.script
    grid_key = ch.terrain_load() or src.file
    w, h, tiles = D.grid(grid_key, src.base if grid_key == src.file else ROMFS)
    groups = dict(D.dispos(src.file, src.base))
    # Each tile handler's model (a door's says whether it's two tiles wide).
    models = {(hd['args'][0], hd['args'][1]): hd['args'][3] for hd in ch.ths if hd['k'] == E.TILE and len(hd['args']) > 3}
    # The load's own tile changes, made before the battle (ev::TrickSet(x, y, kind, state), 0x3b6c8c): Champions of Yore's razed
    # village, Smash Brethren's open doors, Roster Rescue's open walls, Paralogue 14's hidden villages.
    original = [row[:] for row in tiles]
    at_load = {}
    for hd in ch.of_kind(E.LOAD):
        for args in ch.calls(hd, 'ev::TrickSet'):
            if len(args) == 4 and None not in args:
                for tx, ty in trick_tiles(args[0], args[1], args[2], models):
                    tiles[ty][tx] = trick_terrain(original[ty][tx], args[3])
                    at_load[(tx, ty)] = args[3]
    meta = CHAPTERS.get(key, {})
    mid = map_id(key)
    if key.startswith('E'):
        heading, title = 'Xenologue', src.name('MCID_E000')
    else:
        heading, title = meta.get('heading'), meta.get('title')
    m = {
        'id': mid, 'route': 'DLC' if key.startswith('E') else 'Paralogue' if key.startswith('X') else 'Story',
        'chapter': 0 if key.startswith('P') else int(key[1:]) if key[0] in 'XE' else int(key),
        'heading': heading, 'title': title, 'location': None if key.startswith('E') else meta.get('location'),
        'width': w - 2, 'height': h - 2, 'grid': grid_rows(w, h, tiles),
    }
    names = tile_names(tiles, w, h)
    if names:
        m['terrainOverrides'] = names
    # The chapter's load handler: its win rule and the groups placed before the battle.
    rule, at_start, random_pool, random_spots = None, [], [], []
    for hd in ch.of_kind(E.LOAD):
        for args in ch.calls(hd, 'ev::ChapterSetWinRule'):
            rule = args[0]
        if ch.calls(hd, 'ev::VariableGet'):
            # A random pick (DLC: Infinite Regalia, The Golden Gaffe, EXPonential Growth): the load draws a number, sets the template
            # group it names aside (Dispos with 512) again and again, then places the picks on a group of positions (1028).
            for args in ch.calls(hd, 'ev::Dispos'):
                if args[1] == 1028:
                    random_spots.append(args[0])
                elif args[0] and args[1] in (4, 0):
                    at_start.append(args[0])
            random_pool = [a.strip("'") for _, n, a in hd['ins'] if n == 'str' and a.strip("'") in groups
                           and a.strip("'") not in random_spots and a.strip("'") not in at_start]
            continue
        for di in range(3):
            for group, cond in E.run(ch.s, hd, di, 0):
                if group not in at_start:
                    at_start.append(group)
    # The opening: what turn 1's player-phase handlers place, before you act, stands there from the start (the Prologue's party,
    # Chapter 3's Sumia); a group placed only on some branch (Paralogue 13's choice) still arrives.
    for hd in ch.of_kind(E.TURN, E.TUTORIAL):
        if hd['args'][:1] == (1,) and hd['args'][1:2] in ((1,), ()) and (len(hd['args']) < 3 or hd['args'][2] == 0):
            for di in range(3):
                for group, cond in E.run(ch.s, hd, di, 1):
                    if not cond and group not in at_start:
                        at_start.append(group)
    m['victory'] = 'Defeat the commander' if rule == 0x40000 else 'Rout the enemy'
    m['defeat'] = 'Chrom or the Avatar is defeated'
    # Anyone else whose fall loses the chapter: a unit on your side whose person record has the defeat-condition flag (SID_敗北条件,
    # 0x20), and Chapter 3's keys (its CantDoorOpen condition ends the game).
    losers = []
    for group in at_start + [g for g in groups if g not in at_start]:
        for u in groups.get(group, []):
            p = person(src, u['pid'])
            if p and u['team'] != 1 and p['flags'] & 0x20 and u['pid'] not in AVATAR + ('PID_クロム',):
                name = unit_name(src, u['pid'])
                if name not in losers and name not in ('Chrom', 'Avatar', 'Player'):
                    losers.append(name)
    # And anyone a script gives the defeat condition (The Future Past 3's green Lucina, turn 1: UnitSetSkill(SID_敗北条件)).
    for hd in ch.of_kind(E.LOAD, E.TURN):
        for pid in E.skilled(ch, hd, 'SID_敗北条件'):
            name = unit_name(src, pid)
            if name not in losers and name not in ('Chrom', 'Avatar'):
                losers.append(name)
    if losers:
        m['defeat'] = 'Chrom, the Avatar' + ''.join(f', {n}' for n in losers[:-1]) + f' or {losers[-1]} is defeated'
    for hd in ch.of_kind(E.AREA):
        if ch.string(hd['args'][5]) == 'CantDoorOpen':
            m['defeat'] += ', or the door keys are lost before a door is opened'
    units, starts, forced = [], [], []
    lord = None
    # Units the opening (turn 1's player-phase handlers) takes off the map before the battle (Chapter 9's Gangrel and Aversa).
    left = set()
    for hd in ch.of_kind(E.TURN, E.TUTORIAL, E.LOAD):
        if hd['k'] == E.LOAD or (hd['args'][:1] == (1,) and (len(hd['args']) < 3 or hd['args'][2] == 0)):
            left |= set(E.removed_pids(ch, hd))
    for group in at_start:
        for u in groups.get(group, []):
            if u['team'] == 0 and key != 'P001':
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], False, u['difficulties']))
            if group == 'Player':
                tile = to_app(*u['end'], h)
                starts.append(tile)
                if u['pid'] == 'PID_クロム' or u['pid'].endswith('_クロム'):
                    lord = tile
                if u['flags'] & 0x02:
                    forced.append({'name': display_name(src, u['pid']), 'tile': tile})
                continue
            if u['team'] == 0 and playable(*u['end'], w, h) and u['pid'] not in left:
                # One of yours an opening places on its own tile (the Prologue's party, Chapter 3's Sumia): placed by the game.
                tile = to_app(*u['end'], h)
                if u['pid'] == 'PID_クロム' or u['pid'].endswith('_クロム'):
                    lord = tile
                if all(f['tile'] != tile for f in forced):
                    forced.append({'name': display_name(src, u['pid']), 'tile': tile})
                continue
            if not playable(*u['end'], w, h) or u['pid'] in left:
                continue
            units.extend(unit_entries(src, u, h))
    # A random foe takes its template's AI: where every template the game picks from shares one (The Golden Gaffe's and EXPonential
    # Growth's escape), the spot says it.
    templates = [u for g in random_pool for u in groups.get(g, [])]
    shared = {json.dumps(ai_behaviour(src, u, h)) for u in templates}
    for group in random_spots:
        for u in groups.get(group, []):
            if playable(*u['end'], w, h):
                e = with_difficulties(u, {'type': 'enemy', 'name': 'Random foe', 'tile': to_app(*u['end'], h),
                                          'note': 'The game picks this foe at random as the map loads.'})
                units.append(with_behaviour(src, e, templates[0], h) if templates and len(shared) == 1 else e)
    if rule == 0x40000:
        bosses = [u['name'] for u in units if u['type'] == 'boss']
        if bosses:
            m['victory'] = f'Defeat {bosses[0]}'
    m['objectives'] = []
    units = merge_same(units)
    # A load that places one group or another by the Avatar's gender (Paralogue 12's Morgans): the other is a stand-in.
    for hd in ch.of_kind(E.LOAD):
        pair = E.gender_branch(hd)
        if pair:
            female, other = ([u for u in groups.get(g, []) if playable(*u['end'], w, h)] for g in pair)
            for fu in female:
                stand = next((e for e in units if e['tile'] == to_app(*fu['end'], h) and e.get('_pid') == fu['pid']), None)
                base = next((e for e in units if e['tile'] == to_app(*fu['end'], h) and e.get('_pid') in {o['pid'] for o in other}), None)
                if stand and base:
                    units.remove(stand)
                    base['standIn'] = {'type': stand['type'], 'name': stand['name'], 'note': stand.get('note', ''),
                                       'when': 'the Avatar is female'}
                    if stand.get('generic'):
                        base['standIn']['generic'] = True
    m['units'] = units
    m['starts'] = starts
    if lord:
        m['corrinStart'] = lord
    if forced:
        m['forced'] = forced
    # What comes later.
    times, areas, turncoats, gone = arrivals(src, h, groups)
    reinforcements, joiners = [], []
    n = 0
    for group, by in times.items():
        members = [u for u in groups.get(group, []) if playable(*u['end'], w, h) and (group, u['pid']) not in gone]
        if not members or group in at_start:
            continue
        for u in members:
            if group in turncoats and u['team'] == 2:
                u['team'] = 1
        if isinstance(collapse(by), dict):
            for u in members:
                u['difficulties'] = [d for d in u['difficulties'] if d in by]
            members = [u for u in members if u['difficulties']]
        foes = [u for u in members if u['team'] == 1]
        if foes:
            n += 1
            g_out = {'id': f'{mid}-{group.lower()}', 'label': f'Group {n}', 'when': collapse(by),
                     'units': merge_same([{**e, 'from': to_app(*u['start'], h)} for u in foes for e in unit_entries(src, u, h)])}
            if areas.get(group):
                g_out['areas'] = areas[group]
            reinforcements.append(g_out)
        for u in members:
            if u['team'] == 1:
                continue
            j = {'name': display_name(src, u['pid']), 'tile': to_app(*u['end'], h), 'from': to_app(*u['start'], h), 'group': group,
                 'when': collapse(by), '_pid': u['pid']}
            if u['team'] == 0:
                # Arriving during the battle (Chapter 7's Cordelia): the recruit's gear is yours from the next chapter.
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], True, u['difficulties']))
            if u['team'] == 2:
                j['ally'] = True
            joiners.append(j)
    if reinforcements:
        m['reinforcements'] = one_per_arrival(reinforcements)
    if joiners:
        m['joiners'] = joiners
    # Talks: what each does, on the unit talked to (a recruit, a gift, a unit turned against you, one taken off the map); a talker the
    # talk hands over says it on its own unit (Paralogue 10's Severa, on reaching Holland).
    talks, words_on, notes_on, conversations = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    pair_count = defaultdict(int)
    for hd in ch.of_kind(E.TALK):
        pair_count[(ch.string(hd['args'][0]), ch.string(hd['args'][1]))] += 1
    for hd in ch.of_kind(E.TALK):
        talker, target = ch.string(hd['args'][0]), ch.string(hd['args'][1])
        who = unit_name(src, talker) if talker else 'anyone'
        moved = E.transfers(ch, hd)
        if (target, 0) in moved:
            talks[target].append((who, pair_count[(talker, target)]))
            continue
        if (talker, 0) in moved:
            gone = [p for p in E.removed_pids(ch, hd) if p == target]
            words_on[talker].append(f'Recruit: joins on reaching {unit_name(src, target)} and talking' +
                                    (f' ({unit_name(src, target)} then leaves the map)' if gone else ''))
            if gone:
                notes_on[target].append(f'Leaves the map once {who} reaches them and talks.')
            continue
        if (None, 1) in moved or (target, 1) in moved:
            words_on[target].append(f'If {who} talks to it, it turns against you')
            continue
        gains = E.item_gains(hd)
        if gains:
            parts = []
            for n, (iid, pids) in enumerate(gains):
                name = article(item_name(iid)) if item_name(iid) else '?'
                if pids and n == 0:
                    parts.append(f"{name} if {' or '.join(unit_name(src, p) for p in pids)} talks")
                elif pids:
                    parts.append(f'otherwise {name}')
                else:
                    parts.append(name)
            words_on[target].append(f"Talk with {who} (gives {', '.join(parts)})")
        elif pair_count[(talker, target)] == 1:
            conversations[target].append(who)
    # Joins and turns that come without a talk: after the battle if alive (an end handler: UnitIsAlive, then UnitTransferByIndex to
    # yours), on a turn (with what that turn gives them), and on a condition (Paralogue 10's Severa turning against you).
    TURN_CONDITIONS = {'IsSerenaTransferEnemy': 'if Holland falls before Severa reaches Holland'}
    for hd in ch.hs:
        if not ch.calls(hd, 'ev::UnitIsAlive'):
            continue
        for pid, army in E.transfers(ch, hd):
            if not pid:
                continue
            if army == 0 and hd['k'] == E.END:
                notes_on[pid].append('Joins your army after the battle if alive.')
            elif army == 0 and hd['k'] in (E.TURN, E.TURN2):
                gives = [article(item_name(i)) for i, _ in E.item_gains(hd) if item_name(i)]
                notes_on[pid].append(f'Joins your army at the start of {when_text(hd)}' + (f", with {', '.join(gives)}." if gives else '.'))
            elif army == 1 and hd['k'] == E.AREA and len(hd['args']) > 5 and TURN_CONDITIONS.get(ch.string(hd['args'][5])):
                notes_on[pid].append(f'Turns against you {TURN_CONDITIONS[ch.string(hd["args"][5])]}.')
    for e in units + joiners + [u for g in reinforcements for u in g['units']]:
        pid = e.get('_pid')
        if pid in talks:
            ways = list(dict.fromkeys(w for w, _ in talks[pid]))
            n_talks = max(n for _, n in talks[pid])
            e['talk'] = 'Recruit: talk with ' + ' or '.join(ways) + (f" {['', 'once', 'twice', 'three times', 'four times'][n_talks]}, "
                                                                     'one talk a turn' if n_talks > 1 else '')
            if e.get('type') in ('enemy', 'named', 'boss', 'ally'):
                # A talk recruits during the battle: the recruit's gear is yours from the next chapter.
                facts['joins'].append((pid, groups_items(groups, pid), True, e.get('difficulties')))
        if conversations.get(pid):
            words_on[pid].append(f"Talk with {' or '.join(dict.fromkeys(conversations[pid]))} (a conversation)")
        if words_on.get(pid):
            e['talk'] = '; '.join(([e['talk']] if e.get('talk') else []) + list(dict.fromkeys(words_on[pid])))
        if notes_on.get(pid) and 'note' in e:
            mine = list(dict.fromkeys(notes_on[pid]))
            if any(n.startswith('Joins your army at the start') for n in mine):
                # Joined on a turn already: the end's own join (if alive) is only its fallback.
                mine = [n for n in mine if not n.startswith('Joins your army after the battle')]
            e['note'] = add_sentences(e['note'], *mine)
    # After the battle: units the end of the chapter places on your side join then (Chapter 4's Lon'qu, Chapter 7's Cordelia).
    for hd in ch.of_kind(E.END):
        for di in range(3):
            for group, cond in E.run(ch.s, hd, di, 99):
                for u in groups.get(group, []):
                    if u['team'] == 0 and u['pid'] not in E.removed_pids(ch, hd) and E.DIFFS[di] in u['difficulties']:
                        facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], True, [E.DIFFS[di]]))
    # Gifts the story hands over in the chapter's own script: the load's or the turn-1 opening's are yours from this chapter; one at
    # the end or after the battle (the 0x0a and 0x0b handlers, a scene nothing calls), or from an event during it (a talk, a turn),
    # from the next. Each says the condition it's given on.
    for hd in ch.hs:
        gains = E.item_gains(hd)
        if not gains or hidden_spot(hd):
            continue
        conds = gift_conditions(ch, hd, src)
        opening = hd['k'] == E.LOAD or (hd['k'] in (E.TURN, E.TUTORIAL) and hd['args'][:1] == (1,) and
                                         (len(hd['args']) < 3 or hd['args'][2] == 0))
        asked = set()
        for iid, pids in gains:
            if opening:
                text, later = 'Given at the start of the chapter', False
            elif hd['k'] in (E.END, POST) or (hd['k'] == 0 and hd['index'] not in E.called(ch.s)):
                text, later = 'Given at the end of the chapter', True
            elif hd['k'] == E.TALK:
                talker, target = ch.string(hd['args'][0]), ch.string(hd['args'][1])
                partner = unit_name(src, target)
                text, later = f"Given in a talk with {article(partner.lower()) if is_generic(src, target) else partner}", True
                if pids and tuple(pids) in asked:
                    # The branch after the UnitIsPID check (Paralogue 5's sage: the Missiletainn for Owain, a Speed Tonic otherwise).
                    text += f", if anyone but {' or '.join(unit_name(src, p) for p in pids)} talks"
                elif pids:
                    text += f", if {' or '.join(unit_name(src, p) for p in pids)} talks"
                    asked.add(tuple(pids))
            elif hd['k'] in (E.TURN, E.TURN2, E.REINFORCE):
                text, later = f'Given at the start of {when_text(hd)}', True
            else:
                text, later = 'Given during the chapter', True
            if conds.get(iid):
                text += f', {conds[iid]}'
            facts['gifts'].append((iid, later, text))
    # Joins by a handover (UnitTransferByIndex to yours) at the end, after the battle or during it (Tiki, Aversa, Severa): their gear
    # is yours from the next chapter.
    for hd in ch.hs:
        if hd['k'] in (E.LOAD,):
            continue
        for pid, army in E.transfers(ch, hd):
            if pid and army == 0 and pid not in AVATAR:
                facts['joins'].append((pid, groups_items(groups, pid), True, None))
    # What foes drop and carry, for the weapon page, with the difficulties they're placed on (None: all three).
    for e in units:
        if e['type'] != 'ally' and e.get('carries'):
            facts['carries'].append((e['name'], [FORGED.sub('', x) for x in e['carries']], e.get('drops', []), False, bool(e.get('_generic')),
                                     e.get('difficulties')))
    for g in reinforcements:
        for e in g['units']:
            if e.get('carries'):
                facts['carries'].append((e['name'], [FORGED.sub('', x) for x in e['carries']], e.get('drops', []), True,
                                         bool(e.get('_generic')), e.get('difficulties')))
    for group in random_pool:
        for u in groups.get(group, []):
            facts['random'].append(([item_name(i['iid']) for i in u['items'] if item_name(i['iid'])],
                                    [item_name(i['iid']) for i in u['items'] if i['drop'] and item_name(i['iid'])], u['difficulties']))
    m['objects'], m['changes'], m['notes'] = [], [], []
    on, notes = growth_notes(src, [u for g in list(at_start) + [g for g in times if g not in at_start] for u in groups.get(g, [])
                                   if u['pid'] != DUMMY])
    if on:
        m['notesOn'] = on
    m['notes'] += notes
    opener = CHAPTERS.get('E000' if key.startswith('E') else key, {})
    if key[0] in 'XE' and opener.get('after'):
        after = CHAPTERS[opener['after']]['heading']
        if key.startswith('E'):
            m['notes'].append(f'Opens at the Outrealm Gate once {after} is cleared.')
        elif opener.get('parent'):
            parent = 'the Avatar' if opener['parent'].startswith('プレイヤー') else src.name('MPID_' + opener['parent'])
            m['notes'].append(f'Opens once {after} is cleared and {parent} is married.')
        elif opener.get('type') == 2:
            m['notes'].append(f'Opens once {after} is cleared and its SpotPass data has been received.')
        else:
            m['notes'].append(f'Opens once {after} is cleared.')
    m['changes'] = scripted_changes(ch, tiles, original, w, h, mid, models, at_load, src)
    extras = door_extras(ch, h, models)
    # A hidden item an area handler gives (Paralogue 14's at (9, 18): the Goddess Staff, to one of your units that enters the tile once
    # the village at (16, 5) has been visited, a flag its condition function reads; the other flag it reads is its own once-only latch).
    for hd in ch.of_kind(E.AREA):
        if not hidden_spot(hd):
            continue
        gains = [item_name(i) for i, _ in E.item_gains(hd) if item_name(i)]
        fn = condition_fn(ch, hd)
        flags = [f for f in E.flags_read(hd) + (E.flags_read(fn) if fn else []) if f not in E.flags_set(hd)]
        cause = next((c for c in (flag_cause(ch, f, h, src) for f in flags) if c), None)
        tile = to_app(*hd['args'][:2], h)
        m['objects'].append({'type': 'hidden', 'tile': tile, 'area': [*tile, *tile], 'contents': ', '.join(gains),
                             'note': 'One of your units that enters this tile gets it' + (f', once {cause}.' if cause else '.')})
        facts['hidden'].extend(gains)
    # A choice of offers (Paralogue 13's turn 1, asked again until one is taken): what taking each does to the armies, on the map and
    # on each unit it turns; a green unit an offer turns against you then drops what it carries to drop.
    for hd in ch.of_kind(E.TURN, E.TURN2):
        branches = offer_branches(ch, hd, src)
        if not branches:
            continue
        team_of = {u['pid']: u['team'] for us in groups.values() for u in us}
        army = {team_of[b['asker']]: f"{unit_name(src, b['asker'])}'s army" for b in branches if b['named'] and b['asker'] in team_of}
        turned = defaultdict(lambda: defaultdict(list))
        choices = []
        for b in branches:
            moves = [(t, s) for t, s in b['sides'].items() if t in army]
            for t, s in moves:
                turned[t][s].append(b['cond'])
            choices.append(b['gerund'] + (' turns ' + ' and '.join(f'{army[t]} {SIDES[s]}' for t, s in moves) if moves
                                          else ' leaves the armies as they are'))
        names = [unit_name(src, b['asker']) for b in branches if b['named']]
        m['notes'].append(f"At the start of {when_text(hd)}, {' and '.join(names)} each make an offer, asked again until you take one of "
                          f"the {['', 'one', 'two', 'three', 'four'][len(choices)]} choices: {'; '.join(choices)}.")
        for e in units:
            t = 1 if e['type'] in ('enemy', 'named', 'boss') else 2 if e['type'] == 'ally' else None
            for s, conds in turned.get(t, {}).items():
                e['note'] = add_sentences(e.get('note'), f'Turns {SIDES[s]} if {either(conds)}.')
                pu = next((u for us in groups.values() for u in us if u['pid'] == e.get('_pid') and u['team'] == t), None)
                drops = [item_name(i['iid']) for i in (pu or {}).get('items', []) if i['drop'] and item_name(i['iid'])]
                if s == 1 and drops:
                    e['note'] = add_sentences(e['note'], f"It then drops {', '.join(drops)}.")
                    facts['carries'].append((f"{e['name']}, if {either(conds)}", drops, drops, False, bool(e.get('_generic')),
                                             e.get('difficulties')))
    # Gold the end of the chapter gives (Paralogue 13's, by the choice taken and the green units left).
    for hd in ch.of_kind(E.END, POST):
        gold = gold_rewards(ch, hd, src, h)
        if gold:
            m['notes'].append(f"Clearing it gives {'; '.join(gold)}.")
    # A DLC map's reward: who clearing it adds to your army (ev::CompleteJoin, in its end scene).
    for hd in ch.hs:
        for args in ch.calls(hd, 'ev::CompleteJoin'):
            if args and args[0]:
                # The DLC's own name for its reward (MID_DLC_名前_<name>), else its hero's (its person file, then its text's MPID_配信 /
                # 予約 / plain labels), else the game's.
                pid = f'PID_{key}_{args[0]}'
                name = src.text.get(f'MID_DLC_名前_{args[0]}') or (unit_name(src, pid) if pid in src.persons else None) or next(
                    (n for n in (src.name(f'MPID_{p}{args[0]}') for p in ('配信', '予約', '')) if n), None) or unit_name(src, 'PID_' + args[0])
                m['notes'].append(f'Clearing it adds {name} to your army.')
    if any('schedule' in json.dumps(g['when']) for g in m.get('reinforcements', [])):
        m.setdefault('unconfirmed', []).append("Which turns each sigil's foes come on: the script's schedule isn't decoded.")
    if key == 'X016':
        m['notes'].append('Besides what its doors bring down (tap a door), its walls move during the battle: the script opens and shuts '
                          'them each turn once your units reach rows 6-9 or 11-14, and moves the row 5 walls from turn 3.')
        m['unconfirmed'] = ["How the moving walls are picked: the every-turn handler seems to leave open only the wall on a row whose "
                            "four columns hold the most of your units less foes, a count the turn shifts by 0 to 3; this isn't traced "
                            'line by line.']
    for hd in ch.ths:
        if hd['k'] != E.TILE:
            continue
        x, y, kind = hd['args'][:3]
        tile = to_app(x, y, h)
        what = E.TILE_KINDS.get(kind)
        if (x, y) in at_load and what in ('village', 'door'):
            # Changed as the map loads: a razed or hidden village, a door already open.
            continue
        gains = [item_name(i) for i, _ in E.item_gains(hd) if item_name(i)]
        # A random item (the DLC's villages and chests): one of a pool the program builds (fe13_data.random_pool).
        randoms = E.random_gains(hd)
        picks = [f'random item (the game picks one of {len(D.random_pool(r == "limit"))})' for r in randoms]
        if what == 'village':
            m['objects'].append({'type': 'village', 'tile': tile, 'reward': ', '.join(gains + picks)})
            notes = []
            # A recruit a visit brings (Paralogue 14's Laurent, when Chrom or Miriel visits): a group of yours it places.
            visitors = [hd['ins'][k - 1][2].strip("'") for k, (_, n, a) in enumerate(hd['ins'])
                        if n == 'call' and a.startswith('ev::UnitIsPID') and ins_str(hd['ins'][k - 1])]
            joins = [u['pid'] for g, _ in E.run(ch.t, hd, 0, 1) for u in groups.get(g, []) if u['team'] == 0]
            if joins:
                for p in dict.fromkeys(joins):
                    facts['joins'].append((p, groups_items(groups, p), True, None))
                who = ' or '.join(dict.fromkeys(unit_name(src, p) for p in visitors)) or 'anyone'
                names = list(dict.fromkeys(unit_name(src, p) for p in joins))
                notes.append(f"Visited by {who}, {' and '.join(names)} {'joins' if len(names) == 1 else 'join'} your army.")
            if TERRAINS[tiles[y][x]]['becomes'] == 4:
                # A phantom village (TerrainData +12 desert): gone once visited.
                notes.append('It turns to desert once visited.')
            if notes:
                m['objects'][-1]['note'] = ' '.join(notes)
            facts['villages'].extend(gains)
            facts['random_villages'].extend(randoms)
        elif what == 'chest':
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': ', '.join(gains + [p[0].upper() + p[1:] for p in picks])})
            facts['chests'].extend(gains)
            facts['random_chests'].extend(randoms)
        elif what == 'door':
            m['objects'].append({'type': 'door', 'tile': tile})
            # Opening it makes the trick's state 2 under it (TerrainData +12: a door to plain, floor or snowy floor); a turn may open
            # it by itself, and the flag its opening sets may bring walls down (door_extras).
            words, more = extras.get((x, y), ([], []))
            m['changes'].append({'id': f'door-{tile[0]}-{tile[1]}', 'trigger': 'event', 'tile': {'default': tile}, 'usableBy': '',
                                 'effect': ' '.join([LOCKED] + words),
                                 'patch': [{'tile': to_app(tx, ty, h), 'becomes': LETTER[trick_terrain(tiles[ty][tx], 2)]}
                                           for tx, ty in trick_tiles(x, y, kind, models)] +
                                          [{'tile': to_app(*t, h), 'becomes': LETTER[trick_terrain(original[t[1]][t[0]], st)]} for t, st in more]})
        elif what == 'event':
            m['objects'].append({'type': 'event', 'tile': tile})
            facts['event_tiles'].append(tile)
    # A village names the raiders on the map at the start that make for it (their AI's village, or any).
    raiders = defaultdict(list)
    for e in units:
        if e.get('_raids'):
            raiders[json.dumps(e['_raids'])].append(e['name'])
    for o in m['objects']:
        names = raiders.get(json.dumps(o['tile']), []) + raiders.get('"any"', []) if o['type'] == 'village' else []
        if names:
            o['note'] = add_sentences(o.get('note'), f"{' or '.join(dict.fromkeys(names))} can raze it before you visit.")
    if any('south edge of the map' in e.get('note', '') for e in units + [u for g in reinforcements for u in g['units']]):
        m.setdefault('unconfirmed', []).append("Where its foes escape: their AI (AI_MI_Escape) names no exit; the Fire Emblem Wiki says "
                                               'they make for the south.')
    # What the AI routines that pick a person leave unread.
    unread = {e.get('_unread') for e in units + joiners + [u for g in reinforcements for u in g['units']]}
    if 'person' in unread:
        m.setdefault('unconfirmed', []).append('Whether a unit that targets someone attacks others when they are out of reach: the last '
                                               'command of its AI routine (AI_AT_Person) is not read.')
    targets = sorted({x[1] for x in unread if isinstance(x, tuple) and x[0] == 'x017'})
    if targets:
        m.setdefault('unconfirmed', []).append(f"When its foes stop targeting {' or '.join(targets)} and attack anyone: their own routine "
                                               '(AI_MV_X017Enemy) switches them to AI_AT_Attack on a condition about the unit they target '
                                               'that is not read.')
    if 'x009' in unread:
        m.setdefault('unconfirmed', []).append('What sends its boss to the tile its AI names, whether it attacks (its attack slot is '
                                               'AI_AT_Null) and whether it leaves the map there: its own routine (AI_MI_X009Boss) is not '
                                               'read.')
    for e in units + joiners + [u for g in reinforcements for u in g['units']]:
        e.pop('_pid', None)
        e.pop('_generic', None)
        e.pop('_raids', None)
        e.pop('_unread', None)
    return m


LAVA_FLOOR, HAZARD, BARRIER = 45, 46, 48


def islet(g, x, y, w, h):
    """The lava floor tiles joined to (x, y) side by side: one islet."""
    seen, todo = set(), [(x, y)]
    while todo:
        a, b = todo.pop()
        if (a, b) in seen or not (0 <= a < w and 0 <= b < h) or g[b][a] != LAVA_FLOOR:
            continue
        seen.add((a, b))
        todo += [(a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)]
    return sorted(seen)


CHEST_TILE = 43


def where(tiles, h):
    """'(3, 14)', '(8, 20) and (14, 20)': file tiles in the app's words."""
    words = [f'({x}, {y})' for x, y in (to_app(*t, h) for t in tiles)]
    return words[0] if len(words) == 1 else ', '.join(words[:-1]) + ' and ' + words[-1]


def when_text(hd):
    """'turn 3 (player phase)': when a turn handler (first turn, last turn, phase) runs."""
    first, last, phase = hd['args'][:3]
    turns = f'turn {first}' if first == last or last == first else (f'every turn from {first}' if last < 0 else f'turns {first}-{last}')
    return f'{turns} ({E.PHASES.get(phase, "phase")})'


def scripted_changes(ch, g, original, w, h, mid, models, load_state, src):
    """What a chapter's script reshapes during the battle, each previewed (ev::TrickSet through fe13_events.tricks):
    Chapter 18's lava islets (an islet's model gives the rectangle it covers from its tile, 0x2b8f30: its lava floor turns to hazard
    and any chest in it to scrap, TerrainData +13); Chapter 23's barrier (falling once Validar is first beaten); walls a turn flips
    (Roster Rescue: a function opens a wall that's shut and shuts one that's open, so each preview shows the walls as that turn leaves
    them); a village a turn-1 choice closes (Paralogue 13); a village a visit brings up (Paralogue 14: the every-turn handler shows it
    once the flag the visit sets is up); and a tile a turn simply sets (The Future Past 2's turn-1 wall). Doors a turn opens are said
    on the door's own preview (door_extras)."""
    out = []
    chest_items = {(hd['args'][0], hd['args'][1]): ', '.join(n for n in (item_name(i) for i, _ in E.item_gains(hd)) if n)
                   for hd in ch.ths if hd['k'] == E.TILE and hd['args'][2] == 15}
    # Chapter 18's islets.
    rects = {(hd['args'][0], hd['args'][1]): C.model_size(hd['args'][3]) for hd in ch.ths if hd['k'] == E.TILE and hd['args'][2] == 20}
    when = defaultdict(list)
    for hd in ch.of_kind(E.TURN, E.TURN2):
        for x, y, kind, state, _ in E.tricks(ch, hd):
            if kind == 20 and state == 4 and (x, y) in rects:
                when[(x, y)].append((hd['args'][0], hd['args'][2]))
    for n, (corner, times) in enumerate(sorted(when.items(), key=lambda kv: min(kv[1]))):
        rw, rh = rects[corner]
        cells = [(corner[0] + dx, corner[1] + dy) for dy in range(rh) for dx in range(rw) if playable(corner[0] + dx, corner[1] + dy, w, h)]
        lava = [c for c in cells if g[c[1]][c[0]] == LAVA_FLOOR]
        burnt = [c for c in cells if g[c[1]][c[0]] == CHEST_TILE]
        text = ', '.join(f'turn {t} ({E.PHASES.get(p, "phase")})' for t, p in sorted(set(times)))
        effect = f'This lava floor islet turns to hazard terrain at the start of {text}.'
        for c in burnt:
            effect += f' Its chest at {where([c], h)} burns to scrap' + (f', and the {chest_items[c]} in it is lost.' if chest_items.get(c) else '.')
        out.append({'id': f'{mid}-islet{n + 1}', 'trigger': 'eruption', 'tile': {'default': to_app(*(lava or cells)[0], h)},
                    'usableBy': '', 'effect': effect,
                    'patch': [{'tile': to_app(*c, h), 'becomes': LETTER[TERRAINS[g[c[1]][c[0]]]['becomes2']]} for c in lava + burnt]})
    # Chapter 23's barrier, once its boss is defeated (IsDisposBoss): not "first", which would give away the boss's return, a later
    # arrival the spoiler block hides.
    for hd in ch.of_kind(E.AREA):
        if ch.string(hd['args'][5]) == 'IsDisposBoss':
            tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if g[y][x] == BARRIER]
            if tiles:
                groups = dict(D.dispos(src.file, src.base))
                boss = next((unit_name(src, u['pid']) for gr in groups.values() for u in gr if u['boss']), 'the boss')
                out.append({'id': f'{mid}-barrier', 'trigger': 'event', 'tile': {'default': to_app(*tiles[0], h)}, 'usableBy': '',
                            'effect': f'The barrier of light falls once {boss} is defeated.',
                            'patch': [{'tile': to_app(x, y, h), 'becomes': '.'} for x, y in tiles]})
    # Walls a turn flips, and tiles a turn sets.
    walls = {}  # wall corner -> open now
    for hd in sorted(ch.of_kind(E.TURN, E.TURN2), key=lambda hd: (hd['args'][0], hd['args'][2])):
        found = [t for t in E.tricks(ch, hd) if None not in t[:4]]
        states = defaultdict(set)
        for x, y, kind, state, _ in found:
            if kind == 22:
                states[(x, y)].add(state)
        flips = [c for c, st in states.items() if st >= {1, 2}]
        sets = [(c, min(st)) for c, st in states.items() if len(st) == 1]
        if flips:
            opened, closed = [], []
            for c in flips:
                now = walls.get(c, load_state.get(c) == 2)
                walls[c] = not now
                (opened if walls[c] else closed).append(c)
            changed = [c for c, op in walls.items() if op != (load_state.get(c) == 2)]
            parts = ([f'{where(opened, h)} open' if opened else ''] + [f'{where(closed, h)} close' if closed else ''])
            out.append({'id': f'{mid}-walls-{hd["args"][0]}', 'trigger': 'event', 'tile': {'default': to_app(*flips[0], h)}, 'usableBy': '',
                        'effect': f'At the start of {when_text(hd)} the walls at ' + ', and those at '.join(x for x in parts if x) +
                                  ' (the preview shows the walls as that turn leaves them).',
                        'patch': [{'tile': to_app(tx, ty, h), 'becomes': LETTER[trick_terrain(original[ty][tx], 2 if walls[c] else 1)]}
                                  for c in changed for tx, ty in trick_tiles(*c, 22, models)]})
        for c, state in sets:
            cells = [t for t in trick_tiles(*c, 22, models) if playable(*t, w, h)]
            new = [(t, LETTER[trick_terrain(original[t[1]][t[0]], state)]) for t in cells]
            new = [(t, letter) for t, letter in new if letter != LETTER[g[t[1]][t[0]]]]
            if new:
                out.append({'id': f'{mid}-tiles-{c[0]}-{c[1]}', 'trigger': 'event', 'tile': {'default': to_app(*new[0][0], h)}, 'usableBy': '',
                            'effect': f'At the start of {when_text(hd)} {where([t for t, _ in new], h)} become impassable to every unit.'
                                      if all(letter == '#' for _, letter in new) else f'Changes at the start of {when_text(hd)}.',
                            'patch': [{'tile': to_app(*t, h), 'becomes': letter} for t, letter in new]})
    # A village a turn-1 choice closes: each ev::TrickSet under the offer of the boss whose PID the handler names last before it.
    for hd in ch.of_kind(E.TURN):
        if hd['args'][:3] != (1, 1, 0) or not ch.calls(hd, 'ev::DialogYesNo'):
            continue
        asker, by = None, defaultdict(list)
        ins = hd['ins']
        local = {}
        for k, (_, n, a) in enumerate(ins):
            if n == 'str' and a.strip("'").startswith('PID_'):
                p = person(src, a.strip("'"))
                if p and p['raw'][0x46] == 2:
                    asker = a.strip("'")
            if n == 'assign' and k >= 2 and ins[k - 2][1] == 'load' and ins[k - 1][1] == 'int':
                local[int(ins[k - 2][2], 16)] = ins[k - 1][2]
            if n == 'call' and a.startswith('ev::TrickSet') and k >= 4 and ins[k - 2][2] == 8 and ins[k - 1][2] == 2:
                xy = [local.get(int(ins[j][2], 16)) if ins[j][1] == 'var' else ins[j][2] if ins[j][1] == 'int' else None for j in (k - 4, k - 3)]
                if asker and None not in xy and tuple(xy) not in by[asker]:
                    by[asker].append(tuple(xy))
        for asker, villages in by.items():
            name = unit_name(src, asker)
            out.append({'id': f'{mid}-choice-{name.lower()}', 'trigger': 'event', 'tile': {'default': to_app(*villages[0], h)}, 'usableBy': '',
                        'effect': f"The villages at {where(villages, h)} close on turn 1 if you accept {name}'s offer.",
                        'patch': [{'tile': to_app(*v, h), 'becomes': LETTER[trick_terrain(original[v[1]][v[0]], 2)]} for v in villages]})
    # A village a visit brings up (the flag its visit sets, read by the every-turn handler).
    setters = {f: hd for hd in ch.ths if hd['k'] == E.TILE for f in E.flags_set(hd)}
    for hd in ch.of_kind(E.REINFORCE):
        for flag, found in E.tricks_by_flag(ch, hd).items():
            for x, y, kind, state in found:
                if kind == 8 and state == 1 and load_state.get((x, y)) == 2:
                    by = setters.get(flag)
                    gives = [item_name(i) for i, _ in E.item_gains(next(t for t in ch.ths if t['k'] == E.TILE and t['args'][:2] == (x, y)))]
                    after = f' once the village at {where([by["args"][:2]], h)} is visited' if by else f' once flag {flag} is set'
                    out.append({'id': f'{mid}-village-{x}-{y}', 'trigger': 'event', 'tile': {'default': to_app(x, y, h)}, 'usableBy': '',
                                'effect': f'A village appears here at the start of the next turn{after}' +
                                          (f'; visiting it gives {article(gives[0])}' if gives else '') + ', and it turns to desert once visited.',
                                'patch': [{'tile': to_app(x, y, h), 'becomes': LETTER[original[y][x]]}]})
    return out


def door_extras(ch, h, models):
    """{door tile: [words]} said on a door's preview: a turn that opens it by itself (Smash Brethren, The Future Past 1), and the walls
    the flag its opening sets brings down (Paralogue 16: the every-turn handler opens them once the flag is up). Each with the extra
    tiles to patch: {door: (words, [(tile, state)])}."""
    out = defaultdict(lambda: ([], []))
    for hd in ch.of_kind(E.TURN, E.TURN2):
        for x, y, kind, state, _ in E.tricks(ch, hd):
            if kind == 14 and state == 2 and None not in (x, y):
                words = f'It opens by itself at the start of {when_text(hd)}.'
                if words not in out[(x, y)][0]:
                    out[(x, y)][0].append(words)
    by_flag = {}
    for hd in ch.hs:
        for flag, found in E.tricks_by_flag(ch, hd).items():
            by_flag.setdefault(flag, []).extend(t for t in found if t not in by_flag.get(flag, []))
    for hd in ch.ths:
        if hd['k'] != E.TILE or hd['args'][2] != 14:
            continue
        opened = [(x, y) for f in E.flags_set(hd) for x, y, kind, state in by_flag.get(f, []) if kind == 22 and state == 2]
        if opened:
            door = tuple(hd['args'][:2])
            out[door][0].append(f'Opening it also brings down the walls at {where(opened, h)} for good.')
            out[door][1].extend((t, 2) for c in opened for t in trick_tiles(*c, 22, models))
    return out


def ins_str(x):
    return x[1] == 'str'


POST = 0x0b  # the post-battle handler (ChapterSetNextIncrement): with 0x0a, the chapter's end


def gift_conditions(ch, hd, src):
    """{iid: words} for the gifts a handler gives only on a condition: each gift is under the checks whose jump (jz) it sits inside, a
    count at or above a number (the green units left, VariableGet('緑軍生存数'); a PID's units left, ForceUnitGetCountPID; a unit's
    kills, UnitGetRecordKill) or a unit alive (UnitIsAlive). A check that guards only a scene or a join before the gifts (Paralogue
    22's, Paralogue 12's) doesn't count. A gift ev::ItemGain or ItemGainSilent hands a unit it names (not the talker, MindGetUnit) is
    said to go to it."""
    ins = hd['ins']
    var_pid, counts, pending, guards, out = {}, {}, None, [], {}
    for k, (pc, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::UnitGetByPID') and k >= 2 and ins[k - 2][1] == 'load' and ins[k - 1][1] == 'str':
            var_pid[ins[k - 2][2]] = ins[k - 1][2].strip("'")
        elif n == 'call' and a.split('/')[0] in ('ev::VariableGet', 'ev::ForceUnitGetCountPID', 'ev::UnitGetRecordKill'):
            # The count goes into the local the nearest load before the call names.
            into = next((ins[j][2] for j in range(k - 1, max(k - 5, -1), -1) if ins[j][1] == 'load'), None)
            if a.startswith('ev::VariableGet') and ins[k - 1][2] == "'緑軍生存数'":
                counts[into] = ('green', None)
            elif a.startswith('ev::ForceUnitGetCountPID') and ins[k - 1][1] == 'str':
                counts[into] = ('units', unit_name(src, ins[k - 1][2].strip("'")))
            elif a.startswith('ev::UnitGetRecordKill') and ins[k - 1][1] == 'var' and ins[k - 1][2] in var_pid:
                counts[into] = ('kills', unit_name(src, var_pid[ins[k - 1][2]]))
        elif n == 'call' and a.startswith('ev::UnitIsAlive') and ins[k - 1][1] == 'var' and ins[k - 1][2] in var_pid:
            pending = ('alive', unit_name(src, var_pid[ins[k - 1][2]]))
        elif n in ('ge', 'gt') and ins[k - 1][1] == 'int' and ins[k - 2][1] == 'var' and ins[k - 2][2] in counts:
            pending = ('count', ins[k - 2][2], ins[k - 1][2] + (1 if n == 'gt' else 0))
        elif n == '?32':
            pending = None
        elif n == 'jz':
            if pending:
                guards.append((pending, pc, a))
            pending = None
        elif n == 'call' and a.startswith('ev::ItemGain') and ins[k - 1][1] == 'str':
            under = [g for g, start, end in guards if start < pc < end]
            alive = [g[1] for g in under if g[0] == 'alive']
            top = {}
            for g in under:
                if g[0] == 'count':
                    top[g[1]] = max(top.get(g[1], 0), g[2])
            clauses = []
            for var, n_ in top.items():
                kind, who = counts[var]
                if kind == 'kills':
                    clauses.append(f'{who} defeats {n_} or more foes' + (' and survives' if who in alive else ''))
                    alive = [x for x in alive if x != who]
                elif kind == 'green':
                    clauses.append(f'{n_} or more green units survive')
                else:
                    clauses.append(f'{n_} or more {who.lower()}s survive')
            clauses = [f'{x} is alive' for x in dict.fromkeys(alive)] + clauses
            words = [f"if {' and '.join(clauses)}"] if clauses else []
            if ins[k - 2][1] == 'var' and ins[k - 2][2] in var_pid:
                words.append(f'to {unit_name(src, var_pid[ins[k - 2][2]])}')
            out[ins[k - 1][2].strip("'")] = ', '.join(words)
    return out


def gold_rewards(ch, hd, src, h):
    """['10,000 gold if you turn both offers down', 'otherwise 500 gold for each green unit that survives']: what a handler's
    ev::GoldGain(0, n) gives, a flat sum or one for each unit a count counts (var * n), each under the flag it checks first (what sets
    it) or, past that branch's jmp, 'otherwise'."""
    ins = hd['ins']
    at = {pc: j for j, (pc, _, _) in enumerate(ins)}
    pending, guards, counts, out = None, [], {}, []
    for k, (pc, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::FlagGet') and ins[k - 1][1] == 'str':
            pending = flag_cause(ch, ins[k - 1][2].strip("'"), h, src)
        elif n == 'call' and a.startswith('ev::VariableGet') and ins[k - 1][2] == "'緑軍生存数'":
            into = next((ins[j][2] for j in range(k - 1, max(k - 5, -1), -1) if ins[j][1] == 'load'), None)
            counts[into] = 'green unit that survives'
        elif n == 'jz':
            if pending:
                guards.append((f'if {pending}', pc, a))
                j = at.get(a)
                if j and ins[j - 1][1] == 'jmp' and ins[j - 1][2] > a:
                    guards.append(('otherwise', a - 1, ins[j - 1][2]))
            pending = None
        elif n == 'call' and a.startswith('ev::GoldGain'):
            if ins[k - 1][1] == 'int':
                total = f'{ins[k - 1][2]:,} gold'
            elif ins[k - 1][1] == 'mul' and ins[k - 2][1] == 'int' and ins[k - 3][1] == 'var' and ins[k - 3][2] in counts:
                total = f'{ins[k - 2][2]:,} gold for each {counts[ins[k - 3][2]]}'
            else:
                continue
            under = [w for w, start, end in guards if start < pc < end]
            out.append(f'otherwise {total}' if under and under[-1] == 'otherwise' else ' '.join([total] + under[-1:]))
    return out


def article(name):
    return ('an ' if name[0].lower() in 'aeiou' else 'a ') + name


def renown_rewards():
    """OtherData's renown rewards (名声アイテム, up to the next label): each a pointer to the item's Japanese name (its IID without the
    prefix) followed by the renown it needs."""
    b = D.load('data/OtherData.bin.lz')
    start = b.at['名声アイテム']
    end = min(o for o, n in b.labels if o > start)
    out = []
    for o in range(start + 4, end, 4):
        if o in b.ptrs and b.str(o):
            out.append((b.str(o), b.u32(o + 4)))
    return out


def main():
    global GENERIC_LABELS, ARMY_LABELS, FACELESS
    GENERIC_LABELS, ARMY_LABELS, FACELESS = generic_labels()
    info, groups = build_terrain()
    # A plain its art draws as dirt (art_ground) works as a plain.
    info['ga'] = {**info[encode(GAME, '.')], 'name': 'Plain'}
    info['t2'] = {**info[encode(GAME, '.')], 'name': 'Plain'}  # a snowy map's snow (fe13_ground's dirtAs)
    info['gb'] = {**info[encode(GAME, '.')], 'name': 'Plain'}  # a town's cobbled streets (PAVED)
    info['t3'] = {**info[encode(GAME, 'O')], 'name': 'Floor'}  # a ship's deck (map_pieces.ship_decks)
    info['t4'] = {**info[encode(GAME, 'O')], 'name': 'Floor'}  # a port's cobbled floor (PAVED_FLOORS)
    # A village's house drawn whole over its building (map_pieces.village_houses) works as the walls it stands for.
    for p in 'abcdefghijklmnopqr':
        info['r' + p] = {**info[encode(GAME, '0')], 'name': 'House'}
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, {i: c['name'] for i, c in enumerate(D.classes())})
    by_index = {it['index']: it for it in D.items()}
    sources = defaultdict(list)
    held = defaultdict(set)  # (item, map id, kind, text) -> the difficulties the line holds on

    def add(name, mid, kind, text, ds=None):
        """`ds`: the difficulties of the placed unit the line comes from (None: all three, as for anything else)."""
        if not name:
            return
        if {'mapId': mid, 'kind': kind, 'text': text} not in sources[name]:
            sources[name].append({'mapId': mid, 'kind': kind, 'text': text})
        held[(name, mid, kind, text)] |= set(E.DIFFS if ds is None else ds)

    maps, joined, skirmishes = [], set(), []
    first_tiles = None
    for key in STORY + PARALOGUES + DLC:
        facts = defaultdict(list)
        m = build_map(key, facts)
        mid = m['id']
        dlc = key.startswith('E')
        pre = 'dlc-' if dlc else ''
        c = CHAPTERS.get(key)
        if c and not dlc:
            # The location's shop opens once its battle is won and stays open (any time you're on the world map).
            for idx in c['shop']:
                add(D.item_name(by_index[idx]), mid, 'town-shop-later', f"Sold at the shop in {c['location']}")
            for idx in c['merchant']:
                if idx == D.RARE:
                    continue
                add(D.item_name(by_index[idx]), mid, 'merchant-later',
                    f"Sometimes sold by a travelling merchant in {c['location']}")
            if D.RARE in c['merchant'] and key == 'P002':
                for iid in D.rare_items():
                    add(item_name(iid), mid, 'merchant-later', 'Sometimes sold by a travelling merchant anywhere (a rare item)')
        for name in facts['chests']:
            add(name, mid, pre + 'chest', 'In a chest')
        for name in facts['hidden']:
            add(name, mid, pre + 'hidden', 'Hidden on the map')
        for name in facts['villages']:
            add(name, mid, pre + 'village', 'Given at a village')
        # A random village or chest gives each item of its pool with its chance.
        for kind, where, what in (('village', 'random_villages', 'Sometimes given at a village'), ('chest', 'random_chests', 'Sometimes in a chest')):
            for r in dict.fromkeys(facts[where]):
                pool = D.random_pool(r == 'limit')
                total = sum(w for _, w in pool)
                for it, w in pool:
                    add(D.item_name(it), mid, pre + kind, f'{what} ({percent(100 * w / total)})')
        for who, carries, drops, later, generic, ds in facts['carries']:
            whom = f'a foe {who}' if generic else who
            for name in drops:
                add(name, mid, pre + ('drop-later' if later else 'drop'), f'Dropped by {whom}', ds)
            for name in carries:
                if name not in drops:
                    add(name, mid, pre + ('foe-later' if later else 'foe'), f'Carried by {whom}', ds)
        for carries, drops, ds in facts['random']:
            for name in drops:
                add(name, mid, 'dlc-drop', 'Dropped by one of the foes the game picks at random', ds)
            for name in carries:
                if name not in drops:
                    add(name, mid, 'dlc-foe', 'Carried by one of the foes the game picks at random', ds)
        for iid, later, text in facts['gifts']:
            add(item_name(iid), mid, pre + ('gift-later' if later else 'gift'), text)
        # Who joins for the first time here, and whether at the end of the chapter: each of their records counts (a recruit can
        # have one per difficulty), as long as it joins the way the first one does.
        here = {}
        for pid, iids, later, ds in facts['joins']:
            if pid in joined or dlc or here.setdefault(pid, later) != later:
                continue
            who = unit_name(Source(key), pid)
            who = 'the Avatar' if who == 'Avatar' else who
            for iid in iids:
                add(item_name(iid), mid, 'kit-later' if later else 'kit', f'Carried by {who} when they join', ds)
        joined |= set(here)
        if facts['event_tiles'] and first_tiles is None and not dlc:
            first_tiles = mid
        maps.append({k: v for k, v in m.items() if v is not None})
        if not dlc:
            sk = skirmish_map(key, m)
            if sk:
                skirmishes.append(sk)
    # Event tiles give a random item from the ones the game marks as such (item +4's 0x02: sold for a quarter of their worth).
    for it in D.items():
        if it['flags'][4] & 0x02:
            add(D.item_name(it), first_tiles, 'event-tile', 'A random find on an event tile')
    for jp, renown in renown_rewards():
        add(item_name('IID_' + jp), map_id('P002'), 'renown', f'Renown reward ({renown:,} renown)')
    gm.write_maps(GAME, TITLE, SCRIPT, [encode_grid(m) for m in maps + skirmishes])
    gm.mark_difficulties(sources, held, {m['id']: E.DIFFS for m in maps})
    gm.write_sources(GAME, TITLE, SCRIPT, sources, prefixes=('dlc-',), diffs=E.DIFFS)
    # When each side map opens: the story chapter whose clearing opens it (GameData's chapter record +20).
    opens = {}
    for key in PARALOGUES + DLC:
        after = CHAPTERS['E000' if key.startswith('E') else key]['after']
        opens[map_id(key)] = map_id(after)
    # A skirmish comes once its location is reached: a chapter's once the chapter is cleared, a paralogue's with the paralogue.
    for sk in skirmishes:
        base = sk['skirmishOf']
        opens[sk['id']] = opens.get(base, base)
    gm.write(GAME, f'{GAME}Opens.ts', [
        '/*',
        f" * GENERATED by scripts/{SCRIPT} from {TITLE}'s chapter list (data/GameData.bin). Do not edit by hand.",
        ' */',
        '',
        '/** Each paralogue and DLC map, and the story chapter whose clearing opens it. */',
        f'export const FE13_OPENS: Record<string, string> = {json.dumps(opens, indent=2)}',
    ])
    print('wrote', len(maps), 'maps and the sources of', len(sources), 'items')


def skirmish_map(key, base):
    """A world-map skirmish at a chapter's location (scripts/Encount.cmb): the chapter's own grid (TerrainLoad(ChapterGetName()):
    none of the chapter's load changes), its encounter placement file (<key>E: DisposLoad(ChapterGetEncountName())), whose Player
    group gives the start tiles, and two slots: each is its group of Risen (Mob00, Mob01) or, where the world map's encounter makes
    that slot a trader (ChapterIsMobDisposTrader: type 3), the Trader group. Every unit in them is a dummy the game fills."""
    path = os.path.join(ROMFS, 'data', 'dispos', key + 'E.bin.lz')
    if not os.path.exists(path):
        return None
    w, h, tiles = D.grid(key)
    groups = dict(D.dispos(key + 'E'))
    tile = lambda u: to_app(*u['end'], h)  # noqa: E731
    starts = [tile(u) for u in groups.get('Player', []) if playable(*u['end'], w, h)]
    labels = ['Group 1', 'Group 2']
    foe_groups = [{'label': labels[i], 'tiles': [tile(u) for u in groups.get(g, []) if playable(*u['end'], w, h)]}
                  for i, g in enumerate(('Mob00', 'Mob01'))]
    trader = [tile(u) for u in groups.get('Trader', []) if playable(*u['end'], w, h)]
    units = [{'type': 'enemy', 'name': 'Random foe', 'tile': t, 'note': f"One of {g['label']}'s Risen can stand here (the game picks them)."}
             for g in foe_groups for t in g['tiles']]
    units += [{'type': 'ally', 'name': 'Merchant', 'tile': t, 'generic': True,
               'note': "The travelling merchant's tiles, used in place of a group when the world map puts a merchant here."}
              for t in trader]
    location = CHAPTERS.get(key, {}).get('location') or base['title']
    out = {
        'id': f"{base['id']}-skirmish", 'route': 'Skirmish', 'chapter': base['chapter'], 'title': location,
        'skirmishOf': base['id'], 'width': w - 2, 'height': h - 2, 'grid': grid_rows(w, h, tiles),
        'victory': 'Rout the enemy', 'defeat': 'Chrom or the Avatar is defeated', 'objectives': [], 'units': units,
        'foeGroups': foe_groups, 'starts': starts, 'objects': [], 'changes': [],
        'notes': [
            'A skirmish the world map brings here: the game picks its Risen each time (their classes, levels, items and how many), '
            'and they come as one group or two, on the outlined tiles.',
            "When the world map puts a travelling merchant here instead of one of the groups, the merchant takes the merchant's tiles; "
            'if the merchant survives, you get a token of thanks.',
            'Routing two groups of Risen gets a reward from the villagers.',
            "The map is the chapter's own grid, as its terrain file lays it out: none of the chapter's own changes are made.",
        ],
        'unconfirmed': [
            "How many of a group's tiles the Risen fill, and how strong they are: the world map's encounter decides, not traced.",
            "Whether the merchant stands on one of its tiles or a party fills them, and whether the chapter's villages and chests "
            'work in a skirmish.',
        ],
    }
    names = tile_names(tiles, w, h)
    if names:
        out['terrainOverrides'] = names
    return out


def percent(p):
    """'0.5%', '3.2%', '10%': a chance as the weapon page says it."""
    return f'{p:.1f}'.rstrip('0').rstrip('.') + '%'


# Each map's ground from its 3D scene (scripts/fe13_ground.py, which renders them: data-raw/fe13-ground.json): its colours per code
# and the plain tiles its art draws as dirt, those drawn as dirt but still named as the game names them (scripts/art_ground.py).
GROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe13-ground.json')
GAME_CODES = {k: encode(GAME, k) for k in LETTER_NAME}


def own_name(code):
    return 'Plain' if code in ('ga', 't2', 'gb') else LETTER_NAME[next(k for k, v in GAME_CODES.items() if v == code)]


# The towns whose paler ground is their streets' cobbles, not dirt (the user's calls, the review of every map: the Prologue's,
# Southtown's, the capital's, Plegia's and the port's roads), drawn as paving with the plain's numbers; a skirmish on one shares it.
PAVED = {'fe13-prologue', 'fe13-1', 'fe13-2', 'fe13-3', 'fe13-9', 'fe13-12', 'fe13-22'}
PAVED_FLOORS = {'fe13-12'}


def encode_grid(m):
    m['grid'] = [''.join(encode(GAME, c) for c in row) for row in m['grid']]
    m['terrainOverrides'] = {encode(GAME, k): v for k, v in (m.get('terrainOverrides') or {}).items()}
    g = art_ground.table(GROUND).get(m['id'])
    if g and m['id'].replace('-skirmish', '') in PAVED and 'dirtAs' not in g:
        g = dict(g, dirtAs='gb', fills={('gb' if k == 'ga' else k): v for k, v in g['fills'].items()})
    art_ground.apply(m, g, own_name)
    # A building over a village is the village's house, drawn whole (map_pieces.village_houses: the user, Chapter 8's villages); a
    # ship's floor its deck (map_pieces.ship_decks: the user, wood for a ship's deck).
    m['grid'] = map_pieces.ship_decks(map_pieces.village_houses(m['grid'], ('w0', 'wa')))
    if 't1' in (m.get('fills') or {}) and any('t3' in r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)):
        m['fills']['t3'] = m['fills']['t1']
    # A port's floor its cobbles (the user's call: Chapter 12's quay), with the floor's numbers.
    if m['id'].replace('-skirmish', '') in PAVED_FLOORS:
        m['grid'] = [''.join('t4' if r[i:i + 2] == 't1' else r[i:i + 2] for i in range(0, len(r), 2)) for r in m['grid']]
        if 't1' in (m.get('fills') or {}):
            m['fills']['t4'] = m['fills']['t1']
    if not m['terrainOverrides']:
        m.pop('terrainOverrides')
    for c in m.get('changes', []):
        for p in c.get('patch', []):
            p['becomes'] = encode(GAME, p['becomes'])
    return m


if __name__ == '__main__':
    main()
