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

GAME, TITLE, SCRIPT = 'fe13', 'Awakening', 'build-fe13-maps.py'
DLC_ROOT = os.path.join(ROMFS, 'dlc')

# Terrain id -> builder letter (terrain_codes.py's 'fe13'), by how the game treats each: its stats and movement column.
LETTER = {
    0: '#', 1: '.', 2: '.', 3: 'f', 4: 's', 5: 's', 6: 'm', 7: 'C', 8: 'C', 9: 'C', 10: 'Z', 11: 'C', 12: 'C', 13: '#', 14: 'b', 15: 'b',
    16: 'w', 17: 'a', 18: 'a', 19: 'F', 20: 'g', 21: '#', 22: 'v', 23: 'V', 24: '.', 25: 'v', 26: 'V', 27: '.', 28: 'C', 29: '#',
    30: '#', 31: 'r', 32: 'l', 33: '.', 34: 'S', 35: 'p', 36: 't', 37: 'l', 38: 'l', 39: 'l', 40: '#', 41: 'd', 42: 'd', 43: 'c',
    44: 'C', 45: 'X', 46: 'H', 47: 'M', 48: '#', 49: '#', 50: '#', 51: '.', 52: '.', 53: 'C', 54: 'v', 55: '#', 56: '.', 57: 'C',
    58: 'a', 59: '.', 60: '.', 61: 'f', 62: 'm', 63: 'b', 64: 'v', 65: 'V', 66: '.', 67: 'd', 68: 'b', 69: '.', 70: 'a',
}
# What the panel calls each letter (the game's own names, merged where the game treats them the same).
LETTER_NAME = {
    '.': 'Plain / floor', 'b': 'Bridge', 'f': 'Woods', 's': 'Desert / beach', 'm': 'Mountain', 'w': 'River', 'a': 'Sea / lake',
    'Z': 'Sky', 'M': 'Lava', 'F': 'Fort', 'g': 'Gate', 't': 'Throne', 'S': 'Stairs', 'p': 'Pillar', 'v': 'Village / house',
    'V': 'Closed village / house', 'd': 'Door', 'c': 'Chest', 'C': 'Cliff / peak / building', 'r': 'Rubble',
    'l': 'Fence / partition / supplies', '#': 'Wall', 'X': 'Lava floor', 'H': 'Hazard',
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
        if letter == 'H':
            entry['note'] = 'Damages a unit standing on it (its terrain flag 0x20).'
        if letter == 'X':
            entry['note'] = 'Chapter 18: islets of it turn to hazard terrain on set turns (tap a flame).'
        if all(v is None for v in move.values()):
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
    return e


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


def flag_cause(ch, flag, h, src):
    """'the village at (18, 16) is visited', 'Severa talks to Holland or Severa turns against you': what sets a flag, from the handlers
    that set it; None where nothing readable does."""
    out = []
    for hd in ch.hs + ch.ths:
        if flag not in E.flags_set(hd):
            continue
        k, args = hd['k'], hd['args']
        if k == E.TILE:
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
    flags, asker = [], None
    tiles, count = [], None
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::FlagGet') and ins[k - 1][1] == 'str':
            flags.append(ins[k - 1][2].strip("'"))
        elif n == 'str' and a.strip("'").startswith('PID_') and ch.calls(hd, 'ev::DialogYesNo'):
            p = person(src, a.strip("'"))
            if p and p['raw'][0x46] == 2:
                asker = a.strip("'")
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
            if group in out:
                continue
            ends = {tuple(u['end']) for u in groups.get(group, [])}
            if asker:
                out[group] = f"if you accept {unit_name(src, asker)}'s offer"
            elif tiles and ends and set(tiles[1:]) == ends:
                out[group] = 'unless your units stand on all of its arrival tiles'
            elif count is not None:
                out[group] = f'once fewer than {count} foes are left'
            else:
                # The first flag read with a readable cause (a later one can be the handler's own once-only latch).
                cause = next((c for c in (flag_cause(ch, f, h, src) for f in flags) if c), None)
                if cause:
                    out[group] = f'after {cause}'
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
    if losers:
        m['defeat'] = 'Chrom, the Avatar' + ''.join(f', {n}' for n in losers[:-1]) + f' or {losers[-1]} is defeated'
    for hd in ch.of_kind(E.AREA):
        if ch.string(hd['args'][5]) == 'CantDoorOpen':
            m['defeat'] += ', or the door keys are lost before a door is opened'
    units, starts, forced = [], [], []
    lord = None
    # Units the opening (turn 1's player-phase handlers) takes off the map before the battle (Chapter 9's Gangrel and Aversa).
    left = set()
    for hd in ch.of_kind(E.TURN, E.TUTORIAL):
        if hd['args'][:1] == (1,) and (len(hd['args']) < 3 or hd['args'][2] == 0):
            left |= set(E.removed_pids(ch, hd))
    for group in at_start:
        for u in groups.get(group, []):
            if u['team'] == 0 and key != 'P001':
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], False, u['difficulties']))
            if group == 'Player':
                tile = to_app(*u['end'], h)
                starts.append(tile)
                if u['pid'] == 'PID_クロム':
                    lord = tile
                if u['flags'] & 0x02:
                    forced.append({'name': display_name(src, u['pid']), 'tile': tile})
                continue
            if not playable(*u['end'], w, h) or u['pid'] in left:
                continue
            units.extend(unit_entries(src, u, h))
    for group in random_spots:
        for u in groups.get(group, []):
            if playable(*u['end'], w, h):
                units.append(with_difficulties(u, {'type': 'enemy', 'name': 'Random foe', 'tile': to_app(*u['end'], h),
                                                   'note': 'The game picks this foe at random as the map loads.'}))
    if rule == 0x40000:
        bosses = [u['name'] for u in units if u['type'] == 'boss']
        if bosses:
            m['victory'] = f'Defeat {bosses[0]}'
    m['objectives'] = []
    units = merge_same(units)
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
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], False, u['difficulties']))
            if u['team'] == 2:
                j['ally'] = True
            joiners.append(j)
    if reinforcements:
        m['reinforcements'] = one_per_arrival(reinforcements)
    if joiners:
        m['joiners'] = joiners
    # Talks: a target the talk hands over (UnitTransferByIndex) is recruited by its talker.
    talks = defaultdict(list)
    for hd in ch.of_kind(E.TALK):
        talker, target = ch.string(hd['args'][0]), ch.string(hd['args'][1])
        if target in E.recruits(ch, hd):
            talks[target].append(unit_name(src, talker))
    for e in units + joiners + [u for g in reinforcements for u in g['units']]:
        if e.get('_pid') in talks:
            e['talk'] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(talks[e['_pid']]))
            if e.get('type') in ('enemy', 'named', 'boss', 'ally'):
                facts['joins'].append((e['_pid'], groups_items(groups, e['_pid']), False, e.get('difficulties')))
    # After the battle: units the end of the chapter places on your side join then (Chapter 4's Lon'qu, Chapter 7's Cordelia).
    for hd in ch.of_kind(E.END):
        for di in range(3):
            for group, cond in E.run(ch.s, hd, di, 99):
                for u in groups.get(group, []):
                    if u['team'] == 0 and u['pid'] not in E.removed_pids(ch, hd) and E.DIFFS[di] in u['difficulties']:
                        facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], True, [E.DIFFS[di]]))
    # Gifts the story hands over in the chapter's own script (the end of Chapter 24's Exalted Falchion, a DLC map's reward).
    for hd in ch.hs:
        for iid, pids in E.item_gains(hd):
            facts['gifts'].append((iid, hd['k'] == E.END, pids))
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
    if key == 'E027':
        m['unconfirmed'] = ['The Fire Emblem Wiki says the map is also lost if the green Lucina falls; nothing in its files says so.']
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
            if TERRAINS[tiles[y][x]]['becomes'] == 4:
                # A phantom village (TerrainData +12 desert): gone once visited.
                m['objects'][-1]['note'] = 'It turns to desert once visited.'
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
    for e in units + joiners + [u for g in reinforcements for u in g['units']]:
        e.pop('_pid', None)
        e.pop('_generic', None)
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
    # Chapter 23's barrier.
    for hd in ch.of_kind(E.AREA):
        if ch.string(hd['args'][5]) == 'IsDisposBoss':
            tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if g[y][x] == BARRIER]
            if tiles:
                out.append({'id': f'{mid}-barrier', 'trigger': 'event', 'tile': {'default': to_app(*tiles[0], h)}, 'usableBy': '',
                            'effect': 'The barrier of light falls once Validar is first defeated.',
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

    maps, joined = [], set()
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
        for iid, end, pids in facts['gifts']:
            text = 'Given at the end of the chapter' if end else 'Given in the chapter'
            add(item_name(iid), mid, pre + ('gift-later' if end else 'gift'), text)
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
    # Event tiles give a random item from the ones the game marks as such (item +4's 0x02: sold for a quarter of their worth).
    for it in D.items():
        if it['flags'][4] & 0x02:
            add(D.item_name(it), first_tiles, 'event-tile', 'A random find on an event tile')
    for jp, renown in renown_rewards():
        add(item_name('IID_' + jp), map_id('P002'), 'renown', f'Renown reward ({renown:,} renown)')
    gm.write_maps(GAME, TITLE, SCRIPT, [encode_grid(m) for m in maps])
    gm.mark_difficulties(sources, held, {m['id']: E.DIFFS for m in maps})
    gm.write_sources(GAME, TITLE, SCRIPT, sources, prefixes=('dlc-',), diffs=E.DIFFS)
    # When each side map opens: the story chapter whose clearing opens it (GameData's chapter record +20).
    opens = {}
    for key in PARALOGUES + DLC:
        after = CHAPTERS['E000' if key.startswith('E') else key]['after']
        opens[map_id(key)] = map_id(after)
    gm.write(GAME, f'{GAME}Opens.ts', [
        '/*',
        f" * GENERATED by scripts/{SCRIPT} from {TITLE}'s chapter list (data/GameData.bin). Do not edit by hand.",
        ' */',
        '',
        '/** Each paralogue and DLC map, and the story chapter whose clearing opens it. */',
        f'export const FE13_OPENS: Record<string, string> = {json.dumps(opens, indent=2)}',
    ])
    print('wrote', len(maps), 'maps and the sources of', len(sources), 'items')


def percent(p):
    """'0.5%', '3.2%', '10%': a chance as the weapon page says it."""
    return f'{p:.1f}'.rstrip('0').rstrip('.') + '%'


def encode_grid(m):
    m['grid'] = [''.join(encode(GAME, c) for c in row) for row in m['grid']]
    for c in m.get('changes', []):
        for p in c.get('patch', []):
            p['becomes'] = encode(GAME, p['becomes'])
    return m


if __name__ == '__main__':
    main()
