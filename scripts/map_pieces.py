"""
A multi-tile building drawn whole on any game's map (the user's call): each tile of a building is the piece for its place in it,
a, b, c along its top (left, middle, right), d, e, f through its middle, g, h, i along its front, from which sides the building
goes on past the tile. scripts/gba_walls.py places the GBA games' pieces from their terrain ids; this places them on a built map's
codes (the Tellius games' houses, their `w8` until then), and gives each piece its terrain entry and name.
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


def houses(m, terrain):
    """Draws a built (encoded) map's houses (`w8`) as village pieces, each piece keeping the house's terrain entry and the map's
    name for it; `terrain` the game's table by code, given the pieces' entries."""
    m['grid'] = place(m['grid'], 'w8', 'v', {'w8', 'oc'})
    pieces = {r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2) if r[i] == 'v' and r[i + 1] in 'abcdefghi'}
    for p in pieces:
        if 'w8' in terrain:
            terrain.setdefault(p, terrain['w8'])
        over = m.get('terrainOverrides', {})
        if 'w8' in over:
            over[p] = over['w8']
    return m
