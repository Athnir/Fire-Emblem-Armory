"""
Readers for Fire Emblem Awakening's data files (data-raw/fe13/romfs, from scripts/fe13_extract.py): the item, class, terrain and chapter
tables in data/GameData.bin, the per-chapter person and placement files, and the English text in m/E. Formats are in
data-raw/fe13/README.md.
"""
import functools
import os

from fe13_bin import ROMFS, Bin, load
from fates_lz import decompress
import fates_text

ITEM_SIZE = 56
CLASS_SIZE = 128
CHAPTER_SIZE = 68
TERRAIN_SIZE = 28
UNIT_SIZE = 116
PERSON_SIZE = 568

# Item +24: what kind of item it is.
TYPES = ['sword', 'lance', 'axe', 'bow', 'tome', 'staff', 'dragonstone', 'beaststone', 'claw', 'breath', 'item']
# Weapon rank by the weapon experience an item asks for (+28), from GameData's WeaponLevelData (A 91, B 61, C 36, D 16, E 1).
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']
# The class categories (GameData's JCID_ list, in bit order): class +90 holds the first eight, class +91 the rest. An item's
# effectiveness byte (+48) uses the first eight; its class locks (+4..+5) use the second.
JCID = ['flying', 'dragon', 'beast', 'monster', 'armour', 'boss', 'manakete', 'taguel']
JCID2 = ['lord', 'myrmidon', 'archer', 'darkmage', 'dancer']
DIFFS = {0x40: 'Normal', 0x80: 'Hard', 0x100: 'Lunatic'}
RARE = 0x7FFF  # a merchant's slot for a rare item: one of RARE_ITEMS
# The rare items a travelling merchant picks from: the program's list of IID names at 0x4d6468 (10 pointers; code.bin loads at 0x100000).
RARE_TABLE, RARE_COUNT = 0x4D6468, 10


@functools.lru_cache(None)
def gamedata():
    return load('data/GameData.bin.lz')


@functools.lru_cache(None)
def text(name='GameData', base=ROMFS):
    path = os.path.join(base, 'm', 'E', name + '.bin.lz')
    return fates_text.read(path) if os.path.exists(path) else {}


def name_of(label, base=ROMFS):
    """English text for a label from the game's own text (GameData's names)."""
    return text('GameData', base).get(label)


def table(label, size):
    b = gamedata()
    start = b.at[label]
    count = b.u32(b.at[label + 'Num'])
    return [start + i * size for i in range(count)]


@functools.lru_cache(None)
def weapon_levels():
    b = gamedata()
    o = b.at['WeaponLevelData']
    return [(b.u8(o + i), 'ABCDE'[i]) for i in range(5)]  # (exp, letter), A first


def rank_letter(exp):
    for need, letter in weapon_levels():
        if exp >= need:
            return letter
    return None


def items():
    b = gamedata()
    out = []
    for r in table('ItemData', ITEM_SIZE):
        d = b.d[0x20 + r:0x20 + r + ITEM_SIZE]
        out.append({
            'index': b.u16(r + 20), 'iid': b.str(r + 8), 'name_label': b.str(r + 12), 'help_label': b.str(r + 16),
            'flags': d[0:8], 'cost': b.u16(r + 22), 'type': TYPES[d[24]] if d[24] < len(TYPES) else d[24], 'series': d[25], 'tier': d[26],
            'use_kind': d[27], 'rank_exp': d[28], 'staff_exp': d[30], 'uses': d[31], 'mt': d[32], 'hit': d[33], 'crit': d[34],
            'min_range': d[35], 'max_range': d[36], 'value': d[40], 'bonus': dict(zip(STATS[1:], d[41:48])), 'effective': d[48],
            'raw': d,
        })
    return out


def item_name(it):
    return name_of(it['name_label'])


@functools.lru_cache(None)
def isid_bits():
    """{ISID name: bit}: the item flags by name, from GameData's ISID_ labels (each record: the name, its bit, the next). An item's
    flags are the 64-bit little-endian word at +0, as the program reads them (0x3b4dd4: the item's first two words against a mask)."""
    b = gamedata()
    return {n: b.u32(o + 4) for o, n in b.labels if n.startswith('ISID_')}


def has_isid(it, name):
    return bool(int.from_bytes(it['flags'], 'little') >> isid_bits()[name] & 1)


def random_pool(limit=False):
    """[(item, weight)]: what a script's random item comes from, the pick uniform over the list the program builds.
    ev::ItemGetRandom (0x3b31dc): every item with +38 1 (listed twice) or 2, leaving out the ones only foes use (ISID_敵専用) and
    the ones that can't be traded wirelessly (ISID_通信譲渡禁止). ev::ItemGetRandomLimit (0x3b4d00): every item with +38 3, and
    the Bolt Axe, leaving out the ones only foes use. With nothing in the list, either gives a Vulnerary."""
    out = []
    for it in items():
        if has_isid(it, 'ISID_敵専用'):
            continue
        cls = it['raw'][38]
        if limit:
            if cls == 3 or it['iid'] == 'IID_ボルトアクス':
                out.append((it, 1))
        elif cls in (1, 2) and not has_isid(it, 'ISID_通信譲渡禁止'):
            out.append((it, 2 if cls == 1 else 1))
    return out


@functools.lru_cache(None)
def classes():
    b = gamedata()
    out = []
    for r in table('JobData', CLASS_SIZE):
        d = b.d[0x20 + r:0x20 + r + CLASS_SIZE]
        out.append({
            'jid': b.str(r + 8), 'name': name_of(b.str(r + 16)), 'female': bool(d[0] & 1), 'promoted': bool(d[0] & 8),
            'move_type': d[80], 'mov': d[81], 'pairup': dict(zip(STATS, d[64:72])), 'cat': d[90], 'cat2': d[91], 'weapons': d[84:90], 'raw': d,
        })
    return out


@functools.lru_cache(None)
def class_by_jid():
    return {c['jid']: c for c in classes()}


def chapters():
    """GameData's chapter list: id (the files' key: 'P002', '001', 'X005'), heading, title, location, the chapter it opens after,
    the shop's five items and a travelling merchant's ten (item indexes; RARE stands for one of the rare items)."""
    b = gamedata()
    recs = table('ChapterData', CHAPTER_SIZE)
    out = []
    for i, r in enumerate(recs):
        cid = b.str(r)
        key = cid[4:]
        d = b.d[0x20 + r:0x20 + r + CHAPTER_SIZE]
        shop = [b.u16(r + 32 + 2 * k) for k in range(5)]
        merchant = [b.u16(r + 42 + 2 * k) for k in range(10)]
        after = d[20]
        out.append({
            'index': i, 'key': key, 'heading': name_of(f'MCID_{key}_T'), 'title': name_of(f'MCID_{key}'),
            'location': name_of(f'MCID_T_{key}'), 'after': None if after == 0xFF else b.str(recs[after])[4:],
            'parent': b.str(r + 16), 'shop': [x for x in shop if x], 'merchant': [x for x in merchant if x],
            # +64: 1 a paralogue, 2 a SpotPass paralogue, 3 the Outrealm Gate (DLC).
            'type': b.u16(r + 64),
        })
    return out


@functools.lru_cache(None)
def terrains():
    """TerrainData: name, its stats (Def, Avoid, healing %), its movement column, and what it becomes when changed (a village
    once visited, a chest once opened, a door once unlocked)."""
    b = gamedata()
    cat0 = b.at['TerrainCategoryData']
    out = []
    for r in table('TerrainData', TERRAIN_SIZE):
        cat = (b.u32(r + 8) - cat0) // 4
        out.append({
            'tid': b.str(r), 'name': name_of(b.str(r + 4)), 'cat': cat, 'def': b.s8(cat0 + cat * 4), 'avo': b.s8(cat0 + cat * 4 + 1),
            'heal': b.u8(cat0 + cat * 4 + 2), 'becomes': b.u8(r + 12), 'becomes2': b.u8(r + 13), 'flags': b.u8(r + 16),
        })
    return out


@functools.lru_cache(None)
def move_costs():
    """TerrainCostData: one row per movement type (a class's +80), one cost per terrain category; 255 = can't enter."""
    b = gamedata()
    o = b.at['TerrainCostData']
    rows = []
    count = (b.at['BelongData'] - o - 4) // 20
    for m in range(count):
        rows.append([b.u8(o + 4 + m * 20 + c) for c in range(18)])
    return rows


def grid(key, base=ROMFS):
    """A map's terrain grid (data/terrain/<key>.bin): width, height and rows of terrain ids, top row first, border included."""
    b = Bin(decompress(open(os.path.join(base, 'data', 'terrain', key + '.bin.lz'), 'rb').read()))
    w, h = b.u32(0), b.u32(4)
    return w, h, [[b.u8(8 + y * 32 + x) for x in range(w)] for y in range(h)]


def persons(key, base=ROMFS):
    """The chapter's own characters (data/person/<key>.bin): PID -> class, name label and level."""
    path = os.path.join(base, 'data', 'person', key + '.bin.lz')
    if not os.path.exists(path):
        return {}
    b = Bin(decompress(open(path, 'rb').read()))
    out = {}
    for o, name in b.labels:
        # +0: the person's SID flags, in GameData's SID_ order: 0x01 female, 0x02 the main character, 0x04 the player's avatar,
        # 0x08 promoted, 0x10 a leader, 0x20 a defeat condition (the chapter is lost if they fall)... +12 the portrait (FID_), which
        # generic soldiers don't have.
        out[name] = {'jid': b.str(o + 16), 'name_label': b.str(o + 20), 'level': b.u8(o + 69), 'flags': b.u32(o),
                     'fid': b.str(o + 12) if (o + 12) in b.ptrs else None, 'raw': b.d[0x20 + o:0x20 + o + PERSON_SIZE]}
    return out


@functools.lru_cache(None)
def main_persons():
    """The playable and recurring characters (data/person/000.bin's list is the chapter-independent one)."""
    out = {}
    for f in sorted(os.listdir(os.path.join(ROMFS, 'data', 'person'))):
        if f[0].isdigit() and f.startswith('00') and len(f.split('.')[0]) == 3:
            out.update(persons(f.split('.')[0]))
    return out


def dispos(key, base=ROMFS):
    """A chapter's placement file: [(group name, [unit...])]. Coordinates are as stored (0 at the top-left, the border included)."""
    path = os.path.join(base, 'data', 'dispos', key + '.bin.lz')
    b = Bin(decompress(open(path, 'rb').read()))
    groups = []
    i = 0
    while (i * 12) in b.ptrs:
        name, off, cnt = b.str(i * 12), b.u32(i * 12 + 4), b.u32(i * 12 + 8)
        units = []
        for u in range(cnt):
            o = off + u * UNIT_SIZE
            flags = b.u16(o + 16)
            items = []
            for k in range(5):
                p = o + 28 + k * 8
                if p in b.ptrs:
                    # +4 bit 0: dropped on defeat; +5..+7 the item's level on Normal, Hard and Lunatic (0: not carried there), which
                    # can step a foe's weapon up its series (the loader, 0x27cd00).
                    items.append({'iid': b.str(p), 'drop': bool(b.u8(p + 4) & 1), 'levels': list(b.d[0x20 + p + 5:0x20 + p + 8]),
                                  'raw': b.d[0x20 + p + 4:0x20 + p + 8]})
            units.append({
                'pid': b.str(o), 'flags': flags, 'difficulties': [d for bit, d in DIFFS.items() if flags & bit],
                'boss': bool(flags & 0x800), 'team': b.u8(o + 20), 'start': (b.u8(o + 22), b.u8(o + 23)), 'end': (b.u8(o + 24), b.u8(o + 25)),
                # +68 four AI slots (action, mind, attack, move), each [name, parameters]: data/AIData.bin defines each name, its
                # parameters the placement's comma-separated fields ('pos(5,17),0,pos(20,21)'; -4 the first, -5 the second...).
                'items': items, 'ai': [b.str(o + 68 + 8 * k) for k in range(4)],
                'ai_params': [b.str(o + 72 + 8 * k) if (o + 72 + 8 * k) in b.ptrs else None for k in range(4)],
                'raw': b.d[0x20 + o:0x20 + o + UNIT_SIZE],
                # +4 a class and +0x15 a level that replace the person's (0x2679bc passes them to the unit's setup, 0x2dd940).
                'jid': b.str(o + 4) if (o + 4) in b.ptrs else None, 'level': b.u8(o + 21),
            })
        groups.append((name, units))
        i += 1
    return groups


@functools.lru_cache(None)
def rare_items():
    import struct
    code = open(os.path.join(ROMFS, 'code.bin'), 'rb').read()
    out = []
    for k in range(RARE_COUNT):
        ptr = struct.unpack_from('<I', code, RARE_TABLE - 0x100000 + 4 * k)[0] - 0x100000
        out.append(code[ptr:code.index(b'\0', ptr)].decode('shift_jis'))
    return out


@functools.lru_cache(None)
def iid_index():
    return {it['iid']: it for it in items()}
