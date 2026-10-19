import { describe, expect, it } from 'vitest'
import { FE9_WEAPONS } from '../../data/fe9/fe9Weapons'

const w = (name: string) => FE9_WEAPONS.find((x) => x.name === name)!

describe("Path of Radiance weapons from the game's item table", () => {
  it('reads stats, uses and worth', () => {
    expect(w('Iron Sword')).toMatchObject({ rank: 'E', mt: 5, hit: 90, crit: 0, wt: 7, range: '1', uses: 46, worth: 460, wex: 1 })
    expect(w('Killing Edge')).toMatchObject({ rank: 'C', mt: 9, hit: 75, crit: 30, wt: 9 })
  })

  it('reads effectiveness, rules and stat bonuses', () => {
    expect(w('Armorslayer').effective).toEqual(['armour'])
    expect(w('Brave Sword').flags).toContain('twice')
    expect(w('Ragnell')).toMatchObject({ rank: 'Prf', range: '1-2', uses: null, stats: { def: 5 } })
    expect(w('Double Bow').stats).toEqual({ str: 3 })
    expect(w('Physic').range).toBe('1-Mag/2')
  })

  it('leaves out cut and codes-only weapons', () => {
    for (const name of ['Warp', 'Berserk', 'Unlock', 'Devil Axe', 'Urvan', 'Bright Bow']) expect(FE9_WEAPONS.some((x) => x.name === name), name).toBe(false)
  })

  it('has unique ids', () => {
    expect(new Set(FE9_WEAPONS.map((x) => x.id)).size).toBe(FE9_WEAPONS.length)
  })
})
