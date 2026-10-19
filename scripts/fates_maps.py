"""
Which game files make up each of the app's maps, and where in the dump each kind of file lives.

The cartridge is Birthright, so its route files sit in the romfs itself; Conquest's and Revelation's
come from their route packs (dlc/00000002 and dlc/00000035). Each DLC map is a pack of its own whose
files are all named E000, so a DLC map is found by its pack rather than its code.
"""
import glob
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
ROUTE_PACK = {'B': os.path.join(RAW, 'dlc', '00000002', 'local'), 'C': os.path.join(RAW, 'dlc', '00000035', 'local')}

# App map id -> (the game's chapter code, route, chapter number)
MAPS = {}
# App map id -> its DLC pack's folder (DLC maps only)
PACK = {}
for n in range(1, 6):
    MAPS[f'fe14-{n}'] = (f'A00{n}', 'Shared', n)
for prefix, short, route in (('A', 'b', 'Birthright'), ('B', 'c', 'Conquest'), ('C', 'r', 'Revelation')):
    for n in range(6, 28):
        MAPS[f'fe14{short}-{n}'] = (f'{prefix}0{n:02d}', route, n)
    MAPS[f'fe14{short}-endgame'] = (f'{prefix}028', route, 28)
for n in range(1, 23):
    MAPS[f'fe14-x{n}'] = (f'X{n:03d}', 'Paralogue', n)
# The DLC maps, in the order the packs were released (their folder numbers), then the amiibo Hero Battles.
for i, pack in enumerate(sorted(glob.glob(os.path.join(RAW, 'dlc', '*', 'local')))):
    if os.path.exists(os.path.join(pack, 'GameData', 'Terrain', 'E000.bin.lz')):
        map_id = f'fe14-dlc-{os.path.basename(os.path.dirname(pack))[-2:]}'
        MAPS[map_id] = ('E000', 'DLC', i)
        PACK[map_id] = pack
for n in range(1, 5):
    MAPS[f'fe14-hero{n}'] = (f'M00{n}', 'DLC', 100 + n)

# DLC grind maps (Boo Camp, Beach Brawl, Ghostly Gold, Museum Melee, Royal Royale): they spawn more and
# stronger enemies the more you defeat in a run, so only where each group spawns and where it heads are kept.
GRIND = {'fe14-dlc-67', 'fe14-dlc-68', 'fe14-dlc-6a', 'fe14-dlc-6b', 'fe14-dlc-6d'}

# Paralogues 1-6 are open on every route; 7-14 need a Hoshidan father, 15-22 a Nohrian one.
PARALOGUE_ROUTES = {n: ['Birthright', 'Conquest', 'Revelation'] if n <= 6 else
                    ['Birthright', 'Revelation'] if n <= 14 else ['Conquest', 'Revelation'] for n in range(1, 23)}


def _first(paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def find(kind, code, pack=None):
    """A chapter's Dispos or Person file."""
    if pack:
        return _first([os.path.join(pack, 'GameData', kind, code + '.bin.lz')])
    route = ROUTE_PACK.get(code[0])
    return _first(([os.path.join(route, 'GameData', kind, code[0], code + '.bin.lz')] if route else []) +
                  [os.path.join(RAW, kind, code + '.bin.lz'), os.path.join(RAW, kind, code[0], code + '.bin.lz')])


def find_script(code, pack=None):
    """A chapter's event script."""
    if pack:
        return _first([os.path.join(pack, 'Scripts', code + '.cmb')])
    route = ROUTE_PACK.get(code[0])
    return _first(([os.path.join(route, 'Scripts', code[0], code + '.cmb')] if route else []) +
                  [os.path.join(RAW, 'Scripts', code + '.cmb'), os.path.join(RAW, 'Scripts', code[0], code + '.cmb')])


def terrain(code, pack=None):
    return os.path.join(pack, 'GameData', 'Terrain', code + '.bin.lz') if pack else os.path.join(RAW, 'Terrain', code + '.bin.lz')


def terrain_script(code, pack=None):
    """A chapter's terrain script: its Dragon Veins, chests, villages and objective tiles."""
    return _first([os.path.join(pack or RAW, 'Scripts', code + '_Terrain.cmb')])


def pack_text(pack):
    """A DLC pack's own English text (its title, rules and characters), or None."""
    return _first([os.path.join(pack, 'm', '@E', 'E000.bin.lz')]) if pack else None


_TEXT = {}


def text_for(pack=None):
    """The game's English text, with a DLC pack's own text on top of it."""
    from fates_text import read
    if None not in _TEXT:
        _TEXT[None] = read(os.path.join(RAW, 'm', '@E', 'GameData.bin.lz'))
        # DLC items and skills (e.g. the Aether scroll) name themselves in their pack's shared text.
        for p in sorted(glob.glob(os.path.join(RAW, 'dlc', '*', 'global', 'm', '@E', '*.bin.lz'))):
            _TEXT[None].update(read(p))
    if pack not in _TEXT:
        extra = pack_text(pack)
        _TEXT[pack] = {**_TEXT[None], **(read(extra) if extra else {})}
    return _TEXT[pack]
