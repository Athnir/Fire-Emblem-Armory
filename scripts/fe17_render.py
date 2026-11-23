"""
Fire Emblem Engage's battle maps as the game draws them, seen from straight above (the user's call, 2026-11-23: a model of the game's
own look, checked against the maps photographed in the emulator, for the maps that can't be photographed).

A field's scene (scripts/fe17_art.py's Scene: the scene bundle and the bundles it draws on, data-raw/fe17/romfs/art) is rasterised
straight down over the map's terrain window, the highest surface winning, as the battle map's camera shows it:
- only the battle map's own objects: layer 9 is the battle scenes' (the close terrain, the high-detail props), 28 the characters'
  shadows, 31 a lighting sphere; a renderer that only casts shadows (ShadowModel), a sky dome high over the field (the Last Engage's
  stars) and the shadow catchers, fog and clouds fe17_art leaves out aren't drawn either;
- back faces culled as the materials cull them (_Cull 2: a temple's ceiling seen from above is its inside, which the camera never
  shows: Paralogue 6's ceiling had hidden its whole floor);
- roofs and ceilings more than ROOF_GAP over the field's floor (the median top surface) left out: the tilted battle camera looks
  under them (Chapter 3's tower roof);
- transparent surfaces (water) laid over what's under them.
Each surface is lit as the map's shader lights it: its albedo (the colour texture at about one texel a pixel, as the mips give it)
times its baked lightmap (the renderer's LightmapSettings, read as stored: linear, times 2) plus the main light (its colour, N.L, and
the baked shadowmask; the intensity to a power); the terrain's battle-map version (Mt_Terrain_Bmap, its baked colour) and water (its
base colour) by weights of their own. Then the map's fog (MapEnvironment's Bmap colour, linear from its start to its end) at the
battle camera's distance, and the map's own post-processing (its PPP_<map>_Bmap volume profile, not the battle scenes' _Combat one:
post exposure, white balance in LMS, contrast, lift/gamma/gain, saturation, the filmic piecewise tonemapper, as URP's code does them).

The shader itself isn't in the files read (its toon ramp isn't modelled), so the weights, the camera's distance and the light's power
(WEIGHTS) were fitted to the emulator's photos: each tile's colour round the cursor in every shot of 64 fields (19,410 tiles), the
model's error 22 per channel against 17 for the photos' own median per code (units, the interface and the tilted view's walls in the
shots); per code, 16 against the unlit art's 46.5 (the old renders). Lava isn't lit as the game lights it (its glow): drawn dim.

    python scripts/fe17_render.py FIELD X1,Z1,X2,Z2 OUT.png [PX]     a field over a terrain window (tiles), PX pixels a tile (24)
"""
import colorsys
import math
import os
import sys
import time

import numba as nb
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fe17_art  # noqa: E402

TILE = 5.0
EXCLUDE_LAYERS = (9, 28, 31)
ROOF_GAP = 25.0
SKY = 300.0
SKIP = fe17_art.SKIP_MATERIAL + ('Star',)
# Fitted to the emulator's photos (see above): lightmap, main light, unlit (no lightmap), Bmap terrain's albedo, its main light, its
# lightmap, water's base colour; the camera's distance for the fog; the light's intensity power.
WEIGHTS = dict(lightmap=0.4287, light=1.1549, unlit=0.0, bmap=0.1488, bmap_light=0.8528, bmap_lightmap=0.3667, water=0.3857,
               distance=123.52, power=1.0615)
VOLUME = ('ColorAdjustments', 'WhiteBalance', 'LiftGammaGain', 'Tonemapping', 'ShadowsMidtonesHighlights', 'ChannelMixer',
          'SplitToning')


def srgb2lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


@nb.njit(cache=False)
def _raster(px, pz, py, tris, W, H, depth, triid, bb0, bb1, base, cap):
    for t in range(tris.shape[0]):
        a, b, c = tris[t, 0], tris[t, 1], tris[t, 2]
        x0, z0, x1, z1, x2, z2 = px[a], pz[a], px[b], pz[b], px[c], pz[c]
        minx = max(int(np.floor(min(x0, min(x1, x2)))), 0)
        maxx = min(int(np.ceil(max(x0, max(x1, x2)))), W - 1)
        minz = max(int(np.floor(min(z0, min(z1, z2)))), 0)
        maxz = min(int(np.ceil(max(z0, max(z1, z2)))), H - 1)
        if minx > maxx or minz > maxz:
            continue
        den = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
        if abs(den) < 1e-12:
            continue
        for zz in range(minz, maxz + 1):
            gz = zz + 0.5
            for xx in range(minx, maxx + 1):
                gx = xx + 0.5
                l0 = ((z1 - z2) * (gx - x2) + (x2 - x1) * (gz - z2)) / den
                l1 = ((z2 - z0) * (gx - x2) + (x0 - x2) * (gz - z2)) / den
                l2 = 1.0 - l0 - l1
                if l0 < -1e-6 or l1 < -1e-6 or l2 < -1e-6:
                    continue
                d = l0 * py[a] + l1 * py[b] + l2 * py[c]
                if d > depth[zz, xx] and d <= cap:
                    depth[zz, xx] = d
                    triid[zz, xx] = base + t
                    bb0[zz, xx] = l0
                    bb1[zz, xx] = l1


class _Buffer:
    def __init__(self, W, H):
        self.depth = np.full((H, W), -1e9, np.float32)
        self.tri = np.full((H, W), -1, np.int64)
        self.b0 = np.zeros((H, W), np.float32)
        self.b1 = np.zeros((H, W), np.float32)
        self.part = []
        self.n = 0


class Field:
    """A field's surfaces over a window, rasterised; `shade()` lights and grades them."""

    def __init__(self, field, window, px=24, scene=None, colour=True, cap=None):
        self.sc = scene or fe17_art.Scene(field)
        x1, z1, x2, z2 = window
        self.window, self.px = window, px
        if cap is None:
            first = Field(field, window, max(4, px // 4), self.sc, colour=False, cap=np.inf)
            dd = first.opaque.depth[first.opaque.depth > -1e8]
            cap = float(np.median(dd)) + ROOF_GAP if len(dd) else np.inf
        self.cap = cap
        ppu = px / TILE
        self.W, self.H = W, H = int(round((x2 - x1) * px)), int(round((z2 - z1) * px))
        self.opaque, self.water = _Buffer(W, H), _Buffer(W, H)
        self.parts = []
        self._images = {}
        self.lightmaps = self._lightmaps() if colour else []
        for r, go, mat, P, N, UV, UV1, T, batched in self._renderers():
            props = mat.m_SavedProperties
            floats = dict(props.m_Floats)
            colours = {k: v for k, v in props.m_Colors}
            if N is not None and floats.get('_Cull', 2.0) == 2.0:
                T = T[N[T[:, 0], 1] + N[T[:, 1], 1] + N[T[:, 2], 1] > 1e-3]
            if not len(T):
                continue
            bc = colours.get('_BaseColor') or colours.get('_Color')
            part = dict(mat=mat.m_Name, P=P, N=N, UV=UV, UV1=UV1, T=T, lmi=r.m_LightmapIndex if r.m_LightmapIndex < 65534 else -1,
                        st=np.array([r.m_LightmapTilingOffset.x, r.m_LightmapTilingOffset.y, r.m_LightmapTilingOffset.z,
                                     r.m_LightmapTilingOffset.w]),
                        base=np.array([bc.r, bc.g, bc.b, bc.a], np.float32) if bc is not None else np.ones(4, np.float32),
                        bmap='Terrain_Bmap' in mat.m_Name, tex=None)
            if colour:
                part['tex'], part['scale'], part['off'] = self._texture(dict(props.m_TexEnvs), P, UV, T, ppu)
            buf = self.water if floats.get('_Surface', 0.0) == 1.0 else self.opaque
            _raster(((P[:, 0] - x1 * TILE) * ppu).astype(np.float64), ((P[:, 2] - z1 * TILE) * ppu).astype(np.float64),
                    P[:, 1].astype(np.float64), T.astype(np.int64), W, H, buf.depth, buf.tri, buf.b0, buf.b1, buf.n, self.cap)
            part['tbase'] = buf.n
            buf.part.append(np.full(len(T), len(self.parts), np.int32))
            buf.n += len(T)
            self.parts.append(part)
        for buf in (self.opaque, self.water):
            buf.part = np.concatenate(buf.part) if buf.part else np.zeros(0, np.int32)

    def _texture(self, envs, P, UV, T, ppu):
        """The colour texture at about one texel a pixel here (box-averaged from the full image, as its mips are), linear RGBA."""
        Tu = np.unique(T)
        ext_px = max(np.ptp(P[Tu, 0]), np.ptp(P[Tu, 2])) * ppu
        for key in fe17_art.COLOUR_KEYS:
            e = envs.get(key)
            if e is None or not e.m_Texture.path_id:
                continue
            scale = np.array([e.m_Scale.x, e.m_Scale.y])
            ext_uv = max(np.ptp(UV[Tu, 0]) * abs(scale[0]), np.ptp(UV[Tu, 1]) * abs(scale[1])) if UV is not None else 1.0
            want = int(2 ** np.clip(np.ceil(np.log2(max(ext_px / max(ext_uv, 1e-3), 1))), 4, 11))
            k = (id(e.m_Texture.assetsfile), e.m_Texture.file_id, e.m_Texture.path_id)
            if k not in self._images:
                try:
                    a = np.asarray(e.m_Texture.read().image.convert('RGBA'), np.float32)[::-1] / 255   # v up
                    self._images[k] = (np.dstack([srgb2lin(a[..., :3]), a[..., 3:]]), {})
                except Exception:  # noqa: BLE001
                    self._images[k] = None
            if self._images[k] is None:
                continue
            full, mips = self._images[k]
            if want not in mips:
                h, w = full.shape[:2]
                f = max(1, max(h, w) // want)
                mips[want] = full[:h // f * f, :w // f * f].reshape(h // f, f, w // f, f, 4).mean((1, 3)) if f > 1 else full
            return mips[want], scale, np.array([e.m_Offset.x, e.m_Offset.y])
        return None, None, None

    def _lightmaps(self):
        out = []
        for obj in self.sc.env.objects:
            if obj.type.name == 'LightmapSettings' and obj.assets_file in self.sc.files:
                for lm in obj.read().m_Lightmaps:
                    def get(p):
                        try:
                            return np.asarray(p.read().image.convert('RGBA'), np.float32)[::-1] / 255
                        except Exception:  # noqa: BLE001
                            return None
                    out.append((get(lm.m_Lightmap), get(lm.m_ShadowMask)))
        return out

    def _renderers(self):
        from UnityPy.helpers.MeshHelper import MeshHandler
        sc = self.sc
        for obj in sc.env.objects:
            if obj.type.name != 'MeshRenderer' or obj.assets_file not in sc.files:
                continue
            r = obj.read()
            if not r.m_Enabled:
                continue
            go = r.m_GameObject.read()
            if not go.m_IsActive or go.m_Layer in EXCLUDE_LAYERS:
                continue
            if getattr(r, 'm_CastShadows', 1) == 3 or go.m_Name.startswith('ShadowModel'):
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
            except Exception:  # noqa: BLE001
                continue
            nv = h.m_VertexCount

            def arr(x, k):
                if not x:
                    return None
                a = np.array(x, np.float32)
                return (a.reshape(nv, -1) if a.ndim == 1 else a)[:, :k]
            V, N, UV, UV1 = arr(h.m_Vertices, 3), arr(h.m_Normals, 3), arr(h.m_UV0, 2), arr(h.m_UV1, 2)
            if UV1 is None:
                UV1 = UV   # a mesh with no second UV set is lightmapped by its first
            sb = r.m_StaticBatchInfo
            batched = bool(sb.subMeshCount)
            sel, M = (range(sb.firstSubMesh, sb.firstSubMesh + sb.subMeshCount), np.eye(4)) if batched else (range(len(subs)), sc.world(tr))
            P = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
            if P[:, 1].min() > SKY:
                continue
            Nw = None
            if N is not None:
                Nw = N @ np.linalg.inv(M[:3, :3])
                Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-9)
            for k, si in enumerate(sel):
                if si >= len(subs) or not subs[si] or k >= len(r.m_Materials) or not r.m_Materials[k].path_id:
                    continue
                try:
                    mat = r.m_Materials[k].read()
                except Exception:  # noqa: BLE001
                    continue
                if any(s in mat.m_Name for s in SKIP):
                    continue
                basev = getattr(mesh.m_SubMeshes[si], 'baseVertex', 0) or 0
                yield r, go, mat, P, Nw, UV, UV1, np.array(subs[si], np.int64).reshape(-1, 3) + basev, batched

    def inputs(self):
        """Per pixel: albedo (linear), lightmap (linear; NaN where none), shadowmask, normal, Bmap terrain, water's colour, drawn."""
        H, W = self.H, self.W
        n = H * W
        alb, lm, nrm = np.zeros((n, 3), np.float32), np.full((n, 3), np.nan, np.float32), np.zeros((n, 3), np.float32)
        sm, bmap = np.ones(n, np.float32), np.zeros(n, bool)
        nrm[:, 1] = 1
        buf = self.opaque
        tri = buf.tri.reshape(-1)
        idx = np.flatnonzero(tri >= 0)
        pidx = buf.part[tri[idx]]
        b0, b1 = buf.b0.reshape(-1)[idx], buf.b1.reshape(-1)[idx]
        for pi in np.unique(pidx):
            p = self.parts[pi]
            s = pidx == pi
            ii = idx[s]
            T = p['T'][tri[ii] - p['tbase']]
            w0, w1 = b0[s, None], b1[s, None]
            w2 = 1 - w0 - w1

            def interp(A):
                return w0 * A[T[:, 0]] + w1 * A[T[:, 1]] + w2 * A[T[:, 2]]
            col = np.tile(srgb2lin(p['base'][:3]), (len(ii), 1))
            if p['tex'] is not None and p['UV'] is not None:
                uv = interp(p['UV']) * p['scale'] + p['off']
                th, tw = p['tex'].shape[:2]
                col = p['tex'][np.floor(uv[:, 1] * th).astype(np.int64) % th, np.floor(uv[:, 0] * tw).astype(np.int64) % tw, :3] * col
            alb[ii] = col
            bmap[ii] = p['bmap']
            if p['N'] is not None:
                nn = interp(p['N'])
                nrm[ii] = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
            if 0 <= p['lmi'] < len(self.lightmaps) and p['UV1'] is not None and self.lightmaps[p['lmi']][0] is not None:
                L, S = self.lightmaps[p['lmi']]
                uv1 = interp(p['UV1']) * p['st'][:2] + p['st'][2:]
                lh, lw = L.shape[:2]
                xs, ys = np.clip(uv1[:, 0] * lw - 0.5, 0, lw - 1), np.clip(uv1[:, 1] * lh - 0.5, 0, lh - 1)
                x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
                x1, y1 = np.minimum(x0 + 1, lw - 1), np.minimum(y0 + 1, lh - 1)
                fx, fy = (xs - x0)[:, None], (ys - y0)[:, None]

                def bil(A):
                    return A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x1] * fx * (1 - fy) + A[y1, x0] * (1 - fx) * fy + A[y1, x1] * fx * fy
                lm[ii] = bil(L)[:, :3] * 2.0
                if S is not None:
                    sm[ii] = bil(S)[:, 0]
        # water over the opaque surface: its base colour
        wet = np.zeros(n, bool)
        water = np.zeros((n, 3), np.float32)
        wt = self.water.tri.reshape(-1)
        wi = np.flatnonzero((wt >= 0) & (self.water.depth.reshape(-1) > buf.depth.reshape(-1)))
        if len(wi):
            wp = self.water.part[wt[wi]]
            for pi in np.unique(wp):
                water[wi[wp == pi]] = srgb2lin(self.parts[pi]['base'][:3])
            wet[wi] = True
        drawn = tri >= 0
        shape = (H, W)
        return dict(alb=alb.reshape(shape + (3,)), lm=lm.reshape(shape + (3,)), sm=sm.reshape(shape), nrm=nrm.reshape(shape + (3,)),
                    bmap=bmap.reshape(shape), wet=wet.reshape(shape), water=water.reshape(shape + (3,)), drawn=drawn.reshape(shape))


def settings(sc):
    """The battle map's own settings: its volume profile (PPP_<map>_Bmap, the PostProcess_Bmap volume's), its main light, its fog."""
    out = {'volume': {}, 'light': None, 'fog': None, 'profile': None}
    byid, profiles = {}, []
    for obj in sc.env.objects:
        if obj.assets_file not in sc.files:
            continue
        byid[(id(obj.assets_file), obj.path_id)] = obj
        if obj.type.name == 'MonoBehaviour':
            try:
                mb = obj.read()
                script = mb.m_Script.read().m_ClassName if mb.m_Script.path_id else '?'
            except Exception:  # noqa: BLE001
                continue
            if script == 'VolumeProfile':
                profiles.append(obj)
            elif script == 'MapEnvironment':
                b = obj.read_typetree().get('Bmap')
                if b:
                    c = b['color']
                    out['fog'] = (srgb2lin(np.array([c['r'], c['g'], c['b']])), b['start'], b['end'])
        elif obj.type.name == 'Light':
            light = obj.read()
            if light.m_Type != 1 or not light.m_Enabled:
                continue
            go = light.m_GameObject.read()
            if go.m_Name != 'MainLight' and out['light'] is not None:
                continue
            tr = next(c.component for c in go.m_Component if c.component.type.name == 'Transform')
            M = sc.world(tr)
            out['light'] = dict(colour=srgb2lin(np.array([light.m_Color.r, light.m_Color.g, light.m_Color.b])),
                                intensity=light.m_Intensity, toward=-M[:3, 2] / np.linalg.norm(M[:3, 2]))
            if go.m_Name == 'MainLight':
                out['light']['main'] = True
    chosen = None
    for obj in profiles:
        d = obj.read_typetree()
        if d.get('m_Name', '').endswith('_Bmap') or chosen is None:
            chosen = (obj, d)
    if chosen:
        pobj, d = chosen
        out['profile'] = d.get('m_Name')
        for c in d.get('components', []):
            o = byid.get((id(pobj.assets_file), c['m_PathID']))
            if o is None:
                continue
            try:
                script = o.read().m_Script.read().m_ClassName
            except Exception:  # noqa: BLE001
                continue
            if script in VOLUME:
                t = o.read_typetree()
                if t.get('active', 1):
                    out['volume'][script] = t
    return out


# --- the post-processing, as URP's colour grading does it ---

LIN_2_LMS = np.array([[3.90405e-1, 5.49941e-1, 8.92632e-3], [7.08416e-2, 9.63172e-1, 1.35775e-3], [2.31082e-2, 1.28021e-1, 9.36245e-1]])
LMS_2_LIN = np.array([[2.85847e+0, -1.62879e+0, -2.48910e-2], [-2.10182e-1, 1.15820e+0, 3.24281e-4], [-4.18120e-2, -1.18169e-1, 1.06867e+0]])


def _balance(temperature, tint):
    """ColorUtils.ColorBalanceToLMSCoeffs."""
    t1, t2 = temperature / 65.0, tint / 65.0
    x = 0.31271 - t1 * (0.1 if t1 < 0 else 0.05)
    y = (2.87 * x - 3 * x * x - 0.27509507) + t2 * 0.05
    X, Z = x / y, (1 - x - y) / y
    lms = np.array([0.7328 * X + 0.4296 - 0.1624 * Z, -0.7036 * X + 1.6975 + 0.0061 * Z, 0.0030 * X + 0.0136 + 0.9834 * Z])
    return np.array([0.949237, 1.03542, 1.08728]) / lms


def _lgg(lift, gamma, gain):
    """ColorUtils.PrepareLiftGammaGain."""
    def lum(v):
        return v[0] * 0.2126 + v[1] * 0.7152 + v[2] * 0.0722
    L, M, G = np.array(lift) * 0.2, np.array(gamma) * 0.8, np.array(gain) * 0.8
    return (L[:3] - lum(L[:3]) + L[3], 1.0 / np.maximum(M[:3] - lum(M[:3]) + M[3] + 1, 1e-3), G[:3] - lum(G[:3]) + G[3] + 1)


class _Hable:
    """The filmic piecewise power curve (John Hable's, as Unity's custom tonemapper builds it from its six parameters)."""

    def __init__(self, toe_strength, toe_length, shoulder_strength, shoulder_length, shoulder_angle, gamma):
        toe_length = min(max(toe_length, 0), 1) ** 2.2
        toe_strength = min(max(toe_strength, 0), 1)
        shoulder_angle = min(max(shoulder_angle, 0), 1)
        shoulder_strength = min(max(shoulder_strength, 1e-5), 1 - 1e-5)
        shoulder_length = max(0.0, shoulder_length)
        g = max(1e-5, gamma)
        x0 = toe_length * 0.5
        y0 = (1 - toe_strength) * x0
        remaining = 1 - y0
        x1 = x0 + (1 - shoulder_strength) * remaining
        y1 = y0 + (1 - shoulder_strength) * remaining
        W = x0 + remaining + 2 ** shoulder_length - 1
        over_x, over_y = (W * 2) * shoulder_angle * shoulder_length / W, 0.5 * shoulder_angle * shoulder_length
        self.inv = 1 / W
        nx0, nx1 = x0 / W, x1 / W
        m = (y1 - y0) / (nx1 - nx0) if nx1 != nx0 else 1.0
        b = y0 - nx0 * m
        self.seg = [None, dict(ox=-(b / m), oy=0.0, sx=1.0, sy=1.0, lnA=g * math.log(m), B=g), None]
        toe_m, shoulder_m = g * m * (m * nx0 + b) ** (g - 1), g * m * (m * nx1 + b) ** (g - 1)
        py0, py1 = max(1e-5, y0 ** g), max(1e-5, y1 ** g)
        over_y = (1 + over_y) ** g - 1
        self.x0, self.x1 = nx0, nx1
        B = toe_m * nx0 / py0
        self.seg[0] = dict(ox=0.0, oy=0.0, sx=1.0, sy=1.0, lnA=math.log(py0) - B * math.log(nx0), B=B)
        sx0, sy0 = (1 + over_x) - nx1, (1 + over_y) - py1
        B = shoulder_m * sx0 / sy0
        self.seg[2] = dict(ox=1 + over_x, oy=1 + over_y, sx=-1.0, sy=-1.0, lnA=math.log(sy0) - B * math.log(sx0), B=B)
        scale = self._eval(self.seg[2], np.array([1.0]))[0]
        for s in self.seg:
            s['oy'] /= scale
            s['sy'] /= scale

    @staticmethod
    def _eval(s, x):
        x0 = (x - s['ox']) * s['sx']
        return np.where(x0 > 0, np.exp(s['lnA'] + s['B'] * np.log(np.maximum(x0, 1e-12))), 0.0) * s['sy'] + s['oy']

    def __call__(self, x):
        nx = x * self.inv
        out = np.empty_like(nx)
        a, c = nx < self.x0, nx >= self.x1
        b = ~a & ~c
        for mask, s in ((a, self.seg[0]), (b, self.seg[1]), (c, self.seg[2])):
            out[mask] = self._eval(s, nx[mask])
        return out


def grading(volume):
    """f(linear rgb, any shape (..., 3)) -> display rgb 0-1 (sRGB), from a volume profile's components."""
    def value(comp, name, default):
        p = (volume.get(comp) or {}).get(name)
        return p['m_Value'] if p and p.get('m_OverrideState') else default
    exposure = 2 ** value('ColorAdjustments', 'postExposure', 0.0)
    contrast = value('ColorAdjustments', 'contrast', 0.0) / 100 + 1
    saturation = value('ColorAdjustments', 'saturation', 0.0) / 100 + 1
    cf = value('ColorAdjustments', 'colorFilter', {'r': 1, 'g': 1, 'b': 1})
    cf = np.array([cf['r'], cf['g'], cf['b']])
    temp, tint = value('WhiteBalance', 'temperature', 0.0), value('WhiteBalance', 'tint', 0.0)
    bal = _balance(temp, tint) if (temp or tint) else np.ones(3)

    def v4(name, d):
        v = value('LiftGammaGain', name, None)
        return [v['x'], v['y'], v['z'], v['w']] if v else d
    lift, inv_gamma, gain = _lgg(v4('lift', [1, 1, 1, 0]), v4('gamma', [1, 1, 1, 0]), v4('gain', [1, 1, 1, 0]))
    curve = None
    if value('Tonemapping', 'mode', 0) == 3:
        curve = _Hable(*(value('Tonemapping', k, d) for k, d in (('toeStrength', 0), ('toeLength', 0.5), ('shoulderStrength', 0),
                                                                  ('shoulderLength', 0.5), ('shoulderAngle', 0), ('gamma', 1))))
    cut, a, b, c, d, e, f = 0.011361, 5.555556, 0.047996, 0.244161, 0.386036, 5.301883, 0.092819

    def grade(rgb):
        x = rgb.reshape(-1, 3).astype(np.float64) * exposure
        x = ((x @ LIN_2_LMS.T) * bal) @ LMS_2_LIN.T
        if contrast != 1:
            logc = np.where(x > cut, c * np.log10(np.maximum(a * x + b, 1e-10)) + d, e * x + f)
            logc = (logc - 0.4135884) * contrast + 0.4135884
            x = np.where(logc > e * cut + f, (np.power(10.0, (logc - d) / c) - b) / a, (logc - f) / e)
        x = np.maximum(x * cf, 0) * gain + lift
        x = np.sign(x) * np.power(np.abs(x), inv_gamma)
        if saturation != 1:
            luma = x @ np.array([0.2126729, 0.7151522, 0.0721750])
            x = luma[:, None] + saturation * (x - luma[:, None])
        if curve is not None:
            x = curve(np.maximum(x, 0))
        x = np.clip(x, 0, 1)
        return lin2srgb(x).reshape(rgb.shape).astype(np.float32)
    return grade


def shade(d, s, w=WEIGHTS):
    """The lit, fogged and graded picture (H, W, 3; 0-1, sRGB; row 0 the south) from Field.inputs() and settings()."""
    lm = np.nan_to_num(d['lm'])
    has_lm = np.isfinite(d['lm'][..., :1])
    alb, bm, dry = d['alb'], d['bmap'][..., None], ~d['wet'][..., None]
    light = s['light']
    if light is not None:
        ndl = np.clip((d['nrm'] * light['toward']).sum(-1), 0, None)
        direct = alb * (ndl * d['sm'])[..., None] * light['colour'] * light['intensity'] ** w['power']
    else:
        direct = np.zeros_like(alb)
    x = (~bm * dry * (w['lightmap'] * alb * lm + w['light'] * direct + w['unlit'] * alb * ~has_lm)
         + bm * dry * (w['bmap'] * alb + w['bmap_light'] * direct + w['bmap_lightmap'] * alb * lm)
         + w['water'] * d['water'] * d['wet'][..., None])
    if s['fog'] is not None:
        fc, start, end = s['fog']
        f = np.clip((w['distance'] - start) / max(end - start, 1e-3), 0, 1)
        x = x * (1 - f) + fc * f
    img = grading(s['volume'])(x)
    img[~d['drawn'] & ~d['wet']] = 0
    return img


def render(field, window, px=24):
    """The field over the window as the battle map shows it, north up: a PIL image, `px` pixels a tile."""
    from PIL import Image
    fl = Field(field, window, px)
    img = shade(fl.inputs(), settings(fl.sc))
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)[::-1])


if __name__ == '__main__':
    t0 = time.time()
    field, window, out = sys.argv[1], tuple(int(v) for v in sys.argv[2].split(',')), sys.argv[3]
    im = render(field, window, int(sys.argv[4]) if len(sys.argv) > 4 else 24)
    im.save(out)
    print(out, im.size, f'{time.time() - t0:.0f}s')
