"""
Which game files make up each of the app's maps, and where in the dump each kind of file lives.

The cartridge is Birthright, so its route files sit in the romfs itself; Conquest's and Revelation's
come from their route packs (dlc/00000002 and dlc/00000035).
"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
ROUTE_PACK = {'B': os.path.join(RAW, 'dlc', '00000002', 'local'), 'C': os.path.join(RAW, 'dlc', '00000035', 'local')}

# App map id -> (the game's chapter code, route, chapter number)
MAPS = {}
for n in range(1, 6):
    MAPS[f'fe14-{n}'] = (f'A00{n}', 'Shared', n)
for prefix, short, route in (('A', 'b', 'Birthright'), ('B', 'c', 'Conquest'), ('C', 'r', 'Revelation')):
    for n in range(6, 28):
        MAPS[f'fe14{short}-{n}'] = (f'{prefix}0{n:02d}', route, n)
    MAPS[f'fe14{short}-endgame'] = (f'{prefix}028', route, 28)


def _first(paths):
    return next((p for p in paths if os.path.exists(p)), None)


def find(kind, code):
    """A chapter's Dispos or Person file."""
    pack = ROUTE_PACK.get(code[0])
    return _first(([os.path.join(pack, 'GameData', kind, code[0], code + '.bin.lz')] if pack else []) +
                  [os.path.join(RAW, kind, code + '.bin.lz'), os.path.join(RAW, kind, code[0], code + '.bin.lz')])


def find_script(code):
    """A chapter's event script."""
    pack = ROUTE_PACK.get(code[0])
    return _first(([os.path.join(pack, 'Scripts', code[0], code + '.cmb')] if pack else []) +
                  [os.path.join(RAW, 'Scripts', code + '.cmb'), os.path.join(RAW, 'Scripts', code[0], code + '.cmb')])


def terrain(code):
    return os.path.join(RAW, 'Terrain', code + '.bin.lz')


def terrain_script(code):
    """A chapter's terrain script: its Dragon Veins, chests, villages and objective tiles."""
    return _first([os.path.join(RAW, 'Scripts', code + '_Terrain.cmb')])
