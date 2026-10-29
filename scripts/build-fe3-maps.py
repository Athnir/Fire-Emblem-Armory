"""
Builds Mystery of the Emblem's maps from the user's clean ROM (scripts/fe3_rom.py), named from the translation patch
(scripts/fe3_names.py):
  src/data/fe3/fe3Terrain.ts      terrain avoid and movement costs, from the game's own tables
  src/data/fe3/fe3Maps.ts         every chapter's map, units, reinforcements, villages, houses, chests, doors, shops, hidden items and
                                  objectives
  src/data/fe3/fe3ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe3-maps.py

The chapters' scripts are played by scripts/fe3_events.py. Formats are in data-raw/fe3/README.md. Coordinates: the game counts rows
and columns from 0 at the top left, and the cursor never goes onto row or column 0 or the last ones ($83:D822 and on), so the playable
map is the stored one without its outer ring; the app counts from (1, 1) at the bottom left.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe3_events as fe  # noqa: E402
import fe3_rom as r  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe3_names import chapter_titles, character_names, class_names, item_names, objectives  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe3', 'Mystery of the Emblem', 'build-fe3-maps.py'
R = r.R
NAMES = character_names()
CLASSES = class_names()
ITEMS = item_names()
MARTH = 0x00

# Terrain id -> (builder letter, name), from the patch's terrain names (162 ids) and how the game treats each.
TERRAIN = {}
for _ids, _letter, _name in [
    ((0, 12), '.', 'Plain'), ((1, 13, 159), 'L', 'Path'), ((2, 14), 'w', 'River'), ((3, 15), 'f', 'Forest'),
    ((4, 16, 23), 'b', 'Bridge'), ((5, 17, 20), 'P', 'Peak'), ((6, 18), 'w', 'Waterfall'), ((7, 19, 161), 'm', 'Mountain'),
    ((8, 95), 'v', 'Village'), ((9, 96), 'B', 'House'), ((10,), 'a', 'Sea'), ((11,), 's', 'Desert'), ((21, 22), 'M', 'Magma'),
    ((24, 47, 97), 'F', 'Fort'), ((26, 27, 28, 29, 30, 32, 33, 145), 'N', 'Castle'), ((25, 46, 100), 'G', 'Castle (no healing)'),
    ((34, 35, 36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 88, 146, 156), 'O', 'Floor'),
    ((37, 40, 43, 49, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 147, 157, 160), 'p', 'Pillar'),
    ((38, 41, 44, 50, 53, 56, 59, 62, 65, 68, 71, 74, 77, 80, 148), 't', 'Throne'),
    ((81, 82, 90, 91, 98, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 151, 152, 155), '#', 'Wall'),
    ((31,), 'Q', 'Floor (Avo +30)'), ((83, 86, 99), 'r', 'Rubble'), ((84, 103, 105, 107, 109, 111, 113, 115, 117, 119, 121, 123, 125, 127, 129, 149), 'c', 'Chest'),
    ((101, 158), 'K', 'Chest'), ((85, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 144, 150), 'O', 'Floor'),
    ((87,), 'd', 'Door'), ((89,), 'Z', 'Drawbridge'), ((92, 93), 'W', 'Stream'), ((94, 102), 'T', 'Tunnel'), ((153,), 'H', 'Shop'),
    ((154,), 'R', 'Arena'),
]:
    for _t in _ids:
        TERRAIN[_t] = (_letter, _name)
assert set(TERRAIN) == set(range(r.TERRAIN_COUNT))

# A class in each movement group (the classes whose cost rows are the same) -> the group's name.
MOVE_NAMES = {
    0x00: 'Lord', 0x01: 'Fighters & bandits', 0x02: 'Soldiers, knights & mercenaries', 0x03: 'Cavaliers & horsemen',
    0x04: 'Paladins', 0x07: 'Armor knights', 0x09: 'Pegasus & dragon knights', 0x0B: 'Hunters', 0x0C: 'Snipers', 0x0D: 'Archers',
    0x0F: 'Manaketes', 0x12: 'Heroes & berserkers', 0x13: 'Thieves & dancers', 0x14: 'Commandos', 0x16: 'Clerics',
    0x17: 'Mages & bishops', 0x1E: 'Pirates', 0x1F: 'Barbarians', 0x23: 'Shooters', 0x26: 'Ice dragons', 0x27: 'Sea dragons',
    0x28: 'Flying dragons', 0x29: 'Earth dragons',
}
SHOP_KINDS = {0: 'Armory', 1: 'Vendor', 2: 'Secret shop'}
HOUSE, SHOP, ARENA, VILLAGE, SEIZE, CHEST, DOOR, BRIDGE, SECRET = 0, 1, 2, 3, 4, 7, 5, 6, 8
# Who is in your army as a chapter starts, for the scripts that ask (IF_PRESENT's mode 0: Chapter 11 brings Palla and Catria only
# when Minerva is with you): everyone the book has had join by then, as it's usually played.
ARMY = set()
LORD = {}  # Marth's record, from the book's first chapter


def world():
    return fe.World(army=set(ARMY))


NUMBER = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'}


def chapters():
    """(chapter number, map index, map id, book, heading): Book 1's chapters 1-20, then Book 2's 1-20, Endgame 1 and Endgame 2's three
    parts (chapter numbers 42-44, each its own map)."""
    out = []
    for n in range(1, r.MAX_CHAPTER + 1):
        book = 1 if n <= 20 else 2
        k = n if book == 1 else n - 20
        if n == 20:
            heading, tail = 'Endgame', 'endgame'
        elif n == 41:
            heading, tail = 'Endgame 1', 'e1'
        elif n > 41:
            heading, tail = 'Endgame 2', f'e2-{n - 41}'
        else:
            heading, tail = f'Ch.{k}', str(k)
        out.append((n, r.chapter_map(n), f'fe3-{book}-{tail}', book, heading))
    return out


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def name_of(n):
    return NAMES.get(n, f'#{n}')


# --- terrain ---

def heal_ids():
    """The terrain ids that heal at the start of a phase: groups 0 (castles, thrones) and 1 (forts) of the table at $88:CB7A, which the
    healing routine ($93:DF10) asks for."""
    groups, cur, a = [], [], 0x88CB7A
    while len(groups) < 2:
        v = r.u8(a)
        a += 1
        if v == 0xFF:
            groups.append(cur)
            cur = []
        else:
            cur.append(v)
    return set(groups[0]) | set(groups[1])


HEALS = heal_ids()


def move_groups():
    groups = {}
    for c in range(r.CLASS_COUNT if hasattr(r, 'CLASS_COUNT') else 0x2D):
        groups.setdefault(bytes(r.move_costs(c)), []).append(c)
    out = []
    for row, classes in groups.items():
        label = next((MOVE_NAMES[c] for c in classes if c in MOVE_NAMES), None)
        assert label, f'no name for the movement row of classes {[CLASSES[c] for c in classes]}'
        out.append((label, classes, row))
    order = list(MOVE_NAMES.values())
    return sorted(out, key=lambda g: order.index(g[0]))


def tile_info(t, groups):
    letter, name = TERRAIN[t]
    move = {label: (None if row[t] == 0xFF else row[t]) for label, _, row in groups}
    e = {'name': name, 'def': 0, 'avo': r.avoid_row(0)[t], 'heal': 0, 'move': move}
    if all(v is None for v in move.values()):
        e['avo'] = 0
    if t in HEALS:
        e['note'] = 'Restores 3 to 9 HP (at random) at the start of each turn.'
    if letter in ('O', 'Q') and move['Cavaliers & horsemen'] is None:
        e['note'] = 'Mounted units and fliers can\'t enter.'
    return letter, e


# --- one chapter ---

class Chapter:
    def __init__(self, n, m):
        self.n, self.m = n, m
        hd = r.map_header(m)
        self.cols, self.rows = hd['cols'], hd['rows']
        self.w, self.h = self.cols - 2, self.rows - 2
        self.ids = r.terrain_ids(m)
        self.table = r.R[r.lo(r.u24(r.TILESET_TERRAIN + 3 * hd['tileset'])):][:0x400]
        self.shops = {}  # (row, column) -> the kind of shop its event opens
        self.tile_infos = []
        self.slots = []

    def app(self, row, col):
        """A game tile (row, column from 0 at the top left) -> the app's [x, y] (from (1, 1) at the bottom left)."""
        return [col, self.h + 1 - row]

    def rect(self, rows, cols):
        return [cols[0], self.h + 1 - rows[1], cols[1], self.h + 1 - rows[0]]

    def inside(self, row, col):
        return 1 <= row <= self.h and 1 <= col <= self.w

    def set_tile(self, row, col, cell):
        self.ids[row][col] = self.table[cell & 0x3FF]


def script_entries(m):
    """Every script a map can run: its turn, area and character events, its tile events and its talks."""
    out = [e['ptr'] for e in r.turn_events(m) + r.area_events(m) + r.char_events(m)]
    out += [r.tile_script(t['id']) for t in r.tile_records(r.TILE_EVENTS) + r.tile_records(r.TILE_OBJECTS) if t['map'] == m]
    out += [t['ptr'] for t in r.talks() if t['map'] == m]
    return out


def placed_units(m):
    """The units a map can actually show: those placed as it loads, and the chapter-list records its scripts load (by character:
    the first record with it) or swap in. (Some list records are never used.)"""
    lst = r.unit_list(r.EVENT_UNITS, m)
    out, mine = list(r.unit_list(r.START_UNITS, m)), set()
    for ptr in script_entries(m):
        cmds = fe.reachable(ptr)
        # A unit a scene loads and takes off again (Book 2's Chapter 1 opening brings on a general for a talk) never stands there.
        gone = {ops[0] for _, c, ops in cmds if c == 0x0B}
        for _, c, ops in cmds:
            char = ops[1] if c in (0x0C, 0x0D) else None
            rec = next((u for u in lst if u['char'] == char), None) if char is not None else None
            if not rec or char in gone:
                continue
            if all(rec is not u for u in out):
                out.append(rec)
            if c == 0x0D or (c == 0x0C and ops[0] == 0):
                mine.add(rec['name'])
    return out, mine


def generic_names():
    """Names three or more of a chapter's units share, unless a unit of that name ever fights on your side: the armies' and bands'
    names ("Galder", "Dolhr"), shown on the map by class; and names that are a class's menu name ("Brserkr", "FireDrg")."""
    from collections import Counter
    from fe3_names import menu_text
    menu_classes = {menu_text(0xF0889C, c) for c in range(0x2D)}
    shared, ours = {n for n, v in NAMES.items() if v in menu_classes}, set()
    for n in range(1, r.MAX_CHAPTER + 1):
        units, mine = placed_units(r.chapter_map(n))
        shared |= {k for k, v in Counter(u['name'] for u in units).items() if v >= 3}
        ours |= mine
    return shared - ours


def book_joiners():
    """{book: the name ids of everyone who joins your army somewhere in it}."""
    out = {1: set(), 2: set()}
    for n in range(1, r.MAX_CHAPTER + 1):
        out[1 if n <= 20 else 2] |= placed_units(r.chapter_map(n))[1]
    return out


GENERIC = generic_names()
JOINERS = book_joiners()


def unit_entry(ch, u, kind, talk=None):
    cls = CLASSES.get(u['class'], '?')
    generic = u['name'] in GENERIC
    lv = f"Lv {u['level']}"
    out = {'type': kind, 'name': cls if generic else name_of(u['name']), 'tile': ch.app(u['row'], u['col']),
           'note': lv if generic else f'{lv} {cls}'}
    items = [item_name(i) for i in u['items']]
    if items:
        out['carries'] = items
    drops = [item_name(i) for i in u['drops']] + ([f"{u['gold']} gold"] if u['gold'] else [])
    if drops and not (talk or '').startswith('Recruit'):
        out['drops'] = drops
    if talk:
        out['talk'] = talk
    return out


def foe_sources(source, map_id, u, entry, later=False):
    """A foe's item slots are what it drops; its weapon slots are only said for a weapon nothing else gives (write_sources)."""
    tail, kind = (', arriving mid-chapter', '-later') if later else ('', '')
    generic = entry['type'] == 'enemy'
    who = f"a foe {entry['name']}" if generic else entry['name']
    for i in u['drops']:
        source(i, map_id, 'drop' + kind, f'Dropped by {who}{tail}')
    for i in u['weapons']:
        if i not in u['drops']:
            source(i, map_id, ('foe' + kind) + ('-generic' if generic else ''),
                   f"Carried by {who}{', a foe' if not generic else ''}{tail}")


def opening_events(ch):
    """The events that run before your first move: turn 0's (the chapter's turn counter starts at 0 while it loads), then turn 1's
    for your phase. $87:9B68 runs the first event that matches the turn and phase."""
    out = []
    for turn in (0, 1):
        e = next((e for e in r.turn_events(ch.m) if e['turn'] == turn and e['phase'] == 0), None)
        if e:
            out.append(e)
    return out


def opening(ch):
    """The units placed as the chapter loads, Marth on the first starting tile, then the opening events. The tiles they change are
    changed on the map."""
    run = fe.Run(ch.m, world())
    for rec in r.unit_list(r.START_UNITS, ch.m):
        run.place(rec, fe.ENEMY)
    starts = r.deploy_tiles(ch.m)
    # Marth by name (Book 2 gives him another character id, 0x81). Only each book's first chapter lists him; after that he comes from
    # your army, onto the first starting tile all the same.
    marth = next((u for u in run.event_list.values() if u['name'] == MARTH), None) or LORD.get('record')
    if marth:
        LORD['record'] = {**marth, 'items': [], 'weapons': [], 'drops': []}
    if marth and starts:
        run.place({**marth, 'row': starts[0][0], 'col': starts[0][1]}, fe.PLAYER)
    for e in opening_events(ch):
        run.run(e['ptr'])
    for t in run.tiles:
        ch.set_tile(t['row'], t['col'], t['tile'])
    return run


def talk_recruit(ch, t):
    """The unit a talk makes yours, if any of its branches does (Minerva joins only once Maria is with you: the talk asks, and its
    other branch is a plain conversation): the record its SWAP loads from the chapter's list."""
    lst = {u['char']: u for u in r.unit_list(r.EVENT_UNITS, ch.m)}
    for _, c, ops in fe.reachable(t['ptr']):
        if c == 0x0D and ops[1] in lst:
            return lst[ops[1]]
    return None


def talks_of(ch):
    """{target name id: 'Recruit: talk with Marth'} from the talk table (a talk whose script makes the target yours recruits), and the
    items the talks give."""
    found, gifts = {}, []
    for t in r.talks():
        if t['map'] != ch.m:
            continue
        run = fe.Run(ch.m, world()).run(t['ptr'])
        e = found.setdefault(t['target'], {'recruit': [], 'talk': []})
        (e['recruit'] if talk_recruit(ch, t) else e['talk']).append(name_of(t['talker']))
        gifts += [(i, t['talker'], t['target']) for i, _ in run.items]
    out = {}
    for target, e in found.items():
        if e['recruit']:
            out[target] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(e['recruit']))
        elif e['talk']:
            out[target] = 'Talk with ' + ' or '.join(dict.fromkeys(e['talk']))
    return out, gifts


def recruit_items(ch):
    """What each talk recruit carries when it joins."""
    out = {}
    for t in r.talks():
        if t['map'] == ch.m and talk_recruit(ch, t):
            out.setdefault(t['target'], talk_recruit(ch, t))
    return out


def boss_names():
    """The game's own list of bosses, by name id ($93:FEB5, checked by the unit loader at $83:DF7D), ended by FF."""
    out, a = set(), 0x93FEB5
    while r.u8(a) != 0xFF:
        out.add(r.u8(a))
        a += 1
    return out


BOSSES = boss_names()


def phase_words(phase):
    return {0: 'your phase', 1: 'enemy phase'}.get(phase, f'phase {phase}')


def arrivals(ch, m, source, talks, carried):
    """The turn events after the opening, the area events and the character events: who they bring in, and when; and the spawn
    slots they fill (the slots spawn a unit at the start of each enemy phase while their count lasts, $87:9DB2)."""
    groups, joiners, n = [], [], 0
    events = []
    first = opening_events(ch)
    for e in r.turn_events(ch.m):
        if e in first:
            continue
        events.append((f"Turn {e['turn']}, {phase_words(e['phase'])}", None, e['ptr']))
    def called(char):
        """A character as these lines name it: its name, or a generic unit's class."""
        u = next((u for u in list(carried) + placed_units(ch.m)[0] if u['char'] == char), None)
        if u is None:
            return 'a unit'
        return f"the {CLASSES.get(u['class'], 'unit')}" if u['name'] in GENERIC else name_of(u['name'])

    for e in r.area_events(ch.m):
        # $87:9C43: FC any of your units (slots below 0x20), FD any enemy, FE anyone, else that character.
        who = {0xFC: 'player', 0xFD: 'enemy', 0xFE: 'player'}.get(e['who'], 'player')
        whose = {0xFC: 'one of your units', 0xFD: 'one of the enemy', 0xFE: 'any unit'}.get(e['who']) or called(e['who'])
        events.append((f'When {whose} enters the marked area', {'who': who, 'rect': ch.rect(e['rows'], e['cols'])}, e['ptr']))
    for e in r.char_events(ch.m):
        events.append((f"Once {called(e['char'])} is defeated", None, e['ptr']))
    slots = {}
    for when, area, ptr in events:
        run = fe.Run(ch.m, world(), units=[dict(u) for u in carried]).run(ptr)
        for k, s in run.slots.items():
            slots.setdefault(k, []).append((when, s))
            ch.slots.append(s)
        foes = [u for u in run.loads if u['side'] == fe.ENEMY]
        friends = [u for u in run.loads if u['side'] == fe.PLAYER]
        if foes:
            n += 1
            g = {'id': f'g{n}', 'label': f'Group {n}', 'when': when,
                 'units': [{**unit_entry(ch, u, 'enemy' if u['name'] in GENERIC else 'named', talks.get(u['name'])),
                            'from': ch.app(*u['start'])} for u in foes]}
            if area:
                g['areas'] = [area]
            groups.append(g)
            for u, entry in zip(foes, g['units']):
                foe_sources(source, m['id'], u, entry, later=True)
        for u in friends:
            j = {'name': name_of(u['name']), 'tile': ch.app(u['row'], u['col']), 'from': ch.app(*u['start']), 'group': f'e{ptr:x}',
                 'when': when}
            if area:
                j['areas'] = [area]
            joiners.append(j)
            for i in u['items']:
                source(i, m['id'], 'kit-later', f"Carried by {name_of(u['name'])} on joining", who=u['char'])
    for k, sets in sorted(slots.items()):
        when, s = sets[0]
        if not s['count']:
            continue
        u = r.reinforcement_unit(s['unit'])
        stops = [w for w, x in sets[1:] if not x['count']]
        start = when[0].lower() + when[1:]
        odds = '' if s['chance'] >= 100 else f" ({s['chance']}% chance each time)"
        if s['count'] == 1:
            text = f"{when}: one arrives at the start of the first enemy phase its tile is free{odds}"
        else:
            text = f"From {start}: one at the start of each enemy phase while the tile is free{odds}, {s['count']} in all"
        if stops:
            text += f"; they stop {stops[0][0].lower() + stops[0][1:]}"
        n += 1
        tile = ch.app(s['row'], s['col'])
        g = {'id': f'g{n}', 'label': f'Group {n}', 'when': text[0].upper() + text[1:],
             'units': [{**unit_entry(ch, {**u, 'row': s['row'], 'col': s['col']}, 'enemy' if u['name'] in GENERIC else 'named'),
                        'from': tile}]}
        groups.append(g)
        foe_sources(source, m['id'], u, g['units'][0], later=True)
    if groups:
        m['reinforcements'] = groups
    if joiners:
        m['joiners'] = joiners


def tile_events(ch):
    return [t for t in r.tile_records(r.TILE_EVENTS) if t['map'] == ch.m]


def tile_objects(ch):
    return [t for t in r.tile_records(r.TILE_OBJECTS) if t['map'] == ch.m]


def words_of(run):
    return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])


def locations(ch, m, source):
    """Houses, villages, shops, secret shops and the seize tile ($8C:917C), chests and doors ($8C:9AD3), hidden items ($8C:9FDE)."""
    seize = None
    for t in tile_events(ch):
        tile = ch.app(t['row'], t['col'])
        if t['kind'] == SEIZE:
            seize = (t['row'], t['col'])
            continue
        if t['kind'] == ARENA:
            continue
        run = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
        if t['kind'] in (SHOP, SECRET):
            shop = next(ops for name, ops in run.calls if isinstance(name, str) is False) if False else None
            for at, c, ops in fe.script(r.tile_script(t['id'])):
                if c == 0x10:
                    shop = ops
            kind = SHOP_KINDS[shop[1]]
            stock = r.shop(shop[0])
            if not stock:
                continue
            m['objects'].append({'type': 'shop', 'tile': tile, 'kind': kind, 'stock': [item_name(i) for i in stock]})
            ch.shops[(t['row'], t['col'])] = kind
            for i in stock:
                source(i, m['id'], 'shop', f'Sold at the {kind.lower()}' + (', with a Member Card' if kind == 'Secret shop' else ''))
            continue
        reward = words_of(run)
        joins = [name_of(u['name']) for u in run.loads if u['side'] == fe.PLAYER]
        if t['kind'] in (VILLAGE, HOUSE):
            if not reward and not joins:
                continue
            o = {'type': 'village', 'tile': tile, 'reward': reward}
            notes = [f"{' and '.join(dict.fromkeys(joins))} {'joins' if len(set(joins)) == 1 else 'join'} your army."] if joins else []
            if t['kind'] == HOUSE:
                notes.append('(A house.)')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i, _ in run.items:
                source(i, m['id'], 'village', 'Given at a village' if t['kind'] == VILLAGE else 'Given at a house')
            for u in run.loads:
                if u['side'] == fe.PLAYER:
                    for i in u['items']:
                        source(i, m['id'], 'kit', f"Carried by {name_of(u['name'])} on joining", who=u['char'])
    for t in tile_objects(ch):
        tile = ch.app(t['row'], t['col'])
        if t['kind'] == CHEST:
            run = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': words_of(run)})
            for i, _ in run.items:
                source(i, m['id'], 'chest', 'In a chest')
        elif t['kind'] == DOOR:
            m['objects'].append({'type': 'door', 'tile': tile})
    a = 0x8C9FDE
    while r.u8(a) != 0xFF:
        mp, col, row, _cond, it = (r.u8(a + k) for k in range(5))
        if mp == ch.m:
            tile = ch.app(row, col)
            # Found from the tile or one beside it ($83:9D95): a thief always, anyone else a Luck% chance each time.
            m['objects'].append({'type': 'hidden', 'tile': tile, 'area': tile + tile, 'contents': item_name(it),
                                 'note': 'Found by a unit that waits on this tile or one next to it (not diagonally): a thief '
                                         'always finds it, anyone else has a Luck% chance.'})
            source(it, m['id'], 'hidden', 'Hidden on the map')
        a += 7
    return seize


ENDGAME_NOTE = ('Opens if your army holds the Binding Shield when Marth seizes the throne in Chapter 20; without it, the game ends '
                'there.')


def main():
    titles, goals = chapter_titles(), objectives()
    groups = move_groups()
    maps, sources, used, variants = [], {}, {}, {}
    joined = set()
    state = {'joining': {}}

    def source(item, map_id, kind, words, who=None):
        if who is not None:
            if who in joined:
                return
            if state['joining'].setdefault(who, (kind, words)) != (kind, words):
                return
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    for n, mi, map_id, book, heading in chapters():
        if n == 21:
            joined.clear()  # Book 2 starts the army afresh
            ARMY.clear()
            LORD.clear()
        state['joining'] = {}
        ch = Chapter(n, mi)
        run = opening(ch)
        talks, gifts = talks_of(ch)
        recruits = recruit_items(ch)
        rows = [[ch.ids[y][x] for x in range(1, ch.cols - 1)] for y in range(1, ch.rows - 1)]
        m = {
            'id': map_id, 'route': 'Story', 'heading': f'Book {book}, {heading}', 'chapter': n if book == 1 else n - 20,
            'title': titles[n][1], 'width': ch.w, 'height': ch.h, 'grid': [],
            'victory': goals[n], 'defeat': 'Marth is defeated', 'objectives': [], 'units': [], 'starts': [], 'objects': [],
            'changes': [], 'notes': [], 'lord': 'Marth',
        }
        seize = locations(ch, m, source)
        for i, a, b in gifts:
            source(i, map_id, 'talk', f'{name_of(a)} talks to {name_of(b)}')
        # Your army's starting tiles; Marth's is the first, and the opening may walk him from it.
        m['starts'] = [ch.app(*t) for t in r.deploy_tiles(mi) if ch.inside(*t)]
        foes = [u for u in run.units if u['side'] == fe.ENEMY]
        # The game's boss list is by name, for both books: a talk recruit on it is this chapter's boss only when no one else on the list
        # is (Sheena in Book 2's Chapter 17 is; Lorenz, Book 2's first boss, isn't in Book 1's Chapter 16, where Camus is).
        listed = {u['name'] for u in foes if u['name'] in BOSSES}
        plain = {n for n in listed if not (talks.get(n) or '').startswith('Recruit')}
        bosses = plain or listed
        forced = []
        for u in run.units:
            if u['side'] == fe.PLAYER:
                if u['name'] == MARTH:
                    m['corrinStart'] = ch.app(u['row'], u['col'])
                    if n in (1, 21):
                        for i in u['items']:
                            source(i, map_id, 'kit', 'Carried by Marth from the start', who=u['char'])
                else:
                    forced.append({'name': name_of(u['name']), 'tile': ch.app(u['row'], u['col'])})
                    for i in u['items']:
                        source(i, map_id, 'kit', f"Carried by {name_of(u['name'])} on joining", who=u['char'])
                continue
            kind = 'boss' if u['name'] in bosses else 'enemy' if u['name'] in GENERIC else 'named'
            e = unit_entry(ch, u, kind, talks.get(u['name']))
            m['units'].append(e)
            if (e.get('talk') or '').startswith('Recruit'):
                joiner = recruits.get(u['name'], u)
                for i in joiner['items']:
                    source(i, map_id, 'kit', f"Carried by {e['name']} on joining", who=joiner['char'])
            else:
                foe_sources(source, map_id, u, e)
        if forced:
            m['forced'] = forced
        if m.get('corrinStart') and m['starts'] and m['corrinStart'] not in m['starts']:
            # The opening walks Marth off his starting tile (Chapter 1 of each book): he starts where it leaves him.
            m['starts'][0] = m['corrinStart']
        arrivals(ch, m, source, talks, run.units)
        if seize:
            what = 'throne' if 'throne' in goals[n] else 'castle'
            m['objectives'].append({'type': 'seize', 'tiles': [ch.app(*seize)], 'label': f'Seize the {what} with Marth'})
        # The end of the chapter: what the seize scene gives.
        for t in tile_events(ch):
            if t['kind'] == SEIZE:
                end = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
                for i, who in end.items:
                    source(i, map_id, 'event', 'Given at the end of the chapter')
        if n == 41:
            m['notes'].append(ENDGAME_NOTE)
        if n == 6:
            # $83:B96E: in this chapter an attack on Minerva, Palla, Catria or Est always misses.
            m['notes'].append("Minerva, Palla, Catria and Est can't be hit in this chapter: every attack on them misses.")
        # Terrain: each id's code; per-map overrides where a map's tile works differently from the game-wide one.
        codes = []
        for y, row in enumerate(rows, 1):
            line = []
            for x, t in enumerate(row, 1):
                letter, info = tile_info(t, groups)
                kind = ch.shops.get((y, x))
                if letter == 'H' and kind in ('Armory', 'Vendor'):
                    # One shop tile for both: drawn as the shop its event opens.
                    letter, info = ('A' if kind == 'Armory' else 'V'), {**info, 'name': kind}
                code = encode(GAME, letter)
                line.append(code)
                ch.tile_infos.append((letter, info))
                variants.setdefault(code, {}).setdefault(repr(info), [info, set()])[1].add(map_id)
            codes.append(''.join(line))
        m['grid'] = codes
        used[map_id] = {}
        for letter, info in ch.tile_infos:
            code = encode(GAME, letter)
            old = used[map_id].setdefault(code, info)
            if old != info:
                # Two variants of one code on a map: they may differ only for movement groups none of its units belong to (Book 1's
                # Chapter 8: its two pillars differ for Ice and Sea Dragons alone).
                diff = {k for k in info['move'] if info['move'][k] != old['move'][k]}
                assert {k: v for k, v in info.items() if k != 'move'} == {k: v for k, v in old.items() if k != 'move'}, (map_id, code)
                classes = {u['class'] for u in run.units} | {r.reinforcement_unit(s['unit'])['class'] for s in ch.slots}
                present = {label for label, members, _ in groups if set(members) & classes}
                assert not diff & present, (map_id, code, diff & present)
        maps.append(m)
        joined |= set(state['joining'])
        ARMY.update(u['char'] for u in run.units if u['side'] == fe.PLAYER)
        ARMY.update(rec['char'] for rec in recruits.values())
        ARMY.update(state['joining'])
        print(map_id, m['title'], f'{ch.w}x{ch.h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    # The game-wide terrain table: each code's most common variant; a map using another gets it as an override.
    info = {}
    for code, vs in variants.items():
        best = max(vs.values(), key=lambda v: len(v[1]))
        info[code] = best[0]
    for m in maps:
        over = {}
        for code, e in used[m['id']].items():
            if e != info[code]:
                diff = {k: v for k, v in e.items() if v != info[code].get(k)}
                over[code] = diff
        # A map with two variants of one code: they must differ only where its units never go (checked by hand: Chapter 8's
        # pillars differ for Ice and Sea Dragons alone).
        if over:
            m['terrainOverrides'] = over
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
