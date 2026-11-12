"""
New Mystery of the Emblem's maps and where each item turns up, from the game's own files (data-raw/fe12/README.md): each chapter's
grid (map/<chapter>), its placements (dispos/<chapter>), its scripts (script/<chapter>.cmb, script/<chapter>_ter.cmb) and the
database, named by the translation patch (scripts/fe12_names.py). The engine is Shadow Dragon's (scripts/build-fe11-maps.py), with
its numbers moved. Writes src/data/fe12/fe12Terrain.ts, fe12Maps.ts and fe12ItemSources.ts.

- The story: Prologue I-VIII (bmap201-208; IV, VI and VII each have a second version, bmap204B, 206B and 207B, which the answer at the
  end of the chapter before picks), then Chapters 1-23 (bmap001-023) with each gaiden chapter (bmap103-120: 3x, 6x, 10x, 13x, 16x, 20x)
  where it comes, then the Endgame (bmap024). Outside the story: the four Archanean Chronicles episodes (bmap301-304) and the three
  downloadable chapters (dl001-003, whose placements, scripts and text are on the cartridge under scrambled names, fe12_data.DLC_FILES).
- A map's grid: the map file's first 32 x 32 grid (TerrainData ids), its width and height from the header (+0xc, +0xd).
- Units: a placement file's groups ([name, records, count]); 88-byte records: +0 person, +2 class, +4 x, y (where it enters), +6 x, y
  (where it stands), +8 team (0 yours, 1 enemy, 2 other), +9 level, +0x10 its five items (u16 item, u16 flags: 0x01 it drops),
  +0x2c u32 flags, +0x30-+0x3c its AI's four routines, +0x40-+0x4c their parameters. `MapBegin` places 'mikata' (your deployment
  slots) and 'first' (the foes); the opening scene places more; groups named e01 / ev... are the scenes' actors. A turn handler (type
  0x03 or 0x17: first turn, last turn, phase) placing a group is a reinforcement.
- Handlers: 0x04 an area (x1, y1, x2, y2, whose unit, flag), 0x08 a talk, 0x09 a battle talk, 0x0b a death, 0x18 a hidden treasure (an
  area where a unit that stops finds an item: ItemGet).
- Tiles: a terrain script's handlers (x, y, kind): 5 a door, 6 a chest (TreasureGet, TreasureMoneyGet), 7 and 8 a drawbridge, 9 a
  village (ItemGet, MoneyGet, or a recruit walking out: DisposPlayArea), 10 a house, 11 an armory and 12 a vendor (Goods), 13 a
  secret shop (a VIP Card; GoodsLimit: each item a limited stock), 15 the tile to seize.

    python scripts/build-fe12-maps.py
"""
import json
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe12_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from fe11_cmb import Script  # noqa: E402
from fe12_names import say  # noqa: E402
from fe13_bin import Bin  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe12', 'New Mystery of the Emblem', 'build-fe12-maps.py'
ROM = D.ROM

PROLOGUE = ['bmap201', 'bmap202', 'bmap203', 'bmap204', 'bmap205', 'bmap206', 'bmap207', 'bmap208']
# The prologue's second versions: the answer at the end of the chapter before picks one (data-raw/fe12/README.md).
SECOND = {'bmap204': 'bmap204B', 'bmap206': 'bmap206B', 'bmap207': 'bmap207B'}
GAIDEN = {'bmap103': '3x', 'bmap106': '6x', 'bmap110': '10x', 'bmap113': '13x', 'bmap116': '16x', 'bmap120': '20x'}
AFTER = {3: 'bmap103', 6: 'bmap106', 10: 'bmap110', 13: 'bmap113', 16: 'bmap116', 20: 'bmap120'}
ENDGAME = 'bmap024'
# Outside the story: the Archanean Chronicles' four episodes and the three downloadable chapters.
CHRONICLES = ['bmap301', 'bmap302', 'bmap303', 'bmap304']
DLC = ['dl001', 'dl002', 'dl003']

# Terrain ids (the database's TerrainData table, by its name label) -> a letter. Each letter's code: GAME['fe12'] in terrain_codes.py.
# A cave plays as a mountain and bones as a plain (their numbers and costs are the same), so they share their codes.
LETTER = {
    'MS_TER_NOMOVE': '#', 'MS_TER_PLAIN': '.', 'MS_TER_VILLAGE': 'v', 'MS_TER_HOUSE': 'B', 'MS_TER_FORT': 'F',
    'MS_TER_CASTLEGATE': 'g', 'MS_TER_GROVE': 'f', 'MS_TER_DESERT': 's', 'MS_TER_RIVER': 'w', 'MS_TER_MOUNTAIN': 'm',
    'MS_TER_ALP': 'P', 'MS_TER_BRIDGE': 'b', 'MS_TER_SEA': 'a', 'MS_TER_FLOOR': 'O', 'MS_TER_WALL': '#', 'MS_TER_COLUMN': 'p',
    'MS_TER_STEP': 'S', 'MS_TER_STONEWALL': 'C', 'MS_TER_CASTLE': 'N', 'MS_TER_FENSE': 'l', 'MS_TER_WEAPON': 'A',
    'MS_TER_ITEM': 'V', 'MS_TER_COLISSEUM': 'R', 'MS_TER_CHECKROOM': 'U', 'MS_TER_TREASUREBOX': 'c', 'MS_TER_THRONE': 't',
    'MS_TER_DOOR': 'd', 'MS_TER_DRAWBRIDGE': 'Z', 'MS_TER_LAVA': 'M', 'MS_TER_CLOSEVILLAGE': 'X', 'MS_TER_DESTROYVILLAGE': 'r',
    'MS_TER_CAVE': 'm', 'MS_TER_BONE': '.', 'MS_TER_COLOSSEUM': 'R', 'MS_TER_ALTER': 'H',
}
DOOR, CHEST, VILLAGE, HOUSE, ARMORY, VENDOR, SECRET, SEIZE = 5, 6, 9, 10, 11, 12, 13, 15
DRAWBRIDGES = (7, 8)
DRAWBRIDGE = 7
TURN, AREA, TALK, HIDDEN = 0x17, 0x04, 0x08, 0x18
TURNS = (0x17, 0x03)  # both a turn's handler: (first turn, last turn, phase)
DEATH = 0x0b
# A unit handed over to your army (Shadow Dragon spelt it UnitTransfar; UnitTransferDefection only in Prologue VIII's ChapterNext).
TRANSFER = ('UnitTransfer', 'UnitTransferDefection')
# MapTableData +0x15: 0x01 seize, 0x02 rout, 0x04 defeat the boss, 0x08 a person reaching a tile (Archanean Chronicles 4: Nyna).
WIN = {1: 'Seize', 2: 'Rout the enemy', 4: 'Defeat the boss', 8: 'Arrive'}
BOSS = 0x100


# ---------------------------------------------------------------------------------------------------------------------------------
# Files

def mapfile(key):
    b = Bin(open(os.path.join(ROM, 'map', key), 'rb').read())
    w, h = b.d[0x20 + 0xc], b.d[0x20 + 0xd]
    g = b.u32(0x10)
    return w, h, [[b.d[0x20 + g + y * 32 + x] for x in range(w)] for y in range(h)]


def rooms_of(key):
    """{(x, y): room id} from the map file's room grid (+0x14: 32 x 32, 0 none). The map's loader closes every room as it loads
    (overlay 00 0x21a2834 sets bit 0x80 on its tiles), and a closed room is barred to every unit, fliers included (the move range,
    arm9 0x20e401c), until a door into it opens or a script opens its roof."""
    b = Bin(open(os.path.join(ROM, 'map', key), 'rb').read())
    if 0x14 not in b.ptrs:
        return {}
    p = b.u32(0x14)
    return {(x, y): b.d[0x20 + p + y * 32 + x] for y in range(32) for x in range(32) if b.d[0x20 + p + y * 32 + x]}


def dispos(key):
    """{group: [unit]} from a placement file."""
    b = Bin(open(os.path.join(ROM, 'dispos', D.DLC_FILES.get(key, key)), 'rb').read())
    P, J, I = D.persons(), D.jobs(), D.items()
    out, o = {}, 0
    while True:
        n, rec, cnt = struct.unpack_from('<3I', b.d, 0x20 + o)
        if not n and not rec:
            return out
        units = []
        for k in range(cnt):
            r = b.d[0x20 + rec + k * 88:0x20 + rec + k * 88 + 88]
            p, j = struct.unpack_from('<HH', r, 0)
            items = []
            for s in range(0x10, 0x24, 4):
                item, iflags = struct.unpack_from('<HH', r, s)
                if item:
                    items.append((I[item]['iid'], bool(iflags & 1), iflags))
            # (0, 0) for where it stands: it stays where it enters.
            at = (r[6], r[7]) if r[6] or r[7] else (r[4], r[5])
            # +0x30-+0x3c: its AI's four routines (action, mind, attack, move: cpu/database names each), +0x40-+0x4c their parameters.
            base = rec + k * 88
            units.append({'person': P[p], 'job': J[j], 'from': (r[4], r[5]), 'at': at, 'team': r[8], 'level': r[9],
                          'hard_level': r[0xa], 'items': items, 'flags': struct.unpack_from('<I', r, 0x2c)[0],
                          'ai': [b.str(base + o) if base + o in b.ptrs else None for o in (0x30, 0x34, 0x38, 0x3c)],
                          'ai_params': [b.str(base + o) if base + o in b.ptrs else None for o in (0x40, 0x44, 0x48, 0x4c)]})
        out[b.cstr(0x20 + n)] = units
        o += 12


def script(key):
    path = os.path.join(ROM, 'script', D.DLC_FILES.get(key, key) + '.cmb')
    return Script(path) if os.path.exists(path) else None


def trigger(s, h):
    return struct.unpack_from('<I', s.d, s.offs[h['index']] + 0xc)[0] & 0xFFFF


def named(s, name):
    return next((h for h in s.handlers() if h['name'] == name), None)


# A story flag a placement waits on, in words.
FLAG_WORDS = {'gf_２４章外伝を通る': 'Chapter 24x was played'}


HARD_OPS = {'op2f': lambda a, b: a == b, 'op30': lambda a, b: a != b, 'op31': lambda a, b: a < b, 'op32': lambda a, b: a <= b,
            'op33': lambda a, b: a > b, 'op34': lambda a, b: a >= b}


def hard_regions(ops):
    """[(start, end, test)]: code that runs only when the save's difficulty (GetHard(): 0 Normal, 3 Hard, 4 Maniac, 5 Lunatic) passes a
    comparison: an if's body (from after its jz to the jump's target) under the test, and its else (from the target to where the
    body's last jmp goes) under the test's opposite."""
    out = []
    for k, (pc, op, v) in enumerate(ops[:-4]):
        if not (op == 'call' and v[0] == 'GetHard' and ops[k + 1][1] == 'int' and ops[k + 2][1] in HARD_OPS and ops[k + 3][1] == 'jz'):
            continue
        n, cmp_, target = ops[k + 1][2], HARD_OPS[ops[k + 2][1]], ops[k + 3][2]

        def test(d, n=n, c=cmp_):
            return c(d, n)
        out.append((ops[k + 4][0], target, test))
        before = [q for q in ops if q[0] < target]
        if before and before[-1][1] == 'jmp' and before[-1][2] > target:
            out.append((target, before[-1][2], lambda d, t=test: not t(d)))
    return out


def play(ch, handlers, mode=None):
    """Play the scenes that set the map up (MapBegin, then the opening), the way the engine does, straight through: each Dispos places
    a group's units where its records stand them, a unit fetched into a local (UnitGetByPID, UnitGetByPos, UnitGetHero) is moved by
    UnitMovePos / UnitMovePosEx / UnitSetPos / UnitWarpAppearance and taken off by UnitRemove*; UnitStackPush saves every unit and
    UnitStackPop puts them back as they were (arm9 0x20451ec / 0x20451fc: overlay 00 0x21a323c / 0x21a32c8), undoing what the scene
    moved in between; a 0x37 runs another handler of the script. Both sides of a story flag's check run (FlagGet of a gf_ flag, then
    jz), each placement tagged with the side it's on. With a mode, code a check of the difficulty (GetHard) keeps from it is skipped;
    a map loaded over the first (MapLoadD: Prologue I's scene in the castle, then the training ground) takes its units away. Returns
    [(group, unit, tile, conditions)] for what stands at the end, a condition being (flag, True if set)."""
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
        skip = hard_regions(ops) if mode else []
        for k, (pc, op, v) in enumerate(ops):
            if any(start <= pc < end and not test(MODE_VALUE[mode]) for start, end, test in skip):
                continue
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
                elif fn == 'MapLoadD' and placed:
                    placed.clear()
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
            elif op == 'jnz':
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
            elif op == 'dup':
                stack.append(stack[-1] if stack else None)
            elif op == 'dupderef':
                stack.append(None)
            elif op == 'inc':
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
    for _, o in D.table('TerrainData', 36, (b.at['TerrainCategory'] - b.at['TerrainData']) // 36):
        cat = b.u32(o + 4)
        avo, df, _, heal = (b.u8(cat + i) for i in range(4))
        out.append((b.str(o), avo if avo < 0x80 else avo - 0x100, df, heal, (cat - cat0) // 4))
    return out


def cost_rows():
    b = D.db()
    start = b.at['TerrainCost'] + 4
    rows = b.u32(b.at['TerrainCost'])
    cols = (b.at['WeaponLevel'] - start) // rows
    return [[b.u8(start + r * cols + c) for c in range(cols)] for r in range(rows)]


TERRAIN = terrain_rows()
COSTS = cost_rows()
# The translation's names (fe12_names), but where one name covers tiles that work differently: '----' (no unit's tile), the raised
# drawbridge (the game's "Bridge", as it is once lowered), and a village closed or razed.
NAMES = {'MS_TER_NOMOVE': 'Out of bounds', 'MS_TER_DRAWBRIDGE': 'Drawbridge', 'MS_TER_CLOSEVILLAGE': 'Village (closed)',
         'MS_TER_DESTROYVILLAGE': 'Ruins'}
# Tiles only the lord can't enter: the game's categories 25-29 (a plain, floor, forest, fort and mountain whose cost column bars the
# Lord's row alone: reinforcements' entry tiles in Chapters 9 and 12x), each kind a code of its own.
LORD_ONLY = {'MS_TER_PLAIN': 'Q', 'MS_TER_FLOOR': 'Q', 'MS_TER_GROVE': 'K', 'MS_TER_FORT': 'J', 'MS_TER_MOUNTAIN': 'Y'}


def used_jobs():
    """The classes some placement in a played map uses."""
    keys = PROLOGUE + [f'bmap{n:03d}' for n in range(1, 25)] + list(GAIDEN) + CHRONICLES + DLC
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
    name = (NAMES.get(label) or say(label) or label) + (" (the lord can't enter)" if letter_of(t) in LORD_ONLY.values() else '')
    return {'name': name, 'def': df, 'avo': avo, 'heal': heal, 'move': move}


# ---------------------------------------------------------------------------------------------------------------------------------
# One chapter

class Chapter:
    """A chapter's files. Every grid has a one-tile border no unit enters (the wiki's sizes are the files' less 2 each way): the map
    is the tiles inside it, from (1, 1) at the bottom left."""
    def __init__(self, key):
        self.key = key
        _, shared, _, self.rec = next(m for m in D.maps() if m[0] == key)
        # The prologue's second versions share their chapter's grid and placements (MapTableData +4), with scripts of their own.
        self.file = shared or key
        w, h, self.ids = mapfile(self.file)
        self.w, self.h = w - 2, h - 2
        self.groups = dispos(self.file)
        # MapTableData +0x16: the levels of growth each mode's k counts; +0x17: the modes' weapon tier; +0x18: the battle
        # preparations' menus (0x04: the armory and its forge).
        self.levels, self.tier, self.prep = self.rec[0x16], self.rec[0x17], self.rec[0x18]
        self.s = script(key)
        self.ter = script(key + '_ter')
        self.rooms = rooms_of(self.file)

    def app(self, xy):
        x, y = xy
        return [x, self.h + 1 - y]

    def inside(self, xy):
        return 1 <= xy[0] <= self.w and 1 <= xy[1] <= self.h


AVATAR = 'PID_PLAYER'


def unit_name(u):
    p, j = u['person'], u['job']
    if p['pid'] == AVATAR:
        return 'Avatar'
    return (p['name'] if p['named'] else None) or j['name']


def person_name(pid):
    if pid == AVATAR:
        return 'the Avatar'
    p = next((p for p in D.persons() if p['pid'] == pid), None)
    return (p['name'] if p else None) or pid


def item_name(iid):
    """An item's name; a false copy (IID_MAFU_FALSE, IID_FALCHION_FALSE: what Chapter 23's doubles of Gharnef carry) says so, and
    the weaker Falchion Chapter 24x's end gives (IID_FALCHION_TINY: Mt 7, Hit 90, Wt 9) is an item of its own, "Falchion (24x)"."""
    it = next(i for i in D.items() if i['iid'] == iid)
    return it['name'] + (' (false)' if iid.endswith('_FALSE') else ' (24x)' if iid.endswith('_TINY') else '')


MODES = ['Normal', 'Hard', 'Maniac', 'Lunatic', 'Reverse Lunatic']
# Each mode's value in the save (+0x1a9; overlay 15, the mode menu): Reverse Lunatic is Lunatic's 5 with the global flag 0x400000.
MODE_VALUE = {'Normal': 0, 'Hard': 3, 'Maniac': 4, 'Lunatic': 5, 'Reverse Lunatic': 5}
# The foe builder (arm9 0x204c45c, as a placement makes its unit): a placement with +0x2c 0x10 (most generic foes) or 0x100 (bosses)
# gains each mode's levels of growth, k x MapTableData +0x16 (0x204c75c: k is Hard 2, Maniac 4, Lunatic 5), in HP, Str, Mag, Skl, Spd
# and Lck (Def and Res only by a person's own growths for the modes, Person +0x1c), its shown level unchanged; its weapon ranks are
# raised to C, B or A (0x204c8a8); and its weapons step up (0x204c974): the tier T is MapTableData +0x17 less 2 on Hard, 1 on Maniac,
# held 0-4, and a weapon of a lower tier (item +0x3a 0-3) becomes its kind's weapon at T (the lists at arm9 0x20ff888), forged Mt +4,
# Hit +20 at T 3; a 0x7d weapon is forged at T 2 (Mt +4, or +8 at T 3; Hit +20), a 0x7e one at T 3 (Mt +4, Hit +20), never one with
# +0x2b 0x40; on Lunatic the 1-range breaths (0x7c) become their 1-2 range versions (the next item). A slot whose flags have 0x100
# never changes, and a dropped item only in the first slot: the foe then gets a copy of the original that still drops (0x204ffe4).
AUTOLEVEL = 0x110
LEVELS_K = {'Normal': 0, 'Hard': 2, 'Maniac': 4, 'Lunatic': 5, 'Reverse Lunatic': 5}
TIER_BY = {'Hard': -2, 'Maniac': -1, 'Lunatic': 0, 'Reverse Lunatic': 0}
RANK_FLOOR = {'Hard': 'C', 'Maniac': 'B', 'Lunatic': 'A', 'Reverse Lunatic': 'A'}
NO_CHANGE = 0x100
ARM9 = open(os.path.join(ROM, 'arm9.bin'), 'rb').read()
ARM9_AT = 0x02004000


def _arm9_u32(a):
    return struct.unpack_from('<I', ARM9, a - ARM9_AT)[0]


def _arm9_str(a):
    o = a - ARM9_AT
    return ARM9[o:ARM9.index(b'\0', o)].decode('ascii')


# The kinds' upgrade lists (arm9 0x20ff888: sword, lance, axe, bow, tome; five IIDs each, by tier).
UPGRADES = {k: [_arm9_str(_arm9_u32(_arm9_u32(0x20ff888 + 4 * k) + 4 * t)) for t in range(5)] for k in range(5)}
assert UPGRADES[0] == ['IID_IRONSWORD', 'IID_STEELSWORD', 'IID_SILVERSWORD', 'IID_SILVERSWORD', 'IID_BRAVESWORD'], UPGRADES[0]


# The difficulty gates (from the save's difficulty, +0x1a9: Normal 0, Hard 3, Maniac 4, Lunatic 5): a placement's +0x2c and an item
# slot's flags (the same bits, 8 lower) say which modes have it (overlay 00 0x2205b5c).
GATES = {0x400: lambda d: d >= 3, 0x800: lambda d: d >= 4, 0x1000: lambda d: d >= 5, 0x2000: lambda d: d < 3, 0x4000: lambda d: d < 4,
         0x8000: lambda d: d < 5}


def gated(bits, mode):
    """Whether a placement's or an item's gate bits let it on a mode."""
    return all(test(MODE_VALUE[mode]) for bit, test in GATES.items() if bits & bit)


def record_modes(u):
    """The modes a placement record is placed on."""
    return [m for m in MODES if gated(u['flags'], m)]


def prep_armory():
    """The IIDs the battle preparations' armory always sells (overlay 10 0x22304f0: each loaded from the literal pool, looked up and
    added with no limit, before the global flag 0x04, a Lunatic clear, adds the stat boosters)."""
    import capstone
    ov = open(os.path.join(ROM, 'overlay', '10_0222e6c0.bin'), 'rb').read()
    at = 0x0222e6c0
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    out = []
    for a in range(0x22304f0, 0x2230570, 4):
        i = next(md.disasm(ov[a - at:a - at + 4], a))
        if i.mnemonic == 'tst':
            break
        if i.mnemonic == 'ldr' and i.op_str.startswith('r0, [pc, #'):
            lit = struct.unpack_from('<I', ov, a + 8 + int(i.op_str.split('#')[1].rstrip(']'), 16) - at)[0]
            o = lit - at
            if 0 <= o < len(ov) and ov[o:o + 4] == b'IID_':
                out.append(ov[o:ov.index(b'\0', o)].decode('ascii'))
    assert out ==['IID_IRONSWORD', 'IID_IRONLANCE', 'IID_IRONAXE', 'IID_IRONBOW', 'IID_FIRE', 'IID_LIVE'], out
    return out


PREP_ARMORY = prep_armory()


def mode_items(u, mode, ch):
    """A unit's items on a mode: each slot's gate (its flags shifted up 8: 0x04 Hard and up... 0x80 below Lunatic), then, for a foe the
    game levels, the mode's weapons (above). Returns [(item id, name, drops)]."""
    items = [(iid, drop, iflags) for iid, drop, iflags in u['items'] if gated(iflags << 8, mode)]
    if mode == 'Normal' or u['team'] != 1 or not u['flags'] & AUTOLEVEL:
        return [(iid, item_name(iid), drop) for iid, drop, _ in items]
    I = {i['iid']: i for i in D.items()}
    by_index = D.items()
    t = max(0, min(4, ch.tier + TIER_BY[mode]))
    out, kept = [], []
    for slot, (iid, drop, iflags) in enumerate(items):
        it = I[iid]
        name = item_name(iid)
        if iflags & NO_CHANGE or it['tier'] == 0x7F or drop and slot:
            out.append((iid, name, drop))
            continue
        new, forge = iid, None
        if it['tier'] <= 3 and it['kind'] in UPGRADES and t > it['tier']:
            new = UPGRADES[it['kind']][t]
            forge = (4, 20) if t >= 3 else None
        elif it['tier'] == 0x7D and t >= 2 and not it['noforge']:
            forge = (8 if t >= 3 else 4, 20)
        elif it['tier'] == 0x7E and t >= 3 and not it['noforge']:
            forge = (4, 20)
        elif it['tier'] == 0x7C and MODE_VALUE[mode] >= 5:
            new = by_index[it['index'] + 1]['iid']
        if new == iid and not forge:
            out.append((iid, name, drop))
            continue
        out.append((new, item_name(new) + (f' (forged: Mt +{forge[0]}, Hit +{forge[1]})' if forge else ''), False))
        if drop:
            kept.append((iid, name, True))
    return out + kept


def unit_entries(ch, u, kind, modes):
    """The unit as each of its modes has it: one entry per set of items the modes give it (a slot gated to some modes), with the
    modes it holds on where that's fewer than the game's. Returns [(entry, [(item id, drops)], modes)]."""
    sets = {}
    for mode in MODES:
        if mode in modes:
            sets.setdefault(tuple(mode_items(u, mode, ch)), []).append(mode)
    out = []
    for items, ms in sets.items():
        e = {'type': kind, 'name': unit_name(u), 'tile': ch.app(u['at'])}
        carried = [n for _, n, _ in items]
        drops = [n for i, n, d in items if d and not i.endswith('_FALSE')]
        e['note'] = f"Lv {u['level']} {u['job']['name']}" + (': ' + ', '.join(carried) if carried else '')
        if carried:
            e['carries'] = carried
        if drops:
            e['drops'] = drops
        if len(ms) < len(MODES):
            e['difficulties'] = ms
        out.append((e, [(i, d) for i, _, d in items], ms))
    return out


# GetNormalizeTurn (arm9 0x2028510): a turn limit times a percentage by the save's difficulty (+0x1a9: 0 100, 1 105, 2 110, 3 120,
# 4 140, 5 160, or 180 with the global flag 0x400000, Reverse Lunatic's), rounded down.
NORMALIZE = {'Normal': 100, 'Hard': 120, 'Maniac': 140, 'Lunatic': 160, 'Reverse Lunatic': 180}
ZENKAKU = str.maketrans('0123456789', '０１２３４５６７８９')


def gaiden_condition(ch, number):
    """What opens a gaiden chapter, from the Ending of the chapter before: each FlagSet of its gf_<n>ｘ分岐 flag is one way, under the
    checks just before it. Returns (the turn limit or None, [other ways in words]): the chapter cleared by a turn (GetTurn() <=
    GetNormalizeTurn(n), scaled by difficulty), no foe having escaped (IsEnemyEscape), someone in your army (ForceUnitCheckPID on
    forces 0 and 2), so many of a list (a count of them, >=), the Avatar promoted at a level (UnitIsHighJob, UnitGetLevel), or so
    many of a chapter's own units still on the map (GetCountSamePID, kept in a local)."""
    ops = ch.s.disasm(named(ch.s, 'Ending'))
    flag = f'gf_{str(number).translate(ZENKAKU)}ｘ分岐'
    counted = {}   # a local -> the PID GetCountSamePID counted into it
    for k, (_, op, v) in enumerate(ops[:-2]):
        if op == 'addr' and ops[k + 1][1] == 'str' and ops[k + 2][1] == 'call' and ops[k + 2][2][0] == 'GetCountSamePID':
            counted[v] = ops[k + 1][2]
    turns, ways, start = None, [], 0
    for k, (_, op, v) in enumerate(ops):
        if not (op == 'call' and v[0] == 'FlagSet' and ops[k - 1][2] == flag):
            continue
        seg = ops[start:k]
        start = k + 1
        calls = [x[2][0] for x in seg if x[1] == 'call']
        if 'GetNormalizeTurn' in calls:
            i = next(i for i, x in enumerate(seg) if x[1] == 'call' and x[2][0] == 'GetNormalizeTurn')
            assert seg[i - 1][1] == 'int' and seg[i + 1][1] == 'op32', (ch.key, seg[i - 2:i + 2])
            turns = seg[i - 1][2]
            continue
        if 'IsEnemyEscape' in calls:
            assert seg[calls.index('IsEnemyEscape') + 1:] and any(x[1] == 'not' for x in seg), ch.key
            ways.append('no foe has escaped the map')
            continue
        if 'UnitIsHighJob' in calls:
            assert 'PID_PLAYER' in [x[2] for x in seg if x[1] == 'str'], ch.key
            level = next(x[2] for x in reversed(seg) if x[1] == 'int')
            ways.append(f'the Avatar is in a promoted class at level {level} or higher')
            continue
        pids = list(dict.fromkeys(x[2] for x in seg if x[1] == 'str' and x[2].startswith('PID_')))
        cmp_ = [x for x in seg if x[1] in ('op34', 'op33')]
        if pids and 'ForceUnitCheckPID' in calls and not cmp_:
            assert len(pids) == 1, (ch.key, pids)
            ways.append(f'{person_name(pids[0])} is in your army')
            continue
        if pids and 'ForceUnitCheckPID' in calls:
            n = next(x[2] for x in reversed(seg) if x[1] == 'int')
            names = [person_name(p) for p in pids]
            ways.append(f"at least {n} of {', '.join(names[:-1])} and {names[-1]} are in your army")
            continue
        loc = next((x[2] for x in seg if x[1] == 'local' and x[2] in counted), None)
        if loc is not None and cmp_:
            n = next(x[2] for x in reversed(seg) if x[1] == 'int')
            pid = counted[loc]
            units = [u for us in ch.groups.values() for u in us if u['person']['pid'] == pid]
            ways.append(f"at least {n} of the {len(units)} foe {units[0]['job']['name']}s are still on the map")
            continue
        raise AssertionError((ch.key, seg[-12:]))
    return turns, ways


def guarded_calls(s, h):
    """[(pc, function, arguments, conditions)]: each call a handler makes, with the conditions its code runs under, read from the
    branches around it: ('flag', name, True if it must be set), ('lt', value, n) for ValueGet(value) < n, ('army', side, n) for
    ForceGetCount(side) == n (0x2f, ==: Prologue IV's door opens once "all but the prince have been slain", MS204_EV8_6). A jz's
    condition covers the code up to its target; the 'and' jumps before it add theirs, an 'and' that lands on another passing them on
    (Chapter 7's area: the boss alive and the counter below 3)."""
    ops = s.disasm(h)
    stack, regions, ands, out = [], [], defaultdict(list), []
    for k, (pc, op, v) in enumerate(ops):
        nxt = ops[k + 1][0] if k + 1 < len(ops) else pc + 1
        active = [c for a, b, cs in regions if a <= pc < b for c in cs]
        if op in ('int', 'str'):
            stack.append(v)
        elif op == 'call':
            fn, argc = v
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            out.append((pc, fn, args, active))
            if fn == 'FlagGet' and args and isinstance(args[0], str):
                stack.append(('flag', args[0], True))
            elif fn == 'ValueGet' and args and isinstance(args[0], str):
                stack.append(('val', args[0]))
            elif fn == 'ForceGetCount' and args and isinstance(args[0], int):
                stack.append(('count', args[0]))
            elif fn == 'TTIsEnable' and len(args) > 2 and all(isinstance(v, int) for v in args[:3]):
                # A tile still in its first state (a village not yet visited, a door shut): ('tt', (x, y), kind, True).
                stack.append(('tt', (args[0], args[1]), args[2], True))
            elif fn in ('UnitSafetyGetByPos', 'UnitGetByPos') and len(args) == 2 and all(isinstance(v, int) for v in args):
                stack.append(('unit_at', (args[0], args[1]), True))
            else:
                stack.append(None)
        elif op == 'not':
            x = stack.pop() if stack else None
            stack.append(('flag', x[1], not x[2]) if isinstance(x, tuple) and x[0] == 'flag' else
                         x[:-1] + (not x[-1],) if isinstance(x, tuple) and x[0] in ('tt', 'unit_at') else None)
        elif op == 'op31':
            b = stack.pop() if stack else None
            a = stack.pop() if stack else None
            stack.append(('lt', a[1], b) if isinstance(a, tuple) and a[0] == 'val' and isinstance(b, int) else None)
        elif op == 'op2f':
            b = stack.pop() if stack else None
            a = stack.pop() if stack else None
            stack.append(('army', a[1], b) if isinstance(a, tuple) and a[0] == 'count' and isinstance(b, int) else None)
        elif op == 'and':
            ands[v] += ands.pop(pc, []) + [stack.pop() if stack else None]
        elif op in ('or', 'jnz'):
            if stack:
                stack.pop()
        elif op == 'dup':
            stack.append(stack[-1] if stack else None)
        elif op == 'dupderef':
            stack.append(None)
        elif op == 'inc':
            if stack:
                stack[-1] = None
        elif op == 'jz':
            c = stack.pop() if stack else None
            conds = [x for x in ands.pop(pc, []) + [c] if isinstance(x, tuple) and x[0] in ('flag', 'lt', 'army', 'tt', 'unit_at')]
            if v > pc and conds:
                regions.append((nxt, v, conds))
        elif op in ('local', 'arg', 'addr', 'gaddr'):
            stack.append(None)
        elif op == 'assign':
            del stack[-2:]
        elif op in ('pop', 'setlocal'):
            if stack:
                stack.pop()
        elif op in ('deref', 'eaddr'):
            if stack:
                stack[-1] = None
        elif op.startswith('op'):
            if len(stack) >= 2:
                stack.pop()
            if stack:
                stack[-1] = None
    return out


BOSS_DEAD = 'ボス死亡'


def bosses(ch, seize):
    """The chapter's own boss: the person whose death handler (type 0x0b) sets ボス死亡 (Chapter 12's Volzhin, not Heimler; flag 0x100
    of a placement is only the Hard modes' growth, arm9 0x203a234); where no death sets it, the foe on the seize tile at the start,
    unless a handler takes it off the map (Chapter 15's Gharnef warps away on turn 6). Returns ({PID}, {PID a handler removes})."""
    dead = {ch.s.string(h['args'][0]) for h in ch.s.handlers() if trigger(ch.s, h) == DEATH and h['args']
            and any(fn == 'FlagSet' and a and a[0] == BOSS_DEAD for fn, a in ch.s.calls(h))}
    gone = set()
    for h in ch.s.handlers():
        if h['name'] in ('MapBegin', 'Opening'):
            continue
        calls = ch.s.calls(h)
        if any(fn.startswith('UnitRemove') or fn == 'UnitEffectWarpEscape' for fn, _ in calls):
            gone |= {a[0] for fn, a in calls if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and a and isinstance(a[0], str)}
    return dead, gone


POS = re.compile(r'pos\((\d+),(\d+)\)')


def ai_words(ch, u):
    """(words, looter, goes to, village it raids) for what a placement's AI sends a unit to do, or None where it only fights. A thief
    with CP_SP_Treasure goes for the chest at the move parameter's first tile and leaves by its second; CP_SP_Village goes for the
    village at its first tile, or the nearest, razing it, then leaves by its second or attacks; CP_SP_Talk comes to the person in its
    mind parameter to talk; CP_MV_Position heads for its tile; CP_AT_Person picks the person in its attack parameter when it attacks;
    CP_AC_Area waits for a unit in the rectangle its two tiles make, CP_AC_Attacked until it's attacked, and CP_AT_Null in the action
    slot until the chapter's script wakes it (CpuSetActive); CP_AT_Null as its attack never attacks."""
    ac, sp, at, mv = u.get('ai') or [None] * 4
    pa, ps, pt, pm = u.get('ai_params') or [None] * 4

    def tiles(p):
        return [ch.app((int(a), int(b))) for a, b in POS.findall(p or '')]

    def where(t):
        return f'({t[0]}, {t[1]})'

    quiet = ', never attacking' if at == 'CP_AT_Null' else ''
    t = tiles(pm)
    if sp == 'CP_SP_Treasure' and t:
        if len(t) > 1:
            return (f'goes for the chest at {where(t[0])}, empties it, then makes for {where(t[1])} and leaves the map{quiet}', True,
                    [t[1]], None)
        return f'goes for the chest at {where(t[0])} and empties it{quiet}', True, None, None
    if sp == 'CP_SP_Village':
        what = f'the village at {where(t[0])}' if t else 'the nearest village'
        then = f', then makes for {where(t[1])} and leaves the map' if len(t) > 1 else ', then attacks'
        return f'goes for {what}, razing it{then}', True, ([t[1]] if len(t) > 1 else None), (t[0] if t else 'any')
    if sp == 'CP_SP_Talk' and ps:
        return f'comes to {person_name(ps)} to talk{quiet}', False, None, None
    if mv == 'CP_MV_Position' and t:
        return f'heads for {where(t[0])}{quiet}', False, [t[0]], None
    if at == 'CP_AT_Person' and pt:
        return f'targets {person_name(pt)} when it attacks', False, None, None
    area = tiles(pa)
    if ac == 'CP_AC_Area' and len(area) > 1:
        (x1, y1), (x2, y2) = area[:2]
        still = 'stays where it stands and ' if mv == 'CP_MV_Null' else ''
        return (f'{still}waits until one of your units is in the area from ({min(x1, x2)}, {min(y1, y2)}) to ({max(x1, x2)}, '
                f'{max(y1, y2)})', False, None, None)
    if ac == 'CP_AC_Attacked':
        return 'holds still until it is attacked', False, None, None
    if ac == 'CP_AT_Null':
        return "doesn't move or attack unless the chapter's script wakes it", False, None, None
    return None


def with_ai(ch, e, u):
    """A unit entry with what its AI sends it to do: a sentence on its note, the torch badge for a looter, the tiles it heads for."""
    b = ai_words(ch, u)
    if b:
        words, looter, goes, raid = b
        e['note'] = e['note'] + '. ' + words[0].upper() + words[1:] + '.'
        if looter:
            e['looter'] = True
        if goes:
            e['goesTo'] = goes
        if raid:
            e['_raids'] = raid
    return e


def article(name):
    return ('an ' if name[:1].lower() in 'aeiou' else 'a ') + name


def unit_effects(ch):
    """{('pid', PID) or ('pos', game tile): [sentence]}: what a turn or area handler does to a unit already on the map: takes it off
    (UnitRemove*, UnitEffectWarpEscape: Chapter 7's Whitewings, Chapter 15's Gharnef), moves it (UnitMovePos, UnitMovePosEx,
    UnitSetPos: Chapter 1's Gazzak onto the throne), turns it into another class (UnitDragonTransform: the Endgame's Medeus) or wakes
    its AI (CpuSetActive: Chapter 12's Heimler)."""
    out = defaultdict(list)
    names = {j['jid']: j['name'] for j in D.jobs()}
    for h in ch.s.handlers():
        t = trigger(ch.s, h)
        if t in TURNS:
            first, last, phase = h['args'][:3]
            if not first:
                continue
            side = 'enemy' if phase == 1 else 'player'
            when = f"at the start of turn {first}'s {side} phase" if first == last else f'on turns {first}-{last}, {side} phase'
        elif t == AREA:
            (x1, y1), (x2, y2) = ch.app(h['args'][:2]), ch.app(h['args'][2:4])
            when = (f'when one of your units enters the area from ({min(x1, x2)}, {min(y1, y2)}) to ({max(x1, x2)}, '
                    f'{max(y1, y2)})')
        else:
            continue
        stack, local = [], {}
        for _, op, v in ch.s.disasm(h):
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
            elif op == 'call':
                fn, argc = v
                args = stack[len(stack) - argc:] if argc else []
                del stack[len(stack) - argc:]
                res = None
                ref = args[0] if args and isinstance(args[0], tuple) and args[0][0] in ('pid', 'pos') else None
                said = None
                if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and args and isinstance(args[0], str):
                    res = ('pid', args[0])
                elif fn in ('UnitGetByPos', 'UnitSafetyGetByPos') and len(args) == 2:
                    res = ('pos', (args[0], args[1]))
                elif ref and (fn == 'UnitEffectWarpEscape' or fn.startswith('UnitRemove')):
                    said = f'leaves the map {when}'
                elif ref and fn in ('UnitMovePos', 'UnitMovePosEx', 'UnitSetPos') and len(args) >= 3 and isinstance(args[1], int):
                    x, y = ch.app((args[1], args[2]))
                    said = f'moves to ({x}, {y}) {when}'
                elif ref and fn == 'UnitDragonTransform' and len(args) > 1 and args[1] in names:
                    said = f'turns into {article(names[args[1]])} {when}'
                elif ref and fn == 'CpuSetActive':
                    said = f'wakes {when}'
                if said and said not in out[ref]:
                    out[ref].append(said)
                stack.append(res)
            elif op in ('pop', 'jz', 'jnz', 'or', 'and'):
                if stack:
                    stack.pop()
            elif op in ('deref', 'eaddr'):
                if stack:
                    stack[-1] = None
            elif op == 'dup':
                stack.append(stack[-1] if stack else None)
            elif op == 'dupderef':
                stack.append(None)
            elif op == 'inc':
                if stack:
                    stack[-1] = None
    return out


def acts(s, h):
    """[(function, arguments)] for a handler's calls, a unit argument read as ('pid', PID) where it was fetched by UnitGetByPID /
    UnitSafetyGetByPID, the hero (UnitGetHero) as ('pid', 'PID_MARS'), and the acting unit (MindGetUnit) as ('visitor',)."""
    stack, local, out = [], {}, []
    for _, op, v in s.disasm(h):
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
        elif op == 'call':
            fn, argc = v
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            out.append((fn, args))
            res = None
            if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and args and isinstance(args[0], str):
                res = ('pid', args[0])
            elif fn == 'UnitGetHero':
                res = ('pid', 'PID_MARS')
            elif fn == 'MindGetUnit':
                res = ('visitor',)
            stack.append(res)
        elif op in ('pop', 'jz', 'jnz', 'or', 'and'):
            if stack:
                stack.pop()
        elif op in ('deref', 'eaddr'):
            if stack:
                stack[-1] = None
        elif op == 'dup':
            stack.append(stack[-1] if stack else None)
        elif op == 'dupderef':
            stack.append(None)
        elif op == 'inc':
            if stack:
                stack[-1] = None
    return out


def pid_of(ref):
    return ref[1] if isinstance(ref, tuple) and ref[0] == 'pid' else None


def talks_of(ch):
    """What each talk does: {recruit PID: [(recruiter, condition)]} for the talks that hand a unit over (UnitTransfer), each talk's
    condition read from its done flag (the 4th argument: set by the opening, it shuts the talk until a handler clears it: Chapter
    10's Minerva once Maria joins, Chapter 11's Jake once the house at (22, 7) is visited); [(item, recipient, recruit)] it gives
    (ItemGet: Chapter 18's Mercurius, taken off Est, to Marth); {PID: items it takes off}; and {PID: talker} for a talk that sends
    its unit off the map to join after the battle (Chapter 20x's Ymir: the end hands over whoever the flag it sets says)."""
    starts = {a[0] for h in ch.s.handlers() if h['name'] in ('MapBegin', 'Opening') for fn, a in ch.s.calls(h)
              if fn == 'FlagSet' and a and isinstance(a[0], str)}
    recruits, gifts, takes, later, clears = defaultdict(list), [], defaultdict(set), {}, defaultdict(list)
    talk_info = []
    for h in ch.s.handlers():
        if trigger(ch.s, h) != TALK:
            continue
        a, b = (ch.s.string(v) for v in h['args'][:2])
        done = ch.s.string(h['args'][3]) if len(h['args']) > 3 else None
        done_ok = done if isinstance(done, str) else None
        did = acts(ch.s, h)
        talk_info.append((h, a, b, done_ok, did))
        moved = [pid_of(x[0]) for fn, x in did if fn in TRANSFER and x]
        for fn, x in did:
            if fn == 'FlagClr' and x and isinstance(x[0], str) and moved and moved[0]:
                clears[x[0]].append(f'once {person_name(moved[0])} has joined your army')
    for h in ch.ter.handlers() if ch.ter else []:
        if len(h['args']) >= 3 and h['args'][2] in (VILLAGE, HOUSE):
            x, y = ch.app(h['args'][:2])
            for fn, a in ch.ter.calls(h):
                if fn == 'FlagClr' and a and isinstance(a[0], str):
                    clears[a[0]].append(f"once the {'house' if h['args'][2] == HOUSE else 'village'} at ({x}, {y}) is visited")
    for h, a, b, done, did in talk_info:
        moved = [pid_of(x[0]) for fn, x in did if fn in TRANSFER and x and pid_of(x[0])]
        removed = [pid_of(x[0]) for fn, x in did if fn.startswith('UnitRemove') and x and pid_of(x[0])]
        cond = ' or '.join(dict.fromkeys(clears[done])) if done in starts and clears.get(done) else None
        for pid in moved:
            other = b if a == pid else a
            recruits[pid].append((person_name(other), cond))
            for fn, x in did:
                if fn == 'UnitSetItemPutOff' and len(x) > 1 and pid_of(x[0]) == pid and isinstance(x[1], str):
                    takes[pid].add(x[1])
                elif fn == 'ItemGet' and len(x) > 1 and isinstance(x[1], str) and pid_of(x[0]) and pid_of(x[0]) != pid:
                    gifts.append((x[1], person_name(pid_of(x[0])), person_name(pid)))
        for pid in removed:
            if pid not in moved:
                later[pid] = person_name(b if a == pid else a)
    return recruits, gifts, takes, later


def ending_of(ch):
    """What the chapter's end does: {PID: words} for whom it hands over (UnitTransfer; 'if alive' where it checks: UnitCheckDead, a
    ...死亡 flag), and [(item, recipient PID or None)] it gives (ItemGet: Chapter 4's Silver Sword, Chapter 12's Parthia, Chapter 24x's
    Falchion)."""
    h = named(ch.s, 'Ending')
    if not h:
        return {}, []
    did = acts(ch.s, h)
    checks = any(fn == 'UnitCheckDead' or fn == 'FlagGet' and a and isinstance(a[0], str) and '死亡' in a[0] for fn, a in did)
    joins = {pid_of(a[0]): 'Joins your army after the battle' + (' if alive.' if checks else '.')
             for fn, a in did if fn in TRANSFER and a and pid_of(a[0])}
    gifts = [(a[1], pid_of(a[0])) for fn, a in did if fn == 'ItemGet' and len(a) > 1 and isinstance(a[1], str)]
    return joins, gifts


def tid(label):
    """The terrain id with a name label (its first: the lord's own variants come after)."""
    return next(i for i, row in enumerate(TERRAIN) if row[0] == label)


# What a tile's state makes it (the tile-state routine, overlay 00 0x21d4a7c-0x21d4b18): a door, done (1), floor and, closed (0), a
# door no unit enters; a drawbridge lowered, a bridge; a village done, closed, and destroyed (2), ruins.
STATE_TILE = {(DOOR, 1): 'MS_TER_FLOOR', (DOOR, 0): 'MS_TER_DOOR', (DRAWBRIDGE, 1): 'MS_TER_BRIDGE',
              (DRAWBRIDGE, 0): 'MS_TER_DRAWBRIDGE', (VILLAGE, 1): 'MS_TER_CLOSEVILLAGE', (VILLAGE, 2): 'MS_TER_DESTROYVILLAGE'}
TT_STATE = {'TTDone': 1, 'TTEnable': 0, 'TTDestroy': 2}
DECOY = 19
CLOSED = 'ws'


def or_list(words):
    """'a or b', 'a, b or c'; 'a, b, or c' where one has an 'and' of its own."""
    if len(words) == 1:
        return words[0]
    return ', '.join(words[:-1]) + (',' if len(words) > 2 and any(' and ' in w for w in words) else '') + ' or ' + words[-1]


LOCKED = 'A locked door: a Door Key or a Master Key opens it, making it floor'


def changes_of(ch, start_names):
    """What reshapes the map, from the scripts' tile natives (arm9 0x2046e50: TTEnable, TTDone, TTDestroy, RoofOpen) and the terrain
    script's doors and drawbridges: ({game tile: terrain id} the opening leaves, {game tile} still closed rooms, [change], [note],
    {game tile of a village: note}). A door a key opens is floor once open and opens the closed rooms beside it (_TTDone, arm9
    0x2045648, through overlay 00 0x21d4e44); a drawbridge a key lowers is a bridge; a script's change says what sets it off. What
    names someone who isn't on the map as the chapter starts (`start_names`: Prologue IV's Gordin) goes in a note the spoiler block
    leaves out."""
    start, opened_rooms, changes, notes, village_notes = {}, set(), [], [], {}
    # The flags a death or a talk sets: what a change waiting on them waits for.
    death_flags, talk_flags = {}, {}
    for h in ch.s.handlers():
        t = trigger(ch.s, h)
        k = 0 if t == DEATH else 1 if t == TALK else None
        if k is None or len(h['args']) <= k:
            continue
        who = person_name(ch.s.string(h['args'][k]))
        for fn, a in ch.s.calls(h):
            if fn == 'FlagSet' and a and isinstance(a[0], str):
                (death_flags if t == DEATH else talk_flags)[a[0]] = who

    def rooms_beside(x, y):
        return {ch.rooms[t] for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if t in ch.rooms}

    def room_tiles(ids):
        return sorted((t for t, r in ch.rooms.items() if r in ids and ch.inside(t)), key=lambda t: (t[1], t[0]))

    def code(t):
        return encode(GAME, letter_of(t))

    def cond_words(conds):
        """A change's guards in words, and whom they name: a death's flag, a recruit's talk, the army down to Marth; None where one
        can't be said. A flag cleared is the handler's own "done" flag (Prologue IV's ドアオープン)."""
        out, names = [], set()
        for c in conds:
            if c[0] == 'flag' and c[2] and c[1] in death_flags:
                out.append(f'after {death_flags[c[1]]} falls')
                names.add(death_flags[c[1]])
            elif c[0] == 'flag' and c[2] and c[1] in talk_flags:
                out.append(f'once {talk_flags[c[1]]} has joined')
                names.add(talk_flags[c[1]])
            elif c[0] == 'army' and c[1:] == (0, 1):
                out.append('only Marth is left in your army')
            elif not (c[0] == 'flag' and not c[2]):
                return None
        return out, names

    # The opening's changes, made before the battle (MapBegin and Opening: Chapter 1's razed village, the Endgame's open doors).
    for h in ch.s.handlers():
        if h['name'] not in ('MapBegin', 'Opening'):
            continue
        for fn, a in ch.s.calls(h):
            if fn in TT_STATE and len(a) > 2 and all(isinstance(v, int) for v in a[:3]):
                label = STATE_TILE.get((a[2], TT_STATE[fn]))
                if label:
                    start[(a[0], a[1])] = tid(label)
                if fn == 'TTDone' and a[2] == DOOR:
                    opened_rooms |= rooms_beside(a[0], a[1])
            elif fn == 'RoofOpen' and len(a) > 1 and (a[0], a[1]) in ch.rooms:
                opened_rooms.add(ch.rooms[(a[0], a[1])])
    closed = {t for t, r in ch.rooms.items() if r not in opened_rooms}

    # What the chapter's handlers change during the battle, and when: game tile -> [(words, state, kind, whom they name)].
    scripted = defaultdict(list)
    room_opens = []
    for h in ch.s.handlers():
        t = trigger(ch.s, h)
        if h['name'] in ('MapBegin', 'Opening', 'Ending') or t not in TURNS + (AREA,):
            continue
        if t == AREA:
            (x1, y1), (x2, y2) = ch.app(h['args'][:2]), ch.app(h['args'][2:4])
            when = f'when one of your units enters the area from ({min(x1, x2)}, {min(y1, y2)}) to ({max(x1, x2)}, {max(y1, y2)})'
        else:
            first, last, phase = h['args'][:3]
            side = 'enemy' if phase == 1 else 'player'
            when = f"at the start of turn {first}'s {side} phase" if first and first == last else None
        sets = {a[0] for fn, a in ch.s.calls(h) if fn == 'FlagSet' and a}
        did = [(fn, a, conds) for _, fn, a, conds in guarded_calls(ch.s, h) if fn in TT_STATE or fn == 'RoofOpen']
        both = ({(a[0], a[1]) for fn, a, _ in did if fn == 'TTDone' and len(a) > 1} &
                {(a[0], a[1]) for fn, a, _ in did if fn == 'TTEnable' and len(a) > 1})
        for fn, a, conds in did:
            if len(a) < 2 or not all(isinstance(v, int) for v in a[:2]) or (a[0], a[1]) in both:
                continue  # a door a scene opens and shuts again (Prologue IV's turn 2)
            words, names = when, set()
            if words is None and t in TURNS and not first:
                said = cond_words(conds)
                if said and said[0]:
                    names = said[1]
                    # Run once (its guard a flag it sets itself): the first such phase; a death's flag: the phase after it.
                    once = any(c[0] == 'flag' and not c[2] and c[1] in sets for c in conds)
                    words = (f'on the {side} phase ' if said[0][0].startswith('after') else
                             f'on the first {side} phase ' if once else f'on {article(side)} phase ') + ' and '.join(said[0])
            if not words:
                continue
            if fn == 'RoofOpen':
                if (a[0], a[1]) in ch.rooms:
                    room_opens.append((ch.rooms[(a[0], a[1])], (a[0], a[1]), words))
            elif len(a) > 2:
                scripted[(a[0], a[1])].append((words, TT_STATE[fn], a[2], names))

    # The terrain script's tiles: what visiting one does to another (Chapter 16's villages close each other; Prologue IV's fort, a
    # decoy's, opens a door).
    classes = {u['person']['pid']: u for units in ch.groups.values() for u in units}
    for h in ch.ter.handlers() if ch.ter else []:
        if len(h['args']) < 3:
            continue
        x, y, kind = h['args'][:3]
        X, Y = ch.app((x, y))
        calls = ch.ter.calls(h)
        if kind == DECOY:
            # Closed in the opening (TTDone), it opens when a handler enables it; a unit other than Marth that visits it stays
            # behind (UnitRemoveEventDead: Marth is turned back), the units it takes off the map leave, and the door it opens opens.
            opens = [(w, n) for w, st, _, n in scripted.pop((x, y), []) if st == 0]
            names = set().union(*(n for _, n in opens))
            visit = f'when a unit visits the fort at ({X}, {Y})'
            for fn, a in calls:
                if fn in TT_STATE and len(a) > 2 and all(isinstance(v, int) for v in a[:3]):
                    scripted[(a[0], a[1])].append((visit, TT_STATE[fn], a[2], names))
            gone = sorted({classes[a[0]]['job']['name'] + 's' for fn, a in calls
                           if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and a and a[0] in classes
                           and not classes[a[0]]['person']['named']})
            visitor = f'a unit other than Marth that visits the fort at ({X}, {Y})'
            if opens:
                visitor = f"from {or_list([w.removeprefix('on ') for w, _ in opens])}, {visitor}"
            note = visitor + ' stays behind as the decoy and leaves your army for good' + (
                f", and the {' and '.join(gone)} leave the map" if gone else '') + '.'
            notes.append((note[0].upper() + note[1:], names))
            continue
        for fn, a in calls:
            # A village's own TTDone takes its handler's arguments (None here); another tile's is that village closing.
            if fn == 'TTDone' and kind == VILLAGE and len(a) > 1 and isinstance(a[0], int) and (a[0], a[1]) != (x, y):
                tx, ty = ch.app((a[0], a[1]))
                village_notes[(x, y)] = f'Visiting it closes the village at ({tx}, {ty}).'

    # Doors and drawbridges: the terrain script's, each with what a script does to it.
    keyed = {(h['args'][0], h['args'][1]): h['args'][2] for h in (ch.ter.handlers() if ch.ter else [])
             if len(h['args']) > 2 and h['args'][2] in (DOOR, DRAWBRIDGE)}
    for (x, y), kind in sorted(keyed.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if not ch.inside((x, y)):
            continue
        X, Y = ch.app((x, y))
        what = scripted.pop((x, y), [])
        if kind == DRAWBRIDGE:
            assert not what, (ch.key, x, y)
            changes.append({'id': f'bridge-{X}-{Y}', 'trigger': 'event', 'tile': {'default': [X, Y]}, 'usableBy': '',
                            'effect': 'A raised drawbridge: a Bridge Key or a Master Key lowers it, making it a bridge.',
                            'patch': [{'tile': [X, Y], 'becomes': code(tid('MS_TER_BRIDGE'))}]})
            continue
        if start.get((x, y)) == tid('MS_TER_FLOOR'):
            # Open as the battle starts (the Endgame's): a script shuts it.
            shuts = [w for w, st, _, _ in what if st == 0]
            assert shuts and all(st == 0 for _, st, _, _ in what), (ch.key, x, y, what)
            changes.append({'id': f'door-{X}-{Y}', 'trigger': 'event', 'tile': {'default': [X, Y]}, 'usableBy': '',
                            'effect': f'Open as the battle starts; {or_list(shuts)} it shuts, a locked door again (a Door Key or a '
                                      'Master Key opens it).',
                            'patch': [{'tile': [X, Y], 'becomes': code(tid('MS_TER_DOOR'))}]})
            continue
        rooms = rooms_beside(x, y) - opened_rooms
        assert all(st == 1 for _, st, _, _ in what), (ch.key, x, y, what)
        # A visit first, then an area, then a phase.
        what = sorted(what, key=lambda w: (not w[0].startswith('when a unit visits'), not w[0].startswith('when')))
        seen = [w for w, _, _, n in what if n <= start_names]
        later = [(w, n) for w, _, _, n in what if not n <= start_names]
        effect = LOCKED + (', and the closed room behind it opens' if rooms else '') + '.'
        if seen:
            effect += f' It also opens {or_list(seen)}.'
        if later:
            notes.append((f'The door at ({X}, {Y}) also opens {or_list([w for w, _ in later])}.', set().union(*(n for _, n in later))))
        changes.append({'id': f'door-{X}-{Y}', 'trigger': 'event', 'tile': {'default': [X, Y]}, 'usableBy': '', 'effect': effect,
                        'patch': [{'tile': [X, Y], 'becomes': code(tid('MS_TER_FLOOR'))}] +
                                 [{'tile': ch.app(t), 'becomes': code(ch.ids[t[1]][t[0]])} for t in room_tiles(rooms)]})
    assert not scripted, (ch.key, dict(scripted))
    # A roof a script lifts (Chapter 17x's throne room).
    for room, (x, y), words in room_opens:
        if room in opened_rooms:
            continue
        X, Y = ch.app((x, y))
        changes.append({'id': f'room-{X}-{Y}', 'trigger': 'event', 'tile': {'default': [X, Y]}, 'usableBy': '',
                        'effect': f'A closed room: it opens {words}.',
                        'patch': [{'tile': ch.app(t), 'becomes': code(ch.ids[t[1]][t[0]])} for t in room_tiles({room})]})
    # A note naming someone who isn't on the map at the start says so first (the spoiler block leaves it out).
    out = []
    for note, names in notes:
        later = sorted(names - start_names)
        out.append(f"{' and '.join(later)} {'is' if len(later) == 1 else 'are'}n't on the map at the start: " + note[0].lower() + note[1:]
                   if later else note)
    return start, closed, changes, out, village_notes


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
    # MapTableData +0x15: the goal.
    wins = {f: rec[0x15] for f, _, _, rec in D.maps()}
    story = []
    for key in PROLOGUE:
        story.append(key)
        if key in SECOND:
            story.append(SECOND[key])
    for n in range(1, 24):
        story.append(f'bmap{n:03d}')
        if n in AFTER:
            story.append(AFTER[n])
    story += [ENDGAME] + CHRONICLES + DLC

    maps, sources, variants, used = [], defaultdict(list), {}, {}
    names_seen = defaultdict(lambda: defaultdict(int))

    held = {}  # (item, map id, kind, text) -> the modes the line holds on

    def source(iid, mid, kind, text, ds=None, limited=None):
        if iid.endswith('_FALSE'):
            return  # a double's false copy is never yours
        name = item_name(iid)
        # The downloadable chapters' sources sit behind the weapon page's DLC switch.
        if mid.startswith('fe12-dl'):
            kind = 'dlc-' + kind
        e = {'mapId': mid, 'kind': kind, 'text': text, **({'limited': limited} if limited else {})}
        if e not in sources[name]:
            sources[name].append(e)
        held.setdefault((name, mid, kind, text), set()).update(ds or MODES)

    # Who has joined: every mode plays the prologue.
    joined = set()

    def join(who, key):
        """The modes on which a unit joining in this chapter joins for the first time ([]: it has joined before)."""
        if who in joined:
            return []
        joined.add(who)
        return list(MODES)

    for key in story:
        ch = Chapter(key)
        title = titles[key]
        route = 'Story'
        firsts = {b: a for a, b in SECOND.items()}
        if key in PROLOGUE or key in firsts:
            n = PROLOGUE.index(firsts.get(key, key)) + 1
            mid, chapter, heading = f'fe12-p{n}' + ('b' if key in firsts else ''), n, 'Prologue'
        elif key in GAIDEN:
            mid, chapter, heading = f'fe12-{GAIDEN[key]}', int(GAIDEN[key][:-1]), None
        elif key == ENDGAME:
            mid, chapter, heading = 'fe12-final', 24, 'Endgame'
        elif key in CHRONICLES:
            mid, chapter, heading, route = f'fe12-ac{CHRONICLES.index(key) + 1}', CHRONICLES.index(key) + 1, 'Chronicles', 'Extra'
        elif key in DLC:
            mid, chapter, heading, route = f'fe12-dl{DLC.index(key) + 1}', DLC.index(key) + 1, 'DLC', 'DLC'
        else:
            mid, chapter, heading = f'fe12-{int(key[4:])}', int(key[4:]), None
        # 'Ch. 1 Grustian Expedition', 'Prologue I Meeting', 'Endgame Light and Shadow': the heading taken off.
        name = re.sub(r'^(Ch\. \w+|Endgame|Prologue [IVX]+) ', '', title)
        # The game is lost when Marth or the Avatar falls (script/startup.cmb's death handlers set gf_gameover).
        on_map = {u['person']['pid'] for units in ch.groups.values() for u in units}
        lost = ' or '.join(n_ for p_, n_ in (('PID_MARS', 'Marth'), (AVATAR, 'the Avatar')) if p_ in on_map) or 'Marth'
        m = {'id': mid, 'route': route, 'chapter': chapter, 'title': name, 'width': ch.w, 'height': ch.h, 'grid': [],
             'victory': WIN.get(wins.get(key), 'Seize'), 'defeat': lost[0].upper() + lost[1:] + ' is defeated', 'units': [],
             'starts': [], 'objects': [], 'objectives': [], 'changes': [], 'notes': [], 'lord': 'Marth'}
        if heading:
            m['heading'] = heading
        modes = MODES

        # Who stands where as the chapter starts: MapBegin's groups and the opening scene's, played out (scenes move units).
        begin, opening = named(ch.s, 'MapBegin'), named(ch.s, 'Opening')
        # Per mode: the scenes' difficulty checks and the placements' own gates.
        merged = {}
        for mode in MODES:
            for g, u, at, conds in play(ch, [begin, opening], mode):
                if mode in record_modes(u):
                    merged.setdefault((g, id(u), tuple(at), repr(conds)), [g, u, at, conds, []])[4].append(mode)
        placed = [(g, u, at, conds) for g, u, at, conds, _ in merged.values()]
        modes_of = {(g, id(u), tuple(at), repr(conds)): ms for g, u, at, conds, ms in merged.values()}
        starting_foes = []
        # The chapter's own boss (bosses()), and the doubles a handler shuffles with it: Chapter 23's handler 9 hands the real
        # Gharnef's PID and items to one of its three Gharnefs at random (RandomMinMax, UnitSetPID, UnitSetItemAdd).
        seize_at = [tuple(h['args'][:2]) for h in (ch.ter.handlers() if ch.ter else []) if len(h['args']) >= 3 and h['args'][2] == SEIZE]
        boss_dead, gone = bosses(ch, seize_at)
        effects = unit_effects(ch)
        recruits, talk_gifts, talk_takes, join_later = talks_of(ch)
        end_joins, end_gifts = ending_of(ch)
        stock_of = {a[0]: a[1] for h in ch.s.handlers() for fn, a in ch.s.calls(h)
                    if fn == 'ValueRegistSet' and len(a) > 1 and isinstance(a[0], str) and isinstance(a[1], int)}
        start_tiles, closed_rooms, map_changes, change_notes, village_notes = changes_of(
            ch, {person_name(u['person']['pid']) for _, u, _, _ in placed if u['person']['named']})
        m['changes'] = map_changes
        m['notes'] += change_notes

        def recruit(u, ents):
            """A unit a talk recruits, or that joins later, says so; its items are yours from the next chapter, not a foe's."""
            pid = u['person']['pid']
            if pid not in recruits and pid not in join_later and pid not in end_joins:
                return False
            for e in ents:
                if pid in recruits:
                    e['type'] = 'named'
                    e['talk'] = 'Recruit: talk with ' + ' or '.join(
                        dict.fromkeys(w + (f', {c}' if c else '') for w, c in recruits[pid]))
                    e.pop('drops', None)
                elif pid in join_later:
                    e['talk'] = f'Talk with {join_later[pid]}: leaves the map, and joins your army after the battle'
                    e.pop('drops', None)
                if pid in end_joins and pid not in join_later:
                    e['note'] += '. ' + end_joins[pid]
                    e['note'] = e['note'].replace('..', '.')
            ds = join(pid, key)
            for iid, *_ in u['items'] if ds else []:
                if iid not in talk_takes.get(pid, ()):
                    source(iid, mid, 'kit-later', f"Carried by {unit_name(u)} on joining", ds)
            return True
        boss_pids = set(boss_dead)
        real, doubles = {}, set()
        for h in ch.s.handlers():
            pid = None
            for fn, a in ch.s.calls(h):
                if fn == 'UnitSetPID' and len(a) > 1 and isinstance(a[1], str):
                    pid = a[1]
                    if pid.endswith('_FALSE'):
                        doubles.add(pid)
                elif fn == 'UnitSetItemAdd' and len(a) > 1 and isinstance(a[1], str) and pid and not pid.endswith('_FALSE'):
                    real.setdefault(pid, []).append((a[1], bool(a[2]) if len(a) > 2 else False))
        boss_pids |= {d for d in doubles if d.removesuffix('_FALSE') in boss_pids}
        if not boss_pids:
            boss_pids = {u['person']['pid'] for g, u, at, _ in placed if not g.startswith('mikata') and tuple(at) in seize_at
                         and u['person']['pid'] not in gone}
        if not begin:
            for g in ('mikata', 'first'):
                if not any(pg == g for pg, _, _, _ in placed):
                    placed += [(g, u, tuple(u['at']), []) for u in ch.groups.get(g, [])]
                    modes_of.update({(g, id(u), tuple(u['at']), '[]'): record_modes(u) for u in ch.groups.get(g, [])})
        alternatives = {}
        for g, u, at, conds in placed:
            umodes = modes_of[(g, id(u), tuple(at), repr(conds))]
            u = {**u, 'at': at}
            when = '; '.join(('if ' if on else 'unless ') + FLAG_WORDS.get(flag, flag) for flag, on in conds)
            if not g.startswith('mikata') and u['team'] == 0 and u['person']['pid'] in ('PID_MARS', AVATAR) and ch.inside(u['at']):
                # Marth or the Avatar left standing by the opening's scene (Prologue I's Avatar is its scene's e02): yours to move.
                m.setdefault('forced', []).append({'name': unit_name(u), 'tile': ch.app(u['at'])})
                if u['person']['pid'] == AVATAR and 'corrinStart' not in m:
                    m['corrinStart'] = ch.app(u['at'])
                continue
            if g.startswith('mikata'):
                if not ch.inside(u['at']):
                    continue
                # The lord's start: Marth's, or in the prologue chapters he isn't in, the Avatar's.
                if u['person']['pid'] == 'PID_MARS' or u['person']['pid'] == AVATAR and 'corrinStart' not in m:
                    m['corrinStart'] = ch.app(u['at'])
                # The deployment slots: 'mikata' (a prologue chapter's second version's own, 'mikataB'), 'mikata1'...
                deploy = bool(re.fullmatch(r'mikata\d?B?', g))
                if deploy:
                    m['starts'].append(ch.app(u['at']))
                elif conds:
                    # One of two units the opening places by a story flag (the Endgame: Nagi if Chapter 24x was played, else Gotoh).
                    alternatives.setdefault(tuple(u['at']), []).append((conds[0][1], unit_name(u), conds[0][0]))
                else:
                    m.setdefault('forced', []).append({'name': unit_name(u), 'tile': ch.app(u['at'])})
                # A unit's items are a source where it first joins: a deployment slot's in the prologue (Normal) and Chapter 1 (the
                # Hard modes, whose army joins there), any other placement of yours where it's placed.
                if not deploy or key in PROLOGUE or key == 'bmap001':
                    ds = join(u['person']['pid'], key)
                    for iid, *_ in u['items'] if ds else []:
                        source(iid, mid, 'kit', f"Carried by {unit_name(u)} on joining" + (f' ({when})' if when else ''), ds)
                continue
            if re.match(r'e\d|ev', g) or not ch.inside(u['at']) or u['team'] == 0:
                continue
            kind = 'boss' if u['person']['pid'] in boss_pids else 'named' if u['person']['named'] else 'enemy'
            if u['team'] == 2:
                kind = 'ally'
            ents = unit_entries(ch, u, kind, umodes)
            # What its AI and the chapter's handlers have it do.
            told = effects.get(('pos', tuple(u['at'])), []) + (effects.get(('pid', u['person']['pid']), []) if u['person']['named'] else [])
            for e, _, _ in ents:
                with_ai(ch, e, u)
                for said in dict.fromkeys(told):
                    e['note'] += '. ' + said[0].upper() + said[1:] + '.'
                e['note'] = e['note'].replace('..', '.')
            base = u['person']['pid'].removesuffix('_FALSE')
            if base in real and (u['person']['pid'] in doubles or base == u['person']['pid']):
                # Which of them is real is picked as the map loads: each tile says so, its items left to the note.
                n = sum(1 for _, x, _, _ in placed if x['person']['pid'].removesuffix('_FALSE') == base)
                items = ' and '.join(f'the {item_name(i)} it drops' if d else item_name(i) for i, d in real[base])
                for e, _, _ in ents:
                    e.pop('carries', None)
                    e.pop('drops', None)
                    e['note'] = (f"Lv {u['level']} {u['job']['name']}. One of these {n}, picked at random as the map loads, is the real "
                                 f'{unit_name(u)}, with {items}; the others are doubles with false copies (a double drops a Steel Sword).')
                if u['person']['pid'] in doubles:
                    source('IID_STEELSWORD', mid, 'drop', f'Dropped by a double of {unit_name(u)}')
            m['units'].extend(e for e, _, _ in ents)
            starting_foes.append((u, ents))
        for at, alts in alternatives.items():
            unset = next((n for on, n, _ in alts if not on), None)
            sets = [(n, f) for on, n, f in alts if on]
            name = unset + ''.join(f' ({n} if {FLAG_WORDS.get(f, f)})' for n, f in sets) if unset else ' or '.join(n for n, _ in sets)
            m.setdefault('forced', []).append({'name': name, 'tile': ch.app(at)})

        if wins.get(key) == 8:
            for h in ch.s.handlers():
                calls = ch.s.calls(h)
                who = [a[1] for fn, a in calls if fn == 'UnitCheckPID' and len(a) > 1 and isinstance(a[1], str)]
                if trigger(ch.s, h) == AREA and who and any(fn == 'FlagSet' and a == ['gf_complete'] for fn, a in calls):
                    X, Y = ch.app(h['args'][:2])
                    m['objectives'].append({'type': 'arrive', 'tiles': [[X, Y]], 'label': f'{person_name(who[0])} arrives here'})
                    m['victory'] = f'{person_name(who[0])} reaches ({X}, {Y})'

        # Area triggers (x1, y1, x2, y2, side): entering one sets flags the turn handlers check (under the conditions the area's
        # handler checks: the boss alive, a counter), or places a group itself.
        def rect(a):
            x1, y1, x2, y2 = (max(1, min(v, lim)) for v, lim in zip(a[:4], (ch.w, ch.h, ch.w, ch.h)))
            return [x1, ch.h + 1 - y2, x2, ch.h + 1 - y1]
        flag_areas, area_conds, area_arrivals = defaultdict(list), defaultdict(list), []
        # Where each group's units stand once the handler that places it has run (a group warped in from off the map: Chapter 23's
        # z02; a scene's actor placed and taken off again in one handler, Prologue IV's e02, is never one).
        arrived = {}

        def place(h):
            got = {}
            for mode in MODES:
                for g, u, at, _ in play(ch, [h], mode):
                    if mode in record_modes(u):
                        got.setdefault(g, {}).setdefault((id(u), tuple(at)), [u, at, []])[2].append(mode)
            for g, units in got.items():
                arrived.setdefault(g, [tuple(x) for x in units.values()])
            return set(got)

        def arrivals(h):
            """The groups a handler places together (under the same conditions: one arrival), each with its conditions."""
            kept = place(h)
            out = {}
            for _, fn, a, conds in guarded_calls(ch.s, h):
                if fn.startswith('Dispos') and fn != 'DisposWait' and a and isinstance(a[0], str) and a[0] in kept:
                    out.setdefault(repr(conds), (conds, []))[1].append(a[0])
            return [(tuple(dict.fromkeys(gs)), conds) for conds, gs in out.values()]

        for h in ch.s.handlers():
            if trigger(ch.s, h) != AREA:
                continue
            area = {'who': 'enemy' if h['args'][4] == 1 else 'player', 'rect': rect(h['args'])}
            for _, fn, a, conds in guarded_calls(ch.s, h):
                if fn == 'FlagSet' and a and isinstance(a[0], str):
                    flag_areas[a[0]].append(area)
                    area_conds[a[0]] += [c for c in conds if c not in area_conds[a[0]]]
            for gs, _ in arrivals(h):
                area_arrivals.append((gs, area))

        # A flag a talk sets (Prologue IV: Marth's talk with Gordin sets ゴードン味方): who joins by that talk.
        talk_flags = {}
        for h in ch.s.handlers():
            if trigger(ch.s, h) == TALK:
                calls = ch.s.calls(h)
                got = [a[0] for fn, a in calls if fn in ('UnitGetByPID', 'UnitSafetyGetByPID') and a and isinstance(a[0], str)]
                if any(fn in TRANSFER for fn, _ in calls) and got:
                    for fn, a in calls:
                        if fn == 'FlagSet' and a and isinstance(a[0], str):
                            talk_flags[a[0]] = person_name(got[0])

        # Counters: a value a turn handler steps after placing its groups (ValueInc) and resets when it stops (ValueSet to 0, with the
        # flag that started it cleared): so many phases in a row; one only an area resets: so many times in all.
        incs = defaultdict(set)
        resets = defaultdict(set)
        for h in ch.s.handlers():
            for fn, a in ch.s.calls(h):
                if fn == 'ValueInc' and a and isinstance(a[0], str):
                    incs[a[0]].add(trigger(ch.s, h))
                elif fn == 'ValueSet' and len(a) > 1 and a[1] == 0 and isinstance(a[0], str):
                    resets[a[0]].add(trigger(ch.s, h))

        # Reinforcements: turn handlers placing groups; the groups one handler places together are one arrival, and the same arrival
        # placed on several turns is one group with its turns, the areas whose flags its handler waits on, and what stops it.
        turns, conds_of, keys, once = defaultdict(list), {}, [], set()
        for h in ch.s.handlers():
            if trigger(ch.s, h) not in TURNS:
                continue
            first, last, phase = h['args'][:3]
            sets = {a[0] for fn, a in ch.s.calls(h) if fn == 'FlagSet' and a and isinstance(a[0], str)}
            for gs, conds in arrivals(h):
                if gs not in conds_of:
                    keys.append(gs)
                    conds_of[gs] = conds
                turns[gs].append((first, last, phase))
                # A handler that sets the flag it waits on to be clear runs once (Prologue IV's Knights).
                if any(c[0] == 'flag' and not c[2] and c[1] in sets for c in conds):
                    once.add(gs)
        # An arrival made of other arrivals' groups (the Endgame's turns 15 and 20 bring both its pairs at once) is their turns.
        for gs in list(keys):
            parts = [k for k in keys if k != gs and set(k) < set(gs)]
            if parts and set().union(*map(set, parts)) == set(gs) and conds_of[gs] == [] and all(conds_of[k] == [] for k in parts):
                for k in parts:
                    turns[k] += turns[gs]
                keys.remove(gs)
        for gs, area in area_arrivals:
            if gs not in conds_of:
                keys.append(gs)
                conds_of[gs] = []
        boss_name = ' or '.join(person_name(p) for p in sorted(boss_dead)) if boss_dead else None
        reinf = []
        for gs in keys:
            units = []
            for g in gs:
                for u, at, ms in arrived.get(g, []):
                    if not ch.inside(at) or u['team'] == 0:
                        continue
                    u = {**u, 'at': at}
                    kind = 'boss' if u['person']['pid'] in boss_pids else 'named' if u['person']['named'] else 'enemy'
                    ents = unit_entries(ch, u, kind, ms)
                    for e, _, _ in ents:
                        e['from'] = ch.app(u['from']) if ch.inside(u['from']) else e['tile']
                        with_ai(ch, e, u)
                        units.append(e)
                    if recruit(u, [e for e, _, _ in ents]):
                        continue
                    for e, items, ms in ents:
                        for iid, drop in items:
                            source(iid, mid, 'drop-later' if drop else 'foe-later', ('Dropped by ' if drop else 'Carried by ') + (
                                e['name'] if u['person']['named'] else f"a foe {e['name']}"), ms)
            if not units:
                continue
            conds = conds_of[gs]
            gates = [c[1] for c in conds if c[0] == 'flag' and c[2] and c[1] in flag_areas]
            unless = [c[1] for c in conds if c[0] == 'flag' and not c[2] and c[1] in flag_areas]
            areas = [a for f in gates + unless for a in flag_areas[f]] + [a for k, a in area_arrivals if k == gs]
            areas = [a for i, a in enumerate(areas) if a not in areas[:i]]
            later = [c for f in gates for c in area_conds[f]]
            boss = any(c == ('flag', BOSS_DEAD, False) for c in conds + later)
            counted = [(c[1], c[2]) for c in conds if c[0] == 'lt']
            cap = next((c[2] for c in later if c[0] == 'lt' and incs.get(c[1])), None)
            phase = {p for _, _, p in turns[gs]}
            phase_word = 'enemy phase' if phase == {1} else 'player phase' if phase == {0} else 'phase'
            the = 'the area below' if len(areas) == 1 else 'one of the areas below'
            if gates and counted and any(TURN in resets.get(v, ()) or 0x03 in resets.get(v, ()) for v, _ in counted):
                n = counted[0][1]
                when = f'The next {n} {phase_word}s after one of your units enters {the}'
            elif gates and counted:
                when = f'Every {phase_word} once one of your units has entered {the}, at most {counted[0][1]} times'
            elif gates:
                when = arrival_words(turns[gs]) + (' once an area below is entered' if len(areas) > 1 else ' once the area below is entered')
            elif any(c[0] == 'flag' and c[2] and c[1] in talk_flags for c in conds):
                who = next(talk_flags[c[1]] for c in conds if c[0] == 'flag' and c[2] and c[1] in talk_flags)
                when = (f'The first {phase_word} after {who} joins your army' if gs in once else
                        f'Every {phase_word} once {who} has joined your army')
            elif unless:
                when = arrival_words(turns[gs]) + f', unless one of your units has entered {the} by then'
            elif turns.get(gs):
                when = arrival_words(turns[gs])
                # A tile's state or a unit on a tile the handler checks (Chapter 1's thief: only while the village is unvisited, and
                # only when its entry tile is clear); one that sets the flag it waits on comes once.
                checks = []
                for c in conds:
                    if c[0] == 'tt':
                        X, Y = ch.app(c[1])
                        what = {VILLAGE: 'village', HOUSE: 'house', DOOR: 'door', CHEST: 'chest'}.get(c[2], 'tile')
                        state = {VILLAGE: 'unvisited', HOUSE: 'unvisited', DOOR: 'shut', CHEST: 'unopened'}.get(c[2], 'untouched')
                        checks.append(f"while the {what} at ({X}, {Y}) is {state}" if c[3] else f"once the {what} at ({X}, {Y}) is {state.removeprefix('un')}")
                    elif c[0] == 'unit_at':
                        X, Y = ch.app(c[1])
                        checks.append(f'if no unit stands on ({X}, {Y})' if not c[2] else f'if a unit stands on ({X}, {Y})')
                if gs in once and len(turns[gs]) == 1 and turns[gs][0][0] != turns[gs][0][1]:
                    when += ': the first of them' + (' ' + ' and '.join(checks) if checks else '')
                elif checks:
                    when += ', ' + ' and '.join(checks)
            else:
                when = 'When a unit enters the area below' if len(areas) == 1 else 'When a unit enters an area below'
            if cap:
                when += f', up to {cap} times'
            if boss and boss_name:
                when += f', until {boss_name} is defeated'
            r = {'id': f"{mid}-{'-'.join(gs)}", 'label': gs, 'units': units, 'when': when}
            if areas:
                r['areas'] = areas
            reinf.append(r)
        # Groups go by number, in the order of their own (zNN) groups' numbers, then the others (an opening's foes an area brings,
        # Prologue IV's Knights) as they come.
        def order(r):
            nums = [int(g[1:].rstrip('B')) for g in r['label'] if re.fullmatch(r'z\d+B?', g)]
            return (0, min(nums)) if nums else (1, 0)
        reinf.sort(key=order)
        for k, r in enumerate(reinf, 1):
            r['label'] = f'Group {k}'
        if reinf:
            m['reinforcements'] = reinf

        # Talks that recruit (talks_of), and units the chapter's end hands over (ending_of): their gear is yours from the next chapter.
        recruited = set()
        for u, ents in starting_foes:
            if recruit(u, [e for e, _, _ in ents]):
                recruited.add(id(u))
        # What a talk or the chapter's end gives: from the next chapter (talk-later, event-later).
        for iid, who, pid in talk_gifts:
            source(iid, mid, 'talk-later', f'Given to {who} when {pid} joins')
        for iid, to in end_gifts:
            source(iid, mid, 'event-later', 'Given at the end of the chapter' + (f' to {person_name(to)}' if to else ''))

        # What the starting foes carry and drop on each mode (a recruit's items are yours instead, above).
        for u, ents in starting_foes:
            if id(u) in recruited:
                continue
            for e, items, ms in ents:
                for iid, drop in items:
                    source(iid, mid, 'drop' if drop else 'foe', ('Dropped by ' if drop else 'Carried by ') + (
                        e['name'] if u['person']['named'] else f"a foe {e['name']}"), ms)

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
                elif kind == VILLAGE and start_tiles.get((x, y)) == tid('MS_TER_DESTROYVILLAGE'):
                    continue  # razed before the battle (Chapter 1's opening)
                elif kind == VILLAGE:
                    reward = []
                    for g in groups_placed(ch.ter, h):
                        # A recruit walks out of the village (Wrys in Chapter 1).
                        for u in ch.groups.get(g, []):
                            who = unit_name(u)
                            reward.append(f'{who} joins')
                            m.setdefault('joiners', []).append({'name': who, 'tile': ch.app(u['at']), 'from': tile, 'group': g,
                                                                'when': f'Joins when a unit visits the village at ({tile[0]}, {tile[1]})'})
                            ds = join(u['person']['pid'], key)
                            for iid, *_ in u['items'] if ds else []:
                                source(iid, mid, 'kit-later', f'Carried by {who} on joining', ds)
                    # A reward only for a visit with items in hand (Chapter 22's Starlight: Marth carrying the Lightsphere and the
                    # Starsphere, both taken), read from the checks before it.
                    needs = [a[1] for fn, a in calls if fn == 'UnitCheckItem' and len(a) > 1 and isinstance(a[1], str)]
                    takes = [a[1] for fn, a in calls if fn == 'UnitSetItemPutOff' and len(a) > 1 and isinstance(a[1], str)]
                    cond = ''
                    if needs:
                        orbs = ' and the '.join(item_name(i) for i in needs)
                        cond = (f'if Marth carries the {orbs}' + (' (both taken)' if len(takes) > 1 else ' (taken)' if takes else ''))
                    for fn, a in calls:
                        if fn == 'ItemGet' and len(a) > 1 and a[1]:
                            reward.append(item_name(a[1]) + (f', {cond}' if cond else ''))
                            source(a[1], mid, 'village', 'Given at a village' + (f', {cond}' if cond else ''))
                        elif fn == 'MoneyGet' and a:
                            reward.append(f'{a[0]} gold')
                    m['objects'].append({'type': 'village', 'tile': tile, 'reward': ', '.join(reward)})
                    if (x, y) in village_notes:
                        m['objects'][-1]['note'] = village_notes[(x, y)]
                elif kind in (ARMORY, VENDOR, SECRET):
                    stock = []
                    where = {ARMORY: 'the armory', VENDOR: 'the vendor', SECRET: 'the secret shop, with a VIP Card'}[kind]
                    for fn, a in calls:
                        if fn in ('Goods', 'GoodsLimit') and a and a[0]:
                            # GoodsLimit(item, value): only as many as the chapter's script sets the value to (ValueRegistSet).
                            n = stock_of.get(a[1]) if fn == 'GoodsLimit' and len(a) > 1 else None
                            assert fn == 'Goods' or n, (key, a)
                            stock.append(item_name(a[0]) + (f' ({n} in stock)' if n else ''))
                            source(a[0], mid, 'shop', f'Sold at {where}' + (f' ({n} in stock)' if n else ''), limited=n)
                    label = {ARMORY: 'Armory', VENDOR: 'Vendor', SECRET: 'Secret shop'}[kind]
                    m['objects'].append({'type': 'shop', 'tile': tile, 'kind': label, 'stock': stock})
                elif kind == SEIZE:
                    m['objectives'].append({'type': 'seize', 'tiles': [tile], 'label': 'Seize with Marth'})

        # Hidden treasure (handler type 0x18: an area, then a done flag): the unit that finds it gets its item (MindGetUnit, ItemGet).
        for h in ch.s.handlers():
            if trigger(ch.s, h) != HIDDEN or h['args'][0] == 0xFFFF:
                continue
            got = [a[1] for fn, a in ch.s.calls(h) if fn == 'ItemGet' and len(a) > 1 and isinstance(a[1], str)]
            if not got:
                continue
            x1, y1, x2, y2 = h['args'][:4]
            (l, t), (r, b) = ch.app((min(x1, x2), min(y1, y2))), ch.app((max(x1, x2), max(y1, y2)))
            for iid in got:
                m['objects'].append({'type': 'hidden', 'tile': ch.app(((x1 + x2) // 2, (y1 + y2) // 2)), 'area': [l, b, r, t],
                                     'contents': item_name(iid)})
                source(iid, mid, 'hidden', 'Hidden on the map')

        # A village names the raiders on the map at the start that make for it (their AI's village, or the nearest).
        raiders = defaultdict(list)
        for e in m['units']:
            if e.get('_raids'):
                raiders[json.dumps(e['_raids'])].append(e['name'])
        for o in m['objects']:
            names = raiders.get(json.dumps(o['tile']), []) + raiders.get('"any"', []) if o['type'] == 'village' else []
            if names:
                o['note'] = ((o['note'] + ' ') if o.get('note') else '') + f"{' or '.join(dict.fromkeys(names))} can raze it before you visit."
        for e in m['units'] + [u for g in m.get('reinforcements', []) for u in g['units']]:
            e.pop('_raids', None)

        # The modes: what the foe builder gives the foes it levels, Lunatic's hit (arm9 0x2050470) and Reverse Lunatic's order (overlay
        # 00 0x21f56fc: when one of your units attacks, the foe strikes first; the game's own words, MIMH_LUNATICD).
        for mode in MODES[1:]:
            note = (f"Foes the game levels gain {LEVELS_K[mode] * ch.levels} levels' worth of growth in HP, Str, Mag, Skl, Spd and Lck "
                    f"(Def and Res only where a foe has growths of its own for the modes), their shown level unchanged, and their weapon "
                    f"ranks are at least {RANK_FLOOR[mode]}.")
            if MODE_VALUE[mode] >= 5:
                note += ' Foes get +10 hit.'
            if mode == 'Reverse Lunatic':
                note += ' When one of your units attacks, the foe strikes first.'
            m.setdefault('notesOn', []).append({'note': note, 'difficulties': [mode]})

        # The battle preparations' armory (overlay 10 0x22304f0), where MapTableData +0x18 has 0x04: from Chapter 1.
        if ch.prep & 0x04:
            for iid in PREP_ARMORY:
                source(iid, mid, 'shop', "Sold at the preparations' armory")

        # A gaiden chapter: what opens it, from the end of the chapter before: its turn limit on each difficulty, or another way.
        if key in GAIDEN:
            before = next(k for k, v in AFTER.items() if v == key)
            turns, ways = gaiden_condition(Chapter(f'bmap{before:03d}'), before)
            assert turns, key
            other = f", or if {' or '.join(ways)} when it ends" if ways else ''
            limits = {mode: turns * NORMALIZE[mode] // 100 for mode in MODES}
            for limit in sorted(set(limits.values())):
                ds = [md for md in MODES if limits[md] == limit]
                note = f'Opens if Chapter {before} is cleared by turn {limit}{other}.'
                if len(ds) == len(MODES):
                    m['notes'].append(note)
                else:
                    m.setdefault('notesOn', []).append({'note': note, 'difficulties': ds})

        # Terrain codes: each code's stats are one set in every map (checked), its names the game's per tile; the opening's changes
        # made (Chapter 1's razed village), closed rooms closed.
        rows = []
        used[mid] = defaultdict(lambda: defaultdict(list))
        for y in range(1, ch.h + 1):
            line = []
            for x in range(1, ch.w + 1):
                t = start_tiles.get((x, y), ch.ids[y][x])
                info = tile_info(t)
                code = encode(GAME, letter_of(t))
                if (x, y) in closed_rooms:
                    info, code = {'name': 'Roof (closed room)', 'def': 0, 'avo': 0, 'heal': 0, 'move': {g: None for g, _ in GROUPS},
                                  'note': 'A room under its roof: no unit can enter it, fliers included, until a door into it opens or '
                                          "the chapter's script lifts its roof."}, CLOSED
                line.append(code)
                stats = {k: v for k, v in info.items() if k != 'name'}
                assert variants.setdefault(code, stats) == stats, (mid, code, info)
                names_seen[code][info['name']] += 1
                used[mid][code][info['name']].append(ch.app((x, y)))
            rows.append(''.join(line))
        m['grid'] = rows
        if not any(u['person']['pid'] == 'PID_MARS' and u['team'] == 0 for _, u, _, _ in placed):
            m['lord'] = 'the Avatar'
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
    gm.mark_difficulties(sources, held, {m['id']: MODES for m in maps})
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=MODES)


if __name__ == '__main__':
    main()
