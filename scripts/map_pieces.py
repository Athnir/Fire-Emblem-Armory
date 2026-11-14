"""
A multi-tile building drawn whole on any game's map (the user's call): each tile of a building is the piece for its place in it,
a, b, c along its top (left, middle, right), d, e, f through its middle, g, h, i along its front, from which sides the building
goes on past the tile. scripts/gba_walls.py places the GBA games' pieces from their terrain ids; this places them on a built map's
codes (the Tellius games' houses, their `w8` until then: each a town house, one house over its tiles; and their markets' stalls),
and gives each piece its terrain entry and name.
"""
import json
import os


def place(rows, code, group, inside, side_on=False, cuts=(), turn=()):
    """A map's grid rows (two-character codes) with every `code` tile as its building's piece (`group` + a-i); `inside` the codes a
    building goes on through (its own and its entrances'). `side_on`: a building taller than it's wide is turned side-on, its
    pieces `group` + j-r (the user's call: a town house seen as its roof alone, not a tall silo), as is any building with a tile in
    `turn`; `cuts`: pairs of side-by-side tiles (grid indices) that belong to two buildings."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    cut = {frozenset(c) for c in cuts}
    joined = lambda a, b: frozenset((a, b)) not in cut  # noqa: E731
    has = lambda x, y: 0 <= x < w and 0 <= y < h and grid[y][x] in inside  # noqa: E731
    turned = set()
    if side_on or turn:
        seen = set()
        for y in range(h):
            for x in range(w):
                if grid[y][x] != code or (x, y) in seen:
                    continue
                part, todo = set(), [((x, y), (x, y))]
                while todo:
                    c, frm = todo.pop()
                    if c in part or not (0 <= c[0] < w and 0 <= c[1] < h) or grid[c[1]][c[0]] != code or not joined(c, frm):
                        continue
                    part.add(c)
                    todo += [((c[0] + dx, c[1] + dy), c) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                seen |= part
                xs, ys = [c[0] for c in part], [c[1] for c in part]
                if (side_on and max(ys) - min(ys) > max(xs) - min(xs)) or part & set(turn):
                    turned |= part
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != code:
                continue
            up, down = has(x, y - 1) and joined((x, y), (x, y - 1)), has(x, y + 1) and joined((x, y), (x, y + 1))
            left, right = has(x - 1, y) and joined((x, y), (x - 1, y)), has(x + 1, y) and joined((x, y), (x + 1, y))
            row = 2 if not down else 0 if not up else 1
            col = 0 if not left and right else 2 if not right and left else 1
            out[y][x] = group + ('jklmnopqr' if (x, y) in turned else 'abcdefghi')[row * 3 + col]
    return [''.join(r) for r in out]


def stalls(rows, code):
    """A map's grid rows with each `code` tile as its row of stalls' piece: o5 its left end, o6 between, o7 its right end, o8 alone."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    out = [row[:] for row in grid]
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            if c != code:
                continue
            left, right = x > 0 and row[x - 1] == code, x + 1 < len(row) and row[x + 1] == code
            out[y][x] = 'o6' if left and right else 'o7' if left else 'o5' if right else 'o8'
    return [''.join(r) for r in out]


# Bridges the 3D map builds of stone, their ground at both ends stone too (the user, from the game: Path of Radiance's Great Bridge
# and Radiant Dawn's Part 3 Ch.11). The game calls them Bridge and plain like any other.
STONE_BRIDGES = {'fe9-23', 'fe10-3-11'}


# Carpets the 3D map lays on a hall's floor, which the game calls floor (the user's agreed review: a red carpet up the aisle), read
# off the minimaps: (x0, y0, x1, y1) app coordinates, the floor tiles in it carpet. Path of Radiance's Ch.22 and Ch.27-2.
CARPETS = {'fe9-22': [(8, 6, 10, 18)], 'fe9-27-2': [(5, 2, 7, 9)]}


# A floor's second look by area where the files give no level for it (the user's description against the minimap): Trial 3's darker
# cross, two tiles wide to each edge, and the ring round its lighter middle 2 x 2. (x0, y0, x1, y1, code) in app coordinates, in order.
FLOOR_LOOKS = {'fe9-trial3': [(5, 1, 6, 10, 'ge'), (1, 5, 10, 6, 'ge'), (4, 4, 7, 7, 'ge'), (5, 5, 6, 6, 't1')]}


def floor_looks(m, terrain):
    """A built (encoded) map's floor looks by area (FLOOR_LOOKS): the floor's stats either way."""
    looks = FLOOR_LOOKS.get(m['id'])
    if not looks:
        return m
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    for x0, y0, x1, y1, code in looks:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rows[m['height'] - y][x - 1] in ('t1', 'ge'):
                    rows[m['height'] - y][x - 1] = code
    m['grid'] = [''.join(r) for r in rows]
    terrain.setdefault('ge', {**terrain['t1'], 'name': 'Floor (another level)'})
    over = m.get('terrainOverrides', {})
    if 't1' in over:
        over['ge'] = over['t1']
    return m


def carpets(m, terrain):
    """A built (encoded) map's carpets (CARPETS) as carpet (`t9`), with the floor's stats."""
    rects = CARPETS.get(m['id'])
    if not rects:
        return m
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    for x0, y0, x1, y1 in rects:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rows[m['height'] - y][x - 1] == 't1':
                    rows[m['height'] - y][x - 1] = 't9'
    m['grid'] = [''.join(r) for r in rows]
    terrain.setdefault('t9', {**terrain['t1'], 'name': 'Floor (carpet)'})
    over = m.get('terrainOverrides', {})
    if 't1' in over:
        over['t9'] = over['t1']
    return m


def stone_crossing(m, terrain):
    """A built (encoded) map's bridges as stone (`t8`) and its plain as paving (`gb`), each with the stats of what it stands for,
    where the map's bridge is stone (STONE_BRIDGES)."""
    m = floor_looks(carpets(m, terrain), terrain)
    if m['id'] not in STONE_BRIDGES:
        return m
    m['grid'] = [''.join({'tb': 't8', 't0': 'gb'}.get(r[i:i + 2], r[i:i + 2]) for i in range(0, len(r), 2)) for r in m['grid']]
    terrain.setdefault('t8', {**terrain['tb'], 'name': 'Bridge (stone)'})
    terrain.setdefault('gb', {**terrain['t0'], 'name': 'Plain (paving)'})
    over = m.setdefault('terrainOverrides', {})
    for old, new in (('tb', 't8'), ('t0', 'gb')):
        if old in over:
            over[new] = over.pop(old)
    return m


# Walls the 3D map shows as a barrier of light though the game calls them walls (the user, from the game: Radiant Dawn's Part 4
# Endgame (2), the row across its middle). App coordinates: (x, y) tiles, or a whole row as ('row', y).
BARRIERS = {'fe10-4-endgame-2': [('row', 15)]}


def barriers(m, terrain):
    """A built (encoded) map's barrier walls (BARRIERS) as a barrier (`wu`), with the wall's stats."""
    spots = BARRIERS.get(m['id'])
    if not spots:
        return m
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    tiles = [(x, s[1]) for s in spots if s[0] == 'row' for x in range(1, m['width'] + 1)] + [s for s in spots if s[0] != 'row']
    for x, y in tiles:
        code = rows[m['height'] - y][x - 1]
        if code[0] != 'w':
            raise SystemExit(f"{m['id']}: ({x}, {y}) is {code}, not a wall")
        terrain.setdefault('wu', {**terrain[code], 'name': 'Barrier (a wall of light)'})
        rows[m['height'] - y][x - 1] = 'wu'
    m['grid'] = [''.join(r) for r in rows]
    return m


def forts(m, terrain):
    """A built (encoded) Tellius map's forts standing whole (a solid block of the game's 砦, its gate the goal tile in it: Path of
    Radiance's Lonely Isle, the user's call) as a castle drawn whole (`ca`-`ci`, the wall's stats); a fort that walls in a yard stays
    walls."""
    over = m.get('terrainOverrides', {})
    if 'Fort' not in over.get('w0', {}).get('name', ''):
        return m
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    h, w = len(grid), len(grid[0])
    seen, found = set(), False
    for y in range(h):
        for x in range(w):
            if grid[y][x] != 'w0' or (x, y) in seen:
                continue
            part, todo = set(), [(x, y)]
            while todo:
                c = todo.pop()
                if c in part or not (0 <= c[0] < w and 0 <= c[1] < h) or grid[c[1]][c[0]] not in ('w0', 'bc'):
                    continue
                part.add(c)
                todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            seen |= part
            xs, ys = [c[0] for c in part], [c[1] for c in part]
            if len(part) == (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) and min(len(set(xs)), len(set(ys))) >= 2:
                found = True
                for cx, cy in part:
                    if grid[cy][cx] == 'w0':
                        grid[cy][cx] = 'cx'
    if not found:
        return m
    m['grid'] = place([''.join(r) for r in grid], 'cx', 'c', {'cx', 'bc'})
    for p in {r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2) if r[i] == 'c'}:
        terrain.setdefault(p, terrain['w0'])
        over[p] = over['w0']
    return m


# Buildings the 3D map shows as two that the grid joins, by the tiles either side of each cut (app coordinates): Port Toha's long house
# at the bottom is two houses, each with its door (the user); the Endgame's two top fountains are three 2 x 2 basins each (the user).
SPLITS = {
    'fe9-11': [((8, 4), (9, 4)), ((8, 5), (9, 5))],
    'fe9-endgame': [((x, y), (x + 1, y)) for x in (8, 10, 23, 25) for y in (20, 21)],
    # Radiant Dawn's Part 2 Ch.1: two houses each where the long ones stand (the user, the review of every map).
    'fe10-2-1': [((10, 3), (11, 3)), ((10, 4), (11, 4)), ((3, 14), (4, 14))],
}
# Towns packed so close that only their houses' roofs show (the user's calls): every house tile a roof, a door over each place to visit,
# and chimneys on these tiles (app coordinates). Radiant Dawn's Part 1 Ch.1 and Ch.3 (its camp's buildings in the town's red).
ROOFTOPS = {
    'fe10-1-1': [(7, 3), (4, 2), (7, 6), (12, 2), (15, 2), (14, 10), (14, 12), (14, 14), (12, 13)],
    'fe10-1-3': [],
    'fe10-1-prologue': [(8, 8)],
}
# Rooftop towns whose bare walls (`wa`, no model on them) are drawn as the ground round them, railed off like its walled houses (the
# user's call: the Prologue's dark corner is cobbles in the 3D map).
GROUND_WALLS = {'fe10-1-prologue'}
# Houses the user has turned side-on, roof only, though they aren't taller than they're wide: a tile of each (app coordinates).
SIDE_ON = {'fe9-11': [(7, 7)]}


def lone_stalls(rows, code):
    """A building of a single tile (`code`) is a market stall, not a house (the user: Pirates Aground's and Port Toha's)."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    same = lambda x, y: 0 <= x < w and 0 <= y < h and grid[y][x] == code  # noqa: E731
    for y in range(h):
        for x in range(w):
            if grid[y][x] == code and not any(same(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                grid[y][x] = 'o6'
    return [''.join(r) for r in grid]


def town(m, terrain):
    """Draws a built (encoded) Tellius map's houses (`w8`) as town houses, one house over each building's tiles (the user's call: a
    whole village doesn't fit in one house), and its markets (`o6`) as rows of stalls; each piece keeps its building's terrain entry
    and the map's name for it. `terrain` the game's table by code, given the pieces' entries."""
    m = forts(m, terrain)
    models = m.pop('houseModels', None)
    markets = m.pop('marketModels', None)
    if m['id'] in ROOFTOPS:
        m['rooftops'] = {'chimneys': [f'{x},{y}' for x, y in ROOFTOPS[m['id']]]}
        # Which roof tiles make each house, marked by the user (data-raw/tellius-house-marks.json): an edge where two houses meet.
        marks = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data-raw', 'tellius-house-marks.json')
        houses = json.load(open(marks, encoding='utf-8')).get(m['id']) if os.path.exists(marks) else None
        if not houses and models:
            # Unmarked, the game's own house models part the roofs (build-fe10-maps.house_models), numbered from 1: on the buildings'
            # tiles and the props under a house's model.
            # A wall (`wa`) under a house's model is the house too (the Prologue's): no unit enters it, fliers included, so the viewer
            # rails it round (the user's call).
            def building(t):
                x, y = map(int, t.split(','))
                c = m['grid'][m['height'] - y][2 * (x - 1):2 * x]
                return c in ('w8', 'pe', 'ke', 'wa') or (c == 'o4' and m.get('props', {}).get(t) == 'roof')
            models = {t: k for t, k in models.items() if building(t)}
            number = {k: i + 1 for i, k in enumerate(sorted(set(models.values())))}
            houses = {t: number[k] for t, k in sorted(models.items(), key=lambda e: tuple(map(int, e[0].split(',')))[::-1])}
        if houses:
            m['rooftops']['houses'] = houses
        # A wall under a market's model is its stalls, railed round as the walled houses are (the Prologue's, the user's call).
        walled = [t for t in (markets or {}) if not (houses or {}).get(t)
                  and m['grid'][m['height'] - int(t.split(',')[1])][2 * (int(t.split(',')[0]) - 1):2 * int(t.split(',')[0])] == 'wa']
        if walled:
            m['rooftops']['stalls'] = sorted(walled, key=lambda t: tuple(map(int, t.split(',')))[::-1])
        if m['id'] in GROUND_WALLS:
            m['rooftops']['ground'] = [f'{x},{y}' for y in range(1, m['height'] + 1) for x in range(1, m['width'] + 1)
                                       if m['grid'][m['height'] - y][2 * (x - 1):2 * x] == 'wa' and not (houses or {}).get(f'{x},{y}')
                                       and f'{x},{y}' not in walled]
        if houses:
            # A tile marked 0 is no house but odds and ends (the user): a prop there isn't roof.
            for k, n in houses.items():
                if n == 0 and m.get('props', {}).get(k) == 'roof':
                    del m['props'][k]
    H = m['height']
    to_grid = lambda t: (t[0] - 1, H - t[1])  # noqa: E731
    cuts = [(to_grid(a), to_grid(b)) for a, b in SPLITS.get(m['id'], [])]
    turn = [to_grid(t) for t in SIDE_ON.get(m['id'], [])]
    # Only where a stall is a building drawn as one (Path of Radiance): Radiant Dawn's stalls are a terrain with stats of their own.
    grid = m['grid']
    if 'w8' in terrain and ('o6' not in terrain or terrain['o6']['name'] == 'Market stall (a building)'):
        grid = lone_stalls(grid, 'w8')
        if any('o6' in r for r in grid):
            terrain.setdefault('o6', {**terrain['w8'], 'name': 'Market stall (a building)'})
            if 'w8' in m.get('terrainOverrides', {}):
                m['terrainOverrides']['o6'] = m['terrainOverrides']['w8']
    grid = place(grid, 'w8', 'r', {'w8'}, side_on=True, cuts=cuts, turn=turn)
    # Churches (`ke`), prison camps (`pe`) and fountains (`fe`) over their tiles too, each its building's pieces.
    for code, group in (('ke', 'k'), ('pe', 'p'), ('fe', 'f')):
        grid = place(grid, code, group, {code}, cuts=cuts)
    m['grid'] = stalls(grid, 'o6')
    found = {r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)}
    over = m.get('terrainOverrides', {})
    pieces_of = lambda g: sorted(p for p in found if p[0] == g and p[1] in 'abcdefghijklmnopqr')  # noqa: E731
    for source, pieces in (('w8', pieces_of('r')), ('ke', pieces_of('k')), ('pe', pieces_of('p')), ('fe', pieces_of('f')),
                           ('o6', ['o5', 'o7', 'o8'])):
        for p in pieces:
            if p in found and source in terrain:
                terrain.setdefault(p, terrain[source])
            if p in found and source in over:
                over[p] = over[source]
    return m


# A small stone fort (Gaiden's and Echoes': its walls only fliers cross, `wx`, round its fort tile, its stairs, its gate and its
# castle floor) of this many tiles or fewer, standing in the open, is drawn whole: a stone fort seen from above, its walls its pieces
# (`qa`-`qi`) round what's inside it (the user's calls: as the DS games' castles, then a design of its own rather than a castle's
# towers, the same in the remake).
SMALL_FORT = 9
FORT_PARTS = {'wx', 'b0', 'bb', 'tc', 'bv'}
FORT_INSIDE = {'bb', 'tc', 'bv'}
INDOORS = {'t1', 't3', 'w0', 'w9', 'wy', 'b3', 'wx'}


def small_forts(codes):
    """{(row, column) from 0: piece code} for a map's small stone forts; `codes` its rows of app codes. A fort is its walls with the
    fort, stairs, gate and castle floor among them, standing in the open: nothing round it but the ground outside (the user: walls by
    a castle's floors or a dungeon's came out as little castles; the forts of four corner walls round a cross of floor as a fort)."""
    h, w = len(codes), len(codes[0])
    keep, seen = set(), set()
    for y in range(h):
        for x in range(w):
            if codes[y][x] != 'wx' or (y, x) in seen:
                continue
            part, todo = set(), [(y, x)]
            while todo:
                c = todo.pop()
                if c in part or not (0 <= c[0] < h and 0 <= c[1] < w) or codes[c[0]][c[1]] not in FORT_PARTS:
                    continue
                part.add(c)
                todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            seen |= part
            inside = {codes[c[0]][c[1]] for c in part}
            beside = {codes[c[0] + dy][c[1] + dx] for c in part for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      if 0 <= c[0] + dy < h and 0 <= c[1] + dx < w and (c[0] + dy, c[1] + dx) not in part}
            if len(part) <= SMALL_FORT and inside & FORT_INSIDE and not beside & INDOORS:
                keep |= {c for c in part if codes[c[0]][c[1]] == 'wx'}
    rows = [''.join(code if code != 'wx' or (y, x) in keep else 'XX' for x, code in enumerate(row)) for y, row in enumerate(codes)]
    placed = place(rows, 'wx', 'q', FORT_PARTS)
    return {(y, x): placed[y][2 * x:2 * x + 2] for y, x in keep}


# A block of walls (or buildings) standing over a village's tile, its front just above it, is that village's house: drawn whole as
# a house, the village before it its door mat (the user's calls, the review of every map: Awakening's villages, as Fates').
VILLAGES = ('oc', 'od')
HOUSE_WIDE, HOUSE_TALL = (2, 6), 4


def village_houses(rows, walls):
    """The grid rows (two-character codes) with each wall block (codes in `walls`) that stands just above a village's tile, two to
    six tiles wide and up to four tall and filling its box, as a house's pieces (`ra`-`rr`, side-on where taller than wide)."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    houses = set()
    for y in range(1, h):
        for x in range(w):
            if grid[y][x] not in VILLAGES or grid[y - 1][x] not in walls:
                continue
            code = grid[y - 1][x]
            comp, todo = set(), [(x, y - 1)]
            while todo:
                c = todo.pop()
                if c in comp or not (0 <= c[0] < w and 0 <= c[1] < h) or grid[c[1]][c[0]] != code:
                    continue
                comp.add(c)
                todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            xs, ys = [c[0] for c in comp], [c[1] for c in comp]
            bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if len(comp) == bw * bh and HOUSE_WIDE[0] <= bw <= HOUSE_WIDE[1] and bh <= HOUSE_TALL and max(ys) == y - 1:
                houses |= comp
    if not houses:
        return rows
    marked = [''.join('XH' if (x, y) in houses else c for x, c in enumerate(r)) for y, r in enumerate(grid)]
    return place(marked, 'XH', 'r', {'XH'}, side_on=True)
