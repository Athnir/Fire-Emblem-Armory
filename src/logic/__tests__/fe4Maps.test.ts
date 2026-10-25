import { describe, expect, it } from 'vitest'
import { FE4_MAPS } from '../../data/fe4/fe4Maps'
import { FE4_MOVE_CLASSES, FE4_TERRAIN } from '../../data/fe4/fe4Terrain'
import { rowCodes } from '../maps'

describe("Genealogy of the Holy War's maps", () => {
  it('has the twelve chapters in order, the Prologue 64 x 32 and the rest 64 x 64', () => {
    expect(FE4_MAPS.map((m) => m.heading)).toEqual(['Prologue', 'Ch.1', 'Ch.2', 'Ch.3', 'Ch.4', 'Ch.5', 'Ch.6', 'Ch.7', 'Ch.8', 'Ch.9', 'Ch.10', 'Final'])
    for (const m of FE4_MAPS) {
      expect([m.width, m.height], m.id).toEqual([64, m.id === 'fe4-prologue' ? 32 : 64])
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it('gives every tile a terrain the table knows, with a cost for every movement type', () => {
    for (const m of FE4_MAPS) {
      for (const row of m.grid) {
        for (const code of rowCodes(row)) {
          const info = FE4_TERRAIN[code]
          expect(info, `${m.id} ${code}`).toBeDefined()
          for (const mc of FE4_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
        }
      }
    }
  })

  it("reads the terrain as the game does: villages, a castle and Serenes' avoid values", () => {
    const prologue = FE4_MAPS[0]
    const codes = new Set(prologue.grid.flatMap((r) => rowCodes(r)))
    expect(codes.has('oc')).toBe(true)
    expect(codes.has('wn')).toBe(true)
    expect(FE4_TERRAIN.oc!.avo).toBe(20)
    expect(FE4_TERRAIN.ba!.avo).toBe(20)
    expect(FE4_TERRAIN.bt!.avo).toBe(40)
    expect(FE4_TERRAIN.bm!.avo).toBe(30)
    expect(FE4_TERRAIN.we!.avo).toBe(-30)
    // Only pirates wade the sea; fliers cross anything but walls.
    expect(FE4_TERRAIN.we!.move['Pirates']).toBe(5)
    expect(FE4_TERRAIN.we!.move['Knights']).toBeNull()
    expect(FE4_TERRAIN.wb!.move['Fliers']).toBe(1)
  })
})
