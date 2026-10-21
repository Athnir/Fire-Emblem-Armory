import { describe, expect, it } from 'vitest'
import { FE10_FORGE_CARDS, FE10_WEAPONS } from '../../data/fe10/fe10Weapons'
import { fe10CanLower, fe10ForgeCost, fe10ForgedStats, NO_CHANGE } from '../fe10Forge'

const w = (name: string) => FE10_WEAPONS.find((x) => x.name === name)!

describe("Radiant Dawn's forge", () => {
  it("charges steps² × a tenth of the price for each stat (Serenes Forest's worked example)", () => {
    // A Silver Sword (1800G) with +5 Mt, +15 Crit and -2 Wt costs 11,520G.
    expect(fe10ForgeCost(w('Silver Sword'), { mt: 5, hit: 0, crit: 5, wt: -2 })).toBe(11520)
    expect(fe10ForgeCost(w('Iron Sword'), NO_CHANGE)).toBe(500)
    // Down costs the same as up.
    expect(fe10ForgeCost(w('Iron Sword'), { mt: -2, hit: 0, crit: 0, wt: 0 })).toBe(fe10ForgeCost(w('Iron Sword'), { mt: 2, hit: 0, crit: 0, wt: 0 }))
  })

  it('keeps forged stats at 1 or more (Crit at 0 or more), and stops lowering a stat at 1', () => {
    expect(fe10ForgedStats(w('Iron Sword'), { mt: 5, hit: -5, crit: 5, wt: -5 })).toEqual({ mt: 11, hit: 65, crit: 15, wt: 2 })
    expect(fe10CanLower(w('Iron Sword'), NO_CHANGE, 'crit')).toBe(false)
    expect(fe10CanLower(w('Iron Sword'), { mt: -5, hit: 0, crit: 0, wt: 0 }, 'mt')).toBe(false)
    expect(fe10CanLower(w('Iron Sword'), { mt: 0, hit: 0, crit: 0, wt: -5 }, 'wt')).toBe(false)
  })

  it('offers the base weapons the forge grid names, and the Coin cards add up to 100%', () => {
    expect(w('Iron Sword').forge!.normal).toMatch(/^Part 1: Ch\.4/)
    expect(w('Silver Sword').forge!.normal).toMatch(/^Part 4/)
    expect(w('Fire').forge).toBeDefined()
    expect(w('Killing Edge').forge).toBeUndefined()
    expect(FE10_FORGE_CARDS.reduce((n, c) => n + c.chance, 0)).toBe(100)
    expect(FE10_FORGE_CARDS.find((c) => c.name === 'Goddess')).toMatchObject({ mt: 1, hit: 10, crit: 5, chance: 1 })
  })
})
