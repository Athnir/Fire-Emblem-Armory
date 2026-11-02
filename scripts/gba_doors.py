"""
What the GBA games' map changes do (The Binding Blade, The Blazing Blade, The Sacred Stones): doors, and what an event's script
reshapes (a throne room opening on a turn, a wall opening as an area is entered).

A chapter's map changes are 12-byte records up to an id of 0xFF: id, x, y, width, height (from the top-left), three unused
bytes, then a pointer to the replacement tiles (u16, rows from the top; tile >> 2 is the metatile, as on the map itself; a 0
leaves its tile as it is, which is how a change covers less than its rectangle). A door applies the first change whose
rectangle holds its tile; a scripted door (a location event with the door command) and any other script apply the changes at
the tiles they name. A room the tileset draws under its roof (Roof terrain) is closed to everyone until a change lifts the roof
(The Binding Blade's Chapter 6, its doors; Chapter 3's throne room). Each change is previewed like a Dragon Vein: the tiles it
reshapes, and what each becomes. An opening's changes are made before the battle, so the map starts with them.
"""
import struct

LOCKED = 'A locked door: open it with a key or a thief'


def read_changes(rom, at):
    """{id: (x, y, width, height, [tile, ...])} from the list at ROM offset `at` (None: the chapter has none)."""
    out = {}
    o = at
    while o is not None and rom[o] != 0xFF:
        x, y, w, h = rom[o + 1], rom[o + 2], rom[o + 3], rom[o + 4]
        ptr = struct.unpack_from('<I', rom, o + 8)[0]
        assert 0x08000000 <= ptr < 0x0A000000, (hex(o), hex(ptr))
        p = ptr - 0x08000000
        out[rom[o]] = (x, y, w, h, [struct.unpack_from('<H', rom, p + 2 * k)[0] for k in range(w * h)])
        o += 12
    return out


def change_at(changes, xy):
    """The id of the first change whose rectangle holds the tile: the one the game applies there (None: no change)."""
    x, y = xy
    return next((cid for cid, (cx, cy, w, h, _) in changes.items() if cx <= x < cx + w and cy <= y < cy + h), None)


def tiles_after(changes, letter_of, cids):
    """{(x, y): letter} for what the changes put down (a 0 tile leaves its tile: the corridor beside Chapter 6's rooms)."""
    out = {}
    for cid in cids:
        x0, y0, w, h, tiles = changes[cid]
        for k, t in enumerate(tiles):
            if t:
                out[(x0 + k % w, y0 + k // w)] = letter_of(t)
    return out


def apply(changes, letters, letter_of, cids):
    """Makes the changes on the map's letters (an opening's, before the battle: Chapter 1's raided village)."""
    for (x, y), letter in tiles_after(changes, letter_of, cids).items():
        if y < len(letters) and x < len(letters[y]):
            letters[y][x] = letter


def previews(changes, letters, letter_of, sources, roof):
    """{key: [((x, y), letter after)]} for each (key, [change ids]) in `sources`: the tiles that change, from the map's starting
    letters by [y][x]. Changed in place first: a roofed tile (`roof(xy)`) that a change turns into something a unit can stand on
    is a closed room ('Q') until then."""
    for _, cids in sources:
        for (x, y), letter in tiles_after(changes, letter_of, cids).items():
            if y < len(letters) and x < len(letters[y]) and roof((x, y)) and letter != '#':
                letters[y][x] = 'Q'
    out = {}
    for key, cids in sources:
        out[key] = [((x, y), letter) for (x, y), letter in sorted(tiles_after(changes, letter_of, cids).items(),
                                                                  key=lambda kv: (kv[0][1], kv[0][0]))
                    if y < len(letters) and x < len(letters[y]) and letters[y][x] != letter]
    return out


def door_change(door_app, patch_app, others_app):
    """The app's record for one door: a change previewed before and after (tiles already in the app's coordinates). `others_app`:
    the other doors it opens with it (Chapter 6's paired doors)."""
    room = len(patch_app) > 1 + len(others_app)
    words = LOCKED + (', and the room behind it opens' if room else '') + '.'
    if others_app:
        words += ' ' + ('Its other door at ' if room else 'The door at ') + ' and '.join(f'({x}, {y})' for x, y in others_app) \
            + (' opens too.' if len(others_app) == 1 else ' open too.')
    return {'id': f'door-{door_app[0]}-{door_app[1]}', 'trigger': 'event', 'tile': {'default': list(door_app)}, 'usableBy': '',
            'effect': words, 'patch': [{'tile': list(t), 'becomes': letter} for t, letter in patch_app]}


WATER = set('auwD')  # sea, lake / water, river, deeps


def closed_room(labels):
    """The terrain entry for a room under its roof: no one enters it until a door or a script opens it."""
    return {'name': 'Roof (closed room)', 'def': 0, 'res': 0, 'avo': 0, 'heal': 0, 'move': {label: None for label in labels},
            'note': 'A room under its roof: no unit can enter it, fliers included, until a door into it opens.'}


def what_opens(before, after):
    """'the closed room opens', 'the wall opens'...: what a patch does, from the letters before and after."""
    kinds = []
    recedes = any(b in WATER and a not in WATER for b, a in zip(before, after))
    rises = any(a in WATER and b not in WATER for b, a in zip(before, after))
    if recedes and rises:
        kinds.append('the water shifts')  # land and sea trade places (Ephraim's Chapter 11's phantom ship moving on)
    elif recedes:
        kinds.append('the water recedes')
    elif rises:
        kinds.append('the water rises')
    if any(b == 'Q' for b, _ in zip(before, after)):
        kinds.append('the closed room opens')
    if any(b == 'd' and a != 'd' for b, a in zip(before, after)):
        kinds.append('the door opens')
    if any(b == '#' and a not in '#lQ' for b, a in zip(before, after)):
        kinds.append('the wall opens')
    if any(b == 'l' and a not in '#lQ' for b, a in zip(before, after)):
        kinds.append('the fence opens')
    if any(b == 'v' and a == 'V' for b, a in zip(before, after)):
        kinds.append('the village closes')
    if any(b == 'B' and a == 'V' for b, a in zip(before, after)):
        kinds.append('the house closes')
    return ' and '.join(kinds) if kinds else 'the map changes'


def event_change(tile_app, patch_app, effect):
    """The app's record for a change a chapter's script makes (tiles in the app's coordinates)."""
    return {'id': f'event-{tile_app[0]}-{tile_app[1]}', 'trigger': 'event', 'tile': {'default': list(tile_app)}, 'usableBy': '',
            'effect': effect, 'patch': [{'tile': list(t), 'becomes': letter} for t, letter in patch_app]}


def unique_ids(changes):
    """Two changes on one tile (Chapter 30's house, closed by its turn 12 or by an event) keep apart: '-2', '-3' on the later."""
    seen = {}
    for c in changes:
        n = seen.get(c['id'], 0) + 1
        seen[c['id']] = n
        if n > 1:
            c['id'] = f"{c['id']}-{n}"


WALL, SNAG = 27, 51


def breakables(changes, grid, wall_hp):
    """[(tile, hp, kind)]: what can be attacked down, each with the map change at its tile, which the game makes when its HP runs
    out. A cracked wall (terrain 27) is one obstacle at the top of its column (the tile above isn't one), with the chapter's wall HP;
    a snag (51) has 20 (The Blazing Blade 0x0802BBB8, The Sacred Stones 0x0802E3D2; The Binding Blade's 0x08026C66 has no snags)."""
    out = []
    for y, row in enumerate(grid):
        for x, t in enumerate(row):
            if t == WALL and not (y > 0 and grid[y - 1][x] == WALL):
                out.append(((x, y), wall_hp, 'wall'))
            elif t == SNAG:
                out.append(((x, y), 20, 'snag'))
    return [(xy, hp, kind) for xy, hp, kind in out if change_at(changes, xy) is not None]


def breakable_change(tile_app, hp, kind, patch_app):
    """The app's record for a wall or snag: previewed broken."""
    what = 'A cracked wall' if kind == 'wall' else 'A snag'
    return {'id': f'break-{tile_app[0]}-{tile_app[1]}', 'trigger': 'breakable', 'tile': {'default': list(tile_app)},
            'usableBy': 'Any unit that can attack it', 'effect': f'{what} with {hp} HP: attack it down and it opens.',
            'patch': [{'tile': list(t), 'becomes': letter} for t, letter in patch_app]}
