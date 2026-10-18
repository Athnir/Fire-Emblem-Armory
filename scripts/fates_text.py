"""Read Fire Emblem Fates message archives (m/@E/*.bin.lz): label -> English text."""
import struct
from fates_lz import decompress


def read(path):
    d = decompress(open(path, 'rb').read())
    _, data_size, ptr_count, label_count = struct.unpack_from('<4I', d, 0)
    base = 0x20
    tab = base + data_size + ptr_count * 4
    names = tab + label_count * 8
    out = {}
    for i in range(label_count):
        text_off, name_off = struct.unpack_from('<II', d, tab + i * 8)
        n0 = names + name_off
        label = d[n0:d.index(b'\0', n0)].decode('shift_jis', 'replace')
        t0 = base + text_off
        e = t0
        while d[e:e + 2] != b'\0\0':
            e += 2
        out[label] = d[t0:e].decode('utf-16-le')
    return out


if __name__ == '__main__':
    import sys
    t = read(sys.argv[1])
    for k in list(t)[: int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
        print(k, '=', t[k][:80])
