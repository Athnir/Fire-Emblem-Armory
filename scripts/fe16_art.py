"""
Three Houses' battle maps seen from above, drawn from the user's own game (scripts/fe16_art_extract.py copies the files to
data-raw/fe16/romfs/art), for each map's own colours (the user's call, as the other games' are).

A battle's stage s (the battle map's number) is drawn from two things:
- its terrain, archive file 2391 + s: seven parts (u32 count, (offset, size) pairs), part 1 a KFTK0820 block whose header (+0x14)
  points at three things: a G1T of six layer-weight maps, a G1T of one texture, the terrain's colour baked from above (1024 x 1024
  over the heightfield), and a _MHK0100 heightmap (+0x10 u16 cells across and down, 128; f32 the cell, 500 units; f32 the lowest and
  highest heights; then (cells + 1)^2 u32 heights, each a fraction of that range). The heightfield covers world x and z from 0 to
  64000, its colour map row 0 at z 0;
- its models (scripts/fe16_g1m.py): file 882 + s, or for twelve stages (the program's bitmask 0x14a8e2141 at 0x59db20) the nine files
  from 985 + 9s, each group's G1Ms textured from file 1377 + 8s + the group. Props modelled at the origin (trees, rocks: placed by
  data not found) are left out: a model whose middle lies within PROP of the origin.
A tile is 1000 units: the battle grid's tile (column c, row r from the top) covers world x from 500 x1 + 1000c and z from
500 y1 + 1000r, (x1, y1) the grid file's bounds in half tiles (the colour map's forests fall on the grid's forest tiles). The
highest surface wins, up to ABOVE over the battle ground; no lighting.
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fe16_g1m as G  # noqa: E402
from fe15_raster import Canvas, composite_opaque, fragments  # noqa: E402

ART = os.path.join(HERE, '..', 'data-raw', 'fe16', 'romfs', 'art')
TILE = 1000.0
TERRAIN_FIRST, MODELS_FIRST, RUNS_FIRST, TEXTURES_FIRST = 2391, 882, 985, 1377
RUN_STAGES = {s for s in range(33) if 0x14a8e2141 >> s & 1}
PROP = 3000.0
TEX_SIZE = 256
# Only surfaces this far above the battle ground's middle height are drawn: the battle camera, tilted, never looks straight down, so
# the stages set backdrops over the field far above it (Garreg Mach's cathedral over the mock battle's northern rows, Zanado's
# canopies), while walls, cliffs and roofs on the field stand under two tiles high.
ABOVE = 3000.0


def art(n):
    return open(os.path.join(ART, f'{n}.bin'), 'rb').read()


def parts(data):
    n = struct.unpack_from('<I', data, 0)[0]
    v = struct.unpack_from(f'<{2 * n}I', data, 4)
    return [data[v[2 * k]:v[2 * k] + v[2 * k + 1]] for k in range(n)]


def terrain(stage):
    """(colour map as an (h, w, 3) float array, row 0 at z 0, its world size; heights (n + 1, n + 1), cell size), or None."""
    path = os.path.join(ART, f'{TERRAIN_FIRST + stage}.bin')
    if not os.path.exists(path):
        return None
    k = parts(art(TERRAIN_FIRST + stage))[1]
    if k[:8] != b'KFTK0820':
        return None
    a, b, c = struct.unpack_from('<3I', k, 0x14)
    colour = G.g1t(k[b:c], max_size=1024)[0]
    m = k[c:]
    assert m[:8] == b'_MHK0100'
    cw, ch, cell, lo, hi = struct.unpack_from('<2H3f', m, 0x10)
    t = np.frombuffer(m[0x20:0x20 + (cw + 1) * (ch + 1) * 4], '<u4').astype(np.float64) / 0xFFFFFFFF
    heights = (lo + t * (hi - lo)).reshape(ch + 1, cw + 1)
    return np.asarray(colour.convert('RGB'), np.float32) / 255, cw * cell, heights, cell


def groups(stage):
    if stage in RUN_STAGES:
        return [art(RUNS_FIRST + 9 * stage + k) for k in range(8)]
    return G.container(parts(art(MODELS_FIRST + stage))[0])[:8]


def models(stage):
    """(group, G1M, its textures) for each model the stage places in the world."""
    for k, g in enumerate(groups(stage)):
        if len(g) <= 16 or g[:4] == b'RIVE':
            continue
        path = os.path.join(ART, f'{TEXTURES_FIRST + 8 * stage + k}.bin')
        texs = None
        for slot in G.container(g):
            for blob in G.mdlk(slot):
                m = G.G1M(blob)
                if not m.meshes:
                    continue
                P = np.concatenate([me['positions'] for me in m.meshes])
                middle = (P.min(0) + P.max(0)) / 2
                if np.hypot(middle[0], middle[2]) < PROP:
                    continue
                if texs is None:
                    texs = {i: np.asarray(im.convert('RGBA'), np.float32) / 255
                            for i, im in (G.g1t(art(TEXTURES_FIRST + 8 * stage + k), max_size=TEX_SIZE).items()
                                          if os.path.exists(path) else [])}
                yield k, m, texs


def _sample(img, uv):
    h, w = img.shape[:2]
    return img[np.floor(uv[:, 1] * h).astype(np.int64) % h, np.floor(uv[:, 0] * w).astype(np.int64) % w]


def render(stage, window, px=24):
    """PIL image of the stage over the world window (x0, z0, x1, z1), row 0 at z0 (the battle grid's top row), `px` a tile."""
    x0, z0, x1, z1 = window
    cv = Canvas(x0, z0, x1, z1, px / TILE)
    ter = terrain(stage)
    top = np.inf
    if ter is not None:
        colour, size, H, cell = ter
        top = float(np.median(H[int(z0 // cell):int(z1 // cell) + 1, int(x0 // cell):int(x1 // cell) + 1])) + ABOVE
        n = H.shape[0]
        # The heightfield's cells over the window (and one round them), two triangles each, its colour map over its whole extent.
        i0, i1 = max(int(x0 // cell) - 1, 0), min(int(x1 // cell) + 2, n - 1)
        j0, j1 = max(int(z0 // cell) - 1, 0), min(int(z1 // cell) + 2, n - 1)
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        P = np.c_[ii.ravel() * cell, H[jj.ravel(), ii.ravel()], jj.ravel() * cell].astype(np.float64)
        UV = np.c_[ii.ravel() * cell / size, jj.ravel() * cell / size]
        W = i1 - i0 + 1
        q = (np.arange(j1 - j0)[:, None] * W + np.arange(i1 - i0)[None, :]).ravel()
        T = np.r_[np.c_[q, q + 1, q + W], np.c_[q + 1, q + W + 1, q + W]]
        fr = fragments(cv, P, T, 0, [UV])
        if fr is not None:
            idx, d, (uv,) = fr
            composite_opaque(cv, idx, d, _sample(colour, uv))
    for k, m, texs in models(stage):
        for me in m.meshes:
            mat = m.materials[me['material']] if me['material'] < len(m.materials) else []
            tex = texs.get(next((t for t, layer, kind in mat if kind == 1 and layer == 0), None))
            if tex is None or me['uv'] is None:
                continue
            fr = fragments(cv, me['positions'], me['triangles'], 0, [me['uv']])
            if fr is None:
                continue
            idx, d, (uv,) = fr
            rgba = _sample(tex, uv)
            keep = (rgba[:, 3] > 0.3) & (d <= top)
            if keep.any():
                composite_opaque(cv, idx[keep], d[keep], rgba[keep, :3])
    return cv.image()


def battle_window(map_no):
    """The world window (x0, z0, x1, z1) of a battle map's grid (archive file 365 + map: its bounds in half tiles)."""
    d = open(os.path.join(HERE, '..', 'data-raw', 'fe16', 'romfs', f'{365 + map_no}.bin'), 'rb').read()
    bx1, by1, bx2, by2 = d[4:8]
    return bx1 * TILE / 2, by1 * TILE / 2, bx2 * TILE / 2, by2 * TILE / 2
