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
import fe3_ai as ai  # noqa: E402
import fe3_events as fe  # noqa: E402
import fe3_rom as r  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe3_names import chapter_titles, character_names, class_names, item_names, menu_text, objectives  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe3', 'Mystery of the Emblem', 'build-fe3-maps.py'
R = r.R
NAMES = character_names()
CLASSES = class_names()
ITEMS = item_names()
MARTH = 0x00

# Terrain id -> (builder letter, what it is), by how the game treats each (its avoid and cost tables, the healing groups); the names the
# maps show are the game's own (terrain_name).
TERRAIN = {}
for _ids, _letter, _name in [
    ((0, 12), '.', 'Plain'), ((1, 13, 159), 'L', 'Path'), ((2, 14), 'w', 'River'), ((3, 15), 'f', 'Forest'),
    ((4, 16, 23), 'b', 'Bridge'), ((5, 17, 20), 'P', 'Peak'), ((6, 18), 'w', 'Waterfall'), ((7, 19, 161), 'm', 'Mountain'),
    ((8, 95), 'v', 'Village'), ((9, 96), 'B', 'House'), ((10,), 'a', 'Sea'), ((11,), 's', 'Desert'), ((21, 22), 'M', 'Magma'),
    ((24, 47, 97), 'F', 'Fort'), ((26, 27, 28, 29, 30, 32, 33, 145), 'N', 'Castle'),
    # A castle gate's flanks: no healing; Book 2's Chapters 12 and 13 give theirs Avo 30.
    ((25,), 'G', 'Castle (no healing)'), ((46, 100), 'g', 'Castle (Avo +30, no healing)'),
    # Floors: two open to every unit, the rest closed to mounted units (cavaliers, paladins, pegasus and dragon knights), some with
    # Avo 30 (the floor an opened chest leaves: its window says Recover, but it doesn't heal).
    ((34, 35), 'o', 'Floor'),
    ((36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72, 75, 78, 88, 146, 156), 'O', 'Floor (no mounts)'),
    ((31, 85, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 144, 150), 'Q', 'Floor (Avo +30, no mounts)'),
    ((37, 40, 43, 49, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 147), 'p', 'Pillar'),
    # Book 1's Chapter 8's pillars: Avo 30, and mounted units cross them.
    ((157, 160), 'J', 'Pillar (Avo +30)'),
    ((38, 41, 44, 50, 53, 56, 59, 62, 65, 68, 71, 74, 77, 80, 148), 't', 'Throne'),
    ((81, 82, 90, 91, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 151, 152), '#', 'Wall'),
    # No unit moves onto an altar, but the game places units there (the Endgame's Earth Dragons, and the spawns that bring more): it
    # keeps its stats, under the summoning sigil's code.
    ((98, 155), 'Y', 'Altar'),
    ((83, 86, 99), 'r', 'Rubble'), ((84, 103, 105, 107, 109, 111, 113, 115, 117, 119, 121, 123, 125, 127, 129, 149), 'c', 'Chest'),
    ((101, 158), 'K', 'Chest'),
    ((87,), 'd', 'Door'), ((89,), 'Z', 'Drawbridge'), ((92, 93), 'W', 'Stream'), ((94, 102), 'T', 'Tunnel'), ((153,), 'H', 'Shop'),
    ((154,), 'R', 'Arena'),
]:
    for _t in _ids:
        TERRAIN[_t] = (_letter, _name)
assert set(TERRAIN) == set(range(r.TERRAIN_COUNT))
# The terrain window's names fit in seven letters: the four it shortens, in full.
CUT = {'Corridr': 'Corridor', 'Drawbrg': 'Drawbridge', 'Waterfl': 'Waterfall', 'Mount': 'Mountain'}


def terrain_name(t):
    """The game's name for a terrain id: the first line of its terrain window (the patch's table at $F0:B08E), cut-offs in full."""
    word = menu_text(0xF0B08E, t).split(' ')[0]
    return CUT.get(word, word)

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
    letter, _ = TERRAIN[t]
    move = {label: (None if row[t] == 0xFF else row[t]) for label, _, row in groups}
    e = {'name': terrain_name(t), 'def': 0, 'avo': r.avoid_row(0)[t], 'heal': 0, 'move': move}
    if all(v is None for v in move.values()) and letter != 'Y':
        e['avo'] = 0
    if t in HEALS:
        e['note'] = 'Restores 3 to 9 HP (at random) at the start of each turn.'
    if letter in ('O', 'Q', 'p', 't') and move['Cavaliers & horsemen'] is None:
        assert move['Pegasus & dragon knights'] is None and move['Flying dragons'] is not None, t
        e['note'] = ((e['note'] + ' ') if e.get('note') else '') + 'No mounted units: pegasus and dragon knights can\'t enter either.'
    return letter, e


# A closed room under its roof (the cells a door's or a script's map change lifts): no unit can enter it, fliers included.
ROOF = {'name': 'Roof (closed room)', 'def': 0, 'avo': 0, 'heal': 0,
        'note': "A room under its roof: no unit can enter it, fliers included, until a door into it opens or the chapter's script "
                'lifts its roof.'}


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
        self.patched = {}  # (row, column) -> the terrain ids the chapter's changes can put there

    def app(self, row, col):
        """A game tile (row, column from 0 at the top left) -> the app's [x, y] (from (1, 1) at the bottom left)."""
        return [col, self.h + 1 - row]

    def rect(self, rows, cols):
        """An area's rows and columns as the app's [x1, y1, x2, y2], held to the playable grid (some reach into the border)."""
        return [max(cols[0], 1), self.h + 1 - min(rows[1], self.h), min(cols[1], self.w), self.h + 1 - max(rows[0], 1)]

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
    kinds = {r.item(i)['type'] for i in u['weapons']}
    out['_ai'] = {'ai': tuple(u['ai']), 'char': u['char'], 'name': u['name'], 'class': u['class'], 'here': (u['row'], u['col']),
                  'armed': bool(kinds - {'Staff', 'Item'}), 'staff': 'Staff' in kinds, 'placed_by': None}
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


def opening(ch, w=None, dry=False):
    """The units placed as the chapter loads, Marth on the first starting tile, then the opening events. The tiles they change are
    changed on the map (not on a dry run, which only places)."""
    run = fe.Run(ch.m, w or world())
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
    if not dry:
        for t in run.tiles:
            ch.set_tile(t['row'], t['col'], t['tile'])
    return run


def talk_recruit(ch, t):
    """The unit a talk makes yours, if any of its branches does (Minerva joins only once Maria is with you: the talk asks, and its
    other branch is a plain conversation): (the record its SWAP loads from the chapter's list, the name id of the unit it takes off),
    or None. The unit taken off is the talk's target, or its talker where the foe starts the talk (Book 1's Chapter 11: Catria and
    Palla talk to Marth); the record loaded may be another person (Book 2's Chapter 6: "Navarre" is Samuel)."""
    lst = {u['char']: u for u in r.unit_list(r.EVENT_UNITS, ch.m)}
    on_map = {}
    for u in placed_units(ch.m)[0]:
        on_map.setdefault(u['char'], u['name'])  # the unit placed first is the one on the map (the list's record may be another)
    for _, c, ops in fe.reachable(t['ptr']):
        if c == 0x0D and ops[1] in lst:
            return lst[ops[1]], on_map.get(ops[2], t['target'])
    return None


def talks_of(ch):
    """{name id: 'Recruit: talk with Marth'} from the talk table, for the unit a talk makes yours (keyed by who it takes off: the
    target, or the talker where the foe starts it: 'Recruit: talks to Marth'), and the items the talks give."""
    found, gifts = {}, []
    for t in r.talks():
        if t['map'] != ch.m:
            continue
        run = fe.Run(ch.m, world()).run(t['ptr'])
        got = talk_recruit(ch, t)
        # What the talk asks first (its condition: Minerva's waits for Maria to join, Sheena's until a Gra soldier falls).
        cond = (condition_words(ch.n, condition(t['flag']), own=('talk', (name_of(t['talker']), name_of(t['target']))))
                if conditional(t['flag']) else '')
        if got and got[1] == t['talker'] and t['talker'] != t['target']:
            found.setdefault(t['talker'], {'recruit': [], 'talk': [], 'starts': [], 'cond': []})['starts'].append(name_of(t['target']))
            found[t['talker']]['cond'].append(cond)
        else:
            e = found.setdefault(t['target'], {'recruit': [], 'talk': [], 'starts': [], 'cond': []})
            (e['recruit'] if got else e['talk']).append(name_of(t['talker']))
            e['cond'].append(cond)
        gifts += [(i, t['talker'], t['target']) for i, _ in run.items]
    out = {}
    for who, e in found.items():
        conds = [c for c in dict.fromkeys(e['cond']) if c]
        tail = f", {conds[0]}" if len(conds) == 1 else ''
        if e['starts']:
            out[who] = 'Recruit: talks to ' + ' or '.join(dict.fromkeys(e['starts'])) + tail
        elif e['recruit']:
            out[who] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(e['recruit'])) + tail
        elif e['talk']:
            out[who] = 'Talk with ' + ' or '.join(dict.fromkeys(e['talk'])) + tail
    return out, gifts


def recruit_items(ch):
    """{name id of the unit a talk takes off: the record that joins in its place}."""
    out = {}
    for t in r.talks():
        got = talk_recruit(ch, t) if t['map'] == ch.m else None
        if got:
            out.setdefault(got[1], got[0])
    return out


CONDITIONS = 0x8CA04F  # a long pointer per condition number ($87:AAA7)


def conditional(n):
    """A record's condition byte names a condition: 0 is an empty one and FF none at all ($83:E53F skips the check)."""
    return n not in (0, 0xFF)


def condition(n):
    """Condition n: [(type, value)] (type 0 the acting unit holds the item, 1 the flag is clear (a u16), 2 the character is on the map,
    3 it's in your army and alive, 4 your army holds the item, 5 the chapter is at least the number), ended by FF."""
    a, out = r.u24(CONDITIONS + 3 * n), []
    while r.u8(a) != 0xFF:
        t = r.u8(a)
        out.append((t, r.u16(a + 1) if t == 1 else r.u8(a + 1)))
        a += 3 if t == 1 else 2
    return out


def chapter_label(n):
    return f'Chapter {n if n <= 20 else n - 20}'


def script_sources(n):
    """[(trigger kind, words, script, character or talk)] for every script a chapter can run but its seize."""
    m = r.chapter_map(n)
    units = placed_units(m)[0]

    def called(char):
        u = next((u for u in units if u['char'] == char), None)
        if u is None:
            return None
        return (CLASSES.get(u['class'], 'unit'), True) if u['name'] in GENERIC else (name_of(u['name']), False)
    out = []
    for e in r.turn_events(m):
        out.append(('turn', e, e['ptr'], None))
    for e in r.char_events(m):
        out.append(('death', called(e['char']), e['ptr'], e['char']))
    for t in r.talks():
        if t['map'] == m:
            out.append(('talk', (name_of(t['talker']), name_of(t['target'])), t['ptr'], t))
    for e in r.area_events(m):
        out.append(('area', e, e['ptr'], None))
    for t in r.tile_records(r.TILE_EVENTS) + r.tile_records(r.TILE_OBJECTS):
        if t['map'] == m and t['id'] != 0xFFFF and t['kind'] != SEIZE:
            out.append(('tile', t, r.tile_script(t['id']), None))
    return out


def flag_setters():
    """{flag: [(chapter, kind, words)]} for every script that sets it (SET_FLAG, 0x11), and {(chapter, flag): [...]} for those that
    clear it."""
    sets, clears = {}, {}
    for n in range(1, r.MAX_CHAPTER + 1):
        for kind, words, ptr, _ in script_sources(n):
            for _, c, ops in fe.reachable(ptr):
                f = ops[0] | ops[1] << 8 if c in (0x11, 0x12) else None
                if c == 0x11:
                    sets.setdefault(f, []).append((n, kind, words))
                elif c == 0x12:
                    clears.setdefault((n, f), []).append((kind, words))
    return sets, clears


def plural(word):
    if word.endswith('man'):
        return word[:-3] + 'men'
    return word + ('es' if word.endswith(('s', 'sh', 'ch')) else 's')


def deaths_words(whos):
    """'Samson', 'a Gra Soldier or Samson': who a set of deaths names (generic foes by class)."""
    named = list(dict.fromkeys(w for w, generic in whos if not generic))
    generic = list(dict.fromkeys(w for w, g in whos if g))
    parts = named + ([f"any {' or '.join(generic)}"] if generic else [])
    return ' or '.join(parts) if parts else 'a unit'


def flag_words(f, n, own=None):
    """What a flag that a condition wants clear means in chapter n: 'once Marth has talked to Maria' (set by the opening, cleared by
    a talk), 'until Samson is defeated' (set by deaths), or None (the talk's own once-only flag, or a flag nothing sets)."""
    hits = [(k, kind, words) for k, kind, words in FLAG_SETS.get(f, []) if k == n]
    sets_here = [(kind, words) for _, kind, words in hits if (kind, words) != own]
    deaths = [words for kind, words in sets_here if kind == 'death' and words]
    if deaths:
        return f'until {deaths_words(deaths)} is defeated'
    if any(kind == 'turn' and words['turn'] in (0, 1) for kind, words in sets_here):
        cleared = FLAG_CLEARS.get((n, f), [])
        talks = [words for kind, words in cleared if kind == 'talk']
        if talks:
            return 'once ' + ' or '.join(f'{a} has talked to {b}' for a, b in dict.fromkeys(talks))
        deaths = [words for kind, words in cleared if kind == 'death' and words]
        if deaths:
            return f'once {deaths_words(deaths)} is defeated'
    return None


def condition_words(n, cond, own=None):
    """A condition's requirements in words ('with Minerva in your army, once Marth has talked to Maria'); flags it can't name are
    left out."""
    m = r.chapter_map(n)
    units = placed_units(m)[0]

    def who(char):
        u = next((u for u in units if u['char'] == char), None)
        return name_of(u['name']) if u else (name_of(char) if char in NAMES else 'a unit')
    out = []
    held = [item_name(v) for t, v in cond if t in (0, 4)]
    for t, v in cond:
        if t == 2:
            out.append(f'while {who(v)} is on the map')
        elif t == 3:
            out.append(f'with {who(v)} in your army')
        elif t == 1:
            w = flag_words(v, n, own)
            if w:
                out.append(w)
        elif t == 5:
            out.append(f'from chapter {v} on')
    if held:
        out.append(('for a unit holding the ' if any(t == 0 for t, _ in cond) else 'if your army holds the ') + or_words(held))
    out = [w for w in out if not (w.startswith('while ') and any(w[6:-14] in x for x in out if x.startswith('once ')))]
    return ', '.join(out)


def boss_names():
    """The game's own list of bosses, by name id ($93:FEB5, checked by the unit loader at $83:DF7D), ended by FF."""
    out, a = set(), 0x93FEB5
    while r.u8(a) != 0xFF:
        out.add(r.u8(a))
        a += 1
    return out


BOSSES = boss_names()
FLAG_SETS, FLAG_CLEARS = {}, {}


def phase_words(phase):
    return {0: 'your phase', 1: 'enemy phase'}.get(phase, f'phase {phase}')


def arrivals(ch, m, source, talks, carried):
    """The turn events after the opening, the area events and the character events: who they bring in, and when; and the spawn
    slots they fill (the slots spawn a unit at the start of each enemy phase while their count lasts, $87:9DB2). What one event brings
    at once is one group, and so are the slots one event fills alike (the same count, odds and stop): Book 1's Chapter 8's turn 15
    fills eight. An area event runs as soon as a unit stops in its area ($87:9C43), and its groups show the area."""
    groups, joiners, n = [], [], 0
    events = []
    first = opening_events(ch)
    for e in r.turn_events(ch.m):
        if e in first:
            continue
        phase = phase_words(e['phase'])
        events.append({'when': f"Turn {e['turn']}, {phase}", 'since': f"From turn {e['turn']}'s {phase}",
                       'stop': f"at the {phase} on turn {e['turn']}", 'area': None, 'ptr': e['ptr']})
    for e in r.area_events(ch.m):
        # FC any of your units (slots below 0x20), FD any enemy, FE anyone, else that character.
        who = 'enemy' if e['who'] == 0xFD else 'player'
        trigger = f"{whose(ch, e['who'], carried)} stops in the marked area"
        events.append({'when': f'As soon as {trigger}', 'since': f'Once {trigger}', 'stop': f'once {trigger}',
                       'area': {'who': who, 'rect': ch.rect(e['rows'], e['cols'])}, 'ptr': e['ptr']})
    for e in r.char_events(ch.m):
        trigger = f"{whose(ch, e['char'], carried)} is defeated"
        events.append({'when': f'Once {trigger}', 'since': f'Once {trigger}', 'stop': f'once {trigger}', 'area': None, 'ptr': e['ptr']})
    slots = {}
    for ev in events:
        when, area, ptr = ev['when'], ev['area'], ev['ptr']
        run = fe.Run(ch.m, world(), units=[dict(u) for u in carried]).run(ptr)
        for k, s in run.slots.items():
            slots.setdefault(k, []).append((ev, s))
            ch.slots.append(s)
        # A scene's cast (Book 2's Chapter 1 brings Ogma and Catria on for a talk; Chapter 14's "Lena" records are Gotoh's scene): what
        # the event loads and takes off again never stands on the map.
        gone = {id(u) for u in run.removed}
        foes = [u for u in run.loads if u['side'] == fe.ENEMY and id(u) not in gone]
        friends = [u for u in run.loads if u['side'] == fe.PLAYER and id(u) not in gone]
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
                entry['_ai']['placed_by'] = ptr  # the event that brings it: its AI is already that event's
        for u in friends:
            j = {'name': name_of(u['name']), 'tile': ch.app(u['row'], u['col']), 'from': ch.app(*u['start']), 'group': f'e{ptr:x}',
                 'when': when}
            if area:
                j['areas'] = [area]
            joiners.append(j)
            for i in u['items']:
                source(i, m['id'], 'kit-later', f"Carried by {name_of(u['name'])} on joining", who=u['char'])
    # The slots one event fills alike are one group (the first event to fill a slot; a later one that empties it stops it).
    alike = {}
    for k, sets in sorted(slots.items()):
        ev, s = sets[0]
        if not s['count']:
            continue
        stops = [x['stop'] for x, y in sets[1:] if not y['count']]
        key = (ev['ptr'], s['count'], s['chance'], stops[0] if stops else '')
        alike.setdefault(key, {'event': ev, 'slots': []})['slots'].append(s)
    for (_, count, chance, stop), v in alike.items():
        ev, members = v['event'], v['slots']
        many = len(members) > 1
        odds = '' if chance >= 100 else f' ({chance}% chance each time)'
        if count == 1:
            text = (f"{ev['since']}, one arrives {'on each tile ' if many else ''}at the start of the first enemy phase "
                    f"{'it' if many else 'its tile'} is free{odds}")
        else:
            text = (f"{ev['since']}, one {'on each tile ' if many else ''}at the start of each enemy phase while "
                    f"{'it' if many else 'the tile'} is free{odds}, {count}{' on each' if many else ''} in all")
        if stop:
            text += f'; they stop {stop}'
        n += 1
        g = {'id': f'g{n}', 'label': f'Group {n}', 'when': text, 'units': []}
        for s in members:
            u = r.reinforcement_unit(s['unit'])
            entry = {**unit_entry(ch, {**u, 'row': s['row'], 'col': s['col']}, 'enemy' if u['name'] in GENERIC else 'named'),
                     'from': ch.app(s['row'], s['col'])}
            g['units'].append(entry)
            foe_sources(source, m['id'], u, entry, later=True)
        if ev['area']:
            g['areas'] = [ev['area']]
        groups.append(g)
    if groups:
        m['reinforcements'] = groups
    if joiners:
        m['joiners'] = joiners


def whose(ch, who, carried=()):
    """An area event's who byte ($87:9C43): FC any of your units, FD a foe, FE anyone, else that character."""
    if who in (0xFC, 0xFD, 0xFE):
        return {0xFC: 'one of your units', 0xFD: 'a foe', 0xFE: 'any unit'}[who]
    u = next((u for u in list(carried) + placed_units(ch.m)[0] if u['char'] == who), None)
    if u is None:
        return 'a unit'
    return f"the {CLASSES.get(u['class'], 'unit')}" if u['name'] in GENERIC else name_of(u['name'])


def area_where(ch, e):
    """An area event's tiles in words: 'on (3, 12)', 'in the area from (10, 1) to (24, 8)'."""
    (c1, c2), (r1, r2) = e['cols'], e['rows']
    x1, y1 = ch.app(min(r2, ch.h), max(c1, 1))
    x2, y2 = ch.app(max(r1, 1), min(c2, ch.w))
    return f'on ({x1}, {y1})' if (x1, y1) == (x2, y2) else f'in the area from ({x1}, {y1}) to ({x2}, {y2})'


def walkable(t):
    """A terrain id some class can enter."""
    return any(r.move_costs(c)[t] != 0xFF for c in range(0x2D))


def or_words(words):
    words = list(dict.fromkeys(words))
    return words[0] if len(words) == 1 else ', '.join(words[:-1]) + ' and ' + words[-1]


def changes_of(ch, m, carried):
    """What reshapes the map after the opening, each with what sets it off: doors and drawbridges (TILE_OBJECTS kind 5 and 6: opening
    one writes the record's +8 metatile onto its tile, $83:C8C5, then runs its script; a Thief of either army opens them, $83:E776 /
    $83:E626, as does a unit holding a Door Key or a Bridge Key, $83:ED91 / $83:E64F), chests whose script changes the map, villages
    that close another (SET_TILE), and the area, turn, character and talk events' SET_TILE and SHOW. A seize tile's script runs as the
    chapter ends, so its changes are no battle's. Returns ([change], {game tile} of closed rooms: tiles no unit can enter that a change
    makes walkable)."""
    start = {(y, x): ch.ids[y][x] for y in range(ch.rows) for x in range(ch.cols)}

    roofed = set()

    def after(writes):
        out = {}
        for w in writes:
            out[(w['row'], w['col'])] = ch.table[w['tile'] & 0x3FF]
        patch = {k: t for k, t in out.items() if t != start.get(k) and ch.inside(*k)}
        for k, t in patch.items():
            ch.patched.setdefault(k, set()).add(t)
        # A tile no unit can enter (not a door) that the change makes walkable is a closed room's; its walls stay walls.
        roofed.update(k for k, t in patch.items() if not walkable(start[k]) and walkable(t) and TERRAIN[start[k]][0] != 'd')
        return patch

    def what(patch):
        doors = [k for k, t in patch.items() if TERRAIN[start[k]][0] == 'd' and walkable(t)]
        roofs = [k for k, t in patch.items() if not walkable(start[k]) and walkable(t) and TERRAIN[start[k]][0] != 'd']
        if doors:
            at = or_words(['({}, {})'.format(*ch.app(*k)) for k in doors])
            return f"the door{'s' if len(doors) > 1 else ''} at {at} open{'' if len(doors) > 1 else 's'}" + (
                ', with the closed room behind it' if roofs else '')
        if roofs:
            return 'the closed room opens' if len(patch) > 1 else 'the wall opens'
        if any(TERRAIN[t][0] == 'd' for t in patch.values()):
            return 'a door shuts' + (' here' if len(patch) == 1 else '')
        if any(TERRAIN[start[k]][0] == 'v' and not walkable(t) for k, t in patch.items()):
            return 'the village closes'
        return 'the tiles change'

    def entry(cid, tile, effect, patch, wide=False):
        e = {'id': cid, 'trigger': 'event', 'tile': {'default': ch.app(*tile)}, 'usableBy': '', 'effect': effect,
             'patch': [{'tile': ch.app(*k), 'becomes': encode(GAME, TERRAIN[t][0])} for k, t in sorted(patch.items())]}
        if wide:
            e['wide'] = True
        return e

    changes, opened = [], set()
    ch.patched = {}
    for t in tile_objects(ch):
        if t['kind'] not in (DOOR, BRIDGE, CHEST):
            continue
        run = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
        writes = ([] if t['kind'] == CHEST or t['extra'] == 0xFFFF else [{'row': t['row'], 'col': t['col'], 'tile': t['extra']}])
        patch = after(writes + run.tiles)
        if not patch:
            continue
        opened |= set(patch)
        X, Y = ch.app(t['row'], t['col'])
        rooms = any(not walkable(start[k]) and walkable(v) and k != (t['row'], t['col']) for k, v in patch.items())
        if t['kind'] == DOOR:
            effect = ('A door: a Thief of either army, or a unit holding a Door Key, opens it' +
                      (', and the closed room behind it opens' if rooms else '') + '.')
            changes.append(entry(f'door-{X}-{Y}', (t['row'], t['col']), effect, patch))
        elif t['kind'] == BRIDGE:
            effect = ('A drawbridge: a Thief of either army, or a unit holding a Bridge Key, lowers it' +
                      (', with the rest of its bridge' if len(patch) > 1 else '') + '.')
            changes.append(entry(f'bridge-{X}-{Y}', (t['row'], t['col']), effect, patch))
        else:
            changes.append(entry(f'chest-{X}-{Y}', (t['row'], t['col']),
                                 'Opening this chest also opens the closed rooms beyond its walls.', patch))
    for t in tile_events(ch):
        if t['kind'] not in (VILLAGE, HOUSE):
            continue
        run = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
        patch = after(run.tiles)
        if patch:
            X, Y = ch.app(t['row'], t['col'])
            others = [ch.app(*k) for k in patch if k != (t['row'], t['col'])]
            changes.append(entry(f'visit-{X}-{Y}', (t['row'], t['col']),
                                 'Visiting this village closes the one at ' + or_words([f'({x}, {y})' for x, y in others]) + '.', patch))
            opened |= set(patch)
    # The events: a turn's (after the opening), an area's, a death's, a talk's.
    first = opening_events(ch)
    turned = {}
    for e in r.turn_events(ch.m):
        if e in first:
            continue
        run = fe.Run(ch.m, world()).run(e['ptr'])
        patch = after(run.tiles)
        if not patch:
            continue
        unless = any(w['flags'] == 0 for w in run.tiles)
        if all(TERRAIN[t][0] == 'd' for t in patch.values()):
            # Doors a turn shuts (the Book 1 Endgame's): one change per door, with every turn that shuts it.
            for k, t in patch.items():
                turned.setdefault(((k, t),), {'phase': e['phase'], 'unless': unless, 'turns': []})['turns'].append(e['turn'])
        else:
            turned.setdefault(tuple(sorted(patch.items())), {'phase': e['phase'], 'unless': unless, 'turns': []})['turns'].append(e['turn'])
    for items, v in turned.items():
        patch = dict(items)
        opened |= set(patch)
        ts = sorted(set(v['turns']))
        when = f"At the start of the {phase_words(v['phase'])} on turn{'s' if len(ts) > 1 else ''} {or_words([str(t) for t in ts])}"
        tile = sorted(patch)[0]
        X, Y = ch.app(*tile)
        if len(patch) == 1 and TERRAIN[patch[tile]][0] == 'd':
            effect = (f'{when}, this door shuts' + (' unless a unit stands on it' if v['unless'] else '') +
                      '; a Thief of either army, or a unit holding a Door Key, opens it again.')
        else:
            effect = f'{when}, {what(patch)}' + (' (not under a unit)' if v['unless'] else '') + '.'
        changes.append(entry(f'turn-{X}-{Y}', tile, effect, patch, wide=len(patch) > 1))
    events = []
    for e in r.area_events(ch.m):
        events.append((f"When {whose(ch, e['who'], carried)} stops {area_where(ch, e)}", e['ptr']))
    for e in r.char_events(ch.m):
        events.append((f"Once {whose(ch, e['char'], carried)} is defeated", e['ptr']))
    for t in r.talks():
        if t['map'] == ch.m:
            events.append((f"When {name_of(t['talker'])} talks to {name_of(t['target'])}", t['ptr']))
    for when, ptr in events:
        run = fe.Run(ch.m, world(), units=[dict(u) for u in carried]).run(ptr)
        patch = after(run.tiles)
        if not patch:
            continue
        opened |= set(patch)
        tile = sorted(patch)[0]
        X, Y = ch.app(*tile)
        changes.append(entry(f'event-{ptr:x}', tile, f'{when}, {what(patch)}.', patch, wide=len(patch) > 1))
    return changes, {k for k in opened if k in roofed}


# --- what the foes' AI does (scripts/fe3_ai.py) ---

TERRAIN_GROUPS = ai.terrain_groups()
TALK_IDS = {t['id']: t for t in r.talks()}
DOES = {('villages',): 'razing what it reaches', ('chests',): 'emptying what it reaches',
        ('villages', 'chests'): 'razing or emptying what it reaches'}


def count_words(n, word):
    return f"{'one' if n == 1 else NUMBER.get(n, str(n))} {word if n == 1 else plural(word)}"


def goal_tiles(ch, group):
    """The playable tiles of a terrain group as the battle starts (the opening's changes made), or once a change reveals them (a
    closed room's chests): what a looter can go for."""
    return [(y, x) for y in range(1, ch.h + 1) for x in range(1, ch.w + 1)
            if ch.ids[y][x] in TERRAIN_GROUPS[group] or ch.patched.get((y, x), set()) & TERRAIN_GROUPS[group]]


def under(ch, tile):
    """The terrain a unit stands on, under a closed room's roof the room's own (Book 2's thrones in Chapters 6, 16 and 17)."""
    t = ch.ids[tile[0]][tile[1]]
    if not walkable(t) and ch.patched.get(tile):
        return min(ch.patched[tile])
    return t


def nearest(ch, cls, here, group, taken):
    """The tiles of a terrain group nearest a unit by its class's movement costs ($80:B10B, as the terrain goal reads it: $82:91AB),
    leaving out tiles another unit stands on; [] if it can reach none."""
    import heapq
    costs = r.move_costs(cls)
    dist, todo = {here: 0}, [(0, here)]
    while todo:
        d, (y, x) = heapq.heappop(todo)
        if d > dist[(y, x)]:
            continue
        for k in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if not ch.inside(*k) or costs[ch.ids[k[0]][k[1]]] == 0xFF:
                continue
            nd = d + costs[ch.ids[k[0]][k[1]]]
            if nd < dist.get(k, 0x80):
                dist[k] = nd
                heapq.heappush(todo, (nd, k))
    goals = {k: d for k, d in dist.items() if ch.ids[k[0]][k[1]] in TERRAIN_GROUPS[group] and k not in taken}
    if not goals:
        return []
    best = min(goals.values())
    return sorted(k for k, d in goals.items() if d == best)


def sent_off(ch, moved):
    """What AI a script gives that sends units off the map, in words ('Wolf, Vyland, Sedgar and Roshea, with the Paladins and
    Horsemen, make for (12, 22) and leave the map.'), or None."""
    if not moved:
        return None
    units, named, generic, exits = placed_units(ch.m)[0], [], [], []
    for ai_bytes, chars in moved:
        steps = ai.plan(ai_bytes)['steps']
        exit_ = next((st[1] for st, nxt in zip(steps, steps[1:]) if st[0] == 'tile' and nxt[0] == 'leave' and nxt[2]), None)
        if exit_ is None:
            return None
        exits.append('({}, {})'.format(*ch.app(*exit_)))
        for u in units:
            if u['char'] in chars:
                if u['name'] in GENERIC:
                    generic.append(plural(CLASSES[u['class']]))
                else:
                    named.append(name_of(u['name']))
    if not named and not generic:
        return None
    who = or_words(named) + (f", with the {or_words(generic)}," if named and generic else '') if named else 'the ' + or_words(generic)
    one = len(set(named)) == 1 and not generic
    return f"{who} {'makes' if one else 'make'} for {or_words(exits)} and {'leaves' if one else 'leave'} the map, never attacking."


def leave_words(ch, n):
    """What a leave script that keeps the unit on the map does (Book 1's Chapter 8's opens a door: SET_TILE)."""
    run = fe.Run(ch.m, world()).run(0x8B0000 | r.u16(ai.LEAVES + 2 * n))
    doors = [w for w in run.tiles if TERRAIN[ch.ids[w['row']][w['col']]][0] == 'd']
    assert doors and len(doors) == len(run.tiles), (ch.n, n)
    return (f"opens the door{'s' if len(doors) > 1 else ''} at " +
            or_words(['({}, {})'.format(*ch.app(w['row'], w['col'])) for w in doors]))


def ai_words(ch, ai_bytes, unit, here, taken=(), rewrite=False):
    """(words, looter, goes to, raids villages) for what AI bytes make a unit do, or None where it fights as most foes do (it attacks
    what it can reach, and holds or advances): it comes to someone to talk (a decision script's talk of this map), goes for the villages
    and chests, heads for a tile or the nearest tile of a terrain group, makes for a tile and leaves the map, or never attacks (decision
    script 0x02). `unit`: its AI mark; `here`: its tile while it hasn't moved (a terrain goal it stands on is no goal, and the nearest
    tile of one is worked out from there), `taken` the tiles others stand on; `rewrite`: the AI an event gives, said even where it's
    the usual."""
    p, name = ai.plan(ai_bytes), unit['name']
    for char, tid in p['talks']:
        t = TALK_IDS.get(tid)
        if t and t['map'] == ch.m and name in (t['talker'], t['target']):
            other = t['talker'] if t['target'] == name else t['target']
            return f'comes to {name_of(other)} to talk', False, None, False
    words, goes, looter, raids = [], [], False, False
    steps = p['steps']
    for i, st in enumerate(steps):
        nxt = steps[i + 1] if i + 1 < len(steps) else None
        if st[0] == 'tile':
            at = '({}, {})'.format(*ch.app(*st[1]))
            if nxt and nxt[0] == 'leave':
                words.append(f'makes for {at} and ' + ('leaves the map' if nxt[2] else leave_words(ch, nxt[1])))
                if nxt[2]:
                    goes = [ch.app(*st[1])]
            else:
                words.append(f'heads for {at}')
                goes.append(ch.app(*st[1]))
        elif st[0] == 'leave' and not (i and steps[i - 1][0] == 'tile'):
            words.append('leaves the map' if st[2] else leave_words(ch, st[1]))
        elif st[0] == 'loot':
            chests = len(goal_tiles(ch, 9))
            what = tuple(k for k, n in (('villages', len(goal_tiles(ch, 3))), ('chests', chests)) if n)
            if what:
                looter, raids = True, 'villages' in what
                text = f"goes for the {' and '.join(what)}, {DOES[what]}"
                if 'chests' in what and st[1] < chests:
                    text += f", until it has emptied {count_words(st[1], 'chest')}"
                words.append(text)
        elif st[0] == 'terrain' and (here is None or under(ch, here) not in TERRAIN_GROUPS[st[1]]):
            what = ai.GROUP_NAMES[st[1]]
            goal = nearest(ch, unit['class'], here, st[1], taken) if here and not rewrite else None
            if goal is None or len(goal) > 1:
                words.append(f'heads for the nearest {what}')
            elif goal:
                words.append(f"heads for the nearest {what}, at ({', '.join(map(str, ch.app(*goal[0])))})")
                goes.append(ch.app(*goal[0]))
    advance = any(st[0] == 'advance' for st in steps)
    staff = any(st[0] == 'staff' for st in steps)
    if words:
        text = ', then '.join(words) + (', never attacking' if p['passive'] else '')
    elif staff and p['passive'] and unit['staff']:
        if not (unit['armed'] or rewrite):
            return None  # a healer that can't attack anyway
        text = 'uses its staff, never attacking'
    elif p['passive'] and advance:
        text = 'advances on your army, never attacking'
    elif p['passive']:
        text = 'stops moving and attacking' if rewrite else "doesn't move or attack"
    elif rewrite:
        text = 'advances on your army' if advance else 'uses its staff' if staff and unit['staff'] else 'attacks what it can reach'
    else:
        return None
    return text, looter, goes or None, raids


def stays(ch, ai_bytes, here):
    """Whether a unit's AI keeps it on its tile (so an event's new AI starts from there)."""
    p = ai.plan(ai_bytes)
    if any(TALK_IDS.get(tid, {}).get('map') == ch.m for _, tid in p['talks']):
        return False
    return all(st[0] == 'hold' or (st[0] == 'terrain' and under(ch, here) in TERRAIN_GROUPS[st[1]]) for st in p['steps'])


def ai_rewrites(ch, carried):
    """{character: [(kind, trigger words, AI bytes, script)]}: the AI the events after the opening give (event command 0x18), to every
    unit of the character on the map then, each with what sets it off: a turn, an area, a death, a talk or a village visit."""
    first, out = opening_events(ch), {}
    for kind, words, ptr, extra in script_sources(ch.n):
        if kind == 'turn':
            if words in first:
                continue
            when = f"from the {phase_words(words['phase'])} on turn {words['turn']}"
        elif kind == 'death':
            if not words:
                continue
            when = words
        elif kind == 'talk':
            when = f'once {words[0]} has talked to {words[1]}'
        elif kind == 'area':
            when = f"once {whose(ch, words['who'], carried)} stops {area_where(ch, words)}"
        else:
            assert words['kind'] in (VILLAGE, HOUSE) or not ai.rewrites(ptr), (ch.n, words)
            who = 'Marth' if words['who'] == MARTH else 'a unit'
            when = f"once {who} visits the village at ({', '.join(map(str, ch.app(words['row'], words['col'])))})"
        for ai_bytes, chars in ai.rewrites(ptr):
            for c in chars:
                entry = (kind, when, ai_bytes, ptr)
                if entry not in out.setdefault(c, []):
                    out[c].append(entry)
    return out


def settle_ai(ch, m, carried):
    """Turns each unit's '_ai' mark into what the map says: a sentence on its note for what its AI does and for the AI the chapter's
    events give it later, the torch badge for a looter, the tiles it heads for (`goesTo`), and on each village the looters on the map at
    the start that can raze it."""
    rewrites = ai_rewrites(ch, carried)
    raiders = []
    every = [(e, True) for e in m['units']] + [(e, False) for g in m.get('reinforcements', []) for e in g['units']]
    taken = {e['_ai']['here'] for e, at_start in every if at_start}
    for e, at_start in every:
        unit = e.pop('_ai')
        ai_bytes, char, here = unit['ai'], unit['char'], unit['here']
        sentences = []
        base = ai_words(ch, ai_bytes, unit, here, taken - {here})
        if base:
            words, looter, goes, raids = base
            sentences.append(words)
            if looter:
                e['looter'] = True
            if goes:
                e['goesTo'] = goes
            if raids and at_start:
                raiders.append(e['name'])
        # What the events give it later, its triggers gathered by what it does (the deaths in one).
        later = [new for kind, when, new, ptr in rewrites.get(char, [])]
        at = here if stays(ch, ai_bytes, here) and all(stays(ch, new, here) for new in later) else None
        by_words = {}
        for kind, when, new, ptr in rewrites.get(char, []):
            # Not its own death, not the AI it has, nor the event that brought it (its AI is already the new one).
            if (kind == 'death' and when == (e['name'], False)) or new == ai_bytes or ptr == unit['placed_by']:
                continue
            got = ai_words(ch, new, unit, at, taken - {here}, rewrite=True)
            by_words.setdefault(got[0], []).append((kind, when))
            if got[2]:
                e.setdefault('goesTo', [])
                e['goesTo'] += [t for t in got[2] if t not in e['goesTo']]
        for words, whens in by_words.items():
            deaths = [w for k, w in whens if k == 'death']
            parts = [w for k, w in whens if k != 'death'] + ([f'once {deaths_words(deaths)} is defeated'] if deaths else [])
            sentences.append(f"{', or '.join(parts)}, {words}")
        if sentences:
            text = ' '.join(x[0].upper() + x[1:] + '.' for x in sentences)
            e['note'] = (e['note'] if e['note'].endswith('.') else e['note'] + '.') + ' ' + text
    claimed = {}
    for e, _ in every:
        if e.get('goesTo') and 'nearest' in e['note']:
            claimed.setdefault(tuple(e['goesTo'][0]), []).append(e)
    for tile, es in claimed.items():
        if len(es) > 1:
            for e in es:
                x, y = tile
                e['note'] = e['note'].replace(f', at ({x}, {y})', '')
                e['goesTo'] = [t for t in e['goesTo'] if tuple(t) != tile] or None
                if not e['goesTo']:
                    del e['goesTo']
    if raiders:
        raze = f"{' or '.join(dict.fromkeys(raiders))} can raze it before you visit."
        for o in m['objects']:
            x, y = o['tile']
            if o['type'] == 'village' and ch.ids[ch.h + 1 - y][x] in TERRAIN_GROUPS[3]:
                o['note'] = f"{o['note']} {raze}" if o.get('note') else raze


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
            sends = sent_off(ch, ai.rewrites(r.tile_script(t['id'])))
            if not reward and not joins and not sends:
                continue
            # The record's who byte is a name id ($83:E519): a village is Marth's to visit, a house (FF) anyone's.
            o = {'type': 'village', 'tile': tile, 'reward': reward}
            notes = [f"{' and '.join(dict.fromkeys(joins))} {'joins' if len(set(joins)) == 1 else 'join'} your army."] if joins else []
            if sends:
                notes.append(sends)
            cond = condition(t['flag']) if conditional(t['flag']) else []
            held = [item_name(v) for k, v in cond if k == 0]
            needs = (f", holding the {or_words(held)}" + (' (it takes them)' if run.taken else '')) if held else ''
            if t['kind'] == HOUSE:
                notes.append('(A house: any unit can visit it.)')
            elif t['who'] == MARTH:
                notes.append(f'Only Marth can visit it{needs}.')
            elif needs:
                notes.append(f'Given only to a unit{needs}.')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i, _ in run.items:
                where = 'Given at a village' if t['kind'] == VILLAGE else 'Given at a house'
                source(i, m['id'], 'village', where + (f" for the {or_words(held)}" if held else ''))
            for u in run.loads:
                if u['side'] == fe.PLAYER:
                    for i in u['items']:
                        source(i, m['id'], later('kit', ch.n), f"Carried by {name_of(u['name'])} on joining", who=u['char'])
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


def opening_conditions(ch, units):
    """{id(unit): words} for the units the opening places only on a condition, found by playing it again with each of its checks
    turned the other way (IF_FLAG, IF_PRESENT): Book 1's Chapter 11 brings Catria and Palla only with Minerva in your army, Book 2's
    Chapter 8 Jeorge only if he lived through Chapter 5. And the flags it waits on that no script sets: [(flag, [unit])]."""
    checks = []
    for e in opening_events(ch):
        for _, c, ops in fe.reachable(e['ptr']):
            if c == 0x13:
                checks.append(('flag', ops[0] | ops[1] << 8))
            elif c == 0x1F:
                checks.append(('present', ops[0]))
    key = lambda u: (u['char'], u['start'])  # noqa: E731
    base = {key(u): u for u in units}
    words, unset = {}, []
    for kind, v in dict.fromkeys(checks):
        w = world()
        if kind == 'flag':
            w.flags.add(v)
        else:
            w.army.discard(v)
        alt = {key(u) for u in opening(ch, w, dry=True).units}
        gone = [u for k, u in base.items() if k not in alt]
        if not gone:
            continue
        if kind == 'present':
            text = f"Placed only with {name_of(next((x['name'] for x in placed_units(ch.m)[0] if x['char'] == v), v))} in your army."
        else:
            setters = [(n, k_, wd) for n, k_, wd in FLAG_SETS.get(v, []) if n < ch.n and (n <= 20) == (ch.n <= 20)]
            if not setters:
                unset.append((v, gone))
                continue
            n, k_, wd = setters[-1]
            if k_ == 'death':
                text = f"Placed only if {wd[0]} wasn't defeated in {chapter_label(n)}."
            elif k_ == 'talk':
                text = f"Placed only if {wd[0]} didn't talk to {wd[1]} in {chapter_label(n)}."
            else:
                text = f'Placed only on a condition from {chapter_label(n)}.'
        for u in gone:
            words.setdefault(id(u), []).append(text.replace(f" to {name_of(u['name'])} in ", ' to him in '))
    for kind, v in dict.fromkeys(checks):
        if kind != 'flag' or any(n < ch.n for n, _, _ in FLAG_SETS.get(v, [])):
            continue
        w = world()
        w.flags.add(v)
        base_tiles = {(t['row'], t['col']): t['tile'] for t in opening(ch, dry=True).tiles}
        alt_tiles = {(t['row'], t['col']): t['tile'] for t in opening(ch, w, dry=True).tiles}
        changed = [k for k in set(base_tiles) | set(alt_tiles) if base_tiles.get(k) != alt_tiles.get(k) and ch.inside(*k)]
        if changed:
            unset.append((v, [{'tile': ch.app(*k)} for k in sorted(changed)]))
    return words, unset


def leavers(ch):
    """{(character, row, col) or character: words} for the units a script takes off the map after the opening (REMOVE, 0x0B): on a turn
    (Book 1's Chapter 6: Minerva, Palla, Catria and Est on turn 2; Chapter 12: Gharnef on turn 4), in a talk (Lorenz goes with Marth's)
    or once someone falls (the Earth Dragons with Medeus). The turn ones always go."""
    out, first = {}, opening_events(ch)
    for kind, words, ptr, extra in script_sources(ch.n):
        if kind == 'turn' and words in first:
            continue
        removes = [ops[0] for _, c, ops in fe.reachable(ptr) if c == 0x0B]
        for char in removes:
            if kind == 'turn':
                text, always = f"Leaves at the start of the {phase_words(words['phase'])} on turn {words['turn']}", True
            elif kind == 'talk':
                text, always = f'Leaves when {words[0]} talks to him', False
            elif kind == 'death' and words:
                text, always = f'Leaves once {words[0]} is defeated', False
            else:
                continue
            out.setdefault(char, (text, always))
    return out


def gift_notes(ch, carried=()):
    """Notes for what the area, death and turn events hand out (items, not weapons: the spheres, the Binding Shield): who gets it,
    and on what (IF_NO_ITEM: the items the army must hold; TAKE_ITEM: what it takes)."""
    out, first = [], opening_events(ch)
    every = set(range(r.ITEM_COUNT))
    for kind, words, ptr, extra in script_sources(ch.n):
        if kind not in ('area', 'death', 'turn') or (kind == 'turn' and words in first):
            continue
        rich = fe.Run(ch.m, fe.World(army=set(ARMY), items=set(every))).run(ptr)
        poor = fe.Run(ch.m, fe.World(army=set(ARMY), items=set())).run(ptr)
        given = [i for i, _ in rich.items]
        if not given:
            continue
        needs = [ops[0] for _, c, ops in fe.reachable(ptr) if c == 0x29]
        plain = [i for i, _ in poor.items]
        to = {who for _, who in rich.items}
        to_words = name_of(MARTH) if to <= {None, 0x81} else 'the unit'
        if kind == 'area':
            (c1, c2), (r1, r2) = words['cols'], words['rows']
            x1, y1 = ch.app(r2, c1)
            x2, y2 = ch.app(r1, c2)
            where = f'on ({x1}, {y1})' if (x1, y1) == (x2, y2) else f'in the area from ({x1}, {y1}) to ({x2}, {y2})'
            when = f"When {whose(ch, words['who'], carried)} stops {where}"
        elif kind == 'death':
            when = f'Once {words[0]} is defeated' if words else 'Once a unit is defeated'
        else:
            when = f"At the start of the {phase_words(words['phase'])} on turn {words['turn']}"
        extra_items = [i for i in given if i not in plain]
        if to_words == name_of(MARTH) and when.startswith('When Marth'):
            to_words = 'he'
        text = when + ', '
        if plain:
            text += f"{to_words} gets the {or_words([item_name(i) for i in plain])}"
            if extra_items:
                text += f", and the {or_words([item_name(i) for i in extra_items])} if your army holds the " + \
                        or_words([item_name(i) for i in needs])
        else:
            text += f"if your army holds the {or_words([item_name(i) for i in needs])}, {to_words} gets the " + \
                    or_words([item_name(i) for i in extra_items])
        taken = [item_name(i) for i in rich.taken]
        if taken and set(rich.taken) == set(needs):
            text += " (they're taken)" if len(taken) > 1 else ' (it is taken)'
        elif taken:
            text += f" (the {or_words(taken)} {'are' if len(taken) > 1 else 'is'} taken)"
        out.append(text + '.')
    return out


def later(kind, n):
    """A source that counts from the next chapter: what joins, or is given, during or after a battle ('kit-later'); the last chapter
    has no next, so what it gives counts there."""
    return kind if n == r.MAX_CHAPTER else f'{kind}-later'


def endgame_note():
    """Book 2's Chapter 20 has two seize records ($8C:917C): one with no condition, whose script ends the game (BOOK_END), and one with a
    condition, which goes on to the Endgame (the last record whose condition holds wins)."""
    m40 = r.chapter_map(40)
    conds = [t['flag'] for t in r.tile_records(r.TILE_EVENTS) if t['map'] == m40 and t['kind'] == SEIZE and conditional(t['flag'])]
    words = condition_words(40, condition(conds[0]))
    return f"Opens {words} when Marth seizes the throne in Book 2's Chapter 20; without it, the game ends there."


def main():
    titles, goals = chapter_titles(), objectives()
    groups = move_groups()
    maps, sources, used, variants = [], {}, {}, {}
    names, name_counts = {}, {}  # map id -> code -> name -> tiles; code -> name -> how many tiles
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

    sets, clears = flag_setters()
    FLAG_SETS.update(sets)
    FLAG_CLEARS.update(clears)
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
            source(i, map_id, later('talk', n), f'{name_of(a)} talks to {name_of(b)}')
        # Your army's starting tiles; Marth's is the first, and the opening may walk him from it.
        m['starts'] = [ch.app(*t) for t in r.deploy_tiles(mi) if ch.inside(*t)]
        foes = [u for u in run.units if u['side'] == fe.ENEMY]
        # The game's boss list is by name, for both books: a talk recruit on it is this chapter's boss only when no one else on the list
        # is (Sheena in Book 2's Chapter 17 is; Lorenz, Book 2's first boss, isn't in Book 1's Chapter 16, where Camus is).
        placed_if, unset = opening_conditions(ch, run.units)
        leaving = leavers(ch)
        # A boss a turn's script always takes off the map only passes through (Gharnef in Book 1's Chapter 12): a named foe.
        passing = {u['name'] for u in foes if leaving.get(u['char'], (None, False))[1]}
        listed = {u['name'] for u in foes if u['name'] in BOSSES and u['name'] not in passing}
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
            extra = placed_if.get(id(u), []) + ([leaving[u['char']][0] + '.'] if u['char'] in leaving else [])
            if extra:
                e['note'] = e['note'] + '. ' + ' '.join(extra)
            m['units'].append(e)
            # One who leaves on a turn and can't be harmed before (Imhullu without a Starlight, Book 1's Chapter 6 four) gives nothing.
            if leaving.get(u['char'], (None, False))[1] and (n == 6 or any(item_name(i) == 'Imhullu' for i in u['weapons'])):
                continue
            if (e.get('talk') or '').startswith('Recruit'):
                # The record the talk swaps in, by its own name (Book 2's Chapter 6: the foe called Navarre joins as Samuel).
                joiner = recruits.get(u['name'], u)
                for i in joiner['items']:
                    source(i, map_id, later('kit', n), f"Carried by {name_of(joiner['name'])} on joining", who=joiner['char'])
            else:
                foe_sources(source, map_id, u, e)
        if forced:
            m['forced'] = forced
        if m.get('corrinStart') and m['starts'] and m['corrinStart'] not in m['starts']:
            # The opening walks Marth off his starting tile (Chapter 1 of each book): he starts where it leaves him.
            m['starts'][0] = m['corrinStart']
        arrivals(ch, m, source, talks, run.units)
        m['changes'], closed = changes_of(ch, m, run.units)
        settle_ai(ch, m, run.units)
        if seize:
            what = 'throne' if 'throne' in goals[n] else 'castle'
            label = f'Seize the {what} with Marth'
            # A seize record with a condition (Endgame 2's last part: flag 9, which Medeus's death clears).
            cond = next((t['flag'] for t in tile_events(ch) if t['kind'] == SEIZE and conditional(t['flag'])), None)
            words = condition_words(n, condition(cond)) if cond and n != 40 else ''
            m['objectives'].append({'type': 'seize', 'tiles': [ch.app(*seize)], 'label': label + (f', {words}' if words else '')})
        parts = [x.strip() for x in m['victory'].split('  ') if x.strip()]
        m['victory'] = parts[0] + ''.join(f', then {x[0].lower() + x[1:]}' for x in parts[1:])
        m['notes'] += gift_notes(ch, run.units)
        for f, gone in unset:
            if all('tile' in u for u in gone):
                where = or_words(['({}, {})'.format(*u['tile']) for u in gone])
                m.setdefault('unconfirmed', []).append(
                    f"Whether the village at {where} starts closed: the opening closes it only while an event flag no chapter's script "
                    'sets is set.')
                continue
            m.setdefault('unconfirmed', []).append(
                f"What else could keep {or_words([name_of(u['name']) for u in gone])} away: the opening places "
                f"{'them' if len(gone) > 1 else 'him'} only while an event flag no chapter's script sets is clear.")
        # The end of the chapter: what the seize scene gives.
        for t in tile_events(ch):
            if t['kind'] == SEIZE:
                end = fe.Run(ch.m, world()).run(r.tile_script(t['id']))
                for i, who in end.items:
                    # ITEM with unit FF gives it to the unit acting: Marth, who seizes ($87:9AF5).
                    to = name_of(MARTH) if who is None else whose(ch, who)
                    source(i, map_id, later('event', n), f'Given at the end of the chapter to {to}')
        if n == 41:
            m['notes'].append(endgame_note())
        if n == 6:
            # $83:B96E: in this chapter an attack on Minerva, Palla, Catria or Est always misses.
            m['notes'].append("Minerva, Palla, Catria and Est can't be hit in this chapter: every attack on them misses.")
        # Terrain: each id's code; per-map overrides where a map's tile works differently from the game-wide one.
        codes = []
        for y, row in enumerate(rows, 1):
            line = []
            for x, t in enumerate(row, 1):
                letter, info = tile_info(t, groups)
                if (y, x) in closed:
                    letter, info = 'X', {**ROOF, 'move': {label: None for label in info['move']}}
                kind = ch.shops.get((y, x))
                if letter == 'H' and kind in ('Armory', 'Vendor'):
                    # One shop tile for both: drawn as the shop its event opens.
                    letter, info = ('A' if kind == 'Armory' else 'V'), {**info, 'name': kind}
                code = encode(GAME, letter)
                line.append(code)
                name = info.pop('name')
                names.setdefault(map_id, {}).setdefault(code, {}).setdefault(name, []).append(ch.app(y, x))
                name_counts.setdefault(code, {}).setdefault(name, 0)
                name_counts[code][name] += 1
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
        info[code] = {'name': max(name_counts[code], key=lambda n: (name_counts[code][n], n)), **best[0]}
    for m in maps:
        over = {}
        for code, e in used[m['id']].items():
            if e != {k: v for k, v in info[code].items() if k != 'name'}:
                diff = {k: v for k, v in e.items() if v != info[code].get(k)}
                over[code] = diff
        # A map with two variants of one code: they must differ only where its units never go (checked by hand: Chapter 8's
        # pillars differ for Ice and Sea Dragons alone).
        # The game's names on the map: a code whose tiles the game names otherwise, or by more than one name, says so ('Path /
        # Corridor'), the tiles with each other name listed.
        for code, by_name in names[m['id']].items():
            order = sorted(by_name, key=lambda k: (-len(by_name[k]), k))
            if order != [info[code]['name']]:
                over.setdefault(code, {})['name'] = ' / '.join(order)
                if len(order) > 1:
                    over[code]['tileNames'] = {k: by_name[k] for k in order[1:]}
        if over:
            m['terrainOverrides'] = over
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
