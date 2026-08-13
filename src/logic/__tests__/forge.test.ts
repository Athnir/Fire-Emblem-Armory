import { describe, expect, it } from 'vitest'
import {
  copiesRequiredFromScratch,
  cumulativeForgeBonus,
  discountedMineralCost,
  mineralsRequiredFromScratch,
} from '../forge'

describe('forge', () => {
  it('matches Serenes Forest\'s worked +7 example (128 copies, 247 minerals)', () => {
    expect(copiesRequiredFromScratch(7)).toBe(128)
    expect(mineralsRequiredFromScratch(false, 7)).toBe(247)
  })

  it('sums non-crit bonuses to +11 Mt / +30 Hit at rank 7', () => {
    expect(cumulativeForgeBonus(false, 7)).toEqual({ mt: 11, hit: 30, crit: 0 })
  })

  it('sums crit-capable bonuses to +11 Mt / +20 Hit / +15 Crit at rank 7', () => {
    expect(cumulativeForgeBonus(true, 7)).toEqual({ mt: 11, hit: 20, crit: 15 })
  })

  it('rank 0 has no bonus', () => {
    expect(cumulativeForgeBonus(true, 0)).toEqual({ mt: 0, hit: 0, crit: 0 })
  })

  it('proficient-Smith discount is -1 per combine, floored at 1', () => {
    expect(discountedMineralCost(1, true)).toBe(1)
    expect(discountedMineralCost(2, true)).toBe(1)
    expect(discountedMineralCost(7, true)).toBe(6)
    expect(discountedMineralCost(7, false)).toBe(7)
  })

  it('discount reduces the from-scratch total but never costs more than the undiscounted total', () => {
    const full = mineralsRequiredFromScratch(false, 7)
    const discounted = mineralsRequiredFromScratch(false, 7, true)
    expect(discounted).toBeLessThan(full)
    // Per-combine costs floor(1, k-1) for k=1..7 -> 1,1,2,3,4,5,6, weighted by 2^(7-k):
    // 64 + 32 + 32 + 24 + 16 + 10 + 6 = 184
    expect(discounted).toBe(184)
  })
})
