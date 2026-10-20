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


# Ch.25's boulders, as Serenes Forest's falling-rock diagram draws them (game coordinates: from the
# top-left, 0-based; the start tiles match the script's SetRock calls). Each path is its corners; a
# boulder that leaves the map ends with 'off', one that comes to rest with 'stops'.
BOULDERS = {
    26: [
        ([(5, 10), (7, 10), (7, 13), (6, 13), (6, 14), (4, 14)], 'stops'),
        ([(7, 6), (7, 13), (4, 13), (4, 18), (3, 18), (3, 25)], 'off'),
        ([(8, 6), (8, 26)], 'off'),
        ([(9, 6), (9, 26)], 'off'),
        ([(11, 7), (11, 26)], 'off'),
        ([(13, 6), (13, 19)], 'stops'),
        ([(16, 7), (16, 8), (21, 8), (21, 17), (15, 17), (15, 19), (14, 19)], 'stops'),
        ([(17, 5), (17, 8)], 'stops'),
        ([(18, 5), (18, 8), (21, 8), (21, 11), (17, 11), (17, 13), (21, 13), (21, 16), (16, 16), (16, 17), (15, 17), (15, 18),
          (14, 18), (14, 19), (13, 19), (13, 26)], 'off'),
        ([(21, 10), (21, 11), (17, 11), (17, 13), (20, 13), (20, 17), (14, 17), (14, 26)], 'off'),
        ([(23, 11), (23, 17), (20, 17)], 'stops'),
    ],
}
# A fence model's rotation (top two bits) -> the tile side it stands on.
FENCE_SIDE = {0x00: 'w', 0x80: 'e', 0x40: 'n', 0xC0: 's'}
# Numpad directions in the scripts' walk strings ('2242444').
STEP = {'2': (0, 1), '8': (0, -1), '4': (-1, 0), '6': (1, 0)}


def expand(corners):
    """Corner tiles -> every tile along the path."""
    out = [corners[0]]
    for (x, y) in corners[1:]:
        px, py = out[-1]
        while (px, py) != (x, y):
            px += (x > px) - (x < px)
            py += (y > py) - (y < py)
            out.append((px, py))
    return out


def shift(m, dx, dy):
    """Move every tile on the map by (-dx, -dy) after a crop."""
    def mv(t):
        return [t[0] - dx, t[1] - dy]

    def mv_rect(a):
        l, b, r, t = a['rect']
        a['rect'] = [l - dx, b - dy, r - dx, t - dy]

    for u in m['units']:
        u['tile'] = mv(u['tile'])
    m['starts'] = [mv(t) for t in m['starts']]
    for o in m['objects']:
        o['tile'] = mv(o['tile'])
    for o in m['objectives']:
        o['tiles'] = [mv(t) for t in o['tiles']]
    if 'corrinStart' in m:
        m['corrinStart'] = mv(m['corrinStart'])
    for w in m.get('walls', []):
        w['tile'] = mv(w['tile'])
    for c in m['changes']:
        c['tile'] = {'default': mv(c['tile']['default'])}
        for p in c.get('patch', []):
            p['tile'] = mv(p['tile'])
        if 'path' in c:
            c['path'] = [mv(t) for t in c['path']]
    for g in m.get('reinforcements', []):
        for u in g['units']:
            u['tile'] = mv(u['tile'])
            if 'from' in u:
                u['from'] = mv(u['from'])
        for a in g.get('areas', []):
            mv_rect(a)
    for j in m.get('joiners', []):
        j['tile'] = mv(j['tile'])
        j['from'] = mv(j['from'])
        for a in j.get('areas', []):
            mv_rect(a)


def crop(m, ground, margin=1, reach=True):
    """Trim the map to where things happen: every tile a unit can walk to from anything on the map (or,
    with reach=False, just the things themselves), plus a margin. Ch.13's ships sit in 62x59 tiles of sea."""
    W, H = m['width'], m['height']
    seeds = [tuple(u['tile']) for u in m['units']] + [tuple(t) for t in m['starts']] + [tuple(o['tile']) for o in m['objects']]
    seeds += [tuple(t) for o in m['objectives'] for t in o['tiles']]
    seeds += [tuple(u['tile']) for g in m.get('reinforcements', []) for u in g['units']] + [tuple(j['tile']) for j in m.get('joiners', [])]
    seeds += [tuple(t) for c in m['changes'] for t in c.get('path', [])]
    seeds = [s for s in seeds if 1 <= s[0] <= W and 1 <= s[1] <= H]
    keep = set(seeds)
    if reach:
        def letter(x, y):
            return m['grid'][H - y][x - 1]
        todo = [s for s in seeds if letter(*s) in ground]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 1 <= nx <= W and 1 <= ny <= H and (nx, ny) not in keep and letter(nx, ny) in ground:
                    keep.add((nx, ny))
                    todo.append((nx, ny))
    # ...but no further than a few tiles past the outermost thing on the map (Endgame's open floor runs on
    # far beyond the battle).
    sx = [x for x, _ in seeds]
    sy = [y for _, y in seeds]
    keep = {(x, y) for x, y in keep if min(sx) - 3 <= x <= max(sx) + 3 and min(sy) - 3 <= y <= max(sy) + 3}
    left, right = max(1, min(x for x, _ in keep) - margin), min(W, max(x for x, _ in keep) + margin)
    bottom, top = max(1, min(y for _, y in keep) - margin), min(H, max(y for _, y in keep) + margin)
    if (left, bottom, right, top) == (1, 1, W, H):
        return m
    m['grid'] = [row[left - 1:right] for row in m['grid'][H - top:H - bottom + 1]]
    m['width'], m['height'] = right - left + 1, top - bottom + 1
    shift(m, left - 1, bottom - 1)
    m['walls'] = [w for w in m.get('walls', []) if 1 <= w['tile'][0] <= m['width'] and 1 <= w['tile'][1] <= m['height']]
    if not m['walls']:
        del m['walls']
    return m


def flag_tests(script, h):
    """The flags a handler tests: [(flag, wanted True/False)]."""
    dis, out = script.disasm(h), []
    for k, (_, op, a) in enumerate(dis[:-2]):
        if op == 'str' and dis[k + 1][1] == 'call' and dis[k + 1][2] == 'get/1':
            out.append((a, not (k + 2 < len(dis) and dis[k + 2][1] == 'op29')))
    return out


def section_number(flag):
    return int(flag[-1].translate(str.maketrans('１２３４', '1234')))


def build_chapter(game, terrain, n, section=None):
    """One chapter's map. `section` (1-4) builds one part of Ch.17, the marathon of four sections."""
    ch = game.chapters[n]
    folder = f'bmap{n:02d}'
    script = Script(f'C{n:02d}.cmb')
    handlers = script.handlers()
    hcalls = {h['i']: calls(script, h) for h in handlers}
    # Where units walk: what infantry can enter (not water, which only fliers and pirates cross).
    ground = {k for k, info in terrain.items() if info['move']['Infantry'] is not None}

    # Terrain, with any border of unset tiles trimmed.
    mp = Reloc(map_files(folder, 'map')['map.bin'])
    w, h = struct.unpack_from('>2H', mp.data, 0)

    def panel(x, y):
        idx = struct.unpack_from('>H', mp.data, mp.named['panelindex'] + 2 * (y * w + x))[0]
        return mp.string(mp.named['uniquepanel'] + 12 * idx + 8)

    names = [[strip_digits(panel(x, y)) for x in range(w)] for y in range(h)]

    def unset(cells):
        return all(c == '未設定' for c in cells)

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

    def rect(ax, ay, bx, by):
        return [tile((ax, by))[0], tile((ax, by))[1], tile((bx, ay))[0], tile((bx, ay))[1]]

    # Fences: thin barriers along a tile's side, placed as 3D models (map.bin's mapbuildinst: 12-byte
    # records of x, y, rotation, model index).
    models = [mp.string(o) for o in range(mp.named['mapbuilddesc'], mp.named['mapbuildinst'], 4) if o in mp.ptrs]
    inst_end = min(o for o, _ in mp.tables if o > mp.named['mapbuildinst'])
    walls = []
    for o in range(mp.named['mapbuildinst'], inst_end, 12):
        x, y, rot, idx = mp.data[o:o + 4]
        if idx < len(models) and models[idx].startswith('fence') and on_map((x, y)) and grid[y - y0][x - x0] in ground:
            wall = {'tile': tile((x, y)), 'side': FENCE_SIDE[rot & 0xC0]}
            if wall not in walls:
                walls.append(wall)

    # Tile events: chests, villages, doors and goal tiles.
    objects, objectives = [], []
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
            grid[y - y0][x - x0] = 'd'
        elif sub in goal:
            goals[sub].append(tile((x, y)))
    for sub, tiles in goals.items():
        objectives.append({'type': goal[sub][0], 'tiles': tiles, 'label': goal[sub][1]})
    for hh in handlers:
        if hh['kind'] == 4 and any(fn == 'set' and a == ['gf_gameover'] for fn, a in hcalls[hh['i']]):
            ax, ay, bx, by = hh['args'][:4]
            objectives.append({'type': 'defend', 'tiles': [tile((x, y)) for x in range(ax, bx + 1) for y in range(ay, by + 1)],
                               'label': 'Defend (the enemy wins by reaching it)'})

    # Breakable doors and walls (SetFragile) and Ch.25's boulders: previewed like Fates' Dragon Veins.
    changes = []
    for hh in handlers:
        for fn, a in hcalls[hh['i']]:
            if fn == 'SetFragile' and len(a) == 3 and on_map((a[0], a[1])):
                t = tile((a[0], a[1]))
                door = grid[a[1] - y0][a[0] - x0] == 'd'
                changes.append({'id': f'break-{t[0]}-{t[1]}', 'trigger': 'breakable', 'tile': {'default': t},
                                'usableBy': 'Any unit that can attack it',
                                'effect': f'{a[2]} HP. ' + ('A door: open it with a key, or attack it down.' if door
                                                            else 'Attack it down and it becomes open ground.'),
                                'patch': [{'tile': t, 'becomes': '.'}]})
    for i, (corners, end) in enumerate(BOULDERS.get(n, [])):
        path = [tile(p) for p in expand(corners)]
        changes.append({'id': f'boulder-{i + 1}', 'trigger': 'boulder', 'tile': {'default': path[0]}, 'usableBy': '', 'path': path,
                        'effect': 'Rolls down the marked path; any unit it hits takes 10 damage. '
                                  + ('It rolls off the edge of the map.' if end == 'off' else 'It comes to rest at the end of the path.')})

    placement = {d: dispos(folder, code) for d, code in DIFFS.items()}
    common = dispos(folder, 'c')
    players = {u['pid'] for src in [common] + list(placement.values()) for g, us in src.items() if 'mikata' in g for u in us} | {'PID_IKE'}

    def load(group_names, diff):
        """The units the script's group names place on one difficulty. A name may be the shared '_c' group,
        one difficulty's own ('_n', '_h'; '_m' is the Japanese release's Maniac), or a base name the game
        completes for the difficulty being played. Each group counts once however many calls name it."""
        code, picked = DIFFS[diff], set()
        for a in group_names:
            if a.endswith('_c'):
                picked.add(('c', a))
            elif re.search(r'_[nhm]$', a):
                if a.endswith('_' + code):
                    picked.add((code, a))
            else:
                picked.add((code, f'{a}_{code}'))
        return [u for src, g in sorted(picked) for u in (common if src == 'c' else placement[diff]).get(g, [])]

    # Talks: who can talk to whom, and whether the talk recruits.
    talks = defaultdict(lambda: {'recruit': [], 'talk': []})
    for hh in handlers:
        if hh['kind'] != 8 or len(hh['args']) < 2:
            continue
        a, b = (script.string(x) for x in hh['args'][:2])
        # The talk recruits whoever it moves to your army.
        moved = {x[0] for fn, x in hcalls[hh['i']] if fn == 'UnitTransferToForceByPID' and x}
        for speaker, target in ((a, b), (b, a)):
            if speaker not in game.people:
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
        if talk_text(u['pid']):
            unit['talk'] = talk_text(u['pid'])
        if diff_list is not None:
            unit['difficulties'] = diff_list
        return unit

    def merge(per_diff):
        """Units on both difficulties once; the rest marked with the one they're on."""
        def key(u):
            return (u['pid'], u['jid'], u['at'], u['level'], tuple(u['weapons'] + u['items']), tuple(u['drops']))
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
                    continue
                if d == 'Hard' and used[(k, 'h')] < both:
                    used[(k, 'h')] += 1
                    continue
                out.append((u, [d]))
        return out

    # Who starts on the map: the groups the setup handler places (FinalDisposition, or a Ch.17 section's
    # own opening), minus anyone the openings send away (Nasir in Ch.11), and only the "if X is alive"
    # side of a choice (Gatrie, rather than the Begnion soldier on his tile, in Ch.13).
    if section and section > 1:
        setup = next(hh for hh in handlers if hh['name'] == f'Opening18_{section}')
    else:
        setup = next((hh for hh in handlers if hh['name'] == 'FinalDisposition'), None)
        if not setup:
            # The prologue has no prep screen: its opening handler places everyone.
            setup = next(hh for hh in handlers if any(fn == 'MapLoad' and a == [folder] for fn, a in hcalls[hh['i']]))
    dis = script.disasm(setup)
    branch = {}  # pc -> ('then' | 'else', PID tested)
    for k, (pc, op, a) in enumerate(dis[:-2]):
        if op == 'str' and dis[k + 1][2] == 'UnitCheckLiveByPID/1' and dis[k + 2][1] == 'jz':
            else_at = dis[k + 2][2]
            jmp = next((x for x in dis if x[1] == 'jmp' and pc < x[0] < else_at), None)
            for pc2, _, _ in dis:
                if pc < pc2 < else_at:
                    branch[pc2] = ('then', a)
                elif jmp and else_at <= pc2 < jmp[2]:
                    branch[pc2] = ('else', a)
    start_groups, if_alive, instead_groups, stack = set(), {}, [], []
    for pc, op, a in dis:
        if op in ('str', 'int'):
            stack.append(a)
        elif op == 'call':
            fn, argc = a.split('/')
            argc = int(argc)
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            if fn not in DISPOS_CALLS:
                continue
            for g in args:
                if not (isinstance(g, str) and g.startswith(folder + '_')) or 'mikata' in g:
                    continue
                side = branch.get(pc)
                if side and side[0] == 'else':
                    instead_groups.append(g)
                    continue
                start_groups.add(g)
                if side:
                    if_alive[g] = side[1]
    if section and section > 1:
        sent_away = {a[0] for fn, a in hcalls[setup['i']] if fn == 'UnitEscapeByPID' and a}
    else:
        sent_away = {a[0] for hh in handlers if hh['name'] == 'FinalDisposition' or (hh['name'].startswith('Opening') and not section)
                     for fn, a in hcalls[hh['i']] if fn == 'UnitEscapeByPID' and a}

    def starting(d):
        out, seen = [], set()
        for u in load(start_groups, d):
            # Your own units come from the deployment slots; someone on your roster can still start as an
            # enemy (Shinon in Ch.18).
            if not on_map(u['at']) or u['side'] == 0 or u['pid'] in sent_away or (u['pid'] in players and u['side'] != 1):
                continue
            if u['pid'] in seen and not game.people.get(u['pid'], {}).get('generic', True):
                continue  # the same character placed twice (Ena in Ch.27-2)
            seen.add(u['pid'])
            out.append(u)
        return out

    merged = merge({d: starting(d) for d in DIFFS})
    units = [to_unit(u, dl) for u, dl in merged]
    if if_alive:
        cond_pids = {u['pid'] for g in if_alive for u in load([g], 'Normal')}
        alive = ' and '.join(sorted({game.people[p]['name'] for p in if_alive.values()}))
        instead = ', '.join(sorted({to_unit(u, None)['name'] for u in load(instead_groups, 'Normal')})) or 'no one'
        for unit, (raw, _) in zip(units, merged):
            if raw['pid'] in cond_pids:
                unit['note'] += f' (only if {alive} is still alive; otherwise a {instead} stands here)'

    # Your deployment slots: the mikata_c group (Ike's slot is the lord's start). A Ch.17 section after the
    # first keeps your army where it stood; its opening moves Ike and a few others into place.
    if section and section > 1:
        pos = {}
        for fn, a in hcalls[setup['i']]:
            if fn == 'UnitSetPosDirByPID' and len(a) == 4 and a[0] in players and isinstance(a[1], int):
                pos[a[0]] = (a[1], a[2])
            elif fn == 'UnitMoveDirByPID' and len(a) == 2 and a[0] in pos and isinstance(a[1], str):
                x, y = pos[a[0]]
                for c in a[1]:
                    dx, dy = STEP.get(c, (0, 0))
                    x, y = x + dx, y + dy
                pos[a[0]] = (x, y)
            elif fn == 'UnitEscapeByPID' and a and a[0] in pos:
                del pos[a[0]]
        starts = [tile(p) for p in pos.values() if on_map(p)]
        lord = tile(pos['PID_IKE']) if 'PID_IKE' in pos and on_map(pos['PID_IKE']) else None
    else:
        slots = [u for u in common.get(f'{folder}_mikata_c', []) if on_map(u['at'])]
        if not slots:
            slots = [u for u in placement['Normal'].get(f'{folder}_mikata_n', []) if on_map(u['at'])]
        starts = [tile(u['at']) for u in slots]
        lord = next((tile(u['at']) for u in slots if u['pid'] == 'PID_IKE'), None)
    forced = [] if section and section > 1 else sorted({
        game.people[a[0]]['name'] for hh in handlers for fn, a in hcalls[hh['i']]
        if fn == 'UnitForcedSallyByPID' and a and a[0] in game.people and a[0] != 'PID_IKE'})

    # Flags set by area triggers: {flag: [area]}; and by turn handlers: {flag: text}.
    flag_areas, flag_turns = defaultdict(list), {}
    for hh in handlers:
        for fn, a in hcalls[hh['i']]:
            if fn != 'set' or not a or not isinstance(a[0], str):
                continue
            if hh['kind'] == 4:
                ax, ay, bx, by, who = hh['args'][:5]
                flag_areas[a[0]].append({'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)})
            elif hh['kind'] == 3 and hh['args'] and hh['args'][0]:
                flag_turns[a[0]] = hh['args']

    def when(hh):
        """The handler's trigger as a sentence (per difficulty when it differs), plus any areas."""
        if hh['kind'] == 4:
            ax, ay, bx, by, who = hh['args'][:5]
            return 'When a unit enters the marked area', [{'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)}]
        if hh['kind'] != 3:
            return None, []
        first, last_, phase = (list(hh['args']) + [0, 0, 0])[:3]
        per = difficulty_turns(script, hh)
        ph = PHASE.get(phase, 'turn start')
        if per and len(set(per.values())) > 1:
            return {d: f'Turn {t}, {ph}' for d, t in per.items()}, []
        if per:
            return f'Turn {next(iter(per.values()))}, {ph}', []
        if first:
            # A range fires every turn in it unless the handler marks itself done.
            once = any(fn == 'set' for fn, _ in calls(script, hh))
            return (f'Turn {first}, {ph}' if first == last_ else f"Turns {first}–{last_}, {ph}{'' if once else ', each turn'}"), []
        # Every turn, once a flag is set: by entering an area, or by an earlier turn.
        for f, _ in flag_tests(script, hh):
            if f in flag_areas:
                return 'After a unit enters the marked area', flag_areas[f]
            if f in flag_turns:
                ts, _, tp = (list(flag_turns[f]) + [0, 0, 0])[:3]
                return f'Turn {ts}, {PHASE.get(tp, "turn start")}', []
        return 'When an event in the chapter sets it off', []

    def section_of(hh):
        """Which of Ch.17's sections a handler belongs to, from the flags it tests."""
        tests = flag_tests(script, hh)
        for f, _ in tests:
            m_ = re.match(r'S(\d)増援', f)
            if m_:
                return int(m_.group(1))
        on = [section_number(f) for f, want in tests if f.startswith('セクション') and want]
        off = [section_number(f) for f, want in tests if f.startswith('セクション') and not want]
        if on:
            return max(on)
        if off:
            return min(off) - 1
        return 1

    reinforcements, joiners, seen = [], [], set()
    for hh in handlers:
        # Not the opening (who starts), the chapter end, or cutscenes on another map.
        if hh['name'] == 'FinalDisposition' or hh['name'].startswith('Opening') or hh['kind'] == 1:
            continue
        if any(fn == 'MapLoad' for fn, _ in hcalls[hh['i']]):
            continue
        # One handler brings every section's ally reinforcements; each section takes its own group from it.
        own_allies = section and any(f'mikata_zoen_{section:02d}' in str(a) for _, a in hcalls[hh['i']])
        if section and section_of(hh) != section and not own_allies:
            continue
        here = calls_by_difficulty(script, hh)
        # A cutscene places its own 'event' groups; anything else it places is part of the scene too.
        if hh['kind'] == 0 and any('event' in a for fn, args, _ in here if fn in DISPOS_CALLS for a in args if isinstance(a, str)):
            continue
        # An 'event' group a turn or area brings in can be a real arrival (Jill in Ch.11)...
        loaded = [(a, alive) for fn, args, alive in here if fn in DISPOS_CALLS for a in args
                  if isinstance(a, str) and a.startswith(folder + '_') and ('event' not in a or hh['kind'] in (3, 4))]
        # ...but only alongside the reinforcement group it belongs to (event_jill with z_jill), not a
        # walk-on in a scene (Petrine in Ch.7).
        plain = [a for a, _ in loaded if 'event' not in a]
        loaded = [(a, alive) for a, alive in loaded if 'event' not in a or any(a.split('event_')[1].removesuffix('_c') in p for p in plain)]
        if not loaded or {a for a, _ in loaded} <= start_groups:
            continue
        for base in sorted({re.sub(r'_[nhm]$', '', a) for a, _ in loaded if a not in start_groups}):
            group_names = [a for a, _ in loaded if re.sub(r'_[nhm]$', '', a) == base]
            text, areas = when(hh)
            if 'mikata' in base:
                # Ch.17's ally reinforcements: units you pick join you shortly into the section.
                if section and base.endswith(f'_{section:02d}_c'):
                    for u in load(group_names, 'Normal'):
                        if on_map(u['at']):
                            joiners.append({'name': 'A unit you choose', 'tile': tile(u['at']), 'from': tile(u['from']),
                                            'group': 'Ally reinforcements', 'when': 'Shortly after the section starts (you pick who comes)'})
                continue
            per = {d: [u for u in load([a for a, alive in loaded if re.sub(r'_[nhm]$', '', a) == base and d in alive], d)
                       if u['side'] == 1] for d in DIFFS}
            # Green units that arrive: a new recruit (Marcia in Ch.3) or another army fighting alongside you.
            for u in load(group_names, 'Normal'):
                if u['side'] in (2, 3) and on_map(u['at']) and u['pid'] not in players:
                    person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True})
                    j = {'name': game.classes.get(u['jid'], u['jid']) if person['generic'] else person['name'], 'tile': tile(u['at']),
                         'from': tile(u['from']), 'group': base[len(folder) + 1:], 'ally': True}
                    j['when'] = (text if isinstance(text, str) else text.get('Normal')) if text else 'When an event in the chapter sets it off'
                    if areas:
                        j['areas'] = areas
                    if talk_text(u['pid']):
                        j['talk'] = talk_text(u['pid'])
                    joiners.append(j)
            if not any(per.values()):
                continue
            bosses = {u['name'] for u in units if u['type'] == 'boss'}
            later = [to_unit(u, None)['name'] for d in DIFFS for u in per[d]]
            if later and all(name in bosses for name in later):
                # The same boss again (Ashnard's second form, after the first is beaten).
                text = f'After {later[0]} is first defeated (a second form)'
            if (base, json.dumps(text)) in seen:
                continue
            seen.add((base, json.dumps(text)))
            us = []
            for u, dl in merge(per):
                unit = to_unit(u, dl)
                if u['from'] != u['at']:
                    unit['from'] = tile(u['from'])
                us.append(unit)
            group = {'id': f"{base}-{hh['i']}", 'label': '', 'units': us}
            if text:
                group['when'] = text
            if areas:
                group['areas'] = areas
            reinforcements.append(group)
    # A defend chapter ends after its last turn: a group timed after that never comes (Ch.8's turn 9).
    limit = re.match(r'(?:Defend|Survive) for (\d+) turns', ch['win'] or '')
    if limit:
        reinforcements = [g for g in reinforcements
                          if not (isinstance(g.get('when'), str) and (m_ := re.match(r'Turns? (\d+)', g['when']))
                                  and int(m_.group(1)) > int(limit.group(1)))]
    for i, g in enumerate(reinforcements):
        g['label'] = f'Group {i + 1}'

    title = ch['title'].split(': ', 1)[1] if ': ' in ch['title'] else ch['title']
    # Goals the script sets later (BMSetTerm slot 0, in its sections' order), and an extra loss it clears (slot 3).
    terms = sorted(((hh['name'], a) for hh in handlers for fn, a in hcalls[hh['i']] if fn == 'BMSetTerm' and len(a) == 2), key=lambda x: x[0])
    later_goals = [game.text.get(a[1], a[1]) for _, a in terms if a[0] == 0]
    if section:
        ch = {**ch, 'win': ([ch['win']] + later_goals)[section - 1]}
        later_goals = []
    win, lose = goal_text(ch, units, later_goals, any(a[0] == 3 and a[1] == 'MW_空' for _, a in terms))
    goal_words = ' '.join([win] + later_goals).lower()
    objectives = [o for o in objectives if o['type'] == 'defend' or o['type'] in goal_words]
    heading = ch['title'].split(':')[0] + (f'-{section}' if section else '')
    notes = []
    for g in reinforcements:
        for u in g['units']:
            if u['type'] == 'boss' and 'first defeated' not in str(g.get('when', '')):
                w_ = g.get('when')
                w_ = w_ if isinstance(w_, str) else '; '.join(f'{k}: {v}' for k, v in (w_ or {}).items())
                notes.append(f"{u['name']} isn't on the map at the start: arrives with {g['label']} "
                             f"({w_[0].lower() + w_[1:] if w_ else 'when the script sets it off'}).")
    if section and section > 1:
        notes.append('Your units carry over from the last section: Ike and anyone the opening moves start on the marked '
                     'tiles, the rest where they stood.')
    m = {
        'id': f'fe9-{heading.lower().replace("ch.", "").replace(" ", "")}',
        'route': 'Story', 'chapter': n - 1, 'heading': heading,
        'title': title + (f' (part {section} of 4)' if section else ''),
        'width': W, 'height': H, 'grid': [''.join(r) for r in grid],
        'victory': win, 'defeat': lose, 'objectives': objectives, 'units': units, 'starts': starts,
        'objects': objects, 'changes': changes, 'notes': notes,
    }
    if walls:
        m['walls'] = walls
    if lord:
        m['corrinStart'] = lord
    if forced:
        m['forced'] = [{'name': f} for f in forced]
    if reinforcements:
        m['reinforcements'] = reinforcements
    if joiners:
        m['joiners'] = joiners
    if section:
        # One part of the big map: show just the part this section is fought on.
        return crop(m, ground, margin=2, reach=False)
    return crop(m, ground)


def main():
    game = Game()
    terrain, groups = build_terrain(game)
    maps = []
    for n in range(1, 32):
        # Ch.17 (file 18) is four sections played back to back on one big map: one map each.
        for section in ((1, 2, 3, 4) if n == 18 else (None,)):
            m = build_chapter(game, terrain, n, section)
            maps.append(m)
            print(f"{m['heading']}: {m['width']}x{m['height']}, {len(m['units'])} units, {len(m.get('reinforcements', []))} groups, "
                  f"{len(m.get('joiners', []))} joiners, {len(m['objects'])} objects, {len(m.get('walls', []))} fences, "
                  f"{len(m['changes'])} changes")

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


if __name__ == '__main__':
    main()
