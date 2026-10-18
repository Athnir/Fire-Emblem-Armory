"""Read Fire Emblem Fates terrain files (GameData/Terrain/*.bin.lz): terrain types and the tile grid."""
import struct
import sys
from fates_lz import decompress


def cstr(d, off):
    end = d.index(b'\0', off)
    return d[off:end].decode('shift_jis', 'replace')


def read(path):
    d = decompress(open(path, 'rb').read())
    base = 0x20
    count = struct.unpack_from('<I', d, base + 4)[0]
    field = cstr(d, base + struct.unpack_from('<I', d, base + 8)[0])
    grid_off = base + struct.unpack_from('<I', d, base + 12)[0]
    types = []
    for i in range(count):
        e = base + 0x10 + i * 0x28
        vals = struct.unpack_from('<10I', d, e)
        types.append({'tid': cstr(d, base + vals[0]), 'raw': vals})
    w, h, x1, y1, x2, y2 = struct.unpack_from('<6I', d, grid_off)
    stride = 32
    cells = d[grid_off + 24:]
    rows = [list(cells[r * stride:r * stride + w]) for r in range(h)]
    return {'field': field, 'types': types, 'w': w, 'h': h, 'rect': (x1, y1, x2, y2), 'rows': rows}


if __name__ == '__main__':
    for p in sys.argv[1:]:
        t = read(p)
        print(p.split('/')[-1], t['field'], t['w'], t['h'], t['rect'], len(t['types']))
