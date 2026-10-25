import { describe, expect, it } from 'vitest'
import { FE9_WEAPONS } from '../../data/fe9/fe9Weapons'
import { FE9_MAP_SET } from '../../data/fe9/fe9MapSet'
import { FE10_WEAPONS } from '../../data/fe10/fe10Weapons'
import { FE10_MAP_SET } from '../../data/fe10/fe10MapSet'
import type { MapSet } from '../../data/maps/mapSet'
import { fe9ItemSources, fe10ItemSources } from '../fe9ItemSources'
import { atStart } from '../maps'
import { reachOf } from '../spoiler'
import { chaptersFor, inChapter } from '../spoilerWeapons'

const GAMES = [
  { name: 'Path of Radiance', set: FE9_MAP_SET, weapons: FE9_WEAPONS, sources: fe9ItemSources },
  { name: 'Radiant Dawn', set: FE10_MAP_SET, weapons: FE10_WEAPONS, sources: fe10ItemSources },
] as const

const story = (set: MapSet) => set.story!
const idsOf = (set: MapSet) => story(set).maps.map((m) => m.id)
const weaponsIn = (g: (typeof GAMES)[number], id: string) => g.weapons.filter((w) => chaptersFor(w, g.sources).has(id)).map((w) => w.name)

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
      const lists = [w.shopAt?.normal, w.shopAt?.hard, w.bargainAt?.normal, w.bargainAt?.hard, w.forgeAt?.normal, w.forgeAt?.hard, w.baseAt, w.giftAt]
      for (const list of lists) for (const id of list ?? []) expect(ids, `${w.name} ${id}`).toContain(id)
    }
  })

  it('gives each chapter its own stock, not what came before', () => {
    const counts = ids.map((id) => weaponsIn(g, id).length)
    expect(Math.max(...counts)).toBeGreaterThan(10)
    // A chapter's list is what it gives itself: it isn't growing with the story.
    expect(new Set(counts).size).toBeGreaterThan(3)
    expect(Math.max(...counts)).toBeLessThan(g.weapons.length)
  })

  it("cuts a weapon down to the chapter: that base's stock and gifts, nothing from another chapter", () => {
    const here = story(g.set).maps.find((m) => weaponsIn(g, m.id).length > 5)!
    for (const w of g.weapons.filter((x) => chaptersFor(x, g.sources).has(here.id))) {
      const cut = inChapter(w, here, story(g.set))
      for (const text of [cut.shop, cut.bargain, cut.forge]) for (const d of [text?.normal, text?.hard]) expect([undefined, '', story(g.set).name(here)]).toContain(d)
      expect(cut.baseAt ?? [here.id]).toEqual([here.id])
      expect(cut.giftAt ?? [here.id]).toEqual([here.id])
    }
  })

  it("leaves out the drops of foes who arrive later", () => {
    const late = g.weapons.find((w) => g.sources(w.name).some((s) => s.arrives))!
    for (const s of g.sources(late.name).filter((x) => x.arrives)) {
      const only = g.sources(late.name).filter((x) => x.mapId === s.mapId && !x.arrives)
      if (only.length === 0 && !late.shopAt?.normal.includes(s.mapId) && !late.baseAt?.includes(s.mapId) && !late.giftAt?.includes(s.mapId))
        expect(chaptersFor(late, g.sources).has(s.mapId)).toBe(false)
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

  it('lists a story gift in the chapter that hands it over', () => {
    const [pr, rd] = GAMES
    expect(weaponsIn(pr, 'fe9-4')).toContain('Regal Sword')
    expect(weaponsIn(pr, 'fe9-27-2')).toContain('Ragnell')
    expect(weaponsIn(rd, 'fe10-3-11')).toContain('Ragnell')
    expect(weaponsIn(rd, 'fe10-3-10')).not.toContain('Ragnell')
  })

  it('lists a base conversation gift where the file gives it, and a drop where the foe stands', () => {
    const [pr] = GAMES
    expect(weaponsIn(pr, 'fe9-11')).toContain('Laguzslayer')
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
