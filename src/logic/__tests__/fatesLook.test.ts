import { describe, expect, it } from 'vitest'
import { ALL_MAPS } from '../../data/maps'
import { FATES_TERRAIN } from '../../data/maps/fatesTerrain'
import { rowCodes } from '../maps'

const map = (id: string) => ALL_MAPS.find((m) => m.id === id)!
const codes = (id: string) => map(id).grid.flatMap(rowCodes)

// scripts/fates_ground.py renders each field from above (scripts/fates_art.py) into data-raw/fates-ground.json, which
// scripts/build-fates-terrain.py applies.
describe("Fates' maps as its 3D fields draw them", () => {
  it('gives each map its own colours, its challenge too', () => {
    for (const m of ALL_MAPS) expect(m.fills, m.id).toBeDefined()
    expect(map('fe14b-6-challenge').fills).toEqual(map('fe14b-6').fills)
  })

  it("parts its plains' dirt from their grass, and floors from plains, all working alike", () => {
    expect(codes('fe14b-6').filter((c) => c === 'ga').length).toBeGreaterThan(50) // Birthright 6's paths
    expect(codes('fe14r-24').filter((c) => c === 't1').length).toBeGreaterThan(400) // the castle's floors (床)
    expect(codes('fe14r-24')).not.toContain('ta')
    for (const c of ['ga', 't1'] as const) expect(FATES_TERRAIN[c]!.move, c).toEqual(FATES_TERRAIN.ta!.move)
  })

  it("keeps the app's blue for water the render doesn't draw blue", () => {
    for (const m of ALL_MAPS)
      for (const c of ['tf', 'we', 'wm'] as const) {
        const hex = m.fills?.[c]
        if (!hex) continue
        const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
        expect(b, `${m.id} ${c}`).toBeGreaterThanOrEqual(Math.max(r, g))
      }
  })
})

// The review of every map (2026-11-14): Fates' houses, statues and challenge villages.
describe("Fates' buildings drawn as its art shows them", () => {
  const at = (id: string, x: number, y: number) => rowCodes(map(id).grid[map(id).height - y])[x - 1]
  it('draws a building block as a house over its tiles, the village before it its door mat, with the building numbers', () => {
    // Birthright 13's houses: three by two, each with its village below the middle of its front.
    expect([at('fe14b-13', 8, 11), at('fe14b-13', 9, 11), at('fe14b-13', 10, 11), at('fe14b-13', 8, 10), at('fe14b-13', 9, 10), at('fe14b-13', 10, 10)])
      .toEqual(['ra', 'rb', 'rc', 'rg', 'rh', 'ri'])
    expect(at('fe14b-13', 9, 9)).toBe('oc')
    expect(map('fe14b-13').terrainOverrides?.ra?.move).toEqual(map('fe14b-13').terrainOverrides?.wa?.move ?? FATES_TERRAIN.wa!.move)
  })

  it("draws Birthright 21's walls standing alone two by two as its statues", () => {
    expect(Object.values(map('fe14b-21').decor ?? {}).filter((d) => d === 'statue')).toHaveLength(12)
  })

  it("has a challenge's spent villages in ruins: the house and the village before it", () => {
    const ruins = map('fe14b-13-challenge').ruins ?? []
    expect(ruins).toContain('9,9')
    expect(ruins).toContain('9,10')
    expect(map('fe14b-13').ruins).toBeUndefined()
  })
})
