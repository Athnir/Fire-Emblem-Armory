"""A small top-down software rasteriser: textured triangles onto an image, the highest surface winning."""
import numpy as np


def sample(tex, u, v, wrap=True):
    """Nearest texel of tex (h, w, 4; row 0 the top) at (u, v) with v up (the 3DS's convention)."""
    h, w = tex.shape[:2]
    if wrap:
        x = np.floor(u * w).astype(np.int64) % w
        y = np.floor((1 - v) * h).astype(np.int64) % h
    else:
        x = np.clip(np.floor(u * w).astype(np.int64), 0, w - 1)
        y = np.clip(np.floor((1 - v) * h).astype(np.int64), 0, h - 1)
    return tex[y, x]


class Canvas:
    def __init__(self, x0, z0, x1, z1, ppu):
        """World rectangle [x0, x1) x [z0, z1) at ppu pixels per world unit; column = x, row = z."""
        self.x0, self.z0, self.ppu = x0, z0, ppu
        self.W = int(round((x1 - x0) * ppu))
        self.H = int(round((z1 - z0) * ppu))
        self.rgb = np.zeros((self.H, self.W, 3), np.float32)
        self.depth = np.full((self.H, self.W), -1e9, np.float32)
        self.ident = np.full((self.H, self.W), -1, np.int32)  # which layer drew the pixel

    def draw(self, P, UV, T, tex, color=None, tag=0, alpha_test=0.5, wrap=True, depth_bias=0.0, tint=None):
        """P: N x 3 world positions (y up), UV: N x 2, T: M x 3, tex: RGBA image, color: N x 4 vertex colours (multiplied)."""
        if len(T) == 0:
            return
        px = (P[:, 0] - self.x0) * self.ppu
        pz = (P[:, 2] - self.z0) * self.ppu
        py = P[:, 1] + depth_bias
        for a, b, c in T:
            xs = px[[a, b, c]]
            zs = pz[[a, b, c]]
            minx, maxx = int(np.floor(xs.min())), int(np.ceil(xs.max()))
            minz, maxz = int(np.floor(zs.min())), int(np.ceil(zs.max()))
            minx, minz = max(minx, 0), max(minz, 0)
            maxx, maxz = min(maxx, self.W - 1), min(maxz, self.H - 1)
            if minx > maxx or minz > maxz:
                continue
            den = (zs[1] - zs[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (zs[0] - zs[2])
            if abs(den) < 1e-9:
                continue
            gx, gz = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(minz, maxz + 1) + 0.5)
            l0 = ((zs[1] - zs[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gz - zs[2])) / den
            l1 = ((zs[2] - zs[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gz - zs[2])) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not inside.any():
                continue
            l0, l1, l2 = l0[inside], l1[inside], l2[inside]
            gzi = (gz[inside] - 0.5).astype(np.int64)
            gxi = (gx[inside] - 0.5).astype(np.int64)
            d = l0 * py[a] + l1 * py[b] + l2 * py[c]
            front = d > self.depth[gzi, gxi]
            if not front.any():
                continue
            l0, l1, l2, gzi, gxi, d = l0[front], l1[front], l2[front], gzi[front], gxi[front], d[front]
            if tex is not None and UV is not None:
                u = l0 * UV[a, 0] + l1 * UV[b, 0] + l2 * UV[c, 0]
                v = l0 * UV[a, 1] + l1 * UV[b, 1] + l2 * UV[c, 1]
                col = sample(tex, u, v, wrap).astype(np.float32)
            else:
                col = np.full((len(d), 4), 255, np.float32)
                if tint is not None:
                    col[:, :3] = tint
            if color is not None:
                vc = (l0[:, None] * color[a] + l1[:, None] * color[b] + l2[:, None] * color[c])
                col[:, :3] *= np.clip(vc[:, :3], 0, 2)
            keep = col[:, 3] >= alpha_test * 255
            if not keep.any():
                continue
            gzi, gxi = gzi[keep], gxi[keep]
            self.rgb[gzi, gxi] = col[keep, :3]
            self.depth[gzi, gxi] = d[keep]
            self.ident[gzi, gxi] = tag

    def image(self):
        from PIL import Image
        return Image.fromarray(np.clip(self.rgb, 0, 255).astype(np.uint8))


def fragments(cv, P, T, cull, attrs):
    """Every pixel centre each triangle covers: (flat pixel index, height, [interpolated attribute arrays]). cull: 0 keep all,
    1 keep clockwise (seen from above), 2 keep counter-clockwise (facing up)."""
    px = (P[:, 0] - cv.x0) * cv.ppu
    pz = (P[:, 2] - cv.z0) * cv.ppu
    py = P[:, 1]
    if cull and len(T):
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        u, v = b - a, c - a
        ny = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        T = T[ny > 0] if cull == 2 else T[ny < 0]
    idx_l, d_l, bary_l, tri_l = [], [], [], []
    W, H = cv.W, cv.H
    for ti, (a, b, c) in enumerate(T):
        xs = px[[a, b, c]]
        zs = pz[[a, b, c]]
        minx, maxx = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())), W - 1)
        minz, maxz = max(int(np.floor(zs.min())), 0), min(int(np.ceil(zs.max())), H - 1)
        if minx > maxx or minz > maxz:
            continue
        den = (zs[1] - zs[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (zs[0] - zs[2])
        if abs(den) < 1e-9:
            continue
        gx, gz = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(minz, maxz + 1) + 0.5)
        gx, gz = gx.ravel(), gz.ravel()
        l0 = ((zs[1] - zs[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gz - zs[2])) / den
        l1 = ((zs[2] - zs[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gz - zs[2])) / den
        l2 = 1 - l0 - l1
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any():
            continue
        l0, l1, l2 = l0[ins], l1[ins], l2[ins]
        idx_l.append((gz[ins] - 0.5).astype(np.int64) * W + (gx[ins] - 0.5).astype(np.int64))
        d_l.append(l0 * py[a] + l1 * py[b] + l2 * py[c])
        bary_l.append(np.c_[l0, l1, l2])
        tri_l.append(np.full(len(l0), ti))
    if not idx_l:
        return None
    idx = np.concatenate(idx_l)
    d = np.concatenate(d_l)
    bary = np.concatenate(bary_l)
    tri = np.concatenate(tri_l)
    vs = T[tri]  # (n, 3) vertex ids
    out = []
    for A in attrs:
        if A is None:
            out.append(None)
            continue
        out.append(bary[:, 0:1] * A[vs[:, 0]] + bary[:, 1:2] * A[vs[:, 1]] + bary[:, 2:3] * A[vs[:, 2]])
    return idx, d, out


def composite_opaque(cv, idx, d, rgb):
    """Keep the highest fragment per pixel, where it's above what's drawn."""
    order = np.lexsort((d, idx))
    idx, d, rgb = idx[order], d[order], rgb[order]
    last = np.r_[idx[1:] != idx[:-1], True]
    idx, d, rgb = idx[last], d[last], rgb[last]
    depth = cv.depth.reshape(-1)
    front = d > depth[idx]
    idx, d, rgb = idx[front], d[front], rgb[front]
    cv.rgb.reshape(-1, 3)[idx] = rgb * 255
    depth[idx] = d


def composite_blend(cv, idx, d, rgba, factor, write_depth):
    """Blend fragments over what's drawn, lowest first, where they aren't under it."""
    from fe15_shade import blend_factor
    order = np.lexsort((d, idx))
    idx, d, rgba = idx[order], d[order], rgba[order]
    depth = cv.depth.reshape(-1)
    vis = d >= depth[idx] - 0.5
    idx, d, rgba = idx[vis], d[vis], rgba[vis]
    if not len(idx):
        return
    start = np.r_[True, idx[1:] != idx[:-1]]
    grp = np.cumsum(start) - 1
    first = np.flatnonzero(start)
    rank = np.arange(len(idx)) - first[grp]
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
