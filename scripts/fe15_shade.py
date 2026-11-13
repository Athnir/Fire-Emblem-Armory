"""A BCH material as the PICA200 draws it, simplified for a view from straight above.

Read from the material: its three texture units (names, wrap modes) and their coordinators (params +0x0c, 24 bytes each: flags,
transform type, mapping type 0 UV / 1 cube env / 2 sphere env / 3 projection, reference camera; scale, rotation, translation), its
fragment commands (params +0xc8: the six texture combiner stages 0xc0-0xfd with their constant colours, the combiner buffer
0xe0 / 0xfd, face culling 0x40, blending 0x100 / 0x101, alpha test 0x104, depth write 0x107) and its colours (params +0x5c..).

What isn't the material's own is approximated: the fragment lighting's primary colour is white (the ground textures carry their
own baked light), its secondary colour the material's specular colours times SPECULAR (the sea's teal comes from there), a texture mapped by
environment or projection (sky reflections, cloud and shadow maps) its mean colour (the shadow map dummy: white). Texture unit i
reads the mesh's UV set i (the PICA's texture coordinate i), or its first where it has no set i: a ship's atlas on set 1 and its
baked shadows on set 0, a ruin's stone on set 0 and its light map on set 1.
"""
import math
import struct

import numpy as np

from fe15_bch import pica_commands

STAGE_REGS = [0xc0, 0xc8, 0xd0, 0xd8, 0xf0, 0xf8]
# The fragment lighting's secondary (specular) colour seen from straight above: the material's specular colours, scaled down
# as a Fresnel term would for a view along the normal (a guess: the game's LUTs aren't evaluated).
SPECULAR = 0.35


def _rgba(v):
    return np.array([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, v >> 24], np.float32) / 255


class Material:
    def __init__(self, b, mat_entry, texture_lookup):
        """b: the BCH; mat_entry: the 0x2c-byte material record; texture_lookup(name) -> RGBA image or None."""
        w = struct.unpack_from('<11I', b.d, mat_entry)
        self.names = [b.cstr(x) for x in w[7:10]]
        self.name = b.cstr(w[10])
        self.images = [texture_lookup(n) if n else None for n in self.names]
        p = w[0]
        self.coords = []
        for i in range(3):
            o = p + 0x0c + 24 * i
            flags, ttype, mapping, cam = struct.unpack_from('<BBBb', b.d, o)
            sx, sy, rot, tx, ty = struct.unpack_from('<5f', b.d, o + 4)
            self.coords.append({'mapping': mapping, 'scale': (sx, sy), 'rot': rot, 'trans': (tx, ty)})
        cols = {}
        for name, off in (('emission', 0x5c), ('ambient', 0x60), ('diffuse', 0x64), ('specular0', 0x68), ('specular1', 0x6c)):
            cols[name] = _rgba(b.u32(p + off))
        self.colors = cols
        frag = (b.u32(p + 0xc8), b.u32(p + 0xcc))
        regs, _ = pica_commands(b.d, *frag)
        tregs, _ = pica_commands(b.d, w[4], w[5])
        self.regs = regs
        r = lambda k, d=0: regs.get(k, [d])[-1]
        self.stages = []
        for base in STAGE_REGS:
            src, opnd, comb, col, scale = (r(base + k) for k in range(5))
            self.stages.append({
                'src_rgb': [(src >> (4 * k)) & 0xf for k in range(3)], 'src_a': [(src >> (16 + 4 * k)) & 0xf for k in range(3)],
                'op_rgb': [(opnd >> (4 * k)) & 0xf for k in range(3)], 'op_a': [(opnd >> (12 + 4 * k)) & 0x7 for k in range(3)],
                'comb_rgb': comb & 0xf, 'comb_a': (comb >> 16) & 0xf, 'const': _rgba(col),
                'scale_rgb': float(1 << (scale & 3)), 'scale_a': float(1 << ((scale >> 16) & 3))})
        upd = r(0xe0)
        self.buf_rgb = [(upd >> (8 + i)) & 1 for i in range(4)]
        self.buf_a = [(upd >> (12 + i)) & 1 for i in range(4)]
        self.buf_color = _rgba(r(0xfd, 0xff000000))
        self.cull = r(0x40) & 3
        mode = (r(0x100, 0xe40100) >> 8) & 3
        bf = r(0x101, 0x01010000)
        self.blend = None
        if mode == 1:
            src_rgb, dst_rgb, src_a, dst_a = (bf >> 16) & 0xf, (bf >> 20) & 0xf, (bf >> 24) & 0xf, (bf >> 28) & 0xf
            if not (src_rgb == 1 and dst_rgb == 0):
                self.blend = (src_rgb, dst_rgb)
        at = r(0x104)
        self.alpha_test = (at >> 4 & 7, ((at >> 8) & 0xff) / 255) if at & 1 else None
        self.depth_write = bool(r(0x107, 0x1f41) >> 12 & 1)
        # wrap modes (texture unit 0, 1, 2 parameter registers 0x83, 0x93, 0x9b: bits 8-10 t, 12-14 s)
        self.wrap = []
        for reg in (0x83, 0x93, 0x9b):
            v = tregs.get(reg, [0x2220])[-1]
            self.wrap.append(((v >> 12) & 7, (v >> 8) & 7))
        self.means = [None if im is None else im.reshape(-1, 4).mean(0).astype(np.float32) / 255 for im in self.images]

    # -----------------------------------------------------------------------------------------------------------------------
    def sample(self, unit, uv):
        im = self.images[unit]
        n = len(uv)
        if im is None:
            return np.ones((n, 4), np.float32)
        c = self.coords[unit]
        name = self.names[unit] or ''
        if c['mapping'] != 0:
            if 'shadow' in name.lower():
                return np.ones((n, 4), np.float32)
            return np.tile(self.means[unit], (n, 1))
        sx, sy = c['scale']
        u = uv[:, 0] * sx
        v = uv[:, 1] * sy
        if c['rot']:
            cr, sr = math.cos(c['rot']), math.sin(c['rot'])
            u, v = u * cr - v * sr, u * sr + v * cr
        u = u - c['trans'][0]
        v = v - c['trans'][1]
        h, w = im.shape[:2]
        x = np.floor(u * w).astype(np.int64)
        y = np.floor((1 - v) * h).astype(np.int64)
        ws, wt = self.wrap[unit]
        x = _wrap(x, w, ws)
        y = _wrap(y, h, wt)
        return im[y, x].astype(np.float32) / 255

    def shade(self, uvs, color, n):
        """RGBA (0-1) of each fragment from its UV sets (texture unit i reads UV set i, or the first where the mesh has no
        set i) and vertex colour (None: white)."""
        uvs = [u for u in uvs]
        if uvs[0] is None:
            uvs[0] = np.zeros((n, 2))
        tex = [None, None, None]

        def texture(i):
            if tex[i] is None:
                tex[i] = self.sample(i, uvs[i] if uvs[i] is not None else uvs[0])
            return tex[i]

        one = np.ones((n, 4), np.float32)
        primary = color.astype(np.float32) if color is not None else one
        if primary.shape[1] == 3:
            primary = np.c_[primary, np.ones(n, np.float32)]
        primary = np.clip(primary, 0, 1)
        light1 = one
        spec = np.clip((self.colors["specular0"] + self.colors["specular1"]) * SPECULAR, 0, 1)
        spec[3] = 1
        light2 = np.tile(spec, (n, 1))
        out = primary.copy()
        buf = np.zeros((n, 4), np.float32)
        nextbuf = np.tile(self.buf_color, (n, 1))
        for i, st in enumerate(self.stages):
            def source(s):
                if s == 0:
                    return primary
                if s == 1:
                    return light1
                if s == 2:
                    return light2
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


def _wrap(x, n, mode):
    if mode == 3:  # mirrored repeat
        x = np.mod(x, 2 * n)
        return np.where(x >= n, 2 * n - 1 - x, x)
    if mode in (0, 1):  # clamp to edge / border
        return np.clip(x, 0, n - 1)
    return np.mod(x, n)


def _op_rgb(c, o):
    if o == 0:
        return c[:, :3]
    if o == 1:
        return 1 - c[:, :3]
    if o in (2, 3):
        a = c[:, 3:4] if o == 2 else 1 - c[:, 3:4]
        return np.repeat(a, 3, 1)
    ch = {4: 0, 5: 0, 8: 1, 9: 1, 12: 2, 13: 2}.get(o, 0)
    v = c[:, ch:ch + 1]
    if o in (5, 9, 13):
        v = 1 - v
    return np.repeat(v, 3, 1)


def _op_a(c, o):
    ch = {0: 3, 1: 3, 2: 0, 3: 0, 4: 1, 5: 1, 6: 2, 7: 2}[o]
    v = c[:, ch]
    return 1 - v if o & 1 else v


def _combine(op, x):
    a, b, c = x
    if op == 0:
        return a
    if op == 1:
        return a * b
    if op == 2:
        return np.minimum(a + b, 1)
    if op == 3:
        return np.clip(a + b - 0.5, 0, 1)
    if op == 4:
        return a * c + b * (1 - c)
    if op == 5:
        return np.maximum(a - b, 0)
    if op in (6, 7):
        d = 4 * ((a - 0.5) * (b - 0.5)).sum(1, keepdims=True)
        return np.repeat(np.clip(d, 0, 1), a.shape[1], 1)
    if op == 8:
        return np.minimum(a * b + c, 1)
    if op == 9:
        return np.minimum(a + b, 1) * c
    return a


def blend_factor(f, src, dst):
    """A PICA blend factor (0 zero, 1 one, 2 src colour, 3 1 - src colour, 4 dst colour, 5 1 - dst colour, 6 src alpha,
    7 1 - src alpha, 8 dst alpha, 9 1 - dst alpha) for RGB."""
    n = len(src)
    if f == 0:
        return np.zeros((n, 3), np.float32)
    if f == 1:
        return np.ones((n, 3), np.float32)
    if f == 2:
        return src[:, :3]
    if f == 3:
        return 1 - src[:, :3]
    if f == 4:
        return dst
    if f == 5:
        return 1 - dst
    if f == 6:
        return np.repeat(src[:, 3:4], 3, 1)
    if f == 7:
        return np.repeat(1 - src[:, 3:4], 3, 1)
    if f in (8, 9):
        return np.ones((n, 3), np.float32) if f == 8 else np.zeros((n, 3), np.float32)
    return np.ones((n, 3), np.float32)
