import { describe, expect, it } from 'vitest'
import { FE10_TRIANGLE } from '../../data/fe10/fe10Triangle'
import { FE4_BONUSES } from '../../data/fe4/fe4Bonuses'
import { FE9_TRIANGLE } from '../../data/fe9/fe9Triangle'
import { FATES_TRIANGLE } from '../../data/weapons/fatesTriangle'
import type { TriangleRules } from '../triangle'
import { triangleOutcome } from '../triangle'

const base = { outside: '', rules: [], mtLabel: 'Mt' }

describe('weapon triangle data, read from each game', () => {
  it('Path of Radiance: sword > axe > lance > sword and fire > wind > thunder > fire, ±10 hit and ±1 Mt (main.dol)', () => {
    expect(FE9_TRIANGLE.beats).toEqual({ Sword: ['Axe'], Lance: ['Sword'], Axe: ['Lance'], Fire: ['Wind'], Thunder: ['Fire'], Wind: ['Thunder'] })
    expect([FE9_TRIANGLE.hit, FE9_TRIANGLE.mt]).toEqual([10, 1])
  })

  it('Radiant Dawn: the trinity of magic on top (3SukumiData), ±10 hit, ±1 Mt, leadership 5 a star', () => {
    expect(FE10_TRIANGLE.beats.Light).toEqual(['Dark'])
    expect(FE10_TRIANGLE.beats.Dark).toEqual(['Fire', 'Thunder', 'Wind'])
    expect(FE10_TRIANGLE.beats.Fire).toEqual(['Wind', 'Light'])
    expect([FE10_TRIANGLE.hit, FE10_TRIANGLE.mt, FE10_TRIANGLE.leadershipPerStar]).toEqual([10, 1, 5])
  })

  it('Fates: swords and tomes beat axes and bows, and so on round; the bonus grows with the advantaged rank (GameData.bin)', () => {
    expect(FATES_TRIANGLE.beats['Sword / Katana']).toEqual(['Axe / Club', 'Bow / Yumi'])
    expect(FATES_TRIANGLE.beats['Axe / Club']).toEqual(['Lance / Naginata', 'Dagger / Shuriken'])
    expect(FATES_TRIANGLE.beats['Lance / Naginata']).toEqual(['Sword / Katana', 'Tome / Scroll'])
    expect(FATES_TRIANGLE.advantage).toEqual({ E: [0, 5], D: [0, 5], C: [0, 10], B: [1, 10], A: [1, 15], S: [2, 20] })
    // Swords add Atk at each rank from C (and hit at S); axes lean on hit.
    expect(FATES_TRIANGLE.rankBonus['Sword / Katana']).toMatchObject({ C: [1, 0], B: [2, 0], A: [3, 0], S: [4, 5] })
    expect(FATES_TRIANGLE.rankBonus['Axe / Club']).toMatchObject({ C: [0, 5], B: [0, 10], A: [1, 10], S: [2, 15] })
  })
})

describe('triangleOutcome', () => {
  const tellius: TriangleRules = { ...base, beats: FE9_TRIANGLE.beats, advantage: [{ hit: 10, mt: 1 }], loser: 'mirror', offOn: 'Hard mode' }

  it('mirrors the bonus onto the other side', () => {
    const o = triangleOutcome(tellius, 'Sword', 'Axe')
    expect([o.level, o.you, o.foe]).toEqual([1, { hit: 10, mt: 1 }, { hit: -10, mt: -1 }])
    expect(triangleOutcome(tellius, 'Sword', 'Lance').you).toEqual({ hit: -10, mt: -1 })
    expect(triangleOutcome(tellius, 'Sword', 'Bow').level).toBe(0)
  })

  it("turns off on Radiant Dawn's Hard mode", () => {
    expect(triangleOutcome(tellius, 'Sword', 'Axe', { off: true }).you).toEqual({ hit: 0, mt: 0 })
  })

  it('gives FE4 only the winner +20 hit and avoid', () => {
    const fe4: TriangleRules = { ...base, beats: FE4_BONUSES.beats, advantage: [{ hit: 20, avoid: 20 }], loser: 'winner-only' }
    expect(triangleOutcome(fe4, 'Light', 'Fire').you).toEqual({ hit: 20, avoid: 20 })
    expect(triangleOutcome(fe4, 'Light', 'Fire').foe).toEqual({ hit: 0, avoid: 0 })
  })

  it("scales Fates' by rank, doubles and flips it with one reaver, and costs the loser its rank bonus", () => {
    const fates: TriangleRules = {
      ...base,
      beats: FATES_TRIANGLE.beats,
      advantage: Object.entries(FATES_TRIANGLE.advantage).map(([rank, [mt, hit]]) => ({ rank, mt, hit })),
      loser: 'mirror',
      reaver: true,
      rankBonus: { rows: [], rules: [] },
    }
    const sword = 'Sword / Katana'
    const axe = 'Axe / Club'
    expect(triangleOutcome(fates, sword, axe, { rank: 'S' }).you).toEqual({ hit: 20, mt: 2 })
    expect(triangleOutcome(fates, sword, axe, { rank: 'E' }).foe).toEqual({ hit: -5, mt: -0 })
    const reaver = triangleOutcome(fates, sword, axe, { rank: 'B', foeReaver: true })
    expect([reaver.level, reaver.you, reaver.youLoseRankBonus]).toEqual([-2, { hit: -20, mt: -2 }, true])
    expect(triangleOutcome(fates, sword, axe, { rank: 'B', yourReaver: true, foeReaver: true }).level).toBe(1)
  })
})
