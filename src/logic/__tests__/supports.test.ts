import { describe, expect, it } from 'vitest'
import { FE9_AFFINITIES, fe9SupportBonus } from '../../data/supports/fe9Supports'
import { FATES_CLASS_PAIR_UP, FATES_PAIR_UP, FATES_TAG_TEAM } from '../../data/supports/fatesSupports'

const aff = (n: string) => FE9_AFFINITIES.find((a) => a.name === n)!

describe('Path of Radiance supports', () => {
  it('adds both affinities per level and rounds down', () => {
    expect(fe9SupportBonus(aff('Fire'), aff('Fire'), 3)).toEqual({ atk: 3, def: 0, hit: 15, avoid: 0 })
    // Fire + Thunder at C: 0.5 Atk and 0.5 Def round down to nothing; 2.5 Hit and Avoid round to 2.
    expect(fe9SupportBonus(aff('Fire'), aff('Thunder'), 1)).toEqual({ atk: 0, def: 0, hit: 2, avoid: 2 })
    expect(fe9SupportBonus(aff('Earth'), aff('Earth'), 3)).toEqual({ atk: 0, def: 0, hit: 0, avoid: 30 })
  })
})

describe('Fates support data', () => {
  it('gives every character five Tag Team levels starting at Hit +10, and four Pair Up levels', () => {
    for (const [name, levels] of Object.entries(FATES_TAG_TEAM)) {
      expect(levels, name).toHaveLength(5)
      expect(levels[0], name).toEqual({ hit: 10 })
    }
    for (const [name, levels] of Object.entries(FATES_PAIR_UP)) expect(levels, name).toHaveLength(4)
    expect(Object.keys(FATES_TAG_TEAM).sort()).toEqual(Object.keys(FATES_PAIR_UP).sort())
  })

  it('has class Pair Up stats', () => {
    expect(FATES_CLASS_PAIR_UP['Samurai']).toEqual({ spd: 4, lck: 2 })
  })
})
