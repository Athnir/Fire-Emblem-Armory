"""
Builds Radiant Dawn's maps from the game's own files:

- src/data/fe10/fe10Terrain.ts: the terrain table (Def, Avoid, healing and the cost for each movement
  group), from FE10Data.cms.
- src/data/fe10/fe10Maps.ts: each chapter's terrain grid (zmap/bmapPPNN/map.cmp), its units (dispos_*.bin)
  and, from the chapter script (Scripts/CPPNN.cmb): who starts where, reinforcements and when they come,
  chests, villages, doors, buried treasure, goals and talks. The win and lose conditions come from the
  chapter table in FE10Data.cms.

Difficulties: the scripts test only Normal(), which is true on Easy (the Japanese release's Normal), and
the placement files are dispos_n (Easy) and dispos_h (Normal and Hard, the Japanese Hard and Maniac). In
the data 'Normal' stands for Easy and 'Hard' for Normal and Hard; the app labels them so.

Coordinates: the game counts from the top-left corner (0, 0); the app counts from the bottom-left (1, 1),
so (x, y) becomes (x + 1, height - y). Formats are in data-raw/fe10/README.md.
Run:  python scripts/build-fe10-maps.py
"""
import copy
import importlib.util
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fe9_cmb  # noqa: E402
from fe10_files import FE10, GameData, read_text  # noqa: E402
from fe9_files import lz10, unpack  # noqa: E402

fe9_cmb.FE9 = FE10
Script = fe9_cmb.Script
# Path of Radiance's map builder: the shared readers and the cropping.
_spec = importlib.util.spec_from_file_location('fe9maps', os.path.join(HERE, 'build-fe9-maps.py'))
fe9maps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fe9maps)
Reloc, crop_to, flag_tests, expand = fe9maps.Reloc, fe9maps.crop_to, fe9maps.flag_tests, fe9maps.expand
reach_bounds = fe9maps.reach_bounds

ROOT = os.path.join(HERE, '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe10')

# The game's terrain names (without their variant digits) -> the app's map letters. Terrains that share a
# letter must share their stats (checked below).
LETTERS = {
    '平地': '.', '雪原': '.', '石畳': '.', '洞窟': '.', '船': '.', '床': '.', 'スイッチ': '.', '台座': '.', '財宝': '.', '訪問': '.',
    '階段': 'S', '橋': 'b', '橋蓋': 'b',
    '制圧': 't', '到達': 't', '離脱': 't', '防衛': 't',
    '茂み': 'f', '深い茂み': 'f', '葦': 'f', '光の茂み': 'H', '回復': 'H',
    '川': 'w', '浅瀬': 'w', '湿地': 'P', '沼': 'M', '砂地': 's', '砂漠': 's',
    '海岸': 'W', '山道': 'W', '荒地': 'W', '段差': 'E', '低い崖': 'E',
    '海': 'a', '湖': 'a', '水路': 'a', '池': 'u', '堀': 'u',
    '崖': 'C', '岩': 'C', '溶岩': 'C', '落石': 'C', '雪山': 'n',
    '木': 'k', 'ヤシ': 'k', 'サボテン': 'k', '枯れ木': 'k', '倒木': 'k', '森': 'k', '樹海': 'k',
    **{n: 'B' for n in ('屋根', '小物', '酒場', '厩', '倉庫', 'テント', '武器屋', '道具屋', '拠点', '市場', '祠', '古井戸', '馬車',
                        '民家', '収容所', '監視塔', '樽', 'ダミー', '遺跡', '廃墟', '花壇', '焚き火', '馬', 'ロバ', '牛', '石像',
                        '噴水', '荷物', 'たいまつ')},
    **{n: 'l' for n in ('柵', '射柵', '土嚢', '壊れる土嚢', '外壁', '外射壁', '壊れる外壁', '壊れる外射壁', '外柱', '外扉')},
    '穴': 'x', '奈落': 'x', '滝': 'x', '空': 'R', '雲': 'J', '回復壷': 'I',
    '宝箱': 'c', '投石器': 'L', 'アーチ': 'L',
    **{n: '#' for n in ('移動不可', '未設定', '教会', '塔', '風車', '灯台', '闘技場', '進入禁止', '室内壁', '室内射壁', '壊れる壁',
                        '壊れる射壁', '城', '砦', '館', '神殿')},
    # A pillar no one can enter is a wall: the pillar icon is kept for ones a unit can stand on (Fates').
    '柱': '#', '扉': 'd',
}
# The app's name for each letter on Radiant Dawn's maps.
LETTER_NAMES = {
    '.': 'Plain / floor', 'S': 'Stairs', 'b': 'Bridge', 't': 'Goal tile', 'f': 'Thicket', 'H': 'Healing thicket',
    'w': 'River / shallows', 'P': 'Wetland', 'M': 'Swamp', 's': 'Sand / desert', 'W': 'Mountain path / wasteland',
    'E': 'Ledge / low cliff', 'a': 'Sea / lake', 'u': 'Pond / moat', 'C': 'Cliff / rock', 'n': 'Snowy peak',
    'k': 'Tree / forest', 'B': 'Building / object', 'l': 'Fence / outer wall', 'x': 'Hole / chasm', 'c': 'Chest',
    'L': 'Ballista', 'R': 'Sky', 'J': 'Cloud', 'I': 'Healing jar', 'N': 'Beside a healing jar', '#': 'Wall / structure', 'p': 'Pillar', 'd': 'Door', 'v': 'Village',
}
# Movement groups: the game's movement types that share every terrain cost, named as players know them.
GROUP_NAMES = {0: 'Infantry', 4: 'Armour', 5: 'Generals', 6: 'Mages & priests', 8: 'Cavalry', 9: 'Paladins & Valkyries',
               10: 'Fliers', 11: 'Thieves', 13: 'Bandits', 14: 'Beast laguz', 16: 'Beast laguz (Mov 9 classes)',
               15: 'Dragon laguz', 17: 'Dragon laguz (Mov 6 classes)', 21: 'Rafiel', 22: 'Black Knight'}
DIFFS = {'Normal': 'n', 'Hard': 'h'}
DIFF_TEXT = {'Normal': 'Easy', 'Hard': 'Normal and Hard'}
DISPOS_CALLS = ('Dispos', 'DisposRank', 'InstantDispos', 'InstantDisposRank', 'InstantDisposFirstRank', 'DisposContinueRank',
                'DisposFirstRank', 'DisposAsynchronousRank', 'InstantDisposContinueRank',
                'DisposSetMode', 'DisposWarpRank', 'DisposAsynchronous', 'EvArrayDispos')
PHASE = {0: 'player phase', 1: 'enemy phase', 2: 'ally phase'}

# The playable grid of each map (game coordinates, 0-based from the top left: x0, x1, y0, y1), from the
# overviews on fireemblemwod.com: the grid lines they draw cover just the tiles units can use. Keyed by chapter
# file (and section).
# Tiles the user found to be buildings in-game where the map files have open ground (game coordinates).
TILE_FIXES = {'0102': {(5, 5): 'B', (6, 5): 'B'}}
# Fog of war: the scripts turn it on with SetSight(1) (Part 1 Ch.9, Part 3's Prologue); these two set it some
# other way, not yet found in the files, and fireemblemwod.com reports their fog.
FOG_PER_WOD = {'0203', '0302'}
PLAYABLE = {
    '0101': (10, 21, 10, 19), '0102': (5, 20, 5, 18), '0103': (10, 23, 10, 22), '0104': (4, 19, 5, 20), '0105': (5, 18, 5, 17),
    '0106': (1, 15, 1, 16), ('0107', 1): (12, 37, 26, 43), ('0107', 2): (1, 28, 1, 22), '0108': (10, 32, 10, 27),
    '0109': (10, 34, 10, 29), '0110': (1, 9, 1, 8), '0111': (1, 14, 1, 26),
    '0201': (8, 23, 8, 23), '0202': (20, 35, 20, 33), '0203': (10, 34, 10, 22), '0204': (13, 28, 13, 49),
    '0205': (15, 36, 15, 36),
    '0301': (5, 25, 5, 25), '0302': (14, 29, 14, 29), '0303': (5, 32, 5, 31), '0304': (5, 20, 5, 34),
}


_AI_TARGETS = None


def ai_targets():
    """Where each AI sequence sends its unit: {sequence: (x, y)}. The sequences are named tables in
    Cp/cp_data.cms; one that moves its unit to a tile holds it at +92 (x, y as two halves). Part 3 Ch.3's
    SEQ_0304_HORSEMOVE_1..4 each send a horse to its own exit, not the nearest."""
    global _AI_TARGETS
    if _AI_TARGETS is None:
        r = Reloc(lz10(open(os.path.join(FE10, 'Cp', 'cp_data.cms'), 'rb').read()))
        _AI_TARGETS = {name: struct.unpack_from('>2H', r.data, o + 92) for o, name in r.tables
                       if name.startswith('SEQ_') and o + 96 <= len(r.data)}
    return _AI_TARGETS


def strip_digits(name):
    return name.rstrip('０１２３４５６７８９')


def map_files(folder, name):
    return unpack(lz10(open(os.path.join(FE10, 'zmap', folder, name + '.cmp'), 'rb').read()))


def clean(text):
    # Text codes: #X3A, #X35 ...
    return re.sub(r'#X[0-9A-F]{2}|#x', '', text) if text else text


class Game:
    def __init__(self):
        self.g = GameData()
        self.text = read_text()
        g, t = self.g, self.text
        self.items = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in g.records('IID_', 'MIID_')}
        jobs = g.records('JID_', 'MJID_')
        self.classes = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in jobs}
        self.move_type = {g.string(g.u32(o)): g.d[o + 52] for o in jobs}
        pids = g.records('PID_', 'MPID_')
        shared = Counter(g.string(g.u32(o + 4)) for o in pids)
        faces = defaultdict(set)
        for o in pids:
            # By name: a character's cutscene double (MPID_SOTHE_EV) shares their portrait and name.
            mpid = g.string(g.u32(o + 4))
            faces[g.string(g.u32(o + 12))].add(t.get(mpid) or mpid)
        self.people = {}
        for o, nxt in zip(pids, pids[1:] + [pids[-1] + 200]):
            mpid, face = g.string(g.u32(o + 4)), g.string(g.u32(o + 12))
            skills = [s for s in (g.string(g.u32(x)) for x in range(o + 28, min(nxt, o + 48), 4)) if (s or '').startswith('SID_')]
            own_face = face == 'FID_' + mpid[5:]
            self.people[g.string(g.u32(o))] = {
                'name': t.get(mpid) or mpid,
                # A character has a name label of their own (MNPID_), or is a boss, or has a portrait named for
                # them under a name at most a cutscene double shares (Pugo). Begnion's soldiers share one name.
                'generic': not (g.u32(o + 8) or 'SID_BOSS' in skills or (own_face and shared[mpid] <= 2)),
                'boss': 'SID_BOSS' in skills,
                # The commander, whose death loses the chapter (Micaiah); others get it for one chapter.
                'hero': 'SID_HERO' in skills,
            }
        self._green_names(pids)
        self.terrain = self._terrain()
        self.chapters = self._chapters()

    def _green_names(self, pids):
        """Which green (other army) units are named, so get the person icon rather than a plain green dot. Not
        the test for foes: Aimee's portrait is the shop's and Kurth's is FID_KURTHf, so they'd count as
        generic, while the Gallia laguz have a portrait under their army's name, so they'd count as named."""
        g = self.g
        info, shared, names_by_face = {}, Counter(), defaultdict(set)
        for o in pids:
            p, mpid, face = g.string(g.u32(o)), g.string(g.u32(o + 4)), g.string(g.u32(o + 12))
            info[p] = (mpid, face)
            shared[mpid] += 1
            # Cutscene and versus-mode copies share a character's portrait under another name: not counted.
            if not p.endswith('_EV') and '_EV' not in mpid and not p.startswith('PID_VS_'):
                names_by_face[face].add(mpid)
        for p, (mpid, face) in info.items():
            c, m = re.sub(r'_EV\w*$', '', re.sub(r'^PID_(DJ_)?', '', p)), mpid[5:]
            if re.search(r'MAP\d', p):
                named = False  # made for one chapter (Part 3 Ch.3's horses, the prisoners)
            elif c != m and c.startswith(m) and not re.fullmatch(r'_?\d+', c[len(m):]):
                named = False  # an army's name plus a class (GALIA_TIGER, CRIMEASOLDIER)
                # Generic as a foe too: Part 3 Ch.6's Gallia laguz are common enemies, not named ones.
                self.people[p]['generic'] = True
            elif len(names_by_face[face]) > 1:
                named = False  # an army's portrait, shared by its soldiers' names (Crimea, Daein)
            else:
                # A named character, or one with a name of their own few share (Aimee, Kurth; not 'Boy').
                named = not self.people[p]['generic'] or (c == m and shared[mpid] <= 2)
            self.people[p]['green_named'] = named

    def _terrain(self):
        """{game terrain name: 44-byte record}: ground Avoid, Def, Res; fliers' Avoid, Def, Res; heal %; a flag
        byte; three pointers; then the cost for each of 24 movement types (255 = can't enter)."""
        g, out = self.g, {}
        o = next(x for x in range(0x20, len(g.d) - 16, 4) if g.string(g.u32(x)) == '移動不可' and (g.string(g.u32(x + 4)) or '').startswith('MT_'))
        while (g.string(g.u32(o + 4)) or '').startswith('MT_'):
            p = 0x20 + g.u32(o + 8)
            out[g.string(g.u32(o))] = g.d[p:p + 44]
            o += 16
        return out

    def _chapters(self):
        """The chapter table: MCT label, map folder, script, then three blocks of 32 bytes (Easy, Normal,
        Hard), each with the win condition at +0 and the lose conditions at +12 to +24."""
        g, t = self.g, self.text
        out = {}
        for o in range(0x20, len(g.d) - 180, 4):
            mct, folder = g.string(g.u32(o)) or '', g.string(g.u32(o + 4)) or ''
            if not (re.fullmatch(r'MCT\d{4}', mct) and folder.startswith('bmap')):
                continue

            def label(k):
                return g.string(g.u32(o + k)) if g.u32(o + k) else None
            blocks = []
            for b in (32, 64, 96):
                win = clean(t.get(label(b), label(b)))
                loses = [clean(t.get(label(b + k), label(b + k))) for k in (12, 16, 20, 24) if label(b + k)]
                blocks.append((win, loses))
            # +136 is 0 on the maps with no preparations screen (Part 1's Prologue to Ch.2, Part 2's Prologue to
            # Ch.2), where the game deploys your units itself.
            out[mct[3:]] = {'folder': folder, 'script': label(8), 'part': int(mct[3:5]), 'blocks': blocks,
                            'prep': bool(g.d[o + 136]),
                            'title': t.get(mct + '_2', t[mct]), 'heading': t.get(mct + '_3', '')}
        return out


def build_terrain(game):
    """FE10_TERRAIN by letter, and the movement groups."""
    used = {n: r for n, r in game.terrain.items()}
    by_cost = defaultdict(list)
    for mt in range(24):
        by_cost[tuple(r[20 + mt] for r in used.values())].append(mt)
    groups = []  # (name, representative movement type, example classes)
    for types in by_cost.values():
        name = next((GROUP_NAMES[m] for m in types if m in GROUP_NAMES), None)
        if name is None:
            continue
        examples = sorted({c for j, c in game.classes.items() if c and game.move_type.get(j) in types and j != 'JID_DEBUG'})
        groups.append((name, types[0], examples))
    order = list(GROUP_NAMES.values())
    groups.sort(key=lambda gr: order.index(gr[0]))
    table = {}
    for name, r in game.terrain.items():
        letter = LETTERS.get(strip_digits(name))
        if not letter:
            continue
        move = {gname: (None if r[20 + mt] == 255 else r[20 + mt]) for gname, mt, _ in groups}
        entry = {'name': LETTER_NAMES[letter], 'def': r[1], 'avo': r[0], 'heal': r[6], 'move': move}
        if r[2]:
            entry['note'] = f'Res +{r[2]}.'
        if (r[3], r[4]) != (0, 0):
            entry['note'] = (entry.get('note', '') + ' Fliers get its bonus too.').strip()
        if letter in table:
            a = table[letter]
            impassable = all(v is None for v in a['move'].values() if v is not None) or all(
                a['move'][gname] is None for gname, _, _ in groups if gname != 'Fliers')
            if (a['move'], a['def'], a['avo'], a.get('note')) != (move, entry['def'], entry['avo'], entry.get('note')) or (
                    a['heal'] != entry['heal'] and not impassable):
                raise SystemExit(f'{name} differs from the other terrain on letter {letter!r}')
        else:
            table[letter] = entry
    table['v'] = {**table['.'], 'name': LETTER_NAMES['v']}
    # A healing jar heals a unit directly beside it, not diagonally (main.dol 0x800544e4: at the start of the
    # turn the game checks the 4 tiles around the unit for terrain flagged 0x40, and heals by that terrain's %).
    jar = table['I']
    jar['note'] = f"Heals {jar['heal']}% of max HP at the start of the turn to a unit directly beside it (not diagonally)."
    table['N'] = {**table['.'], 'name': LETTER_NAMES['N'], 'heal': jar['heal'],
                  'note': f"A healing jar beside it heals {jar['heal']}% of max HP at the start of the turn, in place of this tile's own healing."}
    # Height (main.dol 0x8002ad94 compares the two units' tiles; 0x8002f388, 0x8002f6f0): the unit on higher ground
    # gets +2 attack and +50 Hit, the one below -50 Hit.
    table['E']['note'] = 'Height counts: a unit attacking from higher ground gets +2 attack and +50 Hit, and one below it -50 Hit.'
    if 'L' in table:
        table['L']['note'] = 'The machine itself: no one can enter it. A bow user fires it from the marked tile beside it.'
    return table, groups


def dispos(folder, diff):
    """All groups in a placement file: {group: [unit]}. Units are 104 bytes: a 4-byte ID, PID, JID, a
    pointer, then where the unit comes from (x, y) and where it stands (x, y), level, side (0 player, 1 enemy,
    2 other armies), the affinity, 7 item slots ('/D' drops, '/L' can't be taken), 5 skills and the AI."""
    path = os.path.join(FE10, 'zmap', folder, f'dispos_{diff}.bin')
    if not os.path.exists(path):
        return {}
    r = Reloc(open(path, 'rb').read())
    out = {}
    for o, group in r.tables:
        count, p, units = r.data[o], o + 4, []
        for _ in range(count):
            raw = r.data[p:p + 104]
            slots = [r.string(p + 36 + 4 * k) for k in range(7)]
            units.append({
                'group': group, 'pid': r.string(p + 4), 'jid': r.string(p + 8),
                'from': (raw[12], raw[13]), 'at': (raw[14], raw[15]), 'level': raw[16], 'side': raw[17],
                'items': [s.split('/')[0] for s in slots if s],
                'drops': [s.split('/')[0] for s in slots if s and 'D' in s.split('/')[1:]],
                'skills': [s for s in (r.string(p + 64 + 4 * k) for k in range(5)) if s],
                'ai': [s for s in (r.string(p + 84 + 4 * k) for k in range(5)) if s],
            })
            p += 104
        out[group] = units
    return out


def if_alive(script):
    """Groups placed only when a character has died earlier: {group: (PID, group placed while they live)}.
    Part 3 Ch.6 places Lethe if she's alive, else Kezhda on her tile: `UnitCheckLiveByPID(PID) ; jz ;
    InstantDisposRank(alive group) ; jmp ; InstantDisposRank(other group)`."""
    out = {}
    for h in script.handlers():
        ops = [(op, a) for _, op, a in script.disasm(h) if op in ('str', 'call', 'jz', 'jmp')]
        for k in range(len(ops) - 6):
            (o0, pid), (o1, fn), (o2, _), (o3, g1), (o4, f1), (o5, _), (o6, g2) = ops[k:k + 7]
            if (o0, o1, o2, o3, o5, o6) == ('str', 'call', 'jz', 'str', 'jmp', 'str') and fn == 'UnitCheckLiveByPID/1'                     and f1.split('/')[0] in DISPOS_CALLS and k + 7 < len(ops) and ops[k + 7][1].split('/')[0] in DISPOS_CALLS:
                out[g2] = (pid, g1)
    return out


def calls10(script, hs, h, alive=None, depth=0, env=None):
    """A handler's calls with their arguments and the difficulties that reach them: [(name, [args],
    difficulties)]. Radiant Dawn's scripts branch on `if (Normal()) {...}` (Easy) and call other handlers by
    number (op 0x37, `-> hN`), which are followed; each is listed as ('->', [N], ...). Arguments are
    literals, or what a variable holds: ('unit', PID) from UnitGetByPID, ('pos', x, y) from UnitGetByPos."""
    alive = frozenset(DIFFS) if alive is None else alive
    env = {} if env is None else env
    dis = script.disasm(h)
    stack, out, blocks = [], [], []
    pcs = [pc for pc, _, _ in dis]

    def pop():
        return stack.pop() if stack else ('?',)
    for k, (pc, op, a) in enumerate(dis):
        while blocks and pc >= blocks[-1][0]:
            alive = blocks.pop()[1]
        if op == 'call' and a == 'Normal/0':
            j = k + 1
            negate = j < len(dis) and dis[j][1] == 'op29'
            j += negate
            if j < len(dis) and dis[j][1] == 'jz':
                end = dis[j][2]
                inside = (alive - {'Normal'}) if negate else (alive & {'Normal'})
                last = max((i for i, x in enumerate(pcs) if x < end), default=j)
                after = alive - inside if dis[last][1] == 'ret' else alive
                blocks.append((end, after))
                alive = inside
        if op in ('str', 'int'):
            stack.append(a)
        elif op == 'var':
            stack.append(env.get(a, ('?',)))
        elif op == 'load':
            stack.append(('addr', a))
        elif op in ('ref', 'index'):
            stack.append(('?',))
        elif op == '?47':  # store
            value, addr = pop(), pop()
            if isinstance(addr, tuple) and addr[0] == 'addr':
                env[addr[1]] = value
        elif op == 'op27':  # negate
            v = pop()
            stack.append(-v if isinstance(v, int) else ('?',))
        elif op in ('op29', 'deref'):
            pop()
            stack.append(('?',))
        elif op.startswith('op') and op not in ('op29', 'op27'):
            pop(), pop()
            stack.append(('?',))
        elif op == 'pop':
            pop()
        elif op == 'call':
            fn, argc = a.split('/')
            argc = int(argc)
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            out.append((fn, args, alive))
            stack.append(('unit', args[0]) if fn == 'UnitGetByPID' and args else
                         ('pos', args[0], args[1]) if fn == 'UnitGetByPos' and len(args) == 2 else ('?',))
        elif op == 'stmt' and depth < 8:
            idx = int(a, 16)
            if idx < len(hs) and idx != h['i']:
                out.append(('->', [idx], alive))
                out += calls10(script, hs, hs[idx], alive, depth + 1)
    return out


STEP = {'2': (0, 1), '8': (0, -1), '4': (-1, 0), '6': (1, 0)}


def stage(units, cs):
    """Where the units stand once the openings have walked them about: [(unit, (x, y))], leaving out anyone
    sent off the map."""
    placed = [[u, tuple(u['at'])] for u in units]

    def find(ref):
        if isinstance(ref, tuple) and ref[0] == 'unit':
            return next((p for p in placed if p[0]['pid'] == ref[1]), None)
        if isinstance(ref, tuple) and ref[0] == 'pos':
            return next((p for p in placed if p[1] == (ref[1], ref[2])), None)
        if isinstance(ref, str):
            return next((p for p in placed if p[0]['pid'] == ref), None)
        return None
    for fn, a, _ in cs:
        if not a:
            continue
        who = find(a[0])
        if who is None:
            continue
        if fn in ('UnitMovePos', 'UnitMovePosDir', 'UnitSetPos', 'UnitSetPosDir', 'UnitMovePosHold', 'UnitMovePosByPID',
                  'UnitSetPosDirByPID') and len(a) >= 3 and isinstance(a[1], int) and isinstance(a[2], int):
            who[1] = (a[1], a[2])
        elif fn.startswith('UnitMoveRoute') and len(a) >= 2 and isinstance(a[1], str):
            nums = [int(n) for n in re.findall(r'-?\d+', a[1])]
            if len(nums) >= 2:
                who[1] = (nums[-2], nums[-1])
        elif fn in ('UnitMoveDir', 'UnitMoveDirByPID') and len(a) >= 2 and isinstance(a[1], str):
            x, y = who[1]
            for c in a[1]:
                dx, dy = STEP.get(c, (0, 0))
                x, y = x + dx, y + dy
            who[1] = (x, y)
        elif fn in ('UnitEscape', 'UnitEscapeByPID', 'UnitDeadEscape'):
            placed.remove(who)
    return placed


def is_scene(fn, a, folder):
    """A cutscene starts: REventStart(map, 1), or on another map. REventStart(map, 0) on this one (or '')
    sets up the battle itself."""
    if fn == 'EventMapLoad':
        return True
    return len(a) < 2 or a[1] != 0 or a[0] not in ('', folder)


def scenes_removed(cs, folder):
    """The calls outside cutscenes."""
    out, scene = [], False
    for c in cs:
        if c[0] in ('REventStart', 'REventStart2', 'EventMapLoad'):
            scene = is_scene(c[0], c[1], folder)
        elif c[0] in ('REventEnd', 'EventMapFree'):
            scene = False
        elif not scene:
            out.append(c)
    return out


def battle_calls(cs, folder):
    """What the openings do once the battle map is up: from its MapLoad (or REventStart(map, 0)) on, outside
    cutscenes."""
    out, started, scene = [], False, False
    for c in cs:
        fn, a = c[0], c[1]
        if fn in ('REventStart', 'REventStart2', 'EventMapLoad'):
            scene = is_scene(fn, a, folder)
            started = started or not scene
            continue
        if fn in ('REventEnd', 'EventMapFree'):
            scene = False
            continue
        if fn == 'MapLoad' and a == [folder]:
            started = True
        if started and not scene:
            out.append(c)
    return out


def join_turns(texts):
    """'Turn 9, player phase' and 'Turn 10, player phase' -> 'Turns 9 and 10, player phase'."""
    turns = [re.fullmatch(r'Turn (\d+), (.+)', t) for t in texts]
    if len(texts) > 1 and all(turns) and len({m.group(2) for m in turns}) == 1:
        ns = sorted(int(m.group(1)) for m in turns)
        return f"Turns {', '.join(map(str, ns[:-1]))} and {ns[-1]}, {turns[0].group(2)}"
    return ' or '.join(texts)


def goals(ch):
    """The win and lose conditions in plain words, noting where Easy differs."""
    (ew, el), (nw, nl), (hw, hl) = ch['blocks']
    fix = {'Rout enemy': 'Rout the enemy', 'Defeat boss': 'Defeat the boss'}

    def win_text(w):
        w = fix.get(w, w)
        m = re.match(r'Escape in (\d+) turns', w)
        if m:
            return f'Escape within {m.group(1)} turns'
        m = re.match(r'Rout in (\d+) turns', w)
        if m:
            return f'Rout the enemy within {m.group(1)} turns'
        m = re.match(r'Turn (\d+): (.+)', w)
        return f'{m.group(2)} by turn {m.group(1)}' if m else w
    win = win_text(nw) if nw == hw else f'{win_text(nw)} (Normal); {win_text(hw)} (Hard)'
    if ew and ew != nw:
        a, b = win_text(nw), win_text(ew)
        # Only the numbers differ: just give Easy's.
        easy_numbers = ', '.join(re.findall(r'\d+', b))
        win += (f' ({easy_numbers} on Easy)' if re.sub(r'\d+', '#', a) == re.sub(r'\d+', '#', b)
                else f' ({b[0].lower() + b[1:]} on Easy)')

    def lose_text(ls):
        out = []
        for x in ls:
            m = re.match(r'(\d+) turns complete', x)
            out.append(f'Take more than {m.group(1)} turns' if m else x)
        return ', or '.join(x if i == 0 or not re.match(r'(Any|Take|All|Other|Enemy) ', x) else x[0].lower() + x[1:]
                            for i, x in enumerate(out))
    lose = lose_text(nl)
    if lose_text(el) != lose:
        lose += f' (Easy: {lose_text(el)})'
    return win, lose


def build_chapter(game, terrain, code, section=None):
    ch = game.chapters[code]
    folder = ch['folder']
    script = Script(ch['script'] + '.cmb')
    hs = script.handlers()
    hcalls = {h['i']: calls10(script, hs, h) for h in hs}
    ground = {k for k, info in terrain.items() if info['move']['Infantry'] is not None}

    # Terrain.
    mp = Reloc(map_files(folder, 'map')['map.bin'])
    w, h = mp.data[2], mp.data[3]
    pi, up = mp.named[f'{folder}:panelindex'], mp.named[f'{folder}:uniquepanel']

    ri, rp = mp.named.get(f'{folder}:roofindex'), mp.named.get(f'{folder}:roofpanel')

    def panel(x, y):
        # The roof layer (roofindex into roofpanel's 12-byte records) has the terrain where a roof covers the
        # ground: a house or church over paving is a building. A plain roof (屋根) is lifted when a unit goes in
        # (Part 1 Ch.7's cells), so the floor under it counts.
        idx = struct.unpack_from('>H', mp.data, pi + 2 * (y * w + x))[0]
        roof = struct.unpack_from('>H', mp.data, ri + 2 * (y * w + x))[0] if ri is not None else 0
        ground = strip_digits(mp.string(up + 12 * idx + 8))
        top = strip_digits(mp.string(rp + 12 * roof + 8) or '') if roof else ''
        if top == '屋根':
            roofed.append((x, y))
        if top:
            under[(x, y)] = ground
        return ground if top in ('', '屋根') else top
    W, H = w, h
    roofed, under = [], {}
    grid = [[LETTERS[panel(x, y)] for x in range(w)] for y in range(h)]
    for (x, y), letter in TILE_FIXES.get(code, {}).items():
        grid[y][x] = letter
    for y in range(h):
        for x in range(w):
            if grid[y][x] == 'I':
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == '.':
                        grid[ny][nx] = 'N'
    # Clouds (Part 2's Prologue): they drift one tile left each phase, wrapping round the whole map, so the
    # map keeps the full pattern (fireemblemwod.com: one tile per player phase and per enemy phase).
    cloud_rows = [''.join('#' if grid[y][x] == 'J' else '.' for x in range(w)) for y in range(h)] if any('J' in r for r in grid) else None

    def tile(p):
        return [p[0] + 1, H - p[1]]

    def on_map(p):
        return 0 <= p[0] < W and 0 <= p[1] < H

    def rect(ax, ay, bx, by):
        return [tile((ax, by))[0], tile((ax, by))[1], tile((bx, ay))[0], tile((bx, ay))[1]]

    # Which section a handler belongs to (Part 1 Ch.6's two maps: the script tests 'セクションＢ').
    def section_of(hh):
        for f, want in flag_tests(script, hh):
            if f == 'セクションＢ':
                return 2 if want else 1
        return None

    def in_section(hh):
        return not section or section_of(hh) in (None, section)

    # Tile events.
    objects, objectives = [], []
    goal_tiles = defaultdict(list)
    torches, changes = [], []
    arson = defaultdict(list)
    for hh in hs:
        if hh['kind'] != 5 or len(hh['args']) < 3:
            continue
        x, y, sub = hh['args'][:3]
        if not on_map((x, y)):
            continue
        cs = hcalls[hh['i']]
        got = [a[0] for fn, a, _ in cs if fn == 'MindGetItem' and a]
        gold = [a[0] for fn, a, _ in cs if fn == 'MindGetMoney' and a]
        reward = ', '.join(game.items.get(i, i) for i in got) or (f'{gold[0]} gold' if gold else '')
        if sub == 12:
            objects.append({'type': 'chest', 'tile': tile((x, y)), 'contents': reward})
            grid[y][x] = 'c'
        elif sub == 9:
            objects.append({'type': 'village', 'tile': tile((x, y)), 'reward': reward})
            grid[y][x] = 'v'
        elif sub == 11:
            grid[y][x] = 'd'
        elif sub == 55 and any(fn == 'SetBomber' for fn, _, _ in cs):
            # A house an arsonist sets alight (BuildEventFlame: BuildInstTorch, then SetBomber); event 59 on the
            # same tile puts it out. The tiles of one house share a flag.
            flag = next((a[0] for fn, a, _ in cs if fn == 'set' and a), (x, y))
            arson[flag].append((x, y))
        elif sub == 55:
            radius = next((a[2] for fn, a, _ in cs if fn == 'BuildInstTorch' and len(a) == 4 and isinstance(a[2], int)), 0)
            torches.append(((x, y), radius))
            t = tile((x, y))
            changes.append({'id': f'torch-{t[0]}-{t[1]}', 'trigger': 'torch', 'tile': {'default': t}, 'radius': radius,
                            'usableBy': 'a unit next to it',
                            'effect': f'Lights every tile within {radius} of it, lifting the fog there.'})
        elif sub in (13, 14, 42, 45):
            # Easy hides an escape or goal tile it doesn't use (BuildInstHide).
            goal_tiles[sub].append((x, y))
    for pts in arson.values():
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        objects.append({'type': 'fire', 'tile': tile((min(xs), min(ys))),
                        'area': [min(xs) + 1, H - max(ys), max(xs) + 1, H - min(ys)]})
    # A village a bandit can destroy: tile event 38 on the same tile (BuildDestruction).
    destroyable = {tuple(tile(hh['args'][:2])) for hh in hs if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 38}
    for o in objects:
        if o['type'] == 'village' and tuple(o['tile']) in destroyable:
            o['note'] = 'Bandits can destroy it before you visit.'
    hidden_on_easy = {(a[0], a[1]) for hh in hs for fn, a, alive in hcalls[hh['i']] if fn == 'BuildInstHide' and len(a) == 2
                      and alive == {'Normal'}}
    # A tile-45 exit whose event loses the chapter: where an enemy carries off a captive (Leanne, Part 2's Prologue).
    captive_exits = {(hh['args'][0], hh['args'][1]) for hh in hs if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 45
                     and any(fn == 'set' and a == ['gf_gameover'] for fn, a, _ in hcalls[hh['i']])}
    labels = {13: ('seize', 'Seize'), 14: ('escape', 'Escape'), 42: ('arrive', 'Arrive'), 45: ('escape', 'Where units leave the map')}
    # Who leaves by a tile-45 exit: units whose AI escapes (in the placement file, or switched to
    # SEQ_ESCAPEMOVE by the script for someone it names).
    escapers, looters = [], False

    def plural(word):
        return word[:-1] + 'ves' if word.endswith('f') else word + 's'

    def who(pid, jid):
        p_ = game.people[pid]
        if not p_['generic']:
            return p_['name']
        cls = plural(game.classes.get(jid, jid))
        return cls if p_['name'] in cls else f"{p_['name']} {cls}"
    for src in [dispos(folder, c) for c in ('n', 'h', 'c')]:
        for us in src.values():
            for u in us:
                if any('ESCAPE' in a for a in u['ai']) and u['pid'] in game.people:
                    looters = looters or any('LOOTER' in a for a in u['ai'])
                    escapers.append(who(u['pid'], u['jid']))
    for hh in hs:
        cs = hcalls[hh['i']]
        for k, (fn, a, _) in enumerate(cs):
            if fn == 'UnitSetCpMoveSeq' and any('ESCAPE' in str(x) for x in a):
                pid = next((x for f2, b, _ in reversed(cs[:k]) if f2 in ('UnitGetByPID', 'UnitQueryPID')
                            for x in b if isinstance(x, str) and x.startswith('PID_')), None)
                jid = next((u['jid'] for c_ in ('n', 'h', 'c') for us in dispos(folder, c_).values() for u in us if u['pid'] == pid), None)
                if pid in game.people:
                    escapers.append(who(pid, jid))
    escapers = list(dict.fromkeys(escapers))
    # Areas a named kind of unit flees through (UnitQueryPID, then UnitEscape): Part 3 Ch.3's horses.
    fleeing = defaultdict(list)
    for hh in hs:
        if hh['kind'] != 4:
            continue
        cs = hcalls[hh['i']]
        pid = next((x for fn, a, _ in cs if fn == 'UnitQueryPID' for x in a if isinstance(x, str) and x.startswith('PID_')), None)
        if pid in game.people and any(fn == 'UnitEscape' for fn, _, _ in cs):
            ax, ay, bx, by = hh['args'][:4]
            fleeing[pid].append([(x, y) for x in range(ax, bx + 1) for y in range(ay, by + 1)])
    for pid, areas in fleeing.items():
        jid = next((u['jid'] for c_ in ('n', 'h', 'c') for us in dispos(folder, c_).values() for u in us if u['pid'] == pid), None)
        objectives.append({'type': 'escape', 'tiles': [tile(p) for a in areas for p in a],
                           'label': f'Where the {who(pid, jid)} flee (each makes for its own exit, not the nearest: tap one to see which)'})

    # Green units a turn event sends to the nearest fire (Part 3 Ch.9's Crimean knights): {PID: turn}.
    to_fires = {}
    for hh in hs:
        if hh['kind'] == 3 and hh['args'] and hh['args'][0]:
            cs = hcalls[hh['i']]
            for k, (fn, a, _) in enumerate(cs):
                if fn == 'UnitSetCpMoveSeq' and any('TORCHMOVE' in str(x) for x in a):
                    pid = next((x for f2, b, _ in reversed(cs[:k]) if f2 == 'UnitQueryPID' for x in b if str(x).startswith('PID_')), None)
                    if pid:
                        to_fires.setdefault(pid, hh['args'][0])
    # Units an every-action event walks off the map once the enemy is down to a few (Part 3 Ch.10's Valtome):
    # {(x, y): how many enemies are left then}. The count is the number the handler stores before comparing.
    walk_off = {}
    for hh in hs:
        cs = hcalls[hh['i']]
        if hh['kind'] == 7 and any(fn == 'ForceGetCount' for fn, _, _ in cs) and any(fn == 'UnitEscape' for fn, _, _ in cs):
            ops = script.disasm(hh)
            n = next((ops[k + 1][2] for k in range(len(ops) - 2) if ops[k][1] == 'load' and ops[k + 1][1] == 'int'
                      and ops[k + 2][1] == '?47'), None)
            for fn, a, _ in cs:
                if fn == 'UnitGetByPos' and len(a) >= 2 and isinstance(a[-1], int):
                    walk_off[tuple(a[-2:])] = n

    def heads_for(u):
        """The flee area a unit's AI sends it to, when it has one."""
        for seq in u['ai']:
            to = ai_targets().get(seq)
            for area in fleeing.get(u['pid'], []):
                if to in area:
                    return [tile(p) for p in area]
        return None
    for sub, pts in goal_tiles.items():
        kind, label = labels[sub]
        if sub == 45 and all(p in captive_exits for p in pts):
            label = 'Where an enemy carrying a captive escapes (you lose)'
        elif sub == 45 and escapers:
            plural = len(escapers) > 1 or escapers[0].endswith('s')
            label = f"Where {' and '.join(escapers)} {'escape' if plural else 'escapes'}" + (" with what they've looted" if looters else '')
        if any(p in hidden_on_easy for p in pts):
            label += ' (not on Easy)'
        objectives.append({'type': kind, 'tiles': [tile(p) for p in pts], 'label': label})
    for hh in hs:
        if hh['kind'] == 4 and len(hh['args']) >= 5 and hh['args'][4] == 1 and any(fn == 'set' and a == ['gf_gameover'] for fn, a, _ in hcalls[hh['i']]):
            ax, ay, bx, by = hh['args'][:4]
            easy = all('Normal' not in alive for fn, a, alive in hcalls[hh['i']] if fn == 'set' and a == ['gf_gameover'])
            objectives.append({'type': 'defend', 'tiles': [tile((x, y)) for x in range(ax, bx + 1) for y in range(ay, by + 1)],
                               'label': 'Defend (the enemy wins by reaching it)' + (' (not on Easy)' if easy else '')})

    for hh in hs:
        for fn, a, alive in hcalls[hh['i']]:
            if fn == 'SetTerrName' and len(a) == 3 and a[2] == '到達' and on_map((a[0], a[1])) and in_section(hh):
                if not any(o['type'] == 'arrive' for o in objectives):
                    objectives.append({'type': 'arrive', 'tiles': [tile((a[0], a[1]))], 'label': 'Arrive'})
                continue
            if fn == 'SetTerrName' and len(a) == 3 and a[2] == '防衛' and on_map((a[0], a[1])) and in_section(hh):
                if any(o['type'] == 'defend' and tile((a[0], a[1])) in o['tiles'] for o in objectives):
                    continue
                objectives.append({'type': 'defend', 'tiles': [tile((a[0], a[1]))],
                                   'label': 'Defend (the enemy wins by reaching it)' + ('' if 'Normal' in alive else ' (not on Easy)')})

    # Buried treasure (GetRndTreasure, in startup.cmb): one of your units that stops in the area may dig it up.
    # The script rolls 0-100 against a stat of the unit's own.
    for hh in hs:
        got = [a[0] for fn, a, _ in hcalls[hh['i']] if fn == 'GetRndTreasure' and a]
        if hh['kind'] == 4 and got and in_section(hh):
            ax, ay, bx, by = hh['args'][:4]
            objects.append({'type': 'hidden', 'tile': tile(((ax + bx) // 2, (ay + by) // 2)), 'area': rect(ax, ay, bx, by),
                            'contents': ', '.join(game.items.get(i, i) for i in got)})

    # Ballistae and breakable walls and doors.
    for hh in hs:
        for fn, a, _ in hcalls[hh['i']]:
            if fn == 'SetShooter' and len(a) == 4 and on_map((a[0], a[1])) and not any(
                    o['type'] == 'ballista' and o['tile'] == tile((a[0], a[1])) for o in objects):
                dx, dy = fe9maps.FACING[a[2]]
                objects.append({'type': 'ballista', 'tile': tile((a[0], a[1])), 'machine': tile((a[0] + dx, a[1] + dy)),
                                'weapon': game.items.get(a[3], a[3])})
            elif fn == 'SetFragile' and len(a) == 3 and on_map((a[0], a[1])):
                t = tile((a[0], a[1]))
                if any(c['id'] == f'break-{t[0]}-{t[1]}' for c in changes):
                    continue
                door = grid[a[1]][a[0]] == 'd'
                # It becomes what the floor layer has under the wall (the roof layer holds the wall itself).
                becomes = LETTERS.get(under.get((a[0], a[1]), ''), '.')
                changes.append({'id': f'break-{t[0]}-{t[1]}', 'trigger': 'breakable', 'tile': {'default': t},
                                'usableBy': 'Any unit that can attack it',
                                'effect': f'{a[2]} HP. ' + ('A door: open it with a key, or attack it down.' if door
                                                            else f"Attack it down and it becomes {LETTER_NAMES[becomes].lower()}."),
                                'patch': [{'tile': t, 'becomes': becomes}]})

    placement = {d: dispos(folder, c) for d, c in DIFFS.items()}
    common = dispos(folder, 'c')

    def load(names, diff):
        """The units a script's group names place on one difficulty: a '_c' group, one difficulty's own, or a
        base name the game completes for the difficulty being played."""
        code_, picked = DIFFS[diff], []
        for a in names:
            if a.endswith('_c'):
                key = ('c', a)
            elif re.search(r'_[nhm]$', a):
                if not a.endswith('_' + code_):
                    continue
                key = (code_, a)
            else:
                key = (code_, f'{a}_{code_}')
            if key not in picked:
                picked.append(key)
        return [u for src, g in picked for u in (common if src == 'c' else placement[diff]).get(g, [])]

    # The battle's setup: what the openings (Opening0, 1, 2; a second section has its own) do once the map is up.
    openings = [hh for hh in hs if hh['name'].startswith('Opening')]
    second = [hh for hh in openings if any(fn == 'set' and a == ['セクションＢ'] for fn, a, _ in hcalls[hh['i']])]
    if section == 2:
        openings = second
    elif section == 1:
        openings = [hh for hh in openings if hh not in second]
    start_calls = battle_calls([c for hh in openings for c in hcalls[hh['i']]], folder)
    start_groups = [a[0] for fn, a, _ in start_calls if fn in DISPOS_CALLS and a and isinstance(a[0], str) and a[0].startswith(folder + '_')]
    mikata = [g for g in start_groups if 'mikata' in g]
    sally = [a[0] for fn, a, _ in start_calls if fn in ('SallySetByGroupRank', 'SallyAddByGroupRank') and a]
    forced_pids = [a[0] for fn, a, _ in start_calls if fn == 'UnitForcedSallyByPID' and a]
    players = {u['pid'] for d in DIFFS for u in load(mikata + sally, d)}

    # Talks: who can talk to whom, and whether the talk recruits.
    talks = defaultdict(lambda: {'recruit': [], 'talk': []})
    for hh in hs:
        if hh['kind'] != 8 or len(hh['args']) < 2:
            continue
        a, b = (script.string(x) for x in hh['args'][:2])
        moved = {x[0] for fn, x, _ in hcalls[hh['i']] if fn == 'UnitTransferToForceByPID' and x}
        for speaker, target in ((a, b), (b, a)):
            if speaker not in game.people or speaker in moved:
                continue
            name = game.people[speaker]['name']
            kind = 'recruit' if target in moved else 'talk'
            if name not in talks[target][kind]:
                talks[target][kind].append(name)

    def talk_text(pid):
        t = talks.get(pid)
        if not t:
            return None
        others = [x for x in t['talk'] if x not in t['recruit']]
        if t['recruit']:
            return f"Recruit: talk with {' or '.join(t['recruit'])}" + (f" (also talks with {', '.join(others)})" if others else '')
        return f"Talk with {' or '.join(others)}" if others else None

    def to_unit(u, diff_list):
        person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True, 'boss': False})
        cls = game.classes.get(u['jid'], u['jid'])
        boss = person['boss'] or 'SID_BOSS' in u['skills']
        kind = 'ally' if u['side'] in (2, 3) else 'boss' if boss else 'enemy' if person['generic'] else 'named'
        gear = ', '.join(game.items.get(i, i) for i in u['items'])
        unit = {'type': kind, 'name': cls if person['generic'] and kind == 'enemy' else person['name'], 'tile': tile(u['at']),
                'note': f"Lv {u['level']} {cls}" + (f': {gear}' if gear else '')}
        if kind == 'ally' and not person.get('green_named'):
            unit['generic'] = True  # a plain green dot: the person icon is for named green units
        if any('ARSON' in a for a in u['ai']):
            unit['note'] += '. Never attacks: makes for the nearest house and sets it alight.'
        if u['side'] in (2, 3) and u['pid'] in to_fires:
            unit['note'] += f". From turn {to_fires[u['pid']]}, makes for the nearest fire to put it out."
        if tuple(u['at']) in walk_off:
            n = walk_off[tuple(u['at'])]
            unit['note'] += ((". Doesn't fight: walks" if any('NOATTACK' in a for a in u['ai']) else '. Walks') + ' off the map once '
                             + (f'{n} or fewer enemies are left' if n else 'the enemy is nearly beaten')
                             + ", so the rout doesn't need them.")
            if kind == 'boss':
                unit['type'] = 'named'
        if 'SID_IMMORTAL' in u['skills']:
            unit['note'] += ' (has the hidden skill Immortal)'
        if u['drops']:
            unit['drops'] = [game.items.get(i, i) for i in u['drops']]
        if talk_text(u['pid']):
            unit['talk'] = talk_text(u['pid'])
        if heads_for(u):
            unit['goesTo'] = heads_for(u)
        if diff_list is not None:
            unit['difficulties'] = diff_list
        return unit

    def merge(per_diff):
        """Units on both difficulties once; the rest marked with the one they're on."""
        def key(u):
            return (u['pid'], u['jid'], u['at'], u['level'], tuple(u['items']), tuple(u['drops']))
        normal, hard = Counter(key(u) for u in per_diff['Normal']), Counter(key(u) for u in per_diff['Hard'])
        out, used = [], Counter()
        for d in DIFFS:
            for u in per_diff[d]:
                k = key(u)
                both = min(normal[k], hard[k])
                if used[(k, d)] < both:
                    used[(k, d)] += 1
                    if d == 'Normal':
                        out.append((u, None))
                    continue
                out.append((u, [d]))
        return out

    # Groups placed only if someone died earlier stay off the map; who'd stand there goes in a note instead.
    instead = if_alive(script)
    stand_ins = {d: load([g for g in start_groups if g in instead], d) for d in DIFFS}
    start_groups = [g for g in start_groups if g not in instead]
    # Everyone the openings place, where they stand once the openings have walked them into place.
    staged = {d: [{**u, 'at': at} for u, at in stage(load(start_groups, d), start_calls)] for d in DIFFS}

    def starting(d):
        return [u for u in staged[d] if on_map(u['at']) and u['side'] != 0]

    merged = merge({d: starting(d) for d in DIFFS})
    units = [to_unit(u, dl) for u, dl in merged]
    for g, (pid, _) in instead.items():
        for u in units:
            # Who stands on this unit's tile instead, on each difficulty it's on.
            alts = {d: s for d in (u.get('difficulties') or DIFFS) for s in stand_ins[d]
                    if re.sub(r'_[nhc]$', '', s['group']) == g and tile(s['at']) == u['tile']}
            if not alts:
                continue
            s = next(iter(alts.values()))
            alt = game.people.get(s['pid'], {'name': s['pid'], 'generic': True})
            cls = game.classes.get(s['jid'], s['jid'])
            levels = {d: a['level'] for d, a in alts.items()}
            lv = (f'Lv {s["level"]}' if len(set(levels.values())) == 1 else
                  f"Lv {levels['Normal']} on Easy, {levels['Hard']} on Normal / Hard")
            who_ = f'a {cls} ({lv})' if alt['generic'] else f"{alt['name']} ({lv} {cls})"
            u['note'] += f" If {game.people[pid]['name']} has died earlier, {who_} stands here instead."

    # Your units: the deployment slots, and who the game places on a tile itself. Before the base opens there's
    # no preparations screen, so everyone the game places is fixed.
    yours = [u for u in staged['Hard'] if on_map(u['at']) and u['side'] == 0]
    starts = [tile(u['at']) for u in yours]
    named_slots = [u for u in yours if u['pid'] in game.people and not game.people[u['pid']]['generic']]
    # The commander: whoever the setup gives SID_HERO for the chapter (Part 2's), or who has it already (Micaiah).
    given = [c[1][0][1] for c in start_calls if c[0] in ('UnitTstSkill', 'UnitAddSkill') and 'SID_HERO' in c[1]
             and isinstance(c[1][0], tuple) and c[1][0][0] == 'unit']
    hero = given[0] if given else next((u['pid'] for u in named_slots if game.people[u['pid']]['hero']), None)
    # With a preparations screen, the game still places whoever it names, and anyone it sets down outside the
    # deployment slots (the Black Knight in Part 1 Ch.9).
    sally_groups = {re.sub(r'_[nhc]$', '', g) for g in sally}
    fixed_pids = forced_pids + [u['pid'] for u in named_slots if re.sub(r'_[nhc]$', '', u['group']) not in sally_groups]         if ch['prep'] else [u['pid'] for u in named_slots]
    forced = []
    for pid in dict.fromkeys(fixed_pids):
        u = next((u for u in named_slots if u['pid'] == pid), None)
        if pid in game.people and pid != hero:
            forced.append({'name': game.people[pid]['name'], **({'tile': tile(u['at'])} if u else {})})
    lord_pid = next((u for u in named_slots if u['pid'] == hero), None)

    # Flags set by area triggers, turns, door openings and the enemy-count check.
    flag_when = defaultdict(list)
    for hh in hs:
        for fn, a, _ in hcalls[hh['i']]:
            if fn != 'set' or not a or not isinstance(a[0], str) or a[0].startswith('gf_'):
                continue
            if hh['kind'] == 4:
                ax, ay, bx, by, who = hh['args'][:5]
                flag_when[a[0]].append(('After a unit enters the marked area', [{'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)}]))
            elif hh['kind'] == 5 and hh['args'][2] == 11:
                x, y = hh['args'][:2]
                flag_when[a[0]].append((f'After the door at ({tile((x, y))[0]}, {tile((x, y))[1]}) is opened', [{'who': 'player', 'rect': rect(x, y, x, y)}]))
            elif hh['kind'] == 7 and any(f == 'ForceGetCount' for f, _, _ in hcalls[hh['i']]):
                flag_when[a[0]].append(('Once every other enemy is defeated', []))
            elif hh['kind'] == 3 and hh['args'] and hh['args'][0]:
                flag_when[a[0]].append((f"Turn {hh['args'][0]}, {PHASE.get(hh['args'][2], 'turn start')}", []))

    def when(hh):
        """The handler's trigger as a sentence, plus any areas."""
        if hh['kind'] == 4:
            ax, ay, bx, by, who = hh['args'][:5]
            return 'When a unit enters the marked area', [{'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)}]
        if hh['kind'] == 5 and hh['args'][2] == 11:
            x, y = hh['args'][:2]
            return f'When the door at ({tile((x, y))[0]}, {tile((x, y))[1]}) is opened', [{'who': 'player', 'rect': rect(x, y, x, y)}]
        if hh['kind'] == 11:
            pid = script.string(hh['args'][0])
            return f"When {game.people.get(pid, {}).get('name', pid)} is defeated", []
        if hh['kind'] in (3, 7):
            first, last_, phase = (list(hh['args']) + [0, 0, 0])[:3] if hh['kind'] == 3 else (0, 0, 0)
            ph = PHASE.get(phase, 'turn start')
            if first:
                return (f'Turn {first}, {ph}' if first == last_ else f'Turns {first}–{last_}, {ph}'), []
            for f, want in flag_tests(script, hh):
                if want and f in flag_when:
                    texts = [t for t, _ in flag_when[f]]
                    areas = [a for _, ar in flag_when[f] for a in ar]
                    return ' or '.join(dict.fromkeys(texts)), areas
        return 'When an event in the chapter sets it off', []

    # Reinforcements and arrivals: every group a trigger places, with the difficulties that reach it.
    arrivals = defaultdict(list)  # group base -> [(when, areas, difficulties)]
    leaving = defaultdict(set)  # group base -> PIDs the same event sends off again (Sothe's walk-on in Part 1 Ch.2)
    setup_like = {hh['i'] for hh in hs if hh['name'].startswith('Opening')}
    for hh in hs:
        if hh['i'] in setup_like or hh['kind'] in (0, 1, 14, 256, 512, 1024) or not in_section(hh):
            continue
        for fn, a, alive in scenes_removed(hcalls[hh['i']], folder):
            if fn in DISPOS_CALLS and a and isinstance(a[0], str) and a[0].startswith(folder + '_') and alive:
                base = re.sub(r'_[nhc]$', '', a[0])
                if a[0] in start_groups or base in start_groups:
                    continue
                arrivals[base].append((when(hh), alive, a[0]))
                leaving[base] |= {x[0] for f2, x, _ in hcalls[hh['i']] if f2 == 'UnitEscapeByPID' and x}

    carried = {}
    for base in list(arrivals):
        if base.endswith('_child'):
            carried[base[:-len('_child')]] = [game.people.get(u['pid'], {'name': u['pid']})['name'] for u in load([base], 'Hard')]
            del arrivals[base]
    reinforcements, joiners = [], []
    for base, events in arrivals.items():
        per_diff_texts, areas = defaultdict(list), []
        for (text, ar), alive, _ in events:
            for d in alive:
                if text not in per_diff_texts[d]:
                    per_diff_texts[d].append(text)
            areas += [x for x in ar if x not in areas]
        per_diff_when = {d: join_turns(t) for d, t in per_diff_texts.items()}
        names = sorted({n for _, _, n in events})
        per = {d: [u for u in load(names, d) if u['side'] == 1 and on_map(u['at'])] if d in per_diff_when else [] for d in DIFFS}
        whens = set(per_diff_when.values())
        # One sentence when every difficulty agrees; otherwise one per difficulty that gets the group at all.
        when_ = next(iter(whens)) if len(whens) == 1 and set(per_diff_when) == set(DIFFS) else dict(per_diff_when)
        for u in load(names, 'Hard') or load(names, 'Normal'):
            if u['side'] in (0, 2, 3) and on_map(u['at']) and (u['side'] == 0 or u['pid'] not in players) and u['pid'] not in leaving[base]:
                person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True})
                j = {'name': game.classes.get(u['jid'], u['jid']) if person['generic'] else person['name'], 'tile': tile(u['at']),
                     'from': tile(u['from']), 'group': base[len(folder) + 1:],
                     'when': when_}
                if u['side'] != 0:
                    j['ally'] = True
                    if not person.get('green_named'):
                        j['generic'] = True
                if areas:
                    j['areas'] = copy.deepcopy(areas)
                if talk_text(u['pid']):
                    j['talk'] = talk_text(u['pid'])
                if carried.get(base) and not any(k['group'] == j['group'] for k in joiners):
                    j['note'] = f"Carrying {' and '.join(carried[base])}"
                joiners.append(j)
        if not any(per.values()):
            continue
        us = []
        for u, dl in merge(per):
            unit = to_unit(u, dl)
            if u['from'] != u['at']:
                unit['from'] = tile(u['from'])
            us.append(unit)
        group = {'id': base, 'label': '', 'units': us, 'when': when_}
        if areas:
            group['areas'] = copy.deepcopy(areas)
        reinforcements.append(group)

    def first_turn(g):
        m_ = re.match(r'Turns? (\d+)', g['when'] if isinstance(g['when'], str) else g['when'].get('Hard', ''))
        return int(m_.group(1)) if m_ else 99
    reinforcements.sort(key=first_turn)
    for i, g in enumerate(reinforcements):
        g['label'] = f'Group {i + 1}'
    joiners = [j for i, j in enumerate(joiners) if not any((k['name'], k['tile']) == (j['name'], j['tile']) for k in joiners[:i])]

    win, lose = goals(ch)
    for hh in hs:
        if hh['i'] in setup_like or not in_section(hh):
            continue
        cs = hcalls[hh['i']]
        for fn, a, _ in cs:
            if fn == 'BMSetLoseTerm' and len(a) >= 2 and isinstance(a[-1], str) and game.text.get(a[-1]):
                # Added by the event that brings that unit in (Tibarn in Part 3 Ch.11), or partway through.
                arrives = any(f2 in DISPOS_CALLS for f2, _, _ in cs)
                extra = f", or {game.text[a[-1]]}" + (' (after arriving)' if arrives else ' (from partway through)')
                lose = lose.replace(' (Easy:', extra + ' (Easy:', 1)[:-1] + extra + ')' if '(Easy:' in lose else lose + extra
    if section == 2:
        terms = [a[1] for fn, a, _ in start_calls if fn == 'BMSetWinTerm' and len(a) == 2]
        if terms:
            win = {'Rout enemy': 'Rout the enemy', 'Defeat boss': 'Defeat the boss'}.get(game.text.get(terms[0]), game.text.get(terms[0]))
    notes = []
    if any(o['type'] == 'hidden' for o in objects):
        notes.append('Buried treasure (the marked areas): one of your units that stops there may dig it up. fireemblemwod.com gives '
                     'the chance as Skill %, +60 for the Thief line, and more or less with biorhythm.')
    part = ch['part']
    heading = ch['heading'].replace('Ch.', '')
    heading = f"{part}-{heading}" if heading[:1].isdigit() else f"{part}-{heading}"
    m = {
        'id': f"fe10-{heading.lower()}" + (f'-{section}' if section else ''),
        'route': 'Story', 'chapter': 0, 'heading': heading,
        'title': ch['title'] + (f' (part {section} of 2)' if section else ''),
        'width': W, 'height': H,
        'grid': [''.join(r) for r in grid],
        'victory': win, 'defeat': lose, 'objectives': objectives, 'units': units, 'starts': starts,
        'objects': objects, 'changes': changes, 'notes': notes,
    }
    if hero in game.people:
        m['lord'] = game.people[hero]['name']
    if lord_pid:
        m['corrinStart'] = tile(lord_pid['at'])
    if forced:
        m['forced'] = forced
    if reinforcements:
        m['reinforcements'] = reinforcements
    if joiners:
        m['joiners'] = joiners
    play = PLAYABLE.get((code, section) if section else code)
    if not play:
        # No grid fitted yet: keep what units can walk to from anything on the map (Path of Radiance's crop).
        ground = {k for k, info in terrain.items() if info['move']['Infantry'] is not None}
        left, right, bottom, top = reach_bounds(m, ground)
        play = (left - 1, right - 1, H - top, H - bottom)
        m.setdefault('unconfirmed', []).append("The map's edges are where units can reach, not yet checked in-game.")
    if play:
        gx0, gx1, gy0, gy1 = play
        m = crop_to(m, gx0 + 1, gx1 + 1, H - gy1, H - gy0)
    else:
        gx0, gy1 = 0, H - 1
    gx1_, gy0_ = (play[1], play[2]) if play else (W - 1, 0)

    def app(x, y):
        return [x - gx0 + 1, gy1 - y + 1]
    fogged = code in FOG_PER_WOD or any(fn == 'SetSight' and a and a[-1] == 1 for fn, a, _ in start_calls)
    # Torches the setup lights as the map loads (BuildInstTorch(x, y, radius, 0)) start lit.
    for fn, a, _ in start_calls:
        if fn == 'BuildInstTorch' and len(a) == 4 and isinstance(a[0], int):
            for c in m['changes']:
                if c['trigger'] == 'torch' and c['tile']['default'] == app(a[0], a[1]):
                    c['lit'] = True
    # Torches whose flags all win the chapter when set (Part 3 Ch.3's).
    torch_flags = {f for hh in hs if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 55
                   for fn, a, _ in hcalls[hh['i']] if fn == 'set' and a for f in a[:1]}
    to_win = torch_flags and any(torch_flags <= {f for f, want in flag_tests(script, hh) if want}
                                 and any(fn == 'set' and a == ['gf_complete'] for fn, a, _ in hcalls[hh['i']]) for hh in hs)
    if to_win:
        # Each set of supplies is a few tiles whose events set the same flag: lighting any one burns the set.
        sets = defaultdict(list)
        for hh in hs:
            if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 55:
                flag = next(a[0] for fn, a, _ in hcalls[hh['i']] if fn == 'set' and a)
                sets[flag].append(app(hh['args'][0], hh['args'][1]))
        m['changes'] = [c for c in m['changes'] if c['trigger'] != 'torch']
        for k, flag in enumerate(sorted(sets)):
            m['objectives'].append({'type': 'burn', 'tiles': sets[flag],
                                    'label': f'Supplies to burn (set {k + 1} of {len(sets)}): a unit next to them can set them alight. '
                                             'Burning every set wins the chapter.'})
    if not fogged:
        for c in m['changes']:
            if c['trigger'] == 'torch' and not to_win:
                c['effect'] = f"Lights the tiles within {c['radius']} of it."
    elif torches and not to_win:
        # Shade everything the lit torches don't reach.
        m['fog'] = True
        m['notes'].append('Fog of war: the shaded tiles are hidden until one of your units, or a lit torch, sees them. '
                          f'A unit next to a torch can light it, and it lights the tiles within {torches[0][1]} of it.')
    else:
        m['notes'].append('Fog of war: you only see what your units can see (fireemblemwod.com: 3 tiles around each).')
    if any(o['type'] == 'fire' for o in m['objects']):
        m.setdefault('unconfirmed', []).append("What a burning house does to the units beside it (the script's SetBomber(5)) "
                                               "isn't read yet. The fires don't change how the chapter is won or lost.")
    inside = [(x, y) for x, y in roofed if gx0 <= x <= gx1_ and gy0_ <= y <= gy1]
    if inside:
        m['roofed'] = [app(x, y) for x, y in inside]
        m.setdefault('unconfirmed', []).append(
            "The hatched tiles are under a roof that lifts when what's inside is opened (a cell door): check in-game what "
            "they hold. The map shows the floor under the roof.")
    if cloud_rows:
        turns = re.search(r'(\d+) turns', m['victory'])
        m['clouds'] = {'pattern': cloud_rows[gy0_:gy1 + 1], 'left': gx0, 'turns': int(turns.group(1)) if turns else 10}
        m.setdefault('unconfirmed', []).append('The clouds drift one tile left on each player and enemy phase '
                                               '(fireemblemwod.com); whether they also move on the ally phase is unchecked.')
    return m


def main():
    game = Game()
    terrain, groups = build_terrain(game)
    maps = []
    chapters = sorted(c for c in game.chapters if (c[:2] in ('01', '02') or c in ('0301', '0302', '0303', '0304', '0305', '0306', '0307', '0308', '0309', '0310', '0311', '0312')) and game.chapters[c]['folder'] == f'bmap{c}')
    for code in chapters:
        for section in ((1, 2) if code == '0107' else (None,)):
            m = build_chapter(game, terrain, code, section)
            m['chapter'] = len(maps) + 1
            maps.append(m)
            print(f"{m['heading']}: {m['width']}x{m['height']}, {len(m['units'])} units, {len(m.get('reinforcements', []))} groups, "
                  f"{len(m.get('joiners', []))} joiners, {len(m['objects'])} objects, {len(m['changes'])} changes")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'fe10Terrain.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { TerrainInfo } from '../maps/fatesTerrain'\nimport type { TerrainLetter } from '../maps/types'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe10-maps.py from the terrain table in FE10Data.cms. Do not edit by hand.\n */\n\n')
        f.write("/** Radiant Dawn's movement groups: classes in a group pay the same cost on every terrain. */\n")
        f.write(f'export const FE10_MOVE_CLASSES = {json.dumps([g[0] for g in groups], ensure_ascii=False)} as const\n\n')
        f.write('export const FE10_MOVE_CLASS_EXAMPLES: Record<string, string> = {\n')
        for name, _, ex in groups:
            f.write(f"  {json.dumps(name, ensure_ascii=False)}: {json.dumps(', '.join(ex), ensure_ascii=False)},\n")
        f.write('}\n\n/** Def, Avoid, healing (% of max HP each turn) and movement cost (null = can\'t enter) by map letter. */\n')
        f.write('export const FE10_TERRAIN: Partial<Record<TerrainLetter, TerrainInfo>> = {\n')
        for letter, info in terrain.items():
            f.write(f'  {json.dumps(letter)}: {json.dumps(info, ensure_ascii=False)},\n')
        f.write('}\n')
    with open(os.path.join(OUT_DIR, 'fe10Maps.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { ChapterMap } from '../maps/types'\nimport { FE10_TERRAIN } from './fe10Terrain'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe10-maps.py from the game\'s own map, placement and script files.\n')
        f.write(' * Do not edit by hand.\n */\n\nconst RAW = [\n')
        for m in maps:
            f.write('  ' + json.dumps(m, ensure_ascii=False) + ',\n')
        f.write(']\n\nexport const FE10_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE10_TERRAIN }))\n')


if __name__ == '__main__':
    main()
