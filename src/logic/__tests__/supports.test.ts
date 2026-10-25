import { describe, expect, it } from 'vitest'
import { FE9_AFFINITIES, fe9SupportBonus } from '../../data/supports/fe9Supports'
import { FE10_AFFINITIES, FE10_PAIR_OFFSETS, FE10_SUPPORT_ACTIONS, FE10_SUPPORT_TOTALS, fe10SupportBonus } from '../../data/supports/fe10Supports'
import { GAMES } from '../../games'
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

describe('Radiant Dawn supports', () => {
  const rd = (n: string) => FE10_AFFINITIES.find((a) => a.name === n)!
  it('adds both affinities, times the level, with a half rounded up', () => {
    // Fire + Thunder at C: Atk 0.5 and Def 0.5 round up to 1 each (Path of Radiance gives 0).
    expect(fe10SupportBonus(rd('Fire'), rd('Thunder'), 1)).toEqual({ atk: 1, def: 1, hit: 3, avoid: 3 })
    // Heaven is Hit +9 and Earth Avoid +7.5 a level here.
    expect(fe10SupportBonus(rd('Heaven'), rd('Earth'), 3)).toEqual({ atk: 0, def: 0, hit: 27, avoid: 23 })
    expect(fe10SupportBonus(rd('Heaven'), rd('Heaven'), 3).hit).toBe(54)
  })

  it("follows the game's support point table (RelianceParam)", () => {
    expect(FE10_SUPPORT_TOTALS).toEqual([50, 100, 150])
    // The fastest kind of pair: Serenes Forest's type 00 row.
    expect(FE10_SUPPORT_ACTIONS.map((a) => a.points + FE10_PAIR_OFFSETS[0])).toEqual([3, 5, 6, 7, 17])
    expect(FE10_SUPPORT_ACTIONS.map((a) => a.points + FE10_PAIR_OFFSETS[4])).toEqual([-1, 1, 2, 3, 13])
  })

  it('is in the game list with its own hit system, supports, weapons and maps', async () => {
    const fe10 = GAMES.find((g) => g.id === 'fe10')!
    expect(fe10).toMatchObject({ title: 'Fire Emblem: Radiant Dawn', hitSystem: '2rn' })
    const parts = await fe10.load()
    expect(parts.supports).toBeDefined()
    expect(parts.weapons).toBeDefined()
    expect(parts.maps).toBeDefined()
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

  it('lists only classes a partner can be in (no enemy-only classes)', () => {
    for (const enemyOnly of ['Lancer', 'Lord', 'Cleric', 'Faceless', 'Stoneborn', 'Automaton', 'Feral Dragon', 'Name']) {
      expect(FATES_CLASS_PAIR_UP, enemyOnly).not.toHaveProperty(enemyOnly)
    }
  })
})
