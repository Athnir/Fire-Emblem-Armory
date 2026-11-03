import { describe, expect, it } from 'vitest'
import { FE17_ITEM_SOURCES } from '../../data/fe17/fe17ItemSources'
import { FE17_LISTED } from '../../data/fe17/fe17Listed'
import { FE17_MAPS } from '../../data/fe17/fe17Maps'
import { FE17_STORY } from '../../data/fe17/fe17MapSet'
import { FE17_SUPPORTS } from '../../data/fe17/fe17Supports'
import { FE17_MOVE_CLASSES, FE17_TERRAIN } from '../../data/fe17/fe17Terrain'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { trueHit } from '../trueHit'

const map = (id: string) => FE17_MAPS.find((m) => m.id === id)!
const on = (u: MapUnit, d: Difficulty) => !u.difficulties || u.difficulties.includes(d)
const DIFFS: Difficulty[] = ['Normal', 'Hard', 'Maddening']
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && on(u, d))
const totals = (m: ChapterMap) => DIFFS.map((d) => foes(m, d).length)
const arriving = (m: ChapterMap) =>
  DIFFS.map((d) => (m.reinforcements ?? []).reduce((n, g) => n + g.units.filter((u) => on(u, d)).length, 0))

describe("Engage's story maps", () => {
  it('has the Prologue and Chapters 1 to 26, each grid its own size', () => {
    expect(FE17_MAPS.filter((m) => m.route === 'Story').map((m) => m.id)).toEqual(
      Array.from({ length: 27 }, (_, k) => `fe17-m${String(k).padStart(3, '0')}`),
    )
    for (const m of FE17_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The grid's own window (its MapTerrain object): Chapter 4 is 23 by 20.
    expect([map('fe17-m004').width, map('fe17-m004').height]).toEqual([23, 20])
    expect(FE17_STORY.maps.map((m) => FE17_STORY.short(m)).slice(0, 3)).toEqual(['Prologue', 'Ch.1', 'Ch.2'])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE17_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE17_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const c of FE17_MOVE_CLASSES) expect(info!.move[c], `${code} ${c}`).not.toBeUndefined()
    }
    // Woods and thickets: Avo +30, two moves on foot or horseback, one for fliers and dragons (terrain.xml).
    expect(FE17_TERRAIN.ba).toMatchObject({ avo: 30, move: { Infantry: 2, Cavalry: 2, Fliers: 1, Dragons: 1 } })
  })

  it("matches Fire Emblem Wiki's starting foes on every difficulty", () => {
    // [Normal, Hard, Maddening], each chapter page's enemy count (its Normal/Hard tab where it gives one for both).
    const wiki: Record<string, number[]> = {
      'fe17-m000': [1, 1, 1], 'fe17-m001': [3, 4, 5], 'fe17-m003': [12, 14, 14], 'fe17-m004': [14, 17, 18],
      'fe17-m005': [25, 25, 27], 'fe17-m006': [17, 19, 27], 'fe17-m007': [21, 21, 30], 'fe17-m008': [17, 19, 21],
      'fe17-m009': [27, 29, 30], 'fe17-m010': [21, 23, 27], 'fe17-m011': [22, 23, 28], 'fe17-m012': [12, 13, 13],
      'fe17-m013': [35, 36, 42], 'fe17-m014': [35, 35, 43], 'fe17-m015': [30, 35, 38], 'fe17-m016': [32, 34, 34],
      'fe17-m017': [35, 41, 45], 'fe17-m018': [32, 36, 41], 'fe17-m019': [28, 28, 36], 'fe17-m020': [28, 31, 39],
      'fe17-m021': [28, 28, 34], 'fe17-m022': [27, 32, 41], 'fe17-m023': [31, 36, 46], 'fe17-m024': [25, 25, 36],
      'fe17-m025': [48, 49, 53], 'fe17-m026': [11, 11, 11],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    // Chapter 4's reinforcements as the wiki counts them: the Ruffian on turn 2, two Corrupted on turn 4 and two on turn 5, and three
    // more on turn 7 on Maddening.
    expect(arriving(map('fe17-m004'))).toEqual([5, 5, 8])
  })

  it('places what the openings bring: Chapter 10 opens with nineteen of its foes', () => {
    expect(totals(map('fe17-m010'))[0]).toBe(21)
  })
})

describe("Engage's paralogues", () => {
  it('lists the fifteen, each opening before the chapter after the one its world map spot names', () => {
    const side = FE17_MAPS.filter((m) => m.route === 'Paralogue')
    expect(side.map((m) => m.id)).toEqual(Array.from({ length: 15 }, (_, k) => `fe17-s${String(k + 1).padStart(3, '0')}`))
    // Paralogue 1, Budding Talent, opens once Chapter 5 is cleared (chapter.xml): played before Chapter 6.
    expect(FE17_STORY.opensAt!('fe17-s001')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m006'))
    expect(map('fe17-s001').title).toBe('Budding Talent')
  })

  it("matches Fire Emblem Wiki's starting foes (The Radiant Hero's page gives no count)", () => {
    const wiki: Record<string, number[]> = {
      'fe17-s001': [13, 15, 16], 'fe17-s002': [20, 21, 22], 'fe17-s003': [9, 9, 9], 'fe17-s004': [22, 22, 33],
      'fe17-s006': [27, 27, 29], 'fe17-s007': [18, 18, 22], 'fe17-s008': [31, 38, 47], 'fe17-s009': [31, 31, 36],
      'fe17-s010': [32, 37, 38], 'fe17-s011': [18, 20, 30], 'fe17-s012': [26, 34, 40], 'fe17-s013': [6, 7, 7],
      'fe17-s014': [30, 34, 39], 'fe17-s015': [15, 15, 19],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    // Where the groups come once, their totals match too: The Crux of Fate's 4, 6 and 6, The Connector's 28, 28 and 37.
    expect(arriving(map('fe17-s007'))).toEqual([4, 6, 6])
    expect(arriving(map('fe17-s015'))).toEqual([28, 28, 37])
  })
})

describe("Engage's weapons", () => {
  it('sells from the chapter after the one whose clearing opens the armory (Chapter 4)', () => {
    const iron = FE17_ITEM_SOURCES['Iron Sword'].filter((s) => s.kind === 'shop')
    expect(iron[0].mapId).toBe('fe17-m005')
  })

  it('reads effectiveness and its multiplier from the skill table', () => {
    expect(FE17_LISTED.find((w) => w.name === 'Armorslayer')?.effective).toEqual(['armour'])
    expect(FE17_LISTED.find((w) => w.name === 'Levin Sword')?.magic).toBe(true)
  })

  it("rolls hit as Fates does (App.BattleMath.GetHitRatio10000)", () => {
    expect(trueHit('hybrid-fates', 75).trueHitBasisPoints).toBe(8500)
    expect(trueHit('hybrid-fates', 50).trueHitBasisPoints).toBe(5000)
  })
})

describe("Engage's supports", () => {
  it('gives each type its four levels from the support table', () => {
    expect(FE17_SUPPORTS.map((t) => t.type)).toEqual(['Default', 'Balanced', 'Hit', 'Crit', 'Avoid', 'Dodge'])
    for (const t of FE17_SUPPORTS) expect(t.levels.map((l) => l.level)).toEqual(['C', 'B', 'A', 'Ring'])
    // The Hit type at the ring: Hit +30, Avoid +5 (reliance.xml).
    expect(FE17_SUPPORTS.find((t) => t.type === 'Hit')!.levels[3]).toEqual({ level: 'Ring', hit: 30, crit: 0, avoid: 5, dodge: 0 })
  })
})
