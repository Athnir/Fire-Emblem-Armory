"""
Echoes: Shadows of Valentia's tables (Data/*.bin.lz, read with scripts/fe15_bin.py) and English text (m/@NOA_EN), shared by the
generators. Formats are in data-raw/fe15/README.md.
"""
import os
from functools import lru_cache

import fates_text
from fe15_bin import ROMFS, load, table

TEXT = os.path.join(ROMFS, 'm', '@NOA_EN')
# Item.bin's 種類 (kind).
KINDS = {1: 'Sword', 2: 'Lance', 3: 'Axe', 4: 'Bow', 5: 'Black magic', 6: 'White magic', 7: 'Monster', 8: 'Valuable', 9: 'Shield',
         10: 'Ring', 11: 'Provision', 12: 'Headgear', 13: 'Silver mark', 14: 'Gold mark', 15: 'Other'}
# Skill.bin's 特効 (effective against): the class kinds a class's 種別 marks.
EFFECTIVE = {2: 'horseback', 4: 'armour', 8: 'flying', 32: 'terror'}


@lru_cache(None)
def text(name):
    path = os.path.join(TEXT, name + '.bin.lz')
    return fates_text.read(path) if os.path.exists(path) else {}


def say(label, *files):
    """A label's English text from the first file that has it."""
    for f in files or ('Name', 'Item', 'Skill', 'Job', 'GameData'):
        t = text(f).get(label)
        if t is not None:
            return t
    return None


@lru_cache(None)
def items():
    return table('Data/Item.bin.lz')


@lru_cache(None)
def skills():
    return table('Data/Skill.bin.lz')


@lru_cache(None)
def jobs():
    return table('Data/Job.bin.lz')


@lru_cache(None)
def persons():
    return table('Data/Person.bin.lz')


@lru_cache(None)
def chapters():
    return table('Data/Chapter.bin.lz')


@lru_cache(None)
def item_bin():
    return load('Data/Item.bin.lz')


def item_name(iid):
    r = items().by_id.get(iid)
    return say(r['名前'], 'Item') if r else None


def lists(b, label, size):
    """A [name, count, pointer] header's records: the raw bytes of each (Item.bin's forge and evolution lists, Access.bin, Dispos)."""
    o = b.at[label]
    n, p = b.u32(o + 4), b.u32(o + 8)
    return [(p + i * size, b.d[0x20 + p + i * size:0x20 + p + (i + 1) * size]) for i in range(n)]


def forge(label):
    """A weapon's forge list (Item.bin's 錬成): the first row is its value in marks; each further row a star, with what that star
    costs and the weapon's total bonuses at it. Rows: u16 silver, u16 gold, s8 Mt, s8 Wt, u8 Hit, u8 Crit, 2 unused."""
    b = item_bin()
    rows = []
    for _, raw in lists(b, label, 10):
        s = lambda i: raw[i] - 256 if raw[i] > 127 else raw[i]
        rows.append({'silver': raw[0] | raw[1] << 8, 'gold': raw[2] | raw[3] << 8, 'mt': s(4), 'wt': s(5), 'hit': raw[6], 'crit': raw[7]})
    return rows


def evolve(label):
    """What a weapon evolves into (Item.bin's 進化): [target IID, u16 silver, u16 gold, u8 stars needed, 3 unused]."""
    b = item_bin()
    out = []
    for o, raw in lists(b, label, 12):
        out.append({'into': b.str(o), 'silver': raw[4] | raw[5] << 8, 'gold': raw[6] | raw[7] << 8, 'stars': raw[8]})
    return out
