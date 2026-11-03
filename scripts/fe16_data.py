"""Read Fire Emblem: Three Houses' data files, as fe16_extract.py copies them into data-raw/fe16/romfs (archive file n as `<n>.bin`).

Field names follow the Three Houses Research Team's 010 Editor templates (github.com/three-houses-research-team/
010-binary-templates), each checked against the files here; data-raw/fe16/README.md lists the layouts and what was checked.

Most data files are one container: u32 section count, then (u32 offset, u32 size) per section. A table section starts with a
0x40-byte header (u32 magic 0x16121900, u32 record count, u32 record size) and its records follow. The text (file 0) is the same
container, one section per language (1 = English, as the US release has it), each holding four Koei 'XL' string tables.
"""
import os
import struct

ROMFS = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe16', 'romfs')
DLC = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe16', 'dlc')
TABLE_MAGIC = 0x16121900
ENGLISH = 1

# Archive file numbers (DATA0), as the update's INFO0 names the ones it replaces.
MSGDATA, FIXED_DATA, STAGEDATA, CLASSDATA, PERSONDATA, ACTDATA, SKILL, SCENARIO, SHOPDATA = 0, 6, 10, 11, 12, 13, 15, 22, 30
SC_FIRST = 83            # SC00_00.bai; each scenario has a .bai (its units) and a .bsi (its script), in turn
GRID_FIRST = 365         # map 0's grid; map m's is GRID_FIRST + m

# Text table 1's ranges (each name list is followed by its descriptions).
PERSON_NAME = 1157       # person p's name
CLASS_NAME = 3453        # class c's name
WEAPON_NAME = 3756       # weapon w's name; its description is WEAPON_NAME + 500 + w

_cache = {}


def archive_file(n):
    if n not in _cache:
        _cache[n] = open(os.path.join(ROMFS, f'{n}.bin'), 'rb').read()
    return _cache[n]


def sections(data):
    count = struct.unpack_from('<I', data, 0)[0]
    return [data[o:o + s] for o, s in (struct.unpack_from('<II', data, 4 + 8 * k) for k in range(count))]


def records(section):
    """A table section's records."""
    magic, count, size = struct.unpack_from('<III', section, 0)
    assert magic == TABLE_MAGIC, hex(magic)
    return [section[0x40 + i * size:0x40 + (i + 1) * size] for i in range(count)]


def table(n, k):
    return records(sections(archive_file(n))[k])


def xl_strings(t):
    """A Koei XL string table: 'XL', u16 version, u16 size (its low 16 bits), u16 columns, u16 count, u16 entry size, u32 header
    size, u32 -; then a u32 offset per string (from the header's end), each string UTF-8 and NUL-terminated."""
    assert t[:2] == b'XL', t[:4]
    count, _esize, header = struct.unpack_from('<HHI', t, 8)
    out = []
    for k in range(count):
        o = header + struct.unpack_from('<I', t, header + 4 * k)[0]
        out.append(t[o:t.index(b'\0', o)].decode('utf-8'))
    return out


def texts(lang=ENGLISH):
    """The language's three string tables (the fourth XL table, its first, is an index)."""
    key = ('texts', lang)
    if key not in _cache:
        _cache[key] = [xl_strings(x) for x in sections(sections(archive_file(MSGDATA))[lang])[1:]]
    return _cache[key]


def text(n, table_no=1, lang=ENGLISH):
    return texts(lang)[table_no][n]


def person_name(p):
    return text(PERSON_NAME + p)


def class_name(c):
    return text(CLASS_NAME + c)


def weapon_name(w):
    return text(WEAPON_NAME + w)


def weapon_description(w):
    return text(WEAPON_NAME + 500 + w)


# fixed_data.bin (file 6), section 0: the weapons, 24-byte records.
WEAPON_TYPES = ['Sword', 'Lance', 'Axe', 'Bow', 'Gauntlets']


def weapons():
    """Each weapon record: +2/+3 its two effects' values, +4 an extra effect, +5 type (0 sword .. 4 gauntlets), +6 rank, +7 max
    range, +8 model, +9 crest (86 none), +10 min range, +11 uses, +12 status it inflicts, +13 icon, +14 effective against (bits:
    infantry, armour, cavalry, flier, dragon, monster), +15 flags (0x40 broken, 0x80 crest stone), +16 Mt, +17 Hit, +18 Crit,
    +19 Wt, +20/+21 two effects (skill properties), +22 flags (0x01 magic, 0x02 against Res, 0x04 leaves 1 HP, 0x08 not
    fliers, 0x10 no follow-up, 0x20 strikes twice, 0x40/0x80 relic)."""
    out = []
    for w, r in enumerate(table(FIXED_DATA, 0)):
        out.append({
            'id': w, 'name': weapon_name(w),
            'value1': r[2], 'value2': r[3], 'extra': r[4], 'type': r[5], 'rank': r[6], 'max_range': r[7], 'model': r[8],
            'crest': r[9], 'min_range': r[10], 'uses': r[11], 'status': r[12], 'icon': r[13], 'effective': r[14],
            'flags1': r[15], 'mt': r[16], 'hit': r[17], 'crit': r[18], 'wt': r[19], 'effect1': r[20], 'effect2': r[21],
            'flags': r[22], 'raw': r,
        })
    return out
