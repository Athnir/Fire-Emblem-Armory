"""
The DS Fire Emblems' map art, Shadow Dragon's (FE11) and New Mystery of the Emblem's (FE12), read from the user's own cartridges (never
written out), for each map's own colours (`fills`; the user's call, as the GBA games', Shadow Dragon and the Blade of Light's and the
Tellius games' are).

The maps are drawn with the DS's 3D engine, not with BG tiles:
- map/<chapter> (Awakening's Bin container): +4 a pointer to its texture file's name ('bmap001.ta'), +0xc width, +0xd height (tiles,
  with the one-tile border the app crops), +0x10 the terrain grid, +0x14 the room grid, +0x18 the layer list (up to +0x1c, the material
  list).
  - A layer (0x18 bytes): +0 kind (0 ground and overlays, 1 a village's sprite at tile (+2, +3), 2 a room's roof, 3 an animated flag,
    4 a roof's shadow, 5 a weather overlay: snow, sand, mist), +1 the polygon alpha (0-31), +4 its material, +8 / +0xc its GX display
    list and size (axis-aligned quads, packed BEGIN_VTXS, TEXCOORD, VTX_16, VTX_XY, END_VTXS), +0x10 / +0x14 animation records.
  - The map's units are 24 per tile and textures are mapped one texel per unit: the art is 24 texels per tile.
  - A material (0x28 bytes): +0 the texture's offset and +4 its size in the .ta file, +0xc / +0x10 its palette's, +0x1c width, +0x1e
    height, +0x20 the GX format (1 A3I5, 4 8 bpp), +0x23 repeat (1 s, 2 t), +0x25 colour 0 transparent.
- map/<chapter>.ta: the textures and palettes back to back. FE12's are LZ11; FE11's LZ10 or a format of their own, header byte 0x40
  (`zero_rle`: only runs of zeros packed).
"""
import hashlib
import os
import struct
import sys
from functools import lru_cache

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe11_extract  # noqa: E402  (the cartridges' paths)
import fe12_extract  # noqa: E402
import tellius_minimaps  # noqa: E402  (soften, contrast)
from fe13_bin import Bin  # noqa: E402
from nds_rom import Nds, decompress  # noqa: E402

UNIT = 24  # map units (and texels) per tile
CART = {'fe11': fe11_extract.CART, 'fe12': fe12_extract.CART}
CODE = {'fe11': 'YFEE', 'fe12': 'VI2J'}

GROUND, VILLAGE, ROOF, FLAG, ROOF_SHADOW, WEATHER = 0, 1, 2, 3, 4, 5


@lru_cache(None)
def rom(game):
    r = Nds(CART[game])
    assert r.code == CODE[game], r.code
    return r


def zero_rle(d):
    """FE11's .ta compression 0x40: literals, with runs of zeros coded 0x00 n (n + 1) or 0x00 n m ((n & 0x7f) << 8 | m, + 1)."""
    size = int.from_bytes(d[1:4], 'little')
    out, i = bytearray(), 4
    while len(out) < size:
        b = d[i]
        if b:
            out.append(b)
            i += 1
            continue
        n = d[i + 1]
        if n & 0x80:
            n = (n & 0x7f) << 8 | d[i + 2]
            i += 3
        else:
            i += 2
        out += bytes(n + 1)
    return bytes(out)


class MapFile:
    def __init__(self, game, key):
        r = rom(game)
        self.game, self.key = game, key
        self.b = b = Bin(r.read('map/' + key))
        self.d = b.d
        self.w, self.h = self.u8(0xc), self.u8(0xd)
        ta_name = b.cstr(0x20 + b.u32(4))
        raw = r.read('map/' + ta_name)
        self.ta = zero_rle(raw) if raw[0] == 0x40 else decompress(raw)
        self.layers = []
        o, end = b.u32(0x18), b.u32(0x1c)
        while o < end:
            kind, alpha, x, y, mat, dl, size, a1, a2 = struct.unpack_from('<4B5I', self.d, 0x20 + o)
            quads = self.quads(dl, size)
            self.layers.append({'index': len(self.layers), 'kind': kind, 'alpha': alpha if kind not in (VILLAGE, FLAG) else 31,
                                'tile': (x, y), 'mat': mat, 'quads': quads, 'z': quads[0][0][2] if quads else 0,
                                'anim': (a1, a2)})
            o += 0x18
        self._tex = {}

    def u8(self, o):
        return self.d[0x20 + o]

    def quads(self, off, size):
        """[[(x, y, z, s, t)] * 4] from a packed GX display list (only BEGIN_VTXS quads, TEXCOORD, VTX_16, VTX_XY, END_VTXS occur)."""
        nparam = {0x00: 0, 0x20: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1, 0x28: 1, 0x29: 1, 0x2a: 1, 0x2b: 1,
                  0x40: 1, 0x41: 0}
        d, p, end = self.d, 0x20 + off, 0x20 + off + size
        verts, s, t, x, y, z = [], 0.0, 0.0, 0, 0, 0
        sx = lambda v: v - 0x10000 if v & 0x8000 else v  # noqa: E731
        while p < end:
            cmds = d[p:p + 4]
            p += 4
            for c in cmds:
                n = nparam[c]
                a = struct.unpack_from('<%dI' % n, d, p)
                p += 4 * n
                if c == 0x40:
                    assert a[0] == 1, 'only quads'
                elif c == 0x22:
                    s, t = sx(a[0] & 0xffff) / 16, sx(a[0] >> 16) / 16
                elif c == 0x23:
                    x, y, z = sx(a[0] & 0xffff), sx(a[0] >> 16), sx(a[1] & 0xffff)
                    verts.append((x, y, z, s, t))
                elif c == 0x25:
                    x, y = sx(a[0] & 0xffff), sx(a[0] >> 16)
                    verts.append((x, y, z, s, t))
                elif c in (0x24, 0x26, 0x27, 0x28):
                    raise ValueError('unexpected vertex command %#x' % c)
        return [verts[i:i + 4] for i in range(0, len(verts) - 3, 4)]

    def material(self, mat):
        m = self.d[0x20 + mat:0x20 + mat + 0x28]
        to, ts, _, po, ps = struct.unpack_from('<5I', m, 0)
        w, h = struct.unpack_from('<HH', m, 0x1c)
        return {'tex': (to, ts), 'pal': (po, ps), 'w': w, 'h': h, 'fmt': m[0x20], 'repeat': m[0x23], 'zero': m[0x25]}

    def texture(self, mat):
        """RGBA texels (h, w, 4) of a material: A3I5 (alpha 3 bits, 5-bit index) or 8 bpp (colour 0 transparent where flagged)."""
        if mat in self._tex:
            return self._tex[mat]
        m = self.material(mat)
        (to, ts), (po, ps) = m['tex'], m['pal']
        raw = np.frombuffer(self.ta[to:to + ts], np.uint8).astype(np.int32)
        pal = rgb555(np.frombuffer(self.ta[po:po + ps], np.uint16))
        rgba = np.zeros((raw.size, 4), np.uint8)
        if m['fmt'] == 1:
            idx, a3 = raw & 31, raw >> 5
            rgba[:, :3] = pal[np.minimum(idx, len(pal) - 1)]
            rgba[:, 3] = (a3 * 4 + a3 // 2) * 255 // 31
        elif m['fmt'] == 4:
            rgba[:, :3] = pal[np.minimum(raw, len(pal) - 1)]
            rgba[:, 3] = 255
            if m['zero']:
                rgba[raw == 0, 3] = 0
        else:
            raise ValueError('texture format %d' % m['fmt'])
        tex = rgba.reshape(m['h'], m['w'], 4)
        self._tex[mat] = tex
        return tex

    def texture_key(self, mat):
        """A name for a material's texels and palette that's the same in every map sharing them."""
        m = self.material(mat)
        (to, ts), (po, ps) = m['tex'], m['pal']
        return hashlib.md5(self.ta[to:to + ts] + self.ta[po:po + ps]).hexdigest()[:8]


def rgb555(v):
    v = np.asarray(v, np.uint32)
    return np.stack([(v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31], -1).astype(np.uint8)


@lru_cache(None)
def mapfile(game, key):
    return MapFile(game, key)


def affine(q):
    """(s, t) as a + b x + c y over the quad's corners (exact: every quad is an axis-aligned rectangle)."""
    A = np.array([[1, v[0], v[1]] for v in q], float)
    S = np.array([[v[3], v[4]] for v in q], float)
    coef, *_ = np.linalg.lstsq(A, S, rcond=None)
    return coef  # rows: const, d/dx, d/dy; columns: s, t


def draw_quad(canvas, tex, q, alpha, repeat):
    """Fill the quad's pixels [x0, x1) x [y0, y1); texcoords are taken at each pixel's top-left corner, as the DS interpolates them
    (so a mirrored quad's s 23 -> -1 reads texels 23..0), clamped or wrapped by the material."""
    H, W = canvas.shape[:2]
    xs, ys = [v[0] for v in q], [v[1] for v in q]
    x0, x1, y0, y1 = max(min(xs), 0), min(max(xs), W), max(min(ys), 0), min(max(ys), H)
    if x0 >= x1 or y0 >= y1:
        return
    coef = affine(q)
    px, py = np.meshgrid(np.arange(x0, x1, dtype=float), np.arange(y0, y1, dtype=float))
    s = coef[0, 0] + coef[1, 0] * px + coef[2, 0] * py
    t = coef[0, 1] + coef[1, 1] * px + coef[2, 1] * py
    th, tw = tex.shape[:2]
    si, ti = np.floor(s + 1e-6).astype(int), np.floor(t + 1e-6).astype(int)
    si = np.mod(si, tw) if repeat & 1 else np.clip(si, 0, tw - 1)
    ti = np.mod(ti, th) if repeat & 2 else np.clip(ti, 0, th - 1)
    c = tex[ti, si].astype(np.float32)
    a = c[..., 3:4] / 255.0 * alpha
    sub = canvas[y0:y1, x0:x1]
    sub[..., :3] = sub[..., :3] * (1 - a) + c[..., :3] * a
    sub[..., 3:4] = np.maximum(sub[..., 3:4], a)


def drawn_layers(mf, roofs=True, weather=False, villages=None):
    """The layers drawn, far to near (by depth, then the list's order backwards). `villages`: the village sprites' tiles to keep
    (None keeps all)."""
    out = []
    for L in mf.layers:
        if L['kind'] in (ROOF, ROOF_SHADOW) and not roofs:
            continue
        if L['kind'] == WEATHER and not weather:
            continue
        if L['kind'] == VILLAGE and villages is not None and L['tile'] not in villages:
            continue
        out.append(L)
    return sorted(out, key=lambda L: (-L['z'], -L['index']))


@lru_cache(None)
def texels(game, key):
    """(h, w, 576, 3): each app tile's 24 x 24 texels as the map starts, the one-tile border off, drawn without the roofs over
    closed rooms (the floor under them) or the weather."""
    mf = mapfile(game, key)
    canvas = np.zeros((mf.h * UNIT, mf.w * UNIT, 4), np.float32)
    for L in drawn_layers(mf, roofs=False, weather=False):
        m = mf.material(L['mat'])
        tex = mf.texture(L['mat'])
        for q in L['quads']:
            draw_quad(canvas, tex, q, L['alpha'] / 31.0, m['repeat'])
    a = canvas[UNIT:(mf.h - 1) * UNIT, UNIT:(mf.w - 1) * UNIT, :3]
    h, w = mf.h - 2, mf.w - 2
    return a.reshape(h, UNIT, w, UNIT, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, UNIT * UNIT, 3)


def tile_colours(game, key):
    """Rows (top to bottom) of each app tile's colour: the median of its texels."""
    return np.median(texels(game, key), axis=2)


# A plain tile is dirt (`ga`) where its art is mostly the map's dirt (the user's call: the DS maps' tan patches and paths, sorted
# from the art before any marking by hand). The map's plain texels part into two looks, its grass and a paler, less green one
# (two-means over lightness, green share and warmth, seeded at the greenest and the palest quarter); when the pale look is lighter
# and less green enough to be dirt, a tile is dirt where at least this share of its texels are.
DIRT_SHARE = 0.45
DIRT_LIGHTER, DIRT_LESS_GREEN = 0.04, 0.05


def _looks(p):
    s = p.sum(1) + 1e-6
    return np.stack([p.mean(1) / 255, p[:, 1] / s * 3, (p[:, 0] - p[:, 2]) / 255], 1)


def dirt(game, key, codes):
    """{(row, column) from 0 at the top left}: the plain (`t0`) tiles drawn as dirt. `codes` the map's rows of app codes."""
    return dirt_of(texels(game, key), codes)


def dirt_of(px, codes):
    """dirt() over any map's tiles: `px` (h, w, n, 3) each tile's texels, `codes` its rows of app codes (Echoes' too)."""
    plain = [(r, c) for r, row in enumerate(codes) for c, code in enumerate(row) if code == 't0']
    if len(plain) < 8:
        return set()
    X = _looks(np.concatenate([px[r][c][::7] for r, c in plain]))
    greenest = X[:, 1] >= np.quantile(X[:, 1], 0.75)
    palest = (X[:, 0] >= np.quantile(X[:, 0], 0.75)) & (X[:, 1] <= np.median(X[:, 1]))
    if not palest.any():
        return set()
    C = np.stack([np.median(X[greenest], 0), np.median(X[palest], 0)])
    for _ in range(20):
        near = np.argmin(((X[:, None] - C[None]) ** 2).sum(2), 1)
        C = np.stack([X[near == k].mean(0) if (near == k).any() else C[k] for k in range(2)])
    grass, pale = C
    if not (pale[0] - grass[0] > DIRT_LIGHTER and grass[1] - pale[1] > DIRT_LESS_GREEN):
        return set()
    out = set()
    for r, c in plain:
        near = np.argmin(((_looks(px[r][c])[:, None] - C[None]) ** 2).sum(2), 1)
        if (near == 1).mean() >= DIRT_SHARE:
            out.add((r, c))
    return out


# The codes each map colours from its art: plain, dirt, floor, sand, river, sea, walls and stone walls (ledges).
COLOURED = {'t0', 'ga', 't1', 'td', 'tg', 'we', 'w0', 'tt'}
MIN_TILES = 4


# Water is its blue texels' colour, not the banks its edge tiles show (the user: the rivers came out grey-green).
WATER = {'tg', 'we'}


def fills(game, key, codes):
    """{code: colour} for a map's ground, water and walls: the median of each code's tiles, softened to the app's and walls kept a
    step apart from the ground (tellius_minimaps' soften and contrast). `codes` the map's rows of app codes, top to bottom."""
    px = texels(game, key)
    seen = np.median(px, axis=2)
    for r, row in enumerate(codes):
        for c, code in enumerate(row):
            if code in WATER:
                t = px[r][c]
                blue = t[(t[:, 2] > t[:, 0] + 12) & (t[:, 2] >= t[:, 1])]
                if len(blue) >= 0.3 * len(t):
                    seen[r][c] = np.median(blue, 0)
    return fills_of(seen, codes, COLOURED)


# Boards laid on the ground (Shadow Dragon's and New Mystery's walkways between a town's houses): a plain tile whose grain runs much
# more one way than the other, in a wood's colour (the user: wood tiles).
PLANKS, WOOD = 1.4, 0.2
# Bones lying in a desert (New Mystery's, as Mystery of the Emblem's): a sand tile with this share of bone-white texels.
BONE_WHITE = 0.01


def boards(game, key, codes):
    """{(row, column) from 0}: the plain (`t0`) tiles drawn as boards."""
    px = texels(game, key)
    out = set()
    for r, row in enumerate(codes):
        for c, code in enumerate(row):
            if code != 't0':
                continue
            t = px[r][c].reshape(UNIT, UNIT, 3) / 255
            L = (t.max(2) + t.min(2)) / 2
            dx, dy = np.abs(np.diff(L, axis=1)).mean(), np.abs(np.diff(L, axis=0)).mean()
            p = t.reshape(-1, 3)
            wood = ((p[:, 0] >= p[:, 1]) & (p[:, 1] >= p[:, 2] + 0.08)).mean()
            if max(dx, dy) / max(min(dx, dy), 1e-3) >= PLANKS and wood >= WOOD:
                out.add((r, c))
    # Boards come in walkways: a lone tile is something else.
    return {(r, c) for r, c in out if any((r + dr, c + dc) in out for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


def bones(game, key, codes):
    """{(row, column) from 0}: the sand and desert tiles with bones lying on them."""
    px = texels(game, key)
    return {(r, c) for r, row in enumerate(codes) for c, code in enumerate(row)
            if code in ('td', 'tk') and (px[r][c].min(1) > 0.78 * 255).mean() >= BONE_WHITE}


def fills_of(seen, codes, coloured, grounds=None, walls=None):
    """fills() over any map's tiles: `seen` each tile's colour by row and column, the codes in `coloured` given theirs; `grounds` and
    `walls` the codes the walls are kept a step apart from (tellius_minimaps.contrast), where a game's differ from the defaults."""
    by_code = {}
    for r, row in enumerate(codes):
        for c, code in enumerate(row):
            by_code.setdefault(code, []).append(seen[r][c])
    out = {code: tellius_minimaps.soften(np.median(np.array(cs), 0)) for code, cs in by_code.items()
           if code in coloured and len(cs) >= MIN_TILES}
    tellius_minimaps.contrast(out, by_code, grounds, walls)
    return out
