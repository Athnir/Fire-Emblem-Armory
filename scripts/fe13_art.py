"""
Fire Emblem Awakening's (FE13) battle maps seen from straight above, drawn from the user's own cartridge and DLC dumps, cropped to the
app's grids (src/data/fe13/fe13Maps.ts).

Where the art lives
-------------------
Each battle map is a 3D scene in a CGFX file (.bcres, LZ11 with the 0x13 header): `map/terrain/<key>.bcres.lz` on the cartridge
(romfs), or, for a DLC map, `map/terrain/E000.bcres.lz` inside its `E0xx_MAP.arc` (each DLC content's romfs). The program loads it
by the name the chapter's script gives TerrainLoad (`map/terrain/%s.bcres.lz`, beside `data/terrain/%s.bin.lz` and
`map/height/%s.bin`), so the Premonition (P001, TerrainLoad('023')) is drawn on Chapter 23's scene. A scene holds:

- the ground: one big mesh (model `grid_BMap<key>_geo`, sometimes split into geo1..geo9 or spread over several materials) whose
  colour texture `bmap<key>_geo` (1024 x 1024 ETC1) is the whole battlefield painted from above, one world unit per tile;
- props as models of their own, already in place (identity transforms): trees, forts, castles, houses, ships, bones, walls;
- overlays the program draws on top: the tile grid (`grid00`, a 32 x 32 texture repeated once per tile, in the ground's combiner as
  1 - grid, or a mesh of its own), clouds, a sky dome (`Bmap_wallpaper`), birds, effects (`eff`);
- one directional fragment light (CFLT) and material animations (constant colours, scrolling UVs).

World units: battle tile (x, y) of the terrain file (from the top left, border included) covers world x in [x, x + 1) and z in
[y, y + 1), y up; the app's grid (the file's tiles 1 .. w-2, 1 .. h-2) is the world seen from above with x to the right and z down.

How it's drawn
--------------
The container is read by scripts/fe13_cgfx.py. Textures are decoded with the repo's scripts/fe15_bch.py (every PICA200 format,
ETC1 / ETC1A4 too), triangles rasterised top-down with scripts/fe15_raster.py, and each material's six texture-combiner stages run
per fragment with the operand and combiner helpers of scripts/fe15_shade.py. CGFX specifics handled here: each stage's constant
colour is the material constant the stage names; texture unit i reads the UV set its coordinator names, through the coordinator's
3x4 matrix; the fragment light's primary colour is the light's ambient plus its diffuse times N.L (the specular colour is left
black: the LUTs aren't evaluated). Left out on purpose: the tile grid (grid00 is replaced by black, which is what 1 - grid needs to
leave the ground unchanged; grid-only meshes skipped), clouds and cloud shadows (a scrolling texture: its mean colour), the sky,
birds and effects. Material animations aren't played: the static colours are used.

scripts/fe13_ground.py renders every map with it and writes each one's colours and dirt for scripts/build-fe13-maps.py.
"""
import json
import os
import sys
from functools import lru_cache

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, '..')
sys.path.insert(0, HERE)

from ncch_romfs import RomFS, cia_contents, ncsd_partitions  # noqa: E402
from fe15_bch import decompress, decode_texture, pica_commands  # noqa: E402
from fe15_raster import Canvas, composite_opaque, fragments  # noqa: E402
from fe15_shade import _combine, _op_a, _op_rgb, _wrap, blend_factor  # noqa: E402
from fe13_bin import Bin  # noqa: E402
from fe13_cgfx import CGFX, cstr, f32s, i32, rel, u32  # noqa: E402

GAMES = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games')
CART = os.path.join(GAMES, '00040000000A0500_v00.trim.3ds')
DLC = os.path.join(GAMES, 'Fire_Emblem_-_Awakening_NA_DLC.cia')
CACHE = os.path.join(REPO, 'data-raw', 'fe13', 'romfs', 'art-cache')  # the scenes copied out of the dumps (git-ignored)
APP_MAPS = os.path.join(REPO, 'src', 'data', 'fe13', 'fe13Maps.ts')
PX = 32

# ---------------------------------------------------------------------------------------------------------------------------
# Files


def _cached(rel_path, fetch):
    path = os.path.join(CACHE, rel_path)
    if not os.path.exists(path):
        data = fetch()
        if data is None:
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
    return open(path, 'rb').read()


@lru_cache(maxsize=None)
def _cart_index():
    part = dict((i, o) for i, o, _ in ncsd_partitions(CART))[0]
    r = RomFS(CART, part)
    return r, {p: (o, n) for p, o, n in r.walk()}


def cart_file(path):
    """A file of the cartridge's romfs ('/map/terrain/001.bcres.lz'), raw."""
    def fetch():
        r, idx = _cart_index()
        if path not in idx:
            return None
        o, n = idx[path]
        return r.read(o, n)
    return _cached('cart' + path, fetch)


@lru_cache(maxsize=None)
def _dlc_arcs():
    """{'E001': (RomFS, offset, size)} of every DLC map archive."""
    out = {}
    for cid, idx, off, _ in cia_contents(DLC):
        try:
            r = RomFS(DLC, off)
        except AssertionError:
            continue
        for p, o, n in r.walk():
            if p.endswith('_MAP.arc'):
                out[os.path.basename(p)[:4]] = (r, o, n)
    return out


def dlc_file(key, name):
    """A file inside a DLC map's archive (E0xx_MAP.arc: the 3DS FE binary layout, each label a path pointing at [name, index,
    size, offset])."""
    def fetch():
        arcs = _dlc_arcs()
        if key not in arcs:
            return None
        r, o, n = arcs[key]
        b = Bin(r.read(o, n))
        for off, label in b.labels:
            if label == name:
                size, start = b.u32(off + 8), b.u32(off + 12)
                return b.d[0x20 + start:0x20 + start + size]
        return None
    return _cached(f'dlc/{key}/{name}', fetch)


def scene_file(art):
    """The CGFX bytes of a map's scene: 'E0xx' a DLC map's own, else the cartridge's map/terrain/<art>.bcres.lz."""
    raw = dlc_file(art, 'map/terrain/E000.bcres.lz') if art.startswith('E') else cart_file(f'/map/terrain/{art}.bcres.lz')
    return decompress(raw)


def script_terrain(key):
    """The terrain a chapter's script loads (TerrainLoad's string argument), or None for its own: the Premonition's '023'."""
    import fe13_events as E
    root = os.path.join(REPO, 'data-raw', 'fe13', 'romfs')
    path = os.path.join(root, 'dlc', key, 'scripts', 'E000.cmb') if key.startswith('E') else os.path.join(root, 'scripts', key + '.cmb')
    if not os.path.exists(path):
        return None
    t = E.Chapter(path).terrain_load()
    return t if isinstance(t, str) else None


# ---------------------------------------------------------------------------------------------------------------------------
# The app's maps


def key_of(map_id):
    """fe13-premonition P001, fe13-prologue P002, fe13-endgame 026, fe13-<n> chapter, fe13-par<n> X0nn, fe13-dlc<n> E0nn; a
    skirmish is its chapter's map."""
    base = map_id[:-len('-skirmish')] if map_id.endswith('-skirmish') else map_id
    s = base[len('fe13-'):]
    if s == 'premonition':
        return 'P001'
    if s == 'prologue':
        return 'P002'
    if s == 'endgame':
        return '026'
    if s.startswith('par'):
        return 'X%03d' % int(s[3:])
    if s.startswith('dlc'):
        return 'E%03d' % int(s[3:])
    return '%03d' % int(s)


def art_of(map_id):
    key = key_of(map_id)
    return script_terrain(key) or key


@lru_cache(maxsize=None)
def app_maps():
    out = {}
    for line in open(APP_MAPS, encoding='utf-8'):
        if line.startswith('  {'):
            m = json.loads(line.strip().rstrip(','))
            out[m['id']] = m
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# Materials


def _rgba(v):
    return np.array([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, v >> 24], np.float32) / 255


GRID = 'grid00'           # the tile grid: drawn as black so 1 - grid leaves the ground as it is
MEAN_OF = ('cloud', 'touei')  # scrolling cloud and projected shadow maps: their mean colour


class Material:
    """An MTOB as the PICA200 draws it seen from straight above (cgfx.py's notes give the layout)."""

    def __init__(self, c, mo, texture):
        d = c.d
        self.name = cstr(d, rel(d, mo + 0x0c))
        self.flags = u32(d, mo + 0x18)
        cols = [_rgba(u32(d, mo + 0xd4 + 4 * i)) for i in range(11)]
        self.emission, self.ambient, self.diffuse, self.spec0, self.spec1 = cols[:5]
        self.consts = cols[5:]
        rast, _ = pica_commands(d, mo + 0x110, 2)
        self.cull = rast.get(0x40, [0])[-1] & 3
        depth, _ = pica_commands(d, mo + 0x11c, 4)
        self.depth_write = bool(depth.get(0x107, [0x1000])[-1] >> 12 & 1)
        blend, _ = pica_commands(d, mo + 0x140, 6)
        mode = (blend.get(0x100, [0xe40100])[-1] >> 8) & 3
        bf = blend.get(0x101, [0x01010000])[-1]
        self.blend = None
        if mode == 1:
            s, t = (bf >> 16) & 0xf, (bf >> 20) & 0xf
            if not (s == 1 and t == 0):
                self.blend = (s, t)
        self.coords = []
        for i in range(3):
            o = mo + 0x16c + 88 * i
            m = np.array(f32s(d, o + 0x28, 12)).reshape(3, 4)
            self.coords.append({'src': max(i32(d, o), 0), 'mapping': u32(d, o + 4), 'matrix': m})
        self.names, self.images, self.wrap = [], [], []
        for i in range(3):
            t = rel(d, mo + 0x274 + 4 * i)
            name, wrap = None, (2, 2)
            if t:
                name = cstr(d, rel(d, rel(d, t + 8) + 0x18))
                regs, _ = pica_commands(d, t + 0x10, max(u32(d, t + 0x48) // 4, 2))
                for reg in (0x83, 0x93, 0x9b):
                    if reg in regs:
                        v = regs[reg][-1]
                        wrap = ((v >> 12) & 7, (v >> 8) & 7)
            self.names.append(name)
            self.wrap.append(wrap)
            self.images.append(texture(name) if name else None)
        self.means = [None if im is None else im.reshape(-1, 4).mean(0).astype(np.float32) / 255 for im in self.images]
        fs = rel(d, mo + 0x288)
        self.stages = []
        for k in range(6):
            ci = u32(d, fs + 0x2c + 0x1c * k)
            regs, _ = pica_commands(d, fs + 0x30 + 0x1c * k, 6)
            base = min(regs)
            src, opnd, comb, _, scale = (regs.get(base + j, [0])[-1] for j in range(5))
            self.stages.append({
                'src_rgb': [(src >> (4 * j)) & 0xf for j in range(3)], 'src_a': [(src >> (16 + 4 * j)) & 0xf for j in range(3)],
                'op_rgb': [(opnd >> (4 * j)) & 0xf for j in range(3)], 'op_a': [(opnd >> (12 + 4 * j)) & 0x7 for j in range(3)],
                'comb_rgb': comb & 0xf, 'comb_a': (comb >> 16) & 0xf, 'const': self.consts[ci] if ci < 6 else _rgba(0xff000000),
                'scale_rgb': float(1 << (scale & 3)), 'scale_a': float(1 << ((scale >> 16) & 3))})
        tail, _ = pica_commands(d, fs + 0xd4, 8)
        upd = tail.get(0xe0, [0])[-1]
        self.buf_rgb = [(upd >> (8 + i)) & 1 for i in range(4)]
        self.buf_a = [(upd >> (12 + i)) & 1 for i in range(4)]
        self.buf_color = _rgba(tail.get(0xfd, [0xff000000])[-1])
        at = tail.get(0x104, [0])[-1]
        self.alpha_test = (at >> 4 & 7, ((at >> 8) & 0xff) / 255) if at & 1 else None
        self.grid_only = self.names[0] == GRID and not any(self.names[1:])

    def uses(self, source):
        return any(source in st['src_rgb'] or source in st['src_a'] for st in self.stages)

    def sample(self, unit, uvsets, n):
        im = self.images[unit]
        if im is None:
            return np.ones((n, 4), np.float32)
        name = self.names[unit]
        if name == GRID:
            return np.tile(np.array([0, 0, 0, 1], np.float32), (n, 1))
        c = self.coords[unit]
        if c['mapping'] != 0 or name.lower().startswith(MEAN_OF) or 'touei' in name.lower():
            return np.tile(self.means[unit], (n, 1))
        uv = uvsets[c['src']] if uvsets[c['src']] is not None else uvsets[0]
        m = c['matrix']
        u = m[0, 0] * uv[:, 0] + m[0, 1] * uv[:, 1] + m[0, 3]
        v = m[1, 0] * uv[:, 0] + m[1, 1] * uv[:, 1] + m[1, 3]
        h, w = im.shape[:2]
        x = _wrap(np.floor(u * w).astype(np.int64), w, self.wrap[unit][0])
        y = _wrap(np.floor((1 - v) * h).astype(np.int64), h, self.wrap[unit][1])
        return im[y, x].astype(np.float32) / 255

    def shade(self, uvsets, color, normal, light, n):
        """RGBA (0-1) of n fragments: the six combiner stages, with the vertex colour as the primary colour, the fragment light
        (its ambient plus diffuse times N.L) as the fragment primary colour, and black as the fragment secondary colour."""
        if uvsets[0] is None:
            uvsets = [np.zeros((n, 2))] + list(uvsets[1:])
        tex = [None, None, None]

        def texture(i):
            if tex[i] is None:
                tex[i] = self.sample(i, uvsets, n)
            return tex[i]

        one = np.ones((n, 4), np.float32)
        primary = np.clip(color.astype(np.float32), 0, 1) if color is not None else one
        if primary.shape[1] == 3:
            primary = np.c_[primary, np.ones(n, np.float32)]
        if light is not None and normal is not None:
            nrm = normal / np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-9)
            ndl = np.clip(nrm @ (-light['direction']), 0, 1)[:, None]
            frag1 = self.emission[None, :3] + self.ambient[None, :3] * light['ambient'][None, :3] + \
                self.diffuse[None, :3] * light['diffuse'][None, :3] * ndl
            frag1 = np.c_[np.clip(frag1, 0, 1), np.ones(n)].astype(np.float32)
        else:
            frag1 = one
        frag2 = np.tile(np.array([0, 0, 0, 1], np.float32), (n, 1))
        out = primary.copy()
        buf = np.zeros((n, 4), np.float32)
        nextbuf = np.tile(self.buf_color, (n, 1))
        for i, st in enumerate(self.stages):
            def source(s):
                if s == 0:
                    return primary
                if s == 1:
                    return frag1
                if s == 2:
                    return frag2
                if 3 <= s <= 5:
                    return texture(s - 3)
                if s == 0xd:
                    return buf
                if s == 0xe:
                    return np.tile(st['const'], (n, 1))
                return out
            rgb_in = [_op_rgb(source(s), o) for s, o in zip(st['src_rgb'], st['op_rgb'])]
            a_in = [_op_a(source(s), o) for s, o in zip(st['src_a'], st['op_a'])]
            rgb = _combine(st['comb_rgb'], rgb_in) * st['scale_rgb']
            a = _combine(st['comb_a'], [x[:, None] for x in a_in])[:, 0] * st['scale_a']
            new = np.c_[np.clip(rgb, 0, 1), np.clip(a, 0, 1)].astype(np.float32)
            buf = nextbuf.copy()
            if i < 4:
                if self.buf_rgb[i]:
                    nextbuf[:, :3] = new[:, :3]
                if self.buf_a[i]:
                    nextbuf[:, 3] = new[:, 3]
            out = new
        return out

    def alpha_pass(self, a):
        if self.alpha_test is None:
            return np.ones(len(a), bool)
        f, ref = self.alpha_test
        return [np.zeros_like(a, bool), np.ones_like(a, bool), a == ref, a != ref, a < ref, a <= ref, a > ref, a >= ref][f]


def composite_blend(cv, idx, d, rgba, factor, write_depth, tol=0.02):
    """fe15_raster's blend, with the tolerance for a blended surface lying under what's drawn scaled to Awakening's world (a tile
    is 1 unit here, 50 in Echoes, whose 0.5 let water paint over ice floes 0.2 above it)."""
    order = np.lexsort((d, idx))
    idx, d, rgba = idx[order], d[order], rgba[order]
    depth = cv.depth.reshape(-1)
    vis = d >= depth[idx] - tol
    idx, d, rgba = idx[vis], d[vis], rgba[vis]
    if not len(idx):
        return
    start = np.r_[True, idx[1:] != idx[:-1]]
    grp = np.cumsum(start) - 1
    rank = np.arange(len(idx)) - np.flatnonzero(start)[grp]
    flat = cv.rgb.reshape(-1, 3)
    for r in range(int(rank.max()) + 1):
        s = rank == r
        ii = idx[s]
        dst = flat[ii] / 255
        src = rgba[s]
        out = src[:, :3] * blend_factor(factor[0], src, dst) + dst * blend_factor(factor[1], src, dst)
        flat[ii] = np.clip(out, 0, 1) * 255
        if write_depth:
            depth[ii] = np.maximum(depth[ii], d[s])


# ---------------------------------------------------------------------------------------------------------------------------
# The scene

SKIP_MODELS = ('eff', 'cloud', 'under_cloud', 'sky')   # effects, clouds, birds, the sky dome
SKIP_TEXTURES = ('Bmap_wallpaper', 'bird_01')


GRID_EXTENTS = {}  # art -> [(x min, x max, z min, z max)] of its grid-overlay meshes (the game's own tile grid, skipped)


@lru_cache(maxsize=8)
def scene(art):
    """(meshes, light) of a map's scene: each mesh a dict with positions (world), normals, UV sets, colour, triangles and its
    Material."""
    c = CGFX(scene_file(art))
    images = {}

    def texture(name):
        if name not in images:
            images[name] = c.texture_image(name) if name in c.textures() else None
        return images[name]

    mats = {}
    out = []
    for mname, m in c.sec['models']:
        low = mname.lower()
        if low.startswith(SKIP_MODELS) and 'geo' not in low:
            continue
        for me in c.meshes(m):
            if not me['visible'] or me['material_off'] is None:
                continue
            mo = me['material_off']
            if mo not in mats:
                mats[mo] = Material(c, mo, texture)
            mat = mats[mo]
            if mat.grid_only:
                P = me['positions']
                GRID_EXTENTS.setdefault(art, []).append((P[:, 0].min(), P[:, 0].max(), P[:, 2].min(), P[:, 2].max()))
                continue
            if any(n in SKIP_TEXTURES for n in mat.names if n):
                continue
            me['mat'] = mat
            out.append(me)
    lights = [l for l in c.lights() if 'direction' in l]
    return out, (lights[0] if lights else None)


def render(map_id, px=PX, flip=False):
    """The map seen from above, cropped to the app's grid: a PIL image of width * px by height * px, tile (1, 1) at the bottom
    left. `flip` mirrors the world's z (for the alignment check's comparison only)."""
    m = app_maps()[map_id]
    w, h = m['width'], m['height']
    meshes, light = scene(art_of(map_id))
    cv = Canvas(1, 1, 1 + w, 1 + h, px)
    opaque = [me for me in meshes if me['mat'].blend is None]
    blended = sorted((me for me in meshes if me['mat'].blend is not None), key=lambda me: me['positions'][:, 1].mean())
    for me in opaque + blended:
        mat = me['mat']
        P = me['positions']
        if flip:
            P = P * np.array([1, 1, -1]) + np.array([0, 0, h + 2])
        T = me['triangles']
        if flip:
            T = T[:, ::-1]
        fr = fragments(cv, P, T, mat.cull, [me['uv0'], me['uv1'], me['uv2'], me['color'], me['normals']])
        if fr is None:
            continue
        idx, d, (uv0, uv1, uv2, col, nrm) = fr
        rgba = mat.shade((uv0, uv1, uv2), col, nrm, light, len(idx))
        keep = mat.alpha_pass(rgba[:, 3])
        idx, d, rgba = idx[keep], d[keep], rgba[keep]
        if not len(idx):
            continue
        if mat.blend is None:
            composite_opaque(cv, idx, d, rgba[:, :3])
        else:
            composite_blend(cv, idx, d, rgba, mat.blend, mat.depth_write)
    return cv.image()
