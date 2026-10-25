import { describe, expect, it } from 'vitest'
import { FE9_BASES, FE9_WEAPONS } from '../../data/fe9/fe9Weapons'
import { FE9_MAP_SET } from '../../data/fe9/fe9MapSet'
import { FE10_BASES, FE10_WEAPONS } from '../../data/fe10/fe10Weapons'
import { FE10_MAP_SET } from '../../data/fe10/fe10MapSet'
import type { TelliusWeapon } from '../../data/fe9/types'
import type { MapSet } from '../../data/maps/mapSet'
import { atStart } from '../maps'
import { chapterText, reachOf } from '../spoiler'

const GAMES = [
  { name: 'Path of Radiance', set: FE9_MAP_SET, weapons: FE9_WEAPONS, bases: FE9_BASES, style: { parts: false, onward: true } },
  { name: 'Radiant Dawn', set: FE10_MAP_SET, weapons: FE10_WEAPONS, bases: FE10_BASES, style: { parts: true, onward: false } },
] as const

const story = (set: MapSet) => set.story!

describe.each(GAMES)('spoiler block: $name', ({ set, weapons, bases, style }) => {
  const ids = story(set).maps.map((m) => m.id)
  const last = reachOf(story(set), ids.length - 1)

  it('lists the story in order, once, without the side maps', () => {
    expect(new Set(ids).size).toBe(ids.length)
    expect(story(set).maps.every((m) => m.route === 'Story')).toBe(true)
    const names = story(set).maps.map((m) => story(set).name(m))
    expect(new Set(names).size).toBe(names.length)
  })

  it('knows the chapter every weapon first appears in, and every chapter its shops name', () => {
    for (const w of weapons) {
      expect(ids, `${w.name} from`).toContain(w.from)
      for (const at of [w.shopAt, w.bargainAt, w.forgeAt])
        for (const list of Object.values(at ?? {})) for (const id of list) expect(ids, `${w.name} ${id}`).toContain(id)
      // It can't be sold before it's first available.
      for (const at of [w.shopAt, w.bargainAt, w.forgeAt])
        for (const list of Object.values(at ?? {})) for (const id of list) expect(ids.indexOf(id), `${w.name} ${id}`).toBeGreaterThanOrEqual(ids.indexOf(w.from))
    }
  })

  it('words a shop list exactly as the generator does when every chapter is reached', () => {
    const check = (w: TelliusWeapon, text: { normal: string; hard: string } | undefined, at: { normal: string[]; hard: string[] } | undefined) => {
      if (!text || !at) return
      for (const d of ['normal', 'hard'] as const) expect(chapterText(at[d], bases[d], story(set), last, style), `${w.name} ${d}`).toBe(text[d])
    }
    for (const w of weapons) {
      check(w, w.shop, w.shopAt)
      check(w, w.bargain, w.bargainAt)
      check(w, w.forge, w.forgeAt)
    }
  })

  it('keeps every chapter you have not reached out of a shop list', () => {
    const w = weapons.find((x) => x.shop && x.shop.normal.includes('–'))!
    const all = w.shopAt!.normal
    const at = ids.indexOf(all[1])
    const text = chapterText(all, bases.normal, story(set), reachOf(story(set), at), style)
    for (const id of all.filter((i) => ids.indexOf(i) > at)) expect(text).not.toContain(story(set).short(story(set).maps[ids.indexOf(id)]) + ',')
    expect(text).not.toBe(w.shop!.normal)
    expect(chapterText(all, bases.normal, story(set), reachOf(story(set), ids.indexOf(all[0]) - 1), style)).toBe('')
  })

  it('hides weapons until their chapter, and shows them all by the end', () => {
    const count = (at: number) => weapons.filter((w) => reachOf(story(set), at).has(w.from)).length
    expect(count(0)).toBeGreaterThan(0)
    expect(count(0)).toBeLessThan(weapons.length)
    expect(count(ids.length - 1)).toBe(weapons.length)
    for (let i = 1; i < ids.length; i++) expect(count(i)).toBeGreaterThanOrEqual(count(i - 1))
  })
})

describe('what the block hides', () => {
  const first = (weapons: TelliusWeapon[], name: string) => weapons.find((w) => w.name === name)!.from
  it("keeps Ike's Ragnell back until the chapter that gives it", () => {
    const at = (set: MapSet, id: string) => set.story!.maps.findIndex((m) => m.id === id)
    const rag9 = first(FE9_WEAPONS, 'Ragnell')
    const rag10 = first(FE10_WEAPONS, 'Ragnell')
    expect(reachOf(FE9_MAP_SET.story!, at(FE9_MAP_SET, rag9) - 1).has(rag9)).toBe(false)
    expect(reachOf(FE9_MAP_SET.story!, at(FE9_MAP_SET, rag9)).has(rag9)).toBe(true)
    expect(reachOf(FE10_MAP_SET.story!, at(FE10_MAP_SET, rag10) - 1).has(rag10)).toBe(false)
  })

  it('opens the trial maps once the story is cleared', () => {
    const story = FE9_MAP_SET.story!
    expect(reachOf(story, 3).has('fe9-trial1')).toBe(false)
    expect(reachOf(story, story.maps.length - 1).has('fe9-trial1')).toBe(true)
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
