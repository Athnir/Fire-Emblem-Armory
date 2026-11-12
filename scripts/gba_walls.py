"""
The GBA games' walls by what they are on each map (the user's call: 'so you can tell it's a ruin in a forest or a castle in a forest'):
castle, ruins, village building, temple, wood, sandstone, snow and ice; roofs, the void beyond a map's ground, and the walls fliers
cross (village walls, a ship's sides) keep kinds of their own. The Binding Blade, The Blazing Blade and The Sacred Stones share their
terrain ids (scripts/gba_maps.py's TERRAIN), so this serves all three builders.

Every terrain id here is impassable to everyone (0, 26, 27, 34, 44, 63, 64: no movement row enters them) or to all but fliers (46, 61);
the kind is drawn by look, read from each map's real art:
- A building no unit enters (terrain 44) whose entrance is a castle gate or throne (11, 35, 31) is a castle; one whose entrance is a
  village, house, shop or inn is a village building; any other takes its tileset's kind.
- A wall (26, 27, 63) takes its tileset's kind (the chapter record's graphics, +4 in FE7 and FE8, +8 in FE6), by look at every wall
  tile each tileset puts on a map: castle halls, Lagdou's ruins, the Dragon's Gate's temple, Jehanna's sandstone, Ilia's snow. A
  chapter can override it (the same tileset under another palette: Jehanna's Hall), and so can a range of a tileset's metatiles (The
  Binding Blade's desert set draws its impassable edge as grass and sand: the void).
- Terrain 0 (unnamed) is the black void around some maps; 34 a roof; 64 a mast; 46 (unnamed) a village, its houses and walls, and 61 a
  ship's sides, which fliers cross. A building of 44 (rare: a castle on an outdoor map) beside a village's 46 is part of the village.
"""

WALL_LETTER = '#'
# The kinds' letters (scripts/terrain_codes.py maps them for 'fe6', and The Blazing Blade and The Sacred Stones inherit them).
LETTERS = {'castle': '0', 'ruins': '1', 'village': '2', 'temple': '3', 'wood': '4', 'sandstone': '5', 'ice': '6', 'roof': '7',
           'village-wall': '8', 'ship-side': '9', 'void': '_'}
NAMES = {'castle': 'Castle wall', 'ruins': 'Ruins', 'village': 'Village building', 'temple': 'Temple wall', 'wood': 'Wooden wall / mast',
         'sandstone': 'Sandstone wall', 'ice': 'Snowy wall', 'roof': 'Roof', 'village-wall': 'Village houses and walls', 'ship-side': "Ship's side",
         'void': 'Void (beyond the map)'}
# Every letter a wall can be drawn with: the plain one and the kinds'.
WALL_LETTERS = {WALL_LETTER} | {v for k, v in LETTERS.items() if k not in ('village-wall', 'ship-side')}

BUILDING, WALLS, VILLAGE_WALL, SHIP_SIDE = 44, (26, 27, 63), 46, 61
FIXED = {0: 'void', 34: 'roof', 64: 'wood', VILLAGE_WALL: 'village-wall', SHIP_SIDE: 'ship-side'}
THEMED = {BUILDING, *WALLS, *FIXED}
CASTLE_DOORS = {11, 35, 31}                     # gates and the throne
VILLAGE_DOORS = {3, 4, 5, 6, 7, 8, 55, 56}      # villages, houses, shops, the arena, ruined villages, inns

# By look at each tileset's walls (the chapters each tileset serves are in data-raw/<game>/README.md).
TILESETS = {
    'fe6': {1: 'castle', 18: 'castle', 33: 'castle', 44: 'castle', 51: 'castle', 62: 'castle', 69: 'castle', 83: 'sandstone',
            102: 'ice', 115: 'ice', 122: 'castle', 129: 'castle', 142: 'temple', 165: 'castle', 177: 'castle'},
    'fe7': {1: 'castle', 10: 'castle', 16: 'castle', 22: 'castle', 28: 'castle', 91: 'wood', 106: 'castle', 145: 'castle',
            167: 'castle', 174: 'temple', 193: 'temple'},
    'fe8': {1: 'castle', 14: 'castle', 24: 'castle', 46: 'castle', 60: 'castle', 66: 'sandstone', 80: 'castle', 95: 'temple',
            108: 'ruins', 121: 'castle', 136: 'ruins'},
}
# A chapter whose palette makes its tileset's walls another kind (chapter record numbers).
CHAPTERS = {
    'fe7': {25: 'temple', 26: 'temple', 42: 'sandstone'},   # the Dragon's Gate (Ch.19, 19x part 2); Sands of Time
    'fe8': {14: 'sandstone'},                               # Jehanna's Hall
}
# Ranges of a tileset's metatiles that are another kind: (first, last, kind).
METATILES = {
    'fe6': {83: [(0, 499, 'void')]},      # The Binding Blade's desert set: the impassable edge drawn as grass and sand
}

# What was drawn with which kind, per game: (terrain id, letter) -> how many tiles (the builders' terrain tables use it).
PLACED = {}


def kind(game, tileset, chapter, meta, tid):
    """A wall tile's kind without its neighbours (a map change's tile)."""
    if tid in FIXED:
        return FIXED[tid]
    for first, last, k in METATILES.get(game, {}).get(tileset, ()):
        if first <= meta <= last:
            return k
    if tid == BUILDING:
        return 'village'
    return CHAPTERS.get(game, {}).get(chapter) or TILESETS[game].get(tileset, 'castle')


def letter(game, tileset, chapter, tile, tid, base):
    """A tile's letter: a wall's kind's, anything else's own (`base`). `tile` is the map's u16 (metatile << 2)."""
    if tid not in THEMED:
        return base
    out = LETTERS[kind(game, tileset, chapter, tile >> 2, tid)]
    PLACED.setdefault(game, {}).setdefault((tid, out), 0)
    PLACED[game][(tid, out)] += 1
    return out


def theme(game, tileset, chapter, tiles, grid, letters):
    """Rewrites a map's wall letters in place by kind: `tiles` the map's u16s and `grid` its terrain ids by [y][x], after the
    opening's changes. A building (44) takes its kind from what its entrance is: each run of building tiles, side by side, looks at
    the tiles around it."""
    h, w = len(grid), len(grid[0])
    seen = set()
    for y in range(h):
        for x in range(w):
            tid = grid[y][x]
            if tid not in THEMED:
                continue
            if tid != BUILDING:
                letters[y][x] = letter(game, tileset, chapter, tiles[y][x], tid, letters[y][x])
                if tid != VILLAGE_WALL:
                    continue
            if tid != BUILDING or (x, y) in seen:
                continue
            # The building: every building tile joined to this one, through the village walls around it too (a village's houses
            # stand inside its walls, its entrance in a gap), and what borders them.
            part, todo, border = [], [(x, y)], set()
            seen.add((x, y))
            while todo:
                cx, cy = todo.pop()
                if grid[cy][cx] == BUILDING:
                    part.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        if grid[ny][nx] in (BUILDING, VILLAGE_WALL) and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            todo.append((nx, ny))
                        elif grid[ny][nx] not in (BUILDING, VILLAGE_WALL):
                            border.add(grid[ny][nx])
            meta_kind = [kind(game, tileset, chapter, tiles[cy][cx] >> 2, BUILDING) for cx, cy in part]
            if border & CASTLE_DOORS:
                k = 'castle'
            elif border & VILLAGE_DOORS:
                k = 'village'
            else:
                k = None
            for (cx, cy), mk in zip(part, meta_kind):
                # A metatile range of its own (ruins, void) wins; otherwise the entrance's kind, else the tileset's.
                own = any(first <= tiles[cy][cx] >> 2 <= last for first, last, _ in METATILES.get(game, {}).get(tileset, ()))
                chosen = mk if own else (k or CHAPTERS.get(game, {}).get(chapter) or TILESETS[game].get(tileset, 'castle'))
                out = LETTERS[chosen]
                letters[cy][cx] = out
                PLACED.setdefault(game, {}).setdefault((BUILDING, out), 0)
                PLACED[game][(BUILDING, out)] += 1


def kind_of_letter(ch):
    return next((k for k, v in LETTERS.items() if v == ch), None)


def table_letters(game, tid, base_letter, base_name):
    """The (letter, name) pairs a terrain id was drawn with: a wall's kinds (`PLACED`), anything else its own."""
    placed = sorted({out for (t, out) in PLACED.get(game, {}) if t == tid})
    if tid in THEMED and placed:
        return [(out, NAMES[kind_of_letter(out)]) for out in placed]
    return [(base_letter, base_name)]
