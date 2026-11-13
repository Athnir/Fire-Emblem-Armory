"""Fates' BCH materials seen from straight above (scratch): scripts/fe15_shade.Material with these changes.
- The real-time shadow map (ShadowMapDummyTex, or a projected 'shadow' map) is the program's own, drawn at run time: here it lets
  the colour through unchanged (1 where the combiner multiplies, 0 where it adds), whatever operand reads it (Fates' grounds use
  1 - shadow, which read as black with the shadow taken as white).
- The fragment lighting's secondary (specular) colour is black, as Awakening's renderer has it: the LUTs aren't evaluated, and the
  material's specular colours made the seas pink.
- Environment-mapped textures (sky reflections) give their mean colour, as before."""
import numpy as np

from fe15_shade import Material, _combine, _op_a, _op_rgb

ADDS = (2, 3, 5)  # add, add signed, subtract: a neutral operand is 0


class FMaterial(Material):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.shadow_units = {i for i, (n, c) in enumerate(zip(self.names, self.coords))
                             if n and (n == 'ShadowMapDummyTex' or (c['mapping'] != 0 and 'shadow' in n.lower()))}
        self.untextured = not any(self.names)

    def shade(self, uvs, color, n):
        uvs = list(uvs)
        if uvs[0] is None:
            uvs[0] = np.zeros((n, 2))
        tex = [None, None, None]

        def texture(i):
            if tex[i] is None:
                tex[i] = self.sample(i, uvs[i] if uvs[i] is not None else uvs[0])
            return tex[i]

        one = np.ones((n, 4), np.float32)
        zero3 = np.zeros((n, 3), np.float32)
        primary = color.astype(np.float32) if color is not None else one
        if primary.shape[1] == 3:
            primary = np.c_[primary, np.ones(n, np.float32)]
        primary = np.clip(primary, 0, 1)
        light1 = one
        light2 = np.tile(np.array([0, 0, 0, 1], np.float32), (n, 1))
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
            neutral_rgb = zero3 if st['comb_rgb'] in ADDS else np.ones((n, 3), np.float32)
            neutral_a = np.zeros(n, np.float32) if st['comb_a'] in ADDS else np.ones(n, np.float32)
            rgb_in = [neutral_rgb if 3 <= s <= 5 and (s - 3) in self.shadow_units else _op_rgb(source(s), o)
                      for s, o in zip(st['src_rgb'], st['op_rgb'])]
            a_in = [neutral_a if 3 <= s <= 5 and (s - 3) in self.shadow_units else _op_a(source(s), o)
                    for s, o in zip(st['src_a'], st['op_a'])]
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
