"""
Applies a BPS patch (the beat format the fan translations ship in) in memory, for cross-checking names against a translation.
The patched image is never written into the repo; the generators read data only from the clean ROM.

    from bps import apply
    patched = apply(clean_bytes, open('Lil-Nordion 1.01.bps', 'rb').read())
"""
import zlib


def _varint(data, i):
    value, shift = 0, 1
    while True:
        x = data[i]
        i += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, i
        shift <<= 7
        value += shift


def apply(source, patch):
    assert patch[:4] == b'BPS1', 'not a BPS patch'
    assert zlib.crc32(patch[:-4]) == int.from_bytes(patch[-4:], 'little'), 'patch checksum'
    assert zlib.crc32(source) == int.from_bytes(patch[-12:-8], 'little'), 'this patch is for a different ROM'
    i = 4
    source_size, i = _varint(patch, i)
    target_size, i = _varint(patch, i)
    meta, i = _varint(patch, i)
    i += meta
    target = bytearray(target_size)
    out = src_rel = tgt_rel = 0
    end = len(patch) - 12
    while i < end:
        data, i = _varint(patch, i)
        command, length = data & 3, (data >> 2) + 1
        if command == 0:  # source read
            target[out:out + length] = source[out:out + length]
            out += length
        elif command == 1:  # target read
            target[out:out + length] = patch[i:i + length]
            i += length
            out += length
        elif command == 2:  # source copy
            d, i = _varint(patch, i)
            src_rel += (-1 if d & 1 else 1) * (d >> 1)
            target[out:out + length] = source[src_rel:src_rel + length]
            src_rel += length
            out += length
        else:  # target copy (may overlap, byte by byte)
            d, i = _varint(patch, i)
            tgt_rel += (-1 if d & 1 else 1) * (d >> 1)
            for _ in range(length):
                target[out] = target[tgt_rel]
                out += 1
                tgt_rel += 1
    assert zlib.crc32(target) == int.from_bytes(patch[-8:-4], 'little'), 'result checksum'
    return bytes(target)
