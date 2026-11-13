"""
A multi-tile building drawn whole on any game's map (the user's call): each tile of a building is the piece for its place in it,
a, b, c along its top (left, middle, right), d, e, f through its middle, g, h, i along its front, from which sides the building
goes on past the tile. scripts/gba_walls.py places the GBA games' pieces from their terrain ids; this places them on a built map's
codes (the Tellius games' houses, their `w8` until then: each a town house, one house over its tiles; and their markets' stalls),
and gives each piece its terrain entry and name.
"""


def place(rows, code, group, inside, side_on=False):
    """A map's grid rows (two-character codes) with every `code` tile as its building's piece (`group` + a-i); `inside` the codes a
    building goes on through (its own and its entrances'). `side_on`: a building taller than it's wide is turned side-on, its
    pieces `group` + j-r (the user's call: a town house seen as its roof alone, not a tall silo)."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    has = lambda x, y: 0 <= x < w and 0 <= y < h and grid[y][x] in inside  # noqa: E731
    turned = set()
    if side_on:
        seen = set()
        for y in range(h):
            for x in range(w):
                if grid[y][x] != code or (x, y) in seen:
                    continue
                part, todo = set(), [(x, y)]
                while todo:
                    c = todo.pop()
                    if c in part or not (0 <= c[0] < w and 0 <= c[1] < h) or grid[c[1]][c[0]] != code:
                        continue
                    part.add(c)
                    todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
                seen |= part
                xs, ys = [c[0] for c in part], [c[1] for c in part]
                if max(ys) - min(ys) > max(xs) - min(xs):
                    turned |= part
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != code:
                continue
            up, down, left, right = has(x, y - 1), has(x, y + 1), has(x - 1, y), has(x + 1, y)
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
    m = carpets(m, terrain)
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


def town(m, terrain):
    """Draws a built (encoded) Tellius map's houses (`w8`) as town houses, one house over each building's tiles (the user's call: a
    whole village doesn't fit in one house), and its markets (`o6`) as rows of stalls; each piece keeps its building's terrain entry
    and the map's name for it. `terrain` the game's table by code, given the pieces' entries."""
    m = forts(m, terrain)
    grid = place(m['grid'], 'w8', 'r', {'w8'}, side_on=True)
    # Churches (`ke`), prison camps (`pe`) and fountains (`fe`) over their tiles too, each its building's pieces.
    for code, group in (('ke', 'k'), ('pe', 'p'), ('fe', 'f')):
        grid = place(grid, code, group, {code})
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
