"""Read Fire Emblem Fates unit placement files (GameData/Dispos/*.bin.lz)."""
import struct
from fates_lz import decompress

UNIT = 0x8C


def read(path, height):
    """height = the map's playable height (terrain h - 2), to convert to bottom-left (1, 1) coordinates."""
    d = decompress(open(path, 'rb').read())
    B = 0x20
    data_size = struct.unpack_from('<I', d, 4)[0]

    def s(p):
        if not p:
            return None
        o = B + p
        if o < B + data_size - 0x10 or o >= len(d):
            return None
        return d[o:d.index(b'\0', o)].decode('shift_jis', 'replace')

    factions = []
    fi = 0
    while True:
        np, off, cnt = struct.unpack_from('<III', d, B + fi * 12)
        name = s(np)
        if not name:
            break
        units = []
        for u in range(cnt):
            o = B + off + u * UNIT
            items = []
            for k in range(5):
                ip, iflags = struct.unpack_from('<II', d, o + 0x14 + k * 8)
                if s(ip):
                    items.append((s(ip), iflags))
            skills = [s(struct.unpack_from('<I', d, o + 0x3C + k * 4)[0]) for k in range(5)]
            x1, y1, x2, y2 = d[o + 10], d[o + 11], d[o + 12], d[o + 13]
            units.append({
                'pid': s(struct.unpack_from('<I', d, o)[0]),
                'team': d[o + 8], 'level': d[o + 9],
                'start': (x1, height + 1 - y1), 'arrive': (x2, height + 1 - y2),
                'flags': struct.unpack_from('<I', d, o + 0x10)[0],
                'items': items,
                'skills': [k for k in skills if k],
                'raw': d[o:o + UNIT],
            })
        factions.append({'name': name, 'units': units})
        fi += 1
    return factions
