import { describe, expect, it } from 'vitest'
import { copiesRequiredFromScratch, cumulativeForgeBonus, mineralsRequiredFromScratch } from '../forge'

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
})
