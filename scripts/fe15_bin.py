"""Read Echoes: Shadows of Valentia's data files.

The container is the 3DS Fire Emblem binary format (`scripts/fe13_bin.py`), but Echoes' tables describe themselves: each file opens
with a `MOD_<table>` block (a field count, then per field: name, type name, minimum, maximum, step) and its records follow
`DAT_<table>`, one label per record. Types: str and ptr (a 4-byte pointer), s8 / u8, s16 / u16, u32, f32; records are packed in
field order. `table(path)` returns the records as dicts by field name (a repeated name gets #2, #3: Item.bin's three sets of stat
fields), each with '_off' (its data offset) and '_id' (its label).
"""
import os
import struct

from fe13_bin import Bin
from fates_lz import decompress

ROMFS = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe15', 'romfs')
SIZE = {'str': 4, 'ptr': 4, 's8': 1, 'u8': 1, 's16': 2, 'u16': 2, 'u32': 4, 's32': 4, 'f32': 4}


def load(path):
    raw = open(os.path.join(ROMFS, path), 'rb').read()
    return Bin(decompress(raw) if path.endswith('.lz') else raw)


def schema(b, mod):
    """[(field name, type)] of the MOD_ block at `mod`, repeated names numbered."""
    out, seen = [], {}
    for i in range(b.u32(mod)):
        o = mod + 4 + 20 * i
        name, typ = b.str(o), b.str(o + 4)
        seen[name] = seen.get(name, 0) + 1
        out.append((name if seen[name] == 1 else '%s#%d' % (name, seen[name]), typ))
    return out


def read_field(b, o, typ):
    if typ == 'str':
        return b.str(o)
    if typ == 'ptr':
        return b.u32(o) if o in b.ptrs else None
    if typ == 'f32':
        return struct.unpack_from('<f', b.d, 0x20 + o)[0]
    return {'s8': b.s8, 'u8': b.u8, 's16': b.s16, 'u16': b.u16, 'u32': b.u32,
            's32': lambda x: struct.unpack_from('<i', b.d, 0x20 + x)[0]}[typ](o)


def read_record(b, o, fields):
    rec = {'_off': o}
    for name, typ in fields:
        rec[name] = read_field(b, o, typ)
        o += SIZE[typ]
    return rec


class Table:
    """One MOD_/DAT_ table of a file: `rows` in order, `by_id` by their first field (IID_..., JID_...). Usually one label marks each
    record; with `every`, all records between DAT_ and the next table are read (the event files' command rows, where a label marks only
    each sequence's first)."""

    def __init__(self, b, name=None, every=False):
        self.b = b
        mods = [(o, n[4:]) for o, n in b.labels if n.startswith('MOD_')]
        mod, self.name = mods[0] if name is None else next(m for m in mods if m[1] == name)
        self.fields = schema(b, mod)
        size = sum(SIZE[t] for _, t in self.fields)
        dat = b.at['DAT_' + self.name]
        end = min([o for o, n in b.labels if n.startswith('MOD_') and o > dat] + [b.size])
        labels = {o: n for o, n in b.labels if dat <= o < end and not n.startswith(('DAT_', 'MOD_'))}
        offsets = range(dat, end - size + 1, size) if every else sorted(labels)
        self.rows = []
        for o in offsets:
            label = labels.get(o)
            if (o - dat) % size:
                continue
            r = read_record(b, o, self.fields)
            r['_id'] = label
            self.rows.append(r)
        key = self.fields[0][0]
        self.by_id = {r[key]: r for r in self.rows if r.get(key)}


def table(path, name=None, every=False):
    return Table(load(path), name, every)

