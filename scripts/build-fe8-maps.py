"""
Builds The Sacred Stones' maps from the user's (U) ROM (scripts/gba_rom.py, scripts/fe8_events.py):
  src/data/fe8/fe8Terrain.ts      terrain stats and movement costs by movement type
  src/data/fe8/fe8Maps.ts         every chapter of the story, Eirika's and Ephraim's routes, the Tower of Valni and the Lagdou Ruins:
                                  terrain, units, reinforcements, joiners, chests, villages, shops
  src/data/fe8/fe8ItemSources.ts  where each item turns up, by chapter (the weapon page and the spoiler block)
Run:
    python scripts/build-fe8-maps.py

What is read where (data-raw/fe8/README.md has the formats):
  - Chapter records, 0x94 bytes at 0x8B0890: the map at +8 (an index into the pointer table at 0x8B363C), map changes at +0xB, the
    fog vision at +0xC, the generic enemies' level changes by difficulty at +0x14, the title at +0x70 (text id), the event data at
    +0x74, the goal at +0x88, the character to protect at +0x8E.
  - A chapter's start: the opening scene, played for the route and difficulty; where it calls the preparations screen, your army's
    group gives the deploy tiles. Then every turn-1 event on your phase runs. Units end on the tile the scripted moves leave them.
  - Every later turn, talk, area and location event that loads units is a reinforcement, with when it fires.
Chapter titles and goals are the game's own text.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe8_events as fe  # noqa: E402
import gba_maps as gm  # noqa: E402
from gba_rom import rom  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe8', 'The Sacred Stones', 'build-fe8-maps.py'
r = rom('fe8')
R = r.R
NAMES = r.character_names()
CLASSES = r.class_names()
ITEMS = r.item_names()

EIRIKA, EPHRAIM = 1, 15
# The story as the chapter records list it, with the headings the game shows (the records' titles have no numbers): everyone plays
# the Prologue to Chapter 8 (5x is Ephraim's, between 5 and 6), then Eirika's route or Ephraim's. The order is the end scripts'
# (0x2A); the routes' Chapter 11 maps (entries 61, 62) come in through the world map.
SHARED = [(0, 'Prologue'), (1, 'Ch.1'), (2, 'Ch.2'), (3, 'Ch.3'), (4, 'Ch.4'), (6, 'Ch.5'), (5, 'Ch.5x'), (7, 'Ch.6'), (8, 'Ch.7'),
          (9, 'Ch.8')]
ROUTE_TAIL = ['Ch.9', 'Ch.10', 'Ch.11', 'Ch.12', 'Ch.13', 'Ch.14', 'Ch.15', 'Ch.16', 'Ch.17', 'Ch.18', 'Ch.19', 'Ch.20', 'Final',
              'Final pt 2']
EIRIKA_ROUTE = list(zip([10, 11, 61, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], ROUTE_TAIL))
EPHRAIM_ROUTE = list(zip([23, 24, 62, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35], ROUTE_TAIL))
TOWER = [(36 + i, f'Tower {i + 1}') for i in range(8)]
RUINS = [(46 + i, f'Ruins {i + 1}') for i in range(10)]
DIFFS = ['Easy', 'Normal', 'Hard']

MOVE_NAMES = {1: 'Lords, heroes & thieves', 3: 'Paladins & great lords', 5: 'Cavaliers', 9: 'Armours', 72: 'Fliers',
              15: 'Infantry', 29: 'Rangers & dogs', 37: 'Mages & priests', 63: 'Fighters', 65: 'Brigands',
              66: 'Pirates', 67: 'Berserkers', 91: 'Mauthe Doogs & Tarvos', 102: 'Demon King'}
PHASE = {0x00: 'your phase', 0x40: "the other army's phase", 0x80: 'enemy phase'}
SHOP = {0x16: 'Armory', 0x17: 'Vendor', 0x18: 'Secret shop'}
# Location commands (the byte at +0xA of a location event).
VISIT, SEIZE, CHEST, DOOR = 0x10, 0x11, 0x14, 0x12
# Classes the difficulty's level change leaves alone (0x0800F818, 0x08017BFC: the two Gorgon Egg classes).
NO_LEVEL_CHANGE = {0x34, 0x62}


def char_record(c):
    return r.character_record(c)


def is_boss(c):
    """The boss flag: bit 0x8000 of the abilities (+0x28), set on each chapter's boss."""
    return bool(r.u32(char_record(c) + 0x28) & 0x8000)


def has_portrait(c):
    return r.u16(char_record(c) + 6) != 0


def class_of(u):
    return u['class'] or R[char_record(u['char']) + 5]


def level_of(u):
    return u['level'] if u['level'] is not None else R[char_record(u['char']) + 0xB]


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def drops(u):
    """The item a foe drops: its last, when its record's tile has the drop bit (bit 13, 0x2000: the unit's state gets 0x1000 as it's
    made, 0x08017CC4)."""
    return u['items'][-1:] if u.get('drop') else []


def levels(entry, u):
    """A unit's level by difficulty: an enemy whose character id is above 0x3B (the generic ones and the bosses) loses the chapter's
    Easy or Normal amount of levels or gains its Hard amount as it's made (0x0800F80A; the record's +0x14 nibbles: Easy, Hard,
    Normal), not below 1."""
    lv = level_of(u)
    if u['side'] != 'enemy' or u['char'] <= 0x3B or class_of(u) in NO_LEVEL_CHANGE:
        return {d: lv for d in DIFFS}
    b = R[r.chapter(entry) + 0x14], R[r.chapter(entry) + 0x15]
    return {'Easy': max(1, lv - (b[0] & 0xF)), 'Normal': max(1, lv - (b[1] & 0xF)), 'Hard': lv + (b[0] >> 4)}


def level_text(entry, u):
    lv = levels(entry, u)
    others = [f'{d} {lv[d]}' for d in ('Easy', 'Hard') if lv[d] != lv['Normal']]
    return f"Lv {lv['Normal']}" + (f" ({', '.join(others)})" if others else '')


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


class Chapter:
    def __init__(self, entry, mode, height):
        self.entry, self.mode, self.h = entry, mode, height
        self.away = set()
        self.ev = fe.events_of(entry)
        self.turns = fe.event_list(self.ev['turn'])
        self.talks = fe.event_list(self.ev['talk'])
        self.locations = fe.event_list(self.ev['location'])
        self.misc = fe.event_list(self.ev['misc'])
        self.changes = map_changes(entry)

    def world(self, difficulty='Normal', **kw):
        return fe.World(mode=self.mode, difficulty=difficulty, away=self.away, **kw)

    def run(self, ptr, difficulty='Normal', **kw):
        return fe.Run(self.world(difficulty, **kw), chapter=self.entry).run(ptr)

    def opening(self, difficulty):
        run = fe.Run(self.world(difficulty), chapter=self.entry)
        run.run(self.ev['opening'])
        if run.prep:
            # The preparations screen: your army deploys on its group's tiles (the same group on every difficulty), the units the
            # opening put on the map with it.
            run.units = [u for u in run.units if u['side'] != 'player']
            run.load(self.ev['army'], army=True)
        for e in self.turns:
            if self.is_opening(e) and fe.ROM.is_ptr(e['ptr']):
                run.run(e['ptr'])
        return run

    @staticmethod
    def is_opening(e):
        b = e['b']
        return e['type'] == 2 and b[0] == 1 and b[1] in (0, 1) and (b[2] | b[3] << 8) == 0


def turn_text(e):
    first, last, phase = e['b'][0], e['b'][1], e['b'][2] | e['b'][3] << 8
    p = PHASE.get(phase, 'any phase')
    if last == 255:
        return f'Every {p} from turn {first}' if first > 1 else f'Every {p}'
    if last > first:
        return f'Every turn from {first} to {last}, {p}'
    return f'Turn {first}, {p}'


def unit_entry(entry, u, h, talk=None):
    if u.get('monster'):
        # A random monster (bit 12 of the record's tile): its class, level and items are picked as it's made (0x08017ACC), so only
        # where it stands is the record's.
        note = 'Class, level and items picked at random as the map loads'
        if u.get('optional'):
            note += '; may not appear at all'
        return {'type': 'enemy', 'name': 'Random monster', 'tile': gm.to_app(u['tile'], h), 'note': note}
    c = u['char']
    cls = CLASSES.get(class_of(u), '?')
    name = NAMES.get(c, '?')
    items = [item_name(i) for i in u['items']]
    if u['side'] == 'enemy':
        kind = 'boss' if is_boss(c) else 'named' if has_portrait(c) else 'enemy'
    else:
        kind = 'ally'
    named = kind in ('boss', 'named') or (kind == 'ally' and has_portrait(c))
    lv = level_text(entry, u)
    out = {'type': kind, 'name': name if named else cls, 'tile': gm.to_app(u['tile'], h), 'note': f'{lv} {cls}' if named else lv}
    if kind == 'ally' and not named:
        out['generic'] = True
    if items:
        out['carries'] = items
    if u['side'] == 'enemy' and drops(u):
        out['drops'] = [item_name(i) for i in drops(u)]
    if talk:
        out['talk'] = talk
    return out


def talk_recruits(ch, e):
    """Whether a talk recruits its second character: its script changes that character's side to yours (0x34 variant 2)."""
    run = ch.run(e['ptr'], active=e['b'][0] or None)
    return e['b'][1] in run.recruits, run


def talks_of(ch):
    """{name: 'Recruit: talk with Eirika or Ephraim'} from the talk events."""
    found = {}
    for e in ch.talks:
        if e['type'] != 3 or not r.is_ptr(e['ptr']):
            continue
        a, b = e['b'][0], e['b'][1]
        recruits, run = talk_recruits(ch, e)
        t = found.setdefault(NAMES.get(b, '?'), {'recruit': [], 'talk': [], 'gives': []})
        who = NAMES.get(a, '?') if a else 'anyone'
        if recruits:
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


def lord_of(mode):
    return EPHRAIM if mode == 'Ephraim' else EIRIKA


def build_units(ch, m, source):
    h = m['height']
    talks = talks_of(ch)
    for e in ch.talks:
        if e['type'] == 3 and r.is_ptr(e['ptr']):
            recruits, run = talk_recruits(ch, e)
            for i, _ in run.items:
                source(i, m['id'], 'talk', f"{NAMES.get(e['b'][0], 'Anyone')} talks to {NAMES.get(e['b'][1], '?')}")
    runs = {d: ch.opening(d) for d in DIFFS}
    ch.closed = set()
    for cid in runs['Normal'].map_changes:
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
            seen[key] = seen.get(key, 0) + 1
            placed.setdefault(key + (seen[key],), (u, []))[1].append(d)
    if moved:
        m.setdefault('unconfirmed', []).append(
            "A unit whose tile was taken when it arrived is shown on the nearest free tile; the game picks its own free tile, which "
            "may differ.")
    lord_id = m['lordId']
    army = [(u, ds) for u, ds in placed.values() if u['army']]
    lord = next((u for u, _ in placed.values() if u['char'] == lord_id and u['side'] == 'player'), None)
    if army:
        m['starts'] = [gm.to_app(u['tile'], h) for u, _ in dict(((u['tile'], (u, ds)) for u, ds in army)).values()]
    if lord:
        m['corrinStart'] = gm.to_app(lord['tile'], h)
        if not army:
            m['starts'] = [m['corrinStart']]
    forced = []
    # A unit the opening scene loads as yours joins here, even when it leaves the map before the battle.
    for run in runs.values():
        for _, grp, in_army in run.loads:
            for g in grp:
                if g['side'] == 'player' and not in_army:
                    for i in g['items']:
                        source(i, m['id'], 'kit', f"Carried by {NAMES.get(g['char'], '?')} on joining", who=g['char'])
    prep = runs['Normal'].prep
    for u, ds in placed.values():
        if u['army']:
            continue
        if u['side'] == 'player':
            if u['char'] != lord_id and not prep:
                f = {'name': NAMES.get(u['char'], '?'), 'tile': gm.to_app(u['tile'], h)}
                if f not in forced:
                    forced.append(f)
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'])
            continue
        e = unit_entry(ch.entry, u, h, talks.get(NAMES.get(u['char'], '?')))
        if m['victory'] == f"Defeat {e['name']}" or (e['name'] in m['victory'] and is_boss(u['char'])):
            e['type'] = 'boss'
        if len(ds) < len(DIFFS):
            e['difficulties'] = ds
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit'):
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'])
        elif e['type'] in ('boss', 'named') and u['side'] == 'enemy':
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by {e['name']}")
            for i in u['items']:
                source(i, m['id'], 'foe', f"Carried by {e['name']}, a foe")
        elif u['side'] == 'enemy' and not u.get('monster'):
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by a foe {CLASSES.get(class_of(u), '?')}")
            for i in u['items']:
                source(i, m['id'], 'foe-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')}")
    if forced:
        m['forced'] = forced
    build_arrivals(ch, m, source, talks)


def describe_flag(ch, flag):
    for e in ch.turns + ch.talks + ch.locations + ch.misc:
        if e['flag'] == flag and e['type'] != 1:
            if e['type'] == 2:
                return turn_text(e)
            if e['type'] == 3:
                return f"once {NAMES.get(e['b'][0], 'anyone')} talks to {NAMES.get(e['b'][1], '?')}"
            if 5 <= e['type'] <= 10:
                return f"once the tile at ({e['b'][0] + 1}, {ch.h - e['b'][1]}) is visited"
            if e['type'] == 11:
                return 'once one of your units enters the area'
    return None


def arrival_of(ch, e):
    t = e['type']
    if t == 2:
        return turn_text(e), None
    if t == 1:
        flag = e['b'][0] | e['b'][1] << 8
        what = describe_flag(ch, flag)
        return (what[0].upper() + what[1:] if what else 'After an event in the chapter'), None
    if t == 3:
        return f"When {NAMES.get(e['b'][0], 'anyone')} talks to {NAMES.get(e['b'][1], '?')}", None
    if t == 11:
        x1, y1, x2, y2 = e['b'][:4]
        return 'When one of your units enters the marked area', [{'who': 'player', 'rect': gm.rect_to_app((x1, y1, x2, y2), ch.h)}]
    if t in (5, 6):
        return f"When the house or village at ({e['b'][0] + 1}, {ch.h - e['b'][1]}) is visited", None
    return 'During the chapter', None


def armed_by(ch, flag):
    """An event whose flag the opening sets can't fire (an event runs only while its flag is clear) until another event clears the
    flag (0x02 variant 1): that event, or None."""
    for e in ch.turns + ch.talks + ch.misc + ch.locations:
        if r.is_ptr(e['ptr']) and e['type'] in (1, 2, 3, 11) or (e['type'] in (5, 6) and e['b'][2] == VISIT):
            if r.is_ptr(e['ptr']) and any(cmd == 0x02 and sub == 1 and args[0] == flag for _, cmd, sub, args in fe.script(e['ptr'])):
                return e
    return None


def build_arrivals(ch, m, source, talks):
    h = m['height']
    groups, joiners = [], []
    start_flags = set(ch.opening('Normal').world.flags)
    events = [e for e in ch.turns if not Chapter.is_opening(e)]
    events += [e for e in ch.talks + ch.misc if e['type'] in (1, 3, 11)]
    events += [e for e in ch.locations if e['type'] in (5, 6) and e['b'][2] == VISIT]
    n = 0
    for e in events:
        if not r.is_ptr(e['ptr']):
            continue
        on = {}
        for d in DIFFS:
            kw = {'turn': e['b'][0]} if e['type'] == 2 else {}
            if e['type'] == 3:
                kw['active'] = e['b'][0] or None
            on[d] = ch.run(e['ptr'], d, **kw)
        if not any(run.loads for run in on.values()):
            continue
        when, areas = arrival_of(ch, e)
        if e['flag'] and e['flag'] in start_flags:
            trigger = armed_by(ch, e['flag'])
            if not trigger:
                continue
            when, areas = arrival_of(ch, trigger)
        # One group per difficulty where they differ; one where they're the same.
        by_units = {}
        for d, run in on.items():
            key = tuple((u['char'], class_of(u), u['tile'], u['side']) for u in run.units)
            by_units.setdefault(key, (run, []))[1].append(d)
        for run, ds in by_units.values():
            only = ds if len(ds) < len(DIFFS) else None
            foes = [u for u in run.units if u['side'] == 'enemy']
            friends = [u for u in run.units if u['side'] != 'enemy']
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': ({d: when for d in only} if only else when),
                     'units': [{**unit_entry(ch.entry, u, h, talks.get(NAMES.get(u['char'], '?'))), 'from': gm.to_app(u['start'], h)}
                               for u in foes]}
                if areas:
                    g['areas'] = areas
                if only:
                    for u in g['units']:
                        u['difficulties'] = only
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if u.get('monster'):
                        continue
                    if (entry.get('talk') or '').startswith('Recruit'):
                        for i in u['items']:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining", who=u['char'])
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
                        if j['talk'].startswith('Recruit'):
                            for i in u['items']:
                                source(i, m['id'], 'kit-later', f"Carried by {j['name']} on joining", who=u['char'])
                else:
                    for i in u['items']:
                        source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'])
                if j not in joiners:
                    joiners.append(j)
    if groups:
        m['reinforcements'] = groups
    if joiners:
        m['joiners'] = joiners


def reward_of(ch, ptr):
    """What a village or house gives, from its script: items, gold. Visitors the script tells apart (0x33 variant 4) get their own."""
    base = ch.run(ptr)
    whos = sorted({args[0] for _, cmd, sub, args in fe.script(ptr) if cmd == 0x33 and sub == 4 and args[0] < 0x100})

    def words(run):
        return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])

    plain = words(base)
    special = {}
    runs = {c: ch.run(ptr, active=c) for c in whos}
    for c, run in runs.items():
        w = words(run)
        if w != plain:
            special.setdefault(w, []).append(NAMES.get(c, '?'))
    if not special:
        return plain, [i for i, _ in base.items], base
    parts = [f"{w} if visited by {' or '.join(names)}" for w, names in special.items()]
    items = [i for i, _ in base.items] + [i for run in runs.values() for i, _ in run.items]
    return '; '.join(parts) + (f'; anyone else: {plain}' if plain else ''), items, base


def end_condition(ch, item):
    """What an end script asks before a reward, in words: the characters whose death loses it (each checked character is tried
    dead in turn, 0x33 variant 2), and how many of the other army's units it needs left (0x19 variant 5 compared with a slot it
    set)."""
    cmds = [c for p in script_tree(ch.ev['end']) for c in fe.script(p)]
    checked = list(dict.fromkeys(args[0] for _, cmd, sub, args in cmds if cmd == 0x33 and sub == 2))
    needed = [c for c in checked if item not in [i for i, _ in ch.run(ch.ev['end'], best=True, dead={c}).items]]
    parts = []
    if needed:
        counts = {}
        for c in needed:
            counts[NAMES.get(c, '?')] = counts.get(NAMES.get(c, '?'), 0) + 1
        words = [f"all {NUMBER[k]} '{n}' units" if k > 1 else n for n, k in counts.items()]
        parts.append((', '.join(words[:-1]) + ' and ' + words[-1] if len(words) > 1 else words[0]) + ' survive')
    if any(cmd == 0x19 and sub == 5 for _, cmd, sub, _ in cmds):
        sets = {args[0]: args[1] for _, cmd, sub, args in cmds if cmd == 0x05}
        need = next((sets.get(args[2]) for _, cmd, sub, args in cmds if cmd == 0x0C and sub == 5 and args[2] in sets), None)
        parts.append(f"at least {need} of the other army's units are left" if need else "enough of the other army's units are left")
    return ' and '.join(parts) or 'a condition in the end scene is met'


# The shared script the desert's buried items call (0x089EE61C): the finder's class (0x33 variant 7) is a Thief (0x0D) or a Rogue
# (0x33), or a random number below 100 (0x04) is at most the Luck the caller read (s2); then it gives the item in s3.
DIG = 0x089EE61C

NUMBER = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six'}


def script_tree(ptr, seen=None):
    """A script and the chapter's own scripts it calls (the shared helpers in 0x0859xxxx / 0x089Exxxx aren't followed)."""
    seen = seen if seen is not None else []
    if ptr in seen or not r.is_ptr(ptr):
        return seen
    seen.append(ptr)
    for _, cmd, _, args in fe.script(ptr):
        if cmd == 0x0A and len(args) > 2:
            q = args[1] | args[2] << 16
            if 0x089F0000 <= q < 0x08A10000:
                script_tree(q, seen)
    return seen


def build_locations(ch, m, source):
    h = m['height']
    seize, seen = [], set()
    grid = r.grid(ch.entry)
    for e in ch.locations:
        x, y, cmd = e['b'][0], e['b'][1], e['b'][2]
        key = (e['type'], x, y, cmd)
        if key in seen:
            continue
        if y >= len(grid) or x >= len(grid[0]) or gm.GAME_TERRAIN[GAME][grid[y][x]][0] == '#':
            # On a tile no unit can enter (Tower of Valni 1's armory and vendor in its walled-off corner): never reached.
            continue
        seen.add(key)
        tile = gm.to_app((x, y), h)
        t = e['type']
        if t == 5 and cmd == SEIZE:
            seize.append(tile)
        elif t == 7:
            item, amount = e['ptr'] & 0xFFFF, e['ptr'] >> 16
            if item == fe.GOLD_ITEM:
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
        elif t in (5, 6) and cmd == VISIT and r.is_ptr(e['ptr']):
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
        v = m['victory'].lower()
        what = 'the throne' if 'throne' in v else 'the gate'
        m['objectives'].append({'type': 'seize', 'tiles': seize, 'label': f"Seize {what} with {NAMES[m['lordId']]}"})
    # Hidden items: area events whose script gives one.
    for e in ch.misc:
        if e['type'] != 11 or not r.is_ptr(e['ptr']):
            continue
        run = ch.run(e['ptr'])
        gives = [i for i, _ in run.items]
        if not gives:
            continue
        area = gm.rect_to_app(tuple(e['b'][:4]), h)
        finders = sorted({NAMES.get(args[0], '?') for _, cmd, sub, args in fe.script(e['ptr']) if cmd == 0x33 and sub == 4
                          and args[0] < 0x100})
        o = {'type': 'hidden', 'tile': [(area[0] + area[2]) // 2, (area[1] + area[3]) // 2], 'area': area,
             'contents': ', '.join(item_name(i) for i in gives)}
        if finders:
            o['note'] = f"Found only by {' or '.join(finders)}, by stopping in the area."
        calls = {args[1] | args[2] << 16 for _, cmd, _, args in fe.script(e['ptr']) if cmd == 0x0A and len(args) > 2}
        if DIG in calls:
            o['note'] = ('Found by one of your units stopping in the area: always by a Thief or a Rogue, by anyone else when a random '
                         "number from 0 to 99 is at most the unit's Luck.")
        m['objects'].append(o)
        for i in gives:
            source(i, m['id'], 'hidden', 'Hidden in the area')
    # The end of the chapter: gifts the end script hands over, and who joins there. A gift the script gives only in the best case
    # (everyone it asks about alive, enough of the other army left) says on what, read from the script's own checks.
    end = ch.run(ch.ev['end'])
    best = ch.run(ch.ev['end'], best=True)
    for i, who in end.items:
        source(i, m['id'], 'event', f'Given to {NAMES.get(who, "your army")} at the end of the chapter')
    extra = [(i, who) for i, who in best.items if (i, who) not in end.items]
    if extra:
        for i, who in extra:
            cond = end_condition(ch, i)
            text = f'Given to {NAMES.get(who, "your army")} at the end of the chapter if {cond}'
            source(i, m['id'], 'event', text)
            m['notes'].append(f'{item_name(i)}: {text[0].lower() + text[1:]}.')
    for _, grp, _ in end.loads:
        for u in grp:
            if u['side'] == 'player':
                for i in u['items']:
                    source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')}, who joins at the end of the chapter",
                           who=u['char'])


WM_NODES = 0x2060B0
WM_NODE_COUNT = 29
WM_SHOPS = ((0xC, 'armory'), (0x10, 'vendor'), (0x14, 'secret shop'))


def world_map_shops():
    """The world map's towns (0x20-byte nodes at 0x2060B0, the decomp's GMapNodeData): name (+0x1C), the chapter played there on
    Eirika's and Ephraim's routes (+4, +5), and u16 item lists for an armory, a vendor and a secret shop (+0xC, +0x10, +0x14)."""
    out = []
    for k in range(WM_NODE_COUNT):
        b = WM_NODES + 0x20 * k
        shops = []
        for at, kind in WM_SHOPS:
            p = r.u32(b + at)
            if p:
                o, stock = r.off(p), []
                while r.u16(o):
                    stock.append(r.u16(o))
                    o += 2
                shops.append((kind, stock))
        if shops:
            out.append({'name': r.text(r.u16(b + 0x1C)), 'chapters': {'Eirika': R[b + 4], 'Ephraim': R[b + 5]}, 'shops': shops})
    return out


def story():
    """(entry, map id, route, mode, heading) for every map: the shared chapters, Eirika's route, Ephraim's, then the side maps."""
    out = []
    for entry, head in SHARED:
        out.append((entry, f"fe8-{head.replace('Ch.', '').lower()}", 'Shared', 'Ephraim' if entry == 5 else 'Prologue', head))
    for route, chapters in (('Eirika', EIRIKA_ROUTE), ('Ephraim', EPHRAIM_ROUTE)):
        for entry, head in chapters:
            tail = head.replace('Ch.', '').replace(' pt 2', '-2').lower()
            out.append((entry, f'fe8-{route.lower()}-{tail}', route, route, head))
    for entry, head in TOWER + RUINS:
        out.append((entry, f"fe8-{head.lower().replace(' ', '-')}", 'Extra', 'Ephraim', head))
    return out


def main():
    maps, sources = [], {}
    used_terrain = set()
    # A unit's items count once per route: when it first joins (the shared chapters count for both routes).
    joined = {'Shared': set()}
    joining = {}

    def source(item, map_id, kind, words, who=None):
        if who is not None:
            if who in joined[route]:
                return
            if joining.setdefault(who, (kind, words)) != (kind, words):
                return
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    for entry, map_id, route, mode, heading in story():
        joined.setdefault(route, set(joined['Shared']))
        joining = {}
        grid = r.grid(entry)
        h, w = len(grid), len(grid[0])
        for row in grid:
            used_terrain |= set(row)
        unknown = {t for row in grid for t in row} - set(gm.TERRAIN)
        assert not unknown, (map_id, unknown)
        rec = r.chapter(entry)
        lord = lord_of(mode)
        protect = R[rec + 0x8E]
        # The lords who lose the game: the route's, and the other twin where the chapter puts them on its map as yours (not
        # confirmed: the game-over check wasn't traced); the character the chapter record says to protect (+0x8E).
        twin = EPHRAIM if lord == EIRIKA else EIRIKA
        ch0 = Chapter(entry, mode, h)
        ch0.away = set(range(1, 0x40)) - joined[route]
        here = {u['char'] for u in ch0.opening('Normal').units if u['side'] == 'player' and not u['army']}
        here |= {u['char'] for _, grp, army in ch0.opening('Normal').loads for u in grp if army and u is grp[0]}
        losers = [NAMES[lord]] + ([NAMES[twin]] if twin in here else [])
        if protect:
            losers.append(NAMES.get(protect, '?'))
        defeat = ' or '.join(losers) + ' is defeated'
        if route == 'Extra':
            defeat = 'The lord of your route (Eirika or Ephraim) is defeated'
        m = {
            'id': map_id, 'route': route, 'chapter': 0 if heading == 'Prologue' else int(''.join(ch for ch in heading if ch.isdigit()) or 21),
            'heading': heading, 'title': r.text(r.u16(rec + 0x70)), 'width': w, 'height': h,
            'grid': [''.join(encode(GAME, gm.GAME_TERRAIN[GAME][t][0]) for t in row) for row in grid],
            **({'fog': True} if R[rec + 0xC] else {}),
            'victory': r.text(r.u16(rec + 0x88)), 'defeat': defeat, 'objectives': [], 'units': [], 'starts': [], 'objects': [],
            'changes': [], 'notes': [], 'lord': NAMES[lord], 'lordId': lord,
        }
        ch = Chapter(entry, mode, h)
        ch.away = set(range(1, 0x40)) - joined[route]
        build_units(ch, m, source)
        build_locations(ch, m, source)
        loaded = {g['char'] for d in DIFFS for _, grp, in_army in ch.opening(d).loads if not in_army for g in grp
                  if g['side'] == 'player'}
        joined[route] |= set(joining) | loaded
        del m['lordId']
        maps.append(m)
        print(map_id, m['title'], f'{w}x{h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    # The world map's town shops: open from the chapter after the one played there (not confirmed), on each route that passes
    # through the town, for the rest of the game.
    ids = {(route, entry): map_id for entry, map_id, route, _, _ in story()}
    for town in world_map_shops():
        for route in ('Eirika', 'Ephraim'):
            entry = town['chapters'][route]
            map_id = ids.get(('Shared', entry)) or ids.get((route, entry))
            if not map_id:
                continue
            for kind, stock in town['shops']:
                words = f"Sold at the {kind} in {town['name']} (world map)" + (', with a Member Card' if kind == 'secret shop' else '')
                for i in stock:
                    entry_ = {'mapId': map_id, 'kind': 'town-shop-later', 'text': words}
                    lst = sources.setdefault(item_name(i), [])
                    if entry_ not in lst:
                        lst.append(entry_)

    groups = gm.move_groups(r, MOVE_NAMES)
    assert gm.flier_rows_are_zero(r, 72)
    info = gm.terrain_table(r, GAME, used_terrain, groups)
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
