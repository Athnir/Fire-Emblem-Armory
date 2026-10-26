"""
Applies a UPS patch (the format the FE6 Localization patch ships in) in memory: nothing patched is written to disk.

UPS: 'UPS1', varint source size, varint target size, then (varint skip, bytes XORed into the source until a 0 byte) records,
then three CRC32s (source, target, patch). Each is checked.
"""
import zlib


def _varint(d, i):
    value, shift = 0, 1
    while True:
        x = d[i]
        i += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, i
        shift <<= 7
        value += shift


def apply(source, patch):
    assert patch[:4] == b'UPS1', 'not a UPS patch'
    src_crc, out_crc, patch_crc = (int.from_bytes(patch[-12 + 4 * k:len(patch) - 8 + 4 * k], 'little') for k in range(3))
    assert zlib.crc32(patch[:-4]) == patch_crc, 'the patch file is damaged'
    assert zlib.crc32(source) == src_crc, 'this patch is for a different ROM'
    i = 4
    src_size, i = _varint(patch, i)
    out_size, i = _varint(patch, i)
    out = bytearray(source[:out_size].ljust(out_size, b'\0'))
    o = 0
    end = len(patch) - 12
    while i < end:
        skip, i = _varint(patch, i)
        o += skip
        while patch[i]:
            out[o] ^= patch[i]
            o += 1
            i += 1
        i += 1
        o += 1
    assert zlib.crc32(out) == out_crc, 'patching failed'
    return bytes(out)
