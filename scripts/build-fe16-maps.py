"""
Builds Three Houses' maps from the game's own files (scripts/fe16_data.py):
  src/data/fe16/fe16Terrain.ts      terrain Prt, Rsl, Avoid, healing and movement costs, from the game's own tables
  src/data/fe16/fe16Maps.ts         each battle's map, units by difficulty and house, reinforcements, objectives
  src/data/fe16/fe16ItemSources.ts  where each weapon turns up on the maps
Run:
    python scripts/build-fe16-maps.py

This first part is White Clouds: the Prologue and Chapters 1 to 11, which every house plays (Chapter 12 is where the routes part).
Formats are in data-raw/fe16/README.md. Coordinates: the grids count rows and columns from 0 at the top left; the app counts from
(1, 1) at the bottom left.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe16_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe16', 'Three Houses', 'build-fe16-maps.py'
DIFFS = ['Normal', 'Hard', 'Maddening']
# The houses, their unit table in a battle's .bai and the routes its scripts test for them (Route 0 Silver Snow and 3 Crimson Flower
# are both the Black Eagles' until the end of Chapter 11, 1 Azure Moon the Blue Lions', 2 Verdant Wind the Golden Deer's).
HOUSES = [('be', 'Black Eagles', 0, (0, 3)), ('bl', 'Blue Lions', 1, (1,)), ('gd', 'Golden Deer', 2, (2,))]
STORY = list(range(12))
# Battles each house plays as its own: the mock battles (each house's unit table), the Rite of Rebirth (the Blue Lions' copy of one
# opening event places two more Myrmidons on Hard and Maddening) and the Holy Tomb (on the Black Eagles' route Edelgard is the foe's
# commander and no leader fights for you). In every other White Clouds battle the houses differ only in which leader fights beside
# Byleth, on the same tile (`shared_check`).
PER_HOUSE = (1, 4, 7, 11)
LORDS = {2: 'Edelgard', 3: 'Dimitri', 4: 'Claude'}
LEADER = 'Your house leader (Edelgard, Dimitri or Claude)'
# Each house's students, who join it at Chapter 1 (persons): the lord first. Byleth and the three lords fight from the Prologue.
STUDENTS = {
    'be': [2, 5, 6, 7, 8, 9, 10, 11], 'bl': [3, 12, 13, 14, 15, 16, 17, 18], 'gd': [4, 19, 20, 21, 22, 23, 24, 25],
}
PROLOGUE_ARMY = [0, 2, 3, 4]
PLAYER_SLOT = 299        # the person a slot you fill holds ("Player")
NO_ARMY = 4              # a unit record's army byte: 0 yours, 1 the foe, 2 green, 3 a third army, 4 none (never on the map)
NAMED_BELOW = 100        # persons 0-99 are people; 100 on are the generic soldiers, villagers and beasts
# Events at the start of the battle: the map's load (10000, 10001), the battle's start (11500, 12000), their group heads (1999, 9999,
# 11499, 11999) and the checks after each action (2000), which the start's conditions also hold for.
START_TRIGGERS = {1999, 2000, 9999, 10000, 10001, 11499, 11500, 11999, 12000}
PHASE = {13000: 'your phase', 14000: 'the enemy phase'}
# Event flags the White Clouds battles test, and what sets them: 61 is set in the monastery's Blue Sea Moon script (file 342) when
# the house's story step "The Goddess's Rite of Rebirth" (quests 42-44: text 14943 + quest) is marked 4.
FLAGS = {61: "\"The Goddess's Rite of Rebirth\" ended a certain way (event flag 61)"}

# Terrain kind (fixed_stagedata.bin) -> builder letter (terrain_codes.py's 'fe16'), by how the game treats each: its stats and cost
# category. No unit enters category 0; only fliers cross category 1 (drawn by look); 2 and 12 cost everyone 1; 10 is a floor that costs
# some monsters 3.
LETTER = {
    0: '#', 1: '.', 2: '.', 3: 'f', 6: 'w', 8: 'R', 9: 'C', 10: 'b', 12: 'O', 13: 'C', 14: 'l', 15: 'S', 16: 'C', 17: 'd', 19: 'r',
    20: '#', 24: 'D', 25: 'T', 34: '#', 37: 'C', 38: 'W', 40: 'H', 41: '#', 42: 'C', 43: 'z', 44: '#', 45: '#', 46: 'c', 47: '#',
    51: 'V', 52: 'o', 56: 'm', 57: 'q', 58: 'A', 59: 'P', 60: 'L', 63: '#', 65: 'C', 68: '#', 69: 'O', 77: 'x', 78: 'Q', 79: '.',
    87: 'C', 91: 'O', 93: '#', 95: 'W', 102: 'C', 106: 'e',
}
LETTER_NAME = {
    '.': 'Plain', 'O': 'Floor', 'b': 'Bridge', 'S': 'Stairs', 'e': 'Wasteland', 'f': 'Forest', 'D': 'Thicket', 'T': 'Thicket',
    'A': 'Floor (Avo +40)', 'q': 'Cover', 'm': 'Wardwood', 'H': 'Healing tile', 'P': 'Prayer stone', 'o': 'Burning floor',
    'w': 'River', 'R': 'Rock', 'C': 'Cliff / mountain / wall', 'z': 'Valley', 'l': 'Fence', 'r': 'Rubble', 'x': 'Trench',
    '#': 'Wall', 'Q': 'Crest Stone', 'd': 'Door', 'c': 'Chest', 'L': 'Ballista', 'V': 'Lever', 'W': 'Breakable wall',
}
TERRAIN = D.terrain()
COSTS = D.move_costs()
CLASSES = D.classes()
DEFAULTS = D.default_weapons()
MONSTER_WEAPON = [r[4] | r[5] << 8 for r in D.table(D.CLASSDATA, 4)]   # by the class's byte +73 (fixed_classdata.bin section 4)
TIER_BONUS = [0, 1, 5, 8, 10, 10, 10]   # 0x1aa9168-0x1aa9198: level added for the default weapon, by the class tier (+69)
STEEL_FROM, SILVER_FROM = 19, 31        # 0x1a271a8, 0x1a271ac


def move_groups():
    """Movement types whose cost rows are the same, named after the classes that move that way."""
    by_row = {}
    for t in range(10):
        by_row.setdefault(tuple(COSTS[t]), []).append(t)
    names = {0: 'Infantry & armour', 2: 'Cavalry', 4: 'Mages', 5: 'Thieves & brawlers', 6: 'Fliers', 7: 'Beasts',
             8: 'Giant Crawlers', 9: 'Giant Wolves'}
    out = []
    for row, types in by_row.items():
        out.append((names[types[0]], types, list(row)))
    return out


GROUPS = move_groups()
CLASS_GROUP = {}
for _c, _r in enumerate(CLASSES):
    for _label, _types, _row in GROUPS:
        if _r[D.MOVE_TYPE] in _types:
            CLASS_GROUP[_c] = _label


def tile_info(kind):
    t = TERRAIN[kind]
    move = {label: (None if row[t['cost']] == 0xFF else row[t['cost']]) for label, _, row in GROUPS}
    e = {'name': LETTER_NAME[LETTER[kind]], 'def': t['prt'], 'res': t['rsl'], 'avo': t['avo'], 'heal': 0, 'move': move}
    if t['heal'] > 0:
        e['heal'] = t['heal']
    elif t['heal'] < 0:
        e['note'] = f"Takes {-t['heal']}% of max HP at the start of each turn."
    return e


def class_name(c):
    return D.class_name(c)


def default_weapon(cls, level):
    """What a unit with no items is given (the unit tables' loader, `0x19e2f8`): a monster its class's weapon; anyone else whose class
    fights with a weapon (main type 0-4) that type's Iron, Steel or Silver one by its level plus its class tier's bonus."""
    rec = CLASSES[cls]
    if rec[0x49] <= 0x1d:
        return MONSTER_WEAPON[rec[0x49]]
    kind = rec[D.MAIN_WEAPON]
    if kind > 4:
        return None
    eff = level + TIER_BONUS[min(rec[D.CLASS_TIER], 6)]
    tier = 2 if eff >= SILVER_FROM else 1 if eff >= STEEL_FROM else 0
    return DEFAULTS[kind][tier] + 10


def inventory(u, level):
    """The unit's items as the loader gives them: the default weapon (or monster weapon) in the first slot, then each filled slot of
    the table replacing the item in its own slot or taking the first free one (`0x19e470`). The drop field (+18) names the slot that
    drops (2-7: slot 0-5), or, from 8, an item more (the field - 1) put in the first free slot and dropped (`0x1a0ef8`)."""
    inv = []
    cls = unit_class(u)
    if cls is not None:
        g = default_weapon(cls, level)
        if g is not None:
            inv.append([g, False])
    drop = u['drops'] - 2 if u['drops'] else None
    for k, raw in enumerate(u['items']):
        if raw:
            if k < len(inv):
                inv[k] = [raw - 1, k == drop]
            else:
                inv.append([raw - 1, k == drop])
        elif k == drop and k < len(inv):
            inv[k][1] = True
    if u['drops'] >= 8 and len(inv) < 6:
        inv.append([u['drops'] - 1, True])
    return inv


def item_name(g):
    return D.global_item_name(g)


def _group(kind, vals):
    """Three-valued 'and' / 'or' (None: unknown). An empty group holds (Chapter 8's Tomas becomes Solon under an empty 'or')."""
    if not vals:
        return True
    if kind == 'and':
        return False if False in vals else None if None in vals else True
    return True if True in vals else None if None in vals else False


def holds(t, ctx):
    """A condition tree's truth at the start of the battle (None: it can't be known there)."""
    if t[0] in ('and', 'or'):
        return _group(t[0], [holds(c, ctx) for c in t[1]])
    name, args = t
    if name == 'Difficulty':
        # (negated, a difficulty, how it compares: 0 <, 1 <=, 2 ==, 3 >=, 4 >)
        d, v, cmp = ctx['diff'], args[1], args[2]
        res = [d < v, d <= v, d == v, d >= v, d > v][cmp]
        return not res if args[0] else res
    if name == 'Route':
        res = args[1] in ctx['routes']
        return (res if args[2] else not res) if not args[0] else not (res if args[2] else not res)
    if name in ('IsStartOfMap', 'IsStartOfBattle', 'StartOfBattleMaybe'):
        return ctx['start']
    if name == 'IsRecruited':
        res = args[1] in ctx.get('recruited', ())
        return not res if args[0] else res
    if name == 'HasOtherScriptRun':
        if args[1] in ctx['ran']:
            return bool(args[2])
        return None if args[1] in ctx['pending'] else not args[2]
    return None


class Battle:
    def __init__(self, s, house):
        self.s = s
        self.scen = D.scenario(s)
        self.w, self.h, self.rows = D.grid(self.scen['map'])
        tabs = D.units(s)
        self.house = house
        self.table = house[2] if s in (1, 7) else 0
        self.tables = tabs
        # A switched-off event never runs (fe16_data.script): it isn't read at all.
        self.events = [e for e in D.script(s) if not e['off']]
        self.loot = looting(self)

    def app(self, x, y):
        return [x + 1, self.h - y]

    def recruit_checks(self):
        """The persons the start's events test 'is recruited' for (students another house can take)."""
        out = []
        for e in self.events:
            if e['trigger'][0] in START_TRIGGERS:
                out += [a[1] for n, a in _flat(e['conditions']) if n == 'IsRecruited']
        return list(dict.fromkeys(out))

    def record(self, slot):
        return self.tables[slot // 100][slot % 100]

    def start(self, diff, recruited=()):
        """The units on the map when the battle starts, as {slot: [x, y]}, after the start's events: spawns, removals and walks
        (`recruited`: the students taken from other houses, whom the start replaces with stand-ins)."""
        placed = {}
        for u in self.tables[self.table]:
            if u['army'] in (0, 1, 2, 3) and not u['scripted'] and (u['person'] is not None or u['class'] is not None):
                placed[self.table * 100 + u['slot']] = (u['x'], u['y'])
        ran, done = set(), set()
        starts = [e for e in self.events if e['trigger'][0] in START_TRIGGERS]
        changed = True
        while changed:
            changed = False
            for e in starts:
                if e['num'] in done:
                    continue
                ctx = {'diff': diff, 'routes': self.house[3], 'start': True, 'ran': ran, 'recruited': recruited,
                       'pending': {x['num'] for x in starts if x['num'] not in done}}
                v = holds(e['conditions'], ctx)
                if v is None:
                    continue
                done.add(e['num'])
                changed = True
                if not v:
                    continue
                ran.add(e['num'])
                for name, args in e['actions']:
                    if name in ('SpawnUnit', 'SpawnUnit130'):
                        r = self.record(args[0])
                        # A unit of no army (4) never appears, whatever places it: Chapter 6 fields Fire Emblem Wiki's 26, 28 and 32
                        # foes only without its one.
                        if r['army'] != NO_ARMY:
                            placed.setdefault(args[0], (r['x'], r['y']))
                    elif name == 'RemoveFromMap':
                        placed.pop(args[0], None)
                    elif name == 'Walk' and args[0] in placed:
                        placed[args[0]] = (args[1], args[2])
                    elif name == 'Walk' and self.record(args[0])['army'] == 0:
                        # A unit of yours the opening walks onto the map (Chapter 2's house leader) stands where the walk ends.
                        placed[args[0]] = (args[1], args[2])
                    elif name == 'ReplaceUnitBAI' and args[1] in placed:
                        placed[args[0]] = placed.pop(args[1])
        return placed, ran


def on_course(t, ctx):
    """A condition tree's truth by its difficulty and route checks alone (None: something else decides it): whether an event can run
    on this difficulty and route at all."""
    if t[0] in ('and', 'or'):
        return _group(t[0], [on_course(c, ctx) for c in t[1]])
    return holds(t, ctx) if t[0] in ('Difficulty', 'Route') else None


def unit_class(u):
    """The unit's class: its record's (+4, class + 1), or, where that's 0, its person's own (person record +26)."""
    if u['class'] is not None:
        return u['class']
    if u['person'] is not None:
        return D.persons()[u['person']][26]
    return None


def level_of(b, u, diff):
    if u['level']:
        return u['level']
    base = b.scen['levels'][diff]
    return max(1, base - {1: 1, 2: 1, 3: 2}.get(u['rank'], 0))


def unit_entry(b, slot, tile, diff, victory):
    u = b.record(slot)
    person = u['person']
    generic = person is None or person >= NAMED_BELOW
    cls = unit_class(u)
    lv = level_of(b, u, diff)
    inv = inventory(u, lv)
    army = u['army']
    commander = u['rank'] == 0 and army == 1
    kind = 'ally' if army == 2 else ('boss' if commander and victory in (1, 3, 8) else 'enemy' if generic else 'named')
    name = class_name(cls) if generic and cls is not None else D.person_shown_name(person)
    e = {'type': kind, 'name': name, 'tile': b.app(*tile)}
    note = f'Lv {lv}' if generic else f'Lv {lv} {class_name(cls)}'
    if army == 3:
        note += ' · third army (yellow in the game): fights you and the red army'
    loot = b.loot.get(slot)
    if loot:
        at = [f'({x}, {y})' for x, y in (b.app(*t) for t in loot['tiles'])]
        what = f"the {loot['thing']} at {at[0]}" if len(at) == 1 else \
            f"the {plural(loot['thing'])} at {', '.join(at[:-1])} and {at[-1]}"
        out = b.app(*loot['exit'])
        note += f'; takes {what}, then leaves the map at ({out[0]}, {out[1]})'
        e['looter'] = True
        e['goesTo'] = [b.app(*t) for t in loot['tiles']] + [out]
    e['note'] = note
    carries = [item_name(g) for g, _ in inv]
    if carries:
        e['carries'] = carries
    drops = [item_name(g) for g, d in inv if d]
    if drops:
        e['drops'] = drops
    if generic:
        e['generic'] = True
    if army == 3:
        e['yellow'] = True
    return e, inv


def _flat(t):
    if t[0] in ('and', 'or'):
        out = []
        for c in t[1]:
            out += _flat(c)
        return out
    return [t]


def end_events(b):
    """The events that end the battle (EndMission) and every event that waits for one: the end scene, whose cast is never a unit on
    the battle map."""
    ends = {e['num'] for e in b.events if any(a[0] == 'EndMission' for a in e['actions'])}
    changed = True
    while changed:
        changed = False
        for e in b.events:
            if e['num'] in ends:
                continue
            if any(n == 'HasOtherScriptRun' and a[2] and a[1] in ends for n, a in _flat(e['conditions'])):
                ends.add(e['num'])
                changed = True
    return ends


def _deaths(t):
    """The defeats a condition tree checks, as (kind, slots): 'all' for those it needs together, 'any' for one of those under an
    'or'."""
    if t[0] == 'or':
        slots = [a[1] for n, a in _flat(t) if n == 'CheckDeathStatus' and a[2]]
        return [('any', slots)] if slots else []
    if t[0] == 'and':
        out, mine = [], []
        for c in t[1]:
            if c[0] in ('and', 'or'):
                out += _deaths(c)
            elif c[0] == 'CheckDeathStatus' and c[1][2]:
                mine.append(c[1][1])
        return ([('all', mine)] if mine else []) + out
    return []


def _who_falls(b, kind, slots):
    """'Kostas is defeated', 'the foe Dark Mage at (12, 3) is defeated', 'either foe Thief at (4, 22) or (4, 21) is defeated'."""
    names = []
    for slot in slots:
        u = b.record(slot)
        p = u['person']
        named = p is not None and p < NAMED_BELOW
        names.append((D.person_shown_name(p) if named else class_name(unit_class(u)), named, b.app(u['x'], u['y'])))
    if len({n for n, _, _ in names}) == 1 and not names[0][1]:
        cls, tiles = names[0][0], [f'({t[0]}, {t[1]})' for _, _, t in names]
        if len(names) == 1:
            return f'the foe {cls} at {tiles[0]} is defeated'
        if kind == 'any':
            first = 'either' if len(names) == 2 else 'any'
            return f"{first} foe {cls} at {', '.join(tiles[:-1])} or {tiles[-1]} is defeated"
        return f"the {len(names)} foe {plural(cls)} at {', '.join(tiles[:-1])} and {tiles[-1]} are defeated"
    words = [n if named else f'the foe {n} at ({t[0]}, {t[1]})' for n, named, t in names]
    joined = words[0] if len(words) == 1 else ', '.join(words[:-1]) + (' or ' if kind == 'any' else ' and ') + words[-1]
    if kind == 'any' and len(words) > 1:
        return f'{joined} is defeated'
    return f'{joined} {"is" if len(words) == 1 else "are"} defeated'


def _step(b, e):
    """One event's own condition (the events it waits for aside), or None where it adds nothing to its time: {'when', 'once', 'areas',
    'flags'}. 'when' says it as the arrival's time, 'once' as a step before a later one."""
    t = e['conditions']
    phase = PHASE.get(e['trigger'][0])
    turn, areas, also, flags, door = None, [], [], [], False
    for name, args in _flat(t):
        if name == 'IsStartOfEnemyPhase':
            phase = 'the enemy phase'
        elif name == 'IsStartOfPlayerPhase':
            phase = 'your phase'
        elif name == 'TurnNumber':
            turn = args[1]
        elif name == 'MovedAnyUnitInRectangle' and not args[0]:
            areas.append({'who': 'player' if args[1] == 0 else 'enemy',
                          'rect': gm.rect_to_app((args[2], args[3], args[4], args[5]), b.h)})
        elif name == 'MovedSpecificUnitInRectangle' and not args[0]:
            u = b.record(args[1])
            also.append(D.person_shown_name(u['person']) if u['person'] is not None else class_name(unit_class(u)))
            areas.append({'who': 'player', 'rect': gm.rect_to_app((args[2], args[3], args[4], args[5]), b.h)})
        elif name == 'CheckDoorOpened':
            door = True
        elif name == 'CheckEventFlag':
            flags.append((args[1], not args[0]))
    whens, onces = [], []
    who = 'one of your units' + ''.join(f', or {n},' for n in dict.fromkeys(also))
    if turn is not None:
        # An event runs once, so 'turn N or later' (cmp 3) comes on turn N, as 'turn N' (cmp 2) does.
        whens.append(f'Turn {turn}' + (f', {phase}' if phase else ''))
        onces.append(f'turn {turn} has come')
    elif areas:
        whens.append(f'At the start of {phase} with {who} in {{area}}' if phase else f'As soon as {who} enters {{area}}')
        onces.append(f'{who} has been in {{area}} at the start of {phase}' if phase else f'{who} has entered {{area}}')
    for kind, slots in _deaths(t):
        words = _who_falls(b, kind, slots)
        whens.append(f'once {words}')
        onces.append(words)
    if door:
        whens.append('once a door is opened')
        onces.append('a door is opened')
    if whens and phase and turn is None and not areas:
        whens.insert(0, f'At the start of {phase}')   # a defeat or a door, checked as a phase begins
    if not whens:
        if e['trigger'][0] in START_TRIGGERS:
            return {'when': None, 'once': None, 'areas': [], 'flags': flags}
        if phase:
            whens.append(f'At the start of {phase}')
            onces.append(f'{phase} has begun')
        else:
            return {'when': None, 'once': None, 'areas': [], 'flags': flags}
    when = whens[0][0].upper() + whens[0][1:] + ''.join(', ' + w for w in whens[1:])
    return {'when': when, 'once': ' and '.join(onces), 'areas': areas, 'flags': flags}


def _chain(b, e, seen=()):
    """The steps an event's arrival waits on, earliest first, each its own condition (`_step`): an event waits for another
    (HasOtherScriptRun) that ran before it. Events at the battle's start lend only their flags; of several alternatives (the routes'
    copies of one event) the first that says something is kept; an event that waits for the arrival of units whose defeat it checks
    needs nothing more said."""
    steps, flags = [], []
    me = _step(b, e)
    dead = {s for _, slots in _deaths(e['conditions']) for s in slots}
    waits = [a[1] for n, a in _flat(e['conditions']) if n == 'HasOtherScriptRun' and a[2] and a[1] not in seen]
    for num in dict.fromkeys(waits):
        other = next((x for x in b.events if x['num'] == num), None)
        if other is None:
            continue
        spawned = {a[1][0] for a in other['actions'] if a[0] in ('SpawnUnit', 'SpawnUnit130')}
        if dead & spawned:
            continue
        sub, sub_flags = _chain(b, other, seen + (e['num'],))
        flags += sub_flags
        if sub and not steps:
            steps = sub
    if me:
        flags += me['flags']
        if me['when'] is not None:
            steps = steps + [me]
    return steps, flags


def describe(b, e):
    """When an event's units arrive: {'text', 'areas', 'flags'}, or None where nothing can be read. A chain of events reads from its
    last step back ('At the start of the enemy phase with one of your units in area 2, once one of your units has been in area 1 at
    the start of your phase'), its areas numbered by step where more than one step has some."""
    steps, flags = _chain(b, e)
    if not steps:
        if e['trigger'][0] in START_TRIGGERS:
            return {'text': 'At the start of the battle', 'areas': [], 'flags': flags}
        return {'text': 'After an event in the chapter', 'areas': [], 'flags': flags} if flags else None
    with_areas = [s for s in steps if s['areas']]
    numbered = len(with_areas) > 1
    areas = []
    for k, s in enumerate(with_areas, 1):
        name = f'area {k}' if numbered else ('the marked areas' if len(s['areas']) > 1 else 'the marked area')
        s['when'] = s['when'].replace('{area}', name)
        s['once'] = s['once'].replace('{area}', name)
        areas += [{**a, 'step': k} if numbered else a for a in s['areas']]
    last, before = steps[-1], steps[:-1]
    text = last['when'] + ''.join(f', once {s["once"]}' for s in reversed(before))
    return {'text': text, 'areas': list({json.dumps(a, sort_keys=True): a for a in areas}.values()), 'flags': flags}


def plural(name):
    return name[:-1] + 'ves' if name.endswith('f') else name + 'es' if name.endswith(('s', 'sh', 'ch')) else name + 's'


def flag_words(flags):
    """What an event flag the battle tests means, where it's traced (data-raw/fe16/README.md)."""
    out = []
    for flag, wanted in dict.fromkeys(flags):
        what = FLAGS.get(flag, f'event flag {flag}')
        out.append(f'if {what}' if wanted else f'unless {what}')
    return out


def reinforcements(b, victory):
    """Groups from the events after the start that place units, per difficulty and merged (gba_maps.one_per_arrival)."""
    groups = []
    ends = end_events(b)
    for d, dname in enumerate(DIFFS):
        placed, ran = b.start(d)
        for e in b.events:
            if e['num'] in ran or e['num'] in ends:
                continue
            if any(n == 'IsRecruited' for n, _ in _flat(e['conditions'])):
                continue
            spawns = [a[1][0] for a in e['actions'] if a[0] in ('SpawnUnit', 'SpawnUnit130')]
            spawns = [x for x in dict.fromkeys(spawns) if x not in placed]
            if not spawns:
                continue
            ctx = {'diff': d, 'routes': b.house[3]}
            if on_course(e['conditions'], ctx) is False:
                continue
            w = describe(b, e)
            units = []
            for slot in spawns:
                r = b.record(slot)
                if r['army'] in (0, NO_ARMY):
                    continue
                u, inv = unit_entry(b, slot, (r['x'], r['y']), d, victory)
                u['difficulties'] = [dname]
                units.append((u, inv))
            if not units:
                continue
            when = w['text'] if w else 'After an event in the chapter'
            if w and w['flags']:
                when += ', ' + ', '.join(flag_words(w['flags']))
            g = {'_event': e['num'], 'when': {dname: when}, 'units': [u for u, _ in units], '_inv': {dname: units}}
            if w and w['areas']:
                g['areas'] = w['areas']
            groups.append(g)
    invs = [(g.pop('_inv'), g['_event']) for g in groups]
    return gm.one_per_arrival(groups, DIFFS), invs


def looting(b):
    """Units the script sends to take something from the map's tiles, then off the map: Chapter 11's Thieves and Brigands and the Crest
    Stones in the Holy Tomb's walls. MoveToRectangleAI580 sends a unit to work in an area; once the tiles it's after are taken
    (InteractedWithTerrain, the tile as y * 100 + x) MoveToRectangleAI sends it to one tile, and standing there (MovedCharacterOnTile)
    takes it off the map (RemoveFromMap) and adds to a count (IncrementVariable: the count, by how many). {slot: {'tiles', 'exit',
    'count', 'adds', 'thing'}}, the thing named by its tiles' terrain ('Crest Stone')."""
    out = {}
    for e in b.events:
        for name, args in e['actions']:
            if name == 'MoveToRectangleAI580':
                out.setdefault(args[0], {})
    for e in b.events:
        tiles = [a[1] for n, a in _flat(e['conditions']) if n == 'InteractedWithTerrain' and a[2]]
        for name, args in e['actions']:
            if name == 'MoveToRectangleAI' and args[0] in out and tiles and (args[1], args[2]) == (args[3], args[4]):
                out[args[0]].update(tiles=[(t % 100, t // 100) for t in tiles], exit=(args[1], args[2]))
    for e in b.events:
        on = [a for n, a in _flat(e['conditions']) if n == 'MovedCharacterOnTile' and a[1] in out]
        if on and any(a[0] == 'RemoveFromMap' and a[1][0] == on[0][1] for a in e['actions']):
            for name, args in e['actions']:
                if name == 'IncrementVariable':
                    out[on[0][1]].update(count=args[0], adds=args[1])
    out = {k: v for k, v in out.items() if 'tiles' in v}
    for v in out.values():
        kinds = {b.rows[y][x][0] for x, y in v['tiles']}
        assert len(kinds) == 1, kinds
        v['thing'] = D.text(5502 + kinds.pop())
        # What it adds to the count is how many of the tiles it takes: the count is of the things carried off.
        assert v.get('adds') == len(v['tiles']), v
    return out


def count_words(conds, var, thing, total):
    """A gift's checks on a looting count, in words ('if no Crest Stone is carried off the map', 'if 1 to 10 Crest Stones are ...').
    CheckVariableValue: (negated, the count, a value, how it compares: 0 <, 1 <=, 2 ==, 3 >=, 4 >)."""
    lo, hi = 0, total
    for name, args in conds:
        if name != 'CheckVariableValue' or args[1] != var:
            continue
        assert not args[0], args
        v, cmp = args[2], args[3]
        if cmp == 2:
            lo = hi = v
        elif cmp in (0, 1):
            hi = min(hi, v - (cmp == 0))
        else:
            lo = max(lo, v + (cmp == 4))
    things = plural(thing)
    if hi == 0:
        return f'if no {thing} is carried off the map'
    if lo == hi:
        return f'if all {total} {things} are carried off the map' if lo == total else f'if {lo} {things} are carried off the map'
    if hi == total:
        return f'if {lo} or more {things} are carried off the map'
    return f'if {lo} to {hi} {things} are carried off the map'


def defeat_text(b, house):
    """The battle's lose condition, the house's own (scenario +41-43, one per house). A battle every house plays alike says it once for
    all three, the leader as 'your house leader (Edelgard, Dimitri or Claude)'."""
    texts = [clean(D.text(11906 + b.scen['raw'][41 + k])) for k in range(3)]
    if house is not None:
        return texts[house[2]]
    forms = {t.replace(LORDS[2 + k], '{lord}') for k, t in enumerate(texts)}
    assert len(forms) == 1, texts
    return forms.pop().replace('{lord}', 'your house leader (Edelgard, Dimitri or Claude)')


def shared_check(s):
    """A battle every house plays alike is one map: each house's start and arrivals are the same but for its leader (`LORDS`), who
    stands on the same tile."""
    seen = []
    for house in HOUSES:
        b = Battle(s, house)
        starts = []
        for d in range(len(DIFFS)):
            placed, _ = b.start(d)
            starts.append(sorted((-1 if b.record(slot)['person'] in LORDS and b.record(slot)['army'] == 0 else slot, tile)
                                 for slot, tile in placed.items()))
        rein, _ = reinforcements(b, b.scen['victory'])
        groups = sorted(json.dumps([g.get('when'), g.get('areas'), sorted(json.dumps(u, sort_keys=True) for u in g['units'])])
                        for g in rein)
        seen.append((json.dumps(starts), json.dumps(groups)))
    assert len(set(seen)) == 1, f'chapter {s} differs by house beyond its leader'


def main():
    groups = GROUPS
    maps, sources, variants, used = [], {}, {}, {}

    held = {}   # (item, map id, kind, text) -> the difficulties the line holds on

    def source(name, map_id, kind, text, diffs=None):
        held.setdefault((name, map_id, kind, text), set()).update(diffs or DIFFS)

    for s in STORY:
        own = s in PER_HOUSE
        if not own and s > 0:
            shared_check(s)
        for house in HOUSES if own else [HOUSES[0]]:
            b = Battle(s, house)
            map_id = f'fe16-{s}' + (f'-{house[0]}' if own else '')
            title = D.text(s)
            victory = b.scen['victory']
            m = {
                'id': map_id, 'route': 'Story', 'chapter': s, 'title': title, 'location': D.text(957 + b.scen['map']),
                'heading': 'Prologue' if s == 0 else f'Ch.{s}' + (f' ({house[1]})' if own else ''),
                'width': b.w, 'height': b.h, 'grid': [], 'objectives': [], 'units': [], 'starts': [], 'objects': [],
                'changes': [], 'notes': [], 'lord': 'Byleth',
                'victory': clean(D.text(11906 + victory)), 'defeat': defeat_text(b, house if own else None),
            }
            # Units per difficulty, merged.
            per_diff, forced, starts = [], {}, set()
            for d, dname in enumerate(DIFFS):
                placed, _ = b.start(d)
                units = []
                for slot, tile in sorted(placed.items()):
                    u = b.record(slot)
                    if u['army'] == 0:
                        if u['person'] in (None, PLAYER_SLOT):
                            starts.add(tuple(b.app(*tile)))
                        else:
                            who = LEADER if not own and s > 0 and u['person'] in LORDS else D.person_shown_name(u['person'])
                            forced[who] = b.app(*tile)
                        continue
                    e, inv = unit_entry(b, slot, tile, d, victory)
                    e['difficulties'] = [dname]
                    units.append(e)
                    who = e['name'] if not e.get('generic') else f"a foe {e['name']}" if u['army'] == 1 else f"a {e['name']}"
                    for g, dropping in inv:
                        if dropping and 10 <= g < 600:
                            source(item_name(g), map_id, 'drop', f'Dropped by {who}', [dname])
                        elif 10 <= g < 600 and u['army'] in (1, 3):
                            kind = 'foe-generic' if e.get('generic') else 'foe'
                            source(item_name(g), map_id, kind, f"Carried by {who}{'' if e.get('generic') else ', a foe'}", [dname])
                per_diff.append(units)
            m['units'] = gm._merge_units(per_diff, DIFFS)
            # Stand-ins: a student another house can recruit is replaced, on the same tile, by a soldier of their class.
            for p in b.recruit_checks():
                base, _ = b.start(0)
                alt, _ = b.start(0, recruited=(p,))
                gone = [slot for slot in base if slot not in alt and b.record(slot)['person'] == p]
                new = [slot for slot in alt if slot not in base]
                for slot in gone:
                    tile = b.app(*base[slot])
                    sub = next((x for x in new if b.app(*alt[x]) == tile), None)
                    if sub is None:
                        continue
                    e, _ = unit_entry(b, sub, alt[sub], 0, victory)
                    for u in m['units']:
                        if u['tile'] == tile and u['name'] == D.person_shown_name(p):
                            u['standIn'] = {'type': e['type'], 'name': e['name'], 'note': e['note'], 'generic': True,
                                            'when': f'if you recruited {D.person_shown_name(p)} into your house'}
            rein, invs = reinforcements(b, victory)
            if rein:
                for g in rein:
                    for u in g['units']:
                        if u.get('difficulties') == DIFFS:
                            u.pop('difficulties')
                m['reinforcements'] = rein
            # What the battle's script gives (GrantItem: a slot, a global item number) once it's won; a gift that checks the count of
            # what looters carried off says how many (Chapter 11's Crest Stones), and the map's notes list every such reward.
            loot = next(iter(b.loot.values()), None)
            total = sum(v['adds'] for v in b.loot.values())
            rewards = []
            for e in b.events:
                gifts = [a[1][1] for a in e['actions'] if a[0] == 'GrantItem' and a[1][0] == 0]
                conds = [c for c in _flat(e['conditions']) if c[0] == 'CheckVariableValue']
                if loot and any(c[1][1] == loot['count'] for c in conds):
                    words = count_words(conds, loot['count'], loot['thing'], total)
                    names = [item_name(g) for g in gifts]
                    rewards.append(f"{words}, {', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0] if names else 'nothing'}")
                elif not gifts:
                    continue
                else:
                    words = 'on a count the battle keeps' if conds else ''
                for g in gifts:
                    if 10 <= g < 600:
                        source(item_name(g), map_id, 'event-later', 'Given when the battle is won' + (f', {words}' if words else ''))
            if loot:
                kinds = [plural(k) for k in dict.fromkeys(class_name(unit_class(b.record(slot))) for slot in sorted(b.loot))]
                who = kinds[0] if len(kinds) == 1 else ', '.join(kinds[:-1]) + ' and ' + kinds[-1]
                m['notes'].append(f"{who} go for the {total} {plural(loot['thing'])} in the walls, then leave the map with them: tap one "
                                  'to see what it takes and where it leaves.')
                m['notes'].append('When the battle is won: ' + '; '.join(rewards) + '.')
            for per, _ in invs:
                for dname, units in per.items():
                    for u, inv in units:
                        who = u['name'] if not u.get('generic') else f"a foe {u['name']}"
                        for g, dropping in inv:
                            if dropping and 10 <= g < 600:
                                source(item_name(g), map_id, 'drop-later', f'Dropped by {who}, arriving mid-chapter', [dname])
            for u in m['units']:
                if u.get('difficulties') == DIFFS:
                    u.pop('difficulties')
            # Your units' tiles: the slots you fill, Byleth's own and those the game places (each one a starting tile).
            if 'Byleth' in forced:
                m['corrinStart'] = forced.pop('Byleth')
                starts.add(tuple(m['corrinStart']))
            starts |= {tuple(t) for t in forced.values()}
            m['starts'] = sorted([list(t) for t in starts], key=lambda t: (-t[1], t[0]))
            m['forced'] = [{'name': n, 'tile': t} for n, t in forced.items()]
            # A leader the lose condition names but nothing places is one you must deploy, on a slot you choose.
            leader = LEADER if not own else LORDS[2 + house[2]]
            named = 'your house leader' in m['defeat'] if not own else leader in m['defeat']
            if s > 0 and named and leader not in forced:
                m['forced'].append({'name': leader})
            if not m['forced']:
                del m['forced']
            # Terrain.
            codes, infos = [], []
            for r in range(b.h):
                line = []
                for c in range(b.w):
                    kind = b.rows[r][c][0]
                    letter = LETTER[kind]
                    code = encode(GAME, letter)
                    info = tile_info(kind)
                    line.append(code)
                    infos.append((code, info))
                    variants.setdefault(code, {}).setdefault(json.dumps(info, sort_keys=True), [info, set()])[1].add(map_id)
                codes.append(''.join(line))
            m['grid'] = codes
            used[map_id] = {}
            for code, info in infos:
                old = used[map_id].setdefault(code, info)
                assert old == info, (map_id, code, old, info)
            maps.append(m)
            print(map_id, title, f'{b.w}x{b.h}', len(m['units']), 'units', len(m['starts']), 'starts')

    info = {}
    for code, vs in variants.items():
        info[code] = json.loads(max(vs.items(), key=lambda kv: len(kv[1][1]))[0])
    for m in maps:
        over = {}
        for code, e in used[m['id']].items():
            if e != info[code]:
                over[code] = {k: v for k, v in e.items() if v != info[code].get(k)}
        if over:
            m['terrainOverrides'] = over
    members = [(label, [c for c, g in CLASS_GROUP.items() if g == label and class_name(c)], row) for label, _, row in groups]
    gm.write_terrain(GAME, TITLE, SCRIPT, info, members, {c: class_name(c) for c in range(len(CLASSES))},
                     fliers='')
    # Starting gear (fixed_persondata.bin section 6): Byleth and the lords from the Prologue, each house's students from its Chapter 1.
    for p in PROLOGUE_ARMY:
        for g in D.starting_items(p):
            if 10 <= g < 600:
                source(item_name(g), 'fe16-0', 'kit', f'Carried by {D.person_shown_name(p)} from the start')
    for key, people in STUDENTS.items():
        for p in people:
            if p in PROLOGUE_ARMY:
                continue
            for g in D.starting_items(p):
                if 10 <= g < 600:
                    source(item_name(g), f'fe16-1-{key}', 'kit', f'Carried by {D.person_shown_name(p)} on joining')
    # The monastery's armory (fixed_shopdata.bin section 0): open from Chapter 1 (after the Prologue), its stock by the shop's level
    # (+16, +17, +18: how many, 0xFF unlimited, 0 none). What raises the level isn't traced yet (README).
    for r in D.table(D.SHOPDATA, 0):
        price, sell, w = struct.unpack_from('<iiH', r, 0)
        if not (6 <= w < 500) or not r[12]:
            continue
        name = D.weapon_name(w)
        for lv in range(3):
            n = r[16 + lv]
            if n == 0:
                continue
            words = "Sold at the monastery's armory" + ('' if lv == 0 else f' once it reaches level {lv + 1}')
            entry = {'mapId': 'fe16-0', 'kind': 'town-shop-later', 'text': words}
            if n != 0xFF:
                entry['limited'] = n
            sources.setdefault(name, []).append(entry)
            if n == 0xFF:
                break   # unlimited from this level on: the higher levels add nothing
    for (name, map_id, kind, text), ds in held.items():
        line = {'mapId': map_id, 'kind': kind, 'text': text}
        if len(ds) < len(DIFFS):
            line['difficulties'] = [d for d in DIFFS if d in ds]
        sources.setdefault(name, []).append(line)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=DIFFS)


def clean(text):
    """The game's text without its colour codes, Byleth's name for its placeholder."""
    out = text.replace('\x1bS0', 'Byleth')
    while '\x1bC' in out:
        i = out.index('\x1bC')
        out = out[:i] + out[i + 3:]
    return out.replace('\x1bR', '').replace('\n', ' ').rstrip('.')


if __name__ == '__main__':
    main()
