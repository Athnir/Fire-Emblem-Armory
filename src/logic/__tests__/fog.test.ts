import { describe, expect, it } from 'vitest'
import { FE10_MAPS } from '../../data/fe10/fe10Maps'
import { FE17_MAPS } from '../../data/fe17/fe17Maps'
import { FE5_MAPS } from '../../data/fe5/fe5Maps'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE9_MAPS } from '../../data/fe9/fe9Maps'
import type { ChapterMap } from '../../data/maps/types'
import { inTheFog, startingSight, tileKey, tilesInRadius } from '../maps'

const seeds = (m: ChapterMap) => [...m.starts, ...(m.corrinStart ? [m.corrinStart] : []), ...(m.forced ?? []).flatMap((f) => (f.tile ? [f.tile] : []))]

describe('fog: a foe shows only where your army sees it at the start (the user\'s call)', () => {
  it("hides the foes beyond the army's sight from its starting tiles, and keeps its allies", () => {
    const m = FE8_MAPS.find((x) => x.id === 'fe8-6')!
    expect(m.fog).toBe(true)
    expect(m.vision).toBe(3)
    const { units, seen } = inTheFog(m)
    const near = (t: [number, number]) => seeds(m).some((s) => Math.abs(s[0] - t[0]) + Math.abs(s[1] - t[1]) <= m.vision!)
    for (const u of m.units) expect(units.includes(u), `${u.name} ${u.tile}`).toBe(u.type === 'ally' || near(u.tile))
    expect(units.length).toBeLessThan(m.units.length)
    for (const s of seeds(m)) expect(seen!.has(tileKey(s))).toBe(true)
    // A map without fog keeps everyone.
    const clear = FE8_MAPS.find((x) => x.id === 'fe8-5')!
    expect(inTheFog(clear).units).toBe(clear.units)
  })

  it('shows what a lit torch lights (Radiant Dawn Part 2 Ch.2)', () => {
    const m = FE10_MAPS.find((x) => x.id === 'fe10-2-2')!
    const dark = inTheFog(m)
    const torch = m.changes.find((c) => c.trigger === 'torch' && c.tile.default[0] === 19 && c.tile.default[1] === 5)!
    const light = new Set(tilesInRadius(m, torch.tile.default, torch.radius!).map(tileKey))
    const lit = inTheFog(m, light)
    expect(lit.units.length).toBeGreaterThan(dark.units.length)
    for (const u of lit.units.filter((u) => !dark.units.includes(u))) expect(light.has(tileKey(u.tile))).toBe(true)
  })

  it('gives every map fogged at the start its sight: the chapter record\'s in the GBA games, 3 in Tellius and Engage', () => {
    const atStart = (m: ChapterMap) => (m.fog || m.fogOn) && !m.notes.some((n) => n.startsWith('Fog of war from'))
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS, ...FE9_MAPS, ...FE10_MAPS, ...FE17_MAPS].filter(atStart))
      expect(m.vision ?? null, m.id).not.toBeNull()
    // Radiant Dawn's fog maps without torches are fog maps too (Part 1 Ch.9, Part 3's Prologue).
    expect(FE10_MAPS.filter((m) => m.fog).map((m) => m.id)).toEqual(['fe10-1-9', 'fe10-2-2', 'fe10-3-prologue', 'fe10-3-1', 'fe10-4-1'])
    expect(FE6_MAPS.find((m) => m.id === 'fe6-14')!.vision).toBe(4)
    // A fog a later turn brings hides no one at the start (Lyn's Chapter 9, from turn 3).
    const later = FE7_MAPS.find((m) => m.id === 'fe7-lyn-9')!
    expect(later.fog).toBe(true)
    expect(startingSight(later)).toBeNull()
    expect(inTheFog(later).units).toBe(later.units)
  })

  it("draws Thracia 776's fog black beyond its vision from the starting tiles, in steps ($80:E626), under the spoiler block", () => {
    const fogged = FE5_MAPS.filter((x) => x.fog)
    expect(fogged.map((x) => x.id)).toEqual(['fe5-2x', 'fe5-4x', 'fe5-8x', 'fe5-11x', 'fe5-12', 'fe5-12x', 'fe5-14x', 'fe5-24x'])
    for (const m of fogged) expect(m.blackFog, m.id).toBe(3)
    const m = FE5_MAPS.find((x) => x.id === 'fe5-2x')!
    expect(inTheFog(m).unseen).toBeUndefined()
    const { units, unseen } = inTheFog(m, new Set(), true)
    for (const u of units) expect(unseen!.has(tileKey(u.tile))).toBe(false)
    // Every starting tile, and every tile 3 steps from one, is seen; one 4 steps from all of them isn't.
    for (const t of m.starts) expect(unseen!.has(tileKey(t))).toBe(false)
    const [sx, sy] = m.starts[0]
    expect(unseen!.has(tileKey([sx, sy + 3])) && sy + 3 <= m.height).toBe(false)
    const far = (x: number, y: number) => seeds(m).every((s) => Math.abs(s[0] - x) + Math.abs(s[1] - y) > 3)
    let hidden = 0
    for (let x = 1; x <= m.width; x++) for (let y = 1; y <= m.height; y++) if (far(x, y)) hidden++
    expect(unseen!.size).toBe(hidden)
    expect(unseen!.size).toBeGreaterThan((m.width * m.height) / 2)
  })
})
