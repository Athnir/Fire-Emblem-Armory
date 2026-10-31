import { describe, expect, it } from 'vitest'
import { FE11_ITEM_SOURCES } from '../../data/fe11/fe11ItemSources'
import { FE11_LISTED } from '../../data/fe11/fe11Listed'
import { FE11_MAPS } from '../../data/fe11/fe11Maps'
import { FE11_STORY } from '../../data/fe11/fe11MapSet'
import { FE11_WEAPONS } from '../../data/fe11/fe11Weapons'

const map = (id: string) => FE11_MAPS.find((m) => m.id === id)!
const weapon = (name: string) => FE11_WEAPONS.find((w) => w.name === name)!

/** Fire Emblem Wiki's Shadow Dragon chapter pages: [columns, rows, enemies at the start (Normal)]. */
const WIKI: Record<string, [number, number, number]> = {
  'fe11-p1': [14, 21, 0], 'fe11-p2': [17, 15, 6], 'fe11-p3': [26, 17, 10], 'fe11-p4': [19, 30, 9],
  'fe11-1': [30, 13, 14], 'fe11-2': [30, 13, 17], 'fe11-3': [30, 20, 15], 'fe11-4': [30, 20, 20], 'fe11-5': [30, 20, 18],
  'fe11-6': [30, 21, 25], 'fe11-6x': [30, 16, 18], 'fe11-7': [14, 28, 16], 'fe11-8': [30, 28, 20], 'fe11-9': [30, 28, 18],
  'fe11-10': [30, 28, 20], 'fe11-11': [30, 23, 20], 'fe11-12': [30, 28, 19], 'fe11-12x': [20, 30, 19], 'fe11-13': [30, 23, 17],
  'fe11-14': [30, 28, 22], 'fe11-15': [30, 28, 19], 'fe11-16': [30, 30, 20], 'fe11-17': [30, 30, 19], 'fe11-17x': [26, 26, 28],
  'fe11-18': [30, 28, 22], 'fe11-19': [14, 28, 20], 'fe11-20': [30, 28, 19], 'fe11-20x': [30, 30, 23], 'fe11-21': [30, 28, 20],
  'fe11-22': [30, 28, 20], 'fe11-23': [30, 28, 21], 'fe11-24': [30, 28, 20], 'fe11-24x': [22, 30, 31], 'fe11-final': [30, 28, 27],
}
/** Where the game's files and the wiki's infobox disagree: Chapter 8's infobox says 20 foes, but its own unit list has the 19 the
 * placement file places. */
const EXCEPTIONS: Record<string, number> = { 'fe11-8': 19 }

describe("Shadow Dragon's maps", () => {
  it('has the Prologue, Chapters 1-24 with each gaiden chapter where it comes, and the Endgame', () => {
    expect(FE11_STORY.maps.map((m) => m.id)).toEqual([
      'fe11-p1', 'fe11-p2', 'fe11-p3', 'fe11-p4', 'fe11-1', 'fe11-2', 'fe11-3', 'fe11-4', 'fe11-5', 'fe11-6', 'fe11-6x', 'fe11-7',
      'fe11-8', 'fe11-9', 'fe11-10', 'fe11-11', 'fe11-12', 'fe11-12x', 'fe11-13', 'fe11-14', 'fe11-15', 'fe11-16', 'fe11-17',
      'fe11-17x', 'fe11-18', 'fe11-19', 'fe11-20', 'fe11-20x', 'fe11-21', 'fe11-22', 'fe11-23', 'fe11-24', 'fe11-24x', 'fe11-final',
    ])
  })

  it("is each chapter's size on the wiki (the files' grids less their border) with the foes it lists", () => {
    for (const [id, [cols, rows, foes]] of Object.entries(WIKI)) {
      const m = map(id)
      expect([id, m.width, m.height]).toEqual([id, cols, rows])
      expect(m.grid).toHaveLength(rows)
      expect(m.grid.every((r) => r.length === cols * 2)).toBe(true)
      expect([id, m.units.filter((u) => u.type !== 'ally').length]).toEqual([id, EXCEPTIONS[id] ?? foes])
    }
  })

  it('places every unit inside its map', () => {
    for (const m of FE11_MAPS) {
      const all = [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
      for (const u of all) {
        expect(u.tile[0] >= 1 && u.tile[0] <= m.width && u.tile[1] >= 1 && u.tile[1] <= m.height, `${m.id} ${u.name}`).toBe(true)
      }
    }
  })

  it("reads the talks that recruit, the gaiden chapters' conditions and the reinforcements' turns", () => {
    expect(map('fe11-2').units.find((u) => u.name === 'Castor')?.talk).toBe('Recruit: talk with Caeda')
    expect(map('fe11-4').units.find((u) => u.name === 'Matthis')?.talk).toBe('Recruit: talk with Lena')
    expect(map('fe11-20').units.find((u) => u.name === 'Lorenz')?.talk).toBe('Recruit: talk with Caeda or Marth')
    expect(map('fe11-6x').notes).toContain('Opens if 15 or fewer of your units are alive at the end of Chapter 6.')
    expect(map('fe11-24x').notes[0]).toMatch(/neither the Falchion nor Tiki/)
    // Chapter 9's reinforcements come on turns 6, 8 and 10.
    expect(map('fe11-9').reinforcements![0].when).toMatch(/^Turns 6, 8 and 10/)
    // Wrys walks out of Chapter 1's village.
    expect(map('fe11-1').joiners?.map((j) => j.name)).toEqual(['Wrys'])
  })
})

describe("Shadow Dragon's weapons", () => {
  it('reads the item table: prices are uses times the price per use, ranks from the weapon experience they need', () => {
    expect(weapon('Iron Sword')).toMatchObject({ mt: 5, hit: 100, crit: 0, wt: 4, uses: 40, worth: 400, rank: 'E' })
    expect(weapon('Silv. Sword')).toMatchObject({ mt: 12, rank: 'B', worth: 2000 })
    expect(weapon('Mercurius').rank).toBe('A')
    expect(weapon('Rapier')).toMatchObject({ effective: ['armour', 'horseback'], rules: ['Marth only'] })
    expect(weapon('Wyrmslayer').effective).toEqual(['fe11-dragons'])
    expect(weapon('Falchion').effective).toEqual(['fe11-dragons-all'])
    expect(weapon('Brv. Sword').rules).toContain('Strikes twice in a row')
  })

  it('lists where each weapon turns up', () => {
    expect(FE11_ITEM_SOURCES['Iron Sword']).toContainEqual({ mapId: 'fe11-1', kind: 'shop', text: 'Sold at the armory' })
    expect(FE11_LISTED.some((w) => w.name === 'Rapier')).toBe(true)
  })
})
