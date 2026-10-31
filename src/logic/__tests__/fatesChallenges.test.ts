import { describe, expect, it } from 'vitest'
import { ALL_MAPS, FATES_MAP_SET } from '../../data/maps'
import { FATES_CHALLENGES } from '../../data/maps/fatesChallenges'
import { FATES_FORK } from '../../data/maps/fatesStory'
import { reachOf } from '../spoiler'
import { terrainAt, terrainInfo } from '../maps'
import type { Tile } from '../../data/maps/types'

type Route = 'Birthright' | 'Conquest' | 'Revelation'
const story = (route: Route) => FATES_FORK.choices.find((c) => c.id === route)!.story
const at = (route: Route, chapter: number) => story(route).maps.findIndex((m) => m.chapter === chapter)
const reached = (route: Route, chapter: number) => reachOf(story(route), at(route, chapter), route)
const challenges = ALL_MAPS.filter((m) => m.route === 'Challenge')

describe("Fates' challenge battles", () => {
  it('rerun every chapter and paralogue map with an encounter file, never on Conquest', () => {
    expect(challenges).toHaveLength(66)
    expect(Object.keys(FATES_CHALLENGES)).toHaveLength(66)
    expect(challenges.every((m) => m.availableIn?.length && !m.availableIn.includes('Conquest'))).toBe(true)
    // Revelation 23, 25 and 27 and Birthright 27 have no encounter file.
    for (const id of ['fe14r-23', 'fe14r-25', 'fe14r-27', 'fe14b-27']) expect(FATES_CHALLENGES[id], id).toBeUndefined()
    // Paralogues 15-22 need a Nohrian father: their challenges are Revelation's alone.
    expect(ALL_MAPS.find((m) => m.id === 'fe14-x16-challenge')!.availableIn).toEqual(['Revelation'])
  })

  it('put both foe groups on the map, outlined, each with its boss, and two shiny spots', () => {
    for (const m of challenges) {
      expect(m.objects.filter((o) => o.type === 'shiny'), m.id).toHaveLength(2)
      expect(m.units.filter((u) => u.type === 'boss'), m.id).toHaveLength(2)
      expect(m.foeGroups!.map((g) => g.label), m.id).toEqual(['Group 1', 'Group 2'])
      // Every unit is one of a group's tiles, the boss first; the two groups never share a tile.
      expect(m.units.map((u) => u.tile.join()), m.id).toEqual(m.foeGroups!.flatMap((g) => g.tiles.map((t) => t.join())))
      expect(new Set(m.units.map((u) => u.tile.join())).size, m.id).toBe(m.units.length)
      for (const g of m.foeGroups!) expect(m.units.find((u) => u.tile.join() === g.tiles[0].join())!.type, m.id).toBe('boss')
    }
    // As read live in Paralogue 16's challenge: the spots, and each group's boss.
    const p16 = ALL_MAPS.find((m) => m.id === 'fe14-x16-challenge')!
    expect(p16.objects.filter((o) => o.type === 'shiny').map((o) => o.tile)).toEqual([[8, 16], [14, 13]])
    expect(p16.foeGroups!.map((g) => g.tiles[0])).toEqual([[18, 17], [10, 11]])
    expect(p16.starts).toHaveLength(10)
  })

  it("say how many foes a group fields: a tile each on Lunatic, two fewer on Normal and Hard, then up to a third fewer", () => {
    // Chapter 3's groups have ten tiles each; four battles read live on Lunatic fielded 8 and 7 (a dual boss), 10, 7 and 8.
    const ch3 = ALL_MAPS.find((m) => m.id === 'fe14-3-challenge')!
    expect(ch3.foeGroups!.map((g) => g.tiles.length)).toEqual([10, 10])
    expect(ch3.notes).toContain('Group 1: its boss and 5 to 7 more foes (Lunatic 6 to 9).')
  })

  it("have the chapter's map with everything spent: every tile in its second state, chests, doors and villages gone", () => {
    for (const m of challenges) {
      const base = ALL_MAPS.find((b) => b.id === m.challengeOf)!
      expect(m.changes, m.id).toEqual([])
      expect(m.dark, m.id).toBeUndefined()
      expect(m.objects.some((o) => o.type === 'chest' || o.type === 'door' || o.type === 'village'), m.id).toBe(false)
      // Every breakable is broken.
      for (const ch of base.changes.filter((x) => x.trigger === 'breakable')) {
        for (const p of ch.patch ?? []) expect(terrainAt(m, p.tile), `${m.id} ${ch.id} ${p.tile}`).toBe(p.becomes)
      }
    }
    // Read live: Chapter 3's 13 sky tiles and Revelation 20's 68 are all bridges, every one at once.
    const bridges = (id: string) => {
      const m = ALL_MAPS.find((x) => x.id === id)!
      return m.grid.join('').match(/../g)!.filter((code) => code === 'tb').length - ALL_MAPS.find((x) => x.id === m.challengeOf)!.grid.join('').match(/../g)!.filter((code) => code === 'tb').length
    }
    expect(bridges('fe14-3-challenge')).toBe(13)
    expect(bridges('fe14r-20-challenge')).toBe(68)
    // And Revelation 11's 62 spike tiles are all spikes, for good, and its door is open.
    const r11 = ALL_MAPS.find((x) => x.id === 'fe14r-11-challenge')!
    expect(r11.grid.join('').match(/../g)!.filter((code) => code === 'de')).toHaveLength(62)
    expect(terrainInfo(r11, 'de')).toMatchObject({ name: 'Spikes', heal: -10 })
    expect(r11.grid.join('').match(/../g)!.filter((code) => code === 'ob')).toHaveLength(0)
    // The foe tiles the chapter's own map has walls on: Chapter 2's vein walls, Paralogue 20's breakable walls and Revelation
    // 10's snow are all open.
    const open = (id: string, t: Tile) => {
      const m = ALL_MAPS.find((x) => x.id === id)!
      return Object.values(terrainInfo(m, terrainAt(m, t)).move).some((v) => v !== null)
    }
    for (const t of [[7, 7], [8, 7], [9, 7]] as Tile[]) expect(open('fe14-2-challenge', t), `Ch.2 ${t}`).toBe(true)
    for (const t of [[17, 22], [17, 21], [18, 21]] as Tile[]) expect(open('fe14-x20-challenge', t), `P20 ${t}`).toBe(true)
    expect(open('fe14r-10-challenge', [1, 5]), 'Revelation 10 spot').toBe(true)
  })

  it('are a list of their own, not chapters or paralogues', () => {
    for (const route of ['Birthright', 'Revelation'] as const) {
      expect(FATES_MAP_SET.routes!.maps(route).some((m) => m.route === 'Challenge')).toBe(false)
      expect(FATES_MAP_SET.routes!.side(route).some((m) => m.route === 'Challenge')).toBe(false)
      expect(FATES_MAP_SET.routes!.third!.maps(route).length).toBeGreaterThan(0)
    }
    expect(FATES_MAP_SET.routes!.third!.maps('Conquest')).toEqual([])
    expect(FATES_MAP_SET.chapterLabel(ALL_MAPS.find((m) => m.id === 'fe14b-7-challenge')!)).toMatch(/^Chapter 7: /)
    expect(FATES_MAP_SET.mapLabel(ALL_MAPS.find((m) => m.id === 'fe14-x16-challenge')!)).toMatch(/^Challenge: Paralogue 16: /)
  })

  it("open once their chapter is cleared, and a paralogue's as soon as the paralogue does", () => {
    expect(reached('Birthright', 7).has('fe14b-7-challenge')).toBe(false)
    expect(reached('Birthright', 8).has('fe14b-7-challenge')).toBe(true)
    // The shared chapters' challenges, on both routes that have challenges.
    expect(reached('Revelation', 6).has('fe14-5-challenge')).toBe(true)
    expect(reached('Conquest', 27).has('fe14-5-challenge')).toBe(false)
    for (const chapter of [10, 20, 26]) {
      const r = reached('Revelation', chapter)
      expect(r.has('fe14-x16-challenge'), `Revelation ${chapter}`).toBe(r.has('fe14-x16'))
    }
    expect(reached('Revelation', 26).has('fe14-x16-challenge')).toBe(true)
  })
})
