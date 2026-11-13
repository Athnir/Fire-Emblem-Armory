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
