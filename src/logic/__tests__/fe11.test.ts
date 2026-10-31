import { describe, expect, it } from 'vitest'
import { FE11_ITEM_SOURCES } from '../../data/fe11/fe11ItemSources'
import { FE11_LISTED } from '../../data/fe11/fe11Listed'
import { FE11_MAPS } from '../../data/fe11/fe11Maps'
import { FE11_STORY } from '../../data/fe11/fe11MapSet'
import { FE11_WEAPONS } from '../../data/fe11/fe11Weapons'
import { GAMES } from '../../games'
import { fe11ForgeCost, fe11ForgeRange, fe11ForgeStatCost } from '../fe11Forge'

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
    expect(map('fe11-24x').notes.some((n) => /neither the Falchion nor Tiki/.test(n))).toBe(true)
    // Chapter 9's reinforcements come on turns 6, 8 and 10.
    expect(map('fe11-9').reinforcements![0].when).toMatch(/^Turns 6, 8 and 10/)
    // Wrys walks out of Chapter 1's village.
    expect(map('fe11-1').joiners?.map((j) => j.name)).toEqual(['Wrys'])
  })
})

describe("Shadow Dragon's Hard modes", () => {
  const note = (id: string, name: string, lv: string) => map(id).units.find((u) => u.name === name && u.note?.startsWith(lv))?.note
  it("names the weapons each mode gives a foe, as Fire Emblem Wiki's mode tabs list them", () => {
    // Chapter 10's boss, Zharov (tier 2): Merciless lifts Steel to Silver and forges the special weapons; a dropped item in the first slot keeps a
    // copy that still drops (Chapter 12's mage: Elfire, and the Thunder it drops).
    expect(note('fe11-10', 'Zharov', 'Lv 3')).toBe(
      'Lv 3 General: Javelin, Steel Lance, Speedwing (Merciless: Javelin (forged: Mt +4, Hit +20), Silv. Lance, Speedwing)',
    )
    expect(map('fe11-12').units.some((u) => /Savage, Fiendish: Elfire, Thunder/.test(u.note ?? ''))).toBe(true)
  })

  it('says what each mode adds, and that the prologue is Normal only', () => {
    expect(map('fe11-1').notes[0]).toMatch(/^Hard modes: foes the game levels gain 3 levels' worth of growth/)
    expect(map('fe11-24').notes[0]).toMatch(/gain 4 levels' worth/)
    expect(map('fe11-p1').notes[0]).toMatch(/^Played on Normal only/)
    // On the Hard modes Chapter 1's army joins in Chapter 1.
    expect(FE11_ITEM_SOURCES['Rapier']).toContainEqual({ mapId: 'fe11-1', kind: 'kit', text: 'Carried by Marth on joining' })
  })

  it("keeps Gharnef's doubles' false copies off the weapon page", () => {
    expect(map('fe11-23').units.filter((u) => u.name === 'Gharnef' && u.carries?.includes('Imhullu (false)'))).toHaveLength(2)
    expect(FE11_ITEM_SOURCES['Falchion (false)']).toBeUndefined()
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

describe("Shadow Dragon's battle numbers", () => {
  it('rolls hit with two numbers averaged (overlay 00 at 0x21c92c4: two 0-99 rolls, added and halved, below the hit lands)', () => {
    expect(GAMES.find((g) => g.id === 'fe11')?.hitSystem).toBe('2rn')
  })

  it("prices the forge as its menu does, matching Serenes Forest's worked example", () => {
    // A Silv. Sword (2,000G) with Mt +10, Crit +30 and Wt -4: (110,000 + 110,000 + 20,000 + 2,000) / 2.
    expect(weapon('Silv. Sword').worth).toBe(2000)
    expect(fe11ForgeCost(2000, { mt: 10, crit: 30, wt: -4 })).toBe(121000)
    // Nothing changed still costs half the price; a part step costs its share of the next (Hit +7: one step and 2/5 of the second).
    expect(fe11ForgeCost(400, {})).toBe(200)
    expect(fe11ForgeStatCost(400, 'hit', 7)).toBe(400 + Math.floor((2 * (1200 - 400)) / 5))
    // The limits: Mt +10 to at most 30, Hit +50 to at most 200, Crit +30 to at most 50, Wt 10 either way between 1 and 30.
    expect(fe11ForgeRange('mt', 12)).toEqual([12, 22])
    expect(fe11ForgeRange('hit', 160)).toEqual([160, 200])
    expect(fe11ForgeRange('crit', 30)).toEqual([30, 50])
    expect(fe11ForgeRange('wt', 5)).toEqual([1, 15])
  })
})
