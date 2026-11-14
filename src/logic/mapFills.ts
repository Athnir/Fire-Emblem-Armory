import type { TerrainCode } from '../data/maps/terrainCodes'

type Fills = Partial<Record<TerrainCode, string>>

/** The lightness (HSL) the darkest of a map's colours is lifted to: a dark grey or brown that still shows on the dark page. */
export const DARKEST_FILL = 0.22
/** Colours darker than this are lifted into DARKEST_FILL to DARK_FILL, in order; lighter ones are left as they are. */
export const DARK_FILL = 0.3
/** A wall's colour darker than this is the void beyond the map, drawn as VOID. */
const VOID_FILL = 0.06
const VOID = '#0b0b0e'

function toHsl(hex: string): [number, number, number] {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4
  return [h / 6, s, l]
}

function toHex(h: number, s: number, l: number): string {
  const hue = (p: number, q: number, t: number) => {
    const u = t < 0 ? t + 1 : t > 1 ? t - 1 : t
    return u < 1 / 6 ? p + (q - p) * 6 * u : u < 1 / 2 ? q : u < 2 / 3 ? p + (q - p) * (2 / 3 - u) * 6 : p
  }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  const rgb = s === 0 ? [l, l, l] : [hue(p, q, h + 1 / 3), hue(p, q, h), hue(p, q, h - 1 / 3)]
  return `#${rgb.map((v) => Math.round(v * 255).toString(16).padStart(2, '0')).join('')}`
}

const lifted = new WeakMap<Fills, Fills>()

/**
 * A map's own colours as drawn: a colour too dark to see on the dark page (a night map's, Revelation's dark castles, Awakening's
 * Chapter 1) is lifted to a dark grey or brown, never near black (the user's call): every colour darker than DARK_FILL is mapped into
 * DARKEST_FILL to DARK_FILL in order, so a map's walls stay darker than its floors, and lighter colours are left alone. Hue and
 * saturation are kept.
 */
export function visibleFills(fills: Fills | undefined): Fills {
  if (!fills) return {}
  const done = lifted.get(fills)
  if (done) return done
  const hsl = Object.entries(fills).map(([code, hex]) => [code, hex!, toHsl(hex!)] as const)
  let out: Fills = fills
  if (hsl.some(([, , [, , l]]) => l < DARK_FILL)) {
    out = {}
    for (const [code, hex, [h, s, l]] of hsl)
      out[code as TerrainCode] =
        // A wall all but black is the void beyond the map: black, not lifted to a dark blue (the user's call, Fates' Endgames).
        code[0] === 'w' && l < VOID_FILL ? VOID
          : l < DARK_FILL ? toHex(h, s, DARKEST_FILL + (l * (DARK_FILL - DARKEST_FILL)) / DARK_FILL) : hex
  }
  lifted.set(fills, out)
  return out
}

/** A colour's HSL lightness (0-1). */
export const lightness = (hex: string) => toHsl(hex)[2]
