"""
Builds The Blazing Blade's maps from the user's (U) ROM (scripts/gba_rom.py, scripts/fe7_events.py):
  src/data/fe7/fe7Terrain.ts      terrain stats and movement costs by movement type
  src/data/fe7/fe7Maps.ts         every chapter of Lyn's, Eliwood's and Hector's stories: terrain, units, reinforcements, joiners,
                                  chests, villages, shops
  src/data/fe7/fe7ItemSources.ts  where each item turns up, by chapter (the weapon page and the spoiler block)
Run:
    python scripts/build-fe7-maps.py

What is read where (data-raw/fe7/README.md has the formats):
  - Chapter records, 0x98 bytes at 0xC9A200: the tile config at +7 and the map at +8 are indices into the pointer table at 0xC9C9C8;
    map changes at +0xB; the fog vision at +0xC; +0xD set when the chapter has preparations; the titles in Eliwood's and Hector's
    stories at +0x70 / +0x72 (text ids); the event data at +0x78; the goal at +0x8C.
  - A chapter's start: the opening scene, played for the story and difficulty. A chapter with preparations then clears every unit
    that isn't yours and loads the event data's enemy group for the story and difficulty (0x0803089C, 0x08018980); your army's
    group gives the deploy tiles. Then every turn-1 event on your phase runs. Units end on the tile the scripted moves leave them.
  - Every later turn, talk, area and location event that loads units is a reinforcement, with when it fires.
Chapter titles and goals are the game's own text. The gaiden chapters' conditions are read from the end scripts (each one also asks
"Embark on side quest?"); where a condition is a routine of its own, its wording is Serenes Forest's, checked against the numbers in
the code.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe7_events as fe  # noqa: E402
import gba_maps as gm  # noqa: E402
from gba_rom import rom  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe7', 'The Blazing Blade', 'build-fe7-maps.py'
r = rom('fe7')
R = r.R
NAMES = r.character_names()
CLASSES = r.class_names()
ITEMS = r.item_names()

LYN = list(range(0, 12))
ELIWOOD = [12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 46, 47]
HECTOR = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44,
          45, 46, 47]
LORD = {'Lyn': 3, 'Eliwood': 1, 'Hector': 2}
DEFEAT = {'Lyn': 'Lyn is defeated', 'Eliwood': 'Eliwood or Hector is defeated', 'Hector': 'Eliwood or Hector is defeated'}
# The two versions of Chapter 23 (Eliwood) / 24 (Hector) and of 25 / 27: who the story pits you against.
VERSION = {31: 'Lloyd', 32: 'Linus', 35: 'Kenneth', 36: 'Jerme'}

# When the story reaches a chapter that not everyone plays: read from the end scripts' checks before each "go to chapter"; every
# gaiden is also offered with "Embark on side quest?". Where the check is a routine of its own, the wording is Serenes Forest's.
SIDE = ' The game asks "Embark on side quest?" first.'
OPENS = {
    8: 'Opens if Chapter 7 is cleared within 15 turns.' + SIDE,
    16: "Opens if Chapter 13's north-western village is visited (flag 9)." + SIDE,
    21: 'Opens if Chapter {16} is cleared with at least one of the Caelin soldiers alive (at most 2 lost).' + SIDE,
    24: 'Opens if Chapter {18} is cleared within 15 turns.' + SIDE,
    25: "Opens in Hector's story if Nils reached level 7 in Lyn's story and Kishuna is defeated in Chapter 19x." + SIDE,
    30: 'Opens if Chapter {22} is cleared with Hawkeye recruited and alive, and your party gained more than 699 EXP in it.' + SIDE,
    31: "Played when Lyn's, Eliwood's and Hector's levels total 49 or less (Serenes Forest; the game's own check is code).",
    32: "Played when Lyn's, Eliwood's and Hector's levels total 50 or more (Serenes Forest; the game's own check is code).",
    # 0x0807D4C1 totals a measure (0x080A01DC) over two of the game's own lists (0x08CB8984, 0x08CB898E); that it's EXP gained is
    # Serenes Forest's.
    35: 'Played when Erk, Lucius, Renault, Priscilla and Serra have gained at least as much EXP as Guy, Dorcas, Bartre and Raven.',
    36: 'Played when Guy, Dorcas, Bartre and Raven have gained more EXP than Erk, Lucius, Renault, Priscilla and Serra.',
    38: 'Opens if Nino talks to Jaffar in Chapter {26} and both are alive at its end.' + SIDE,
    45: "Opens in Hector's story if Chapter 32 is cleared within 20 turns." + SIDE,
}
# Hector's chapter numbers run one or two ahead of Eliwood's from Chapter 15; the notes name chapters the way the mode does.
NUMBERS = {'Eliwood': {16: '16', 18: '18', 22: '22', 26: '26'}, 'Hector': {16: '17', 18: '19', 22: '23', 26: '28'}}

MOVE_NAMES = {1: 'Lords, heroes & thieves', 10: 'Infantry', 20: 'Armours', 18: 'Fighters', 57: 'Brigands', 58: 'Pirates',
              59: 'Berserkers', 28: 'Mages & priests', 40: 'Cavaliers', 42: 'Paladins', 46: 'Nomads', 48: 'Nomad troopers',
              50: 'Fliers', 70: 'Dragons'}
PHASE = {0x00: 'your phase', 0x40: "the other army's phase", 0x80: 'enemy phase'}
TURN_CONDITION = {1: ('Eliwood', False), 2: ('Hector', False), 3: ('Eliwood', True), 4: ('Hector', True)}
ORDINAL = {2: 'second', 3: 'third', 4: 'fourth'}


def char_record(c):
    return r.character_record(c)


def is_boss(c):
    """The boss flag: bit 0x8000 of the abilities (+0x28), set on each chapter's boss."""
    return bool(r.u32(char_record(c) + 0x28) & 0x8000)


def drops(u):
    """The item a foe drops: its last one, when its character's or class's abilities have 0x08000000 (the unit's state gets 0x1000
    as it's made, 0x08017826; a defeated unit in that state hands its last item over, 0x0802FA22)."""
    a = r.u32(char_record(u['char']) + 0x28) | r.u32(r.cfg['classes'] + 84 * class_of(u) + 0x28)
    return u['items'][-1:] if a & 0x08000000 else []


def has_portrait(c):
    return r.u16(char_record(c) + 6) != 0


def class_of(u):
    return u['class'] or R[char_record(u['char']) + 5]


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def heading_title(text):
    """'Ch. 11: Taking Leave' -> ('Ch.11', 'Taking Leave'); 'Final Chapter: Light' -> ('Final', 'Light')."""
    m = re.match(r'(Ch\. ([0-9]+[x]*)(?: pt 2)?|Prologue|Final Chapter): (.*)', text)
    assert m, text
    head = m.group(1)
    if head.startswith('Ch.'):
        head = 'Ch.' + m.group(2) + (' pt 2' if 'pt 2' in head else '')
    elif head == 'Final Chapter':
        head = 'Final'
    return head, m.group(3).strip()


def map_changes(entry):
    """The chapter's map changes: id -> (x, y, w, h) from the top-left (12-byte records up to id 0xFF)."""
    i = R[r.chapter(entry) + 0xB]
    if not i:
        return {}
    o, out = r.pointer(i), {}
    while R[o] != 0xFF:
        out[R[o]] = (R[o + 1], R[o + 2], R[o + 3], R[o + 4])
        o += 12
    return out


def condition_ok(e, mode, hard):
    """A turn event's condition (+0xC) for a mode and difficulty."""
    c = struct_u32(e, 4)
    if c in TURN_CONDITION:
        m, h = TURN_CONDITION[c]
        return m == mode and h == hard
    if c == 5:
        return hard
    return True


def struct_u32(e, i):
    b = e['b']
    return b[i] | b[i + 1] << 8 | b[i + 2] << 16 | b[i + 3] << 24


def turn_conditions(e):
    """The difficulties a turn event fires on, for one mode: None when on all."""
    c = struct_u32(e, 4)
    if c in (3, 4, 5):
        return ['Hard']
    if c in (1, 2):
        return ['Normal']
    return None


class Chapter:
    def __init__(self, entry, mode, height):
        self.entry, self.mode, self.h = entry, mode, height
        self.ev = fe.events_of(entry)
        self.turns = fe.event_list(self.ev['turn'])
        self.talks = fe.event_list(self.ev['talk'])
        self.locations = fe.event_list(self.ev['location'])
        self.misc = fe.event_list(self.ev['misc'])
        self.prep = R[r.chapter(entry) + 0xD]
        self.changes = map_changes(entry)

    def world(self, hard, **kw):
        return fe.World(mode=self.mode, hard=hard, **kw)

    def opening(self, hard):
        run = fe.Run(self.world(hard))
        run.run(self.ev['opening'])
        if self.prep:
            # Everyone not yours is cleared; the chapter's enemies for the story and difficulty are loaded, and your army deploys on
            # its group's tiles.
            run.units = [u for u in run.units if u['side'] == 'player' and not u['army']]
            run.units = [u for u in run.units if u['char'] not in [a['char'] for a in fe.unit_group(self.army(hard))]]
            slot = fe.group_slot(self.mode, hard)
            run.load(self.ev['enemies'][slot])
            run.load(self.army(hard), army=True)
        for e in self.turns:
            # A chapter without preparations lists its opening scene as a turn-1 event as well; it plays once.
            if self.is_opening(e) and condition_ok(e, self.mode, hard) and r.is_ptr(e['ptr']) and e['ptr'] != self.ev['opening']:
                run.run(e['ptr'])
        return run

    def army(self, hard):
        return self.ev['army'][fe.group_slot(self.mode, hard)]

    @staticmethod
    def is_opening(e):
        b = e['b']
        return e['type'] == 2 and b[0] == 1 and b[2] == 0


def turn_text(e):
    first, last, phase = e['b'][0], e['b'][1], e['b'][2]
    p = PHASE.get(phase, 'any phase')
    if last == 255 or (last > first and e['flag'] == 0 and last - first > 30):
        return f'Every {p} from turn {first}' if first > 1 else f'Every {p}'
    if last > first and e['flag'] == 0:
        return f'Every turn from {first} to {last}, {p}'
    return f'Turn {first}, {p}'


def talk_pair(e):
    if e['type'] == 3:
        return e['b'][0], e['b'][1]
    if e['type'] == 4:
        return e['b'][0], e['b'][1]
    return None


def talk_allowed(e, mode):
    if e['type'] != 3:
        return True
    c = e['b'][4]
    return c == 0 or c == 3 or (c == 1 and mode == 'Eliwood') or (c == 2 and mode == 'Hector')


def unit_entry(u, h, talk=None):
    c = u['char']
    cls = CLASSES.get(class_of(u), '?')
    name = NAMES.get(c, '?')
    items = [item_name(i) for i in u['items']]
    if u['side'] == 'enemy':
        kind = 'boss' if is_boss(c) else 'named' if has_portrait(c) else 'enemy'
    else:
        kind = 'ally'
    named = kind in ('boss', 'named') or (kind == 'ally' and has_portrait(c))
    out = {'type': kind, 'name': name if named else cls, 'tile': gm.to_app(u['tile'], h),
           'note': f"Lv {u['level']} {cls}" if named else f"Lv {u['level']}"}
    if kind == 'ally' and not named:
        out['generic'] = True
    if items:
        out['carries'] = items
    if u['side'] == 'enemy' and drops(u):
        out['drops'] = [item_name(i) for i in drops(u)]
    if talk:
        out['talk'] = talk
    return out


def talks_of(ch):
    """{name: 'Recruit: talk with Eliwood or Hector'} from the talk events this story allows."""
    found = {}
    for e in ch.talks:
        pair = talk_pair(e)
        if not pair or not r.is_ptr(e['ptr']) or not talk_allowed(e, ch.mode):
            continue
        a, b = pair
        run = fe.Run(ch.world(False, active=a)).run(e['ptr'])
        t = found.setdefault(NAMES.get(b, '?'), {'recruit': [], 'talk': [], 'gives': []})
        who = NAMES.get(a, '?') if a else 'anyone'
        cmds = fe.script(e['ptr'])
        if b in run.recruits or any(op == 0x65 and (args[0] & 0xFF) == b and args[1] == 0 for _, op, _, args in cmds):
            t['recruit'].append(who)
        else:
            t['talk'].append(who)
            t['gives'] += [item_name(i) for i, _ in run.items]
    out = {}
    for name, t in found.items():
        if t['recruit']:
            out[name] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(t['recruit']))
        else:
            out[name] = 'Talk with ' + ' or '.join(dict.fromkeys(t['talk'])) + (f" (gives {', '.join(t['gives'])})" if t['gives'] else '')
    return out


def build_units(ch, m, source, diffs):
    h = m['height']
    talks = talks_of(ch)
    for e in ch.talks:
        pair = talk_pair(e)
        if pair and r.is_ptr(e['ptr']) and talk_allowed(e, ch.mode):
            run = fe.Run(ch.world(False, active=pair[0])).run(e['ptr'])
            for i, _ in run.items:
                source(i, m['id'], 'talk', f"{NAMES.get(pair[0], '?')} talks to {NAMES.get(pair[1], '?')}")
    runs = {d: ch.opening(d == 'Hard') for d in diffs}
    ch.closed = set()
    for cid in runs[diffs[0]].map_changes:
        if cid in ch.changes:
            x, y, w, hh = ch.changes[cid]
            ch.closed |= {(x + i, y + j) for i in range(w) for j in range(hh)}
    placed = {}
    moved = False
    for d, run in runs.items():
        moved |= spread(run.units, m)
        seen = {}
        for u in run.units:
            key = (u['char'], class_of(u), u['tile'], tuple(u['items']), u['side'], u['army'])
            # Two identical units in one run stay two (a group can walk onto another's tiles: Hector's Chapter 13).
            seen[key] = seen.get(key, 0) + 1
            placed.setdefault(key + (seen[key],), (u, []))[1].append(d)
    if moved:
        m.setdefault('unconfirmed', []).append(
            "A unit whose tile was taken when it arrived is shown on the nearest free tile; the game picks its own free tile, which "
            "may differ.")
    lord_id = LORD[ch.mode]
    army = [(u, ds) for u, ds in placed.values() if u['army']]
    lord = next((u for u, _ in placed.values() if u['char'] == lord_id and u['side'] == 'player'), None)
    if army:
        m['starts'] = [gm.to_app(u['tile'], h) for u, _ in dict(((u['tile'], (u, ds)) for u, ds in army)).values()]
    if lord:
        m['corrinStart'] = gm.to_app(lord['tile'], h)
        if not army:
            m['starts'] = [m['corrinStart']]
    forced = []
    for u, ds in placed.values():
        if u['army']:
            continue
        if u['side'] == 'player':
            if u['char'] != lord_id and not ch.prep:
                f = {'name': NAMES.get(u['char'], '?'), 'tile': gm.to_app(u['tile'], h)}
                if f not in forced:
                    forced.append(f)
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining")
            continue
        e = unit_entry(u, h, talks.get(NAMES.get(u['char'], '?')))
        if m['victory'] == f"Defeat {e['name']}" or (e['name'] in m['victory'] and is_boss(u['char'])):
            e['type'] = 'boss'
        if len(ds) < len(diffs):
            e['difficulties'] = ds
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit'):
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining")
        elif e['type'] in ('boss', 'named') and u['side'] == 'enemy':
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by {e['name']}")
            for i in u['items']:
                source(i, m['id'], 'foe', f"Carried by {e['name']}, a foe")
        elif u['side'] == 'enemy':
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by a foe {CLASSES.get(class_of(u), '?')}")
            for i in u['items']:
                source(i, m['id'], 'foe-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')}")
    if forced:
        m['forced'] = forced
    leaves = {}
    for e in ch.turns:
        if Chapter.is_opening(e) or not r.is_ptr(e['ptr']) or e['ptr'] == ch.ev['opening']:
            continue
        for _, op, _, args in fe.script(e['ptr']):
            if op in (0x6B, 0x6D, 0x6F):
                leaves.setdefault(NAMES.get(args[0] & 0xFF, '?'), turn_text(e))
    for u in m['units']:
        if u['type'] != 'enemy' and u['name'] in leaves:
            u['note'] = f"{u['note']}; leaves the map: {leaves[u['name']].lower()}"
    build_arrivals(ch, m, source, talks, diffs)


def spread(units, m):
    """Units that end on a tile another unit already holds go to the nearest free tile (by steps, then top to bottom, left to
    right): the game moves them off; which tile it picks isn't simulated. True when any moved."""
    taken, moved = set(), False
    for u in units:
        if u['tile'] in taken and not u['army']:
            x0, y0 = u['tile']
            free = sorted((abs(x - x0) + abs(y - y0), y, x) for x in range(m['width']) for y in range(m['height'])
                          if (x, y) not in taken)
            u['tile'] = (free[0][2], free[0][1])
            moved = True
        taken.add(u['tile'])
    return moved


def describe_flag(ch, flag):
    for e in ch.turns + ch.talks + ch.locations + ch.misc:
        if e['flag'] == flag and e['type'] != 1:
            if e['type'] == 2:
                return turn_text(e)
            if e['type'] in (3, 4):
                return f"once {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}"
            if 5 <= e['type'] <= 10:
                return f"once the tile at ({e['b'][0] + 1}, {ch.h - e['b'][1]}) is visited"
            if e['type'] in (11, 12, 13):
                return 'once one of your units enters the area'
    return None


def arrival_of(ch, e):
    t = e['type']
    if t == 2:
        return turn_text(e), None
    if t in (1, 15, 16):
        flag = (e['b'][0] | e['b'][1] << 8) if t == 1 else (e['b'][4] | e['b'][5] << 8)
        what = describe_flag(ch, flag)
        return (what[0].upper() + what[1:] if what else 'After an event in the chapter'), None
    if t in (3, 4):
        return f"When {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}", None
    if t in (11, 12, 13):
        x1, y1, x2, y2 = e['b'][:4]
        return 'When one of your units enters the marked area', [{'who': 'player', 'rect': gm.rect_to_app((x1, y1, x2, y2), ch.h)}]
    if t in (5, 6):
        return f"When the house or village at ({e['b'][0] + 1}, {ch.h - e['b'][1]}) is visited", None
    return 'During the chapter', None


def area_allowed(e, mode):
    return e['type'] not in (12, 13) or (e['type'] == 12) == (mode == 'Eliwood')


def build_arrivals(ch, m, source, talks, diffs):
    h = m['height']
    groups, joiners = [], []
    events = [e for e in ch.turns if not Chapter.is_opening(e) and e['ptr'] != ch.ev['opening']]
    events += [e for e in ch.talks + ch.misc + ch.locations if e['type'] in (1, 3, 4, 5, 6, 11, 12, 13, 15, 16)]
    n = 0
    for e in events:
        if not r.is_ptr(e['ptr']) or not area_allowed(e, ch.mode) or (e['type'] in (3, 4) and not talk_allowed(e, ch.mode)):
            continue
        on = {}
        for d in diffs:
            hard = d == 'Hard'
            if e['type'] == 2 and not condition_ok(e, ch.mode, hard):
                continue
            on[d] = fe.Run(ch.world(hard, turn=e['b'][0] if e['type'] == 2 else 1)).run(e['ptr'])
        if not any(run.loads for run in on.values()):
            continue
        when, areas = arrival_of(ch, e)
        # One group per difficulty where they differ; one where they're the same.
        by_units = {}
        for d, run in on.items():
            key = tuple((u['char'], class_of(u), u['tile'], u['side']) for u in run.units)
            by_units.setdefault(key, (run, []))[1].append(d)
        for run, ds in by_units.values():
            only = ds if len(ds) < len(diffs) else None
            foes = [u for u in run.units if u['side'] == 'enemy']
            friends = [u for u in run.units if u['side'] != 'enemy']
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': ({d: when for d in only} if only else when),
                     'units': [{**unit_entry(u, h, talks.get(NAMES.get(u['char'], '?'))), 'from': gm.to_app(u['start'], h)} for u in foes]}
                if areas:
                    g['areas'] = areas
                if only:
                    for u in g['units']:
                        u['difficulties'] = only
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if (entry.get('talk') or '').startswith('Recruit'):
                        for i in u['items']:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining")
                    elif entry['type'] in ('boss', 'named'):
                        for i in drops(u):
                            source(i, m['id'], 'drop-later', f"Dropped by {entry['name']}, a foe arriving mid-chapter")
                        for i in u['items']:
                            source(i, m['id'], 'foe-later', f"Carried by {entry['name']}, a foe arriving mid-chapter")
                    else:
                        for i in drops(u):
                            source(i, m['id'], 'drop-later', f"Dropped by a foe {CLASSES.get(class_of(u), '?')} arriving mid-chapter")
                        for i in u['items']:
                            source(i, m['id'], 'foe-later-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')} arriving mid-chapter")
            for u in friends:
                if u['army']:
                    continue
                named = has_portrait(u['char'])
                j = {'name': NAMES.get(u['char'], '?') if named else CLASSES.get(class_of(u), '?'), 'tile': gm.to_app(u['tile'], h),
                     'from': gm.to_app(u['start'], h), 'group': f"e{e['at']:x}", 'when': ({d: when for d in only} if only else when)}
                if areas:
                    j['areas'] = areas
                if u['side'] == 'npc':
                    j['ally'] = True
                    if not named:
                        j['generic'] = True
                    if NAMES.get(u['char']) in talks:
                        j['talk'] = talks[NAMES.get(u['char'])]
                else:
                    for i in u['items']:
                        source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining")
                if j not in joiners:
                    joiners.append(j)
    if groups:
        m['reinforcements'] = groups
    if joiners:
        m['joiners'] = joiners


def reward_of(ch, ptr):
    """What a village or house gives, from its script: items, gold. Visitors the script tells apart get their own."""
    base = fe.Run(ch.world(False)).run(ptr)
    whos = sorted({args[1] & 0xFF for _, op, w, args in fe.script(ptr) if op == 0x4E})

    def words(run):
        return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])

    plain = words(base)
    special = {}
    for c in whos:
        w = words(fe.Run(ch.world(False, active=c)).run(ptr))
        if w != plain:
            special.setdefault(w, []).append(NAMES.get(c, '?'))
    if not special:
        return plain, [i for i, _ in base.items], base
    parts = [f"{w} if visited by {' or '.join(names)}" for w, names in special.items()]
    items = [i for i, _ in base.items] + [i for c in whos for i, _ in fe.Run(ch.world(False, active=c)).run(ptr).items]
    return '; '.join(parts) + (f'; anyone else: {plain}' if plain else ''), items, base


SHOP = {0x13: 'Armory', 0x14: 'Vendor', 0x15: 'Secret shop'}
GOLD_ITEM = 0x76


def build_locations(ch, m, source):
    h = m['height']
    seize, seen = [], set()
    for e in ch.locations:
        x, y, cmd = e['b'][0], e['b'][1], e['b'][2]
        key = (e['type'], x, y, cmd)
        if key in seen:
            continue
        seen.add(key)
        tile = gm.to_app((x, y), h)
        t = e['type']
        if t == 5 and cmd == 0x0F:
            seize.append(tile)
        elif t == 7:
            item, amount = e['ptr'] & 0xFFFF, e['ptr'] >> 16
            if item == GOLD_ITEM:
                contents = f'{amount} gold'
            else:
                contents = item_name(item)
                source(item, m['id'], 'chest', 'In a chest')
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': contents})
        elif t == 8:
            m['objects'].append({'type': 'door', 'tile': tile})
        elif t == 10 and cmd in SHOP:
            o, stock = r.off(e['ptr']), []
            while r.u16(o):
                stock.append(r.u16(o))
                o += 2
            m['objects'].append({'type': 'shop', 'tile': tile, 'kind': SHOP[cmd], 'stock': [item_name(i) for i in stock]})
            for i in stock:
                source(i, m['id'], 'shop', f"Sold at the {SHOP[cmd].lower()}")
        elif t in (5, 6) and cmd == 0x0E and r.is_ptr(e['ptr']):
            if {(x, y), (x, y - 1)} & getattr(ch, 'closed', set()):
                continue
            reward, items, run = reward_of(ch, e['ptr'])
            joins = [NAMES.get(u['char'], '?') for _, grp, _ in run.loads for u in grp if u['side'] == 'player']
            if t == 5 and not reward and not joins:
                continue
            o = {'type': 'village', 'tile': tile, 'reward': reward}
            notes = ([f"{' and '.join(joins)} {'joins' if len(joins) == 1 else 'join'} your army."] if joins else [])
            if t == 5:
                notes.append('(A house.)')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i in items:
                source(i, m['id'], 'village', 'Given at a village' if t == 6 else 'Given at a house')
    if seize:
        what = 'the throne' if 'throne' in m['victory'].lower() else 'the gate'
        m['objectives'].append({'type': 'seize', 'tiles': seize, 'label': f"Seize {what} with {NAMES[LORD[ch.mode]]}"})
    # Hidden items: area events whose script gives one.
    for e in ch.misc:
        if e['type'] not in (11, 12, 13) or not r.is_ptr(e['ptr']) or not area_allowed(e, ch.mode):
            continue
        cmds = fe.script(e['ptr'])
        gives = [args[0] & 0xFFFF for _, op, _, args in cmds if op == 0x5B]
        if not gives:
            continue
        area = gm.rect_to_app(tuple(e['b'][:4]), h)
        finders = [NAMES.get(args[1] & 0xFF, '?') for _, op, w, args in cmds if op == 0x4E and w >> 16]
        o = {'type': 'hidden', 'tile': [(area[0] + area[2]) // 2, (area[1] + area[3]) // 2], 'area': area,
             'contents': ', '.join(item_name(i) for i in gives)}
        if finders:
            o['note'] = f"Found only by {' or '.join(finders)}, by stopping in the area."
        m['objects'].append(o)
        for i in gives:
            source(i, m['id'], 'hidden', 'Hidden in the area')
    # The end of the chapter: gifts the end script hands over, and who joins there.
    end = fe.Run(ch.world(False)).run(ch.ev['end'])
    for i, who in end.items:
        source(i, m['id'], 'event', f'Given to {NAMES.get(who, "your army")} at the end of the chapter')
    for _, grp, _ in end.loads:
        for u in grp:
            if u['side'] == 'player':
                for i in u['items']:
                    source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')}, who joins at the end of the chapter")


def story():
    """(entry, map id, mode, number, heading, title) for every map, Lyn's story then Eliwood's and Hector's."""
    out = []
    for mode, entries in (('Lyn', LYN), ('Eliwood', ELIWOOD), ('Hector', HECTOR)):
        for entry in entries:
            rec = r.chapter(entry)
            text = r.text(r.u16(rec + (0x72 if mode == 'Hector' else 0x70)))
            head, title = heading_title(text)
            if entry in VERSION:
                title = f'{title} (vs {VERSION[entry]})'
            if entry == 47:
                title = f'{title} (part 2)'
            number = int(re.match(r'Ch\.([0-9]+)', head).group(1)) if head.startswith('Ch.') else (0 if head == 'Prologue' else 33)
            slug = {'Lyn': 'lyn', 'Eliwood': 'e', 'Hector': 'h'}[mode]
            tail = head.replace('Ch.', '').replace(' pt 2', '-2').lower() if head.startswith('Ch.') else head.lower()
            if entry in VERSION:
                tail += '-' + VERSION[entry].lower()
            if entry == 47:
                tail += '-2'
            out.append((entry, f'fe7-{slug}-{tail}', mode, number, head, title))
    return out


def main():
    maps, sources = [], {}
    used_terrain = set()

    def source(item, map_id, kind, words):
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    for entry, map_id, mode, number, heading, title in story():
        grid = r.grid(entry)
        h, w = len(grid), len(grid[0])
        for row in grid:
            used_terrain |= set(row)
        unknown = {t for row in grid for t in row} - set(gm.TERRAIN)
        assert not unknown, (map_id, unknown)
        rec = r.chapter(entry)
        diffs = ['Normal'] if mode == 'Lyn' else ['Normal', 'Hard']
        m = {
            'id': map_id, 'route': mode, 'chapter': number, 'heading': heading, 'title': title, 'width': w, 'height': h,
            'grid': [''.join(encode(GAME, gm.TERRAIN[t][0]) for t in row) for row in grid],
            **({'fog': True} if R[rec + 0xC] else {}),
            'victory': r.text(r.u16(rec + 0x8C)), 'defeat': DEFEAT[mode], 'objectives': [], 'units': [], 'starts': [], 'objects': [],
            'changes': [], 'notes': [], 'lord': NAMES[LORD[mode]],
            **({'difficulties': diffs} if mode == 'Lyn' else {}),
        }
        if entry in OPENS:
            note = OPENS[entry]
            for k, v in NUMBERS.get(mode, NUMBERS['Eliwood']).items():
                note = note.replace('{%d}' % k, v)
            m['notes'].append(note)
        ch = Chapter(entry, mode, h)
        build_units(ch, m, source, diffs)
        build_locations(ch, m, source)
        maps.append(m)
        print(map_id, title, f'{w}x{h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    groups = gm.move_groups(r, MOVE_NAMES)
    assert gm.flier_rows_are_zero(r, 50)
    info = gm.terrain_table(r, GAME, used_terrain, groups)
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
