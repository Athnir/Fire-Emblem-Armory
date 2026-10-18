"""Decompress Fire Emblem Fates `.lz` files (a 4-byte 0x13 header, then a standard LZ11 stream)."""
import sys


def lz11(data: bytes) -> bytes:
    assert data[0] == 0x11, f'not LZ11 (type {data[0]:#x})'
    size = int.from_bytes(data[1:4], 'little')
    pos = 4
    if size == 0:
        size = int.from_bytes(data[4:8], 'little')
        pos = 8
    out = bytearray()
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not flags >> bit & 1:
                out.append(data[pos])
                pos += 1
                continue
            b = data[pos]
            ind = b >> 4
            if ind == 0:
                length = (((b & 0xF) << 4) | (data[pos + 1] >> 4)) + 0x11
                disp = (((data[pos + 1] & 0xF) << 8) | data[pos + 2]) + 1
                pos += 3
            elif ind == 1:
                length = (((b & 0xF) << 12) | (data[pos + 1] << 4) | (data[pos + 2] >> 4)) + 0x111
                disp = (((data[pos + 2] & 0xF) << 8) | data[pos + 3]) + 1
                pos += 4
            else:
                length = ind + 1
                disp = (((b & 0xF) << 8) | data[pos + 1]) + 1
                pos += 2
            for _ in range(length):
                out.append(out[-disp])
    return bytes(out[:size])


def decompress(data: bytes) -> bytes:
    if data[0] == 0x13:
        return lz11(data[4:])
    return lz11(data)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        raw = decompress(open(path, 'rb').read())
        out = path[:-3] if path.endswith('.lz') else path + '.bin'
        open(out, 'wb').write(raw)
        print(out, len(raw))
