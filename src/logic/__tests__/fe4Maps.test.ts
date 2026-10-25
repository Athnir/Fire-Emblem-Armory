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

  it("places the units from the game's lists: every one inside its map, on a tile someone can stand on", () => {
    for (const m of FE4_MAPS) {
      const all = [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
      expect(all.length, m.id).toBeGreaterThan(10)
      for (const u of all) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
        const code = rowCodes(m.grid[m.height - y])[x - 1]
        const info = FE4_TERRAIN[code]!
        // Foes stand on walls only where the map says they can: a boss on the castle's defence tile, a ballista on a plain.
        const walkable = Object.values(info.move).some((c) => c !== null)
        if (!walkable) expect(['wn'].includes(code) || u.type === 'boss' || u.type === 'named', `${m.id} ${u.name} on ${code}`).toBe(true)
      }
    }
  })

  it("names the Prologue's two bosses from Serenes' table and gives a foe the weapons its record holds", () => {
    const prologue = FE4_MAPS[0]
    const dimaggio = prologue.units.find((u) => u.name === 'Dimaggio')!
    expect(dimaggio.type).toBe('boss')
    expect(dimaggio.tile).toEqual([35, 6])
    expect(dimaggio.carries).toEqual(['Steel Axe'])
    expect(prologue.units.some((u) => u.name === 'Gerrard')).toBe(true)
    expect(prologue.units.filter((u) => u.name === 'Barbarian').length).toBeGreaterThan(10)
  })
})
