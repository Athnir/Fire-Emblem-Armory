import { describe, expect, it } from 'vitest'
import { ALL_MAPS } from '../../data/maps'
import { FATES_JOINS } from '../../data/maps/fatesJoins'
import { FATES_FORK } from '../../data/maps/fatesStory'
import { ALL_WEAPONS } from '../../data/weapons'
import { FATES_BUILDING_CHAPTERS, FATES_SHOPS } from '../../data/weapons/fatesShops'
import { buildingLevel, firstChapter, giftFrom, hiddenByDefault, isCastleItem, isDlcItem, isRewardItem, maxForge, smithyLevel, stockedNow, whereLines } from '../fatesWeapons'
import type { FatesChapter } from '../fatesWeapons'
import { reachOf } from '../spoiler'

type Route = 'Birthright' | 'Conquest' | 'Revelation'
const story = (route: Route) => FATES_FORK.choices.find((c) => c.id === route)!.story
/** The weapon list as it stands on `chapter` of a route. */
const on = (route: Route, chapter: number): FatesChapter => ({ story: story(route), at: story(route).maps.findIndex((m) => m.chapter === chapter), route })
const weapon = (name: string) => ALL_WEAPONS.find((w) => w.name === name)!
const listed = (route: Route, chapter: number) => {
  const c = on(route, chapter)
  return new Set(ALL_WEAPONS.filter((w) => firstChapter(w, c) <= c.at).map((w) => w.name))
}

describe("Fates' route choice", () => {
  it('walks the five shared chapters, then one route', () => {
    expect(FATES_FORK.before.maps.map((m) => m.chapter)).toEqual([1, 2, 3, 4, 5])
    for (const route of ['Birthright', 'Conquest', 'Revelation'] as const) {
      const maps = story(route).maps
      expect(maps.slice(0, 5)).toEqual(FATES_FORK.before.maps)
      expect(maps.slice(5).every((m) => m.route === route)).toBe(true)
      expect(maps[5].chapter).toBe(6)
    }
  })

  it("never reaches another route's chapters, and keeps the shared ones", () => {
    const r = reachOf(story('Birthright'), story('Birthright').maps.length - 1, 'Birthright')
    expect(ALL_MAPS.filter((m) => m.route === 'Conquest' || m.route === 'Revelation').some((m) => r.has(m.id))).toBe(false)
    expect(ALL_MAPS.filter((m) => m.route === 'Birthright' || m.route === 'Shared').every((m) => r.has(m.id))).toBe(true)
  })

  it('opens the DLC after Chapter 6 and the paralogues by chapter, only on the routes that reach them', () => {
    const dlc = ALL_MAPS.find((m) => m.route === 'DLC')!
    const at = (route: Route, chapter: number) => reachOf(story(route), on(route, chapter).at, route)
    expect(at('Birthright', 6).has(dlc.id)).toBe(false)
    expect(at('Birthright', 7).has(dlc.id)).toBe(true)
    const mozu = ALL_MAPS.find((m) => m.route === 'Paralogue' && m.chapter === 1)!
    expect(at('Conquest', 8).has(mozu.id)).toBe(false)
    expect(at('Conquest', 9).has(mozu.id)).toBe(true)
    // Paralogue 7 is Ryoma's child, so it follows Ryoma joining for good: Birthright 13, so the paralogue opens in 14.
    const hoshido = ALL_MAPS.find((m) => m.route === 'Paralogue' && m.chapter === 7)!
    expect(at('Birthright', 13).has(hoshido.id)).toBe(false)
    expect(at('Birthright', 14).has(hoshido.id)).toBe(true)
    expect(at('Conquest', 27).has(hoshido.id)).toBe(false)
  })

  it("opens a child's paralogue the chapter after their fixed parent joins for good", () => {
    const para = (n: number) => ALL_MAPS.find((m) => m.route === 'Paralogue' && m.chapter === n)!
    const at = (route: Route, chapter: number) => reachOf(story(route), on(route, chapter).at, route)
    // Soleil's father Laslow joins in Conquest 12, so her paralogue is Chapter 13.
    expect(at('Conquest', 12).has(para(21).id)).toBe(false)
    expect(at('Conquest', 13).has(para(21).id)).toBe(true)
    // Shigure follows his mother Azura (Conquest 9), not his father: Chapter 10.
    expect(at('Conquest', 9).has(para(3).id)).toBe(false)
    expect(at('Conquest', 10).has(para(3).id)).toBe(true)
    // Azura is with you from Birthright 5, but nothing opens before the castle: Chapter 7.
    expect(at('Birthright', 6).has(para(3).id)).toBe(false)
    expect(at('Birthright', 7).has(para(3).id)).toBe(true)
    // Revelation has its own join chapters: Laslow joins in 17.
    expect(at('Revelation', 17).has(para(21).id)).toBe(false)
    expect(at('Revelation', 18).has(para(21).id)).toBe(true)
    // Jakob's son waits for the later of his two dates.
    expect(at('Birthright', 15).has(para(4).id)).toBe(false)
    expect(at('Birthright', 16).has(para(4).id)).toBe(true)
  })
})

describe('the join chapters', () => {
  it("read from the game's chapter files agree with Serenes Forest's recruitment pages for every fixed parent", () => {
    // Serenes Forest's Hoshidan, Nohrian and Revelation recruitment pages: the chapter each parent joins for good.
    const serenes: Record<Route, Record<string, number>> = {
    Birthright: { Azura: 5, Silas: 7, Kaze: 4, Ryoma: 13, Takumi: 10, Saizo: 7, Kaden: 12, Hinata: 9, Azama: 8, Subaki: 7, Hayato: 8 },
    Conquest: { Azura: 9, Silas: 7, Kaze: 11, Xander: 16, Leo: 14, Benny: 13, Keaton: 14, Arthur: 7, Odin: 8, Laslow: 12, Niles: 8 },
    Revelation: { Azura: 5, Silas: 14, Kaze: 8, Ryoma: 16, Takumi: 10, Saizo: 11, Kaden: 13, Hinata: 10, Azama: 16, Subaki: 8, Hayato: 9, Xander: 17, Leo: 17, Benny: 14, Keaton: 13, Arthur: 14, Odin: 17, Laslow: 17, Niles: 17 },
    }
    expect(FATES_JOINS).toEqual(serenes)
  })
})

describe('My Castle buildings by chapter', () => {
  it('opens each level once its chapter is completed, so on the chapter after', () => {
    const level = (building: string, chapter: number) => buildingLevel(building, on('Birthright', chapter))
    expect([6, 7, 13, 14, 20, 21].map((n) => level('Dawn Armoury', n))).toEqual([0, 1, 1, 2, 2, 3])
    expect([8, 9, 14, 15, 20, 21].map((n) => level('Smithy', n))).toEqual([0, 1, 1, 2, 2, 3])
    expect(FATES_BUILDING_CHAPTERS.Smithy).toEqual([8, 14, 20])
  })

  it('forges up to +2, then +4, then +7, and not at all before the Smithy', () => {
    expect([8, 9, 14, 15, 21].map((n) => maxForge(on('Conquest', n)))).toEqual([0, 2, 2, 4, 7])
    expect(smithyLevel(on('Conquest', 8))).toBe(0)
  })

  it("sells what a shop stocks at the level it's on, and says when it's limited", () => {
    const katana = weapon('Steel Katana')
    expect(stockedNow(katana, on('Birthright', 6))).toBeUndefined()
    expect(stockedNow(katana, on('Birthright', 7))).toMatchObject({ shop: 'Dawn Armoury', level: 1, stock: 1 })
    expect(stockedNow(katana, on('Birthright', 14))).toMatchObject({ level: 2, stock: null })
    const venge = weapon('Venge Katana')
    expect(stockedNow(venge, on('Birthright', 20))).toBeUndefined()
    expect(stockedNow(venge, on('Birthright', 21))).toMatchObject({ level: 3, stock: 1 })
    // Conquest has no Dawn Armoury.
    expect(stockedNow(katana, on('Conquest', 21))).toBeUndefined()
    expect(stockedNow(weapon('Steel Sword'), on('Conquest', 14))).toMatchObject({ shop: 'Dusk Armoury', stock: null })
  })

  it("lists a shop weapon from the first level that stocks it and doesn't hint at later ones", () => {
    const silver = weapon('Silver Katana')
    const c = on('Birthright', 13)
    expect(listed('Birthright', 13).has('Silver Katana') && !isCastleItem(silver)).toBe(false)
    expect(firstChapter(silver, c)).toBeGreaterThan(c.at)
    expect(whereLines(silver, on('Birthright', 9))).toEqual([])
  })
})

describe('the weapon list under the block', () => {
  it("starts with what your own units hold: Corrin's sword in Chapter 1, then Gunter's, Felicia's and Jakob's inventories", () => {
    const player = (route: Route, chapter: number) => [...listed(route, chapter)].filter((n) => !weapon(n).foeOnly)
    expect(player('Birthright', 1)).toEqual(['Bronze Sword'])
    expect(player('Conquest', 2)).toEqual(expect.arrayContaining(['Bronze Sword', 'Ganglari', 'Iron Lance', 'Iron Dagger', 'Heal']))
    expect(player('Revelation', 2)).toHaveLength(5)
    // The Faceless carry their fists on the Chapter 4 map.
    expect(listed('Birthright', 4).has('Shackled Fist')).toBe(true)
  })

  it("gives Corrin's Yato only from the chapter the game puts it in his hands", () => {
    for (const [route, chapter] of [['Birthright', 6], ['Conquest', 6], ['Revelation', 13]] as const) {
      expect(listed(route, chapter - 1).has('Yato'), `${route} before ${chapter}`).toBe(false)
      expect(listed(route, chapter).has('Yato'), `${route} from ${chapter}`).toBe(true)
    }
  })

  it("gives My Castle's ally items from the chapter after Chapter 6, as static items", () => {
    const treasure = ALL_WEAPONS.find((w) => w.availability.source.includes('My Castle: Treasure') && w.availability.routes.includes('Birthright'))!
    expect(listed('Birthright', 6).has(treasure.name)).toBe(false)
    expect(listed('Birthright', 7).has(treasure.name)).toBe(true)
    // Nothing is said about where a static castle item comes from: the My Castle badge on its page is enough.
    expect(whereLines(treasure, on('Birthright', 7))).toEqual([])
  })

  it("keeps Yato's true forms for the chapters that give them, each on its own route", () => {
    const forms: [string, Route, number][] = [
      ['Noble Yato', 'Birthright', 20],
      ['Blazing Yato', 'Birthright', 27],
      ['Grim Yato', 'Conquest', 15],
      ['Shadow Yato', 'Conquest', 27],
      ['Alpha Yato', 'Revelation', 16],
      ['Omega Yato', 'Revelation', 27],
    ]
    for (const [name, route, chapter] of forms) {
      expect(listed(route, chapter - 1).has(name), `${name} before`).toBe(false)
      expect(listed(route, chapter).has(name), `${name} from ${chapter}`).toBe(true)
      expect(giftFrom(weapon(name), route)).toBe(chapter)
    }
    expect(listed('Conquest', 27).has('Blazing Yato')).toBe(false)
    expect(listed('Birthright', 27).has('Grim Yato')).toBe(false)
  })

  it("keeps the other nation's weapons out", () => {
    expect(listed('Conquest', 27).has('Brass Katana')).toBe(false)
    expect(listed('Birthright', 27).has('Bronze Axe')).toBe(false)
    expect(listed('Revelation', 27).has('Brass Katana') && listed('Revelation', 27).has('Bronze Axe')).toBe(true)
  })

  it('never lists a weapon a chapter before the story could give it', () => {
    for (const route of ['Birthright', 'Conquest', 'Revelation'] as const) {
      let previous = 0
      for (let at = 0; at < story(route).maps.length; at++) {
        const c = { story: story(route), at, route }
        const n = ALL_WEAPONS.filter((w) => firstChapter(w, c) <= at).length
        expect(n).toBeGreaterThanOrEqual(previous)
        previous = n
      }
    }
  })
})

describe("weapons only foes carry", () => {
  const foeOnly = ALL_WEAPONS.filter((w) => w.foeOnly)

  it("lists the item table's weapons that no list of the player's has, none of them sold, forged or gifted", () => {
    expect(foeOnly).toHaveLength(33)
    // Lilith's weapons and the dragon-form attack aren't a foe's.
    expect(ALL_WEAPONS.some((w) => ['Draconic Rage', 'Astral Breath', 'Astral Blessing'].includes(w.name))).toBe(false)
    expect(foeOnly.map((w) => w.name)).toEqual(expect.arrayContaining(['Steel Kukri', 'Silver Javelin', 'Bölverk', 'Skadi', 'Dark Breath', 'Rock', 'Big Saw']))
    for (const w of foeOnly) {
      expect(w.purchase, w.name).toBeUndefined()
      expect(w.forgeable, w.name).toBe(false)
      expect(FATES_SHOPS[w.name], w.name).toBeUndefined()
      expect(isCastleItem(w) || giftFrom(w, 'Revelation') !== undefined, w.name).toBe(false)
    }
  })

  it("places each from the first chapter whose map shows a foe carrying it at the start, and keeps it after", () => {
    // Rinkah carries a Steel Mace in Conquest 11: not before, listed from then on.
    expect(listed('Conquest', 10).has('Steel Mace')).toBe(false)
    expect(listed('Conquest', 11).has('Steel Mace')).toBe(true)
    expect(listed('Conquest', 20).has('Steel Mace')).toBe(true)
    // Fuga's Silver Katti is in Conquest 20, and Takumi's Skadi only on the Endgame map.
    expect(listed('Conquest', 19).has('Silver Katti')).toBe(false)
    expect(listed('Conquest', 20).has('Silver Katti')).toBe(true)
    expect(listed('Conquest', 27).has('Skadi')).toBe(false)
    expect(listed('Conquest', 28).has('Skadi')).toBe(true)
  })

  it("keeps the other routes' foes out", () => {
    expect(listed('Birthright', 28).has('Skadi')).toBe(false)
    expect(listed('Revelation', 28).has('Dark Breath')).toBe(false)
  })

  it('lists what a reinforcement carries from the chapter after it arrives', () => {
    // Iron Nageyari is only on the Visitors who arrive mid-chapter in a DLC map, which opens after Chapter 6.
    expect(listed('Revelation', 7).has('Iron Nageyari')).toBe(false)
    expect(listed('Revelation', 8).has('Iron Nageyari')).toBe(true)
    const nageyari = weapon('Iron Nageyari')
    expect(nageyari.mapSources!.every((s) => s.arrives)).toBe(true)
    // The weapon page names the source only once that chapter is over.
    expect(firstChapter(nageyari, on('Revelation', 8))).toBe(on('Revelation', 8).at)
  })

  it("opens the DLC maps' foes with the Dragon's Gate, after Chapter 6", () => {
    expect(listed('Birthright', 6).has('Rock')).toBe(false)
    expect(listed('Birthright', 7).has('Rock')).toBe(true)
  })

  it('says where each one is carried, from the placement files', () => {
    const mace = weapon('Steel Mace')
    expect(mace.mapSources!.some((s) => s.how.startsWith('Carried by Rinkah'))).toBe(true)
    expect(mace.availability.routes).toEqual(['Conquest'])
  })
})

describe('what the weapon list leaves out until asked', () => {
  it("leaves the Battle Points and Visit Points rewards off, unless a weapon has another source (Heal is Felicia's)", () => {
    const raider = weapon('Raider Axe')
    expect(isRewardItem(raider)).toBe(true)
    expect(isRewardItem(weapon('Raider Katana'))).toBe(true)
    // The Dual Club has a Conquest village too, so it isn't a reward only.
    expect(isRewardItem(weapon('Dual Club'))).toBe(false)
    expect(isRewardItem(weapon('Heal'))).toBe(false)
    // With rewards off the castle doesn't bring them in at Chapter 7; with them on it does.
    const c = on('Conquest', 7)
    expect(firstChapter(raider, c)).toBe(Infinity)
    expect(firstChapter(raider, c, true)).toBe(c.at)
    expect(listed('Conquest', 28).has('Raider Axe')).toBe(false)
  })

  it('leaves the DLC items and what only the DLC maps carry off', () => {
    const dlc = ALL_WEAPONS.filter(isDlcItem)
    expect(dlc.length).toBeGreaterThan(0)
    expect(dlc.every((w) => hiddenByDefault(w))).toBe(true)
    expect(isDlcItem(weapon('Steel Sword'))).toBe(false)
    // Rock is carried on the Chapter 7+ DLC maps and by the Faceless in the story chapters: not DLC-only.
    expect(isDlcItem(weapon('Shackled Fist'))).toBe(false)
  })
})

describe('the shop tables', () => {
  it("cover every weapon the app says a shop sells, at the app's price", () => {
    // The amiibo shopkeepers' items are sold at any level by a visiting shopkeeper, not stocked.
    const visiting = new Set(["Marth's Spatha", "Ike's Backup", "Lucina's Estoc", "Robin's Primer"])
    for (const w of ALL_WEAPONS.filter((x) => /Armoury|Store/.test(x.availability.source) && !visiting.has(x.name))) {
      expect(FATES_SHOPS[w.name], w.name).toBeDefined()
      if (w.purchase) expect(FATES_SHOPS[w.name][0].buy, w.name).toBe(w.purchase.buy)
    }
  })

  it('stocks more as a building levels up, never less', () => {
    for (const [name, entries] of Object.entries(FATES_SHOPS))
      for (const e of entries) {
        const amount = e.stock.map((s) => (s === null ? Infinity : s))
        expect(amount[0] <= amount[1] && amount[1] <= amount[2], name).toBe(true)
      }
  })
})
