"""
Fire Emblem Fates' battle maps seen from above, drawn from the user's own cartridge and DLC dumps (scripts/fates_art_extract.py copies
the art to data-raw/fates/romfs/art), for each map's own colours (the user's call, as the other games' are).

Each terrain file names its field (fates_terrain.read()['field']): field/<name>.bch.lz holds its models (Echoes' BCH format,
scripts/fe15_bch.py), <name>_t.bch.lz its textures and <name>.bin.lz places them and the shared Obj_* / Mcl_* files (0x2c-byte
placement records; scripts/fates_art_scene.py). Only each model's battle-map version (`_map`) is drawn: ceilings and roofs exist only
in the combat scenes' (`_low`), so they never cover the map. Map pieces (Mcl_*) hang each mesh on a bone, placed by the skeleton
(scripts/fates_art_bch.py), and a mesh the model hides at the start is left out (the placeholders on chests and doors). Materials run
through the texture combiner as Echoes' do (scripts/fates_art_material.py: the game's real-time shadow map passed through, lighting
white, specular black). A battle tile is 50 world units: tile (x, y) of the terrain file covers world x in [50x, 50x + 50) and z in
[50y, 50y + 50); the app's grid is the file's without its one-tile border.

Left out: clouds, fog and light shafts, Revelation's darkness overlay (its ground is painted dark anyway), Hidden Truths 1's
kingfisher, additive glows but the water's wave layers, Revelation 24's lids over closed rooms (so the floors show). Water is a dark
tint of a land reflection map plus a sky reflection not drawn, so it often comes out olive or teal; animations aren't played.
"""
import re

from fe15_raster import Canvas, composite_blend, composite_opaque, fragments
import fates_art_scene as S

TILE = 50.0  # world units per battle tile
PX = 32      # pixels per tile drawn

SKIP = re.compile(r'^(clouds?|Kumo|Obj_kiri|Mcl_Mist|light\d*|light_ground|directionalLight\d*|Mcl_darkness.*|kawasemi)$', re.I)
LIDS = {'Btl_CastleInvisible_Dungeon': re.compile(r'^Mcl_kabe_[A-D]$')}


def wave_layer(me):
    """A water surface's additive wave layer (rivers, lakes, the sea), kept though other additive layers aren't."""
    t = (me['textures'][0] or '').lower()
    return t.startswith('wave') and 'grass' not in t


def render(field, window, px=PX, pack=None, lids=False):
    """PIL image of the field seen from above over the terrain-file window (x1, z1, x2, z2) in tiles; `pack` a DLC map's .app."""
    x1, z1, x2, z2 = window
    S.set_pack(pack)
    lid = LIDS.get(field) if not lids else None
    cv = Canvas(x1 * TILE, z1 * TILE, x2 * TILE, z2 * TILE, px / TILE)
    meshes = S.scene_meshes(field, lambda name, model: bool(SKIP.match(model) or (lid and lid.match(model))))
    meshes = [m for m in meshes if not m['mat'].untextured and
              not (m['mat'].blend and m['mat'].blend[1] == 1 and not wave_layer(m))]
    opaque = [m for m in meshes if m['mat'].blend is None]
    blended = sorted((m for m in meshes if m['mat'].blend is not None), key=lambda m: m['positions'][:, 1].mean())
    for me in opaque + blended:
        mat = me['mat']
        fr = fragments(cv, me['positions'], me['triangles'], mat.cull, [me['uv0'], me['uv1'], me['uv2'], me['color']])
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
    return cv.image()
