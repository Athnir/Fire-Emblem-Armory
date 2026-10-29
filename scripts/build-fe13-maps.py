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
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
MAIN = D.persons('static')
CHAPTERS = {c['key']: c for c in D.chapters()}
GENERIC_LABELS = set()


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


def generic_labels():
    """Name labels the game gives many units (Risen, Plegian, Valmese...): a label two or more of a chapter's characters share. A
    recurring character (Gangrel) has one record per chapter, so stays named."""
    out = set()
    for f in os.listdir(os.path.join(ROMFS, 'data', 'person')):
        key = f.split('.')[0]
        if key in ('static', 'dual', 'aDebug'):
            continue
        count = defaultdict(int)
        for pid, p in D.persons(key).items():
            count[p['name_label']] += 1
        out |= {label for label, n in count.items() if n >= 2}
    return out


def unit_entry(src, u, h, generic_ok=True):
    """A placement record -> the app's unit (no difficulties yet)."""
    pid = u['pid']
    if pid == DUMMY:
        # A spot the game fills with a foe it picks (the Endgame's sigils pick a class at random from the map's templates).
        e = {'type': 'enemy' if u['team'] == 1 else 'ally', 'name': 'Random foe' if u['team'] == 1 else 'Random ally',
             'tile': to_app(*u['end'], h), 'note': 'The game picks this unit at random when it appears.', '_pid': pid}
        if u['team'] != 1:
            e['generic'] = True
        return e
    name = unit_name(src, pid)
    p = person(src, pid)
    label = p['name_label'] if p else None
    items = [item_name(i['iid']) for i in u['items'] if item_name(i['iid'])]
    drops = [item_name(i['iid']) for i in u['items'] if i['drop'] and item_name(i['iid'])]
    cls = class_name(src, pid)
    lv = level(src, pid)
    note = ' '.join(x for x in [f'Lv {lv}' if lv else '', cls or ''] if x)
    if cls == 'Mirage':
        # Paralogue 22's shadows: ForceUnitTransformForX022 turns each into a copy of one of your units as the battle starts.
        note = 'Takes the form of one of your units as the battle starts'
    if items:
        note += (': ' if note else '') + ', '.join(items)
    generic = label in GENERIC_LABELS and pid not in MAIN
    if u['team'] == 1:
        kind = 'boss' if u['boss'] else ('enemy' if generic else 'named')
    else:
        kind = 'ally'
    e = {'type': kind, 'name': name, 'tile': to_app(*u['end'], h), 'note': note, '_pid': pid}
    if drops and u['team'] == 1:
        e['drops'] = drops
    if items and u['team'] == 1:
        e['carries'] = items
    if kind == 'ally' and generic:
        e['generic'] = True
    return e


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


def turns_text(ts):
    runs, a = [], ts[0]
    for prev, t in zip(ts, ts[1:] + [None]):
        if t != prev + 1:
            runs.append(f'{a}' if a == prev else f'{a}–{prev}')
            a = t
    return ('Turn ' if len(ts) == 1 else 'Turns ') + ', '.join(runs)


def arrivals(src, h):
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
            phase = E.PHASES.get(args[2]) if k != E.REINFORCE and len(args) > 2 else None
            for di, dname in enumerate(E.DIFFS):
                for t in range(max(first, 1), (last if last > 0 else 30) + 1):
                    for group, cond in E.run(ch.s, hd, di, t):
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
                    else:
                        other[group][dname] = 'Once a condition in the chapter is met'
        elif k == 0:
            for di, dname in enumerate(E.DIFFS):
                for group, cond in E.run(ch.s, hd, di, 1):
                    other[group].setdefault(dname, 'During a story event')
    out = defaultdict(dict)
    for group, by in turns_of.items():
        for dname, parts in by.items():
            texts = []
            for (phase, cond), ts in sorted(parts.items(), key=lambda kv: min(kv[1])):
                ts = sorted(ts)
                text = turns_text(ts) if len(ts) < 20 else f'Every turn from turn {ts[0]}'
                if phase and phase != 'player phase':
                    text += f', {phase}'
                if cond:
                    text += ', once a condition in the chapter is met'
                texts.append(text)
            out[group][dname] = '; '.join(texts)
    for group, by in other.items():
        for dname, text in by.items():
            out[group][dname] = f"{out[group][dname]}; {text[0].lower() + text[1:]}" if dname in out[group] else text
    return out, areas, turncoats, gone


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
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], False))
            if group == 'Player':
                tile = to_app(*u['end'], h)
                starts.append(tile)
                if u['pid'] == 'PID_クロム':
                    lord = tile
                if u['flags'] & 0x02:
                    forced.append({'name': unit_name(src, u['pid']), 'tile': tile})
                continue
            if not playable(*u['end'], w, h) or u['pid'] in left:
                continue
            e = with_difficulties(u, unit_entry(src, u, h))
            units.append(e)
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
    m['units'] = units
    m['starts'] = starts
    if lord:
        m['corrinStart'] = lord
    if forced:
        m['forced'] = forced
    # What comes later.
    times, areas, turncoats, gone = arrivals(src, h)
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
                     'units': [{**with_difficulties(u, unit_entry(src, u, h)), 'from': to_app(*u['start'], h)} for u in foes]}
            if areas.get(group):
                g_out['areas'] = areas[group]
            reinforcements.append(g_out)
        for u in members:
            if u['team'] == 1:
                continue
            j = {'name': unit_name(src, u['pid']), 'tile': to_app(*u['end'], h), 'from': to_app(*u['start'], h), 'group': group,
                 'when': collapse(by), '_pid': u['pid']}
            if u['team'] == 0:
                facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], False))
            if u['team'] == 2:
                j['ally'] = True
            joiners.append(j)
    if reinforcements:
        m['reinforcements'] = reinforcements
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
                facts['joins'].append((e['_pid'], groups_items(groups, e['_pid']), False))
    # After the battle: units the end of the chapter places on your side join then (Chapter 4's Lon'qu, Chapter 7's Cordelia).
    for hd in ch.of_kind(E.END):
        for di in range(3):
            for group, cond in E.run(ch.s, hd, di, 99):
                for u in groups.get(group, []):
                    if u['team'] == 0 and u['pid'] not in E.removed_pids(ch, hd):
                        facts['joins'].append((u['pid'], [i['iid'] for i in u['items']], True))
    # Gifts the story hands over in the chapter's own script (the end of Chapter 24's Exalted Falchion, a DLC map's reward).
    for hd in ch.hs:
        for iid, pids in E.item_gains(hd):
            facts['gifts'].append((iid, hd['k'] == E.END, pids))
    # What foes drop and carry, for the weapon page.
    for e in units:
        if e['type'] != 'ally' and e.get('carries'):
            facts['carries'].append((e['name'], e['carries'], e.get('drops', []), False, e['type'] == 'enemy'))
    for g in reinforcements:
        for e in g['units']:
            if e.get('carries'):
                facts['carries'].append((e['name'], e['carries'], e.get('drops', []), True, e['type'] == 'enemy'))
    for group in random_pool:
        for u in groups.get(group, []):
            facts['random'].append(([item_name(i['iid']) for i in u['items'] if item_name(i['iid'])],
                                    [item_name(i['iid']) for i in u['items'] if i['drop'] and item_name(i['iid'])]))
    m['objects'], m['changes'], m['notes'] = [], [], []
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
    m['changes'] = scripted_changes(ch, tiles, w, h, mid)
    if key == '018':
        m['unconfirmed'] = ["Each lava islet's extent: the script names an islet by a corner, so the flames mark where each one is and "
                            'when it turns, not which tiles it covers.']
    if key == 'E027':
        m['unconfirmed'] = ['The Fire Emblem Wiki says the map is also lost if the green Lucina falls; nothing in its files says so.']
    if key == 'X016':
        m['notes'].append('Walls in this chapter collapse and rebuild themselves when your units reach set rows (the script moves them).')
        m['unconfirmed'] = ["Which wall opens when: the script's wall moves (TrickSet kind 22) aren't decoded yet, so the map shows "
                            'every wall standing.']
    for hd in ch.ths:
        if hd['k'] != E.TILE:
            continue
        x, y, kind = hd['args'][:3]
        tile = to_app(x, y, h)
        what = E.TILE_KINDS.get(kind)
        gains = [item_name(i) for i, _ in E.item_gains(hd) if item_name(i)]
        if what == 'village':
            m['objects'].append({'type': 'village', 'tile': tile, 'reward': ', '.join(gains)})
            facts['villages'].extend(gains)
        elif what == 'chest':
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': ', '.join(gains)})
            facts['chests'].extend(gains)
        elif what == 'door':
            m['objects'].append({'type': 'door', 'tile': tile})
        elif what == 'event':
            m['objects'].append({'type': 'event', 'tile': tile})
            facts['event_tiles'].append(tile)
    for e in units + joiners + [u for g in reinforcements for u in g['units']]:
        e.pop('_pid', None)
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


def scripted_changes(ch, g, w, h, mid):
    """What a chapter's script reshapes: Chapter 18's lava islets (TrickSet(x, y, 20, 4) on a turn's phase turns the islet whose corner
    is (x, y) to hazard terrain; the islets' extent isn't decoded, so the change marks the first lava floor at that corner and says when)
    and Chapter 23's barrier (its walls of light fall once Validar is first beaten: the IsDisposBoss handler)."""
    out = []
    when = defaultdict(list)
    for hd in ch.of_kind(E.TURN, E.TURN2):
        for args in ch.calls(hd, 'ev::TrickSet'):
            if args[2:] == [20, 4]:
                x, y = args[0], args[1]
                spot = next(((x + dx, y + dy) for dy in range(3) for dx in range(3) if g[y + dy][x + dx] == LAVA_FLOOR), (x, y))
                when[spot].append((hd['args'][0], hd['args'][2]))
    for n, (spot, times) in enumerate(sorted(when.items(), key=lambda kv: min(kv[1]))):
        text = ', '.join(f'turn {t} ({E.PHASES.get(p, "phase")})' for t, p in sorted(set(times)))
        out.append({'id': f'{mid}-islet{n + 1}', 'trigger': 'eruption', 'tile': {'default': to_app(*spot, h)}, 'usableBy': '',
                    'effect': f'The lava floor islet here turns to hazard terrain at the start of {text}.'})
    for hd in ch.of_kind(E.AREA):
        if ch.string(hd['args'][5]) == 'IsDisposBoss':
            tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if g[y][x] == BARRIER]
            if tiles:
                out.append({'id': f'{mid}-barrier', 'trigger': 'event', 'tile': {'default': to_app(*tiles[0], h)}, 'usableBy': '',
                            'effect': 'The barrier of light falls once Validar is first defeated.',
                            'patch': [{'tile': to_app(x, y, h), 'becomes': '.'} for x, y in tiles]})
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
    global GENERIC_LABELS
    GENERIC_LABELS = generic_labels()
    info, groups = build_terrain()
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, {i: c['name'] for i, c in enumerate(D.classes())})
    by_index = {it['index']: it for it in D.items()}
    sources = defaultdict(list)

    def add(name, mid, kind, text):
        if name and {'mapId': mid, 'kind': kind, 'text': text} not in sources[name]:
            sources[name].append({'mapId': mid, 'kind': kind, 'text': text})

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
        for who, carries, drops, later, generic in facts['carries']:
            whom = f'a foe {who}' if generic else who
            for name in drops:
                add(name, mid, pre + ('drop-later' if later else 'drop'), f'Dropped by {whom}')
            for name in carries:
                if name not in drops:
                    add(name, mid, pre + ('foe-later' if later else 'foe'), f'Carried by {whom}')
        for carries, drops in facts['random']:
            for name in drops:
                add(name, mid, 'dlc-drop', 'Dropped by one of the foes the game picks at random')
            for name in carries:
                if name not in drops:
                    add(name, mid, 'dlc-foe', 'Carried by one of the foes the game picks at random')
        for iid, end, pids in facts['gifts']:
            text = 'Given at the end of the chapter' if end else 'Given in the chapter'
            add(item_name(iid), mid, pre + ('gift-later' if end else 'gift'), text)
        for pid, iids, later in facts['joins']:
            if pid in joined or dlc:
                continue
            joined.add(pid)
            who = unit_name(Source(key), pid)
            who = 'the Avatar' if who == 'Avatar' else who
            for iid in iids:
                add(item_name(iid), mid, 'kit-later' if later else 'kit', f'Carried by {who} when they join')
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
    gm.write_sources(GAME, TITLE, SCRIPT, sources)
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


def encode_grid(m):
    m['grid'] = [''.join(encode(GAME, c) for c in row) for row in m['grid']]
    for c in m.get('changes', []):
        for p in c.get('patch', []):
            p['becomes'] = encode(GAME, p['becomes'])
    return m


if __name__ == '__main__':
    main()
