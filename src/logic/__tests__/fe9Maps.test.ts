import { describe, expect, it } from 'vitest'
import { FE9_MAPS } from '../../data/fe9/fe9Maps'
import { FE9_TERRAIN } from '../../data/fe9/fe9Terrain'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { terrainInfo } from '../maps'

const byHeading = (h: string) => FE9_MAPS.find((m) => m.heading === h)!
const on = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const enemies = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally').filter(on(d)).length
const arrivals = (m: ChapterMap, d: Difficulty) =>
  (m.reinforcements ?? []).reduce((n, g) => n + g.units.filter(on(d)).length * (/each turn/.test(String(g.when)) ? 2 : 1), 0)

// The Fire Emblem Wiki's enemy counts (starting, reinforcements) on Easy/Normal and Hard ("Difficult").
const WIKI: Record<string, [[number, number], [number, number]]> = {
  'Ch.1': [[7, 0], [10, 0]],
  'Ch.2': [[9, 0], [13, 0]],
  'Ch.3': [[14, 0], [15, 0]],
  'Ch.4': [[16, 0], [22, 0]],
  'Ch.5': [[22, 10], [26, 10]],
  'Ch.6': [[18, 0], [24, 0]],
  'Ch.7': [[15, 13], [21, 13]],
  'Ch.8': [[29, 12], [30, 13]],
  'Ch.9': [[17, 7], [23, 11]],
  'Ch.10': [[6, 14], [6, 16]],
  'Ch.11': [[28, 4], [33, 4]],
  'Ch.12': [[6, 7], [6, 8]],
  'Ch.13': [[23, 8], [28, 8]],
  'Ch.14': [[19, 2], [23, 2]],
  'Ch.15': [[20, 0], [20, 0]],
  'Ch.16': [[28, 7], [32, 7]],
  'Ch.18': [[20, 10], [24, 12]],
  'Ch.19': [[27, 0], [32, 0]],
  'Ch.20': [[27, 15], [32, 15]],
  'Ch.21': [[36, 13], [43, 13]],
  'Ch.22': [[41, 11], [47, 11]],
  'Ch.23': [[29, 13], [37, 13]],
  'Ch.24': [[35, 13], [43, 18]],
  'Ch.25': [[24, 2], [29, 6]],
  'Ch.26': [[35, 18], [44, 28]],
  'Ch.28': [[29, 7], [42, 13]],
  Endgame: [[50, 0], [40, 5]],
}
/** Where the game's files and the wiki's count differ, and why. */
const EXCEPTIONS: Record<string, string> = {
  'Ch.11': 'Three Vigilantes the files place as enemies; the wiki leaves them out.',
  'Ch.22': "One Thief short on Easy/Normal: the script brings it only on Hard. Not yet checked in-game.",
  Endgame: "Ashnard's second form is listed as a group of its own.",
}

describe("Path of Radiance's maps from the game files", () => {
  it('has every chapter, from the Prologue to the Endgame', () => {
    expect(FE9_MAPS.map((m) => m.heading)).toEqual([
      'Prologue', ...Array.from({ length: 16 }, (_, i) => `Ch.${i + 1}`), 'Ch.17-1', 'Ch.17-2', 'Ch.17-3', 'Ch.17-4',
      ...Array.from({ length: 10 }, (_, i) => `Ch.${i + 18}`), 'Ch.27-2', 'Ch.28', 'Endgame',
    ])
    expect(new Set(FE9_MAPS.map((m) => m.id)).size).toBe(FE9_MAPS.length)
  })

  it('keeps every grid, unit and tile on the map, with terrain the table knows', () => {
    for (const m of FE9_MAPS) {
      expect(m.grid).toHaveLength(m.height)
      for (const row of m.grid) {
        expect(row, m.heading).toHaveLength(m.width)
        for (const c of row) expect(FE9_TERRAIN, `${m.heading} '${c}'`).toHaveProperty(c)
      }
      const inside = ([x, y]: [number, number]) => x >= 1 && x <= m.width && y >= 1 && y <= m.height
      for (const u of m.units) expect(inside(u.tile), `${m.heading} ${u.name}`).toBe(true)
      for (const t of m.starts) expect(inside(t), m.heading).toBe(true)
      for (const g of m.reinforcements ?? []) for (const u of g.units) expect(inside(u.tile), `${m.heading} ${u.name}`).toBe(true)
      if (m.corrinStart) expect(m.starts).toContainEqual(m.corrinStart)
    }
  })

  it("matches the wiki's enemy counts", () => {
    for (const [heading, [normal, hard]] of Object.entries(WIKI)) {
      if (EXCEPTIONS[heading]) continue
      const m = byHeading(heading)
      expect([enemies(m, 'Normal'), arrivals(m, 'Normal')], `${heading} Easy/Normal`).toEqual(normal)
      expect([enemies(m, 'Hard'), arrivals(m, 'Hard')], `${heading} Hard`).toEqual(hard)
    }
  })

  it('reads bosses, drops, chests and villages', () => {
    const ch2 = byHeading('Ch.2')
    expect(ch2.units.find((u) => u.type === 'boss')).toMatchObject({ name: 'Ikanau', drops: ['Speedwing'] })
    expect(byHeading('Ch.7').objects).toContainEqual(expect.objectContaining({ type: 'chest', contents: 'Miracle' }))
    expect(byHeading('Ch.1').objects).toContainEqual(expect.objectContaining({ type: 'village', reward: 'Seraph Robe' }))
  })

  it('times reinforcements from the script, by phase and difficulty', () => {
    const ch12 = byHeading('Ch.12')
    expect(ch12.reinforcements!.map((g) => g.when)).toContain('Turn 13, start of the enemy phase')
    const ch16 = byHeading('Ch.16')
    expect(ch16.reinforcements![0].when).toEqual({ Normal: 'Turn 9, start of the player phase', Hard: 'Turn 6, start of the player phase' })
    const ch7 = byHeading('Ch.7').reinforcements!
    expect(ch7.find((g) => g.when === 'Turn 2, start of the player phase')!.units[0].difficulties).toEqual(['Hard'])
  })

  it("states each chapter's goals in the game's own terms", () => {
    expect(byHeading('Ch.5')).toMatchObject({ victory: 'Defend for 6 turns', defeat: 'Ike dies, or enemy seizes location' })
    expect(byHeading('Ch.20').victory).toBe('Arrive within 15 turns (20 on Easy)')
  })

  it('places fences, arrivals, talks and conditions from the files', () => {
    expect(byHeading('Ch.1').walls!.length).toBeGreaterThan(20)
    expect(byHeading('Ch.3').joiners).toContainEqual(expect.objectContaining({ name: 'Marcia', talk: 'Talk with Ike', ally: true }))
    expect(byHeading('Ch.11').units.some((u) => u.name === 'Nasir')).toBe(false)
    const ch13 = byHeading('Ch.13').units.filter((u) => u.tile[0] === byHeading('Ch.13').units.find((g) => g.name === 'Gatrie')!.tile[0])
    expect(byHeading('Ch.13').units.find((u) => u.name === 'Gatrie')!.note).toMatch(/only if Gatrie is still alive/)
    expect(ch13.filter((u) => u.tile[1] === byHeading('Ch.13').units.find((g) => g.name === 'Gatrie')!.tile[1])).toHaveLength(1)
    expect(byHeading('Ch.7').notes.join(' ')).toMatch(/Balmer isn't on the map at the start/)
    // Greil comes and goes in Ch.7; Gatrie and Shinon arrive with him and join you.
    const ch7 = byHeading('Ch.7').joiners!
    expect(ch7.some((j) => j.name === 'Greil')).toBe(false)
    expect(ch7.filter((j) => ['Gatrie', 'Shinon'].includes(j.name) && !j.ally)).toHaveLength(2)
    // Haar leaves at the start of Ch.23 and flies back in later, recruited by Jill.
    expect(byHeading('Ch.23').reinforcements!.flatMap((g) => g.units)).toContainEqual(expect.objectContaining({ name: 'Haar', talk: 'Recruit: talk with Jill' }))
  })

  it("splits Ch.17 into its four sections, each with its own goal", () => {
    expect(['Ch.17-1', 'Ch.17-2', 'Ch.17-3', 'Ch.17-4'].map((h) => byHeading(h).victory)).toEqual([
      'Rout the enemy', 'Arrive', 'Survive for 10 turns', 'Defeat boss',
    ])
  })

  it("marks Ch.25's eleven boulders with their paths", () => {
    const rocks = byHeading('Ch.25').changes.filter((c) => c.trigger === 'boulder')
    expect(rocks).toHaveLength(11)
    for (const r of rocks) expect(r.path![0]).toEqual(r.tile.default)
  })

  it("finds Ch.15's buried items and Stefan's hiding spot", () => {
    const hidden = byHeading('Ch.15').objects.filter((o) => o.type === 'hidden')
    expect(hidden.map((o) => o.type === 'hidden' && o.contents).sort()).toEqual(
      ['Boots', 'Coin', 'Coin', 'Guard', 'Physic', 'Shine', 'Silver Blade', 'Statue Frag', 'Stefan (with the Vague Katti)', 'White Gem'],
    )
    expect(hidden.find((o) => o.type === 'hidden' && o.contents.startsWith('Stefan'))).toMatchObject({ note: expect.stringMatching(/Lethe or Mordecai/) })
  })

  it("uses the game's terrain: a thicket gives Avoid +10 and Def +1 and slows horses", () => {
    const thicket = terrainInfo(byHeading('Ch.2'), 'f')
    expect(thicket).toMatchObject({ name: 'Thicket', def: 1, avo: 10 })
    expect(thicket.move).toMatchObject({ Infantry: 2, 'Horse knights': 3, 'Beast laguz': 1, Fliers: 1 })
  })
})
