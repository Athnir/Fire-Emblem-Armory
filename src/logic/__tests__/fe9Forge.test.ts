import { describe, expect, it } from 'vitest'
import { FE9_WEAPONS } from '../../data/fe9/fe9Weapons'
import { fe9ForgeCost, fe9ForgedStats, fe9ForgeMaxSteps, NO_FORGE } from '../fe9Forge'

const w = (name: string) => FE9_WEAPONS.find((x) => x.name === name)!

// Serenes Forest's FE9 forging costs: the extra gold for taking each stat to its limit on its own.
// Two Wt entries differ from Serenes by one digit (Slim Lance 855G, Iron Axe 614G); the game's formula,
// which matches the other 78, gives 885G and 619G, so those are used here.
const EXTRA: [string, number, number, number, number][] = [
  ['Iron Sword', 3450, 727, 3001, 831],
  ['Slim Sword', 8555, 787, 2184, 691],
  ['Steel Sword', 2871, 1361, 4567, 1952],
  ['Silver Sword', 4299, 3387, 12234, 4720],
  ['Iron Lance', 1744, 650, 2349, 700],
  ['Slim Lance', 5332, 885, 2047, 885],
  ['Steel Lance', 1750, 1178, 3654, 1750],
  ['Silver Lance', 2916, 2916, 9787, 4183],
  ['Javelin', 2951, 1258, 3262, 1258],
  ['Iron Axe', 1107, 525, 1761, 619],
  ['Steel Axe', 1171, 963, 2740, 1722],
  ['Silver Axe', 2258, 2630, 8156, 4436],
  ['Hand Axe', 1817, 1045, 2446, 1171],
  ['Iron Bow', 3187, 910, 3523, 666],
  ['Steel Bow', 2981, 1767, 5481, 1767],
  ['Silver Bow', 4585, 3888, 13050, 3373],
  ['Fire', 8555, 833, 3654, 294],
  ['Thunder', 6093, 1012, 2340, 315],
  ['Wind', 14625, 731, 3393, 0],
  ['Light', 22500, 1445, 5220, 681],
]

describe("Path of Radiance's forge", () => {
  it('offers the 20 base weapons the game lists', () => {
    expect(FE9_WEAPONS.filter((x) => x.forge).map((x) => x.name).sort()).toEqual(EXTRA.map((e) => e[0]).sort())
  })

  it("matches Serenes Forest's cost for each stat at its limit", () => {
    for (const [name, mt, hit, crit, wt] of EXTRA) {
      const weapon = w(name)
      const max = fe9ForgeMaxSteps(weapon)
      const extra = (s: Partial<typeof max>) => fe9ForgeCost(weapon, { ...NO_FORGE, ...s }) - weapon.worth
      expect([extra({ mt: max.mt }), extra({ hit: max.hit }), extra({ crit: max.crit }), extra({ wt: max.wt })], name).toEqual([mt, hit, crit, wt])
    }
  })

  it('charges just the price with nothing forged, and rounds the total once', () => {
    expect(fe9ForgeCost(w('Iron Sword'), NO_FORGE)).toBe(460)
    // Each stat alone rounds down (3450 + 727); together the fractions add up before rounding.
    const all = fe9ForgeCost(w('Iron Sword'), { mt: 5, hit: 5, crit: 0, wt: 0 })
    expect(all - 460).toBeGreaterThanOrEqual(3450 + 727)
    expect(all - 460).toBeLessThanOrEqual(3450 + 727 + 1)
  })

  it('stops Wt at 1 and works out the forged stats', () => {
    expect(fe9ForgeMaxSteps(w('Wind')).wt).toBe(0)
    expect(fe9ForgeMaxSteps(w('Iron Bow')).wt).toBe(4)
    expect(fe9ForgedStats(w('Iron Sword'), { mt: 5, hit: 5, crit: 3, wt: 5 })).toEqual({ mt: 10, hit: 115, crit: 9, wt: 2 })
  })

  it('knows which chapters offer each base weapon, by difficulty', () => {
    expect(w('Silver Sword').forge).toEqual({ normal: 'Ch.18 onward', hard: 'Ch.23 onward' })
    expect(w('Steel Axe').forge).toEqual({ normal: 'Ch.8–9, Ch.11 onward', hard: 'Ch.14 onward' })
  })
})
