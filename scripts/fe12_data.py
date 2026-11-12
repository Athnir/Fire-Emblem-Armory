"""
Read New Mystery of the Emblem's database (data/FE12Data.bin: Awakening's container, `scripts/fe13_bin.py`) from data-raw/fe12/rom
(`scripts/fe12_extract.py`), named in English by the translation patch (`scripts/fe12_names.py`). Its labels name the tables; the
records keep Shadow Dragon's layouts where they share a table (data-raw/fe12/README.md):

- PersonData (92 bytes): +0 PID, +4 face, +8 name (a generic's: its army's; a named person's is MPID_ + its PID's or its face's
  tail), +0x2c u32
  its attributes (0x01 a woman, 0x4000 the avatar...), +0x30 five support slots.
- JobData (80 bytes): +0 JID, +4 name, +0x28 its row of TerrainCost, +0x29 Mov, +0x36 u16 its kinds (the bits items' effectiveness
  checks: EFFECTIVE), +0x38 u32 its attributes (0x01 a woman's class, 0x800 promoted).
- ItemData (60 bytes): Shadow Dragon's Item (scripts/fe11_data.py), but every weapon's +0x18 (Wt) is 0 (nothing in battle reads
  it: attack speed is Spd), and +0x24 and +0x28 are u32s: +0x24 what it does (0x01 usable, 0x02 brave, 0x04 magic, 0x08 siege, 0x20 a
  healing staff, 0x40 devil, 0x400 Imhullu's shield, 0x800 Starlight, 0x4000 no harm from magic, 0x40000 the Lightsphere, 0x80000 the
  Iote's Shield, 0x10000000 never wears out), +0x28 more (0x100 drains HP, 0x800 ignores Def and Res) and who may use it (its high
  bits, the equip check at arm9 0x204f870).
- MapTableData (44 bytes): +0 the map's file, +4 the file it shares (the prologue's B chapters), +8 its title (MCT...), +0x15 its goal.
- TerrainData (16 bytes), TerrainCategory, TerrainCost: as Shadow Dragon's.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe12_names import say  # noqa: E402
from fe13_bin import Bin  # noqa: E402

ROM = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe12', 'rom')
KINDS = {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Tome', 5: 'Staff', 6: 'Stone', 7: 'Ballista', 8: 'Item'}
# An item's +0x2c (u16) against a class's +0x36 kinds (u16; overlay 00 0x21f3494): 0x01 dragons, 0x02 Medeus, 0x04 armour, 0x08
# ballisticians, 0x10 horseback, 0x20 fliers, 0x40 manaketes, 0x80 sword fighters (Mercenary, Hero, Myrmidon, Swordmaster), 0x100
# archers (Archer, Sniper: only the Longbow's lock reads it).
EFFECTIVE = {0x01: 'dragon', 0x02: 'medeus', 0x04: 'armour', 0x08: 'ballistician', 0x10: 'horseback', 0x20: 'flying', 0x40: 'manakete',
             0x80: 'swordfighter'}
RANKS = ['A', 'B', 'C', 'D', 'E']
# The downloadable chapters' placements, scripts and text are on the cartridge under scrambled names (each file's own messages say
# which chapter it is: MSDL001_... in m/jk3at).
DLC_FILES = {'dl001': 'ajk3at', 'dl002': 'f9noa4bg', 'dl003': '2invaw9a1'}
DLC_TEXT = {'dl001': 'jk3at', 'dl002': '9noa4bg', 'dl003': 'invaw9a1'}

_db = None


def db():
    global _db
    if _db is None:
        _db = Bin(open(os.path.join(ROM, 'data', 'FE12Data.bin'), 'rb').read())
    return _db


def count(i):
    """FooterData's counts: 0 people, 1 classes, 2 items."""
    return db().u32(db().at['FooterData'] + 4 * i)


def table(name, size, n):
    start = db().at[name]
    return [(i, start + i * size) for i in range(n)]


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
    for i, o in table('ItemData', 60, count(2)):
        r = b.d[0x20 + o:0x20 + o + 60]
        out.append({
            'index': i, 'iid': b.str(o), 'name': say(b.str(o + 4)), 'help': say(b.str(o + 8)),
            'per_use': struct.unpack_from('<H', r, 0x0e)[0], 'kind': r[0x10], 'sub': r[0x11], 'exp': r[0x12], 'uses': r[0x14],
            'mt': r[0x15], 'hit': r[0x16], 'crit': r[0x17], 'wt': r[0x18], 'min': r[0x19], 'max': r[0x1a], 'mov': r[0x1b],
            'hp': r[0x1c], 'stats': dict(zip(('str', 'mag', 'skl', 'spd', 'lck', 'def', 'res'), r[0x1d:0x24])),
            'flags': struct.unpack_from('<I', r, 0x24)[0], 'more': struct.unpack_from('<I', r, 0x28)[0],
            'effective': [t for bit, t in EFFECTIVE.items() if struct.unpack_from('<H', r, 0x2c)[0] & bit], 'raw': r,
            'tier': r[0x3a], 'noforge': bool(r[0x2b] & 0x40),
        })
    return out


def persons():
    b = db()
    out = []
    for i, o in table('PersonData', 92, count(0)):
        pid, fid = b.str(o), b.str(o + 4)
        # A named person's name is MPID_ + its PID's tail, or its face's (PID_WOLEN's face is FID_WOLLEN: MPID_WOLLEN, Warren).
        name = say(b.str(o + 8)) or (say('MPID_' + pid[4:]) if pid else None) or (say('MPID_' + fid[4:]) if fid else None)
        out.append({'index': i, 'pid': pid, 'name': name, 'named': bool(b.str(o + 4)), 'attrs': b.u32(o + 0x2c),
                    'army': b.str(o + 8)})
    return out


def jobs():
    b = db()
    out = []
    for i, o in table('JobData', 80, count(1)):
        jid = b.str(o)
        out.append({'index': i, 'jid': jid, 'name': say(b.str(o + 4)), 'cost_row': b.u8(o + 0x28), 'mov': b.u8(o + 0x29),
                    'kinds': b.u16(o + 0x36), 'attrs': b.u32(o + 0x38)})
    return out


def maps():
    """[(file, shared file, title label, raw record)] for every map in MapTableData, in its order."""
    b = db()
    start, end = b.at['MapTableData'], b.at['TerrainData']
    out = []
    for o in range(start, end - 43, 44):
        if not b.str(o) or o + 8 not in b.ptrs:
            break
        out.append((b.str(o), b.str(o + 4) if o + 4 in b.ptrs else None, b.str(o + 8), b.d[0x20 + o:0x20 + o + 44]))
    return out


def chapters():
    """{file name: its title as the patch writes it ('Ch. 1 Grustian Expedition')}."""
    return {f: say(t) for f, _, t, _ in maps()}
