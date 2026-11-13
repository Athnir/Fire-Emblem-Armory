"""
Builds src/data/maps/gameTerrain.ts from the game's own terrain files: for each map, the tile grid in
the app's terrain letters plus each letter's exact name, Def, Avo, heal and movement costs.

Needs the game files dumped from your own copy into data-raw/fates/romfs/ (git-ignored; see
data-raw/fates/README.md). Run:  python scripts/build-fates-terrain.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_map_convert import parse_tid  # noqa: E402
from fates_maps import MAPS, PACK, find_script, terrain, terrain_script, text_for  # noqa: E402
from fates_movecost import load as load_costs  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_tricks import tricks as read_tricks  # noqa: E402
from fates_cmb import Script  # noqa: E402
from terrain_codes import encode, encode_row  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameTerrain.ts')
GROUND = os.path.join(ROOT, 'data-raw', 'fates-ground.json')


WATER = {'湖', '海', '泉', '氷海', '湖地専', '海の道', '湖配置'}
SKY = {'空', '竜巻', '宇宙'}
LAUNCHER = {'弓砲台': 'L', '魔道砲台': 'O', '暗器砲台': 'U'}
# What a tile turns into after a Dragon Vein (the part after '／' in its terrain name).
AFTER = {'平地': '.', '床': '1', '暗夜床': '1', '回復床': 'H', '回復床50': 'H', '橋': 'b', '空': 'x', '湖': 'a',
         '海': 'a', '河': 'w', '壁': '#', '隆起': '#', '砦': 'F', '済砦': 'F', '宝箱': 'c', '林': 'f', '建物': 'B',
         '太柱': '#', '氷丘': 'I', '溶岩床': 'o', '海の道': '.', '氷結泉': '.', '魔方陣': '.', '竜巻': 'z', '嵐': 'z',
         '毒沼配置': 'P', '宇宙': 'x'}
VEIN, AREA, TOGGLE = 11, 12, 29
# Terrain that can be broken down by attacking it (its name has a '｜' part saying what it becomes).
BREAKABLE = {'壁', '低壁', '建物', '古木', '土塁', '防壁'}
# Revelation 9's whirlwinds: the battle-start handler (kind 8) turns all 50 edge tiles to sky, then calls a helper with computed tiles
# to raise the first two winds, x 8-12 on the top row and x 17-21 on the bottom (in the files' top-down rows 1 and 29). Read live
# on turn 1 (Normal and Lunatic alike): those ten are whirlwinds, the other forty sky.
OPENING_STORMS = {'C009': {(x, 1) for x in range(8, 13)} | {(x, 29) for x in range(17, 22)}}
# Terrain the game's text has no English line for: Birthright 17's lake (the one Conquest 8 has frozen) and a fort in Witches' Trial.
# Revelation 16's flame walls: each one's flag in the chapter script ('炎壁０１' to '炎壁２０').
WALL_FLAG = '炎壁'
UNNAMED = {'湖地専': 'Lake', '済砦': 'Fort', '剣の間2': 'Chamber'}


def letter(name, qual, cost):
    """Pick the app letter for one terrain kind from its base name and movement-cost class."""
    if name in ('扉', '襖'):
        return 'd'
    if cost in (0, 1, 14, 15):
        # Rubble nothing crosses (Birthright's Endgame, Revelation 27) and Revelation 10's ice to dig through get their own letters.
        return {'水壁': 'D', '瘴気': 'D', '闇': 'X', '瓦礫': 'R', '氷': 'J'}.get(name, '#')
    if name in LAUNCHER:
        return LAUNCHER[name]
    if cost in (2, 12, 13):
        if name == '宝箱':
            return 'c'
        if name in WATER:
            return 'a'
        if name in SKY:
            return 'x'
        if name in ('低壁',):
            return 'l'
        if name in ('崖', '高山'):
            return 'C'
        if name in ('深い森',):
            return 'k'
        if name in ('建物', '低建物'):
            return 'B'
        return 'r'
    if cost == 3:
        return 'z'
    if cost == 4:
        if name.startswith('毒沼'):
            return 'P'
        # A floor (床, 暗夜床) is its own code, apart from the plain (the user's call: each kind as the game draws it, its own colour).
        return {'段差': 'E', '亀裂': 'Z', '階段': 'S', '門口': 'e', '村': 'v', '廃村': 'V', '閉じ村': 'V', '剣の間': 'j', '回復床': 'H',
                '橋': 'b', '扉': 'd', '襖': 'd', '守護床': 'K', '竹槍': 'q', '剣の間2': 'N', '床': '1', '暗夜床': '1'}.get(name, '.')
    if cost == 5:
        # A forest's costs: hot springs, Birthright 21's lava floor (it hurts) and Birthright 12's ice hills (no bonus).
        return {'熱水泉': 'M', '溶岩床': 'o', '氷丘': 'I'}.get(name, 'f')
    if cost == 6:
        return {'撒菱': 'T', '水たまり': 'u'}.get(name, 'p')
    if cost == 7:
        return 's'
    if cost == 8:
        return 'n' if '山' in name or name == '石垣' else 'W'
    if cost == 9:
        return 'w'
    if cost == 10:
        return {'砦': 'F', '済砦': 'F', '穴': 'F', '座布団': 'Q', '廃墟門': 'G', '城門': 'g', '玉座': 't',
                '召喚床': 'Y'}.get(name, 'F')
    return '?'


def signed(b):
    return b - 256 if b & 0x80 else b


def main():
    costs = load_costs(os.path.join(RAW, 'GameData.bin.lz'))
    out = {}
    for map_id, (code, _, _) in MAPS.items():
        pack = PACK.get(map_id)
        text = text_for(pack)
        t = read_terrain(terrain(code, pack))
        W, H = t['w'] - 2, t['h'] - 2
        kinds = {}
        def after_letter(state):
            """The letter of what a tile becomes ('／'): the map's own terrain of that name when it has one (Revelation 16's flames
            die down to Canyon, Conquest 25's Chamber turns into its Avo -20 form), else the usual table."""
            if not state:
                return None
            other = next((u for u in t['types'] if parse_tid(u['tid'])[:3] == (state, None, None)), None)
            if other:
                oname, _, _, _, oqual = parse_tid(other['tid'])
                L2 = letter(oname, oqual, other['raw'][4] & 0xFF)
                if L2 != '?':
                    return L2
            return AFTER.get(state)

        rows = []
        firsts = {}
        afters = {}
        breaks = {}
        knock_on = {}
        dark = []
        spent = {}
        for r in range(1, t['h'] - 1):
            row = ''
            for c in range(1, t['w'] - 1):
                ty = t['types'][t['rows'][r][c]]
                name, after, broken, vein, qual = parse_tid(ty['tid'])
                if name == '闇' and after:
                    # Revelation's darkness: the map keeps the terrain underneath, shaded until it lifts.
                    under = next((u for u in t['types'] if parse_tid(u['tid'])[0] == after), None)
                    if under:
                        dark.append((c, H + 1 - r))
                        ty = under
                        name, after, broken, vein, qual = parse_tid(ty['tid'])
                barrier = name == '防壁'
                if barrier:
                    name, after = '床', '壁'  # Endgame barriers: floor until a vein raises them
                r4 = ty['raw'][4]
                cost = r4 & 0xFF
                L = '.' if barrier else letter(name, qual, cost)
                frozen = name == '湖地専' and code == 'B008'
                if frozen:
                    # Conquest 8's frozen lake: ground units walk on it until a vein melts it into lake. Birthright
                    # 17 shares the map, but there it starts as lake and the vein freezes it.
                    L, cost, after = 'i', 4, '湖'
                if L == '?':
                    raise SystemExit(f'{code}: no letter for {ty["tid"]} (cost class {cost})')
                # The game calls both rivers (河) and puddles (水たまり) 'Water'; the puddles get their own name.
                en = 'Frozen lake' if frozen else 'Shallow water' if name == '水たまり' else text.get('MTID_' + name) or text.get('MTID_' + name.replace('配置', '')) or \
                    ('Acid Bog' if name.startswith('毒沼') else 'Floor' if name == '障壁用床' else UNNAMED.get(name, name))
                if name in ('良薬', '劇薬'):
                    en, cost, L = 'Floor', 4, '.'  # pots are objects; the floor under them is what's left
                info = {'name': en, 'def': signed(r4 >> 8 & 0xFF), 'avo': signed(r4 >> 16 & 0xFF),
                        'heal': signed(r4 >> 24 & 0xFF), 'move': costs(cost)}
                if name in ('良薬', '劇薬'):
                    info.update({'def': 0, 'avo': 0, 'heal': 0})
                if barrier:
                    info.update({'def': 0, 'avo': 0, 'heal': 0, 'move': costs(4)})
                A = after_letter((after or '').replace('＃竜脈', ''))
                if A and A != L and name not in ('扉', '襖'):
                    afters[(c, H + 1 - r)] = A
                # '｜' names what a tile becomes once broken: walls, partitions, buildings, an old tree, an earthwork.
                B = AFTER.get(broken or '') or {'段差': 'E'}.get(broken or '')
                if name in BREAKABLE and B and B != L:
                    breaks[(c, H + 1 - r)] = B
                elif B and B != L and name not in ('扉', '襖', '良薬', '劇薬') and not barrier:
                    knock_on[(c, H + 1 - r)] = B  # changes when something nearby breaks (the river under Conquest 19's tree)
                prev = kinds.get(L)
                blocked = all(v is None for v in info['move'].values())
                # Its second state ('／', else what it breaks into, '｜'; a village closes): a challenge battle has the chapter's
                # map with every trick in it spent (read live: Revelation 20's every bridge down at once, its veins and villages
                # used; Paralogue 14's bog all gone and its village closed).
                second = after or broken or {'村': '閉じ村'}.get(name)
                if second and name not in ('良薬', '劇薬') and not barrier:
                    other = next((u for u in t['types'] if parse_tid(u['tid'])[:3] == (second, None, None)), None) or                         next((u for u in t['types'] if parse_tid(u['tid'])[0] == second), None)
                    if other:
                        oname, _, _, _, oqual = parse_tid(other['tid'])
                        o4 = other['raw'][4]
                        S = letter(oname, oqual, o4 & 0xFF)
                        sinfo = {'name': text.get('MTID_' + oname) or UNNAMED.get(oname, oname), 'def': signed(o4 >> 8 & 0xFF),
                                 'avo': signed(o4 >> 16 & 0xFF), 'heal': signed(o4 >> 24 & 0xFF), 'move': costs(o4 & 0xFF)}
                    else:
                        S, sinfo = AFTER.get(second) or {'段差': 'E', '閉じ村': 'V'}.get(second), None
                    if S and S not in ('?', L):
                        spent[(c, H + 1 - r)] = (S, sinfo)
                # Nothing can enter either: they're one obstacle, whatever bonuses the game lists on them.
                if prev and not blocked and (prev['def'], prev['avo'], prev['heal'], prev['move']) != (info['def'], info['avo'], info['heal'], info['move']):
                    raise SystemExit(f'{code}: letter {L} covers two different terrains: {prev} / {info}')
                if not prev:
                    kinds[L] = prev = dict(info, names={}, where={})
                prev['names'][en] = prev['names'].get(en, 0) + 1
                prev['where'].setdefault(en, []).append((c, H + 1 - r))
                firsts[(c, H + 1 - r)] = L
                row += L
            rows.append(row)
        # A spent tile's terrain needs its own entry when nothing on the map is that already.
        for S, info in spent.values():
            if info:
                kinds.setdefault(S, dict(info, names={info['name']: 0}, where={}))
        spent = {tile: S for tile, (S, _) in spent.items()}
        for info in kinds.values():
            names = sorted(info.pop('names').items(), key=lambda kv: -kv[1])
            where = info.pop('where')
            # Tiles under one code with names of their own (Revelation 18's Sigils among its plain, V: Endless Dawn's Dragon Vein
            # tile among its forts): each keeps its name in the tile panel; the most common name is the default.
            if len(names) > 1 and info['move']['Fliers'] is not None:
                info['tileNames'] = {n: sorted(where.get(n, []), key=lambda p: (-p[1], p[0])) for n, _ in names[1:] if where.get(n)}
            # Walls keep the commonest name; walkable kinds list each name (e.g. "Plain / Floor").
            info['name'] = names[0][0] if len(names) == 1 or info['move']['Fliers'] is None else ' / '.join(n for n, _ in names)
        veins = []
        script = terrain_script(code, pack)
        tr = [x for x in read_tricks(script) if max(x) < 100] if script else []

        # Areas the chapter script sets as the map loads (its kind 7 handler) start in that state: Revelation 20 lays the first
        # bridge of each pair, the Heirs of Fate's The Changing Tide spreads three of its bogs (read live: Revelation 20's 34
        # bridge tiles are down on turn 1). The opening cutscene's own changes don't last (Revelation 20's bridge 7).
        loaded = set()
        cscript = find_script(code, pack)
        area_cells = {(x, y): {(x + i, H + 1 - (y + j)) for i in range(w) for j in range(h)} for x, y, w, h, k in tr if k == AREA}
        for h in Script(cscript).handlers() if cscript else []:
            if h['kind'] & 0xFF != 7:
                continue
            ins = Script(cscript).disasm(h)
            for i, (_, n, a) in enumerate(ins):
                if n == 'call' and a.startswith('ev::TrickSet/') and i >= 5 and all(ins[i - k][1] == 'int' for k in range(1, 6)):
                    x, y, kind, state = (ins[i - 5][2], ins[i - 4][2], ins[i - 3][2], ins[i - 2][2])
                    if kind == AREA and (x, y) in area_cells:
                        loaded = (loaded | area_cells[(x, y)]) if state == 2 else (loaded - area_cells[(x, y)])
        if code in OPENING_STORMS:
            loaded |= {t for t in afters if (t[0], H + 1 - t[1]) not in OPENING_STORMS[code]}
        if code == 'B008':
            loaded = set()  # its frozen lake is already the start (above)
        loaded &= set(afters)
        if loaded:
            grid = [list(row) for row in rows]
            for (c, y) in loaded:
                grid[H - y][c - 1] = afters[(c, y)]
            rows = [''.join(row) for row in grid]

        # What each vein does to its areas: TrickSetForDragon's fourth argument is 2 to put them in their second state (Birthright 10
        # raises its spikes) or 1 to flip them (most veins; Revelation 11's lower its spikes once they've sprung). A vein that calls
        # a function flips them too (Revelation 20 moves a bridge from one place to the other).
        vein_state = {}
        if script:
            sc0 = Script(script)
            for h in sc0.handlers():
                a = h['args']
                if len(a) < 5 or a[4] != VEIN:
                    continue
                ins = sc0.disasm(h)
                state = None
                for i, (_, n, arg) in enumerate(ins):
                    if n == 'call' and arg.startswith('ev::TrickSetForDragon/') and i >= 3 and ins[i - 3][1] == 'int':
                        state = 2 if ins[i - 3][2] == 2 else 'toggle'
                if state is None and any(n == 'gvar' for _, n, _ in ins):
                    state = 'toggle'
                vein_state[(a[0], H + 1 - a[1])] = state
        vtiles = [(x, H + 1 - y) for x, y, w, h, k in tr if k == VEIN]
        mine = {v: set() for v in vtiles}

        def cells(x, y, w, h):
            return {(x + i, y - j) for i in range(w) for j in range(h)}

        def dist(v, cs):
            return min(abs(v[0] - a) + abs(v[1] - b) for a, b in cs)
        # Areas follow the vein(s) they belong to: one vein -> its own area; a run of veins followed by
        # fewer areas (or single-tile ones) -> they share them; otherwise each area goes to its nearest vein.
        has_toggles = any(k == TOGGLE for *_, k in tr)
        groups, run, areas = [], [], []
        for x, y, w, h, k in tr:
            if k == VEIN:
                if areas:
                    groups.append((run, areas))
                    run, areas = [], []
                run.append((x, H + 1 - y))
            elif k == (TOGGLE if has_toggles else AREA) and run:
                areas.append(cells(x, H + 1 - y, w, h))
        if run:
            groups.append((run, areas))
        for run, areas in groups:
            if not areas:
                continue
            if len(run) == 1 or len(areas) == 1 or all(len(cs) == 1 for cs in areas):
                for v in run:
                    for cs in areas:
                        mine[v] |= cs
            else:
                for cs in areas:
                    mine[min(run, key=lambda v: dist(v, cs))] |= cs
        # A vein's handler names the areas it changes: its 8th argument is a string of their corners ('3, 3, 5, 3, 6, 3'), in
        # the script's own top-down coordinates. Where it does, that's the vein's patch (Revelation 12's last vein changes all
        # four areas; Conquest 17's veins all name the one area covering the map, so each shows every tile there that changes).
        if script:
            area_at = {(x, y): cells(x, H + 1 - y, w, h) for x, y, w, h, k in tr if k == AREA}
            sc = Script(script)
            for h in sc.handlers():
                a = h['args']
                if len(a) < 8 or a[4] != VEIN or (a[0], H + 1 - a[1]) not in mine:
                    continue
                # Or its code hands them to TrickSetAnyForDragon, last: Birthright 21's bridge vein at (11, 3) names only its
                # bridge, '8, 24' (the lava over the boss's island is the boss's battle talk's doing, not a vein's).
                try:
                    ins = sc.disasm(h)
                except (ValueError, IndexError):
                    ins = []
                given = next((ins[k - 1][2].strip("'") for k in range(len(ins) - 1, 0, -1) if ins[k][1] == 'call'
                              and ins[k][2].startswith('ev::TrickSetAnyForDragon') and ins[k - 1][1] == 'str'), None)
                try:
                    nums = [int(n) for n in (given or sc.string(a[7])).split(',')]
                except (ValueError, IndexError, UnicodeDecodeError):
                    continue
                named = [area_at[(x, y)] for x, y in zip(nums[::2], nums[1::2]) if (x, y) in area_at]
                if not named:
                    continue
                mine[(a[0], H + 1 - a[1])] = set().union(*named)
        if len(vtiles) == 1 and not mine[vtiles[0]]:
            mine[vtiles[0]] = set(afters)
        for v in vtiles:
            state = vein_state.get(v) or 2
            patch = []
            for t in mine[v]:
                if t not in afters:
                    continue
                if t in loaded and state == 'toggle':
                    patch.append((t, firsts[t]))  # back to its first state
                elif t not in loaded and state in (2, 'toggle'):
                    patch.append((t, afters[t]))
            veins.append({'tile': v, 'patch': sorted(patch, key=lambda p: (-p[0][1], p[0][0]))})
        # A breakable tile's HP sits on the terrain-script trick that covers it (args: x, y, w, h, kind, HP).
        hp = {}
        if script:
            for h in Script(script).handlers():
                a = h['args']
                if len(a) >= 6 and a[4] in (0, 9) and 0 < a[5] < 1000 and max(a[:4]) < 100:
                    for i in range(a[2]):
                        for j in range(a[3]):
                            hp[(a[0] + i, H + 1 - (a[1] + j))] = a[5]
        breakables = [{'tile': t, 'becomes': b, 'also': [], **({'hp': hp[t]} if t in hp else {})}
                      for t, b in sorted(breaks.items(), key=lambda kv: (-kv[0][1], kv[0][0]))]
        # A tile that changes once something breaks goes with the nearest breakable (within 3 tiles).
        for t, b in knock_on.items():
            near = min(breakables, key=lambda x: abs(x['tile'][0] - t[0]) + abs(x['tile'][1] - t[1]), default=None)
            if near and abs(near['tile'][0] - t[0]) + abs(near['tile'][1] - t[1]) <= 3:
                near['also'].append((t, b))
        # Traps: a handler for one of your units stopping in an area (kind 0x14, your side) that puts a terrain area in its second
        # state, itself or through a helper it calls with the area's corner: Birthright 10's and Revelation 11's bamboo spikes
        # (checked live on Birthright 10: a unit stopping on a spike tile outside the handler's area springs nothing, one inside it
        # raises the whole group).
        traps = []
        if cscript:
            csc = Script(cscript)
            by_index = {h['index']: h for h in csc.handlers()}

            def raised(h, args=()):
                """The corners of the terrain areas a handler puts in their second state."""
                found = []
                try:
                    ins = csc.disasm(h)
                except (ValueError, IndexError):
                    return found
                for i, (_, n, a) in enumerate(ins):
                    if n == 'call' and a.startswith('ev::TrickSet/') and i >= 5:
                        vals = []
                        for k in range(5, 0, -1):
                            op, arg = ins[i - k][1], ins[i - k][2]
                            vals.append(arg if op == 'int' else args[int(arg, 16)] if op == 'var' and int(arg, 16) < len(args) else None)
                        if vals[2] == AREA and vals[3] == 2 and isinstance(vals[0], int) and isinstance(vals[1], int):
                            found.append((vals[0], vals[1]))
                    if n == 'gvar' and not args and int(a, 16) in by_index:
                        lits, j = [], i - 1
                        while j >= 0 and ins[j][1] in ('int', 'str'):
                            lits.insert(0, ins[j][2])
                            j -= 1
                        found += raised(by_index[int(a, 16)], tuple(lits))
                return found
            for h in csc.handlers():
                a = h['args']
                if h['kind'] & 0xFF != 0x14 or len(a) < 5 or a[4] != 0 or min(a[:4]) < 0:
                    continue
                cells = set().union(*(area_cells.get(c, set()) for c in raised(h)))
                patch = sorted(((t, afters[t]) for t in cells if t in afters and t not in loaded), key=lambda p: (-p[0][1], p[0][0]))
                if patch:
                    zone = [min(a[0], a[2]), H + 1 - max(a[1], a[3]), max(a[0], a[2]), H + 1 - min(a[1], a[3])]
                    traps.append({'zone': zone, 'patch': patch})
        # Walls the chapter script raises and lowers (Revelation 16's flame walls): a wall is a function that hands a helper the
        # corners of its areas, its flag, then the flags of the walls it shares an area with (the helper keeps a shared area up
        # while the other wall is). The battle-start handler (kind 8) raises them all, then lowers one of several sets that
        # RandomGetGame picks; a turn handler flips sets on the turns that divide by 3 and by 4; each vein flips its own wall,
        # and stays usable. Read live on Lunatic: the battle started with the fifth set down, and every state after two veins and
        # on turns 3 and 4 matched.
        switch = None
        if cscript:
            csc = Script(cscript)
            hs = {h['index']: h for h in csc.handlers()}

            def number(flag):
                return int(flag[len(WALL_FLAG):].translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            wall_of, wall_tiles = {}, {}
            for i, h in hs.items():
                if h['kind'] & 0xFF:
                    continue
                try:
                    ins = csc.disasm(h)
                except (ValueError, IndexError):
                    continue
                strs = [a.strip("'") for _, n, a in ins if n == 'str']
                if not strs or not strs[0].startswith(WALL_FLAG) or any(n == 'call' for _, n, _ in ins):
                    continue
                ints = [a for _, n, a in ins if n == 'int']
                segs = list(zip(ints[::2], ints[1::2]))
                if not segs or len(ints) % 2 or not all(sg in area_cells for sg in segs):
                    continue
                wall_of[i] = number(strs[0])
                wall_tiles[number(strs[0])] = set().union(*(area_cells[sg] for sg in segs))
            if wall_of:
                def walls_called(h, arg):
                    '''The walls a handler flips: the wall functions it calls with `arg` (0 at the start, 1 on a turn).'''
                    ins = csc.disasm(h)
                    return [wall_of[int(a, 16)] for k, (_, n, a) in enumerate(ins)
                            if n == 'gvar' and int(a, 16) in wall_of and ins[k - 1][1] == 'int' and ins[k - 1][2] == arg]
                starts, turns = [], []
                for h in hs.values():
                    ins = csc.disasm(h)
                    if h['kind'] & 0xFF == 8 and any(n == 'call' and a.startswith('ev::RandomGetGame') for _, n, a in ins):
                        starts = [sorted(walls_called(hs[int(a, 16)], 0)) for _, n, a in ins if n == 'gvar' and int(a, 16) in hs]
                    if h['kind'] & 0xFF == 0x10:
                        every = None
                        for k, (_, n, a) in enumerate(ins):
                            if n == 'call' and a.startswith('ev::TurnGet') and [x[1] for x in ins[k + 1:k + 6]] == ['int', 'mod', 'int', 'eq', 'jz']:
                                every = ins[k + 1][2]
                                turns.append({'every': every, 'from': h['args'][0], 'walls': []})
                            elif n == 'gvar' and int(a, 16) in wall_of and every and ins[k - 1][2] == 1:
                                turns[-1]['walls'].append(wall_of[int(a, 16)])
                turns = [t for t in turns if t['walls']]
                downs = {afters[t] for ts in wall_tiles.values() for t in ts}
                assert len(starts) > 1 and turns and len(downs) == 1, (code, starts, turns, downs)
                switch = {'walls': sorted(wall_tiles.items()), 'down': downs.pop(), 'starts': starts,
                          'turns': [dict(t, walls=sorted(t['walls'])) for t in turns]}
                # A vein flips the wall whose flag its handler tests first.
                tsc = Script(script)
                for h in tsc.handlers():
                    a = h['args']
                    if len(a) >= 5 and a[4] == VEIN:
                        flags = [x[2].strip("'") for x in tsc.disasm(h) if x[1] == 'str' and x[2].strip("'").startswith(WALL_FLAG)]
                        v = next((v for v in veins if v['tile'] == (a[0], H + 1 - a[1])), None)
                        if v and flags:
                            v['flips'], v['patch'] = number(flags[0]), []
                assert all('flips' in v for v in veins), code
        out[map_id] = {'code': code, 'dark': dark, 'breakables': breakables, 'veins': veins, 'traps': traps, 'width': W, 'height': H,
                       'grid': rows, 'terrain': kinds, 'spent': sorted(spent.items(), key=lambda kv: (-kv[0][1], kv[0][0])),
                       'switch': switch}

    # Out in the app's two-character terrain codes (scripts/terrain_codes.py).
    ground = json.load(open(GROUND, encoding='utf-8')) if os.path.exists(GROUND) else {}
    for map_id, m in out.items():
        m['grid'] = [encode_row('fates', row) for row in m['grid']]
        for b in m['breakables']:
            b['becomes'] = encode('fates', b['becomes'])
            b['also'] = [(t, encode('fates', a)) for t, a in b['also']]
        for v in m['veins'] + m['traps']:
            v['patch'] = [(t, encode('fates', b)) for t, b in v['patch']]
        m['spent'] = [(t, encode('fates', b)) for t, b in m['spent']]
        if m['switch']:
            m['switch']['down'] = encode('fates', m['switch']['down'])
        m['terrain'] = {encode('fates', L): info for L, info in m['terrain'].items()}
        # Its ground from its 3D field (scripts/fates_ground.py: data-raw/fates-ground.json): its colours, and the plain tiles its art
        # draws as dirt (the plain's stats and name).
        g = ground.get(map_id)
        if g:
            rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            dirt = [(x, y) for x, y in g['dirt'] if rows[m['height'] - y][x - 1] == 'ta']
            for x, y in dirt:
                rows[m['height'] - y][x - 1] = 'ga'
            m['grid'] = [''.join(r) for r in rows]
            if dirt:
                plain = m['terrain']['ta']
                m['terrain']['ga'] = {k: v for k, v in plain.items() if k != 'tileNames'} | {'name': plain['name'].split(' / ')[0]}
            m['fills'] = g['fills']
    lines = [
        "import type { TerrainInfo } from './fatesTerrain'",
        "import type { TerrainCode } from './terrainCodes'",
        "import type { SwitchWalls, Tile } from './types'",
        '',
        '/*',
        ' * GENERATED by scripts/build-fates-terrain.py from the game\'s own terrain files. Do not edit by hand:',
        ' * fix the generator (or the per-map data that uses it) and re-run it.',
        ' *',
        " * Each map's grid (top row first) in the app's two-character terrain codes, and each code's exact terrain",
        " * on that map: the game's English name, Def, Avo, heal % and movement costs.",
        ' */',
        'export interface GameTerrain {',
        '  code: string',
        '  width: number',
        '  height: number',
        '  grid: string[]',
        "  /** Tiles under Revelation's darkness: impassable, and shown shaded, until the chapter lifts it. */",
        '  dark?: Tile[]',
        '  /** Walls, partitions and the like that can be attacked down: what each becomes, and its HP when the game sets one. */',
        '  breakables?: { tile: Tile; becomes: TerrainCode; hp?: number; also?: { tile: Tile; becomes: TerrainCode }[] }[]',
        "  /** Every Dragon Vein tile, with the tiles it reshapes (empty when it changes no terrain), or the wall it flips. */",
        '  veins: { tile: Tile; patch: { tile: Tile; becomes: TerrainCode }[]; flips?: number }[]',
        "  /** Traps that spring when one of your units stops in their zone ([left, bottom, right, top]): the tiles they change. */",
        '  traps?: { zone: [number, number, number, number]; patch: { tile: Tile; becomes: TerrainCode }[] }[]',
        "  /** Walls the chapter raises and lowers (Revelation 16's flame walls): each wall's tiles, what they are once down, the",
        "   * sets the battle can start with down (it picks one at random), and the turns that flip sets of them. */",
        '  switchWalls?: SwitchWalls',
        "  /** Every tile with a second state (a vein's or the chapter's change, a door, a wall broken down), and that state: a",
        "   * challenge battle has the chapter's map with everything in it spent. */",
        '  spent?: { tile: Tile; becomes: TerrainCode }[]',
        '  terrain: Partial<Record<TerrainCode, TerrainInfo>>',
        "  /** Its ground's, water's and walls' colours, from its 3D field (scripts/fates_ground.py). */",
        '  fills?: Partial<Record<TerrainCode, string>>',
        '}',
        '',
        'export const GAME_TERRAIN: Record<string, GameTerrain> = {',
    ]
    for map_id, m in out.items():
        lines.append(f"  '{map_id}': {{")
        lines.append(f"    code: '{m['code']}',")
        if m.get('fills'):
            lines.append('    fills: { ' + ', '.join(f"{c}: '{v}'" for c, v in sorted(m['fills'].items())) + ' },')
        lines.append(f"    width: {m['width']},")
        lines.append(f"    height: {m['height']},")
        lines.append('    grid: [')
        for i, row in enumerate(m['grid']):
            lines.append(f"      '{row}', // {m['height'] - i}")
        lines.append('    ],')
        if m['breakables']:
            lines.append('    breakables: [' + ', '.join(
                f"{{ tile: [{b['tile'][0]}, {b['tile'][1]}], becomes: {json.dumps(b['becomes'])}" + (f", hp: {b['hp']}" if 'hp' in b else '')
                + (', also: [' + ', '.join(f'{{ tile: [{x}, {y}], becomes: {json.dumps(a)} }}' for (x, y), a in b['also']) + ']' if b['also'] else '') + ' }'
                for b in m['breakables']) + '],')
        if m['spent']:
            lines.append('    spent: [' + ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in m['spent']) + '],')
        if m['dark']:
            lines.append('    dark: [' + ', '.join(f'[{x}, {y}]' for x, y in m['dark']) + '],')
        lines.append('    veins: [')
        for v in m['veins']:
            patch = ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in v['patch'])
            flips = f", flips: {v['flips']}" if 'flips' in v else ''
            lines.append(f"      {{ tile: [{v['tile'][0]}, {v['tile'][1]}], patch: [{patch}]{flips} }},")
        lines.append('    ],')
        if m['switch']:
            sw = m['switch']
            lines.append('    switchWalls: {')
            lines.append(f"      down: {json.dumps(sw['down'])},")
            lines.append('      walls: [')
            for n, ts in sw['walls']:
                lines.append(f"        {{ id: {n}, tiles: [" + ', '.join(f'[{x}, {y}]' for x, y in sorted(ts, key=lambda p: (-p[1], p[0]))) + '] },')
            lines.append('      ],')
            lines.append('      starts: [' + ', '.join('[' + ', '.join(map(str, st)) + ']' for st in sw['starts']) + '],')
            lines.append('      turns: [' + ', '.join(f"{{ every: {t['every']}, from: {t['from']}, walls: [{', '.join(map(str, t['walls']))}] }}"
                                                   for t in sw['turns']) + '],')
            lines.append('    },')
        if m['traps']:
            lines.append('    traps: [')
            for v in m['traps']:
                patch = ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in v['patch'])
                lines.append(f"      {{ zone: [{', '.join(map(str, v['zone']))}], patch: [{patch}] }},")
            lines.append('    ],')
        lines.append('    terrain: {')
        for L, info in sorted(m['terrain'].items()):
            key = L
            move = ', '.join(f"{json.dumps(k) if ' ' in k else k}: {json.dumps(v)}" for k, v in info['move'].items())
            tile_names = ''
            if info.get('tileNames'):
                tile_names = ', tileNames: { ' + ', '.join(f"{json.dumps(n)}: [" + ', '.join(f'[{x}, {y}]' for x, y in ts) + ']'
                                                          for n, ts in info['tileNames'].items()) + ' }'
            lines.append(f"      {key}: {{ name: {json.dumps(info['name'])}, def: {info['def']}, avo: {info['avo']}, heal: {info['heal']}, move: {{ {move} }}{tile_names} }},")
        lines.append('    },')
        lines.append('  },')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out), 'maps')


if __name__ == '__main__':
    main()
