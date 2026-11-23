"""
Each Engage map's colours as the game draws them, from its lit render (scripts/fe17_render.py): each tile's centre as the emulator's
photos were sampled (scripts' scratch colours.py: the middle of the tile, its lit pixels between the 35th and 95th percentile, the
median), the median per code over the tiles inside a patch of their code (all of them where fewer than three are), written to
data-raw/fe17-lit-fills.json for scripts/build-fe17-maps.py. The maps photographed in the emulator keep the photos' colours over these
(data-raw/fe17-emu-fills.json); these colour the rest (the Prologue, Chapters 1 and 2, the Tempest Trials' stages no skirmish reaches)
and the codes the photos missed: the ground, walls and water. Lava and fire, which glow in the game, aren't lit so here: left
out (the app keeps them dim).

Renders (16 px a tile) are cached in data-raw/fe17/romfs/art-cache (git-ignored); rerun when the renderer or the art changes.

    python scripts/fe17_lit_fills.py              # every map
    python scripts/fe17_lit_fills.py fe17-m000    # some (the others kept)
"""
import colorsys
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fe17_data as D  # noqa: E402
import fe17_ground as G  # noqa: E402
import fe17_render as R  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe17-lit-fills.json')
CACHE = os.path.join(HERE, '..', 'data-raw', 'fe17', 'romfs', 'art-cache')
PX = 16
# The ground, walls and water have colours of their own (the codes the photos' colours cover too: an icon's tile, a building's pieces
# and the effects laid over tiles are drawn as themselves); lava and fire glow in the game (not lit so here), and the app draws them
# dim anyway (the user).
KINDS = ('t', 'g', 'w')
LEFT_OUT = ('wp',)
WATER = ('we', 'wl', 'tg', 'wk', 'wm', 'tf', 'tj', 'to')
# The render's brightest surfaces are its least sure (the shader's toon ramp isn't modelled): held to the photos' brightest ground
# (Chapter 24's road, 0.78 lightness).
TOP = 0.78


def held(rgb):
    h, lum, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    return [v * 255 for v in colorsys.hls_to_rgb(h, min(lum, TOP), s)]


def lit(field, window):
    path = os.path.join(CACHE, f"lit-{field}-{'-'.join(map(str, window))}-{PX}.npy")
    if os.path.exists(path):
        return np.load(path)
    fl = R.Field(field, window, PX)
    img = (np.clip(R.shade(fl.inputs(), R.settings(fl.sc)), 0, 1) * 255).astype(np.uint8)   # row 0 the south
    os.makedirs(CACHE, exist_ok=True)
    np.save(path, img)
    return img


def fills(m, img):
    W, H = m['width'], m['height']
    code = lambda x, y: m['grid'][H - y][2 * (x - 1):2 * x] if 1 <= x <= W and 1 <= y <= H else None  # noqa: E731
    k = int(PX * 0.22)
    per = {}
    for y in range(1, H + 1):
        for x in range(1, W + 1):
            c = code(x, y)
            if not c or c[0] not in KINDS or c in LEFT_OUT:
                continue
            t = img[(y - 1) * PX + k:y * PX - k, (x - 1) * PX + k:x * PX - k].reshape(-1, 3).astype(np.float32)
            if not len(t) or not t.any():
                continue
            if c not in WATER:
                lum = t.sum(1)
                lo, hi = np.percentile(lum, [35, 95])
                keep = (lum >= lo) & (lum <= hi)
                t = t[keep] if keep.any() else t
            inner = all(code(x + i, y + j) == c for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            per.setdefault(c, ([], []))[0 if inner else 1].append(np.median(t, axis=0))
    out = {}
    for c, (inner, edge) in sorted(per.items()):
        cs = inner if len(inner) >= 3 else inner + edge
        if len(cs) < 2:
            continue
        rgb = held(np.median(np.array(cs), axis=0))
        # water only where it's blue (hue 180-250): a dark lake whose base colour is tinted by its grading (Fell Xenologue 6's purple)
        # keeps the app's blue, as builder's separate() keeps a scene's grey or white water
        if c in WATER and not 180 <= colorsys.rgb_to_hsv(*(v / 255 for v in rgb))[0] * 360 <= 250:
            continue
        out[c] = '#%02x%02x%02x' % tuple(int(round(v)) for v in rgb)
    return out


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    chapters = {r['Cid']: r for r in D.rows('chapter')}
    for map_id, m in G.app_maps().items():
        if (only and map_id not in only) or not m['grid']:
            continue
        field, window = G.field_and_window(map_id, chapters)
        if not os.path.exists(os.path.join(R.fe17_art.ART, f'fe_scenes_fld_{field}.bundle')):
            print(map_id, 'no scene for', field)
            continue
        table[map_id] = fills(m, lit(field, window))
        print(map_id, field, table[map_id], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])
