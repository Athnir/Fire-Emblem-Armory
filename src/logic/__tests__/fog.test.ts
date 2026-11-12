import { describe, expect, it } from 'vitest'
import { FE5_MAPS } from '../../data/fe5/fe5Maps'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { inTheFog, tileKey } from '../maps'

describe('fog under the spoiler block', () => {
  it("leaves a fog map's foes off but keeps its ground and allies (the user's call)", () => {
    const m = FE8_MAPS.find((x) => x.id === 'fe8-6')!
    expect(m.fog).toBe(true)
    expect(m.units.some((u) => u.type !== 'ally')).toBe(true)
    const { units, unseen } = inTheFog(m)
    expect(units.every((u) => u.type === 'ally')).toBe(true)
    expect(units).toHaveLength(m.units.filter((u) => u.type === 'ally').length)
    expect(unseen).toBeUndefined()
    // A map without fog keeps everyone.
    const clear = FE8_MAPS.find((x) => x.id === 'fe8-5')!
    expect(inTheFog(clear).units).toBe(clear.units)
  })

  it("draws Thracia 776's fog black beyond its vision from the starting tiles, in steps ($80:E626)", () => {
    const fogged = FE5_MAPS.filter((x) => x.fog)
    expect(fogged.map((x) => x.id)).toEqual(['fe5-2x', 'fe5-4x', 'fe5-8x', 'fe5-11x', 'fe5-12', 'fe5-12x', 'fe5-14x', 'fe5-24x'])
    for (const m of fogged) expect(m.blackFog, m.id).toBe(3)
    const m = FE5_MAPS.find((x) => x.id === 'fe5-2x')!
    const { units, unseen } = inTheFog(m)
    expect(units.every((u) => u.type === 'ally')).toBe(true)
    // Every starting tile, and every tile 3 steps from one, is seen; one 4 steps from all of them isn't.
    for (const t of m.starts) expect(unseen!.has(tileKey(t))).toBe(false)
    const [sx, sy] = m.starts[0]
    expect(unseen!.has(tileKey([sx, sy + 3])) && sy + 3 <= m.height).toBe(false)
    const far = (x: number, y: number) => m.starts.every((s) => Math.abs(s[0] - x) + Math.abs(s[1] - y) > 3)
    let hidden = 0
    for (let x = 1; x <= m.width; x++) for (let y = 1; y <= m.height; y++) if (far(x, y)) hidden++
    expect(unseen!.size).toBe(hidden)
    expect(unseen!.size).toBeGreaterThan((m.width * m.height) / 2)
  })
})
