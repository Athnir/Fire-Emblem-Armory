"""
Builds Path of Radiance's maps from the game's own files:

- src/data/fe9/fe9Terrain.ts: the terrain table (Def, Avoid, healing and the cost for each movement
  group), from FE8Data.bin.
- src/data/fe9/fe9Maps.ts: every chapter's terrain grid (zmap/bmapNN/map.cmp), its units on Easy/Normal
  and Hard (dispos.cmp), and from the chapter script (Scripts/Cnn.cmb): the starting groups,
  reinforcements and when they come, chests, villages, doors, objectives and must-deploy units. The win
  and lose conditions come from the chapter table in FE8Data.bin.

Coordinates: the game counts from the top-left corner (0, 0); the app counts from the bottom-left (1, 1)
like the Fates maps, so (x, y) becomes (x + 1, height - y). Formats are in data-raw/fe9/README.md.
Run:  python scripts/build-fe9-maps.py
"""
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe9_cmb import Script  # noqa: E402
from fe9_files import GameData, map_files, read_text  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe9')

# The game's terrain names (without their variant digits) -> the app's map letters. Terrains that share
# a letter must share their stats (checked below).
LETTERS = {
    '平地': '.', '床': '.', '石畳': '.', '雪原': '.', '船': '.', '台座': '.', '訪問': '.',
    '橋': 'b', '橋蓋': 'b', '階段': 'S',
    '玉座': 't', '制圧': 't', '到達': 't', '離脱': 't', '防衛': 't',
    '茂み': 'f', '光の茂み': 'H', '回復': 'H',
    '川': 'w', '水路': 'w', '海': 'a', '池': 'u', '堀': 'u',
    '崖': 'C', '岩': 'C',
    '木': 'k', '屋根': 'B', '小物': 'B', '建物': 'B',
    '柵': 'l', '土嚢': 'l', '穴': 'x',
    '砂漠': 's', '沼': 'M', '山道': 'W', '海岸': 'W',
    '柱': 'p', '宝箱': 'c', '扉': 'd', '壊れる扉': 'd',
    '移動不可': '#', '城門': '#', '壁': '#', '廃墟': '#', '遺跡': '#', '城': '#', '砦': '#', '噴水': '#',
    '花壇': '#', 'アーチ': '#', '投石器': '#', '落石': '#', '未設定': '#', '光の守り': 'K',
}
# The app's name for each letter on Path of Radiance's maps.
LETTER_NAMES = {
    '.': 'Plain / floor', 'b': 'Bridge', 'S': 'Stairs', 't': 'Throne / goal tile', 'f': 'Thicket', 'H': 'Healing thicket',
    'w': 'River', 'a': 'Sea', 'u': 'Pond / moat', 'C': 'Cliff / rock', 'k': 'Tree', 'B': 'Building / roof',
    'l': 'Fence', 'x': 'Hole', 's': 'Desert', 'M': 'Swamp', 'W': 'Mountain path / shore', 'p': 'Pillar', 'c': 'Chest',
    'd': 'Door', '#': 'Wall / structure', 'K': 'Talisman tile', 'v': 'Village',
}
# Movement groups: the game's movement types that share every terrain cost, named as players know them.
GROUP_NAMES = {1: 'Infantry', 3: 'Knights', 4: 'Generals', 5: 'Mages, priests & thieves', 7: 'Horse knights',
               8: 'Paladins & Valkyries', 9: 'Fliers', 11: 'Bandits & Berserkers', 12: 'Beast laguz'}
DIFFS = {'Normal': 'n', 'Hard': 'h'}
DISPOS_CALLS = ('Dispos', 'DisposSetMode', 'DisposContinue', 'DisposContinueSetMode', 'InstantDisposFirstSetMode',
                'DisposAuxiliary', 'InstantDispos', 'InstantDisposFirst', 'InstantDisposRank', 'InstantDisposSetMode',
                'DisposAsynchronous')
PHASE = {0: 'start of the player phase', 1: 'start of the enemy phase', 2: 'start of the ally phase'}


def strip_digits(name):
    return name.rstrip('０１２３４５６７８９')


class Reloc:
    """A pointer-relocated data file (map.bin, dispos_*.bin): see data-raw/fe9/README.md."""

    def __init__(self, d):
        _, size, n_ptrs, n_names = struct.unpack_from('>4I', d, 0)
        ptrs_at = 0x20 + size
        names_at = ptrs_at + n_ptrs * 4
        strings_at = names_at + n_names * 8
        self.data = d[0x20:0x20 + size]
        self.ptrs = set(struct.unpack_from(f'>{n_ptrs}I', d, ptrs_at))
        self.tables = sorted((struct.unpack_from('>I', d, names_at + k * 8)[0],
                              self._c(d, strings_at + struct.unpack_from('>I', d, names_at + k * 8 + 4)[0]))
                             for k in range(n_names))
        self.named = {n: o for o, n in self.tables}

    @staticmethod
    def _c(d, o):
        return d[o:d.index(b'\0', o)].decode('shift_jis')

    def string(self, o):
        """The string a pointer field points at, or None."""
        if o not in self.ptrs:
            return None
        return self._c(self.data, struct.unpack_from('>I', self.data, o)[0])


class Game:
    def __init__(self):
        self.g = GameData()
        self.text = read_text('common.m')
        g, t = self.g, self.text
        self.items = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in g.records('IID_', 'MIID_')}
        self.classes = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in g.records('JID_', 'MJID_')}
        self.move_type = {g.string(g.u32(o)): g.d[o + 66] for o in g.records('JID_', 'MJID_')}
        pids = g.records('PID_', 'MPID_')
        shared = Counter(g.string(g.u32(o + 4)) for o in pids)
        faces = defaultdict(set)
        for o in pids:
            faces[g.string(g.u32(o + 12))].add(g.string(g.u32(o + 4)))
        self.people = {}
        for o in pids:
            mpid, face = g.string(g.u32(o + 4)), g.string(g.u32(o + 12))
            skills = [g.string(g.u32(o + 4 * k)) for k in (7, 8, 9)]
            # A character has a portrait of their own (FID_GREIL, however many records Greil has). Generic
            # units share a faction's portrait across many names (FID_DAYNE: Soldier, Watch, Mercenary...),
            # or a name with others and a portrait that isn't theirs (Pirates, FID_BANDITS2).
            own_face = face == 'FID_' + mpid[5:]
            self.people[g.string(g.u32(o))] = {
                'name': t.get(mpid) or mpid,
                'generic': not face or len(faces[face]) >= 2 or (shared[mpid] >= 3 and not own_face),
                'boss': any(s in ('SID_BOSS', 'SID_FINAL') for s in skills),
            }
        self.terrain = self._terrain()
        self.chapters = self._chapters()

    def _terrain(self):
        """{game terrain name: (avoid, def, heal, costs by movement type)}."""
        g, out = self.g, {}
        o = next(x for x in range(0x20, len(g.d) - 12, 4) if g.string(g.u32(x)) == '移動不可' and (g.string(g.u32(x + 4)) or '').startswith('MT_'))
        while (g.string(g.u32(o + 4)) or '').startswith('MT_'):
            rec = g.d[0x20 + g.u32(o + 8):0x20 + g.u32(o + 8) + 23]
            out[g.string(g.u32(o))] = (rec[0], rec[1], rec[6], tuple(rec[8:23]))
            o += 12
        return out

    def _chapters(self):
        g, t = self.g, self.text
        out = {}
        for o in g.records('MCT', 'bmap'):
            mct = g.string(g.u32(o))
            label = lambda k: g.string(g.u32(o + 4 * k)) if g.u32(o + 4 * k) else None  # noqa: E731
            clean = lambda s: re.sub(r'#X3A|#x', '', t.get(s, s)) if s else None  # noqa: E731
            out[int(mct[3:])] = {
                'title': t[mct], 'win': clean(label(5)), 'lose': clean(label(7)),
                # Extra conditions: slot 0 another way to lose; 1 and 3 Easy's win and loss, 4 and 6 Hard's.
                'lose2': clean(label(8)), 'easy_win': clean(label(9)),
            }
        return out


def build_terrain(game):
    """FE9_TERRAIN by letter, and the movement groups."""
    by_cost = defaultdict(list)
    for mt in range(15):
        by_cost[tuple(v[3][mt] for v in game.terrain.values())].append(mt)
    groups = []  # (name, representative movement type, examples)
    for types in by_cost.values():
        name = next((GROUP_NAMES[m] for m in types if m in GROUP_NAMES), None)
        if name is None:
            continue  # a movement type no playable or enemy class uses
        examples = sorted({c for j, c in game.classes.items() if c and game.move_type.get(j) in types and not c.startswith('JID')
                           and c not in ('Dummy', 'Child', 'Citizen', 'Princess Crimea', 'King Daein')})
        groups.append((name, types[0], examples))
    order = list(GROUP_NAMES.values())
    groups.sort(key=lambda gr: order.index(gr[0]))
    table = {}
    for name, (avo, dfn, heal, costs) in game.terrain.items():
        letter = LETTERS.get(strip_digits(name))
        if not letter:
            continue
        move = {gname: (None if costs[mt] == 255 else costs[mt]) for gname, mt, _ in groups}
        entry = {'name': LETTER_NAMES[letter], 'def': dfn, 'avo': avo, 'heal': heal, 'move': move}
        if letter in table:
            a, b = table[letter], entry
            impassable = all(v is None for v in a['move'].values())
            if a['move'] != b['move'] or a['def'] != b['def'] or a['avo'] != b['avo'] or (a['heal'] != b['heal'] and not impassable):
                raise SystemExit(f'{name} differs from the other terrain on letter {letter!r}')
        else:
            table[letter] = entry
    # A village's visit tile plays like the plain ground it's on.
    table['v'] = {**table['.'], 'name': LETTER_NAMES['v']}
    return table, groups


def dispos(folder, diff):
    """All groups in a chapter's placement file: {group: [unit dict]}."""
    files = map_files(folder, 'dispos')
    name = f'dispos_{diff}.bin'
    if name not in files:
        return {}
    r = Reloc(files[name])
    out = {}
    for i, (o, group) in enumerate(r.tables):
        if group.endswith('date_' + diff):
            continue
        count, p, units = r.data[o], o + 4, []
        for _ in range(count):
            raw = r.data[p:p + 108]
            items = [r.string(p + 12 + 4 * k) for k in range(8)]
            units.append({
                'pid': r.string(p), 'jid': r.string(p + 4),
                'weapons': [x for x in items[:4] if x], 'items': [x for x in items[4:] if x],
                'drops': [items[4 + k] for k in range(4) if items[4 + k] and raw[104 + k]],
                'skills': [x for x in (r.string(p + 44 + 4 * k) for k in range(5)) if x],
                'from': (raw[92], raw[93]), 'at': (raw[94], raw[95]), 'level': raw[96], 'side': raw[97],
            })
            p += 108
        out[group] = units
    return out


LEVELS = ('Normal', 'Hard', 'Easy', 'Maniac')


def calls(script, h):
    """The handler's calls with their literal arguments: [(name, [args])]."""
    return [(fn, args) for fn, args, _ in calls_by_difficulty(script, h)]


def calls_by_difficulty(script, h):
    """[(name, [args], difficulties that reach the call)]. The scripts branch on difficulty with
    `if (Normal()) { ... }` (`call Normal ; jz end`), `if (!Hard()) { ... }` (`... op29 ; jz end`), several
    joined by `orjump`; a block that ends in `return` also takes those difficulties out of what follows."""
    dis = script.disasm(h)
    stack, out, alive, blocks = [], [], set(DIFFS), []
    pcs = [pc for pc, _, _ in dis]
    for k, (pc, op, a) in enumerate(dis):
        while blocks and pc >= blocks[-1][0]:
            alive = blocks.pop()[1]
        if op == 'call' and a.split('/')[0] in LEVELS:
            names, j = {a.split('/')[0]}, k + 1
            while j + 1 < len(dis) and dis[j][1] == 'orjump' and dis[j + 1][1] == 'call' and dis[j + 1][2].split('/')[0] in LEVELS:
                names.add(dis[j + 1][2].split('/')[0])
                j += 2
            negate = j < len(dis) and dis[j][1] == 'op29'
            j += negate
            if j < len(dis) and dis[j][1] == 'jz':
                end = dis[j][2]
                inside = (alive - names) if negate else (alive & names)
                last = max((i for i, x in enumerate(pcs) if x < end), default=j)
                after = alive - inside if dis[last][1] == 'ret' else alive
                blocks.append((end, after))
                alive = inside
        if op in ('str', 'int'):
            stack.append(a)
        elif op == 'call':
            fn, argc = a.split('/')
            argc = int(argc)
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            out.append((fn, args, frozenset(alive)))
    return out


def difficulty_turns(script, h):
    """Turns a handler checks with BMGetTurn, by difficulty: {'Normal': 9, 'Hard': 6} (or {} if none)."""
    dis = script.disasm(h)
    out, cond, else_at = {}, None, None
    for k, (pc, op, a) in enumerate(dis):
        if op == 'call' and a.split('/')[0] in ('Normal', 'Hard', 'Easy', 'Maniac'):
            names = {a.split('/')[0]}
            j = k + 1
            while j + 1 < len(dis) and dis[j][1] == 'orjump' and dis[j + 1][1] == 'call':
                names.add(dis[j + 1][2].split('/')[0])
                j += 2
            if j < len(dis) and dis[j][1] == 'jz':
                cond, else_at = names, dis[j][2]
        if op == 'call' and a == 'BMGetTurn/0' and k + 2 < len(dis) and dis[k + 1][1] == 'int' and dis[k + 2][1] == 'op30':
            turn = dis[k + 1][2]
            if cond is None:
                for d in DIFFS:
                    out.setdefault(d, turn)
            else:
                applies = cond if pc < else_at else {'Normal', 'Hard', 'Maniac', 'Easy'} - cond
                for d in DIFFS:
                    if d in applies:
                        out.setdefault(d, turn)
    return out


def goal_text(ch, units, later_goals, extra_cleared):
    """The chapter's win and lose conditions in plain words. `later_goals`: the goals its script sets as it
    moves on to new sections (Ch.17); `extra_cleared`: the extra loss condition is dropped when it no longer
    applies (Elincia's, when she isn't on the map)."""
    win = {'Rout enemy': 'Rout the enemy'}.get(ch['win'], ch['win'])
    if win == '???':
        # Ch.27-2 hides its goal; it's the duel with its one enemy.
        boss = next(u['name'] for u in units if u['type'] == 'boss')
        win = f"Defeat {'the ' if boss.startswith('Black') else ''}{boss} (the game shows ???)"
    turns = re.match(r'Arrive (\d+) turns', win)
    easy = re.match(r'Arrive (\d+) turns', ch['easy_win'] or '')
    if turns:
        win = f'Arrive within {turns.group(1)} turns' + (f' ({easy.group(1)} on Easy)' if easy and easy.group(1) != turns.group(1) else '')
    if later_goals:
        steps = [w[0].lower() + w[1:] for w in [win] + [{'Rout enemy': 'Rout the enemy'}.get(g, g) for g in later_goals]]
        win = f'In {len(steps)} sections: ' + ', then '.join(steps)
    lose = ch['lose']
    if ch['lose2']:
        over = re.match(r'Exceed (\d+) turns', ch['lose2'])
        extra = ch['lose2'][0].lower() + ch['lose2'][1:] if ch['lose2'].startswith('Enemy') else ch['lose2']
        lose += f", or take more than {over.group(1)} turns" if over else f", or {extra}{' (while on the map)' if extra_cleared else ''}"
    return win, lose


def crop(m):
    """Trim open sea and solid wall from the map's edges, keeping one tile around everything that matters
    (any other terrain, units, objects, goals). Ch.13's ships sit in 62x59 tiles of sea."""
    W, H = m['width'], m['height']
    keep = [(x + 1, H - y) for y, row in enumerate(m['grid']) for x, c in enumerate(row) if c not in 'a#']
    keep += [tuple(u['tile']) for u in m['units']] + [tuple(t) for t in m['starts']] + [tuple(o['tile']) for o in m['objects']]
    keep += [tuple(t) for o in m['objectives'] for t in o['tiles']]
    keep += [tuple(u['tile']) for g in m.get('reinforcements', []) for u in g['units']]
    left, right = max(1, min(x for x, _ in keep) - 1), min(W, max(x for x, _ in keep) + 1)
    bottom, top = max(1, min(y for _, y in keep) - 1), min(H, max(y for _, y in keep) + 1)
    if (left, bottom, right, top) == (1, 1, W, H):
        return m
    dx, dy = left - 1, bottom - 1

    def move(t):
        return [t[0] - dx, t[1] - dy]

    m['grid'] = [row[left - 1:right] for row in m['grid'][H - top:H - bottom + 1]]
    m['width'], m['height'] = right - left + 1, top - bottom + 1
    for u in m['units']:
        u['tile'] = move(u['tile'])
    m['starts'] = [move(t) for t in m['starts']]
    for o in m['objects']:
        o['tile'] = move(o['tile'])
    for o in m['objectives']:
        o['tiles'] = [move(t) for t in o['tiles']]
    if 'corrinStart' in m:
        m['corrinStart'] = move(m['corrinStart'])
    for g in m.get('reinforcements', []):
        for u in g['units']:
            u['tile'] = move(u['tile'])
            if 'from' in u:
                u['from'] = move(u['from'])
        for a in g.get('areas', []):
            l, b, r, t = a['rect']
            a['rect'] = [l - dx, b - dy, r - dx, t - dy]
    return m


def main():
    game = Game()
    terrain, groups = build_terrain(game)
    maps, report = [], []
    for n in range(1, 32):
        ch = game.chapters[n]
        folder = f'bmap{n:02d}'
        script = Script(f'C{n:02d}.cmb')
        handlers = script.handlers()
        hcalls = {h['i']: calls(script, h) for h in handlers}

        # Terrain, with any border of unset tiles trimmed.
        mp = Reloc(map_files(folder, 'map')['map.bin'])
        w, h = struct.unpack_from('>2H', mp.data, 0)
        panel = lambda x, y: mp.string(mp.named['uniquepanel'] + 12 * struct.unpack_from('>H', mp.data, mp.named['panelindex'] + 2 * (y * w + x))[0] + 8)  # noqa: E731
        names = [[strip_digits(panel(x, y)) for x in range(w)] for y in range(h)]
        unset = lambda cells: all(c == '未設定' for c in cells)  # noqa: E731
        x0 = next(x for x in range(w) if not unset(names[y][x] for y in range(h)))
        x1 = next(x for x in range(w - 1, -1, -1) if not unset(names[y][x] for y in range(h)))
        y0 = next(y for y in range(h) if not unset(names[y]))
        y1 = next(y for y in range(h - 1, -1, -1) if not unset(names[y]))
        W, H = x1 - x0 + 1, y1 - y0 + 1
        grid = [[LETTERS[names[y][x]] for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]

        def tile(p):
            return [p[0] - x0 + 1, H - (p[1] - y0)]

        def on_map(p):
            return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

        # Tile events: chests, villages, doors and goal tiles.
        objects, objectives, doors = [], [], []
        destroyable = {(hh['args'][0], hh['args'][1]) for hh in handlers if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 37}
        goal = {13: ('seize', 'Seize'), 14: ('escape', 'Escape'), 41: ('arrive', 'Arrive')}
        goals = defaultdict(list)
        for hh in handlers:
            if hh['kind'] != 5 or len(hh['args']) < 3:
                continue
            x, y, sub = hh['args'][:3]
            got = [a[0] for fn, a in hcalls[hh['i']] if fn == 'MindGetItem' and a]
            gold = [a[0] for fn, a in hcalls[hh['i']] if fn == 'MindGetMoney' and a]
            reward = ', '.join(game.items.get(i, i) for i in got) or (f'{gold[0]} gold' if gold else '')
            if sub == 12:
                objects.append({'type': 'chest', 'tile': tile((x, y)), 'contents': reward})
                grid[y - y0][x - x0] = 'c'
            elif sub == 9:
                v = {'type': 'village', 'tile': tile((x, y)), 'reward': reward}
                if (x, y) in destroyable:
                    v['note'] = 'Bandits can destroy it before you visit.'
                objects.append(v)
                grid[y - y0][x - x0] = 'v'
            elif sub == 11:
                doors.append(tile((x, y)))
                grid[y - y0][x - x0] = 'd'
            elif sub in goal:
                goals[sub].append(tile((x, y)))
        for sub, tiles in goals.items():
            objectives.append({'type': goal[sub][0], 'tiles': tiles, 'label': goal[sub][1]})
        # Defend: an area the enemy ends the chapter by reaching.
        defend = [hh for hh in handlers if hh['kind'] == 4 and any(fn == 'set' and a == ['gf_gameover'] for fn, a in hcalls[hh['i']])]
        for hh in defend:
            ax, ay, bx, by = hh['args'][:4]
            objectives.append({'type': 'defend', 'tiles': [tile((x, y)) for x in range(ax, bx + 1) for y in range(ay, by + 1)],
                               'label': 'Defend (the enemy wins by reaching it)'})

        # Who starts on the map: the groups the chapter's FinalDisposition handler places.
        final = next((hh for hh in handlers if hh['name'] == 'FinalDisposition'), None)
        start_groups = set()
        setup_calls = hcalls[final['i']] if final else []
        if not final:
            # The prologue has no prep screen: its opening handler places everyone.
            setup_calls = next(hcalls[hh['i']] for hh in handlers if any(fn == 'MapLoad' and a == [folder] for fn, a in hcalls[hh['i']]))
        for fn, args in setup_calls:
            if fn in ('InstantDisposRank', 'DisposAsynchronous', 'InstantDisposFirstSetMode', 'DisposSetMode', 'DisposContinueSetMode',
                      'InstantDispos', 'InstantDisposFirst', 'Dispos'):
                start_groups |= {a for a in args if isinstance(a, str) and a.startswith(folder + '_') and 'mikata' not in a}

        placement = {d: dispos(folder, code) for d, code in DIFFS.items()}
        common = dispos(folder, 'c')

        def load(names, diff):
            """The units the script's group names place on one difficulty. A name may be the shared '_c' group,
            one difficulty's own ('_n', '_h'; '_m' is the Japanese release's Maniac), or a base name the game
            completes for the difficulty being played. Each group counts once however many calls name it."""
            code, picked = DIFFS[diff], set()
            for a in names:
                if a.endswith('_c'):
                    picked.add(('c', a))
                elif re.search(r'_[nhm]$', a):
                    if a.endswith('_' + code):
                        picked.add((code, a))
                else:
                    picked.add((code, f'{a}_{code}'))
            return [u for src, g in sorted(picked) for u in (common if src == 'c' else placement[diff]).get(g, [])]

        def to_unit(u, diff_list):
            person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True, 'boss': False})
            cls = game.classes.get(u['jid'], u['jid'])
            boss = person['boss'] or 'SID_BOSS' in u['skills']
            if u['side'] in (2, 3):
                kind = 'ally'
            elif boss:
                kind = 'boss'
            elif not person['generic']:
                kind = 'named'
            else:
                kind = 'enemy'
            gear = ', '.join(game.items.get(i, i) for i in u['weapons'] + u['items'])
            unit = {'type': kind, 'name': cls if person['generic'] and kind != 'boss' else person['name'], 'tile': tile(u['at']),
                    'note': f"Lv {u['level']} {cls}" + (f': {gear}' if gear else '')}
            if u['drops']:
                unit['drops'] = [game.items.get(i, i) for i in u['drops']]
            if diff_list is not None:
                unit['difficulties'] = diff_list
            return unit

        def merge(per_diff):
            """Units on both difficulties once; the rest marked with the one they're on."""
            key = lambda u: (u['pid'], u['jid'], u['at'], u['level'], tuple(u['weapons'] + u['items']), tuple(u['drops']))  # noqa: E731
            normal = Counter(key(u) for u in per_diff['Normal'])
            hard = Counter(key(u) for u in per_diff['Hard'])
            out, used = [], Counter()
            for d in DIFFS:
                for u in per_diff[d]:
                    k = key(u)
                    both = min(normal[k], hard[k])
                    if used[k] < both:
                        if d == 'Normal':
                            used[k] += 1
                            out.append((u, None))
                        else:
                            continue
                    else:
                        if d == 'Hard' and used[(k, 'h')] < both:
                            used[(k, 'h')] += 1
                            continue
                        out.append((u, [d]))
            return out

        start_units = {d: [u for u in load(start_groups, d) if on_map(u['at']) and u['side'] != 0] for d in DIFFS}
        units = [to_unit(u, dl) for u, dl in merge(start_units)]

        # Your deployment slots: the mikata_c group (Ike's slot is the lord's start).
        slots = [u for u in common.get(f'{folder}_mikata_c', []) if on_map(u['at'])]
        if not slots:
            slots = [u for u in placement['Normal'].get(f'{folder}_mikata_n', []) if on_map(u['at'])]
        starts = [tile(u['at']) for u in slots]
        lord = next((tile(u['at']) for u in slots if u['pid'] == 'PID_IKE'), None)
        forced = sorted({game.people[a[0]]['name'] for hh in handlers for fn, a in hcalls[hh['i']]
                         if fn == 'UnitForcedSallyByPID' and a and a[0] in game.people and a[0] != 'PID_IKE'})

        # Flags set by area triggers: {flag: [area]}; and by turn handlers: {flag: text}.
        flag_areas, flag_turns = defaultdict(list), {}
        for hh in handlers:
            for fn, a in hcalls[hh['i']]:
                if fn != 'set' or not a or not isinstance(a[0], str):
                    continue
                if hh['kind'] == 4:
                    ax, ay, bx, by, who = hh['args'][:5]
                    l, t_ = tile((ax, by))[0], tile((ax, ay))[1]
                    r, b = tile((bx, ay))[0], tile((bx, by))[1]
                    flag_areas[a[0]].append({'who': 'enemy' if who == 1 else 'player', 'rect': [l, b, r, t_]})
                elif hh['kind'] == 3 and hh['args'] and hh['args'][0]:
                    flag_turns[a[0]] = hh['args']

        def when(hh):
            """The handler's trigger as a sentence (per difficulty when it differs), plus any areas."""
            areas = []
            if hh['kind'] == 4:
                ax, ay, bx, by, who = hh['args'][:5]
                areas.append({'who': 'enemy' if who == 1 else 'player',
                              'rect': [tile((ax, by))[0], tile((ax, by))[1], tile((bx, ay))[0], tile((bx, ay))[1]]})
                return 'When a unit enters the marked area', areas
            if hh['kind'] != 3:
                return None, areas
            s, e, phase = (list(hh['args']) + [0, 0, 0])[:3]
            per = difficulty_turns(script, hh)
            ph = PHASE.get(phase, 'turn start')
            if per and len(set(per.values())) > 1:
                return {d: f'Turn {t}, {ph}' for d, t in per.items()}, areas
            if per:
                return f'Turn {next(iter(per.values()))}, {ph}', areas
            if s:
                # A range fires every turn in it unless the handler marks itself done.
                once = any(fn == 'set' for fn, _ in calls(script, hh))
                return (f'Turn {s}, {ph}' if s == e else f"Turns {s}–{e}, {ph}{'' if once else ', each turn'}"), areas
            # Every turn, once a flag is set: by entering an area, or by an earlier turn.
            flags = [a for _, op, a in script.disasm(hh) if op == 'str'][:4]
            for f in flags:
                if f in flag_areas:
                    return 'After a unit enters the marked area', flag_areas[f]
                if f in flag_turns:
                    ts, te, tp = (list(flag_turns[f]) + [0, 0, 0])[:3]
                    return f'Turn {ts}, {PHASE.get(tp, "turn start")}', areas
            return 'When an event in the chapter sets it off', areas

        reinforcements, seen = [], set()
        for hh in handlers:
            # Not the opening (who starts), the chapter end, or cutscenes on another map.
            if hh['name'] == 'FinalDisposition' or hh['name'].startswith('Opening') or hh['kind'] == 1:
                continue
            if any(fn == 'MapLoad' for fn, _ in hcalls[hh['i']]):
                continue
            here = calls_by_difficulty(script, hh)
            # A cutscene places its own 'event' groups; anything else it places is part of the scene too.
            if hh['kind'] == 0 and any('event' in a for fn, args, _ in here if fn in DISPOS_CALLS for a in args if isinstance(a, str)):
                continue
            # An 'event' group a turn or area brings in can be a real arrival (Jill in Ch.11).
            loaded = [(a, alive) for fn, args, alive in here if fn in DISPOS_CALLS for a in args
                      if isinstance(a, str) and a.startswith(folder + '_') and 'mikata' not in a and ('event' not in a or hh['kind'] in (3, 4))]
            # ...but only alongside the reinforcement group it belongs to (event_jill with z_jill), not a
            # walk-on in a scene (Petrine in Ch.7).
            plain = [a for a, _ in loaded if 'event' not in a]
            loaded = [(a, alive) for a, alive in loaded if 'event' not in a or any(a.split('event_')[1].removesuffix('_c') in p for p in plain)]
            if not loaded or {a for a, _ in loaded} <= start_groups:
                continue
            bases = sorted({re.sub(r'_[nhm]$', '', a) for a, _ in loaded if a not in start_groups})
            for base in bases:
                per = {d: [u for u in load([a for a, alive in loaded if re.sub(r'_[nhm]$', '', a) == base and d in alive], d)
                           if u['side'] == 1] for d in DIFFS}
                if not any(per.values()):
                    continue
                text, areas = when(hh)
                bosses = {u['name'] for u in units if u['type'] == 'boss'}
                later = [to_unit(u, None)['name'] for d in DIFFS for u in per[d]]
                if later and all(name in bosses for name in later):
                    # The same boss again (Ashnard's second form, after the first is beaten).
                    text = f'After {later[0]} is first defeated (a second form)'
                gid = f"{base}-{hh['i']}"
                if (base, json.dumps(text)) in seen:
                    continue
                seen.add((base, json.dumps(text)))
                us = []
                for u, dl in merge(per):
                    unit = to_unit(u, dl)
                    if u['from'] != u['at']:
                        unit['from'] = tile(u['from'])
                    us.append(unit)
                group = {'id': gid, 'label': base[len(folder) + 1:].replace('_c', '').replace('zoen', 'Group ').replace('z', 'Group '), 'units': us}
                if text:
                    group['when'] = text
                if areas:
                    group['areas'] = areas
                reinforcements.append(group)
        # A defend chapter ends after its last turn: a group timed after that never comes (Ch.8's turn 9).
        last = re.match(r'(?:Defend|Survive) for (\d+) turns', ch['win'] or '')
        if last:
            reinforcements = [g for g in reinforcements
                              if not (isinstance(g.get('when'), str) and (m := re.match(r'Turns? (\d+)', g['when'])) and int(m.group(1)) > int(last.group(1)))]
        for i, g in enumerate(reinforcements):
            g['label'] = f'Group {i + 1}'

        number = n - 1
        title = ch['title'].split(': ', 1)[1] if ': ' in ch['title'] else ch['title']
        # Goals the script sets later (BMSetTerm slot 0, in its sections' order), and an extra loss it clears (slot 3).
        terms = sorted(((hh['name'], a) for hh in handlers for fn, a in hcalls[hh['i']] if fn == 'BMSetTerm' and len(a) == 2), key=lambda x: x[0])
        later_goals = [game.text.get(a[1], a[1]) for _, a in terms if a[0] == 0]
        win, lose = goal_text(ch, units, later_goals, any(a[0] == 3 and a[1] == 'MW_空' for _, a in terms))
        # Goal tiles only for the goals this chapter has (Ch.27-2's escape tiles aren't its goal).
        goal_words = ' '.join([win] + later_goals).lower()
        objectives = [o for o in objectives if o['type'] == 'defend' or o['type'] in goal_words]
        heading = ch['title'].split(':')[0]
        m = {
            'id': f'fe9-{heading.lower().replace("ch.", "").replace(" ", "")}',
            'route': 'Story', 'chapter': number, 'heading': heading, 'title': title,
            'width': W, 'height': H, 'grid': [''.join(r) for r in grid],
            'victory': win, 'defeat': lose, 'objectives': objectives, 'units': units, 'starts': starts,
            'objects': objects, 'changes': [], 'notes': [],
        }
        if lord:
            m['corrinStart'] = lord
        if forced:
            m['forced'] = [{'name': f} for f in forced]
        if reinforcements:
            m['reinforcements'] = reinforcements
        maps.append(crop(m))
        report.append(f"{heading}: {m['width']}x{m['height']}, {len(units)} units, {len(reinforcements)} groups, {len(objects)} objects")

    with open(os.path.join(OUT_DIR, 'fe9Terrain.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { TerrainInfo } from '../maps/fatesTerrain'\nimport type { TerrainLetter } from '../maps/types'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe9-maps.py from the terrain table in FE8Data.bin. Do not edit by hand.\n */\n\n')
        f.write("/** Path of Radiance's movement groups: classes in a group pay the same cost on every terrain. */\n")
        f.write(f'export const FE9_MOVE_CLASSES = {json.dumps([g[0] for g in groups], ensure_ascii=False)} as const\n\n')
        f.write('export const FE9_MOVE_CLASS_EXAMPLES: Record<string, string> = {\n')
        for name, _, ex in groups:
            f.write(f"  {json.dumps(name, ensure_ascii=False)}: {json.dumps(', '.join(ex), ensure_ascii=False)},\n")
        f.write('}\n\n/** Def, Avoid, healing (% of max HP each turn) and movement cost (null = can\'t enter) by map letter. */\n')
        f.write('export const FE9_TERRAIN: Partial<Record<TerrainLetter, TerrainInfo>> = {\n')
        for letter, info in terrain.items():
            f.write(f'  {json.dumps(letter)}: {json.dumps(info, ensure_ascii=False)},\n')
        f.write('}\n')
    with open(os.path.join(OUT_DIR, 'fe9Maps.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { ChapterMap } from '../maps/types'\nimport { FE9_TERRAIN } from './fe9Terrain'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe9-maps.py from the game\'s own map, placement and script files.\n')
        f.write(' * Do not edit by hand.\n */\n\nconst RAW = [\n')
        for m in maps:
            f.write('  ' + json.dumps(m, ensure_ascii=False) + ',\n')
        f.write(']\n\nexport const FE9_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE9_TERRAIN }))\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
