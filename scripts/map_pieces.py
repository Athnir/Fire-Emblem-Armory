"""
A multi-tile building drawn whole on any game's map (the user's call): each tile of a building is the piece for its place in it,
a, b, c along its top (left, middle, right), d, e, f through its middle, g, h, i along its front, from which sides the building
goes on past the tile. scripts/gba_walls.py places the GBA games' pieces from their terrain ids; this places them on a built map's
codes (the Tellius games' houses, their `w8` until then: each a town house, one house over its tiles; and their markets' stalls),
and gives each piece its terrain entry and name.
"""


def place(rows, code, group, inside):
    """A map's grid rows (two-character codes) with every `code` tile as its building's piece (`group` + a-i); `inside` the codes a
    building goes on through (its own and its entrances')."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    has = lambda x, y: 0 <= x < w and 0 <= y < h and grid[y][x] in inside  # noqa: E731
    out = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] != code:
                continue
            up, down, left, right = has(x, y - 1), has(x, y + 1), has(x - 1, y), has(x + 1, y)
            row = 2 if not down else 0 if not up else 1
            col = 0 if not left and right else 2 if not right and left else 1
            out[y][x] = group + 'abcdefghi'[row * 3 + col]
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
    m['grid'] = stalls(place(m['grid'], 'w8', 'r', {'w8'}), 'o6')
    found = {r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)}
    over = m.get('terrainOverrides', {})
    for source, pieces in (('w8', [p for p in found if p[0] == 'r' and p[1] in 'abcdefghi']), ('o6', ['o5', 'o7', 'o8'])):
        for p in pieces:
            if p in found and source in terrain:
                terrain.setdefault(p, terrain[source])
            if p in found and source in over:
                over[p] = over[source]
    return m
