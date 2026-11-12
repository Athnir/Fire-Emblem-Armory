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


def town(m, terrain):
    """Draws a built (encoded) Tellius map's houses (`w8`) as town houses, one house over each building's tiles (the user's call: a
    whole village doesn't fit in one house), and its markets (`o6`) as rows of stalls; each piece keeps its building's terrain entry
    and the map's name for it. `terrain` the game's table by code, given the pieces' entries."""
    grid = place(m['grid'], 'w8', 'r', {'w8'}, side_on=True)
    # Churches (`ke`) and prison camps (`pe`) over their tiles too, each its building's pieces.
    for code, group in (('ke', 'k'), ('pe', 'p')):
        grid = place(grid, code, group, {code})
    m['grid'] = stalls(grid, 'o6')
    found = {r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)}
    over = m.get('terrainOverrides', {})
    pieces_of = lambda g: sorted(p for p in found if p[0] == g and p[1] in 'abcdefghijklmnopqr')  # noqa: E731
    for source, pieces in (('w8', pieces_of('r')), ('ke', pieces_of('k')), ('pe', pieces_of('p')), ('o6', ['o5', 'o7', 'o8'])):
        for p in pieces:
            if p in found and source in terrain:
                terrain.setdefault(p, terrain[source])
            if p in found and source in over:
                over[p] = over[source]
    return m
