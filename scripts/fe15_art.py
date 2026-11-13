"""
Echoes: Shadows of Valentia's (FE15) battle maps seen from above, drawn from the cartridge's own 3D fields (the user's call: each map's
own colours, as the other games' are), aligned to the app's grids.

A battle is fought on a field (Data/Field.bin's フィールド名): field/<name>.bch.lz holds its models (each in LODs: <model>_map the battle
map's, then _low, _high) with textures there or in its _t / _ta / _tb companions, and field/<name>.bin.lz places them and the shared
field/obj_* models (trees, forts, crates) with scale, rotation and translation (scripts/fe15_scene.py). The BCH container, its PICA200
textures (every format, ETC1 and ETC1A4 too), meshes and materials are read by scripts/fe15_bch.py; a material's texture combiner
stages are run per fragment by scripts/fe15_shade.py (lighting taken as white, environment and projection maps as their texture's
mean colour: water and swamps are close, not exact) and scripts/fe15_raster.py rasterises the triangles top-down. Grass and flower
instances (plant/*.bin) aren't drawn.

A battle tile is 50 world units: terrain tile (x, y) of the map's terrain file covers world x in [50x, 50x + 50) and z in
[50y, 50y + 50), y up, so the app's grid (the file's window [x1, x2) x [y1, y2), top row first) is the world seen from above with x
to the right and z down.
"""
import numpy as np

from fe15_raster import Canvas, composite_blend, composite_opaque, fragments
from fe15_scene import scene_meshes

TILE = 50.0  # world units per battle tile
PX = 32      # pixels per tile drawn


def render(field, window, px=PX):
    """(height, width, px * px, 3): each tile's pixels of the field `field` seen from above over the terrain window (x1, y1, x2, y2).
    Opaque meshes first (the highest surface wins), then blended ones from the lowest up."""
    x1, y1, x2, y2 = window
    cv = Canvas(x1 * TILE, y1 * TILE, x2 * TILE, y2 * TILE, px / TILE)
    meshes = scene_meshes(field)
    opaque = [m for m in meshes if m['mat'].blend is None]
    blended = sorted((m for m in meshes if m['mat'].blend is not None), key=lambda m: m['positions'][:, 1].mean())
    for me in sorted(opaque, key=lambda m: not m.get('under')) + blended:
        mat = me['mat']
        P = me['positions']
        if me.get('under'):
            P = P - np.array([0, 5, 0])  # the low ground lies under the battle map's own
        fr = fragments(cv, P, me['triangles'], mat.cull, [me['uv0'], me['uv1'], me['uv2'], me['color']])
        if fr is None:
            continue
        idx, d, (uv0, uv1, uv2, col) = fr
        rgba = mat.shade((uv0, uv1, uv2), col, len(idx))
        keep = mat.alpha_pass(rgba[:, 3])
        idx, d, rgba = idx[keep], d[keep], rgba[keep]
        if not len(idx):
            continue
        if mat.blend is None:
            composite_opaque(cv, idx, d, rgba[:, :3])
        else:
            composite_blend(cv, idx, d, rgba, mat.blend, mat.depth_write)
    a = np.asarray(cv.image().convert('RGB'), np.float32)
    h, w = y2 - y1, x2 - x1
    return a[:h * px, :w * px].reshape(h, px, w, px, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, px * px, 3)
