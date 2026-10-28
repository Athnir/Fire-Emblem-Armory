"""The app's terrain codes: two characters per map tile.

The first character is the group, the second numbers the code inside it (a-z, then 0-9: 36 per group):
  t  terrain you walk on, with no bonus of its own (floor, bridge, sand, water some units wade)
  b  bonus tiles: terrain with stats (woods, forts, thrones, gates, ledges, the Tower's floors)
  h  healing tiles
  d  damage tiles
  w  walls and blocked terrain (some let fliers over)
  o  objects (chests, doors, villages, buildings, siege machines)
  s  terrain that changes during the chapter (frozen lakes, darkness)

Every code means one thing in every game. Each builder keeps its own one-letter names internally and
converts on output with GAME[game]; a game's letter can mean something else in another game (Fates' P is
an acid bog, Radiant Dawn's a wetland), so each game has its own mapping.

Run this file to regenerate src/data/maps/terrainCodes.ts (the TerrainCode type and each code's name).
"""
import os

CODES = {
    # Terrain.
    'ta': 'Plain / floor', 'tb': 'Bridge', 'tc': 'Stairs', 'td': 'Desert / sand', 'te': 'Wasteland',
    'tf': 'Water (Fates: some units wade)', 'tg': 'River / shallows', 'th': 'Wetland', 'ti': 'Swamp',
    'tj': 'Shallow water (puddle)', 'tk': 'Sand', 'tl': 'Road', 'tm': 'Ruins (rough ground)',
    'tn': 'Indoor floor (no mounts or fliers)',
    # Bonus tiles.
    'ba': 'Woods / thicket', 'bb': 'Fort', 'bc': 'Throne / goal tile', 'bd': 'Gate', 'be': 'Old gate',
    'bf': 'Gateway', 'bg': 'Ledge', 'bh': 'Pillar (Fates: stand on it)', 'bi': 'Cushion', 'bj': 'Ward',
    'bk': 'Talisman tile', 'bl': 'Mountain path / shore', 'bm': 'Mountain (Fates)', 'bn': 'Cloud',
    'bo': 'Defense floor', 'bp': 'Strong defense floor', 'bq': 'Resistance floor',
    'br': 'Defense floor (Avo +15)', 'bs': 'Fissure', 'bt': 'Deep forest', 'bu': 'Peak', 'bv': 'Castle gate (Avo +30)', 'bw': 'Magic floor',
    'bx': 'Magic seal',
    # Healing.
    'ha': 'Healing tile', 'hb': 'Healing thicket', 'hc': 'Chamber', 'hd': 'Healing jar', 'he': 'Beside a healing jar',
    'hf': 'Healing floor',
    # Damage.
    'da': 'Acid bog', 'db': 'Muck', 'dc': 'Caltrops', 'dd': 'Burning ground',
    # Walls and blocked terrain.
    'wa': 'Wall', 'wb': 'Cliff / peak', 'wc': 'Snowy peak', 'wd': 'Chasm / hole', 'we': 'Lake / sea', 'wf': 'Sky',
    'wg': 'Partition / fence', 'wh': 'Thick wood / tree', 'wi': 'Storm', 'wj': 'Rubble', 'wk': 'Pond / moat',
    'wl': 'River (impassable)', 'wm': 'Dark waters', 'wn': 'Valley', 'wo': 'Drawbridge (raised)',
    # Objects.
    'oa': 'Chest', 'ob': 'Door', 'oc': 'Village', 'od': 'Village (closed)', 'oe': 'Building', 'of': 'Ballista',
    'og': 'Fire orb', 'oh': 'Launcher', 'oi': 'Summoning sigil', 'oj': 'Church', 'ok': 'Tower', 'ol': 'Castle',
    'om': 'Armory', 'on': 'Vendor (item shop)', 'oo': 'Arena', 'op': 'Secret shop', 'oq': 'Supply', 'or': 'Chest (outdoors)',
    # Changes during the chapter.
    'sa': 'Frozen lake', 'sb': 'Darkness',
}

# Letters every game uses the same way.
_COMMON = {
    '.': 'ta', 'b': 'tb', 'S': 'tc', 's': 'td', 'f': 'ba', 'F': 'bb', 't': 'bc', 'E': 'bg',
    '#': 'wa', 'C': 'wb', 'x': 'wd', 'a': 'we', 'l': 'wg', 'k': 'wh', 'r': 'wj',
    'c': 'oa', 'd': 'ob', 'v': 'oc', 'B': 'oe', 'L': 'of',
}

GAME = {
    'fates': {
        **_COMMON,
        'W': 'te', 'w': 'tf', 'u': 'tj', 'g': 'bd', 'G': 'be', 'e': 'bf', 'p': 'bh', 'Q': 'bi', 'K': 'bj',
        'n': 'bm', 'Z': 'bs', 'H': 'ha', 'j': 'hc', 'P': 'da', 'M': 'db', 'T': 'dc', 'z': 'wi', 'D': 'wm',
        'V': 'od', 'O': 'og', 'U': 'oh', 'Y': 'oi', 'i': 'sa', 'X': 'sb',
    },
    'tellius': {
        **_COMMON,
        'w': 'tg', 'P': 'th', 'M': 'ti', 'K': 'bk', 'W': 'bl', 'J': 'bn', 'A': 'bo', 'q': 'bp', 'm': 'bq',
        'y': 'br', 'H': 'hb', 'I': 'hd', 'N': 'he', 'h': 'hf', 'o': 'dd', 'n': 'wc', 'R': 'wf', 'u': 'wk',
    },
}
# Genealogy of the Holy War: sea and river are walls to everyone but fliers and pirates; the castle itself is an object tile.
GAME['fe4'] = {
    **_COMMON,
    'w': 'wl', 'm': 'bm', 'D': 'bt', 'g': 'bd', 'N': 'ol', 'y': 'tk', 'R': 'tl', 'h': 'oj', 'T': 'ok',
}

# The Binding Blade: walkers wade its rivers (at a cost, some can't); its peaks are climbable by brigands and berserkers; the
# Chapter 8x valley lets only fliers and dragons across. Its shops and arena are their own tiles.
GAME['fe6'] = {
    **_COMMON,
    'V': 'od', 'W': 'om', 'I': 'on', 'R': 'oo', 'g': 'bd', 'y': 'tk', 'w': 'tg', 'm': 'bm', 'P': 'bu', 'u': 'wk', 'q': 'bq',
    'p': 'bh', 'z': 'wn',
}

# The Blazing Blade and The Sacred Stones: The Binding Blade's terrain ids and more. Their sky, the deeps and the dark beyond some
# maps are walls only fliers cross; barrels, bones and a ship's gunnels work like cliffs; ruins slow everyone (cost 2).
GAME['fe7'] = {**GAME['fe6'], 'Z': 'wf', 'D': 'wm', 'x': 'wd', 'n': 'tm'}
# The Sacred Stones' second gate (terrain 35) gives 30 Avoid where its other (11) gives 20.
GAME['fe8'] = {**GAME['fe7'], 'Y': 'bv'}

# Path of Radiance's river can't be waded (Radiant Dawn's can).
# Thracia 776 (scripts/build-fe5-maps.py): its rivers, sea and lakes let pirates wade; magic floors and seals add 10 Magic.
GAME['fe5'] = {
    **_COMMON,
    'P': 'bu', 'w': 'tg', 'm': 'bm', 'y': 'tk', 'g': 'bd', 'u': 'wk', 'n': 'tm', 'h': 'oj', 'V': 'od', 'W': 'om', 'I': 'on', 'R': 'oo',
    'p': 'bh', 'Q': 'op', 'U': 'oq', 'Z': 'wo', 'e': 'te', 'A': 'bw', 'q': 'bx', 'O': 'tn', 'K': 'or',
}

GAME['fe9'] = {**GAME['tellius'], 'w': 'wl'}
GAME['fe10'] = GAME['tellius']

for _game, _m in GAME.items():
    assert set(_m.values()) <= set(CODES), (_game, set(_m.values()) - set(CODES))


def encode(game, letter):
    """One tile's code."""
    try:
        return GAME[game][letter]
    except KeyError:
        raise SystemExit(f'{game}: no terrain code for {letter!r}; add one to scripts/terrain_codes.py')


def encode_row(game, row):
    """A grid row of one-letter tiles as codes."""
    return ''.join(encode(game, c) for c in row)


def encode_map(game, m):
    """A built map's grid and terrain changes as codes."""
    m['grid'] = [encode_row(game, row) for row in m['grid']]
    for c in m.get('changes', []):
        for p in c.get('patch', []):
            p['becomes'] = encode(game, p['becomes'])
    return m


def write_ts(path):
    lines = [
        '/*',
        ' * GENERATED by scripts/terrain_codes.py. Do not edit by hand.',
        ' *',
        " * Each map tile is two characters: the group (t terrain, b bonus, h healing, d damage, w wall or",
        ' * blocked, o object, s changes during the chapter), then a letter or digit numbering it in the group.',
        ' */',
        '',
        'export const TERRAIN_CODES = {',
    ]
    lines += [f"  {code}: '{name}'," for code, name in CODES.items()]
    lines += ['} as const', '', '/** One map tile: a key of TERRAIN_CODES. */', 'export type TerrainCode = keyof typeof TERRAIN_CODES', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    write_ts(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'maps', 'terrainCodes.ts'))
