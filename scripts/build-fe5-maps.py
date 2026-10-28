"""
Builds Thracia 776's maps from the user's clean ROM (scripts/fe5_rom.py), named from Lil' Manster (scripts/fe5_names.py):
  src/data/fe5/fe5Terrain.ts      terrain stats and movement costs, from the game's own tables
  src/data/fe5/fe5Maps.ts         every chapter's map, units, reinforcements, villages, chests, doors, shops and objectives
  src/data/fe5/fe5ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe5-maps.py

The chapters' scripts are played by scripts/fe5_events.py. Formats are in data-raw/fe5/README.md. Coordinates: the game counts from
(0, 0) at the top left, and the cursor never reaches column 0 or row 0 ($83:BDD8: a move onto either is refused), so the playable map
is the stored one without them; the app counts from (1, 1) at the bottom left.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe5_events as fe  # noqa: E402
import fe5_rom as r  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe5_names import character_names, class_names, generic_names, item_names, patched  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe5', 'Thracia 776', 'build-fe5-maps.py'
R = r.R
NAMES = character_names()
CLASSES = class_names()
ITEMS = item_names()
LEIF, CED = 0x01, 0x45  # Ced's Chapter 23 self (the death that loses the game there: the quote handler, $99:807C)

# Chapter index -> heading. The order is the chapter records' and the end scripts' (each adds to the chapter number to skip a
# gaiden chapter, or to take 16B and 17B).
HEADINGS = ['Ch.1', 'Ch.2', 'Ch.2x', 'Ch.3', 'Ch.4', 'Ch.4x', 'Ch.5', 'Ch.6', 'Ch.7', 'Ch.8', 'Ch.8x', 'Ch.9', 'Ch.10', 'Ch.11',
            'Ch.11x', 'Ch.12', 'Ch.12x', 'Ch.13', 'Ch.14', 'Ch.14x', 'Ch.15', 'Ch.16A', 'Ch.17A', 'Ch.16B', 'Ch.17B', 'Ch.18', 'Ch.19',
            'Ch.20', 'Ch.21', 'Ch.21x', 'Ch.22', 'Ch.23', 'Ch.24', 'Ch.24x', 'Final']

# Terrain id -> (builder letter, name). Ids that work the same share a letter (terrain_codes.py 'fe5').
TERRAIN = {
    0: ('#', 'Map edge'), 1: ('P', 'Peak'), 2: ('k', 'Thicket'), 3: ('C', 'Cliff'), 4: ('.', 'Plain'), 5: ('f', 'Forest'),
    6: ('a', 'Sea'), 7: ('w', 'River'), 8: ('m', 'Mountain'), 9: ('y', 'Sand'), 10: ('#', 'Castle'), 11: ('F', 'Fort'),
    12: ('B', 'House'), 13: ('g', 'Gate'), 14: ('C', 'Outdoor wall'), 15: ('e', 'Wasteland'), 16: ('b', 'Bridge'), 17: ('u', 'Lake'),
    18: ('v', 'Village'), 19: ('n', 'Ruins'), 20: ('#', 'Wall'), 21: ('#', 'Roof'), 22: ('U', 'Supply'), 23: ('h', 'Church'),
    24: ('V', 'House (closed)'), 25: ('.', 'Road'), 26: ('W', 'Armory'), 27: ('I', 'Vendor'), 28: ('R', 'Arena'), 29: ('O', 'Floor'),
    30: ('#', 'Wall'), 31: ('t', 'Throne'), 32: ('d', 'Door'), 33: ('c', 'Chest'), 34: ('.', 'Exit'), 35: ('p', 'Pillar'),
    36: ('Z', 'Drawbridge'), 37: ('Q', 'Secret shop'), 38: ('r', 'Cracked wall'), 39: ('e', 'Sandy soil'), 40: ('A', 'Magic floor'),
    41: ('q', 'Magic seal'), 42: ('h', 'Church (closed)'), 43: ('K', 'Chest'),
}
HEALS = {11, 13, 23, 31, 42}       # +5 HP at the start of the turn ($83:836E): fort, gate, church, throne, closed church
MAGIC_TILES = {40, 41}             # +10 Magic (the terrain magic table)
VILLAGE, HOUSE, CHURCH = 18, 12, 23
SHOP_KINDS = {26: 'Armory', 27: 'Vendor', 37: 'Secret shop'}
# A class in each movement group (the classes whose cost rows are the same) -> the group's name. The ballisticians never move.
MOVE_NAMES = {0x01: 'Mounted', 0x07: 'Mounted (promoted)', 0x10: 'Fliers', 0x29: 'Infantry', 0x1A: 'Armours',
              0x22: 'Brigands & warriors', 0x21: 'Berserkers & hunters', 0x26: 'Pirates'}
# The dismounted forms of the mounted classes (VoltEdge VANILLA/Classes.h): infantry, but named like their mounted selves, so they're
# left out of the movement types' examples.
DISMOUNTED = {0x28, 0x2B, *range(0x42, 0x55), 0x56, 0x58, 0x5A, 0x5C, 0x5E, 0x60, 0x74}
INDOORS = 'Mounted units and fliers have to dismount to come indoors.'
PHASES = {0x00: 'your phase', 0x40: 'enemy phase', 0x80: "the other army's phase"}


def title_and_goals():
    """Lil' Manster's chapter titles and objectives: plain text at $01:C353 of the patched image (bank $01 is past the original
    4 MB), one string per line, ended by 0x01; an objective that doesn't end in a full stop runs on to the next line."""
    p = patched()
    o = 0x400000 + 0x8000 + (0xC353 & 0x7FFF)
    lines = [s.decode('latin-1').replace('®', 'ö') for s in p[o:o + 4000].split(b'\x01')]
    titles = [t.split(': ', 1)[1] for t in lines[:35]]
    goals, buf = [], ''
    for s in lines[35:]:
        buf = f'{buf} {s}'.strip()
        if buf.endswith('.'):
            goals.append(buf[:-1].replace(' AND ', ' and ').replace(' OR ', ' or '))
            buf = ''
        if len(goals) == 35:
            break
    return titles, goals


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def name_of(c):
    return NAMES.get(c, f'#{c}')


def is_generic(c):
    return name_of(c) in generic_names()


def to_app(xy, h):
    """A game tile (from (0, 0) at the top left, row and column 0 unplayable) -> the app's (from (1, 1) at the bottom left); h is
    the playable height."""
    return [xy[0], h + 1 - xy[1]]


def rect_to_app(x1, y1, x2, y2, h):
    return [x1, h + 1 - y2, x2, h + 1 - y1]


# --- terrain ---

def move_groups():
    groups = {}
    for c in range(1, 0x78):
        cl = r.class_(c)
        row = bytes(R[r.lo(cl['move_cost']):r.lo(cl['move_cost']) + 44])
        if set(row) == {255}:
            continue
        groups.setdefault(row, []).append(c)
    out = []
    for row, classes in groups.items():
        label = next((MOVE_NAMES[c] for c in classes if c in MOVE_NAMES), None)
        assert label, f'no name for the movement row of classes {classes}'
        out.append((label, classes, row))
    order = list(MOVE_NAMES.values())
    return sorted(out, key=lambda g: order.index(g[0]))


def terrain_info(used, groups):
    ground = r.class_(0x29)  # Lord: a ground class
    flier = r.class_(0x10)
    assert set(R[r.lo(flier['terrain_avoid']):r.lo(flier['terrain_avoid']) + 44]) == {0}
    info = {}
    for tid in sorted(used):
        letter, name = TERRAIN[tid]
        code = encode(GAME, letter)
        move = {label: (None if row[tid] == 255 else row[tid]) for label, _, row in groups}
        e = {'name': name, 'def': struct_s8(ground['terrain_def'] + tid), 'avo': struct_s8(ground['terrain_avoid'] + tid), 'heal': 0,
             'move': move}
        if all(v is None for k, v in move.items() if k != 'Fliers'):
            e['def'] = e['avo'] = 0
        if tid in HEALS:
            e['note'] = 'Restores 5 HP at the start of each turn.'
        if tid in MAGIC_TILES:
            e['note'] = 'Adds 10 to the Magic of a unit standing on it.'
        if move['Infantry'] is not None and move['Mounted'] is None and move['Fliers'] is None:
            e['note'] = (e.get('note', '') + ' ' + INDOORS).strip()
        if code in info:
            old = info[code]
            same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in e.items() if k != 'name'}
            nobody = all(v is None for v in move.values())
            assert same or nobody, (code, tid, old, e)
            if name.lower() not in old['name'].lower():
                old['name'] += ' / ' + name.lower()
        else:
            info[code] = e
    return info


def struct_s8(a):
    v = r.u8(a)
    return v - 256 if v > 127 else v


# --- the chapter ---

class Chapter:
    def __init__(self, n):
        self.n = n
        self.rec = r.chapter(n)
        self.ev = r.chapter_events(n)
        self.w, self.h, grid = r.map_grid(n)
        table = r.terrain_table(n)
        self.terrain = [[table[t] for t in row] for row in grid]
        self.defs = {k: fe.definitions(v) for k, v in self.ev.items() if k not in ('ending', 'prep_groups')}

    def run(self, ptr, units=None, **kw):
        return fe.Run(fe.World(**kw), units=units).run(ptr)

    def prep_groups(self):
        """The groups placed before the preparations screen: long pointers ended by a 0 word, each to a group whose records follow
        a 2-byte camera spot."""
        out, a = [], self.ev['prep_groups']
        while a and r.u16(a):
            out.append(r.u24(a) + 2)
            a += 3
        return out

    def opening(self):
        """The prep groups, the opening scene, then the turn-1 events of your phase that need nothing but the turn."""
        run = fe.Run(fe.World(turn=0))
        for g in self.prep_groups():
            run.load(g)
        for e in self.defs['opening']:
            run.run(e['ptr'])
        run.world.turn = 1
        run.mem[fe.TURN] = 1
        for e in self.defs['turn']:
            if self.on_turn_one(e):
                if e['flag']:
                    run.world.flags.add(e['flag'])
                run.run(e['ptr'])
        return run

    @staticmethod
    def on_turn_one(e):
        """A turn event that runs as your first phase starts: turn 1, your phase (or any), nothing else asked but clear flags."""
        turn = [a[1] for c, a in e['conds'] if c == 0x06 and a[0] == fe.TURN]
        phase = [a[1] for c, a in e['conds'] if c == 0x06 and a[0] == fe.PHASE]
        others = [c for c, a in e['conds'] if not (c == 0x06 and a[0] in (fe.TURN, fe.PHASE)) and c != 0x0E]
        return turn == [1] and phase in ([], [0]) and not others

    def tile_terrain(self, x, y):
        return self.terrain[y][x] if 0 <= y < self.h and 0 <= x < self.w else 0


def coords_of(conds):
    """The tile a location definition checks: CMP_BYTE on the cursor (or a door's tile), or CMP_BYTE_AT against data in the ROM
    (a shop's or chest's own coordinates)."""
    x = y = None
    for code, a in conds:
        if code == 0x05 and a[0] in (fe.CURSOR_X, fe.TILE_X):
            x = a[1]
        elif code == 0x05 and a[0] in (fe.CURSOR_Y, fe.TILE_Y):
            y = a[1]
        elif code == 0x09 and a[0] == fe.CURSOR_X:
            x = r.u8(a[1])
        elif code == 0x09 and a[0] == fe.CURSOR_Y:
            y = r.u8(a[1])
    return (x, y) if x is not None and y is not None else None


def area_of(conds):
    """A CMP_BYTE_RANGE pair on the cursor: the area whose entry triggers the event."""
    xs = ys = None
    for code, a in conds:
        if code == 0x0B and a[0] == fe.CURSOR_X:
            xs = (a[1], a[2])
        elif code == 0x0B and a[0] == fe.CURSOR_Y:
            ys = (a[1], a[2])
    return (xs[0], ys[0], xs[1], ys[1]) if xs and ys else None


def visitor_of(conds):
    return next((a[1] for code, a in conds if code == 0x06 and a[0] == fe.SELECTED), None)


def phase_of(conds):
    return next((a[1] for code, a in conds if code == 0x06 and a[0] == fe.PHASE), None)


MARTY = 0x08
# Characters out of your army when a chapter starts, where its opening asks: Marty left with Dagdar's group after Chapter 3
# (Lil' Manster's and the Fire Emblem Wiki's account), and Chapter 8's opening puts him back on the map as an enemy.
OUT_OF_ARMY = {9: {MARTY}}
NUMBER = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six'}


def class_id(u):
    return r.character(u['char'])['class']


def unit_entry(u, h, talk=None):
    c = u['char']
    cls = CLASSES.get(class_id(u), '?')
    generic = is_generic(c)
    if u['side'] == fe.ENEMY:
        kind = 'boss' if u['boss'] else 'enemy' if generic else 'named'
    else:
        kind = 'ally'
    lv = f"Lv {u['level']}"
    out = {'type': kind, 'name': cls if generic else name_of(c), 'tile': to_app(u['tile'], h),
           'note': lv if generic else f'{lv} {cls}'}
    if kind == 'ally' and generic:
        out['generic'] = True
    if u.get('roster'):
        out['note'] = f'{cls}, from your army: what they carry is what they had when they left'
    items = [item_name(i) for i in u['items']]
    if items:
        out['carries'] = items
    if talk:
        out['talk'] = talk
    return out


def kind_of(c):
    """A character as a count names it: a generic one by its class and army ('Soldiers of Munster')."""
    if is_generic(c):
        return f"of the '{name_of(c)}' {CLASSES.get(r.character(c)['class'], 'unit')}s"
    return name_of(c)


def flag_words(ch, flag):
    """What sets a flag, in words: the event that runs with it as its own flag."""
    for kind, defs in ch.defs.items():
        for e in defs:
            if e['flag'] == flag:
                return event_words(ch, kind, e, depth=1)
    return None


def event_words(ch, kind, e, depth=0):
    """When an event runs, in words, and the map areas whose entry triggers it."""
    conds = e['conds']
    turn = [a for c, a in conds if c == 0x06 and a[0] == fe.TURN]
    span = [a for c, a in conds if c == 0x0C and a[0] == fe.TURN]
    phase = phase_of(conds)
    p = PHASES.get(phase, '')
    parts = []
    # An event with a flag of its own runs once (the first time its conditions hold); flag 0 runs every time they do.
    once = bool(e['flag'])
    each = {0x00: 'player phase', 0x40: 'enemy phase', 0x80: "phase of the other army"}.get(phase, 'turn')
    lead = f'The first {each}' if once else f'Every {each}'
    if turn:
        parts.append(f'Turn {turn[0][1]}' + (f', {p}' if p else ''))
    elif span:
        a, b = span[0][1], span[0][2]
        parts.append(f'{lead} from turn {a} to {b}' if b < 255 else f'{lead} from turn {a}')
    elif kind == 'turn' and p:
        parts.append(lead)
    area = area_of(conds)
    tile = coords_of(conds)
    if area and kind in ('after_action', 'before_action', 'turn'):
        parts.append('when one of your units enters the marked area')
    elif tile and kind in ('after_action', 'before_action'):
        parts.append(f'when a unit moves onto ({tile[0]}, {ch.h - tile[1]})')
    if kind == 'talk':
        a, b = next((a for c, a in conds if c in (0x00, 0x01)), (0, 0))
        parts.append(f'when {name_of(a)} talks to {name_of(b)}')
    if kind == 'location' and tile:
        parts.append(f'when the tile at ({tile[0]}, {ch.h - tile[1]}) is visited')
    for c, a in conds:
        if c == 0x0D and depth == 0:
            w = flag_words(ch, a[0])
            if w and w[0] != 'During the chapter':
                parts.append(f'after this: {w[0][0].lower() + w[0][1:]}')
            else:
                parts.append('after another event in the chapter')
        elif c == 0x10 and a[1] & fe.DEAD:
            parts.append(f'once {name_of(a[0])} has died')
        elif c == 0x10 and a[1] & fe.RESCUED:
            parts.append(f'once {name_of(a[0])} is carried off')
        elif c == 0x1A:
            parts.append(f'once {name_of(a[0])} is defeated')
        elif c == 0x18:
            parts.append(f'a {a[0]}% chance each time')
        elif c == 0x17:
            parts.append(f'while at least {a[1]} {kind_of(a[0])} remain')
        elif c == 0x16:
            parts.append(f'once at most {a[1]} {kind_of(a[0])} remain')
    text = ', '.join(parts) or 'During the chapter'
    text = text[0].upper() + text[1:]
    areas = [{'who': 'player', 'rect': rect_to_app(*area, ch.h - 1)}] if area and kind in ('after_action', 'before_action', 'turn') else None
    return text, areas


def talks_of(ch, units=None):
    """{name: 'Recruit: talk with Leif'} from the talk events (a talk whose script makes the second character yours recruits), and
    the items talks give. `units`: everyone the chapter brings onto the map, so the talk finds who it recruits."""
    found, gifts = {}, []
    for e in ch.defs['talk']:
        pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
        if not pair:
            continue
        a, b = pair
        run = fe.Run(fe.World(active=a), units=units, mem={fe.TARGET: b}).run(e['ptr'])
        t = found.setdefault(name_of(b), {'recruit': [], 'talk': [], 'gives': []})
        if b in run.recruits:
            t['recruit'].append(name_of(a))
        else:
            t['talk'].append(name_of(a))
            t['gives'] += [item_name(i) for i, _ in run.items]
        gifts += [(i, a, b) for i, _ in run.items]
    out = {}
    for name, t in found.items():
        if t['recruit']:
            out[name] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(t['recruit']))
        elif t['talk']:
            out[name] = 'Talk with ' + ' or '.join(dict.fromkeys(t['talk'])) + (f" (gives {', '.join(t['gives'])})" if t['gives'] else '')
    return out, gifts


def foe_source(source, map_id, u, entry, later):
    """What a foe carries is yours once you capture it (its items can then be taken), or a thief steals it."""
    tail = ', arriving mid-chapter' if later else ''
    kind = 'foe-later' if later else 'foe'
    for i in u['items']:
        if entry['type'] in ('boss', 'named'):
            source(i, map_id, kind, f"Carried by {entry['name']}, a foe{tail}: capture to take it")
        else:
            source(i, map_id, kind + '-generic', f"Carried by a foe {entry['name']}{tail}: capture to take it")


def build_units(ch, m, source, run, talks):
    h = m['height']
    forced = []
    for u in run.units:
        if u['side'] == fe.PLAYER:
            if u['char'] == LEIF:
                m['corrinStart'] = to_app(u['tile'], h)
            else:
                forced.append({'name': name_of(u['char']), 'tile': to_app(u['tile'], h)})
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {name_of(u['char'])} on joining", who=u['char'])
            continue
        e = unit_entry(u, h, talks.get(name_of(u['char'])))
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit'):
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {e['name']} on joining", who=u['char'])
        elif u['side'] == fe.ENEMY:
            foe_source(source, m['id'], u, e, False)
    if forced:
        m['forced'] = forced


def everyone(ch, opening):
    """The opening's units and everyone any of the chapter's events brings onto the map (the first time each character comes)."""
    present = list(opening.units)
    for kind, defs in ch.defs.items():
        if kind == 'shop':
            continue
        for e in defs:
            pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
            run = fe.Run(fe.World(active=pair[0] if pair else LEIF), units=present, mem={fe.TARGET: pair[1]} if pair else {}).run(e['ptr'])
            for _, grp in run.loads:
                for g in grp:
                    if all(u['char'] != g['char'] for u in present):
                        present.append(dict(g))
    return present


def build_recruits(ch, m, source, opening):
    """Characters an event (any of the chapter's, the end scene included) makes yours: their own items join with them. A foe held by
    your army at the end can join too (Lifis in Chapter 2x), so the scripts are played with every character held."""
    carried = {u['char']: u['items'] for u in opening.units}
    ptrs = [(kind, e) for kind, defs in ch.defs.items() if kind != 'shop' for e in defs]
    ptrs.append(('ending', {'ptr': ch.ev['ending'], 'conds': []}))
    present = list(opening.units)

    def play(kind, e):
        pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
        world = fe.World(active=pair[0] if pair else LEIF, held=set(NAMES))
        return fe.Run(world, units=present, mem={fe.TARGET: pair[1]} if pair else {}).run(e['ptr'])

    # Everyone any event brings onto the map, so a later talk can find them (Ced arrives on a turn and joins by a talk).
    for kind, e in ptrs:
        for _, grp in play(kind, e).loads:
            for g in grp:
                carried.setdefault(g['char'], g['items'])
                if all(u['char'] != g['char'] for u in present):
                    present.append(g)
    runs = [(kind, play(kind, e)) for kind, e in ptrs]
    for kind, run in runs:
        for c in run.recruits:
            if is_generic(c) or not carried.get(c):
                continue
            words = f'Carried by {name_of(c)}, who joins at the end of the chapter' if kind == 'ending' else f'Carried by {name_of(c)} on joining'
            for i in carried[c]:
                source(i, m['id'], 'kit-later', words, who=c)


def build_arrivals(ch, m, source, talks, start_flags):
    h = m['height']
    groups, joiners, n = [], [], 0
    for kind in ('turn', 'after_action', 'before_action', 'talk', 'location'):
        for e in ch.defs[kind]:
            if kind == 'turn' and Chapter.on_turn_one(e):
                continue
            if e['flag'] and e['flag'] in start_flags:
                continue
            pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
            world = fe.World(turn=next((a[1] for c, a in e['conds'] if c == 0x06 and a[0] == fe.TURN), 1),
                             active=pair[0] if pair else (visitor_of(e['conds']) or LEIF))
            run = fe.Run(world, mem={fe.TARGET: pair[1]} if pair else {}).run(e['ptr'])
            if not run.loads:
                continue
            when, areas = event_words(ch, kind, e)
            foes = [u for u in run.units if u['side'] == fe.ENEMY]
            friends = [u for u in run.units if u['side'] != fe.ENEMY]
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': when,
                     'units': [{**unit_entry(u, h, talks.get(name_of(u['char']))), 'from': to_app(u['start'], h)} for u in foes]}
                if areas:
                    g['areas'] = areas
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if (entry.get('talk') or '').startswith('Recruit'):
                        for i in u['items']:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining", who=u['char'])
                    else:
                        foe_source(source, m['id'], u, entry, True)
            for u in friends:
                generic = is_generic(u['char'])
                j = {'name': CLASSES.get(class_id(u), '?') if generic else name_of(u['char']), 'tile': to_app(u['tile'], h),
                     'from': to_app(u['start'], h), 'group': f"e{e['at']:x}", 'when': when}
                if areas:
                    j['areas'] = areas
                if u['side'] == fe.NPC:
                    j['ally'] = True
                    if generic:
                        j['generic'] = True
                    if name_of(u['char']) in talks:
                        j['talk'] = talks[name_of(u['char'])]
                recruit = u['side'] == fe.PLAYER or (j.get('talk') or '').startswith('Recruit')
                if recruit and not generic:
                    for i in u['items']:
                        source(i, m['id'], 'kit-later', f"Carried by {j['name']} on joining", who=u['char'])
                if j not in joiners:
                    joiners.append(j)
    if groups:
        m['reinforcements'] = groups
    if joiners:
        m['joiners'] = joiners


def shop_stock(ptr):
    """A shop's data: its tile, then up to seven u16 items (the low byte the item), ended by 0."""
    out, a = [], ptr + 2
    for _ in range(7):
        v = r.u16(a)
        if not v:
            break
        out.append(v & 0xFF)
        a += 2
    return out


def words_of(run):
    if 'GetRandomChestItem' in run.calls:
        return "an item picked at random from what the map's units carry"
    return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])


def build_locations(ch, m, source):
    h = m['height']
    by_tile = {}
    for e in ch.defs['location']:
        tile = coords_of(e['conds'])
        if tile:
            by_tile.setdefault(tile, []).append(e)
    seize = []
    for tile, events in by_tile.items():
        t = ch.tile_terrain(*tile)
        app = to_app(tile, h)
        if any(e['ptr'] == ch.ev['ending'] for e in events):
            seize.append(app)
            continue
        if t == 32:
            m['objects'].append({'type': 'door', 'tile': app})
            continue
        plain, special, items, joins = '', {}, [], []
        for e in events:
            visitor = visitor_of(e['conds'])
            run = fe.Run(fe.World(active=visitor or LEIF)).run(e['ptr'])
            w = words_of(run)
            items += [i for i, _ in run.items]
            joins += [name_of(u['char']) for _, grp in run.loads for u in grp if u['side'] == fe.PLAYER]
            if visitor:
                if w:
                    special.setdefault(w, []).append(name_of(visitor))
            elif w and not plain:
                plain = w
        if t in (33, 43):
            m['objects'].append({'type': 'chest', 'tile': app, 'contents': plain or ', '.join(special)})
            for i in items:
                source(i, m['id'], 'chest', 'In a chest')
            continue
        parts = [f"{w} if visited by {' or '.join(dict.fromkeys(names))}" for w, names in special.items()]
        reward = '; '.join(parts + ([f'anyone else: {plain}' if parts else plain] if plain else []))
        if t in (VILLAGE, HOUSE, CHURCH, 24, 42):
            if not reward and not joins:
                continue
            o = {'type': 'village', 'tile': app, 'reward': reward}
            notes = [f"{' and '.join(dict.fromkeys(joins))} {'joins' if len(set(joins)) == 1 else 'join'} your army."] if joins else []
            if t == HOUSE:
                notes.append('(A house.)')
            elif t in (CHURCH, 42):
                notes.append('(A church.)')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i in items:
                source(i, m['id'], 'village', 'Given at a village' if t == VILLAGE else 'Given at a house' if t == HOUSE
                       else 'Given at a church')
        elif items:
            m['objects'].append({'type': 'hidden', 'tile': app, 'area': app + app, 'contents': reward})
            for i in items:
                source(i, m['id'], 'hidden', 'Hidden on the map')
    for e in ch.defs['shop']:
        tile = coords_of(e['conds'])
        if not tile:
            continue
        kind = SHOP_KINDS.get(ch.tile_terrain(*tile))
        if not kind:
            continue
        stock = shop_stock(e['ptr'])
        m['objects'].append({'type': 'shop', 'tile': to_app(tile, h), 'kind': kind, 'stock': [item_name(i) for i in stock]})
        for i in stock:
            source(i, m['id'], 'shop', f'Sold at the {kind.lower()}' + (', with a Member Card' if kind == 'Secret shop' else ''))
    if seize:
        what = 'the throne' if 'throne' in m['victory'] else 'the gate'
        m['objectives'].append({'type': 'seize', 'tiles': seize, 'label': f'Seize {what} with Leif'})
    marks = objective_markers(ch)
    if marks:
        escape = m['victory'].startswith('Escape')
        m['objectives'].append({'type': 'escape' if escape else 'arrive', 'tiles': [to_app(t, h) for t in marks],
                                'label': 'Exit' if escape else 'Leif arrives here'})


def objective_markers(ch):
    """The chapter record's objective markers (+24): a colour byte, then [x][y][arrow] entries ended by 0."""
    out, a = [], ch.rec['objective']
    if not a:
        return out
    a += 1
    while r.u8(a):
        out.append((r.u8(a), r.u8(a + 1)))
        a += 3
    return out


def guarded_tiles(ch):
    """Tiles an enemy loses you the game by reaching: before/after-action events on the enemy phase whose script calls the game
    over ($80:C29D)."""
    out = []
    for kind in ('before_action', 'after_action'):
        for e in ch.defs[kind]:
            tile = coords_of(e['conds'])
            if tile and phase_of(e['conds']) == 0x40 and 'GameOver' in fe.Run(fe.World()).run(e['ptr']).calls:
                out.append(tile)
    return out


# When a gaiden chapter opens, read from the end script of the chapter before it (the checks before its "add to the chapter number"
# that skips the gaiden chapter), in words; each is tested in GAIDEN_CHECKS against the script itself. The Fire Emblem Wiki's chapter
# pages say the same.
GAIDEN = {
    2: 'Opens if Chapter 2 is cleared with no village destroyed.',
    5: 'Opens if every civilian escapes in Chapter 4.',
    10: "Opens if Chapter 8's boss, Lemay, is captured and held at the end, with Dagdar and Tanya in your army (they left with Marty "
        'after Chapter 3 unless they were with you at its end).',
    14: 'Opens if Chapter 11 is cleared within 30 turns with Fred alive, once Leif has set off the trap in the courtyard.',
    16: 'Opens if Chapter 12 is cleared in fewer than 20 turns.',
    19: "Opens if at least three of the city's houses are visited in Chapter 14 (Homer's doesn't count).",
    29: 'Opens if any of your units has been captured, and not rescued, by the end of Chapter 21.',
    33: "Opens if the Kia staff is taken in Chapter 24 and Sara has joined and is alive and free at its end.",
}


def happened(ch, kind, e):
    """What has to have happened for an event's flag to be set, in words."""
    tile = coords_of(e['conds'])
    pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
    if kind == 'location' and tile:
        who = visitor_of(e['conds'])
        return f"the tile at ({tile[0]}, {ch.h - tile[1]}) has been visited" + (f' by {name_of(who)}' if who else '')
    if kind == 'talk' and pair:
        return f'{name_of(pair[0])} has talked to {name_of(pair[1])}'
    if area_of(e['conds']):
        return 'one of your units has entered the marked area'
    words = event_words(ch, kind, e)[0]
    return 'this has happened: ' + words[0].lower() + words[1:]


def ending_add(ch, **kw):
    return fe.Run(fe.World(**kw)).run(ch.ev['ending']).chapter_add


def check_gaiden(chapters):
    """Each gaiden condition against its end script: the world it names opens the gaiden chapter (adds 0), and leaving one part out
    skips it (adds 1)."""
    c = chapters
    assert ending_add(c[1]) == 0 and ending_add(c[1], flags={10}) == 1
    saved = set(range(149, 155))
    assert ending_add(c[4], flags=saved) == 0 and all(ending_add(c[4], flags=saved - {f}) == 1 for f in saved)
    assert ending_add(c[15]) == 0 and ending_add(c[15], flags={5}) == 1
    houses = set(range(37, 43))
    assert ending_add(c[18], flags=set(sorted(houses)[:3])) == 0 and ending_add(c[18], flags=set(sorted(houses)[:2])) == 1


def conditional_rewards(ch):
    """Items the end script hands over only when flags it tests are set: [(item, who, the events that set them)]."""
    tested = {a[0] for _, cmd, a in fe.script(ch.ev['ending']) if cmd == 0x0E}
    plain = fe.Run(fe.World()).run(ch.ev['ending']).items
    best = fe.Run(fe.World(flags=tested)).run(ch.ev['ending']).items
    out = []
    for i, who in best:
        if (i, who) in plain:
            continue
        need = [f for f in tested if (i, who) not in fe.Run(fe.World(flags=tested - {f})).run(ch.ev['ending']).items]
        setters = []
        for f in need:
            for kind, defs in ch.defs.items():
                if kind == 'shop':
                    continue
                for e in defs:
                    if e['flag'] == f or any(cmd == 0x0C and a[0] == f for _, cmd, a in fe.reachable(e['ptr'])):
                        setters.append(happened(ch, kind, e))
        out.append((i, who, setters))
    return out


def story():
    """(index, map id, route) in the order the chapters are played; 16A and 17A, or 16B and 17B, after Chapter 15."""
    out = []
    for n, head in enumerate(HEADINGS):
        tail = head.replace('Ch.', '').lower()
        route = 'A' if head in ('Ch.16A', 'Ch.17A') else 'B' if head in ('Ch.16B', 'Ch.17B') else 'Story'
        out.append((n, f'fe5-{tail}', route))
    return out


def main():
    titles, goals = title_and_goals()
    maps, sources, used = [], {}, set()
    joined = {'A': set(), 'B': set()}
    state = {'route': 'Story', 'joining': {}}

    def source(item, map_id, kind, words, who=None):
        if who is not None:
            routes = ['A', 'B'] if state['route'] == 'Story' else [state['route']]
            if all(who in joined[x] for x in routes):
                return
            if state['joining'].setdefault(who, (kind, words)) != (kind, words):
                return
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    chapters = [Chapter(n) for n in range(35)]
    check_gaiden(chapters)
    for n, map_id, route in story():
        ch = chapters[n]
        state['route'], state['joining'] = route, {}
        w, h = ch.w - 1, ch.h - 1
        rows = [[ch.terrain[y][x] for x in range(1, ch.w)] for y in range(1, ch.h)]
        for row in rows:
            used |= set(row)
        guarded = guarded_tiles(ch)
        losers = ['Leif'] + (['Ced'] if n == 31 else [])
        defeat = ' or '.join(losers) + ' is defeated'
        if guarded:
            defeat += ', or an enemy reaches ' + ' or '.join(f'({x}, {ch.h - y})' for x, y in guarded)
        heading = HEADINGS[n]
        m = {
            'id': map_id, 'route': 'Story', 'heading': heading,
            'chapter': 25 if heading == 'Final' else int(''.join(c for c in heading if c.isdigit())),
            'title': titles[n], 'width': w, 'height': h,
            'grid': [''.join(encode(GAME, TERRAIN[t][0]) for t in row) for row in rows],
            **({'fog': True} if ch.rec['vision'] else {}),
            'victory': goals[n], 'defeat': defeat, 'objectives': [], 'units': [], 'starts': [], 'objects': [], 'changes': [], 'notes': [],
            'lord': 'Leif',
        }
        run = fe.Run(fe.World(turn=0, disabled=OUT_OF_ARMY.get(n, ())))
        for g in ch.prep_groups():
            run.load(g)
        for e in ch.defs['opening']:
            run.run(e['ptr'])
        run.world.turn, run.mem[fe.TURN] = 1, 1
        for e in ch.defs['turn']:
            if Chapter.on_turn_one(e):
                if e['flag']:
                    run.world.flags.add(e['flag'])
                run.run(e['ptr'])
        talks, gifts = talks_of(ch, everyone(ch, run))
        for i, a, b in gifts:
            source(i, map_id, 'talk', f'{name_of(a)} talks to {name_of(b)}')
        m['starts'] = [to_app(t, h) for t in fe.positions(ch.rec['starts'])]
        build_units(ch, m, source, run, talks)
        if not m['starts'] and 'corrinStart' in m:
            m['starts'] = [m['corrinStart']]
        build_arrivals(ch, m, source, talks, set(run.world.flags))
        build_recruits(ch, m, source, run)
        build_locations(ch, m, source)
        if n in GAIDEN:
            m['notes'].append(GAIDEN[n])
        end = fe.Run(fe.World()).run(ch.ev['ending'])
        for i, who in end.items:
            source(i, map_id, 'event', f"Given to {name_of(who) if who else 'your army'} at the end of the chapter")
        for i, who, setters in conditional_rewards(ch):
            cond = ' and '.join(dict.fromkeys(setters)) or 'a condition from an earlier chapter is met'
            text = f"Given to {name_of(who) if who else 'your army'} at the end of the chapter if {cond}"
            source(i, map_id, 'event', text)
            m['notes'].append(f'{item_name(i)}: {text[0].lower() + text[1:]}.')
        for _, grp in end.loads:
            for u in grp:
                if u['side'] == fe.PLAYER:
                    for i in u['items']:
                        source(i, map_id, 'kit-later', f"Carried by {name_of(u['char'])}, who joins at the end of the chapter",
                               who=u['char'])
        for x in (['A', 'B'] if route == 'Story' else [route]):
            joined[x] |= set(state['joining'])
        maps.append(m)
        print(map_id, m['title'], f'{w}x{h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    groups = move_groups()
    info = terrain_info(used, groups)
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, {c: n for c, n in CLASSES.items() if c not in DISMOUNTED})
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
