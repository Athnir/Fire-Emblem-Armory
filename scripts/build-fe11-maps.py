"""
Shadow Dragon's maps and where each item turns up, from the game's own files (data-raw/fe11/README.md): each chapter's grid
(map/<chapter>), its placements (dispos/<chapter>), its scripts (script/<chapter>.cmb, script/<chapter>_ter.cmb) and the database.
Writes src/data/fe11/fe11Terrain.ts, fe11Maps.ts and fe11ItemSources.ts.

- The story: Prologue I-IV (bmap201-204), then Chapters 1-24 (bmap001-024) with each gaiden chapter (bmap101-105: 6x, 12x, 17x, 20x,
  24x) where it comes, then the Endgame (bmap025). A chapter's `ChapterNext` handler names the gaiden it opens (`SetChapter`).
- A map's grid: the map file's first 32 x 32 grid (Terrain ids), its width and height from the header (+0xc, +0xd).
- Units: a placement file's groups ([name, records, count]); 80-byte records: +0 person, +2 class, +4 x, y (where it enters), +6 x, y
  (where it stands), +8 team (0 yours, 1 enemy, 2 other), +9 level, +0x10 its five items (an item and a flag byte each: 0x01 it drops),
  +0x24 u16 flags (0x100 the boss). `MapBegin` places 'mikata' (your deployment slots) and 'first' (the foes); the opening scene
  places more ('mikata_2': units joining, 'first2'...); groups named e01 / ev... are the scenes' actors. A turn handler (type 0x17:
  first turn, last turn, phase) placing a group is a reinforcement.
- Tiles: a terrain script's handlers (x, y, kind): 5 a door, 6 a chest (TreasureGet), 7 a drawbridge, 8 a village (ItemGet, MoneyGet,
  or a recruit walking out: DisposPlayArea), 9 a house, 10 an armory and 11 a vendor (Goods; GoodsLimit: a limited stock), 12 the secret
  shop (a VIP Card), 14 the tile to seize.

    python scripts/build-fe11-maps.py
"""
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe11_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe11_cmb import Script  # noqa: E402
from fe13_bin import Bin  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe11', 'Shadow Dragon', 'build-fe11-maps.py'
ROM = D.ROM

PROLOGUE = ['bmap201', 'bmap202', 'bmap203', 'bmap204']
GAIDEN = {'bmap101': '6x', 'bmap102': '12x', 'bmap103': '17x', 'bmap104': '20x', 'bmap105': '24x'}
AFTER = {6: 'bmap101', 12: 'bmap102', 17: 'bmap103', 20: 'bmap104', 24: 'bmap105'}

# Terrain ids (the database's Terrain table, by its name label) -> a letter. Each letter's code: GAME['fe11'] in terrain_codes.py.
LETTER = {
    'MS_TER_NOMOVE': '#', 'MS_TER_PLAIN': '.', 'MS_TER_VILLAGE': 'v', 'MS_TER_HOUSE': 'B', 'MS_TER_FORT': 'F',
    'MS_TER_CASTLEGATE': 'g', 'MS_TER_GROVE': 'f', 'MS_TER_DESERT': 's', 'MS_TER_RIVER': 'w', 'MS_TER_MOUNTAIN': 'm',
    'MS_TER_ALP': 'P', 'MS_TER_BRIDGE': 'b', 'MS_TER_SEA': 'a', 'MS_TER_FLOOR': 'O', 'MS_TER_WALL': '#', 'MS_TER_COLUMN': 'p',
    'MS_TER_STEP': 'S', 'MS_TER_STONEWALL': 'C', 'MS_TER_CASTLE': 'N', 'MS_TER_FENSE': 'l', 'MS_TER_WEAPON': 'A',
    'MS_TER_ITEM': 'V', 'MS_TER_COLISSEUM': 'R', 'MS_TER_CHECKROOM': 'U', 'MS_TER_TREASUREBOX': 'c', 'MS_TER_THRONE': 't',
    'MS_TER_DOOR': 'd', 'MS_TER_DRAWBRIDGE': 'Z', 'MS_LAVA': 'M', 'MS_TER_CLOSEVILLAGE': 'X', 'MS_TER_DESTROYVILLAGE': 'r',
}
DOOR, CHEST, DRAWBRIDGE, VILLAGE, HOUSE, ARMORY, VENDOR, SECRET, SEIZE = 5, 6, 7, 8, 9, 10, 11, 12, 14
TURN, AREA, TALK = 0x17, 0x04, 0x08
TURNS = (0x17, 0x03)  # both a turn's handler: (first turn, last turn, phase)
WIN = {1: 'Seize', 2: 'Rout the enemy', 3: 'Defend', 4: 'Defeat the boss'}
BOSS = 0x100


# ---------------------------------------------------------------------------------------------------------------------------------
# Files

def mapfile(key):
    b = Bin(open(os.path.join(ROM, 'map', key), 'rb').read())
    w, h = b.d[0x20 + 0xc], b.d[0x20 + 0xd]
    g = b.u32(0x10)
    return w, h, [[b.d[0x20 + g + y * 32 + x] for x in range(w)] for y in range(h)]


def dispos(key):
    """{group: [unit]} from a placement file."""
    b = Bin(open(os.path.join(ROM, 'dispos', key), 'rb').read())
    P, J, I = D.persons(), D.jobs(), D.items()
    out, o = {}, 0
    while True:
        n, rec, cnt = struct.unpack_from('<3I', b.d, 0x20 + o)
        if not n and not rec:
            return out
        units = []
        for k in range(cnt):
            r = b.d[0x20 + rec + k * 80:0x20 + rec + k * 80 + 80]
            p, j = struct.unpack_from('<HH', r, 0)
            items = []
            for s in range(0x10, 0x1a, 2):
                if r[s]:
                    items.append((I[r[s]]['iid'], bool(r[s + 1] & 1)))
            # (0, 0) for where it stands: it stays where it enters.
            at = (r[6], r[7]) if r[6] or r[7] else (r[4], r[5])
            units.append({'person': P[p], 'job': J[j], 'from': (r[4], r[5]), 'at': at, 'team': r[8], 'level': r[9],
                          'items': items, 'flags': struct.unpack_from('<H', r, 0x24)[0]})
        out[b.cstr(0x20 + n)] = units
        o += 12


def script(key):
    path = os.path.join(ROM, 'script', key + '.cmb')
    return Script(path) if os.path.exists(path) else None


def trigger(s, h):
    return struct.unpack_from('<I', s.d, s.offs[h['index']] + 0xc)[0] & 0xFFFF


def named(s, name):
    return next((h for h in s.handlers() if h['name'] == name), None)


# A story flag a placement waits on, in words.
FLAG_WORDS = {'gf_２４章外伝を通る': 'Chapter 24x was played'}


def play(ch, handlers):
    """Play the scenes that set the map up (MapBegin, then the opening), the way the engine does, straight through: each Dispos places
    a group's units where its records stand them, a unit fetched into a local (UnitGetByPID, UnitGetByPos, UnitGetHero) is moved by
    UnitMovePos / UnitMovePosEx / UnitSetPos / UnitWarpAppearance and taken off by UnitRemove*; UnitStackPush saves every unit and
    UnitStackPop puts them back as they were (arm9 0x20451ec / 0x20451fc: overlay 00 0x21a323c / 0x21a32c8), undoing what the scene
    moved in between; a 0x37 runs another handler of the script. Both sides of a story flag's check run (FlagGet of a gf_ flag, then
    jz), each placement tagged with the side it's on. Returns [(group, unit, tile, conditions)] for what stands at the end, a condition
    being (flag, True if set)."""
    placed = []

    def find(ref):
        if not ref:
            return None
        kind, v = ref
        for i in range(len(placed) - 1, -1, -1):
            g, u, at, _ = placed[i]
            if kind == 'pid' and u['person']['pid'] == v or kind == 'pos' and tuple(at) == tuple(v):
                return i
        return None

    def run(h, depth=0):
        stack, local, saved, regions = [], {}, [], []
        ops = ch.s.disasm(h)
        for k, (pc, op, v) in enumerate(ops):
            conds = [c for start, end, c in regions if start <= pc < end]
            if op in ('int', 'str'):
                stack.append(v)
            elif op == 'addr':
                stack.append(('addr', v))
            elif op == 'local':
                stack.append(local.get(v))
            elif op == 'setlocal':
                local[v] = stack.pop() if stack else None
            elif op == 'assign':
                val = stack.pop() if stack else None
                addr = stack.pop() if stack else None
                if isinstance(addr, tuple) and addr[0] == 'addr':
                    local[addr[1]] = val
            elif op == 'gosub' and depth < 3:
                run(ch.s.handlers()[v], depth + 1)
            elif op == 'call':
                fn, argc = v
                args = stack[len(stack) - argc:] if argc else []
                del stack[len(stack) - argc:]
                res = None
                if fn.startswith('Dispos') and fn != 'DisposWait' and args and isinstance(args[0], str):
                    for u in ch.groups.get(args[0], []):
                        placed.append((args[0], u, tuple(u['at']), conds))
                elif fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and args:
                    res = ('pid', args[0])
                elif fn in ('UnitGetByPos', 'UnitSafetyGetByPos') and len(args) == 2:
                    res = ('pos', (args[0], args[1]))
                elif fn == 'UnitGetHero':
                    res = ('pid', 'PID_MARS')
                elif fn in ('UnitMovePos', 'UnitMovePosEx', 'UnitSetPos', 'UnitWarpAppearance') and len(args) >= 3:
                    i = find(args[0])
                    if i is not None and isinstance(args[1], int) and isinstance(args[2], int):
                        g, u, _, c = placed[i]
                        placed[i] = (g, u, (args[1], args[2]), c)
                elif fn.startswith('UnitRemove') and fn not in ('UnitRemoveAll', 'UnitRemoveAllwithoutHero') and args:
                    i = find(args[0])
                    if i is not None:
                        placed.pop(i)
                elif fn == 'UnitStackPush':
                    saved.append(list(placed))
                elif fn == 'UnitStackPop' and saved:
                    placed[:] = saved.pop()
                elif fn == 'FlagGet' and args and isinstance(args[0], str) and args[0].startswith('gf_'):
                    res = ('flag', args[0])
                stack.append(res)
            elif op == 'pop':
                if stack:
                    stack.pop()
            elif op in ('jz', 'or', 'and'):
                top = stack.pop() if stack else None
                if op == 'jz' and isinstance(top, tuple) and top[0] == 'flag' and v > pc:
                    # if (flag) { ... } else { ... }: the else side runs from the jump's target to where the if side's last jmp goes.
                    regions.append((pc, v, (top[1], True)))
                    last = next((q for q in ops if q[0] < v and ops.index(q) > k and ops[ops.index(q) + 1][0] >= v), None)
                    if last and last[1] == 'jmp' and last[2] > v:
                        regions.append((v, last[2], (top[1], False)))
            elif op in ('deref', 'eaddr'):
                if stack:
                    stack[-1] = None

    for h in handlers:
        if h:
            run(h)
    return placed


def groups_placed(s, h):
    return [a[0] for fn, a in s.calls(h) if fn.startswith('Dispos') and fn not in ('DisposWait',) and a and isinstance(a[0], str)]


# ---------------------------------------------------------------------------------------------------------------------------------
# Terrain

def terrain_rows():
    """[(name label, avoid, defence, heal %, cost column)] by terrain id. The cost column is the terrain's category's index, as the
    engine reads it (arm9 0x2038248 turns the category pointer into its index, 0x203826c reads TerrainCost[4 + 32 x row + index], and
    the map's per-tile column grid is filled the same way as it loads, overlay 00 0x21a3364); Terrain +0xc is another number (plains'
    is 0, a column no class can enter)."""
    b = D.db()
    cat0 = b.at['TerrainCategory']
    out = []
    for _, o in D.table('Terrain', 16, 'TerrainCategory'):
        cat = b.u32(o + 8)
        avo, df, _, heal = (b.u8(cat + i) for i in range(4))
        out.append((b.str(o), avo if avo < 0x80 else avo - 0x100, df, heal, (cat - cat0) // 4))
    return out


def cost_rows():
    b = D.db()
    start = b.at['TerrainCost'] + 4
    return [[b.u8(start + r * 32 + c) for c in range(32)] for r in range(25)]


TERRAIN = terrain_rows()
COSTS = cost_rows()
# The game's names (m/en_*), but for three it can't show plainly: '----' (no unit's tile), the mountain (drawn with special glyphs)
# and the raised drawbridge (the game's "Bridge", as it is once lowered).
NAMES = {
    'MS_TER_NOMOVE': 'Out of bounds', 'MS_TER_PLAIN': 'Plain', 'MS_TER_VILLAGE': 'Village', 'MS_TER_HOUSE': 'House',
    'MS_TER_FORT': 'Fort', 'MS_TER_CASTLEGATE': 'Gate', 'MS_TER_GROVE': 'Forest', 'MS_TER_DESERT': 'Desert',
    'MS_TER_RIVER': 'River', 'MS_TER_MOUNTAIN': 'Mountain', 'MS_TER_ALP': 'Peak', 'MS_TER_BRIDGE': 'Bridge', 'MS_TER_SEA': 'Sea',
    'MS_TER_FLOOR': 'Floor', 'MS_TER_WALL': 'Wall', 'MS_TER_COLUMN': 'Pillar', 'MS_TER_STEP': 'Stairs',
    'MS_TER_STONEWALL': 'Ledge', 'MS_TER_CASTLE': 'Castle', 'MS_TER_FENSE': 'Fence', 'MS_TER_WEAPON': 'Armory',
    'MS_TER_ITEM': 'Vendor', 'MS_TER_COLISSEUM': 'Arena', 'MS_TER_CHECKROOM': 'Storage', 'MS_TER_TREASUREBOX': 'Chest',
    'MS_TER_THRONE': 'Throne', 'MS_TER_DOOR': 'Door', 'MS_TER_DRAWBRIDGE': 'Drawbridge', 'MS_LAVA': 'Lava',
    'MS_TER_CLOSEVILLAGE': 'Village (closed)', 'MS_TER_DESTROYVILLAGE': 'Ruins',
}
# Tiles only the lord can't enter: the game's categories 25-29 (a plain, floor, forest, fort and mountain whose cost column bars the
# Lord's row alone: reinforcements' entry tiles in Chapters 9 and 12x), each kind a code of its own.
LORD_ONLY = {'MS_TER_PLAIN': 'Q', 'MS_TER_FLOOR': 'Q', 'MS_TER_GROVE': 'K', 'MS_TER_FORT': 'J', 'MS_TER_MOUNTAIN': 'Y'}


def used_jobs():
    """The classes some placement in a played map uses."""
    keys = PROLOGUE + [f'bmap{n:03d}' for n in range(1, 26)] + list(GAIDEN)
    return {u['job']['jid'] for k in keys for units in dispos(k).values() for u in units}


def move_groups():
    """Movement types: the classes sharing a row of TerrainCost, named by them (classes no placement uses left out)."""
    by_row = defaultdict(list)
    used = used_jobs()
    for j in D.jobs():
        if j['name'] and j['jid'] != 'JID_DUMMY' and j['jid'] in used:
            by_row[j['cost_row']].append(j['name'])
    groups = []
    for row, names in sorted(by_row.items()):
        label = ', '.join(dict.fromkeys(names))
        groups.append((label, row))
    return groups


GROUPS = move_groups()
LORD_ROW = next(j['cost_row'] for j in D.jobs() if j['jid'] == 'JID_LORD')


def letter_of(t):
    """A terrain id's letter: its name's, or (a tile only the lord can't enter) its kind's own."""
    label, *_, col = TERRAIN[t]
    if label in LORD_ONLY and COSTS[LORD_ROW][col] == 0xFF:
        return LORD_ONLY[label]
    return LETTER[label]


def tile_info(t):
    label, avo, df, heal, col = TERRAIN[t]
    move = {g: (None if COSTS[row][col] == 0xFF else COSTS[row][col]) for g, row in GROUPS}
    name = NAMES.get(label, label) + (" (the lord can't enter)" if letter_of(t) in LORD_ONLY.values() else '')
    return {'name': name, 'def': df, 'avo': avo, 'heal': heal, 'move': move}


# ---------------------------------------------------------------------------------------------------------------------------------
# One chapter

class Chapter:
    """A chapter's files. Every grid has a one-tile border no unit enters (the wiki's sizes are the files' less 2 each way): the map
    is the tiles inside it, from (1, 1) at the bottom left."""
    def __init__(self, key):
        self.key = key
        w, h, self.ids = mapfile(key)
        self.w, self.h = w - 2, h - 2
        self.groups = dispos(key)
        b = D.db()
        rec = next(o for _, o in D.table('MapTbl', 32, 'arena01') if b.str(o) == key)
        # MapTbl +0x1c: the levels of growth each mode adds to foes; +0x1d: the Hard modes' weapon tier.
        self.levels, self.tier = b.u8(rec + 0x1c), b.u8(rec + 0x1d)
        self.s = script(key)
        self.ter = script(key + '_ter')

    def app(self, xy):
        x, y = xy
        return [x, self.h + 1 - y]

    def inside(self, xy):
        return 1 <= xy[0] <= self.w and 1 <= xy[1] <= self.h


def unit_name(u):
    p, j = u['person'], u['job']
    return (p['name'] if p['named'] else None) or j['name']


def person_name(pid):
    p = next((p for p in D.persons() if p['pid'] == pid), None)
    return (p['name'] if p else None) or pid


def item_name(iid):
    """An item's name; a false copy (IID_MAFU_FALSE, IID_FALCHION_FALSE: what Chapter 23's doubles of Gharnef carry) says so."""
    it = next(i for i in D.items() if i['iid'] == iid)
    return it['name'] + (' (false)' if iid.endswith('_FALSE') else '')


MODES = ['Normal', 'Hard', 'Brutal', 'Savage', 'Fiendish', 'Merciless']
# The Hard modes' weapon upgrades (arm9 0x20d4bc0, by weapon kind: the tier 0-3 weapons).
UPGRADES = {0: ['IID_IRONSWORD', 'IID_STEELSWORD', 'IID_SILVERSWORD', 'IID_BRAVESWORD'],
            1: ['IID_IRONLANCE', 'IID_STEELLANCE', 'IID_SILVERLANCE', 'IID_BRAVELANCE'],
            2: ['IID_IRONAXE', 'IID_STEELAXE', 'IID_SILVERAXE', 'IID_BRAVEAXE'],
            3: ['IID_IRONBOW', 'IID_STEELBOW', 'IID_SILVERBOW', 'IID_BRAVEBOW'],
            4: ['IID_FIRE', 'IID_ELFIRE', 'IID_BOLGANONE', 'IID_THORON']}
AUTOLEVEL = 0x110


def mode_items(u, tier, mode):
    """A foe's items on a mode (arm9 0x203a424, as the unit is made): with the chapter's tier (MapTbl +0x1d) less 1 on Savage and
    Fiendish, as it is on Merciless, nothing below Savage, held 0-4. A weapon of a lower tier becomes its kind's weapon of that tier (3
    at most), forged (Mt +4, Hit +20) at tier 4; a special weapon (0x7e) is forged at tier 2 and up on Fiendish and Merciless, or tier 3
    and up on Savage (Mt +4, or +8 at tier 4; Hit +20). A dropped item only changes in the first slot; then the game gives the unit
    a copy of the original that still drops (0x203cef8) and the slot's copy no longer does. Only foes the game levels (+0x24 0x10 or
    0x100) change. Returns [(name, drops)]."""
    I = {i['iid']: i for i in D.items()}
    t = 0 if mode < 3 else tier - 1 if mode < 5 else tier
    t = max(0, min(4, t))
    out, kept = [], []
    for slot, (iid, drop) in enumerate(u['items']):
        it = I[iid]
        name = item_name(iid)
        if not u['flags'] & AUTOLEVEL or it['tier'] == 0x7F or drop and slot:
            out.append((name, drop))
            continue
        if it['tier'] == 0x7E:
            if not it['noforge'] and t >= 2 and (mode >= 4 or t >= 3):
                out.append((f"{name} (forged: Mt +{8 if t >= 4 else 4}, Hit +20)", False))
                if drop:
                    kept.append((name, True))
            else:
                out.append((name, drop))
            continue
        if t > it['tier'] and it['kind'] in UPGRADES:
            new = I[UPGRADES[it['kind']][min(t, 3)]]['name']
            out.append((new + (' (forged: Mt +4, Hit +20)' if t >= 4 else ''), False))
            if drop:
                kept.append((name, True))
        else:
            out.append((name, drop))
    return out + kept


def mode_words(u, tier):
    """' (Savage, Fiendish: Steel Axe; Merciless: Silver Axe)': where the modes change a foe's items, one entry per change."""
    normal = mode_items(u, tier, 0)
    groups = []
    for mode in range(1, 6):
        items = mode_items(u, tier, mode)
        if items == normal:
            continue
        if groups and groups[-1][1] == items:
            groups[-1][0].append(MODES[mode])
        else:
            groups.append(([MODES[mode]], items))
    return '; '.join(', '.join(ms) + ': ' + ', '.join(n for n, _ in items) for ms, items in groups)


def unit_entry(ch, u, kind):
    e = {'type': kind, 'name': unit_name(u), 'tile': ch.app(u['at'])}
    carried = [item_name(i) for i, _ in u['items']]
    drops = [item_name(i) for i, d in u['items'] if d and not i.endswith('_FALSE')]
    e['note'] = f"Lv {u['level']} {u['job']['name']}" + (': ' + ', '.join(carried) if carried else '')
    if u['team'] == 1 and carried:
        modes = mode_words(u, ch.tier)
        if modes:
            e['note'] += f' ({modes})'
    if carried:
        e['carries'] = carried
    if drops:
        e['drops'] = drops
    return e


def gaiden_condition(ch, number):
    """When a chapter's end opens its gaiden chapter, read from its Ending's checks: the count of your units against a number
    (ForceGetCountAllPlayerUnit, then '<'), or (Chapter 24) the army holding an item (AllianceCheckItem) or a person
    (ForceUnitCheckPID), either of which keeps the story on its main path."""
    ops = ch.s.disasm(named(ch.s, 'Ending'))
    for k, (_, op, v) in enumerate(ops):
        if op == 'call' and v[0] == 'ForceGetCountAllPlayerUnit':
            limit = next(x for _, o, x in ops[k:] if o == 'int')
            return f'Opens if {limit - 1} or fewer of your units are alive at the end of Chapter {number}.'
    item = next((ops[k - 1][2] for k, (_, op, v) in enumerate(ops) if op == 'call' and v[0] == 'AllianceCheckItem'), None)
    who = next((ops[k - 1][2] for k, (_, op, v) in enumerate(ops) if op == 'call' and v[0] == 'ForceUnitCheckPID'), None)
    if item and who:
        return (f'Opens if Chapter {number} ends with neither the {item_name(item)} nor {person_name(who)} in your army (without '
                f'either, the story goes this way).')
    return None


def arrival_words(when):
    """[(first turn, last turn, phase)] -> 'Turns 6, 8 and 10, enemy phase'. A first turn of 0 runs every turn (its script decides)."""
    phases = {p for _, _, p in when}
    parts = []
    for first, last, _ in sorted(when):
        if not first:
            parts.append('every turn')
        elif first == last:
            parts.append(str(first))
        else:
            parts.append(f'{first}-{last}')
    words = parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]
    many = len(parts) > 1 or '-' in parts[0]
    head = words[0].upper() + words[1:] if words.startswith('every') else ('Turns ' if many else 'Turn ') + words
    return head + (', enemy phase' if phases == {1} else ', player phase' if phases == {0} else '')


def main():
    titles = D.chapters()
    groups_by = GROUPS
    b = D.db()
    wins = {b.str(o): b.u8(o + 8) for _, o in D.table('MapTbl', 32, 'arena01')}
    order = PROLOGUE + [f'bmap{n:03d}' for n in range(1, 25)]
    story = []
    for key in order:
        story.append(key)
        n = int(key[4:])
        if key.startswith('bmap0') and n in AFTER:
            story.append(AFTER[n])
    story.append('bmap025')

    maps, sources, variants, used = [], defaultdict(list), {}, {}
    names_seen = defaultdict(lambda: defaultdict(int))

    def source(iid, mid, kind, text):
        if iid.endswith('_FALSE'):
            return  # a double's false copy is never yours
        name = item_name(iid)
        e = {'mapId': mid, 'kind': kind, 'text': text}
        if e not in sources[name]:
            sources[name].append(e)

    joined = set()
    for key in story:
        ch = Chapter(key)
        title = titles[key]
        if key in PROLOGUE:
            mid, chapter, heading, short = f'fe11-p{PROLOGUE.index(key) + 1}', PROLOGUE.index(key) + 1, 'Prologue', title
        elif key in GAIDEN:
            mid, chapter, heading = f'fe11-{GAIDEN[key]}', int(GAIDEN[key][:-1]), None
        elif key == 'bmap025':
            mid, chapter, heading = 'fe11-final', 25, 'Endgame'
        else:
            mid, chapter, heading = f'fe11-{int(key[4:])}', int(key[4:]), None
        name = re.sub(r'^(Ch\. \w+|Endgame) - ', '', title)
        m = {'id': mid, 'route': 'Story', 'chapter': chapter, 'title': name, 'width': ch.w, 'height': ch.h, 'grid': [],
             'victory': WIN.get(wins.get(key), 'Seize'), 'defeat': 'Marth is defeated', 'units': [], 'starts': [], 'objects': [],
             'objectives': [], 'changes': [], 'notes': [], 'lord': 'Marth'}
        if heading:
            m['heading'] = heading

        # Who stands where as the chapter starts: MapBegin's groups and the opening scene's, played out (scenes move units).
        begin, opening = named(ch.s, 'MapBegin'), named(ch.s, 'Opening')
        placed = play(ch, [begin, opening])
        starting_foes = []
        if not begin:
            for g in ('mikata', 'first'):
                if not any(pg == g for pg, _, _, _ in placed):
                    placed += [(g, u, tuple(u['at']), []) for u in ch.groups.get(g, [])]
        alternatives = {}
        for g, u, at, conds in placed:
            u = {**u, 'at': at}
            when = '; '.join(('if ' if on else 'unless ') + FLAG_WORDS.get(flag, flag) for flag, on in conds)
            if g.startswith('mikata'):
                if not ch.inside(u['at']):
                    continue
                if u['person']['pid'] == 'PID_MARS':
                    m['corrinStart'] = ch.app(u['at'])
                deploy = g in ('mikata', 'mikata1', 'mikata2', 'mikata3')
                if deploy:
                    m['starts'].append(ch.app(u['at']))
                elif conds:
                    # One of two units the opening places by a story flag (the Endgame: Nagi if Chapter 24x was played, else Gotoh).
                    alternatives.setdefault(tuple(u['at']), []).append((conds[0][1], unit_name(u), conds[0][0]))
                else:
                    m.setdefault('forced', []).append({'name': unit_name(u), 'tile': ch.app(u['at'])})
                who = u['person']['pid']
                # A unit's items are a source where it first joins: a deployment slot's only in the first chapter it appears in. On
                # the Hard modes (no prologue) Chapter 1's army joins there, so its kit counts there too.
                if (who not in joined or key == 'bmap001') and (not deploy or key in (order[0], 'bmap001')):
                    for iid, _ in u['items']:
                        source(iid, mid, 'kit', f"Carried by {unit_name(u)} on joining" + (f' ({when})' if when else ''))
                    joined.add(who)
                continue
            if re.match(r'e\d|ev', g) or not ch.inside(u['at']) or u['team'] == 0:
                continue
            kind = 'boss' if u['flags'] & BOSS else 'named' if u['person']['named'] else 'enemy'
            if u['team'] == 2:
                kind = 'ally'
            e = unit_entry(ch, u, kind)
            m['units'].append(e)
            starting_foes.append(u)
        for at, alts in alternatives.items():
            unset = next((n for on, n, _ in alts if not on), None)
            sets = [(n, f) for on, n, f in alts if on]
            name = unset + ''.join(f' ({n} if {FLAG_WORDS.get(f, f)})' for n, f in sets) if unset else ' or '.join(n for n, _ in sets)
            m.setdefault('forced', []).append({'name': name, 'tile': ch.app(at)})

        # Area triggers (x1, y1, x2, y2, side): entering one sets flags the turn handlers check, or places a group itself.
        def rect(a):
            x1, y1, x2, y2 = (max(1, min(v, lim)) for v, lim in zip(a[:4], (ch.w, ch.h, ch.w, ch.h)))
            return [x1, ch.h + 1 - y2, x2, ch.h + 1 - y1]
        flag_areas, area_groups = defaultdict(list), []
        # Where each group's units stand once the handler that places it has run (a group warped in from off the map: Chapter 23's
        # z02; a scene's actor placed and taken off again in one handler, Prologue IV's e02, is never one).
        arrived = {}

        def place(h):
            # The groups a handler places, each kept as the first handler to place it leaves it.
            got = defaultdict(list)
            for g, u, at, _ in play(ch, [h]):
                got[g].append((u, at))
            for g, units in got.items():
                arrived.setdefault(g, units)
            return list(got)

        for h in ch.s.handlers():
            if trigger(ch.s, h) != AREA:
                continue
            area = {'who': 'enemy' if h['args'][4] == 1 else 'player', 'rect': rect(h['args'])}
            for fn, a in ch.s.calls(h):
                if fn == 'FlagSet' and a and isinstance(a[0], str):
                    flag_areas[a[0]].append(area)
            for g in place(h):
                area_groups.append((g, area))

        # Reinforcements: turn handlers placing a group; a group a handler places on several turns is one group with its turns, and the
        # areas whose flags the handler checks.
        turns, areas = defaultdict(list), defaultdict(list)
        for h in ch.s.handlers():
            if trigger(ch.s, h) not in TURNS:
                continue
            first, last, phase = h['args'][:3]
            checks = [a[0] for fn, a in ch.s.calls(h) if fn == 'FlagGet' and a and isinstance(a[0], str)]
            for g in place(h):
                turns[g].append((first, last, phase))
                for f in checks:
                    for area in flag_areas.get(f, []):
                        if area not in areas[g]:
                            areas[g].append(area)
        for g, area in area_groups:
            areas[g].append(area)
        reinf = []
        for g in list(dict.fromkeys(list(turns) + [g for g, _ in area_groups])):
            units = []
            for u, at in arrived.get(g, []):
                if not ch.inside(at) or u['team'] == 0:
                    continue
                u = {**u, 'at': at}
                e = unit_entry(ch, u, 'boss' if u['flags'] & BOSS else 'named' if u['person']['named'] else 'enemy')
                e['from'] = ch.app(u['from']) if ch.inside(u['from']) else e['tile']
                units.append(e)
                for iid, drop in u['items']:
                    source(iid, mid, 'drop-later' if drop else 'foe-later', ('Dropped by ' if drop else 'Carried by ') + (
                        e['name'] if u['person']['named'] else f"a foe {e['name']}"))
            if not units:
                continue
            r = {'id': f'{mid}-{g}', 'label': g, 'units': units}
            if turns.get(g):
                r['when'] = arrival_words(turns[g]) + (' once an area below is entered' if areas.get(g) else '')
            else:
                r['when'] = 'When a unit enters the area below' if len(areas[g]) == 1 else 'When a unit enters an area below'
            if areas.get(g):
                r['areas'] = areas[g]
            reinf.append(r)
        # Groups go by number: a zNN group keeps its own, the others (an opening's foes an area brings, Prologue IV's Knights) take
        # the next ones in the order they come.
        taken = {int(r['label'][1:]) for r in reinf if re.fullmatch(r'z\d+', r['label'])}
        nxt = max(taken, default=0)
        for r in reinf:
            if re.fullmatch(r'z\d+', r['label']):
                r['label'] = f"Group {int(r['label'][1:])}"
            else:
                nxt += 1
                r['label'] = f'Group {nxt}'
        reinf.sort(key=lambda r: int(r['label'].split()[1]))
        if reinf:
            m['reinforcements'] = reinf

        # Talks that recruit: the unit a talk handler hands to your army (UnitTransfar), and who talks to it (one or more talks).
        talkers = defaultdict(list)
        for h in ch.s.handlers():
            if trigger(ch.s, h) != TALK:
                continue
            a, b2 = (ch.s.string(v) for v in h['args'][:2])
            calls = ch.s.calls(h)
            got = [x[0] for fn, x in calls if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and x]
            if not any(fn == 'UnitTransfar' for fn, _ in calls) or not got:
                continue
            talker = person_name(b2 if got[0] == a else a)
            if talker not in talkers[got[0]]:
                talkers[got[0]].append(talker)
        for e, u in zip(m['units'], starting_foes):
            who = u['person']['pid']
            if who in talkers:
                e['type'] = 'named'
                e['talk'] = 'Recruit: talk with ' + ' or '.join(talkers[who])
                e.pop('drops', None)
                if who not in joined:
                    for iid, _ in u['items']:
                        source(iid, mid, 'kit', f"Carried by {unit_name(u)} on joining")
                    joined.add(who)

        # What the starting foes carry and drop (a recruit's items are yours instead, above).
        for e, u in zip(m['units'], starting_foes):
            if e.get('talk'):
                continue
            for iid, drop in u['items']:
                source(iid, mid, 'drop' if drop else 'foe', ('Dropped by ' if drop else 'Carried by ') + (
                    e['name'] if u['person']['named'] else f"a foe {e['name']}"))

        # Tiles.
        if ch.ter:
            for h in ch.ter.handlers():
                if len(h['args']) < 3:
                    continue
                x, y, kind = h['args'][:3]
                tile = ch.app((x, y))
                calls = ch.ter.calls(h)
                if kind == CHEST:
                    for fn, a in calls:
                        if fn == 'TreasureGet' and a and a[0]:
                            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': item_name(a[0])})
                            source(a[0], mid, 'chest', 'In a chest')
                elif kind == VILLAGE:
                    reward = []
                    for g in groups_placed(ch.ter, h):
                        # A recruit walks out of the village (Wrys in Chapter 1).
                        for u in ch.groups.get(g, []):
                            who = unit_name(u)
                            reward.append(f'{who} joins')
                            m.setdefault('joiners', []).append({'name': who, 'tile': ch.app(u['at']), 'from': tile, 'group': g,
                                                                'when': f'Joins when a unit visits the village at ({tile[0]}, {tile[1]})'})
                            if u['person']['pid'] not in joined:
                                for iid, _ in u['items']:
                                    source(iid, mid, 'kit', f'Carried by {who} on joining')
                                joined.add(u['person']['pid'])
                    for fn, a in calls:
                        if fn == 'ItemGet' and len(a) > 1 and a[1]:
                            reward.append(item_name(a[1]))
                            source(a[1], mid, 'village', 'Given at a village')
                        elif fn == 'MoneyGet' and a:
                            reward.append(f'{a[0]} gold')
                    m['objects'].append({'type': 'village', 'tile': tile, 'reward': ', '.join(reward)})
                elif kind in (ARMORY, VENDOR, SECRET):
                    stock = []
                    for fn, a in calls:
                        if fn in ('Goods', 'GoodsLimit') and a and a[0]:
                            stock.append(item_name(a[0]))
                            where = {ARMORY: 'the armory', VENDOR: 'the vendor', SECRET: 'the secret shop, with a VIP Card'}[kind]
                            source(a[0], mid, 'shop', f'Sold at {where}' + (' (limited stock)' if fn == 'GoodsLimit' else ''))
                    label = {ARMORY: 'Armory', VENDOR: 'Vendor', SECRET: 'Secret shop'}[kind]
                    m['objects'].append({'type': 'shop', 'tile': tile, 'kind': label, 'stock': stock})
                elif kind == SEIZE:
                    m['objectives'].append({'type': 'seize', 'tiles': [tile], 'label': 'Seize with Marth'})

        # The Hard modes: the prologue isn't played on them; elsewhere foes gain growth (arm9 0x203a250) and their weapons change.
        if key in PROLOGUE:
            m['notes'].append("Played on Normal only: the Hard modes start at Chapter 1 (the game's mode descriptions: \"No prologue "
                              'is included").')
        else:
            lv = ch.levels
            m['notes'].append(f"Hard modes: foes the game levels gain {lv} levels' worth of growth for each mode above Normal (Hard {lv}, "
                              f'Brutal {2 * lv}, Savage {3 * lv}, Fiendish {4 * lv}, Merciless {5 * lv}) in HP, Str, Mag, Skl, Spd and '
                              'Lck, not Def or Res; their shown level stays the same. Weapons a mode changes are named on each foe.')

        # A gaiden chapter: what opens it, from the end of the chapter before.
        if key in GAIDEN:
            before = next(k for k, v in AFTER.items() if v == key)
            note = gaiden_condition(Chapter(f'bmap{before:03d}'), before)
            if note:
                m['notes'].append(note)

        # Terrain codes: each code's stats are one set in every map (checked), its names the game's per tile.
        rows = []
        used[mid] = defaultdict(lambda: defaultdict(list))
        for y in range(1, ch.h + 1):
            line = []
            for x in range(1, ch.w + 1):
                t = ch.ids[y][x]
                info = tile_info(t)
                code = encode(GAME, letter_of(t))
                line.append(code)
                stats = {k: v for k, v in info.items() if k != 'name'}
                assert variants.setdefault(code, stats) == stats, (mid, code, info)
                names_seen[code][info['name']] += 1
                used[mid][code][info['name']].append(ch.app((x, y)))
            rows.append(''.join(line))
        m['grid'] = rows
        maps.append(m)
        print(mid, m['title'], f'{ch.w}x{ch.h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    # One entry per code, named by its most common name; a map whose tiles of a code have other names says them ('Floor / Plain', and
    # each tile's own name), as the tile panel and the legend show.
    info = {code: {'name': max(names_seen[code], key=names_seen[code].get), **stats} for code, stats in variants.items()}
    for m in maps:
        over = {}
        for code, names in used[m['id']].items():
            order = sorted(names, key=lambda k: (-len(names[k]), k))
            if order == [info[code]['name']]:
                continue
            over[code] = {'name': ' / '.join(order), **({'tileNames': {k: names[k] for k in order[1:]}} if len(order) > 1 else {})}
        if over:
            m['terrainOverrides'] = over
    classes = {g: g for g, _ in groups_by}
    gm.write_terrain(GAME, TITLE, SCRIPT, info, [(g, [g], None) for g, _ in groups_by], classes)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()
