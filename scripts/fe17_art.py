"""
Fire Emblem Engage's battle maps seen from above, drawn from the user's own game (scripts/fe17_art_extract.py copies each battle's
scene bundle and the bundles it draws on to data-raw/fe17/romfs/art), for each map's own colours (the user's call, as the other
games' are).

A battle's field is a Unity scene (fe_scenes_fld_<field>.bundle): its GameObjects' MeshRenderers, each with a MeshFilter's mesh and
its materials, placed by their Transforms (or, where Unity batched them, a combined mesh already in the world, its renderer naming the
submeshes it draws); meshes, materials and textures live in the scene or in fe_assets_map's bundles, by their CAB names. A tile is 5
world units: grid tile (x, z) (terrains/<name>.json, x and z from 0) covers world x in [5x, 5x + 5) and z in [5z, 5z + 5), y up.
Only what the battle map shows is drawn: the scene's own renderers, enabled on active GameObjects, a LODGroup's first level alone
but for the battle map's own versions (Bmap: the terrain's baked colour, which the zoomed-out map camera shows), no shadow catchers (Mt_CharaShadow), fog or clouds. Each surface takes its material's colour texture (_BakedAlbedoMap on the
terrain, else _BaseMap / _MainTex ...), or its _BaseColor where it has none (water); no lighting.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fe15_raster import Canvas, composite_opaque, fragments  # noqa: E402

ART = os.path.join(HERE, '..', 'data-raw', 'fe17', 'romfs', 'art')
DEPS = os.path.join(ART, 'deps.json')   # field -> the bundles its scene draws on (fe17_art_extract.py)
TILE = 5.0
COLOUR_KEYS = ('_BakedAlbedoMap', '_BaseMap', '_MainTex', '_AlbedoMap', '_BaseColorMap', '_AlbedoMap0', '_ColorMap')
SKIP_MATERIAL = ('CharaShadow', 'Fog', 'Cloud', 'Sky', 'Shadow')
TEX_SIZE = 256


def _quat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class Scene:
    def __init__(self, field):
        import UnityPy
        deps = json.load(open(DEPS, encoding='utf-8'))[field]
        self.scene = os.path.join(ART, f'fe_scenes_fld_{field}.bundle')
        self.env = UnityPy.load(self.scene, *[os.path.join(ART, d) for d in deps if os.path.exists(os.path.join(ART, d))])
        self.files = set()
        for key, f in self.env.files.items():
            if os.path.basename(key) == os.path.basename(self.scene):
                self.files |= {sf for sf in f.files.values() if hasattr(sf, 'objects')}
        self._world, self._tex = {}, {}

    def world(self, ptr):
        key = (id(ptr.assetsfile), ptr.path_id)
        if key not in self._world:
            t = ptr.read()
            m = np.eye(4)
            q, s, p = t.m_LocalRotation, t.m_LocalScale, t.m_LocalPosition
            m[:3, :3] = _quat((q.x, q.y, q.z, q.w)) * np.array([s.x, s.y, s.z])
            m[:3, 3] = (p.x, p.y, p.z)
            if t.m_Father.path_id:
                m = self.world(t.m_Father) @ m
            self._world[key] = m
        return self._world[key]

    def texture(self, ptr):
        key = (id(ptr.assetsfile), ptr.file_id, ptr.path_id)
        if key not in self._tex:
            try:
                im = ptr.read().image.convert('RGBA')
                im.thumbnail((TEX_SIZE, TEX_SIZE))
                self._tex[key] = np.asarray(im, np.float32)[::-1] / 255   # Unity's v runs up
            except Exception:
                self._tex[key] = None
        return self._tex[key]

    def surface(self, mat):
        """(texture or None, uv scale, uv offset, flat colour or None)."""
        props = mat.m_SavedProperties
        envs = dict(props.m_TexEnvs)
        for name in COLOUR_KEYS:
            env = envs.get(name)
            if env is not None and env.m_Texture.path_id:
                tex = self.texture(env.m_Texture)
                if tex is not None:
                    return tex, np.array([env.m_Scale.x, env.m_Scale.y]), np.array([env.m_Offset.x, env.m_Offset.y]), None
        colour = dict((k, v) for k, v in props.m_Colors).get('_BaseColor') or dict((k, v) for k, v in props.m_Colors).get('_Color')
        return None, None, None, (None if colour is None else np.array([colour.r, colour.g, colour.b], np.float32))

    def lod_hidden(self):
        """The renderers a LODGroup draws only at its later levels."""
        hidden, shown = set(), set()
        for obj in self.env.objects:
            if obj.type.name != 'LODGroup' or obj.assets_file not in self.files:
                continue
            for k, lod in enumerate(obj.read().m_LODs):
                for r in lod.renderers:
                    (shown if k == 0 else hidden).add(r.renderer.path_id)
        return hidden - shown

    @staticmethod
    def bmap(r):
        """Whether a renderer is the battle map's own version (Mt_Terrain_Bmap: the terrain's baked colour, Ted_Combat_Color, a later
        LOD level the zoomed-out map camera shows), drawn though its LODGroup lists it after the first level."""
        try:
            return any('Bmap' in m.read().m_Name for m in r.m_Materials if m.path_id)
        except Exception:
            return False

    def renderers(self):
        from UnityPy.helpers.MeshHelper import MeshHandler
        hidden = self.lod_hidden()
        for obj in self.env.objects:
            if obj.type.name != 'MeshRenderer' or obj.assets_file not in self.files:
                continue
            r = obj.read()
            if obj.path_id in hidden and not self.bmap(r):
                continue
            if not r.m_Enabled:
                continue
            go = r.m_GameObject.read()
            if not go.m_IsActive:
                continue
            comps = [c.component for c in go.m_Component]
            mf = next((c for c in comps if c.type.name == 'MeshFilter'), None)
            tr = next((c for c in comps if c.type.name == 'Transform'), None)
            try:
                mf = mf.read() if mf else None
                if mf is None or not mf.m_Mesh.path_id:
                    continue
                mesh = mf.m_Mesh.read()
                h = MeshHandler(mesh)
                h.process()
                subs = h.get_triangles()
            except Exception:
                continue
            V = np.array(h.m_Vertices, np.float32)
            V = (V.reshape(h.m_VertexCount, -1) if V.ndim == 1 else V)[:, :3]
            UV = np.array(h.m_UV0, np.float32) if h.m_UV0 else None
            if UV is not None:
                UV = (UV.reshape(h.m_VertexCount, -1) if UV.ndim == 1 else UV)[:, :2]
            sb = r.m_StaticBatchInfo
            if sb.subMeshCount:
                sel, M = range(sb.firstSubMesh, sb.firstSubMesh + sb.subMeshCount), np.eye(4)
            else:
                sel, M = range(len(subs)), self.world(tr)
            P = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
            for k, si in enumerate(sel):
                if si >= len(subs) or not subs[si] or k >= len(r.m_Materials) or not r.m_Materials[k].path_id:
                    continue
                try:
                    mat = r.m_Materials[k].read()
                except Exception:
                    continue
                if any(s in mat.m_Name for s in SKIP_MATERIAL):
                    continue
                base = getattr(mesh.m_SubMeshes[si], 'baseVertex', 0) or 0
                yield go.m_Name, mat, P, UV, np.array(subs[si], np.int64) + base


def render(field, window, px=24):
    """PIL image (north up) of the field over the grid window (x1, z1, x2, z2) in tiles, `px` pixels a tile."""
    from PIL import Image
    sc = Scene(field)
    x1, z1, x2, z2 = window
    cv = Canvas(x1 * TILE, z1 * TILE, x2 * TILE, z2 * TILE, px / TILE)
    for name, mat, P, UV, T in sc.renderers():
        tex, scale, off, colour = sc.surface(mat)
        fr = fragments(cv, P, T, 0, [UV])
        if fr is None:
            continue
        idx, d, (uv,) = fr
        if tex is not None and uv is not None:
            h, w = tex.shape[:2]
            uv = uv * scale + off
            rgba = tex[np.floor(uv[:, 1] * h).astype(np.int64) % h, np.floor(uv[:, 0] * w).astype(np.int64) % w]
            rgb, keep = rgba[:, :3], rgba[:, 3] > 0.3
        elif colour is not None:
            rgb, keep = np.tile(colour, (len(idx), 1)), np.ones(len(idx), bool)
        else:
            continue
        if keep.any():
            composite_opaque(cv, idx[keep], d[keep], rgb[keep])
    return cv.image().transpose(Image.FLIP_TOP_BOTTOM)
