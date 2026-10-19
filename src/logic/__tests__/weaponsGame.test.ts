import { describe, expect, it } from 'vitest'
import { ALL_WEAPONS } from '../../data/weapons'
import { GAME_ITEMS } from '../../data/weapons/gameItems'
import { effectivenessIcons } from '../../icons/weaponIcons'

/** The icon labels, as the game's effectiveness names. */
const TARGET: Record<string, string> = {
  'armoured units': 'armour', dragons: 'dragon', fliers: 'flying', 'mounted and beast units': 'beast', monsters: 'monster',
  'sword users': 'sword', 'lance users': 'lance', 'axe users': 'axe', 'tome users': 'tome',
}

describe("weapons match the game's own item data", () => {
  for (const w of ALL_WEAPONS) {
    it(w.name, () => {
      const g = GAME_ITEMS[w.name]
      expect(g, 'in the game item table').toBeDefined()
      const range = g.range[0] === g.range[1] ? `${g.range[0]}` : `${g.range[0]}~${g.range[1]}`
      const staff = w.category === 'Staff' || w.category === 'Rod'
      // A staff's 'Mt' in the game is how much it heals; the app shows staves without Might.
      if (!staff) expect(w.stats.mt, 'mt').toBe(g.mt)
      expect([w.stats.hit, w.stats.crit, w.stats.avoid, w.stats.dodge], 'hit, crit, avoid, dodge').toEqual([g.hit, g.crit, g.avoid, g.dodge])
      // Bifröst's range in the game is 0 (it reaches every ally); the app writes 1.
      if (w.name !== 'Bifröst') expect(w.stats.range, 'range').toBe(range)
      expect(w.rank, 'rank').toBe(g.rank)
      if (w.purchase) expect([w.purchase.buy, w.purchase.sell ?? g.sell], 'buy, sell').toEqual([g.buy, g.sell])
      else expect(g.buy, 'sold in a shop').toBe(0)
      if (g.uses) expect(w.stats.uses, 'uses').toBe(g.uses)
      const ours = w.effectiveness ? effectivenessIcons(w.effectiveness.vs).map((t) => TARGET[t.label]) : []
      expect(ours.sort(), 'effective against').toEqual([...g.effective].sort())
      expect(!!w.effectiveness?.nonEffectivePenalty, 'penalty against everything else').toBe(g.weakVsOthers)
    })
  }
})

describe('My Castle rank rewards', () => {
  it('name only weapons the list has (or items that aren\'t weapons)', async () => {
    const { RANK_REWARDS } = await import('../../data/weapons/rankRewards')
    for (const r of RANK_REWARDS) {
      for (const name of [r.battle, r.visit]) {
        if (GAME_ITEMS[name]) expect(ALL_WEAPONS.some((w) => w.name === name), name).toBe(true)
      }
    }
  })

  it('gives the Dual Club at 160 Visit Points', () => {
    expect(ALL_WEAPONS.find((w) => w.name === 'Dual Club')!.rankRewards).toEqual([{ track: 'Visit Points', points: 160 }])
  })
})

describe('special rules read from the game text', () => {
  it('finds every weapon that strikes twice', () => {
    expect(ALL_WEAPONS.filter((w) => w.strikesTwice).map((w) => w.name).sort()).toEqual(
      ['Brave Axe', 'Brave Lance', 'Brave Sword', 'Crescent Bow', 'Lightning', 'Snake Spirit', "Soldier's Knife"].sort(),
    )
  })
  it('finds every weapon whose Mt doubles', () => {
    expect(ALL_WEAPONS.filter((w) => w.mightBoost).map((w) => w.name).sort()).toEqual(
      ['Venge Katana', 'Venge Naginata', 'Venge Club', "Hana's Katana", 'Ink Painting', "Hinata's Katana", "Izana's Scroll", "Subaki's Pike"].sort(),
    )
  })
})
