import { describe, expect, it } from 'vitest'
import { FE9_WEAPONS } from '../../data/fe9/fe9Weapons'
import { FE9_MAP_SET } from '../../data/fe9/fe9MapSet'
import { FE10_WEAPONS } from '../../data/fe10/fe10Weapons'
import { FE10_MAP_SET } from '../../data/fe10/fe10MapSet'
import type { MapSet } from '../../data/maps/mapSet'
import type { Difficulty } from '../../data/maps/types'
import { fe9ItemSources } from '../../data/fe9/fe9ItemSources'
import { fe10ItemSources } from '../../data/fe10/fe10ItemSources'
import { atStart } from '../maps'
import { reachOf } from '../spoiler'
import { chaptersFor, firstChapter, inChapter, telliusKey } from '../spoilerWeapons'

const GAMES = [
  { name: 'Path of Radiance', set: FE9_MAP_SET, weapons: FE9_WEAPONS, sources: fe9ItemSources },
  { name: 'Radiant Dawn', set: FE10_MAP_SET, weapons: FE10_WEAPONS, sources: fe10ItemSources },
] as const

const story = (set: MapSet) => set.story!
const idsOf = (set: MapSet) => story(set).maps.map((m) => m.id)
const weaponsIn = (g: (typeof GAMES)[number], id: string) => g.weapons.filter((w) => chaptersFor(w, g.sources, story(g.set)).has(id)).map((w) => w.name)

describe.each(GAMES)('spoiler block: $name', (g) => {
  const ids = idsOf(g.set)

  it('lists the story in order, once, without the side maps', () => {
    expect(new Set(ids).size).toBe(ids.length)
    expect(story(g.set).maps.every((m) => m.route === 'Story')).toBe(true)
    const names = story(g.set).maps.map((m) => story(g.set).name(m))
    expect(new Set(names).size).toBe(names.length)
  })

  it('names only chapters of the story in every shop, bargain, forge, base conversation and gift list', () => {
    for (const w of g.weapons) {
      const lists = [w.shopAt?.normal, w.shopAt?.hard, w.bargainAt?.normal, w.bargainAt?.hard, w.forgeAt?.normal, w.forgeAt?.hard, w.baseAt, w.giftAt, w.kitAt]
      for (const list of lists) for (const id of list ?? []) expect(ids, `${w.name} ${id}`).toContain(id)
    }
  })

  it('keeps a weapon listed from the chapter it first turns up in, and nothing before', () => {
    for (const w of g.weapons) {
      const first = firstChapter(w, g.sources, story(g.set))
      for (let at = 0; at < ids.length; at++) expect(first <= at, `${w.name} at ${at}`).toBe(ids.slice(0, at + 1).some((id) => chaptersFor(w, g.sources, story(g.set)).has(id)))
    }
    const listed = ids.map((_, at) => g.weapons.filter((w) => firstChapter(w, g.sources, story(g.set)) <= at).length)
    expect(listed[0]).toBeLessThan(listed[listed.length - 1])
    for (let i = 1; i < listed.length; i++) expect(listed[i]).toBeGreaterThanOrEqual(listed[i - 1])
  })

  it("says what this chapter's base sells on the picked difficulty: stock and bargains are the chapter's own, gifts are kept once reached", () => {
    for (const { value: difficulty } of g.set.difficulties) {
      const key = telliusKey(difficulty)
      for (const w of g.weapons) {
        const first = firstChapter(w, g.sources, story(g.set), difficulty)
        for (let at = Math.max(first, 0); at < ids.length && at < first + 40; at += 7) {
          const cut = inChapter(w, at, story(g.set), difficulty)
          const s = story(g.set)
          const name = s.part ? s.name(s.maps[at]) : s.short(s.maps[at])
          expect(!!cut.shop?.[key], `${w.name} sold at ${at} on ${difficulty}`).toBe(!!w.shopAt?.[key].includes(ids[at]))
          expect(!!cut.bargain?.[key], `${w.name} bargain at ${at} on ${difficulty}`).toBe(!!w.bargainAt?.[key].includes(ids[at]))
          for (const text of [cut.shop, cut.bargain, cut.forge]) for (const d of [text?.normal, text?.hard]) expect([undefined, '', name]).toContain(d)
          for (const id of [...(cut.baseAt ?? []), ...(cut.giftAt ?? []), ...(cut.kitAt ?? [])]) expect(ids.indexOf(id)).toBeLessThanOrEqual(at)
        }
      }
    }
  })

  it("keeps each map line's difficulties with it, out of its words, and reads only the picked difficulty's", () => {
    const all = g.weapons.flatMap((w) => g.sources(w.name))
    expect(all.some((s) => s.difficulties)).toBe(true)
    for (const s of all) expect(s.how, s.how).not.toMatch(/ only\)|Normal|Hard|Easy/)
    // A line on some difficulties only counts on those.
    const limited = g.weapons.find(
      (w) => g.sources(w.name).length > 0 && g.sources(w.name).every((s) => s.difficulties?.length === 1) && !w.shopAt && !w.kitAt && !w.giftAt && !w.baseAt,
    )
    if (limited) {
      const on = g.sources(limited.name)[0].difficulties![0] as Difficulty
      const off = g.set.difficulties.map((d) => d.value).find((d) => !g.sources(limited.name).some((s) => s.difficulties!.includes(d)))
      expect(chaptersFor(limited, g.sources, story(g.set), on).size, limited.name).toBeGreaterThan(0)
      if (off) expect(chaptersFor(limited, g.sources, story(g.set), off).size, limited.name).toBe(0)
    }
  })

  it("counts what a foe who arrives mid-chapter carries from the chapter after, not the one it arrives in", () => {
    const late = g.weapons.find((w) => g.sources(w.name).some((s) => s.arrives))!
    for (const s of g.sources(late.name).filter((x) => x.arrives)) {
      const i = ids.indexOf(s.mapId)
      const only = g.sources(late.name).filter((x) => x.mapId === s.mapId && !x.arrives)
      if (only.length === 0 && !late.shopAt?.normal.includes(s.mapId) && !late.baseAt?.includes(s.mapId) && !late.giftAt?.includes(s.mapId))
        expect(chaptersFor(late, g.sources, story(g.set)).has(s.mapId)).toBe(false)
      if (i >= 0 && i + 1 < ids.length) expect(chaptersFor(late, g.sources, story(g.set)).has(ids[i + 1])).toBe(true)
    }
  })
})

describe('what the block shows', () => {
  const at = (set: MapSet, id: string) => set.story!.maps.findIndex((m) => m.id === id)

  it("keeps Petrine's Flame Lance for the Great Bridge, where she's a unit you can see", () => {
    const [pr] = GAMES
    expect(weaponsIn(pr, 'fe9-23')).toContain('Flame Lance')
    // She stands in the placement files of earlier chapters as a cutscene unit, and the lance isn't listed there.
    for (const id of idsOf(pr.set).slice(0, at(pr.set, 'fe9-23'))) expect(weaponsIn(pr, id), id).not.toContain('Flame Lance')
  })

  it('lists what base conversations give, though no shop sells them', () => {
    const [, rd] = GAMES
    const brave = FE10_WEAPONS.find((w) => w.name === 'Brave Axe')!
    expect(brave.shop).toBeUndefined()
    expect(brave.baseAt).toContain('fe10-3-6')
    expect(weaponsIn(rd, 'fe10-3-6')).toEqual(expect.arrayContaining(['Brave Axe', 'Tarvos']))
    expect(weaponsIn(rd, 'fe10-3-5')).not.toContain('Tarvos')
  })

  it('lists a story gift from the chapter that hands it over, and keeps it listed afterwards', () => {
    const rd = FE10_WEAPONS.find((w) => w.name === 'Ragnell')!
    const story = FE10_MAP_SET.story!
    const gift = story.maps.findIndex((m) => m.id === 'fe10-3-11')
    expect(firstChapter(rd, fe10ItemSources, story)).toBe(gift)
    expect(inChapter(rd, gift - 1, story).giftAt).toBeUndefined()
    expect(inChapter(rd, gift + 3, story).giftAt).toEqual(['fe10-3-11'])
    // It isn't for sale in any chapter, before or after.
    expect(rd.shopAt).toBeUndefined()
  })

  it('marks limited stock: Radiant Dawn bargains are one chapter at a time', () => {
    const story = FE10_MAP_SET.story!
    const florete = FE10_WEAPONS.find((w) => w.name === 'Florete')!
    const bargain = florete.bargainAt!.normal
    expect(bargain.length).toBeGreaterThan(0)
    const at = story.maps.findIndex((m) => m.id === bargain[0])
    expect(inChapter(florete, at, story).bargain).toBeDefined()
    expect(inChapter(florete, at + 1, story).bargain).toBeUndefined()
  })

  it("tags a weapon \"shop\" only where the picked difficulty's base sells it", () => {
    const [pr] = GAMES
    // At Ch.12 only Hard's base sells the Iron Sword.
    const sword = FE9_WEAPONS.find((w) => w.name === 'Iron Sword')!
    const at = pr.set.story!.maps.findIndex((m) => m.id === 'fe9-12')
    expect(inChapter(sword, at, pr.set.story!, 'Normal').shop).toBeUndefined()
    expect(inChapter(sword, at, pr.set.story!, 'Hard').shop?.hard).toBe('Ch.12')
  })

  it('lists a base conversation gift where the file gives it, and a drop where the foe stands', () => {
    const [pr] = GAMES
    expect(weaponsIn(pr, 'fe9-11')).toContain('Laguzslayer')
  })

  it("lists a foe's own weapon from the chapter whose map has a foe carrying it at the start", () => {
    const [pr, rd] = GAMES
    // Gurgurant is Ashnard's, on the Endgame map; the Black Knight's Alondite only shows once he's a unit on the map (27-2).
    expect(weaponsIn(pr, 'fe9-endgame')).toContain('Gurgurant')
    expect(weaponsIn(pr, 'fe9-27-2')).toContain('Alondite')
    expect(weaponsIn(pr, 'fe9-24')).not.toContain('Alondite')
    expect(weaponsIn(rd, 'fe10-4-3')).toEqual(expect.arrayContaining(['Rewarp', 'Elsilence', 'Elsleep']))
    expect(weaponsIn(rd, 'fe10-4-2')).not.toContain('Rewarp')
  })

  it("lists what the units on your side hold from the chapter they appear in: a recruit's own weapon, a starting kit", () => {
    const [pr, rd] = GAMES
    const lance = FE9_WEAPONS.find((w) => w.name === 'Brave Lance')!
    expect(lance.kitAt).toBeDefined()
    expect(firstChapter(lance, fe9ItemSources, pr.set.story!)).toBe(pr.set.story!.maps.findIndex((m) => m.id === lance.kitAt![0]))
    // Each unit's gear counts once, from the chapter it first joins, and never from the debug menu's rosters: Geoffrey's Brave
    // Lance after Ch.24's end, Haar's Brave Axe after Jill's talk in Ch.23. Nobody who joins carries a Hand Axe.
    const pw = (name: string) => FE9_WEAPONS.find((w) => w.name === name)!
    expect(lance.kitAt).toEqual(['fe9-25'])
    expect(pw('Brave Axe').kitAt).toEqual(['fe9-24'])
    expect(pw('Hand Axe').kitAt).toBeUndefined()
    // A gift at a chapter's end is the next chapter's (Rhys's Mend after Ch.6); Ch.4's Regal Sword is its opening's, once.
    expect(pw('Mend').giftAt).toEqual(['fe9-7'])
    expect(pw('Regal Sword').giftAt).toEqual(['fe9-4'])
    // What the setup gives a foe is the foe's: Shinon's Brave Bow turns up in Ch.18 as his drop, not as a gift.
    expect(pw('Brave Bow').giftAt).toBeUndefined()
    expect(firstChapter(pw('Brave Bow'), fe9ItemSources, pr.set.story!)).toBe(pr.set.story!.maps.findIndex((m) => m.id === 'fe9-18'))
    // Part 4's Prologue puts Cymbeline in a unit's hands, though no shop or chest ever offers it.
    const tome = FE10_WEAPONS.find((w) => w.name === 'Cymbeline')!
    expect(tome.shopAt).toBeUndefined()
    expect(weaponsIn(rd, 'fe10-4-prologue')).toContain('Cymbeline')
    expect(weaponsIn(rd, 'fe10-3-endgame')).not.toContain('Cymbeline')
    // It's kept once reached, like a gift.
    expect(inChapter(tome, rd.set.story!.maps.length - 1, rd.set.story!).kitAt).toEqual(tome.kitAt)
  })

  it('opens the trial maps once the story is cleared', () => {
    const s = FE9_MAP_SET.story!
    expect(reachOf(s, 3).has('fe9-trial1')).toBe(false)
    expect(reachOf(s, s.maps.length - 1).has('fe9-trial1')).toBe(true)
  })

  it('says which chapter is the one you are on', () => {
    const s = FE9_MAP_SET.story!
    expect(reachOf(s, 2).here(s.maps[2].id)).toBe(true)
    expect(reachOf(s, 2).here(s.maps[1].id)).toBe(false)
  })
})

describe('a map under the block', () => {
  const maps = [...FE9_MAP_SET.maps, ...FE10_MAP_SET.maps]
  it('has no reinforcements, no joiners and no note about either, but keeps who starts on it', () => {
    const prologue = FE9_MAP_SET.maps.find((m) => m.id === 'fe9-prologue')!
    expect(prologue.notes.some((n) => /arrives with Group/.test(n))).toBe(true)
    for (const m of maps) {
      const start = atStart(m)
      expect(start.reinforcements, m.id).toBeUndefined()
      expect(start.joiners, m.id).toBeUndefined()
      expect(start.notes.some((n) => /arrives with Group/.test(n)), m.id).toBe(false)
      expect(start.units, m.id).toBe(m.units)
      expect(start.starts, m.id).toBe(m.starts)
    }
  })
})
