/**
 * The map page's colour-blind friendly look (its switch; the user's call, 2026-11-26). Every pair of armies' markers stays apart under
 * simulated protanopia, deuteranopia and tritanopia (Machado, Oliveira and Fernandes 2009, at full severity, in linear RGB): by its shape,
 * its edge's lightness or its body's colour. The usual markers don't (a red and a green figure under deuteranopia), which is why the
 * switch exists. The look is off by default, so the map page draws as it did (the watched maps' fingerprints hold that).
 */
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ColourBlindContext } from '../../components/ColourBlind'
import { MapGrid } from '../../components/MapViewer'
import { FE7_MAP_SET } from '../../data/fe7/fe7MapSet'
import { FE9_MAP_SET } from '../../data/fe9/fe9MapSet'
import type { MapSet } from '../../data/maps/mapSet'
import { ALLY, COLOUR_BLIND, NAMED_ENEMY, SKULL, type Sprite } from '../../icons/sprites'

type Kind = 'protanopia' | 'deuteranopia' | 'tritanopia'
const MACHADO: Record<Kind, number[][]> = {
  protanopia: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deuteranopia: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
  tritanopia: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
}
const KINDS = Object.keys(MACHADO) as Kind[]

/** A colour as someone with that colour blindness sees it, in CIE Lab. */
function seen(hex: string, kind: Kind): [number, number, number] {
  const lin = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const [r, g, b] = MACHADO[kind].map((row) => Math.min(1, Math.max(0, row[0] * lin[0] + row[1] * lin[1] + row[2] * lin[2])))
  const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116)
  const fx = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047)
  const fy = f(0.2126 * r + 0.7152 * g + 0.0722 * b)
  const fz = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)]
}

const body = (s: Sprite) => s.palette.b ?? s.palette.r ?? s.palette.w
/** Two markers read apart: a shape of their own, an edge clearly lighter or darker, or a body clearly another colour. */
function apart(a: Sprite, b: Sprite, kind: Kind) {
  if (a.rows.join() !== b.rows.join()) return true
  if (Math.abs(seen(a.palette.o, kind)[0] - seen(b.palette.o, kind)[0]) >= 40) return true
  const [p, q] = [seen(body(a), kind), seen(body(b), kind)]
  return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) >= 30
}

const MARKERS: Record<string, Sprite> = {
  'common foe': COLOUR_BLIND.commonEnemy,
  'paired foes': COLOUR_BLIND.commonPair,
  'named foe': COLOUR_BLIND.namedEnemy,
  boss: SKULL,
  'green unit': COLOUR_BLIND.commonAlly,
  'named green unit': COLOUR_BLIND.ally,
  'partner unit': COLOUR_BLIND.commonPartner,
  'named partner unit': COLOUR_BLIND.partner,
  'unit joining you': COLOUR_BLIND.joiner,
  reinforcement: COLOUR_BLIND.reinforcement,
  'named foe arriving': COLOUR_BLIND.namedReinforcement,
  'boss arriving': COLOUR_BLIND.bossReinforcement,
}

describe('the colour-blind friendly look', () => {
  it('keeps every pair of armies apart under each kind of colour blindness', () => {
    const together: string[] = []
    const names = Object.keys(MARKERS)
    for (const [i, a] of names.entries())
      for (const b of names.slice(i + 1)) for (const kind of KINDS) if (!apart(MARKERS[a], MARKERS[b], kind)) together.push(`${a} and ${b} (${kind})`)
    expect(together).toEqual([])
  })

  it('is needed: the usual red and green figures run together under deuteranopia', () => {
    expect(apart(NAMED_ENEMY, ALLY, 'deuteranopia')).toBe(false)
  })

  it('gives each kind of generic marker a shape of its own', () => {
    const generic = [COLOUR_BLIND.commonEnemy, COLOUR_BLIND.commonPair, COLOUR_BLIND.commonAlly, COLOUR_BLIND.commonPartner, COLOUR_BLIND.reinforcement]
    expect(new Set(generic.map((s) => s.rows.join())).size).toBe(generic.length)
  })

  // The Blazing Blade's Eliwood 16 (green units, named and nameless, named foes, a boss, the lord's start); Path of Radiance's Ch.9
  // (partner units, a forced unit's fixed tile).
  const drawn = (set: MapSet, id: string, cb?: boolean) => {
    const map = set.maps.find((m) => m.id === id)!
    const grid = (
      <MapGrid map={map} difficulty={set.difficulties[0].value} selected={null} radius={new Set()} potsBroken={false} previewing={new Set()}
        arrivals={[]} triggers={[]} onSelect={() => {}} />
    )
    return renderToStaticMarkup(cb === undefined ? grid : <ColourBlindContext.Provider value={cb}>{grid}</ColourBlindContext.Provider>)
  }

  it('is off unless switched on', () => {
    expect(drawn(FE7_MAP_SET, 'fe7-e-16', false)).toBe(drawn(FE7_MAP_SET, 'fe7-e-16'))
  })

  it('draws the armies and the starting tiles its own way when on', () => {
    const [usual, cb] = [drawn(FE7_MAP_SET, 'fe7-e-16'), drawn(FE7_MAP_SET, 'fe7-e-16', true)]
    // The foes vermillion, the green units bluish green (the nameless ones diamonds edged in white), none of the usual red or green left.
    expect(cb).toContain('fill="#d55e00"')
    expect(cb).toContain('fill="#009e73"')
    expect(cb).toContain('fill="#f5f5f5"')
    expect(usual).toContain('fill="#d9443b"')
    expect(cb).not.toContain('fill="#d9443b"')
    expect(cb).not.toContain('fill="#3fa35a"')
    // The lord's start has all four corners; the usual look marks two.
    expect(cb).toContain('h-3l3 3z')
    expect(usual).not.toContain('h-3l3 3z')
    // Partner units yellow triangles, a forced unit's tile its corners on the other diagonal in reddish purple.
    const [usual9, cb9] = [drawn(FE9_MAP_SET, 'fe9-9'), drawn(FE9_MAP_SET, 'fe9-9', true)]
    expect(cb9).toContain('fill="#f0e442"')
    expect(cb9).not.toContain('fill="#e2b93b"')
    expect(usual9).toContain('fill="#f472b6"')
    expect(cb9).toContain('fill="#cc79a7"')
  })
})
