"""
Read Shadow Dragon's database (data/database: Awakening's container, `scripts/fe13_bin.py`) and its English text (m/en_*), from
data-raw/fe11/rom (`scripts/fe11_extract.py`). The database's labels name its tables; their records were laid out from the files
(data-raw/fe11/README.md):

- Person (80 bytes): +0 PID, +4 face, +8 name (generic people; a named one's is MPID_ + its PID's tail), unit data after.
- Job (92 bytes): +0 JID, +4 name, +0x28 its row of TerrainCost, +0x29 Mov, +0x36 its kinds (the bits items' effectiveness
  checks: 0x04 armour, 0x08 ballistician, 0x10 horseback, 0x20 flier, 0x40 manakete, 0x01 dragon), +0x39 0x08 promoted.
- Item (60 bytes): +0 IID, +4 name, +8 help, +0xe u16 price per use, +0x10 u8 kind (0 sword, 1 lance, 2 axe, 3 bow, 4 tome, 5 staff,
  6 dragonstone, 7 ballista, 8 item), +0x12 the weapon experience its rank needs, +0x14 uses, +0x15 Mt, +0x16 Hit, +0x17 Crit, +0x18
  Wt, +0x19 / +0x1a range (0xff: Mag / 2), +0x1b Mov, +0x1c HP (or what using it heals), +0x1d-+0x23 Str, Mag, Skl, Spd, Lck, Def,
  Res, +0x3a the Hard modes' weapon tier, +0x24 flags (0x01 usable, 0x02 brave, 0x04 magic damage, 0x08 a siege weapon, 0x20 / 0x30 a healing staff, 0x40 devil),
  +0x25 (0x04 Imhullu's shield, 0x08 Starlight's), +0x2c the classes it's effective against (0x01 dragons, 0x04 armour, 0x08
  ballisticians, 0x10 horseback, 0x20 fliers, 0x40 manaketes).
- WeaponLevel: the weapon experience each rank needs (A, B, C, D, E). WeaponDeadlock: the weapon triangle; WeaponBonus: the rank
  bonuses (12-byte rows: weapon kind(s), then a (Hit, Atk) pair per rank from A down).
- MapTbl (32 bytes): +0 the chapter's file name, +4 its title.
- Terrain (16 bytes): +0 id, +4 name, +8 its row of TerrainCategory (Avo, Def, ?, heal %), +0xc its column of TerrainCost.
"""
import glob
import os
import struct
import unicodedata

from fe13_bin import Bin

ROM = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe11', 'rom')
KINDS = {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Tome', 5: 'Staff', 6: 'Stone', 7: 'Ballista', 8: 'Item'}
EFFECTIVE = {0x01: 'dragon', 0x04: 'armour', 0x08: 'ballistician', 0x10: 'horseback', 0x20: 'flying', 0x40: 'manakete'}
RANKS = ['A', 'B', 'C', 'D', 'E']

_db = None
_text = None


def db():
    global _db
    if _db is None:
        _db = Bin(open(os.path.join(ROM, 'data', 'database'), 'rb').read())
    return _db


def text():
    """Every message label -> its English string (the m/en_* files)."""
    global _text
    if _text is None:
        _text = {}
        for f in sorted(glob.glob(os.path.join(ROM, 'm', 'en_*'))):
            t = Bin(open(f, 'rb').read())
            for o, n in t.labels:
                _text.setdefault(n, t.cstr(0x20 + o))
        # Some labels have a full-width letter in them (MPID_ROＬENSE, Lorenz's name): reachable by the plain spelling too.
        for n, v in list(_text.items()):
            _text.setdefault(unicodedata.normalize('NFKC', n), v)
    return _text


def say(label):
    return text().get(label) if label else None


def table(name, size, end):
    """The records of a database table, from its label to the next table's: [(index, offset)]."""
    b = db()
    start = b.at[name]
    return [(i, start + i * size) for i in range((b.at[end] - start) // size)]


def rank_thresholds():
    b = db()
    return [b.u8(b.at['WeaponLevel'] + i) for i in range(5)]


def rank_of(exp):
    """The rank a weapon needs ('E'..'A'), from the experience its +0x12 asks for."""
    for name, need in zip(RANKS, rank_thresholds()):
        if exp >= need:
            return name
    return ''


def items():
    b = db()
    out = []
    for i, o in table('Item', 60, 'ItemRefine'):
        r = b.d[0x20 + o:0x20 + o + 60]
        out.append({
            'index': i, 'iid': b.str(o), 'name': say(b.str(o + 4)), 'help': say(b.str(o + 8)),
            'per_use': struct.unpack_from('<H', r, 0x0e)[0], 'kind': r[0x10], 'sub': r[0x11], 'exp': r[0x12], 'uses': r[0x14],
            'mt': r[0x15], 'hit': r[0x16], 'crit': r[0x17], 'wt': r[0x18], 'min': r[0x19], 'max': r[0x1a], 'mov': r[0x1b],
            'hp': r[0x1c], 'stats': dict(zip(('str', 'mag', 'skl', 'spd', 'lck', 'def', 'res'), r[0x1d:0x24])),
            'flags': r[0x24], 'flags2': r[0x25], 'effective': [t for bit, t in EFFECTIVE.items() if r[0x2c] & bit], 'raw': r,
            # The Hard modes' weapon tier (0 Iron to 3 Brave, 0x7e a special weapon the modes forge instead, 0x7f never touched), and
            # +0x2b 0x40: never forged.
            'tier': r[0x3a], 'noforge': bool(r[0x2b] & 0x40),
        })
    return out


def persons():
    b = db()
    out = []
    for i, o in table('Person', 80, 'Job'):
        pid = b.str(o)
        # A double (PID_GARNEF_FALSE, one of Gharnef's illusions) has the original's name.
        name = (say(b.str(o + 8)) or say('MPID_' + pid[4:]) or say('MPID_' + pid[4:].replace('_FALSE', ''))) if pid else None
        # A named person has a face; a generic one has none and its name is its army's.
        out.append({'index': i, 'pid': pid, 'name': name, 'named': bool(b.str(o + 4))})
    return out


def jobs():
    b = db()
    out = []
    for i, o in table('Job', 92, 'Item'):
        out.append({'index': i, 'jid': b.str(o), 'name': say(b.str(o + 4)), 'cost_row': b.u8(o + 0x28), 'mov': b.u8(o + 0x29),
                    'kinds': b.u8(o + 0x36)})
    return out


def chapters():
    """{file name: title} for every map in MapTbl."""
    b = db()
    return {b.str(o): say(b.str(o + 4)) for _, o in table('MapTbl', 32, 'arena01')}
