"""The app's terrain codes: two characters per map tile.

The first character is the group, the second numbers the code inside it (a-z, then 0-9: 36 per group):
  t  terrain you walk on, with no bonus of its own (floor, bridge, sand, water some units wade)
  b  bonus tiles: terrain with stats (woods, forts, thrones, gates, ledges, the Tower's floors)
  h  healing tiles
  d  damage tiles
  w  walls and blocked terrain (some let fliers over)
  o  objects (chests, doors, villages, buildings, siege machines)
  s  terrain that changes during the chapter (frozen lakes, darkness)
  e  effects laid over a tile, which still counts under them (Engage's Dragon Vein terrain and miasma: their numbers add to the tile's)

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
    'tn': 'Indoor floor (no mounts or fliers)', 'to': 'Stream', 'tp': 'Tunnel', 'tq': 'Fell floor (Avo -20)',
    'tr': 'Ice (forest costs, no bonus)', 'tx': 'Fell sigil (dragons only)', 'ts': 'Bridge under a snag (once cleared)', 'tt': 'Ledge (climbable, no bonus)',
    'tu': "Plain / floor (the lord can't enter)", 'tv': 'Plain (Avo +5)', 'tw': 'Floor (slows some monsters)',
    # Bonus tiles.
    'ba': 'Woods / thicket', 'bb': 'Fort', 'bc': 'Throne / goal tile', 'bd': 'Gate', 'be': 'Old gate',
    'bf': 'Gateway', 'bg': 'Ledge', 'bh': 'Pillar (Fates: stand on it)', 'bi': 'Cushion', 'bj': 'Ward',
    'bk': 'Talisman tile', 'bl': 'Mountain path / shore', 'bm': 'Mountain (Fates)', 'bn': 'Cloud',
    'bo': 'Defense floor', 'bp': 'Strong defense floor', 'bq': 'Resistance floor',
    'br': 'Defense floor (Avo +15)', 'bs': 'Fissure', 'bt': 'Deep forest', 'bu': 'Peak', 'bv': 'Castle gate (Avo +30)', 'bw': 'Magic floor',
    'bx': 'Magic seal', 'by': 'Floor (Avo +30)', 'bz': 'Stairs (Avo +10)', 'b0': 'Floor (Avo +20)', 'b1': 'Bulwark (no horses)',
    'b2': 'Grave (Avo +60)', 'b3': 'Pillar / thicket (Avo +30)', 'b4': 'Coast', 'b5': "Woods (the lord can't enter)",
    'b6': "Fort (the lord can't enter)", 'b7': "Mountain (the lord can't enter)", 'b8': 'Thicket (Avo +20)',
    'b9': 'Floor (Avo +40)',
    # Healing.
    'ha': 'Healing tile', 'hb': 'Healing thicket', 'hc': 'Chamber', 'hd': 'Healing jar', 'he': 'Beside a healing jar',
    'hf': 'Healing floor', 'hg': 'Prayer stone', 'hh': 'Protection tile (Avo +30, heals)',
    # Damage.
    'da': 'Acid bog', 'db': 'Muck', 'dc': 'Caltrops', 'dd': 'Burning ground', 'de': 'Spikes',
    'df': 'Swamp (hurts)', 'dg': 'Floor trap', 'dh': 'Crater',
    # Walls and blocked terrain.
    'wa': 'Wall', 'wb': 'Cliff / peak', 'wc': 'Snowy peak', 'wd': 'Chasm / hole', 'we': 'Lake / sea', 'wf': 'Sky',
    'wg': 'Partition / fence', 'wh': 'Thick wood / tree', 'wi': 'Storm', 'wj': 'Rubble', 'wk': 'Pond / moat',
    'wl': 'River (impassable)', 'wm': 'Dark waters', 'wn': 'Valley', 'wo': 'Drawbridge (raised)', 'wp': 'Magma',
    'wq': 'Rubble (blocks fliers too)', 'wr': 'Ice to dig through', 'ws': 'Closed room (until a door opens)',
    'wt': 'Rock', 'wv': 'Abyss / waterfall', 'ww': "Ire (Grima's tile: no unit can enter)", 'wx': 'Castle (fliers only)',
    'wz': 'Breakable wall',
    # Objects.
    'oa': 'Chest', 'ob': 'Door', 'oc': 'Village', 'od': 'Village (closed)', 'oe': 'Building', 'of': 'Ballista',
    'og': 'Fire orb', 'oh': 'Launcher', 'oi': 'Summoning sigil', 'oj': 'Church', 'ok': 'Tower', 'ol': 'Castle',
    'om': 'Armory', 'on': 'Vendor (item shop)', 'oo': 'Arena', 'op': 'Secret shop', 'oq': 'Supply', 'or': 'Chest (outdoors)',
    'os': 'Shop', 'ou': 'Castle (no healing)', 'ot': 'House (units stand in it)', 'ov': 'Lever',
    'o0': 'Castle gate (the castle is entered from it)',
    'ow': 'Crest Stone (in a wall: looters take it)', 'ox': 'Onager', 'oy': 'Magic cannon', 'oz': 'Flame cannon',
    # Changes during the chapter.
    'sa': 'Frozen lake', 'sb': 'Darkness', 'sc': 'Lava floor (turns to hazard)',
    # Effects laid over a tile (the tile's own numbers still count: woods under fog give Avo +30 more).
    'ea': 'Fog (Avo +30)', 'eb': 'Fog over woods / pillars', 'ec': 'Water (Avo -30)', 'ed': 'Water over woods / pillars',
    'ee': 'Stone pillars (Def +3)', 'ef': 'Flames (hurt)', 'eg': 'Miasma', 'eh': 'Miasma over woods / pillars', 'ei': 'Frost (Mov +2)',
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
        'n': 'bm', 'Z': 'bs', 'H': 'ha', 'j': 'hc', 'P': 'da', 'M': 'db', 'T': 'dc', 'q': 'de', 'o': 'dd', 'I': 'tr', 'z': 'wi', 'D': 'wm',
        'V': 'od', 'O': 'og', 'U': 'oh', 'Y': 'oi', 'i': 'sa', 'X': 'sb', 'R': 'wq', 'J': 'wr', 'N': 'tq',
    },
    'tellius': {
        **_COMMON,
        'w': 'tg', 'P': 'th', 'M': 'ti', 'K': 'bk', 'W': 'bl', 'J': 'bn', 'A': 'bo', 'q': 'bp', 'm': 'bq',
        'y': 'br', 'H': 'hb', 'I': 'hd', 'N': 'he', 'h': 'hf', 'o': 'dd', 'n': 'wc', 'R': 'wf', 'u': 'wk',
    },
}
# Genealogy of the Holy War: the sea is a wall to everyone but fliers and pirates, and so is the river, which pirates wade as in
# Thracia; the castle itself is an object tile, entered from its gate.
GAME['fe4'] = {
    **_COMMON,
    'w': 'tg', 'm': 'bm', 'D': 'bt', 'g': 'o0', 'N': 'ol', 'y': 'tk', 'R': 'tl', 'h': 'oj', 'r': 'tm',
}

# The Binding Blade: walkers wade its rivers (at a cost, some can't); its peaks are climbable by brigands and berserkers; the
# Chapter 8x valley lets only fliers and dragons across. Its shops and arena are their own tiles.
GAME['fe6'] = {
    **_COMMON,
    'V': 'od', 'W': 'om', 'I': 'on', 'R': 'oo', 'g': 'bd', 'y': 'tk', 'w': 'tg', 'm': 'bm', 'P': 'bu', 'u': 'wk', 'q': 'bq',
    'p': 'bh', 'z': 'wn', 'n': 'tm',
    # A room under its roof until a door into it opens (scripts/gba_doors.py).
    'Q': 'ws',
    # Houses (and The Blazing Blade's and The Sacred Stones' inns): Avo 10 like a village, but no looter goes for them (the raiders'
    # terrain list, scripts/gba_ai.py), so they're tiles of their own.
    'B': 'ot',
}

# The Blazing Blade and The Sacred Stones: The Binding Blade's terrain ids and more. Their sky, the deeps and the dark beyond some
# maps are walls only fliers cross; barrels, bones and a ship's gunnels work like cliffs; ruins slow everyone (cost 2).
# A snag's bridge (terrain 52) is a bridge only the final bosses' movement rows also cross.
GAME['fe7'] = {**GAME['fe6'], 'Z': 'wf', 'D': 'wm', 'x': 'wd', 'j': 'ts'}
# The Sacred Stones' second gate (terrain 35) gives 30 Avoid where its other (11) gives 20.
GAME['fe8'] = {**GAME['fe7'], 'Y': 'bv'}

# Path of Radiance's river can't be waded (Radiant Dawn's can).
# Thracia 776 (scripts/build-fe5-maps.py): its rivers, sea and lakes let pirates wade; magic floors and seals add 10 Magic.
GAME['fe5'] = {
    **_COMMON,
    'P': 'bu', 'w': 'tg', 'm': 'bm', 'y': 'tk', 'g': 'bd', 'u': 'wk', 'n': 'tm', 'h': 'oj', 'V': 'od', 'W': 'om', 'I': 'on', 'R': 'oo',
    'p': 'bh', 'Q': 'op', 'U': 'oq', 'Z': 'wo', 'e': 'te', 'A': 'bw', 'q': 'bx', 'O': 'tn', 'K': 'or',
}

# Mystery of the Emblem (scripts/build-fe3-maps.py): its castle gates heal and their flanks don't (two maps' flanks give Avo 30); its
# plains give 5 Avoid where its open floors give none, and most of its floors keep mounted units out (some with Avo 30); peaks let only
# fliers and Ice Dragons over, magma fliers and Manaketes; its streams stop pegasus and dragon knights (flying dragons cross) and most
# units on foot; its rubble is rough ground and its houses are stood in; one shop tile serves armories and vendors alike, drawn as
# whichever its shop is (the secret shops stand on ordinary tiles).
GAME['fe3'] = {
    **_COMMON,
    '.': 'tv', 'o': 'ta', 'r': 'tm', 'B': 'ot', 'J': 'b3', 'g': 'bv',
    'L': 'tl', 'w': 'tg', 'W': 'to', 'P': 'bu', 'm': 'bm', 'T': 'tp', 'M': 'wp', 'N': 'ol', 'G': 'ou', 'O': 'tn', 'p': 'bh',
    'K': 'or', 'Z': 'wo', 'H': 'os', 'R': 'oo', 'A': 'om', 'V': 'on', 'Q': 'by', 'X': 'ws', 'Y': 'oi',
}

# Shadow Dragon and the Blade of Light (scripts/build-fe1-maps.py): its grassland gives 5 Avoid where its floors give none; forts,
# castle gates and thrones heal; its rivers let some classes wade
# and its sea lets pirates and freelancers through; a village's roof is a wall; its stone walls (石垣) can be climbed slowly; a house
# tile is drawn as the shop its entry opens (the secret shops and storage stand in houses too).
GAME['fe1'] = {
    **_COMMON,
    'g': 'tv', 'D': 'od', 'w': 'tg', 'P': 'bu', 'm': 'bm', 'N': 'ol', 'p': 'bh', 'u': 'tm', 'A': 'om', 'V': 'on', 'R': 'oo', 'X': 'op',
}

# Awakening (scripts/build-fe13-maps.py): every tile that only fliers cross is a wall to the rest (cliffs, peaks, hills, buildings, bones,
# a ship's hull, rubble, fences, supplies, graves, water and lava); its stairs give 10 Avoid; Chapter 18's lava floors turn to hazard
# terrain on set turns.
GAME['fe13'] = {
    **_COMMON,
    'w': 'tg', 'm': 'bm', 'g': 'bd', 'p': 'bh', 'S': 'bz', 'V': 'od', 'Z': 'wf', 'M': 'wp', 'X': 'sc', 'H': 'dd', 'Y': 'oi', 'I': 'ww',
}

# Echoes: Shadows of Valentia (scripts/build-fe15-maps.py): its terrain gives Avoid and healing, never Def. Peaks, ramparts, caverns,
# railings and ships' hulls are walls to all but fliers; its castle tiles and broken bridges give 20 Avoid; graves are walkable (60 Avoid);
# pillars, thickets and coral cost what a forest does and give 30; lava and swamps hurt; the cursed ground of Thabes takes 20 Avoid away.
GAME['fe15'] = {
    **_COMMON,
    'w': 'tg', 'm': 'bm', 'Z': 'wf', 'T': 'b0', 'K': 'b1', 'G': 'b2', 'Y': 'b3', 'Q': 'by', 'R': 'tq', 'H': 'dd',
}

# Shadow Dragon (scripts/build-fe11-maps.py): its sea and peaks let only some classes over (pirates, fliers); floors are indoor
# tiles; shops, the arena and the storage are their own tiles; houses are buildings units stand in (Avo 5, never razed); a ledge is
# climbed at a cost and gives nothing; a castle is a wall to all but fliers; a razed village is walkable ruins; and five tiles the lord
# alone can't enter (the game's categories 25-29: plain, floor, forest, fort and mountain) get codes of their own.
GAME['fe11'] = {
    **_COMMON,
    'w': 'tg', 'm': 'bm', 'P': 'bu', 'g': 'bd', 'O': 'ta', 'p': 'bh', 'C': 'tt', 'N': 'wx', 'A': 'om', 'V': 'on', 'R': 'oo',
    'U': 'oq', 'Z': 'wo', 'M': 'wp', 'X': 'od', 'B': 'ot', 'r': 'tm', 'Q': 'tu', 'K': 'b5', 'J': 'b6', 'Y': 'b7',
}

# Three Houses (scripts/build-fe16-maps.py): its terrain gives Prt, Rsl and Avoid by kind; every tile only fliers cross is a wall to the
# rest (rivers, seas and lakes, lava, rocks, mountains and cliffs, fences, rubble, valleys, trenches, walls, houses, churches and ships),
# drawn by look; its floors indoors cost some monsters more than grass; two thickets (Avo 40 and 20), floors that give Avoid, Prt or
# Rsl, its two healing tiles (the Heal Tile +, with Prt and Rsl, and the plain Heal Tile, a floor code) and the prayer stone, burning
# floors, a swamp, floor traps and craters that hurt; breakable walls, levers, a raised bridge, the ballistae, onagers and fire orbs
# units fire, and the Holy Tomb's Crest Stones (in its walls: Chapter 11's looters take them) are their own tiles.
GAME['fe16'] = {
    **_COMMON,
    'O': 'tw', 'e': 'te', 'D': 'bt', 'T': 'b8', 'A': 'b9', 'q': 'bo', 'm': 'bq', 'H': 'ha', 'P': 'hg', 'o': 'dd', 'w': 'wl', 'R': 'wt',
    'z': 'wn', 'W': 'wz', 'V': 'ov', 'Q': 'ow', 'M': 'wp', 'Z': 'df', 'X': 'dg', 'K': 'dh', 'G': 'og', 'U': 'ox', 'h': 'tg', 'Y': 'wo',
    'J': 'hf',
}

# Engage (scripts/build-fe17-maps.py): its terrain table gives Avoid and healing, and movement by four cost groups (infantry and
# cavalry pay alike); every tile only fliers cross is a wall to the rest (rivers, seas and lakes, mountains and cliffs, rocks,
# rubble and low obstacles, lava, deep forest, holes), drawn by look; houses (their doors impassable: a village is visited from the
# tile in front), buildings and windmills are buildings; shoals, sand pits and ice (cost 3, Avo -30) are shallows; the protection
# tile (Avo +30, heals 10 HP) has its own healing code; breakable walls and junk, doors, chests, the ballistae, magic cannons and
# flame cannons units fire, and the Fell sigils only dragons cross, are their own tiles; a roof over a closed room (until its door
# opens) is one; what lies over a tile at the start (fog, water, stone pillars, flames, miasma, frost: its numbers add to the tile's)
# is its own, apart where the tile under it is woods or pillars.
GAME['fe17'] = {
    **_COMMON,
    'R': 'tl', 'h': 'tg', 'I': 'tg', 'p': 'bh', 'H': 'ha', 'P': 'hh', 'w': 'wl', 'K': 'wt', 'M': 'wp', 'T': 'wh', 'Y': 'wo',
    'W': 'wz', 'O': 'oy', 'G': 'oz', 'N': 'tx', 'Q': 'ws',
    'e': 'ea', 'j': 'eb', 'u': 'ec', 'U': 'ed', 'z': 'ee', 'i': 'ef', 'm': 'eg', 'D': 'eh', 'q': 'ei',
}

GAME['fe9'] = {**GAME['tellius'], 'w': 'wl', 'Y': 'b4', 'Q': 'ws'}
# Radiant Dawn: a flier can land on a rock or in a hole, but not on a cliff or over an abyss or waterfall (TerrainData's byte 7).
GAME['fe10'] = {**GAME['tellius'], 'O': 'wt', 'X': 'wv'}

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
    # A name with an apostrophe ("Ire (Grima's tile...)") goes in double quotes.
    lines += [f"  {code}: " + (f'"{name}"' if "'" in name else f"'{name}'") + ',' for code, name in CODES.items()]
    lines += ['} as const', '', '/** One map tile: a key of TERRAIN_CODES. */', 'export type TerrainCode = keyof typeof TERRAIN_CODES', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    write_ts(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'maps', 'terrainCodes.ts'))
