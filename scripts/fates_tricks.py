"""Read map gimmicks ("tricks": Dragon Veins and the like) from Fates' <chapter>_Terrain.cmb scripts."""
import struct


def tricks(path):
    """[(x, y_from_top, w, h, kind)] in the game's own tile coordinates (border included)."""
    d = open(path, 'rb').read()
    o, offs = 0x3C, []
    while True:
        v = struct.unpack_from('<I', d, o)[0]
        if v == 0:
            break
        offs.append(v)
        o += 4
    out = []
    for f in offs:
        ints = struct.unpack_from('<11I', d, f)
        out.append(ints[6:11])
    return out
