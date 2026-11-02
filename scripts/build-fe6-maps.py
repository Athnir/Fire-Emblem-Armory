"""
Builds The Binding Blade's maps from the user's clean Japanese ROM (scripts/fe6_rom.py), with English names from the FE6 Localization
patch (scripts/fe6_names.py):
  src/data/fe6/fe6Terrain.ts      terrain stats and movement costs by movement type
  src/data/fe6/fe6Maps.ts         every chapter and trial map: terrain, units, reinforcements, joiners, chests, villages, shops
  src/data/fe6/fe6ItemSources.ts  where each item turns up, by chapter (the weapon page and the spoiler block)
Run:
    python scripts/build-fe6-maps.py

What is read where (data-raw/fe6/README.md has the formats):
  - Chapter records, 68 bytes at 0x6637A0: the map, tile config and event data are indices into the pointer table at 0x664398; the
    fog vision is at +0x10 and the number of units you deploy at +0x11 (0: no preparations, the chapter places your army itself).
  - The map (LZ77) gives a metatile per tile; the tile config's byte 0x2000 + metatile is the terrain id. Terrain stats are the
    ground rows (avoid 0x60C978, Def 0x60C9AB, Res 0x60C9DE) and the healing row (0x60CBA9); each class points at its own movement
    cost row (+0x34) and its avoid / Def / Res rows (fliers' avoid and Def rows are all 0).
  - Events (scripts/fe6_events.py): the enemies a chapter starts with (the event data's slot 4), the opening scripts (turn 1 events
    on your phase), every later turn, talk, area and location event, played with the game's own rules for flags, Hard mode and the
    check routines. Units end on the tile the scripted moves leave them on.
Chapter titles aren't text in the ROM (they're drawn); they're Serenes Forest's (its translation script). The trial maps' names are
the patch's.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe6_events as fe  # noqa: E402
import fe6_rom as rom  # noqa: E402
import gba_ai  # noqa: E402
import gba_bosses  # noqa: E402
import gba_doors  # noqa: E402
import gba_maps  # noqa: E402
from fe6_names import character_names, class_names, item_names, text as en  # noqa: E402
from terrain_codes import encode  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe6')
R = rom.R
AI = gba_ai.Ai('fe6', R)

# (chapter entry, map id, chapter number, heading, title): the story as it's played, both routes' chapters in turn, then the
# trial maps (link arena maps, open once the game is cleared). Entry 0 is the tutorial and 39 an unused copy of Chapter 6's map.
STORY = [
    (1, 'fe6-1', 1, 'Ch.1', 'The Breath of Fate'),
    (2, 'fe6-2', 2, 'Ch.2', 'The Princess of Bern'),
    (3, 'fe6-3', 3, 'Ch.3', 'The Latecomer'),
    (4, 'fe6-4', 4, 'Ch.4', 'The Collapse of the Alliance'),
    (5, 'fe6-5', 5, 'Ch.5', 'The Emblem of Fire'),
    (6, 'fe6-6', 6, 'Ch.6', 'The Trap'),
    (7, 'fe6-7', 7, 'Ch.7', 'The Rebellion at Ostia'),
    (8, 'fe6-8', 8, 'Ch.8', 'Reunion'),
    (32, 'fe6-8x', 8, 'Ch.8x', 'The Blazing Sword'),
    (9, 'fe6-9', 9, 'Ch.9', 'The Misty Isles'),
    (10, 'fe6-10a', 10, 'Ch.10A', 'The Rebel Forces'),
    (11, 'fe6-11a', 11, 'Ch.11A', 'The Hero of the West'),
    (26, 'fe6-10b', 10, 'Ch.10B', 'Caught in the Middle'),
    (27, 'fe6-11b', 11, 'Ch.11B', 'The Escape to Freedom'),
    (12, 'fe6-12', 12, 'Ch.12', 'The True Enemy'),
    (33, 'fe6-12x', 12, 'Ch.12x', 'The Axe of Lightning'),
    (13, 'fe6-13', 13, 'Ch.13', 'The Rescue Plan'),
    (14, 'fe6-14', 14, 'Ch.14', 'Arcadia'),
    (34, 'fe6-14x', 14, 'Ch.14x', 'The Infernal Element'),
    (15, 'fe6-15', 15, 'Ch.15', 'The Dragon Girl'),
    (16, 'fe6-16', 16, 'Ch.16', 'Retaking the Capital'),
    (35, 'fe6-16x', 16, 'Ch.16x', 'The Pinnacle of Light'),
    (17, 'fe6-17a', 17, 'Ch.17A', 'The Path Through the Ocean'),
    (18, 'fe6-18a', 18, 'Ch.18A', 'The Frozen River'),
    (19, 'fe6-19a', 19, 'Ch.19A', 'Bitter Cold'),
    (20, 'fe6-20a', 20, 'Ch.20A', 'The Liberation of Ilia'),
    (36, 'fe6-20ax', 20, 'Ch.20Ax', 'The Frozen Spear'),
    (28, 'fe6-17b', 17, 'Ch.17B', "The Bishop's Teachings"),
    (29, 'fe6-18b', 18, 'Ch.18B', 'The Law of Sacae'),
    (30, 'fe6-19b', 19, 'Ch.19B', 'Battle in Bulgar'),
    (31, 'fe6-20b', 20, 'Ch.20B', 'The Silver Wolf'),
    (37, 'fe6-20bx', 20, 'Ch.20Bx', 'The Bow of the Winds'),
    (21, 'fe6-21', 21, 'Ch.21', 'The Binding Blade'),
    (38, 'fe6-21x', 21, 'Ch.21x', 'The Silencing Darkness'),
    (22, 'fe6-22', 22, 'Ch.22', 'The Neverending Dream'),
    (23, 'fe6-23', 23, 'Ch.23', 'The Ghosts of Bern'),
    (24, 'fe6-24', 24, 'Ch.24', 'The Truth of the Legend'),
    (25, 'fe6-final', 25, 'Final', 'Beyond the Darkness'),
]
TRIALS = [(40 + i, f'fe6-trial-{i + 1}', i + 1, f'Trial map {i + 1}') for i in range(5)]

# When the story reaches a chapter that not everyone plays: read from the end scripts (the checks before each "go to chapter"
# command), worded with Serenes Forest's gaiden page. Names are the patch's.
OPENS = {
    'fe6-8x': 'Opens after Chapter 8 if Lilina is alive.',
    'fe6-10a': "Played unless Chapter 9's right-most north-eastern village (the Restore) is visited: the one beside it, or neither.",
    'fe6-10b': "Played when Chapter 9's right-most north-eastern village (the Restore) is visited; visiting it closes the one beside it.",
    'fe6-12x': 'Opens if Chapter 12 is cleared within 20 turns with Elffin alive (if recruited).',
    'fe6-14x': 'Opens if Chapter 14 is cleared within 25 turns with Sophia alive.',
    'fe6-16x': 'Opens after Chapter 16 if Douglas is alive.',
    'fe6-17a': "Played when Thea and Juno have gained at least as much EXP as Sue and Sin (Serenes Forest; the game's own check is code).",
    'fe6-17b': "Played when Sue and Sin have gained more EXP than Thea and Juno (Serenes Forest; the game's own check is code).",
    'fe6-20ax': 'Opens if Chapter 20A is cleared within 25 turns with Juno and Zelot alive.',
    'fe6-20bx': 'Opens if Chapter 20B is cleared within 25 turns with Dayan, Sue and Sin alive.',
    'fe6-21x': 'Opens if Chapter 21 is cleared within 30 turns with Melady and Zeiss alive.',
    'fe6-23': 'Played only with every divine weapon and the Binding Blade in hand (unbroken); otherwise the game ends after Chapter 22.',
}

# Terrain ids -> the letters terrain_codes.py maps for 'fe6'; ids that work the same share a letter. Names are the app's.
TERRAIN = {
    0: ('#', 'Void'), 1: ('.', 'Plain'), 2: ('.', 'Road'), 3: ('v', 'Village'), 4: ('V', 'Closed village'), 5: ('B', 'House'),
    6: ('W', 'Armory'), 7: ('I', 'Vendor'), 8: ('R', 'Arena'), 10: ('F', 'Fort'), 11: ('g', 'Gate'), 12: ('f', 'Forest'),
    13: ('k', 'Thicket'), 14: ('y', 'Sand'), 15: ('s', 'Desert'), 16: ('w', 'River'), 17: ('m', 'Mountain'), 18: ('P', 'Peak'),
    19: ('b', 'Bridge'), 21: ('a', 'Sea'), 22: ('u', 'Lake'), 23: ('.', 'Floor'), 24: ('q', 'Floor (Res +10)'), 25: ('l', 'Fence'),
    26: ('#', 'Wall'), 27: ('#', 'Wall'), 29: ('p', 'Pillar'), 30: ('d', 'Door'), 31: ('t', 'Throne'), 33: ('c', 'Chest'),
    34: ('#', 'Roof'), 37: ('n', 'Ruins'), 38: ('C', 'Cliff'), 39: ('L', 'Ballista'), 40: ('L', 'Long ballista'),
    41: ('L', 'Killer ballista'),
    44: ('#', 'Wall'), 45: ('S', 'Stairs'), 46: ('C', 'Village wall'), 47: ('.', 'Glacier'), 49: ('z', 'Valley'),
}
AVOID, DEF, RES, HEAL = 0x60C978, 0x60C9AB, 0x60C9DE, 0x60CBA9
FLIER_AVOID, FLIER_DEF = 0x60CA11, 0x60CA44
# Movement types: classes whose cost rows are the same, named by who's in them (class ids). Female versions share their row.
MOVE_GROUPS = [
    ('Lords, heroes & thieves', [1, 4, 8, 18, 52, 67]),
    ('Infantry', [2, 6, 16, 48, 54, 55, 62, 65, 66]),
    ('Armours', [12, 14, 61]),
    ('Fighters', [10, 11]),
    ('Brigands', [49]),
    ('Pirates', [50]),
    ('Berserkers', [51]),
    ('Mages & priests', [20, 22, 24, 26, 28, 30]),
    ('Cavaliers', [32, 36]),
    ('Paladins', [34, 37]),
    ('Nomads', [38]),
    ('Nomad troopers', [40]),
    ('Fliers', [42, 43, 44, 46]),
    ('Dragons', [56, 58, 59, 60]),
]
ORDINAL = {2: 'second', 3: 'third', 4: 'fourth'}
PHASE = {0x00: 'your phase', 0x40: "the other army's phase", 0x80: 'enemy phase'}
SIDES = {'player': 'p', 'npc': 'n', 'enemy': 'e'}
DIFFS = ['Normal', 'Hard']

NAMES = character_names()
CLASSES = class_names()
ITEMS = item_names()


def char_record(c):
    """The 48-byte record of character id c (the table starts at id 1)."""
    return rom.CHARACTERS + 48 * (c - 1)


def is_boss(c):
    """The boss flag: bit 0x80 of the abilities' second byte (+0x29), set on each chapter's boss."""
    return bool(rom.u32(char_record(c) + 0x28) & 0x8000)


def has_portrait(c):
    return rom.u16(char_record(c) + 6) != 0


_ARMY = None


def personal(c):
    """A character the game names as a person: a name no army shares (gba_bosses.army_names), on a unit with a portrait or a
    boss's (Morva and Fomortiis have none)."""
    global _ARMY
    if _ARMY is None:
        _ARMY = gba_bosses.army_names({x: NAMES.get(x) for x in range(1, 0x100)}, has_portrait)
    return NAMES.get(c) not in _ARMY and (has_portrait(c) or is_boss(c))


def class_of(u):
    return u['class'] or R[char_record(u['char']) + 5]


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def article(name):
    return ('an ' if name[0].lower() in 'aeiou' else 'a ') + name


def flier_rows_are_zero():
    return set(R[FLIER_AVOID:FLIER_AVOID + 51]) == {0} and set(R[FLIER_DEF:FLIER_DEF + 51]) == {0}


def terrain_table(used):
    """One entry per terrain code: name, Def, Res, Avoid, healing and the cost for each movement type (None: can't enter)."""
    rows = {}
    for label, classes in MOVE_GROUPS:
        costs = {bytes(R[rom.class_(c)['move_cost']:rom.class_(c)['move_cost'] + 51]) for c in classes}
        assert len(costs) == 1, (label, classes)
        rows[label] = costs.pop()
    # Every class has a group, and no two groups share a row.
    for c in range(1, 68):
        if rom.u16(rom.CLASSES + 72 * c):
            row = bytes(R[rom.class_(c)['move_cost']:rom.class_(c)['move_cost'] + 51])
            assert row in rows.values(), (c, CLASSES.get(c))
    assert len(set(rows.values())) == len(rows)
    assert flier_rows_are_zero()
    info = {}
    for tid in sorted(used):
        letter, name = TERRAIN[tid]
        code = encode('fe6', letter)
        move = {label: (None if row[tid] == 255 else row[tid]) for label, row in rows.items()}
        signed = lambda o: R[o + tid] - 256 if R[o + tid] > 127 else R[o + tid]  # noqa: E731
        entry = {'name': name, 'def': signed(DEF), 'res': signed(RES), 'avo': signed(AVOID), 'heal': R[HEAL + tid], 'move': move}
        walkers = [v for k, v in move.items() if k != 'Fliers']
        if all(v is None for v in walkers):
            # Only fliers (and some dragons) enter: fliers get no Avoid or Def from terrain, so the ground row's numbers never apply.
            entry['def'] = entry['avo'] = 0
        if code in info:
            old = info[code]
            same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}
            nobody = all(v is None for v in move.values())
            assert same or nobody, (code, tid, old, entry)
            if name.lower() not in old['name'].lower():
                old['name'] += ' / ' + name.lower()
        else:
            info[code] = entry
    return info


def to_app(xy, height):
    """A tile from the top-left at (0, 0) -> the app's, from the bottom-left at (1, 1)."""
    return [xy[0] + 1, height - xy[1]]


def rect_to_app(r, height):
    x1, y1, x2, y2 = r
    return [x1 + 1, height - y2, x2 + 1, height - y1]


def tiles_of(entry):
    """(the map's tiles by [y][x], the tileset's terrain id for a tile)."""
    rec = rom.CHAPTERS + 68 * entry
    m = lz77(pointer(R[rec + 12]))
    tc = lz77(pointer(R[rec + 11]))
    w, h = m[0], m[1]
    return [[struct.unpack_from('<H', m, 2 + (y * w + x) * 2)[0] for x in range(w)] for y in range(h)], lambda t: tc[0x2000 + (t >> 2)]


def grid_of(entry):
    tiles, terrain = tiles_of(entry)
    return [[terrain(t) for t in row] for row in tiles]


ROOF = 34
# A location event with the door command (0x10) that runs a script: the doors that open together (Chapter 6's upper rooms).
DOOR_COMMAND = 0x10


def changes_of(ch, changes):
    """[(event, [change ids])]: what the chapter's other scripts change on the map (map change, 0x2A), besides its doors and
    its villages closing themselves: Chapter 1's raided village (the opening), Chapter 3's throne room on turn 3, Chapter 5's
    south-western wall and Chapter 22's temple (areas)."""
    out = []
    for e in ch.turns + ch.talks + ch.misc + ch.locations:
        if not (0x08000000 < e['ptr'] < 0x08800000) or e['type'] in (6, 7, 8, 10) or (e['type'] == 5 and e['b'][2] == DOOR_COMMAND):
            continue
        try:
            cmds = fe.script(e['ptr'])
        except AssertionError:
            continue
        cids = [gba_doors.change_at(changes, (a[0] & 0xFF, a[0] >> 8 & 0xFF)) for _, op, a in cmds if op == 0x2A]
        cids = [c for c in dict.fromkeys(cids) if c is not None]
        if cids and not any(e is f for f, _ in out):
            out.append((e, cids))
    return out


def hard_note(ch, rec):
    """Hard's growth the shown level doesn't count (scripts/fe6_events.py, HARD_LEVELS): the chapter record's +0x17 levels for every
    foe, but a foe the chapter starts with gets the number the game's list gives its character, where it has one (0 for the foes
    you can recruit). The stats are the class's growths (0x08017854)."""
    n = R[rec + 0x17]
    if not n:
        return None
    note = (f"On Hard, foes gain {n} levels' worth of their class's growth in HP, Str, Skl, Spd, Def, Res and Lck; their shown "
            'level stays the same.')
    own = fe.hard_levels()
    start = sorted({u['char'] for u in ch.opening(True).units if u['group'] == 'start' and u['side'] == 'enemy'
                    and own.get(u['char'], n) != n}, key=lambda c: NAMES.get(c, '?'))
    for v in sorted({own[c] for c in start}):
        who = [NAMES.get(c, '?') for c in start if own[c] == v]
        names = ' and '.join(who) if len(who) < 3 else ', '.join(who[:-1]) + ' and ' + who[-1]
        gain = ('gains' if len(who) == 1 else 'gain') + (' none' if v == 0 else f' {v}')
        note += f' {names} {gain}.'
    return note


def fog_notes(ch):
    """[(event, 'The fog lifts on turn 26, your phase.')]: a turn event whose script calls the routine that lifts the fog."""
    out = []
    for e in ch.turns:
        if e['type'] not in (2, 3) or not (0x08000000 < e['ptr'] < 0x08800000):
            continue
        if any(op in (0x17, 0x19) and a and a[0] | 1 == fe.FOG_OFF for _, op, a in fe.script(e['ptr'])):
            when = turn_text(e)
            out.append((e, f'The fog lifts on {when[0].lower()}{when[1:]}.' if when.startswith('Turn') else f'The fog lifts: {when}.'))
    return out


# A boss's death quote sets flag 2 (scripts/gba_bosses.py), which a Hard-only turn event (type 3) needs clear: its groups stop once
# the chapter's boss is defeated (0x0806A9DC tests it).
BOSS_DOWN = gba_bosses.BOSS_DOWN


def area_who(e):
    """Who sets an area event off. The check after each action (0x0806B500, run for any army's unit) reads the acting unit's tile
    alone (0x0806ABD0), so any unit stopping there does, unless the script's first branch tests your phase and otherwise clears the
    event's flag to wait for the next (fe6_events.YOUR_PHASE): then one of your units."""
    try:
        cmds = fe.script(e['ptr'])
    except AssertionError:
        return 'a unit of any army'
    if cmds and cmds[0][1] in (0x1F, 0x20) and cmds[0][2][1] | 1 == fe.YOUR_PHASE:
        return 'one of your units'
    return 'a unit of any army'


def place(ch, e):
    """'the village at (4, 19)': what a location event's tile is, named as the map shows it."""
    x, y = e['b'][0] + 1, ch.h - e['b'][1]
    if e['type'] == 5:
        kind = 'seize point' if e['b'][2] == 0x0F else 'house'
    else:
        kind = {6: 'village', 7: 'chest', 8: 'door', 10: 'shop'}.get(e['type'], 'tile')
    return f'the {kind} at ({x}, {y})'


def visited(ch, e):
    """'Roy seizes the seize point at (4, 19)', 'the village at (4, 19) is visited', 'the door at (4, 19) is opened'."""
    if e['type'] == 5 and e['b'][2] == 0x0F:
        return f'Roy seizes {place(ch, e)}'
    return f"{place(ch, e)} is {'opened' if e['type'] in (7, 8) else 'visited'}"


def change_words(ch, e, patch, letters):
    """'Turn 3, enemy phase: the closed room opens.' An area's is named by its tiles."""
    when, areas = arrival_of(ch, e)
    if areas and e['type'] == 11:
        l, b, r, t = areas[0]['rect']
        when = f"As soon as {area_who(e)} stops in the area at ({l}, {b})" + (f"–({r}, {t})" if (l, b) != (r, t) else '')
    what = gba_doors.what_opens([letters[y][x] for (x, y), _ in patch], [c for _, c in patch])
    return f'{when}: {what}.'


def event_marker(e, patch, h):
    """Where an event's change is marked: the changed tile nearest its area, else a door it opens, else its middle."""
    tiles = [t for t, _ in patch]
    if e['type'] == 11:
        x1, y1, x2, y2 = e['b']
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    else:
        cx, cy = sum(x for x, _ in tiles) / len(tiles), sum(y for _, y in tiles) / len(tiles)
    best = min(tiles, key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t[1], t[0]))
    return to_app(best, h)


def doors_of(ch, changes):
    """[(door tile, [change ids])]: a door event (type 8) applies the change under its tile; a scripted one (type 5 with the
    door command) the changes at the tiles its script names (0x2A)."""
    out = {}
    for e in ch.locations:
        xy = (e['b'][0], e['b'][1])
        if e['type'] == 8:
            cids = [gba_doors.change_at(changes, xy)]
        elif e['type'] == 5 and e['b'][2] == DOOR_COMMAND and 0x08000000 < e['ptr'] < 0x08800000:
            cids = [gba_doors.change_at(changes, (a[0] & 0xFF, a[0] >> 8 & 0xFF)) for _, op, a in fe.script(e['ptr']) if op == 0x2A]
        else:
            continue
        out.setdefault(xy, [c for c in cids if c is not None])
    return [(xy, cids) for xy, cids in out.items() if cids]


def pointer(i):
    return rom.off(rom.u32(rom.POINTERS + 4 * i))


def lz77(o):
    """GBA BIOS LZ77 (type 0x10)."""
    assert R[o] == 0x10
    size, out, p = rom.u32(o) >> 8, bytearray(), o + 4
    while len(out) < size:
        flags = R[p]
        p += 1
        for b in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> b):
                v = (R[p] << 8) | R[p + 1]
                p += 2
                for _ in range((v >> 12) + 3):
                    out.append(out[-((v & 0xFFF) + 1)])
            else:
                out.append(R[p])
                p += 1
    return bytes(out)


class Chapter:
    """Everything one chapter entry's events say, worked out once."""

    def __init__(self, entry, map_id, height):
        self.entry, self.map_id, self.h = entry, map_id, height
        self.ev = fe.events_of(entry)
        self.turns = fe.event_list(self.ev['turn'])
        self.talks = fe.event_list(self.ev['talk'])
        self.locations = fe.event_list(self.ev['location'])
        self.misc = fe.event_list(self.ev['misc'])
        self.prep = R[rom.CHAPTERS + 68 * entry + 0x11]

    def opening(self, hard, army=False):
        """Plays the chapter's start: the enemies of slot 4, then each turn-1 event on your phase (the Hard-only ones on Hard).
        Where no script places your army (the Final Chapter's code does), its group is placed first."""
        run = fe.Run(fe.World(hard=hard))
        for u in fe.unit_group(self.ev['enemies']):
            run.units.append({**u, 'tile': u['end'], 'group': 'start', 'army': False})
        if army:
            for u in fe.unit_group(self.ev['army']):
                run.units.append({**u, 'tile': u['end'], 'group': 'army', 'army': True})
        for e in self.turns:
            if self.is_opening(e, hard):
                run.run(e['ptr'])
        if not army and not any(u['side'] == 'player' for u in run.units):
            return self.opening(hard, army=True)
        return run

    @staticmethod
    def is_opening(e, hard):
        b = e['b']
        return (e['type'] == 2 or (e['type'] == 3 and hard)) and b[0] == 1 and b[2] == 0


def turn_text(e):
    first, last, phase = e['b'][0], e['b'][1], e['b'][2]
    p = PHASE[phase]
    if last == 255 or (last > first and e['flag'] == 0 and last - first > 30):
        return f'Every turn from {first}, {p}' if first > 1 else f'Every turn, {p}'
    if last > first and e['flag'] == 0:
        return f'Every turn from {first} to {last}, {p}'
    return f'Turn {first}, {p}'


def main():
    maps, sources = [], {}
    used_terrain = set()
    held = {}  # (item, map id, kind, words) -> the difficulties the line holds on

    def source(item, map_id, kind, words, ds=None):
        """`ds`: the difficulties of the placed unit the line comes from (None: both, as for anything else)."""
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)
        held.setdefault((item_name(item), map_id, kind, words), set()).update(DIFFS if ds is None else ds)

    closed_rooms = False
    for entry, map_id, number, heading, title in STORY + [(e, i, n, h, None) for e, i, n, h in TRIALS]:
        tiles, terrain_of = tiles_of(entry)
        grid = [[terrain_of(t) for t in row] for row in tiles]
        h, w = len(grid), len(grid[0])
        for row in grid:
            used_terrain |= set(row)
        unknown = {t for row in grid for t in row} - set(TERRAIN)
        assert not unknown, (map_id, unknown)
        rec = rom.CHAPTERS + 68 * entry
        # The doors: what each opens, previewed; a room under its roof is closed until a door into it opens.
        changes = gba_doors.read_changes(R, pointer(R[rec + 15]) if R[rec + 15] else None)
        letters = [[TERRAIN[t][0] for t in row] for row in grid]
        letter_of = lambda t: TERRAIN[terrain_of(t)][0]  # noqa: E731
        ch = Chapter(entry, map_id, h)
        doors = doors_of(ch, changes)
        events = changes_of(ch, changes)
        # The opening's changes are made before the battle: the map starts with them.
        for e, cids in events:
            if Chapter.is_opening(e, False):
                gba_doors.apply(changes, letters, letter_of, cids)
        events = [(e, cids) for e, cids in events if not Chapter.is_opening(e, False)]
        # Cracked walls: the chapter record's wall HP (+0x1D: 0x08026C7E reads +0x19 of the record from 0x086637A4).
        broken = gba_doors.breakables(changes, grid, R[rec + 0x1D])
        cracks = [(('break', xy), [gba_doors.change_at(changes, xy)]) for xy, _, _ in broken]
        previews = gba_doors.previews(changes, letters, letter_of, doors + [(id(e), cids) for e, cids in events] + cracks,
                                      lambda xy: grid[xy[1]][xy[0]] == ROOF)
        for cid in {c for _, cids in doors + events + cracks for c in cids} | {c for e, cids in changes_of(ch, changes) for c in cids}:
            used_terrain |= {terrain_of(t) for t in changes[cid][4] if t}
        closed_rooms |= any('Q' in row for row in letters)
        location = en(rom.u16(rec + 0x40)) if rom.u16(rec + 0x40) else ''
        trial = title is None
        if trial:
            title = en(rom.u16(rec + 0x3C))
        goal = en(rom.u16(rec + 0x34))
        m = {
            'id': map_id, 'route': 'Trial' if trial else 'Story', 'chapter': number, 'heading': heading, 'title': title,
            **({'location': location} if location else {}), 'width': w, 'height': h,
            'grid': [''.join(encode('fe6', c) for c in row) for row in letters],
            **({'fog': True} if R[rec + 0x10] else {}),
            'victory': goal, 'defeat': 'Roy is defeated', 'objectives': [], 'units': [], 'starts': [], 'objects': [], 'changes': [],
            'notes': [], 'lord': 'Roy',
        }
        if map_id in OPENS:
            m['notes'].append(OPENS[map_id])
        for e, note in fog_notes(ch):
            if e['type'] == 3:
                m.setdefault('notesOn', []).append({'note': note, 'difficulties': ['Hard']})
            else:
                m['notes'].append(note)
        hard = hard_note(ch, rec)
        if hard:
            m.setdefault('notesOn', []).append({'note': hard, 'difficulties': ['Hard']})
        for door, _ in doors:
            patch = previews[door]
            others = [t for t, _ in patch if t != door and letters[t[1]][t[0]] == 'd']
            m['changes'].append(gba_doors.door_change(to_app(door, h), [(to_app(t, h), encode('fe6', c)) for t, c in patch],
                                                      [to_app(t, h) for t in others]))
        for xy, hp, kind in broken:
            patch = previews[('break', xy)]
            if patch:
                m['changes'].append(gba_doors.breakable_change(to_app(xy, h), hp, kind, [(to_app(t, h), encode('fe6', c)) for t, c in patch]))
        for e, _ in events:
            patch = previews[id(e)]
            if not patch:
                continue
            m['changes'].append(gba_doors.event_change(event_marker(e, patch, h), [(to_app(t, h), encode('fe6', c)) for t, c in patch],
                                                       change_words(ch, e, patch, letters)))
        gba_doors.unique_ids(m['changes'])
        build_units(ch, m, source)
        build_locations(ch, m, source)
        # Only the chapter's own boss keeps the skull (its seize tiles are in by now): one who leaves the map, or whose death
        # doesn't set the boss's flag here, is a named foe.
        gba_bosses.settle(m, gba_bosses.boss_down('fe6', R, entry), lambda c: not personal(c))
        # Looters and the units that leave the map, with the exits they head for.
        gba_ai.settle(m, AI, entry, lambda xy: to_app(xy, h))
        maps.append(m)
        print(map_id, title, f'{w}x{h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    info = terrain_table(used_terrain)
    if closed_rooms:
        # The game's table lets fliers over a roof, but a room under its roof is closed to everyone until a door into it opens
        # (the user's rule, from Path of Radiance: the same tiles there).
        info[encode('fe6', 'Q')] = {'name': 'Roof (closed room)', 'def': 0, 'res': 0, 'avo': 0, 'heal': 0,
                                    'move': {label: None for label, _ in MOVE_GROUPS},
                                    'note': 'A room under its roof: no unit can enter it, fliers included, until a door into it opens.'}
    examples = {label: ', '.join(sorted({CLASSES[c] for c in classes if CLASSES.get(c)})) for label, classes in MOVE_GROUPS}
    write_terrain(info, examples)
    write_maps(maps)
    mark_difficulties(sources, held)
    write_sources(sources)


def unit_entry(u, h, talk=None):
    """A map unit from a placed unit record."""
    c = u['char']
    cls = CLASSES.get(class_of(u), '?')
    name = NAMES.get(c, '?')
    items = [item_name(i) for i in u['items']]
    if u['side'] == 'enemy':
        kind = 'boss' if is_boss(c) else 'named' if personal(c) else 'enemy'
    else:
        kind = 'ally'
    # A generic boss (the trial maps' Bandit, a stand-in name) goes by its class, as any other generic does.
    named = personal(c) and kind != 'enemy'
    out = {'type': kind, 'name': name if named else cls, 'tile': to_app(u['tile'], h),
           'note': f"Lv {u['level']} {cls}" if named else f"Lv {u['level']}"}
    if kind == 'boss':
        out['_char'] = c  # which skull stays is settled once the whole map is in (gba_bosses.settle)
    if kind == 'ally' and not named:
        out['generic'] = True
    if items:
        out['carries'] = items
    if talk:
        out['talk'] = talk
    # What its movement AI does (scripts/gba_ai.py: the abilities are the character's +0x28 and the class's +0x24), said once the
    # map's villages and chests are in (gba_ai.settle).
    ai = gba_ai.of(AI, u, rom.character(c)['abilities'] | rom.class_(class_of(u))['abilities'])
    if ai:
        out['_ai'] = ai
    return out


def talks_of(ch):
    """{name: 'Recruit: talk with Roy or Clarine'} from the talk events (and the coded talks). Keyed by name: a talk names a
    character's own id while the unit on the map can be its enemy version (Gonzalez in Chapter 10B)."""
    found = {}
    for e in ch.talks:
        if e['type'] == 4:
            a, b = e['b'][0], e['b'][1]
        elif e['type'] == 13:
            c = fe.check(rom.u32(e['at'] + 8))
            if c[0] != 'talk':
                continue
            a, b = c[1], c[2]
        else:
            continue
        run = fe.Run(fe.World(active=a)).run(e['ptr'])
        t = found.setdefault(NAMES.get(b, '?'), {'recruit': [], 'talk': [], 'gives': [], 'when': None})
        who = NAMES.get(a, '?')
        cmds = fe.script(e['ptr'])
        if b in run.recruits:
            t['recruit'].append(who)
        elif any(op == 0x2B and args == [b, 0] for _, op, args in cmds):
            # Recruited only on a branch the plain run doesn't take: after paying gold, or on a later talk (flags it sets).
            t['recruit'].append(who)
            checks = [fe.check(args[1]) for _, op, args in cmds if op in (0x1F, 0x20)]
            golds = sorted({c[1] + 1 for c in checks if c[0] == 'gold_over'}, reverse=True)
            flags = [args[1] for _, op, args in cmds if op == 0x22]
            if golds:
                t['when'] = (f"for gold: {golds[0]:,} if you hold that much, otherwise "
                             f"{', '.join(f'{g:,}' for g in golds[1:-1])} or {golds[-1]:,}, by what you hold")
            elif flags:
                t['when'] = f'on the {ORDINAL[len(flags) + 1]} talk, counting one per chapter'
        else:
            t['talk'].append(who)
            t['gives'] += [item_name(i) for i, _ in run.items]
    out = {}
    for name, t in found.items():
        if t['recruit']:
            out[name] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(t['recruit'])) + (f" ({t['when']})" if t['when'] else '')
        else:
            out[name] = 'Talk with ' + ' or '.join(dict.fromkeys(t['talk'])) + (f" (gives {', '.join(t['gives'])})" if t['gives'] else '')
    return out


def build_units(ch, m, source):
    h = m['height']
    talks = talks_of(ch)
    # What a talk hands over (Chapter 8: Roy and Lilina, a Thunder tome).
    for e in ch.talks:
        if e['type'] == 4 and 0x08000000 < e['ptr'] < 0x08800000:
            run = fe.Run(fe.World(active=e['b'][0])).run(e['ptr'])
            for i, _ in run.items:
                # A gift a talk hands over mid-battle is yours from the next chapter.
                source(i, m['id'], 'talk-later', f"{NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}")
    runs = {d: ch.opening(d == 'Hard') for d in DIFFS}
    # What the opening hands over before the battle is yours from this chapter.
    for d, run in runs.items():
        for i, who in run.items:
            source(i, m['id'], 'gift', f"Given to {NAMES.get(who, 'your army')} at the start of the chapter", ds=[d])
    ch.closed = set(runs['Normal'].map_changes)
    placed = {}
    for d, run in runs.items():
        for u in run.units:
            key = (u['char'], class_of(u), u['tile'], tuple(u['items']), u['side'], u['army'])
            placed.setdefault(key, (u, []))[1].append(d)
    army = [(u, ds) for u, ds in placed.values() if u['army']]
    roy = next((u for u, _ in army if u['char'] == 1), None) or next((u for u, _ in placed.values() if u['char'] == 1), None)
    if army:
        m['starts'] = [to_app(u['tile'], h) for u, _ in army]
    if roy:
        m['corrinStart'] = to_app(roy['tile'], h)
        if not army:
            m['starts'] = [m['corrinStart']]
    forced = []
    by_code = any(u['group'] == 'army' for u, _ in placed.values())
    if by_code:
        m.setdefault('unconfirmed', []).append(
            "Who starts here is placed by the game's code, not a script (the army group's names are stand-ins), so the units aren't named.")
    for u, ds in placed.values():
        if u['army']:
            if not ch.prep and not by_code and u['char'] != 1:
                forced.append({'name': NAMES.get(u['char'], '?'), 'tile': to_app(u['tile'], h)})
            continue
        if u['side'] == 'player':
            if u['char'] != 1:
                forced.append({'name': NAMES.get(u['char'], '?'), 'tile': to_app(u['tile'], h)})
                for i in u['items']:
                    source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining", ds=ds)
            continue
        e = unit_entry(u, h, talks.get(NAMES.get(u['char'], '?')))
        if m['victory'] == f"Defeat {e['name']}":
            e['type'] = 'boss'
        if len(ds) == 1:
            e['difficulties'] = ds
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit') and '(' not in e['talk']:
            # A foe a talk recruits joins mid-battle: what it carries is yours from the next chapter.
            for i in u['items']:
                source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining", ds=ds)
        elif e['type'] in ('boss', 'named') and u['side'] == 'enemy' and personal(u['char']):
            for i in u['items']:
                source(i, m['id'], 'foe', f"Carried by {e['name']}, a foe", ds=ds)
        elif u['side'] == 'enemy':
            for i in u['items']:
                source(i, m['id'], 'foe-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')}", ds=ds)
    if forced:
        m['forced'] = forced
    # Units the opening places that a later turn event takes off the map (Zephiel in Chapter 13).
    leaves = {}
    for e in ch.turns:
        if Chapter.is_opening(e, e['type'] == 3) or not (0x08000000 < e['ptr'] < 0x08800000):
            continue
        cmds = fe.script(e['ptr'])
        if any(op == 0x3D for _, op, _ in cmds):
            continue  # the chapter's end clears the map: no one leaves early
        for _, op, args in cmds:
            if op == 0x30:
                leaves.setdefault(NAMES.get(args[0], '?'), turn_text(e))
    for u in m['units']:
        if u['type'] != 'enemy' and u['name'] in leaves:
            u['note'] = f"{u['note']}; leaves the map: {leaves[u['name']].lower()}"
            u['_leaves'] = True
    build_arrivals(ch, m, source, talks)
    # The bosses whose fall stops a group: those the chapter places, at the start or later, whose death sets flag 2.
    down = {NAMES.get(c) for c in gba_bosses.boss_down('fe6', R, ch.entry)}
    bosses = list(dict.fromkeys(u['name'] for u in m['units'] + [u for g in m.get('reinforcements', []) for u in g['units']]
                                if u['type'] == 'boss' and u['name'] in down))
    named = ' or '.join(bosses) if len(bosses) < 3 else ', '.join(bosses[:-1]) + ' or ' + bosses[-1]
    for g in m.get('reinforcements', []):
        g['when'] = ({d: w.replace('{boss}', named or 'the boss') for d, w in g['when'].items()} if isinstance(g['when'], dict)
                     else g['when'].replace('{boss}', named or 'the boss'))



def flag_events(ch, flag):
    """The events whose own flag it is (set as each fires)."""
    return [e for e in ch.turns + ch.talks + ch.locations + ch.misc if e['flag'] == flag and e['type'] != 1]


def describe_flag(ch, flag):
    """What sets a flag: the event whose own flag it is."""
    for e in flag_events(ch, flag):
        if e['type'] in (2, 3):
            return turn_text(e)
        if e['type'] == 4:
            return f"once {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}"
        if e['type'] in (5, 6, 7, 8):
            return f'once {visited(ch, e)}'
        if e['type'] == 11:
            return f'once {area_who(e)} stops in the marked area'
        if e['type'] == 13:
            what = arrival_of(ch, e)[0]
            if what != 'When an event in the chapter fires':
                return what[0].lower() + what[1:]
    return None


def display_name(c):
    """How the map names a character's unit: its name, or 'the Berserker' for one an army's name stands for (gba_bosses)."""
    return NAMES.get(c, '?') if personal(c) else f"the {CLASSES.get(R[char_record(c) + 5], '?')}"


def until(text):
    """'once Roy seizes ...' as 'until Roy seizes ...'."""
    return 'until ' + text[len('once '):] if text.startswith('once ') else f'until {text}'


def flags_text(ch, check):
    """Chapter 24's checks: 'Enemy phase of every even turn, once Roy seizes the seize point at (19, 2) and until Roy seizes the
    seize point at (8, 3)'. A flag no event sets is left for the map's unconfirmed notes (unsaid_flags)."""
    _, phase, flags_set, flags_clear, parity = check
    when = PHASE.get(phase, 'any phase') if phase is not None else 'any phase'
    when = when[0].upper() + when[1:] + (f' of every {parity} turn' if parity else '')
    said = [describe_flag(ch, f) for f in flags_set] + [until(describe_flag(ch, f)) for f in flags_clear if describe_flag(ch, f)]
    return ', '.join([when] + [x for x in said if x])


def unsaid_flags(ch, check):
    return [f for f in check[2] + check[3] if not describe_flag(ch, f)] if check[0] == 'flags' else []


def arrival_of(ch, e):
    """(when, areas) for an event that brings units in."""
    t = e['type']
    if t in (2, 3):
        return turn_text(e), None
    if t == 1:
        flag = rom.u16(e['at'] + 8)
        # A flag the chapter's areas set as they fire (Chapter 7's two): those areas bring the group.
        setters = [x for x in flag_events(ch, flag) if x['type'] == 11]
        if setters:
            areas = [{'who': 'player', 'rect': rect_to_app(tuple(x['b']), ch.h)} for x in setters]
            where = 'a marked area' if len(setters) > 1 else 'the marked area'
            return f'As soon as {area_who(setters[0])} stops in {where}', areas
        what = describe_flag(ch, flag)
        if what and what.startswith('once '):
            what = 'when ' + what[len('once '):]
        return (what[0].upper() + what[1:] if what else 'After an event in the chapter'), None
    if t == 4:
        return f"When {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}", None
    if t == 11:
        x1, y1, x2, y2 = e['b']
        return f'As soon as {area_who(e)} stops in the marked area', [{'who': 'player', 'rect': rect_to_app((x1, y1, x2, y2), ch.h)}]
    if t == 13:
        c = fe.check(rom.u32(e['at'] + 8))
        if c[0] == 'units_in':
            _, phase, rects, negated = c
            p = PHASE.get(phase, 'any phase') if phase is not None else 'any phase'
            areas = [{'who': 'player', 'rect': rect_to_app(r, ch.h)} for r in rects]
            word = 'once none of your units is left in the marked area' if negated else 'once one of your units is in the marked area'
            return f"{p[0].upper() + p[1:]}, {word}", areas
        if c[0] == 'talk':
            return f"When {NAMES.get(c[1], '?')} talks to {NAMES.get(c[2], '?')}", None
        if c[0] == 'flags':
            return flags_text(ch, c), None
        if c[0] == 'no_other':
            return 'Once no unit of another army is left', None
        if c[0] == 'flag_gone':
            what = describe_flag(ch, c[1])
            return ((what[0].upper() + what[1:] + ' and ' if what else 'Once ') + f'{display_name(c[2])} is defeated'), None
        return 'When an event in the chapter fires', None
    if t in (5, 6):
        return f'When {visited(ch, e)}', None
    return 'During the chapter', None


def stops_with_boss(e):
    """Whether an event's groups stop once the chapter's boss is defeated (flag 2): a Hard-only turn event, or a script that skips
    its load once the flag is set (Chapter 5's area event)."""
    if e['type'] == 3:
        return True
    try:
        return any(op == 0x22 and a[1] == BOSS_DOWN for _, op, a in fe.script(e['ptr']))
    except AssertionError:
        return False


def build_arrivals(ch, m, source, talks):
    h = m['height']
    groups, joiners = [], []
    events = [(e, 'Hard' if e['type'] == 3 else None) for e in ch.turns if not Chapter.is_opening(e, e['type'] == 3)]
    events += [(e, None) for e in ch.talks + ch.misc + ch.locations if e['type'] in (1, 4, 5, 6, 11, 13)]
    n = 0
    for e, only in events:
        if not (0x08000000 < e['ptr'] < 0x08800000):
            continue
        # Played on each difficulty it fires on: a script can test for Hard mode itself (Chapter 5's area event places its four
        # foes on Hard only).
        on = {}
        try:
            for d in ([only] if only else DIFFS):
                on[d] = fe.Run(fe.World(hard=d == 'Hard', turn=e['b'][0] if e['type'] in (2, 3) else 1)).run(e['ptr'])
        except AssertionError:
            continue
        if not any(run.loads for run in on.values()):
            continue
        when, areas = arrival_of(ch, e)
        if e['type'] == 13:
            for f in unsaid_flags(ch, fe.check(rom.u32(e['at'] + 8))):
                note = (f"The groups that wait on flag {f} stop once it's set as well; no event in the chapter sets it, and what does "
                        "wasn't traced.")
                if note not in m.setdefault('unconfirmed', []):
                    m['unconfirmed'].append(note)
        if stops_with_boss(e):
            when += ', until {boss} is defeated'  # named once every group is in (Chapter 3's boss arrives with one)
        # One group per difficulty where they differ; one where they're the same.
        by_units = {}
        for d, run in on.items():
            key = tuple((u['char'], class_of(u), u['tile'], u['side'], tuple(u['items'])) for u in run.units)
            by_units.setdefault(key, (run, []))[1].append(d)
        for run, ds in by_units.values():
            ds = ds if len(ds) < len(DIFFS) else None
            foes = [u for u in run.units if u['side'] == 'enemy']
            friends = [u for u in run.units if u['side'] != 'enemy']
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': ({d: when for d in ds} if ds else when),
                     'units': [{**unit_entry(u, h, talks.get(NAMES.get(u['char'], '?'))), 'from': to_app(u['start'], h)} for u in foes]}
                if areas:
                    g['areas'] = areas
                if ds:
                    for u in g['units']:
                        u['difficulties'] = ds
                g['_event'] = e['at']  # one group per arrival (gba_maps.one_per_arrival)
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if (entry.get('talk') or '').startswith('Recruit') and '(' not in entry['talk']:
                        for i in u['items']:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining", ds=ds)
                    elif entry['type'] in ('boss', 'named') and personal(u['char']):
                        for i in u['items']:
                            source(i, m['id'], 'foe-later', f"Carried by {entry['name']}, a foe arriving mid-chapter", ds=ds)
                    else:
                        for i in u['items']:
                            source(i, m['id'], 'foe-later-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')} arriving mid-chapter",
                                   ds=ds)
            for u in friends:
                if u['army']:
                    continue
                named = has_portrait(u['char'])
                j = {'name': NAMES.get(u['char'], '?') if named else CLASSES.get(class_of(u), '?'), 'tile': to_app(u['tile'], h),
                     'from': to_app(u['start'], h), 'group': f"e{e['at']:x}", 'when': when}
                if areas:
                    j['areas'] = areas
                if u['side'] == 'npc':
                    j['ally'] = True
                    if not named:
                        j['generic'] = True
                    if NAMES.get(u['char']) in talks:
                        j['talk'] = talks[NAMES.get(u['char'])]
                    ai = gba_ai.of(AI, u, rom.character(u['char'])['abilities'] | rom.class_(class_of(u))['abilities'])
                    if ai:
                        j['_ai'] = ai
                else:
                    for i in u['items']:
                        source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining", ds=ds)
                joiners.append(j)
    if groups:
        m['reinforcements'] = gba_maps.one_per_arrival(groups, DIFFS)
    if joiners:
        m['joiners'] = joiners


def reward_of(ptr):
    """What a village or house gives, from its script: items, gold, a recruit. Visitors the script tells apart get their own."""
    base = fe.Run(fe.World()).run(ptr)
    whos = sorted({args[1] for _, op, args in fe.script(ptr) if op == 0x24})

    def words(run):
        return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])

    plain = words(base)
    special = {}
    for c in whos:
        w = words(fe.Run(fe.World(active=c)).run(ptr))
        if w != plain:
            special.setdefault(w, []).append(NAMES.get(c, '?'))
    if not special:
        return plain, [i for i, _ in base.items]
    parts = [f"{w} if visited by {' or '.join(names)}" for w, names in special.items()]
    items = [i for i, _ in base.items] + [i for c in whos for i, _ in fe.Run(fe.World(active=c)).run(ptr).items]
    return '; '.join(parts) + (f'; anyone else: {plain}' if plain else ''), items


SHOP = {0x13: 'Armory', 0x14: 'Vendor', 0x15: 'Secret shop'}


def build_locations(ch, m, source):
    h = m['height']
    seize = []
    seen = set()
    villages = {(e['b'][0], e['b'][1]) for e in ch.locations if e['type'] == 6}
    for e in ch.locations:
        # Some events are listed twice (Chapter 11B's village).
        key = (e['type'], e['b'][0], e['b'][1], e['b'][2])
        if key in seen:
            continue
        seen.add(key)
        x, y, cmd = e['b'][0], e['b'][1], e['b'][2]
        tile = to_app((x, y), h)
        t = e['type']
        if t == 5 and cmd == 0x0F:
            seize.append(tile)
        elif t == 7:
            arg = e['ptr']
            if arg & 0xFFFF == 0x6F:
                contents = f'{arg >> 16} gold'
            else:
                contents = item_name(arg)
                source(arg, m['id'], 'chest', 'In a chest')
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': contents})
        elif t == 8 or (t == 5 and cmd == DOOR_COMMAND):
            m['objects'].append({'type': 'door', 'tile': tile})
        elif t == 10 and cmd in SHOP:
            o, stock = rom.off(e['ptr']), []
            while rom.u16(o):
                stock.append(rom.u16(o))
                o += 2
            m['objects'].append({'type': 'shop', 'tile': tile, 'kind': SHOP[cmd], 'stock': [item_name(i) for i in stock]})
            for i in stock:
                source(i, m['id'], 'shop', f"Sold at the {SHOP[cmd].lower()}")
        elif (t == 6 or (t == 5 and cmd == 0x0E)) and 0x08000000 < e['ptr'] < 0x08800000:
            # A village the opening closes (the brigand's in Chapter 1: the map change on it or the tile above) is gone.
            if t == 6 and ({(x, y), (x, y - 1)} & getattr(ch, 'closed', set())):
                continue
            reward, items = reward_of(e['ptr'])
            run = fe.Run(fe.World()).run(e['ptr'])
            closes = [to_app(v, h) for c in run.map_changes for v in ((c[0], c[1]), (c[0], c[1] + 1)) if v in villages and v != (x, y)]
            joins = [NAMES.get(u['char'], '?') for _, _, grp in run.loads for u in grp if u['side'] == 'player']
            if t == 5 and not reward and not joins:
                continue
            o = {'type': 'village', 'tile': tile, 'reward': reward}
            notes = ([f"{' and '.join(joins)} {'joins' if len(joins) == 1 else 'join'} your army."] if joins else [])
            notes += [f'Visiting it closes the village at ({c[0]}, {c[1]}).' for c in closes]
            if t == 5:
                notes.append('(A house.)')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i in items:
                source(i, m['id'], 'village', 'Given at a village' if t == 6 else 'Given at a house')
    if seize:
        what = 'the throne' if 'throne' in m['victory'].lower() else 'the gate'
        m['objectives'].append({'type': 'seize', 'tiles': seize, 'label': f'Seize {what} with Roy'})
    # Hidden items: area events whose script gives one (the desert in Chapter 14).
    for e in ch.misc:
        if e['type'] != 11 or not (0x08000000 < e['ptr'] < 0x08800000):
            continue
        cmds = fe.script(e['ptr'])
        gives = [args[0] for _, op, args in cmds if op == 0x26]
        if not gives:
            continue
        x1, y1, x2, y2 = e['b']
        area = rect_to_app((x1, y1, x2, y2), h)
        checks = [fe.check(args[1]) for _, op, args in cmds if op in (0x1F, 0x20)]
        note = None
        finders = [NAMES.get(args[1], '?') for _, op, args in cmds if op == 0x24]
        if finders:
            # Anyone else clears the event's flag, so it stays until the right unit stops there.
            note = f"Found only by {' or '.join(finders)}, by stopping in the area."
        elif any(c == ('code', 0x0806D029) for c in checks):
            note = ('Found by a unit that waits in the area on your phase: a thief always finds it, anyone else one time in 11 '
                    '(a random number divided by 11 leaving 0).')
        o = {'type': 'hidden', 'tile': [(area[0] + area[2]) // 2, (area[1] + area[3]) // 2], 'area': area,
             'contents': ', '.join(item_name(i) for i in gives)}
        if note:
            o['note'] = note
        m['objects'].append(o)
        for i in gives:
            source(i, m['id'], 'hidden', 'Hidden in the sand')
    # The end of the chapter: gifts the end script hands over (Durandal, the Binding Blade), and who joins there (Fa).
    for _, op, args in fe.script(ch.ev['end']):
        if op == 0x27:
            source(args[1], m['id'], 'event-later', f'Given to {NAMES.get(args[0], "?")} at the end of the chapter')
        if op == 0x12:
            for u in fe.unit_group(args[0]):
                if u['side'] == 'player':
                    for i in u['items']:
                        source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')}, who joins at the end of the chapter")


def write_terrain(info, examples):
    lines = [
        "import type { TerrainInfo } from '../maps/fatesTerrain'",
        "import type { TerrainCode } from '../maps/terrainCodes'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe6-maps.py from The Binding Blade's terrain and movement cost tables. Do not edit by hand.",
        ' */',
        '',
        '/** Movement types the game gives different costs: classes in a group pay the same on every terrain. */',
        'export const FE6_MOVE_CLASSES = ' + json.dumps([label for label, _ in MOVE_GROUPS]) + ' as const',
        '',
        'export const FE6_MOVE_CLASS_EXAMPLES: Record<string, string> = ' + json.dumps(examples, indent=2, ensure_ascii=False),
        '',
        "/** Def, Res, Avoid, healing and movement cost (null = can't enter) by terrain code. Fliers get no Def or Avoid from terrain. */",
        'export const FE6_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {',
    ]
    lines += [f'  {code}: {json.dumps(entry, ensure_ascii=False)},' for code, entry in info.items()]
    lines.append('}')
    write('fe6Terrain.ts', lines)


def write_maps(maps):
    lines = [
        "import type { ChapterMap } from '../maps/types'",
        "import { FE6_TERRAIN } from './fe6Terrain'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe6-maps.py from The Binding Blade's own chapter records and events. Do not edit by hand.",
        ' */',
        '',
        'const RAW = [',
    ]
    lines += ['  ' + json.dumps(m, ensure_ascii=False) + ',' for m in maps]
    lines += [']', '', 'export const FE6_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE6_TERRAIN }))']
    write('fe6Maps.ts', lines)


def mark_difficulties(sources, held):
    """Each source line that holds on one difficulty only says which. `held`: (item, map id, kind, words) -> the difficulties of the
    units the line is written from (both, for a line from anything else), so identical lines from units on each hold on both."""
    for name, lst in sources.items():
        for s in lst:
            on = held[(name, s['mapId'], s['kind'], s['text'])]
            if on != set(DIFFS):
                s['difficulties'] = [d for d in DIFFS if d in on]


def write_sources(sources):
    # A generic foe's weapon is only worth saying where nothing else gives it (it shows who carries a foe-only weapon), difficulty
    # by difficulty: its line keeps the difficulties no line of the item but a foe's holds on (a line without `difficulties` holds
    # on both), and goes where none are left. A named foe's line always stays.
    out = {}
    for name, lst in sources.items():
        covered = {d for s in lst if not s['kind'].startswith('foe') for d in s.get('difficulties', DIFFS)}
        out[name] = []
        for s in lst:
            if not s['kind'].endswith('generic'):
                out[name].append(s)
                continue
            left = [d for d in s.get('difficulties', DIFFS) if d not in covered]
            if left:
                line = {k: v for k, v in s.items() if k != 'difficulties'}
                line['kind'] = s['kind'].replace('-generic', '')
                if len(left) < len(DIFFS):
                    line['difficulties'] = left
                out[name].append(line)
    lines = [
        "import type { ItemSource } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe6-maps.py from The Binding Blade's event scripts and shop lists. Do not edit by hand.",
        ' */',
        '',
        '/** Where each item turns up, by chapter: shops, chests, villages and houses, hidden spots, talks, what a recruit carries, the',
        " * end of a chapter, and what foes carry ('-later': a foe who arrives mid-chapter, seen from the next chapter). */",
        'export const FE6_ITEM_SOURCES: Record<string, ItemSource[]> = ' + json.dumps(out, indent=2, ensure_ascii=False),
    ]
    write('fe6ItemSources.ts', lines)


def write(name, lines):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
