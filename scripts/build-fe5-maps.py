"""
Builds Thracia 776's maps from the user's clean ROM (scripts/fe5_rom.py), named from Lil' Manster (scripts/fe5_names.py):
  src/data/fe5/fe5Terrain.ts      terrain stats and movement costs, from the game's own tables
  src/data/fe5/fe5Maps.ts         every chapter's map as the battle starts, units, reinforcements, villages, chests, doors, shops,
                                  objectives and what reshapes the map during the battle, and on each foe one of your units can
                                  capture, the rare things capturing it takes (`steal`)
  src/data/fe5/fe5ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe5-maps.py

The chapters' scripts are played by scripts/fe5_events.py. Formats are in data-raw/fe5/README.md. Coordinates: the game counts from
(0, 0) at the top left, and the cursor never reaches column 0 or row 0 ($83:BDD8: a move onto either is refused), so the playable map
is the stored one without them; the app counts from (1, 1) at the bottom left.
"""
import functools
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe5_events as fe  # noqa: E402
import fe5_rom as r  # noqa: E402
import gba_doors  # noqa: E402
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
VILLAGE, HOUSE, CHURCH, DOOR = 18, 12, 23, 32
# A shop definition on an Armory or Vendor tile is that command's; on any other tile it's the Secret Shop command's, offered to a
# unit holding a Member Card (item 0x91) once a shop definition matches its tile and the tile is neither ($87:8B59).
SHOP_KINDS = {26: 'Armory', 27: 'Vendor'}
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
        self.w, self.h, self.mt = r.map_grid(n)
        self.table = r.terrain_table(n)
        self.changes = r.map_changes(n)
        self.terrain = [[self.table[t] for t in row] for row in self.mt]
        self.defs = {k: fe.definitions(v) for k, v in self.ev.items() if k not in ('ending', 'prep_groups')}
        # What the battle's changes do (map_changes_of): {tile: terrain ids a change can put there}, the tiles of closed rooms, and
        # {door tile: every tile its opening changes}.
        self.patched, self.closed, self.opened_by = {}, set(), {}

    def lay(self, mt, edits):
        """Makes a script's map edits (fe5_events.Run.edits) on a metatile grid, in order; returns the tiles whose terrain it makes a
        door without redrawing them ($8C:AB17), until a later change reloads the terrain from the tiles ($83:B476: TileChangeByID
        and SingleTileChangeByCoords both do; Chapter 22's bridge is a door for a moment while it's raised)."""
        doors = set()
        for ed in edits:
            if ed[0] == 'change' and ed[1] in self.changes:
                x0, y0, w, h, cells, _ = self.changes[ed[1]]
                for k, c in enumerate(cells):
                    x, y = x0 + k % w, y0 + k // w
                    if c and y < self.h and x < self.w:
                        mt[y][x] = c >> 3
                doors = set()
            elif ed[0] == 'tile' and ed[2] < self.h and ed[1] < self.w:
                mt[ed[2]][ed[1]] = ed[3]
                doors = set()
            elif ed[0] == 'door':
                doors.add((ed[1], ed[2]))
            elif ed[0] == 'random chests':
                for x, y in RANDOM_CHEST_TILES:
                    mt[y][x] = RANDOM_CHEST
            else:
                assert ed[0] != 'revert', 'a script puts a saved tile back ($8C:AACE): lay the tile $8C:AAA5 saved'
        return doors

    def start(self, edits):
        """The map as the battle starts: the opening's edits made on it."""
        doors = self.lay(self.mt, edits)
        self.terrain = [[self.table[t] for t in row] for row in self.mt]
        for x, y in doors:
            self.terrain[y][x] = DOOR

    def terrain_after(self, edits):
        """The terrain of every tile once a script's edits are made on the map as the battle starts."""
        mt = [row[:] for row in self.mt]
        doors = self.lay(mt, edits)
        out = [[self.table[t] for t in row] for row in mt]
        for x, y in doors:
            out[y][x] = DOOR
        return out

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
NUMBER = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten', 16: 'sixteen'}


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


# --- capture: what a foe holds that one of your units can capture it for ---
#
# Capturing a foe takes everything it holds (Thracia 776 has no drops), so a foe is marked (`steal`) with the rare things it holds
# when one of your units can capture it. The Capture command ($87:9B37) needs a weapon that reaches 1 tile and an adjacent foe
# ($87:9AA3, each tile checked by $87:9AEF) that isn't hidden, doesn't have the skill bit that bars capture (skills 2, 0x04: Fred,
# Olwen, Kempf, Saias...) and whose Con is below the captor's ($83:A855 for both). That Con is the unit's own plus its class's base,
# held at 20 ($83:90BE); a ballistician's, and a mounted unit's (a class in the table at $88:8000), count as 20. No unit's goes past
# 20, so a mounted captor beats any foe below 20, and a foe at 20 can't be captured at all. Sleep knocks a mounted unit off
# (the outcome $83:9C70 runs for it, $83:9E39, gives the class its dismounted form from $88:801C), except on a throne or gate or
# on an immortal unit (the Sleep Edge's effect, $83:E257, and the status staves' targeting, $87:B930, refuse both: $83:AF2B); so
# does a script's Dismount ($8C:A203).
UNCAPTURABLE = 0x04                   # skills 2 (the character's or class's)
IMMORTAL = 0x80                       # skills 3
BALLISTICIANS = {0x3D, 0x3E, 0x61}    # $83:A855
MOUNTS = {r.u8(0x888000 + i): r.u8(0x88801C + i) for i in range(28)}  # mounted class -> its dismounted form ($83:A80F)
THRONE, GATE = 31, 13
STATIONARY = {0x03, 0x07}             # movement AI (low 7 bits of the record's +0x11): stays where it stands (VoltEdge AI.h)
SLEEP_ITEMS = {0x09, 0x63, 0x71}      # Sleep Edge, Blizzard, the Sleep staff
WARP_ITEMS = {0x6E, 0x7A}             # Warp, Rewarp
# An item kept for something lasting, by its use effect (+0x11; $87:AE5A holds each one's routines): 0 has no Use command and
# works while held (the scrolls, the Member Card; $87:A34D), 2-18 raise a stat for good ($87:BC53), 20-22 promote ($87:C09E), 40-58
# teach a skill ($87:BD9C). The rest are used up for a moment: 24-30 open chests, doors and drawbridges (the keys, the Lockpick),
# 32-38 heal, cure or light (Vulnerary, Pure Water, Torch, Antitoxin), 102 restores fatigue (Stamina Drink). Weapons and staves
# (their traits) are kept.
LASTING_USE = {0, *range(2, 23, 2), *range(40, 59, 2)}
# A weapon or staff counts as rare only when fewer capturable foes than this hold it in the whole game (the user's call): Thracia's shops sell
# so few that "no shop sells it" alone would mark nearly every soldier (130 carry a Javelin, 118 a Jörmungandr). The counts break
# between 16 (Meteor, the Devil Axe) and 12 (the Master Lance).
FEW_CARRY = 15

# --- Steal: what a thief can take from a foe it can't capture ---
#
# The Steal command ($87:99B7) is a unit's with the Steal skill (skills 1, 0x02, the character's or its class's: the Thief and Rogue
# classes, Lara and Perne). Its targets ($87:99D8, each tile by $87:9A1F) are the foes beside it ($83:B34F) that aren't
# ballisticians and whose Spd (the unit's own plus its class's base, held at 20: $83:90BE) is below the thief's. Its menu ($87:B4A2)
# lists everything the foe holds, weapons included, and an item can be taken when its weight is below the thief's Con ($87:B51A,
# $83:9745: the same Con, held at 20). Spd and Con never pass 20, so a foe at Spd 20 can't be robbed, nor an item weighing 20 taken.
STEALS = 0x02                         # skills 1 (the character's or class's)


def lasting(i):
    it = r.item(i)
    if it['traits'] & (r.BALLISTA | r.BROKEN):
        return False
    return bool(it['traits'] & (r.WEAPON | r.STAFF)) or it['use_effect'] in LASTING_USE


def ordinary_stock(chapters):
    """Every item an armory or vendor sells in any chapter: the shops whose tile is an Armory or Vendor tile. The one secret shop
    (Chapter 24's, behind a door, for Member Card holders) is left out: it doesn't make what it sells common."""
    out = set()
    for ch in chapters:
        for e in ch.defs['shop']:
            tile = coords_of(e['conds'])
            if tile and SHOP_KINDS.get(ch.tile_terrain(*tile)) in ('Armory', 'Vendor'):
                out |= set(shop_stock(e['ptr']))
    return out


def capture_con(c, cls):
    """The Con the capture check compares, on foot ($83:A855, $83:90BE): the unit's own plus its class's base, held at 20. An
    autolevelled unit rolls its own as it's placed (0-3, then its scheme's growth each level: $83:A970); the lowest roll is used."""
    ch = r.character(c)
    return min(20, r.class_(cls)['bases'][6] + (0 if ch['autolevel'] else ch['con']))


def has_steal(c):
    who = r.character(c)
    return bool((who['skills1'] | r.class_(who['class'])['skills1']) & STEALS)


def steal_spd(u):
    """The Spd the Steal command compares ($87:9A56, $83:90BE): the unit's own plus its class's base (its dismounted form's once a
    script has knocked it off), held at 20. An autolevelled unit rolls its own as it's placed; the lowest roll is used, as for Con."""
    who = r.character(u['char'])
    cls = MOUNTS.get(who['class'], who['class']) if u.get('dismounted') else who['class']
    return min(20, r.class_(cls)['bases'][4] + (0 if who['autolevel'] else who['spd']))


def thief_steals(u, i):
    """Who can steal item i from the foe: a thief with more Spd than the foe's (an autolevelled foe's is rolled, so only 'faster')
    and more Con than the item weighs."""
    wt = r.item(i)['wt']
    if r.character(u['char'])['autolevel']:
        return 'a thief faster than it' + (f', with more than {wt} Con,' if wt else '') + ' can steal it'
    return f'a thief with more than {steal_spd(u)} Spd' + (f' and {wt} Con' if wt else '') + ' can steal it'


class Capture:
    """Which foes one of your units can capture or rob in a chapter, and the rare things capturing takes. `sold`: what an ordinary
    shop sells; `sleep` / `warp` / `thief`: whether a Sleep staff, Sleep Edge or Blizzard / a Warp or Rewarp staff / a unit with
    Steal can be yours by this chapter."""

    def __init__(self, ch, run, present, sold, sleep, warp, thief):
        self.ch, self.run, self.sold, self.sleep, self.warp, self.thief = ch, run, sold, sleep, warp, thief
        self.reached = {}
        self.gone = removed_on_capture(ch, present)
        self.behind = taken_when_opened(ch, present)

    def loot(self, u, entry):
        """The rare things (named as `carries` names them) a foe holds that capturing it takes: weapons and staves no shop sells,
        and lasting items no shop keeps in stock. None for a foe a talk recruits: its items come with it."""
        if u['side'] != fe.ENEMY or (entry.get('talk') or '').startswith('Recruit'):
            return []
        rare = list(dict.fromkeys(item_name(i) for i in u['items'] if i not in self.sold and lasting(i)))
        return rare if rare and self.can_capture(u) else []

    def can_capture(self, u):
        c = u['char']
        who = r.character(c)
        cls = who['class']
        if (who['skills2'] | r.class_(cls)['skills2']) & UNCAPTURABLE or cls in BALLISTICIANS:
            return False
        if capture_con(c, MOUNTS.get(cls, cls)) >= 20:
            return False
        if cls in MOUNTS and not u.get('dismounted'):
            # Counted as Con 20 until sleep knocks it off: once a sleep weapon or staff can be yours, and not where it stays on a
            # throne or gate, nor an immortal unit.
            stays = u['ai'][1] & 0x7F in STATIONARY and self.ch.tile_terrain(*u['tile']) in (THRONE, GATE)
            if not self.sleep or stays or (who['skills3'] | r.class_(cls)['skills3']) & IMMORTAL:
                return False
        return c not in self.gone and self.reaches(u)

    def can_steal(self, u, i):
        """A thief of yours can take item i from the foe: a unit with Steal can be yours, and the foe isn't a ballistician, is
        slower than a thief can be and within reach, and the item weighs less than a thief's Con can be (both held at 20)."""
        return (self.thief and r.character(u['char'])['class'] not in BALLISTICIANS and steal_spd(u) < 20
                and r.item(i)['wt'] < 20 and self.reaches(u, has_steal))

    def reaches(self, u, who=None):
        """Within reach of a unit of yours (one `who` picks) without opening the door whose opening takes the foe away (Mareeta,
        behind Chapter 5's arena door: only Eyvel, who can't steal, is in there with her)."""
        return self.within_reach(u['tile'], self.behind.get(u['char']), who)

    def within_reach(self, tile, closed=None, who=None):
        """A unit of yours can get beside it: walking or flying there from your starting tiles (with the door `closed` shut), or,
        once a Warp or Rewarp can be yours, sent onto a tile beside it that some unit can stand on."""
        x, y = tile
        beside = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        if (closed, who) not in self.reached:
            self.reached[closed, who] = reached_tiles(self.ch, self.run, closed, who)
        if any(t in self.reached[closed, who] for t in beside):
            return True
        return self.warp and any(standable(self.ch, t) for t in beside)


@functools.lru_cache(maxsize=None)
def move_rows():
    return tuple(row for _, _, row in move_groups())


def standable(ch, t):
    """A playable tile some unit can stand on as the battle starts, or once a change of the battle opens it (ch.patched)."""
    x, y = t
    if not (0 < x < ch.w and 0 < y < ch.h):
        return False
    return any(walkable(tid) for tid in {ch.terrain[y][x]} | ch.patched.get(t, set()))


def starts_of(ch, run):
    """The chapter's starting positions where they're used: by the preparations (chapter record +36) or by the opening's
    LoadPlayerUnitsByStartingPositions. Chapter 4 has neither (its opening places everyone): its list is junk, partly off the map."""
    return fe.positions(ch.rec['starts']) if ch.rec['prep'] or run.starts_loaded else []


def reached_tiles(ch, run, closed=None, who=None):
    """Every tile a unit of yours can walk or fly to from your starting tiles (the chapter's starting positions and the units the
    opening places on your side, or only those `who` picks), one movement type at a time, through what the battle's changes open
    (ch.patched: the doors and drawbridges with a definition, rooms and walls a script opens, whoever sets it off), but `closed`."""
    starts = set(starts_of(ch, run)) | {u['tile'] for u in run.units
                                                    if u['side'] == fe.PLAYER and (who is None or who(u['char']))}
    shut = ch.opened_by.get(closed, {closed}) if closed else set()
    out = set()
    for row in move_rows():
        todo = [t for t in starts if 0 < t[0] < ch.w and 0 < t[1] < ch.h]
        seen = set(todo)
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and n not in shut and 0 < n[0] < ch.w and 0 < n[1] < ch.h:
                    tid = ch.terrain[n[1]][n[0]]
                    if row[tid] != 255 or any(row[t] != 255 for t in ch.patched.get(n, ())):
                        seen.add(n)
                        todo.append(n)
        out |= seen
    return out


def removed_on_capture(ch, present):
    """Characters an event takes off the map once they're captured, so what they hold can't be taken: a foe your unit captures is
    held (unit state 0x10; 0x800 is a unit of yours carried away, $83:A131), and an event that checks for it hides it (state 0x440)
    or removes it. Mareeta in Chapter 5: the script lets go of her and hides her."""
    out = set()
    for kind, defs in ch.defs.items():
        if kind == 'shop':
            continue
        for e in defs:
            for c, a in e['conds']:
                if c == 0x10 and a[1] & fe.RESCUED:
                    run = fe.Run(fe.World(held={a[0]}, active=LEIF), units=present).run(e['ptr'])
                    u = next((x for x in run.units if x['char'] == a[0]), None)
                    if a[0] in run.removed or (u and u['state'] & (fe.HIDDEN | fe.DISABLED) == fe.HIDDEN | fe.DISABLED):
                        out.add(a[0])
    return out


def taken_when_opened(ch, present):
    """{character: door tile} for a foe an event takes off the map once a door is opened: a door's location event (one checking the
    door's own tile) sets its flag, and an event whose condition is that flag (0x0D) hides the foe (state 0x440) or removes it.
    Chapter 5's arena door: opening it sets flag 36, and right after the action Mareeta is hidden."""
    doors = {e['flag']: coords_of(e['conds']) for e in ch.defs['location']
             if e['flag'] and any(c == 0x05 and a[0] == fe.TILE_X for c, a in e['conds'])}
    out = {}
    for kind, defs in ch.defs.items():
        if kind == 'shop':
            continue
        for e in defs:
            for c, a in e['conds']:
                if c == 0x0D and a[0] in doors:
                    run = fe.Run(fe.World(flags={a[0]}, active=LEIF), units=present).run(e['ptr'])
                    for u in run.units:
                        if u['side'] == fe.ENEMY and (u['char'] in run.removed or
                                                      u['state'] & (fe.HIDDEN | fe.DISABLED) == fe.HIDDEN | fe.DISABLED):
                            out[u['char']] = doors[a[0]]
    return out


def foe_source(source, map_id, u, entry, later, capture):
    """What a foe carries is yours once you capture it (capturing takes everything it holds), or a thief steals it. What neither can
    take is said too ('foe-held'), so a weapon only such foes carry is listed as foe-only, with who carries it."""
    tail = ', arriving mid-chapter' if later else ''
    who = f"{entry['name']}, a foe{tail}" if entry['type'] in ('boss', 'named') else f"a foe {entry['name']}{tail}"
    captured = capture.can_capture(u)
    for i in u['items']:
        if captured:
            kind, how = 'foe', 'capture to take it'
        elif capture.can_steal(u, i):
            kind, how = 'foe', thief_steals(u, i)
        else:
            kind, how = 'foe-held', 'neither capture nor Steal can take it'
        kind += '-later' if later else ''
        source(i, map_id, kind if entry['type'] in ('boss', 'named') else kind + '-generic', f'Carried by {who}: {how}')


def few_carried(maps):
    """Each foe's `steal` keeps a weapon or staff only when fewer than FEW_CARRY foes you can capture hold it in the whole game
    (each one placed on a map, start units and arrivals alike, counted before this pass); a lasting item stays whatever its count."""
    def foes(m):
        return [u for u in m['units'] + [x for g in m.get('reinforcements', []) for x in g['units']] if u['type'] != 'ally']
    carried = {}
    for m in maps:
        for u in foes(m):
            for name in set(u.get('steal', [])):
                carried[name] = carried.get(name, 0) + 1
    arms = {item_name(i) for i in range(r.ITEM_COUNT) if r.item(i)['traits'] & (r.WEAPON | r.STAFF)}
    for m in maps:
        for u in foes(m):
            keep = [x for x in u.get('steal', []) if x not in arms or carried.get(x, 0) < FEW_CARRY]
            if keep:
                u['steal'] = keep
            else:
                u.pop('steal', None)


def with_loot(e, u, capture):
    loot = capture.loot(u, e)
    if loot:
        e['steal'] = loot
    return e


def build_units(ch, m, source, run, talks, capture):
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
        e = with_loot(unit_entry(u, h, talks.get(name_of(u['char']))), u, capture)
        if ch.tile_terrain(*u['tile']) == ROOF:
            # Placed under a roof: hidden in its room ($83:9620, state 0x1040) until a change over its tile is made ($84:95BA).
            e['note'] = f"{e['note']}. Out of sight in a closed room until the room opens"
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit'):
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {e['name']} on joining", who=u['char'])
        elif u['side'] == fe.ENEMY:
            foe_source(source, m['id'], u, e, False, capture)
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


def build_arrivals(ch, m, source, talks, start_flags, capture):
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
            # A script that ends the chapter only stages its end scene: its cast is no unit on the battle map (CLAUDE.md).
            if not run.loads or run.ended:
                continue
            when, areas = event_words(ch, kind, e)
            foes = [u for u in run.units if u['side'] == fe.ENEMY]
            friends = [u for u in run.units if u['side'] != fe.ENEMY]
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': when,
                     'units': [with_loot({**unit_entry(u, h, talks.get(name_of(u['char']))), 'from': to_app(u['start'], h)}, u, capture)
                               for u in foes]}
                if areas:
                    g['areas'] = areas
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if (entry.get('talk') or '').startswith('Recruit'):
                        for i in u['items']:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining", who=u['char'])
                    else:
                        foe_source(source, m['id'], u, entry, True, capture)
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
        if t == DOOR:
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
        if t in CHEST_TILES or any(c == 0x09 for e in events for c, _ in e['conds']):
            # A chest definition (VANILLA_CHEST: its tile in the ROM), or a chest tile: Chapter 24's Kia chest is under the roof of
            # the room a change opens.
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
        if not tile or not standable(ch, tile):
            continue
        t = ch.tile_terrain(*tile)
        kind = SHOP_KINDS.get(t, 'Secret shop')
        stock = shop_stock(e['ptr'])
        o = {'type': 'shop', 'tile': to_app(tile, h), 'kind': kind, 'stock': [item_name(i) for i in stock]}
        if t == DOOR:
            # Chapter 24's: its door opens onto a floor tile (the chapter's map change 0), where the shop is.
            o['note'] = 'On the door: once it is open, a unit holding a Member Card can shop on its tile.'
        m['objects'].append(o)
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


# --- map changes ---
#
# A chapter's map changes (chapter record +18; fe5_rom.map_changes) are laid by its scripts: TileChangeByID ($8C:ACD3 -> $84:92D5)
# puts change n down, SingleTileChangeByCoords ($8C:AADA) one metatile, and the terrain under them is reloaded from the tileset
# ($83:B476). Each script runs when its definition's conditions hold (a definition with no conditions never does: $8C:96D8 refuses
# one, CPY #$0005; such entries, and doors at (0, 0), are there so that reloading a chapter redoes the changes whose flags are set,
# $8C:9637). What sets them off:
#   - A door or a drawbridge: its location definition checks the tile in $7E:4FA0 / $7E:4FA2. The Door and Drawbridge commands
#     ($87:8F14, $87:8FF6) are offered to a unit holding a Door Key or a Bridge Key ($87:A27F), or with Steal (skills 1, 0x02) and a
#     Lockpick ($87:A299), beside a door (terrain 0x20) or a drawbridge (0x24) it can see; they set that tile for each one beside the
#     unit ($87:8FDA, $87:90BF -> $83:A7EC) and run the location events ($8C:9CBD), and the key, or one use of the Lockpick, is
#     spent ($87:A2BA, $87:A2DF). The keys and the Lockpick do the same from the item menu (use effects 26, 28 and 30: $87:BE60,
#     $87:BE65, $87:BEB8). The Unlock staff targets every door, drawbridge and chest on the map its user can see, at any distance
#     ($87:C3E1), and runs the tile's location events ($83:F300, $83:F34A). A tile no command targets (a wall, a river, a bridge, a
#     door in the unplayable column) never opens.
#   - A chest: the Chest command ($87:90DB) on the chest a unit stands on, with a Chest Key or with Steal and a Lockpick; or Unlock.
#     The chest's script turns it into the floor or road it stands for (the same costs and bonuses), so an opened chest isn't drawn.
#   - Razing: an enemy's raze action ($8D:851D) runs the location events of the house, village or church it stands on, or of a
#     cracked wall (terrain 0x26) beside it ($8D:85CE), with the cursor there; the definitions that check the enemy phase lay ruins
#     or break the wall. Nothing attacks a wall: it has no HP, and no command of yours breaks one.
#   - Turn, after-action and talk definitions: their own conditions (turn, phase, area, flags).
# A unit placed on a roof tile is hidden in its room ($83:9620: state 0x1040) until a change over its tile is made ($84:95BA).
EDGE, ROOF, WALL, CRACKED, DRAWBRIDGE = 0, 21, 30, 38, 36
CHEST_TILES = {33, 43}
VISITED = {VILLAGE, HOUSE, CHURCH, 24, 42}    # what a visit or a raze stands on
CLOSED = 'X'                                  # a room under its roof (terrain_codes 'ws')
RANDOM_CHEST = 0x27                           # the metatile Chapter 4's opening lays for each random chest ($8C:B9A4)
# The 16 tiles Chapter 4's random chests are laid on ($8C:BA58 reads them: LDA $99:9147,X) and the four items the game adds to your
# units' ($8C:B964: Rapier, Javelin, Steel Sword, Vulnerary).
RANDOM_CHEST_TILES = [(r.u8(r.u24(0x8CBA59) + 2 * i), r.u8(r.u24(0x8CBA59) + 2 * i + 1)) for i in range(16)]
FIXED_CHEST_ITEMS = [r.u8(a) for a in (0x8CB965, 0x8CB96E, 0x8CB977, 0x8CB980)]
CHANGE_PHASE = {0x00: 'player phase', 0x40: 'enemy phase', 0x80: "other army's phase"}
# The one script condition a change waits on (RUN_ASM): the Final Chapter's throne room opens once your units stand on the tiles of
# the list at $B9:BB1A ($B9:BAED: each tile occupied, by a unit of yours).
SEALS = 0xB9BAED


PICK = 0xB9B671  # Chapter 24: picks a civilian at random (JSL $80:B0E6, AND #$03) from a list and gives it movement AI 0x28


def sent_civilian(ch, units):
    """(turn, phase, [their tiles]) for the turn definition whose script picks one of a list of civilians at random and sends it on
    ($B9:B671: one of the four in the list its LDA $B9:B6AA,X reads, given movement AI 0x28), or None. `units`: who the opening
    places."""
    for e in ch.defs['turn']:
        if any(c in (0x1B, 0x1C, 0x1D) and a[0] == PICK for _, c, a in fe.reachable(e['ptr'])):
            table, count = r.u24(PICK + 0xF), r.u8(PICK + 0xA) + 1
            chars = [r.u16(table + 2 * i) for i in range(count)]
            turn = next(a[1] for c, a in e['conds'] if c == 0x06 and a[0] == fe.TURN)
            tiles = [u['tile'] for c in chars for u in units if u['char'] == c]
            assert len(tiles) == count, (ch.n, chars)
            return turn, phase_of(e['conds']), tiles
    return None


def walkable(tid):
    return any(row[tid] != 255 for row in move_rows())


def app_xy(ch, t):
    """'(x, y)' in the app's coordinates for a game tile."""
    return '({}, {})'.format(*to_app(t, ch.h - 1))


def tiles_words(ch, tiles):
    words = [app_xy(ch, t) for t in sorted(tiles, key=lambda t: (t[1], t[0]))]
    return words[0] if len(words) == 1 else ', '.join(words[:-1]) + ' and ' + words[-1]


def where_words(ch, conds):
    """Where an after-action definition looks: 'on (7, 7)', 'on (7, 7) or (8, 7)', 'in the area from (5, 21) to (11, 24)'."""
    tile, area = coords_of(conds), area_of(conds)
    if tile:
        return 'on ' + app_xy(ch, tile)
    x1, y1, x2, y2 = area
    if (x2 - x1 + 1) * (y2 - y1 + 1) <= 2:
        return 'on ' + ' or '.join(app_xy(ch, (x, y)) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1))
    l, b, r_, t = rect_to_app(x1, y1, x2, y2, ch.h - 1)
    return f'in the area from ({l}, {b}) to ({r_}, {t})'


def who_words(conds):
    """Who an after-action definition waits for: a character it names, a unit carrying one, your units (your phase), any unit."""
    active = visitor_of(conds)
    carried = next((a[0] for c, a in conds if c == 0x14), None)
    if active:
        return name_of(active)
    if carried:
        return f'a unit carrying {name_of(carried)}'
    return 'one of your units' if phase_of(conds) == 0 else 'a unit'


def gold_of(ptr):
    """The gold a script asks for (CompareGoldGTE, $8C:AA47: the value stored to its parameter first), or None."""
    p1 = None
    for _, c, args in sorted(fe.reachable(ptr), key=lambda x: x[0]):
        if c in (0x0F, 0x10, 0x11) and args[0] & 0xFFFF == fe.PARAM1:
            p1 = args[1]
        elif c in (0x1B, 0x1C, 0x1D) and fe.ASMC.get(args[0]) == 'CompareGoldGTE':
            return p1
    return None


def setter_words(ch, flag):
    """What sets a flag, in words ('one of your units stops in the area from ...'): the definition whose own flag it is, else a
    script that sets it (Chapter 17B's gate house, paid)."""
    found = None
    for kind, defs in ch.defs.items():
        for e in defs:
            if e['flag'] == flag and e['conds'] and kind != 'shop':
                found = found or (kind, e)
    if not found:
        for kind, defs in ch.defs.items():
            for e in defs:
                if kind != 'shop' and e['conds'] and any(c == 0x0C and a[0] == flag for _, c, a in fe.reachable(e['ptr'])):
                    found = found or (kind, e)
    if not found:
        return None
    kind, e = found
    if kind == 'after_action' and (coords_of(e['conds']) or area_of(e['conds'])):
        return f"{who_words(e['conds'])} stops {where_words(ch, e['conds'])}"
    if kind == 'location' and coords_of(e['conds']):
        gold = gold_of(e['ptr'])
        where = ('the house at ' if ch.tile_terrain(*coords_of(e['conds'])) in VISITED else '') + app_xy(ch, coords_of(e['conds']))
        return f'{gold:,} gold is paid at {where}' if gold else f'{where} is visited'
    return None


def when_words(ch, kind, e):
    """When a turn, after-action or talk definition's change is made, in words, or None where it can't be said."""
    conds = e['conds']
    phase = phase_of(conds)
    turn = [a[1] for c, a in conds if c == 0x06 and a[0] == fe.TURN]
    flags = [a[0] for c, a in conds if c == 0x0D]
    if kind == 'after_action':
        if not (coords_of(conds) or area_of(conds)):
            return None
        out = f"as soon as {who_words(conds)} stops {where_words(ch, conds)}"
        for f in flags:
            s = setter_words(ch, f)
            if not s:
                return None
            out = f'once {s}, {out}'
        return out[0].upper() + out[1:]
    if kind == 'turn':
        p = CHANGE_PHASE.get(phase, 'turn')
        if any(c == 0x0F and a[0] == SEALS for c, a in conds):
            seals, a = [], r.u24(SEALS + 4)   # the list its LDA $B9:BB1A,X reads, ended by 0
            while r.u8(a):
                seals.append((r.u8(a), r.u8(a + 1)))
                a += 2
            kinds = {TERRAIN[ch.tile_terrain(*t)][1].lower() for t in seals}
            what = f'{kinds.pop()}s' if len(kinds) == 1 else 'tiles'
            return (f'At the start of the first {p} with your units on all {NUMBER.get(len(seals), len(seals))} {what} '
                    f'({tiles_words(ch, seals)})')
        if any(c == 0x0F for c, a in conds):
            return None
        if turn:
            out = f"At the start of turn {turn[0]}'s {p}"
        elif flags:
            s = setter_words(ch, flags[0])
            if not s:
                return None
            out = f'At the start of the first {p} after {s}'
        else:
            return None
        for c, a in conds:
            if c == 0x17 and a[1] == 1 and not is_generic(a[0]):
                out += f', if {name_of(a[0])} is still on the map'
        return out
    if kind == 'talk':
        pair = next((a for c, a in conds if c in (0x00, 0x01)), None)
        return f'When {name_of(pair[0])} talks to {name_of(pair[1])}' if pair else None
    return None


def patch_of(ch, after):
    """{tile: terrain after} for the playable tiles a change gives another terrain."""
    return {(x, y): after[y][x] for y in range(1, ch.h) for x in range(1, ch.w) if after[y][x] != ch.terrain[y][x]}


def clusters(tiles):
    """The tiles in groups of side-by-side ones."""
    left, out = set(tiles), []
    while left:
        todo = [left.pop()]
        group = set(todo)
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in left:
                    left.discard(n)
                    group.add(n)
                    todo.append(n)
        out.append(group)
    return out


def map_changes_of(ch, run):
    """What reshapes the map during the battle, from the chapter's definitions (the opening's changes are on the map already):
    [{kind, tile, patch: {tile: terrain}, words}] in game tiles, one per door, drawbridge, house razed and wall broken, and one per
    other change (turn, after-action, talk, a visit that closes other houses), its ways of being set off joined. Fills ch.patched,
    ch.closed (the roofed tiles a change opens) and ch.opened_by. A door definition on a tile no command targets (a wall: Chapter
    4's central room, Chapter 11x's three; Chapter 20's door in the unplayable column) is left out, as is one whose change writes
    the tiles the map already has (Chapter 12's river, Chapter 13's bridge)."""
    out = []

    def play(kind, e, gone=()):
        pair = next((a for c, a in e['conds'] if c in (0x00, 0x01)), None)
        turn = next((a[1] for c, a in e['conds'] if c == 0x06 and a[0] == fe.TURN), 1)
        world = fe.World(active=pair[0] if pair else (visitor_of(e['conds']) or LEIF), phase=phase_of(e['conds']) or 0, turn=turn,
                         dead=gone)
        return fe.Run(world, units=run.units, mem={fe.TARGET: pair[1]} if pair else {}).run(e['ptr'])

    events = []
    for kind in ('location', 'turn', 'after_action', 'talk', 'before_action', 'battle'):
        for e in ch.defs[kind]:
            if not e['conds'] or (kind == 'turn' and Chapter.on_turn_one(e)):
                continue
            if e['flag'] and e['flag'] in run.world.flags:
                continue  # done in the opening (Chapter 11's open doors): it never runs again
            done = play(kind, e)
            if not done.edits or done.ended:
                continue  # an end scene's changes are no battle's (Chapter 4's central room)
            patch = patch_of(ch, ch.terrain_after(done.edits))
            if patch:
                events.append((kind, e, done, patch))
    for kind, e, done, patch in events:
        conds = e['conds']
        door = next((a[1] for c, a in conds if c == 0x05 and a[0] == fe.TILE_X), None) is not None
        tile = coords_of(conds)
        if kind == 'location' and door:
            t = ch.tile_terrain(*tile)
            if t not in (DOOR, DRAWBRIDGE) or tile not in patch:
                continue
            out.append({'kind': 'door' if t == DOOR else 'bridge', 'tile': tile, 'patch': patch})
        elif kind == 'location':
            if not tile or any(c == 0x09 for c, _ in conds):
                continue  # a chest: it becomes the floor or road it stands for
            phase, t = phase_of(conds), ch.tile_terrain(*tile)
            if phase == 0x40 and t in VISITED:
                out.append({'kind': 'raze', 'tile': tile, 'patch': patch})
            elif phase == 0x40 and t == CRACKED:
                out.append({'kind': 'wall', 'tile': tile, 'patch': patch})
            elif phase == 0x80:
                out.append({'kind': 'other army', 'tile': tile, 'patch': patch})
            elif set(patch) - {tile}:
                # A visit that closes other houses too (Chapter 17B's eight): said with the visitor where another unit's visit (a
                # character id no one has) doesn't.
                other = fe.Run(fe.World(active=0xFFFE), units=run.units).run(e['ptr'])
                only = '' if patch_of(ch, ch.terrain_after(other.edits)) == patch else name_of(visitor_of(conds) or LEIF)
                out.append({'kind': 'visit', 'tile': tile, 'patch': patch, 'by': only})
        else:
            words = when_words(ch, kind, e)
            assert words, (ch.n, kind, hex(e['ptr']))
            # A named character the script needs on the map (Chapter 11's trap springs only while Kempf is there): played with them
            # gone, it changes nothing.
            for c in dict.fromkeys(u['char'] for u in run.units if u['side'] != fe.PLAYER and not is_generic(u['char'])):
                if not play(kind, e, gone={c}).edits:
                    words += f', while {name_of(c)} is on the map'

            area = area_of(conds) if kind == 'after_action' else None
            out.append({'kind': 'event', 'tile': tile, 'area': area, 'patch': patch, 'words': [words]})
    # One change for the same tiles: a visit to any of the houses that close together, and an event set off two ways (Chapter 17B's
    # middle gate, Chapter 11's trap with Leif or a unit carrying him).
    merged = []
    for c in out:
        same = next((m for m in merged if m['kind'] == c['kind'] and m['kind'] in ('event', 'visit') and m['patch'] == c['patch']),
                    None)
        if same is None:
            merged.append({**c, 'tiles': [c['tile']]})
        else:
            same['tiles'].append(c['tile'])
            same['words'] = same.get('words', []) + [w for w in c.get('words', []) if w not in same.get('words', [])]
    for c in merged:
        for xy, t in c['patch'].items():
            ch.patched.setdefault(xy, set()).add(t)
            if ch.terrain[xy[1]][xy[0]] in (ROOF, EDGE) and walkable(t):
                ch.closed.add(xy)
        if c['kind'] in ('door', 'bridge'):
            ch.opened_by[c['tile']] = set(c['patch'])
    return merged


def change_effect(ch, c, m, units):
    """The app's words for a change. `units`: who the opening places."""
    patch = c['patch']
    tile = c['tile']
    start = ch.terrain
    rooms = [xy for xy in patch if xy in ch.closed]
    others = [xy for xy in patch if xy != tile and start[xy[1]][xy[0]] == DOOR and walkable(patch[xy])]
    walls = [xy for xy in patch if xy != tile and xy not in rooms and xy not in others and not walkable_ground(start[xy[1]][xy[0]])
             and walkable_ground(patch[xy])]
    chests = [xy for xy in rooms if patch[xy] in CHEST_TILES]
    with_chest = f', with the chest at {tiles_words(ch, chests)}' if chests else ''
    extra = f' The closed room behind it opens with it{with_chest}.' if rooms else ''
    if others:
        extra += f" The door{'s' if len(others) > 1 else ''} at {tiles_words(ch, others)} open{'' if len(others) > 1 else 's'} with it."
    if walls:
        extra += f" The wall{'s' if len(walls) > 1 else ''} at {tiles_words(ch, walls)} open{'' if len(walls) > 1 else 's'} too."
    unlock = 'and the Unlock staff from any distance' + (' once it can be seen' if m.get('fog') else '')
    if c['kind'] == 'door':
        return f'A door: a unit beside it opens it with a Door Key, or with a Lockpick if it has Steal, {unlock}.{extra}'
    if c['kind'] == 'bridge':
        rest = [xy for xy in patch if xy != tile and start[xy[1]][xy[0]] == DRAWBRIDGE]
        return (f'A raised drawbridge: a unit beside it lowers it with a Bridge Key, or with a Lockpick if it has Steal, {unlock}.'
                + (' The rest of the bridge lowers with it.' if rest else ''))
    if c['kind'] == 'raze':
        what = {VILLAGE: 'village', CHURCH: 'church', 42: 'church'}.get(start[tile[1]][tile[0]], 'house')
        return f'A foe standing on this {what} can raze it on the enemy phase: it falls to ruins.'
    if c['kind'] == 'wall':
        return ("A cracked wall with no HP: your units can't break it, but a foe beside it can raze it on the enemy phase, opening "
                'it.')
    if c['kind'] == 'other army':
        sent = sent_civilian(ch, units)
        assert sent, ch.n
        turn, phase, tiles = sent
        inside = f' (with the chest at {tiles_words(ch, chests)})' if chests else ''
        return (f"A hidden way into the closed room behind this wall{inside}: it opens only on the other army's phase. At the start "
                f'of that phase on turn {turn}, the game picks one of the {NUMBER.get(len(tiles), len(tiles))} civilians at '
                f'{tiles_words(ch, tiles)} at random and sends it here.')
    if c['kind'] == 'visit':
        n = len(c['tiles'])
        who = f"When {c['by']} visits" if c['by'] else 'Visiting'
        return (f"{who} any of these {NUMBER.get(n, n)} houses, all {NUMBER.get(n, n)} close." if n > 1 else
                f"{who} this house closes {tiles_words(ch, [xy for xy in patch if xy != tile])}.")
    return f"{join_whens(c['words'])}: {what_changes(ch, c)}."


def join_whens(words):
    """A change's ways of being set off in one sentence; two that wait for units stopping in the same place name both units ('As
    soon as Leif, or a unit carrying Leif, stops in the area ...')."""
    out = []
    for w in words:
        m = re.match(r'^(.*?)([Aa]s soon as) (.+?) stops (.+)$', w)
        same = next((o for o in out if m and o[0] == 'after' and o[1] == m.group(1) and o[4] == m.group(4)), None)
        if same:
            same[3].append(m.group(3))
        elif m:
            out.append(['after', m.group(1), m.group(2), [m.group(3)], m.group(4)])
        else:
            out.append(['text', w])
    texts = [f"{o[1]}{o[2]} {', or '.join(o[3])}{',' if len(o[3]) > 1 else ''} stops {o[4]}" if o[0] == 'after' else o[1]
             for o in out]
    return texts[0] + ''.join('; or ' + t[0].lower() + t[1:] for t in texts[1:])


BRIDGE, OUTDOOR_WALL = 16, 14


def what_changes(ch, c):
    """'the closed room opens', 'the bridge is raised'...: what an event's change does, from the terrain before and after."""
    patch, start = c['patch'], ch.terrain
    before = {xy: start[xy[1]][xy[0]] for xy in patch}
    parts = []
    shut = [xy for xy, t in patch.items() if t == DOOR]
    if shut:
        parts.append(f"the door{'s' if len(shut) > 1 else ''} at {tiles_words(ch, shut)} shut{'' if len(shut) > 1 else 's'} (each "
                     'opens again as a door does)')
    opened = [xy for xy, b in before.items() if b == DOOR and walkable_ground(patch[xy])]
    if opened:
        parts.append(f"the door{'s' if len(opened) > 1 else ''} at {tiles_words(ch, opened)} open{'' if len(opened) > 1 else 's'}")
    if any(xy in ch.closed for xy in patch):
        parts.append('the closed room opens')
    if any(b == BRIDGE and patch[xy] != BRIDGE for xy, b in before.items()):
        parts.append('the bridge is raised')
    if any(b != BRIDGE and patch[xy] == BRIDGE for xy, b in before.items()):
        parts.append('a bridge is lowered')
    if any(b == CRACKED for b in before.values()):
        parts.append('the cracked wall gives way')
    elif not any(xy in ch.closed for xy in patch) and any(b in (WALL, OUTDOOR_WALL, ROOF, EDGE) and walkable_ground(patch[xy])
                                                          for xy, b in before.items()):
        parts.append('the wall opens')
    return ' and '.join(parts) if parts else 'the map changes'


@functools.lru_cache(maxsize=None)
def ground_rows():
    return tuple(row for label, _, row in move_groups() if label not in ('Fliers', 'Pirates'))


def walkable_ground(tid):
    """A terrain some unit on foot or on horseback can enter (fliers and pirates' waters aside)."""
    return any(row[tid] != 255 for row in ground_rows())


def raze_notes(m):
    """What a foe can raze, said where it stands (the user's call: no raze toggle): in its village's note, or for houses and
    churches with nothing to visit, in one of the map's notes."""
    unvisited = []
    for (x, y), words in m.pop('_razes', []):
        visit = next((o for o in m['objects'] if o['type'] == 'village' and o['tile'] == [x, y]), None)
        if visit:
            visit['note'] = ((visit.get('note') or '') + ' ' + words).strip()
        else:
            unvisited.append(((x, y), words))
    if unvisited:
        what = [f"the {w.split('this ')[1].split(' can')[0]} at ({x}, {y})"
                for (x, y), w in sorted(unvisited, key=lambda t: (t[0][1], t[0][0]))]
        m['notes'].append('A foe standing on a house or church with nothing to visit can raze it on the enemy phase, and it falls '
                          f"to ruins: {', '.join(what[:-1]) + ' and ' + what[-1] if len(what) > 1 else what[0]}.")


def build_changes(ch, m, run):
    """The battle's map changes on the map (m['changes']), each previewed."""
    h = m['height']
    found = map_changes_of(ch, run)
    for c in found:
        patch = [{'tile': to_app(xy, h), 'becomes': encode(GAME, TERRAIN[t][0])}
                 for xy, t in sorted(c['patch'].items(), key=lambda kv: (kv[0][1], kv[0][0]))]
        tiles = c['tiles']
        wide = c['kind'] == 'visit' or (c['kind'] == 'event' and len(clusters(c['patch'])) > 1)
        if c['kind'] == 'event' and not wide:
            # Marked on the changed tile nearest what sets it off (its area or tile), else nearest the change's middle.
            if c['area']:
                x1, y1, x2, y2 = c['area']
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            elif c['tile']:
                cx, cy = c['tile']
            else:
                cx = sum(x for x, _ in c['patch']) / len(c['patch'])
                cy = sum(y for _, y in c['patch']) / len(c['patch'])
            at = min(c['patch'], key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t[1], t[0]))
        elif wide:
            at = min(c['patch'], key=lambda t: (t[1], t[0]))
        else:
            at = tiles[0]
        X, Y = to_app(at, h)
        if c['kind'] == 'raze':
            # Said in its note, not previewed (the user's call: a raze is no map change to toggle): raze_notes, once the
            # villages are on the map.
            m.setdefault('_razes', []).append(((X, Y), change_effect(ch, c, m, run.units)))
            continue
        kind = {'door': 'door', 'bridge': 'bridge', 'raze': 'raze', 'wall': 'wall', 'other army': 'event', 'visit': 'visit'}.get(
            c['kind'], 'event')
        e = {'id': f'{kind}-{X}-{Y}', 'trigger': 'breakable' if c['kind'] == 'wall' else 'event', 'tile': {'default': [X, Y]},
             'usableBy': 'A foe beside it, on the enemy phase' if c['kind'] == 'wall' else '',
             'effect': change_effect(ch, c, m, run.units), 'patch': patch}
        if wide:
            e['wide'] = True
        if c['kind'] == 'event' and c['area'] and wide:
            e['zone'] = rect_to_app(*c['area'], h)
        m['changes'].append(e)
    gba_doors.unique_ids(m['changes'])
    # A cracked wall no event breaks (Chapter 21x's three): a raze beside it runs no definition, so it stays a wall.
    stuck = [(x, y) for y in range(1, ch.h) for x in range(1, ch.w) if ch.terrain[y][x] == CRACKED and (x, y) not in ch.patched]
    if stuck:
        many = len(stuck) > 1
        m['notes'].append(f"The cracked wall{'s' if many else ''} at {tiles_words(ch, stuck)} never break{'' if many else 's'}: no event "
                          f"of the chapter breaks {'them' if many else 'it'}.")


def random_chests(ch, m, source, run):
    """Chapter 4's chests: its opening takes the items your units on the map carry ($8C:B82B) and lays a chest for each on the
    tiles of a list, in a random order (fe5_events: 'random chests'). The game adds four items of its own ($8C:B964) and keeps the
    16 it values most ($8C:B8C0, by $83:B234: items, then staves, then weapons, each by cost per use); the rest are lost."""
    if not any(ed[0] == 'random chests' for ed in run.edits):
        return
    h = m['height']
    fixed = ', '.join(item_name(i) for i in FIXED_CHEST_ITEMS[:-1]) + f' or {item_name(FIXED_CHEST_ITEMS[-1])}'
    whose = ' and '.join(name_of(c) for c in run.stripped) or 'your units'
    for xy in RANDOM_CHEST_TILES:
        m['objects'].append({'type': 'chest', 'tile': to_app(xy, h),
                             'contents': f'one of the items taken from {whose}, or a {fixed}, at random'})
    for i in FIXED_CHEST_ITEMS:
        source(i, m['id'], 'chest', 'In a chest')
    names = [item_name(i) for i in FIXED_CHEST_ITEMS]
    count = NUMBER.get(len(RANDOM_CHEST_TILES), len(RANDOM_CHEST_TILES))
    m['notes'].append(f"As the chapter opens, the items {whose} carry are taken from them and, with a {', a '.join(names[:-1])} "
                      f'and a {names[-1]}, put one to a chest on the {count} chest tiles, in a random order (a tile left without one '
                      f'stays floor); past {len(RANDOM_CHEST_TILES)} items, those the game values least are lost.')


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
    state = {'route': 'Story', 'joining': {}, 'n': 0}
    got = []  # (item, chapter index, route) for each way of getting an item that isn't taking it from a foe

    def source(item, map_id, kind, words, who=None):
        if not kind.startswith('foe'):
            got.append((item, state['n'], state['route']))
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
    sold = ordinary_stock(chapters)
    closed_rooms = False

    def yours_by(n, route, items):
        """Whether one of `items` can be yours by chapter n: given in an earlier chapter of the shared story or of n's route."""
        return any(i in items and k < n and rt in ('Story', route) for i, k, rt in got)

    for n, map_id, route in story():
        ch = chapters[n]
        state['route'], state['joining'], state['n'] = route, {}, n
        w, h = ch.w - 1, ch.h - 1
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
        # The opening's changes are made before the battle: the map starts with them (Chapter 2's razed village, Chapter 11's open
        # doors, Chapter 4's chests).
        ch.start(run.edits)
        guarded = guarded_tiles(ch)
        losers = ['Leif'] + (['Ced'] if n == 31 else [])
        defeat = ' or '.join(losers) + ' is defeated'
        if guarded:
            defeat += ', or an enemy reaches ' + ' or '.join(f'({x}, {ch.h - y})' for x, y in guarded)
        heading = HEADINGS[n]
        m = {
            'id': map_id, 'route': 'Story', 'heading': heading,
            'chapter': 25 if heading == 'Final' else int(''.join(c for c in heading if c.isdigit())),
            'title': titles[n], 'width': w, 'height': h, 'grid': [],
            # Fog: the game draws what your units can't see black, the ground too; each of them sees the chapter's vision in steps
            # (plus its own bonus, +0x17), the visibility map's fill (`$80:E626`).
            **({'fog': True, 'blackFog': ch.rec['vision']} if ch.rec['vision'] else {}),
            'victory': goals[n], 'defeat': defeat, 'objectives': [], 'units': [], 'starts': [], 'objects': [], 'changes': [], 'notes': [],
            'lord': 'Leif',
        }
        # What reshapes the map during the battle, each previewed; a room under its roof is closed until one opens it.
        build_changes(ch, m, run)
        rows = [[ch.terrain[y][x] for x in range(1, ch.w)] for y in range(1, ch.h)]
        for row in rows:
            used |= set(row)
        used |= {t for ts in ch.patched.values() for t in ts}
        m['grid'] = [''.join(encode(GAME, CLOSED if (x, y) in ch.closed else TERRAIN[t][0]) for x, t in enumerate(row, 1))
                     for y, row in enumerate(rows, 1)]
        closed_rooms |= bool(ch.closed)
        random_chests(ch, m, source, run)
        present = everyone(ch, run)
        talks, gifts = talks_of(ch, present)
        for i, a, b in gifts:
            source(i, map_id, 'talk', f'{name_of(a)} talks to {name_of(b)}')
        m['starts'] = [to_app(t, h) for t in starts_of(ch, run)]
        # A unit with Steal is yours once one has joined on every route this chapter is on, or the opening places one on your side.
        thief = (all(any(has_steal(c) for c in joined[x]) for x in (['A', 'B'] if route == 'Story' else [route]))
                 or any(has_steal(u['char']) for u in run.units if u['side'] == fe.PLAYER))
        capture = Capture(ch, run, present, sold, yours_by(n, route, SLEEP_ITEMS), yours_by(n, route, WARP_ITEMS), thief)
        build_units(ch, m, source, run, talks, capture)
        if not m['starts'] and 'corrinStart' in m:
            m['starts'] = [m['corrinStart']]
        build_arrivals(ch, m, source, talks, set(run.world.flags), capture)
        build_recruits(ch, m, source, run)
        build_locations(ch, m, source)
        raze_notes(m)
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

    # Of the weapons and staves capturing takes, only the ones few foes carry count as rare.
    few_carried(maps)
    groups = move_groups()
    info = terrain_info(used, groups)
    if closed_rooms:
        # Roof tiles are closed to every unit, fliers included; a room under them stays closed until a change opens it.
        info[encode(GAME, CLOSED)] = {'name': 'Roof (closed room)', 'def': 0, 'avo': 0, 'heal': 0,
                                      'move': {label: None for label, _, _ in groups},
                                      'note': "A room under its roof: no unit can enter it, fliers included, until it opens (a door "
                                              "into it, or the chapter's script). A unit inside is out of sight until then."}
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, {c: n for c, n in CLASSES.items() if c not in DISMOUNTED})
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    # Who carries an item that neither capture nor Steal can take is only worth saying where nothing else gives it: it shows who
    # carries a foe-only weapon.
    for name, lst in sources.items():
        if any(not x['kind'].startswith('foe-held') for x in lst):
            sources[name] = [x for x in lst if not x['kind'].startswith('foe-held')]
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
