"""
Applies a VCDIFF patch (RFC 3284, the format xdelta3 writes: New Mystery of the Emblem's translation ships as one) in memory, for
reading a translation's names. The patched image is never written anywhere; the generators read data only from the clean ROM.

    from vcdiff import apply
    patched, bad = apply(clean_bytes, open('FE12_v3_01.delta', 'rb').read())

`bad` lists the target windows whose Adler-32 (xdelta3 stores one per window) doesn't match: the parts of the output a different
source image spoiled. Only the default code table is supported, with no secondary compression.
"""
import zlib

NOOP, ADD, RUN, COPY = range(4)
S_NEAR, S_SAME = 4, 3


def _table():
    """The default code table (RFC 3284, 5.6): 256 pairs of (instruction, size, mode)."""
    t = [((RUN, 0, 0), (NOOP, 0, 0))]
    t += [((ADD, s, 0), (NOOP, 0, 0)) for s in range(18)]
    for m in range(9):
        t += [((COPY, s, m), (NOOP, 0, 0)) for s in [0] + list(range(4, 19))]
    for m in range(6):
        t += [((ADD, a, 0), (COPY, c, m)) for a in range(1, 5) for c in range(4, 7)]
    for m in range(6, 9):
        t += [((ADD, a, 0), (COPY, 4, m)) for a in range(1, 5)]
    t += [((COPY, 4, m), (ADD, 1, 0)) for m in range(9)]
    assert len(t) == 256
    return t


TABLE = _table()


def _varint(data, i):
    value = 0
    while True:
        x = data[i]
        i += 1
        value = value << 7 | (x & 0x7F)
        if not x & 0x80:
            return value, i


def apply(source, patch):
    assert patch[:4] == b'\xd6\xc3\xc4\x00', 'not a VCDIFF patch'
    flags, i = patch[4], 5
    assert not flags & 0x03, 'secondary compression or a custom code table'
    if flags & 0x04:   # an application header (xdelta3's: the file names)
        n, i = _varint(patch, i)
        i += n
    out = bytearray()
    bad = []
    while i < len(patch):
        win = patch[i]
        i += 1
        seg = None
        if win & 0x03:
            size, i = _varint(patch, i)
            pos, i = _varint(patch, i)
            seg = (source if win & 0x01 else out)[pos:pos + size]
        seg = bytes(seg or b'')
        _, i = _varint(patch, i)             # the delta encoding's length
        target_len, i = _varint(patch, i)
        assert patch[i] == 0, 'compressed sections'
        i += 1
        data_len, i = _varint(patch, i)
        inst_len, i = _varint(patch, i)
        addr_len, i = _varint(patch, i)
        checksum = None
        if win & 0x04:
            checksum = int.from_bytes(patch[i:i + 4], 'big')
            i += 4
        data, inst = patch[i:i + data_len], patch[i + data_len:i + data_len + inst_len]
        addr = patch[i + data_len + inst_len:i + data_len + inst_len + addr_len]
        i += data_len + inst_len + addr_len
        target = bytearray()
        near, same, slot = [0] * S_NEAR, [0] * (S_SAME * 256), 0
        di = ii = ai = 0
        while ii < len(inst):
            code = inst[ii]
            ii += 1
            for kind, size, mode in TABLE[code]:
                if kind == NOOP:
                    continue
                if size == 0:
                    size, ii = _varint(inst, ii)
                if kind == ADD:
                    target += data[di:di + size]
                    di += size
                elif kind == RUN:
                    target += data[di:di + 1] * size
                    di += 1
                else:
                    here = len(seg) + len(target)
                    if mode == 0:
                        a, ai = _varint(addr, ai)
                    elif mode == 1:
                        a, ai = _varint(addr, ai)
                        a = here - a
                    elif mode < 2 + S_NEAR:
                        a, ai = _varint(addr, ai)
                        a += near[mode - 2]
                    else:
                        a = same[(mode - 2 - S_NEAR) * 256 + addr[ai]]
                        ai += 1
                    near[slot] = a
                    slot = (slot + 1) % S_NEAR
                    same[a % (S_SAME * 256)] = a
                    if a + size <= len(seg):
                        target += seg[a:a + size]
                    else:
                        for k in range(size):
                            p = a + k
                            target.append(seg[p] if p < len(seg) else target[p - len(seg)])
        assert len(target) == target_len, (len(target), target_len)
        if checksum is not None and zlib.adler32(bytes(target)) != checksum:
            bad.append((len(out), target_len))
        out += target
    return bytes(out), bad
