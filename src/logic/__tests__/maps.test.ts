import { describe, expect, it } from 'vitest'
import { ALL_MAPS } from '../../data/maps'
import { CONQUEST_12 } from '../../data/maps/conquest12'
import { FATES_TERRAIN } from '../../data/maps/fatesTerrain'
import { DIFFICULTIES } from '../../data/maps/types'
import type { Tile } from '../../data/maps/types'
import { applyChanges, resolveTile, terrainAt, terrainInfo, tileKey, tilesInRadius } from '../maps'
import { CHAPTER_1, CHAPTER_4, PROLOGUE } from '../../data/maps/shared'

describe('every map', () => {
  for (const map of ALL_MAPS) {
    const onMap = ([x, y]: Tile) => x >= 1 && x <= map.width && y >= 1 && y <= map.height

    it(`${map.id}: grid matches its declared size and uses known terrain letters`, () => {
      expect(map.grid).toHaveLength(map.height)
      for (const row of map.grid) {
        expect(row).toHaveLength(map.width)
        for (const ch of row) expect(FATES_TERRAIN).toHaveProperty(ch)
      }
    })

    it(`${map.id}: every placed tile is on the map, and nothing shares a tile with another object`, () => {
      const seen = new Set<string>()
      for (const o of map.objects) {
        expect(onMap(o.tile), `${o.type} at ${o.tile}`).toBe(true)
        expect(seen.has(tileKey(o.tile)), `two objects at ${o.tile}`).toBe(false)
        seen.add(tileKey(o.tile))
      }
      for (const t of [...map.starts, ...map.units.map((u) => u.tile), ...map.objectives.flatMap((o) => o.tiles)]) {
        expect(onMap(t), `${t}`).toBe(true)
      }
    })

    it(`${map.id}: objects sit on matching terrain; units, starts and veins on walkable tiles`, () => {
      const expected = { chest: 'c', door: 'd', village: 'v', pot: '.' } as const
      for (const o of map.objects) expect(terrainAt(map, o.tile), `${o.type} at ${o.tile}`).toBe(expected[o.type])
      // Something must be able to stand there (fliers start over open sky in Conquest 20).
      const walkable = (t: Tile) => Object.values(FATES_TERRAIN[terrainAt(map, t)].move).some((m) => m !== null)
      for (const t of [...map.starts, ...map.units.map((u) => u.tile)]) expect(walkable(t), `${t}`).toBe(true)
      for (const c of map.changes) {
        for (const d of DIFFICULTIES) expect(walkable(resolveTile(c.tile, d)), `${c.id} on ${d}`).toBe(true)
      }
    })

    it(`${map.id}: every change patch is on the map and actually changes its tile`, () => {
      for (const c of map.changes) {
        for (const p of c.patch ?? []) {
          expect(onMap(p.tile), `${c.id} ${p.tile}`).toBe(true)
          expect(terrainAt(map, p.tile), `${c.id} ${p.tile}`).not.toBe(p.becomes)
        }
      }
    })
  }
})

describe('Conquest 12', () => {
  const pots = CONQUEST_12.objects.filter((o) => o.type === 'pot')

  it('has the 69 pots from the guide: 28 medicine, 41 poison', () => {
    expect(pots).toHaveLength(69)
    expect(pots.filter((p) => p.pot === 'medicine')).toHaveLength(28)
    expect(pots.filter((p) => p.pot === 'poison')).toHaveLength(41)
  })

  it('puts the Dragon Vein next to Saizo & Kagero on Normal/Hard and two tiles north on Lunatic', () => {
    const pair = CONQUEST_12.units.find((u) => u.name.startsWith('Saizo'))!.tile
    const vein = CONQUEST_12.changes[0].tile
    for (const d of ['Normal', 'Hard'] as const) {
      const [x, y] = resolveTile(vein, d)
      expect(Math.abs(x - pair[0]) + Math.abs(y - pair[1])).toBe(1)
    }
    expect(resolveTile(vein, 'Lunatic')).toEqual([pair[0], pair[1] + 2])
  })

  it("has the wiki's enemy totals on each difficulty (31 / 38 / 42, counting each pair as two)", () => {
    const expected = { Normal: 31, Hard: 38, Lunatic: 42 }
    for (const d of DIFFICULTIES) {
      const foes = CONQUEST_12.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d)))
      expect(foes.reduce((n, u) => n + (u.paired ? 2 : 1), 0), d).toBe(expected[d])
      const tiles = foes.map((u) => tileKey(u.tile))
      expect(new Set(tiles).size, `${d}: two units on one tile`).toBe(tiles.length)
    }
  })

  it('has no unit standing on a pot', () => {
    const potTiles = new Set(pots.map((p) => tileKey(p.tile)))
    for (const u of CONQUEST_12.units) expect(potTiles.has(tileKey(u.tile)), `${u.name} at ${u.tile}`).toBe(false)
  })

  it('deploys Corrin + 12', () => {
    expect(CONQUEST_12.starts).toHaveLength(13)
  })
})

describe("enemy totals match the wiki's enemy tables (pairs count as two)", () => {
  const expected: Record<string, [number, number, number]> = {
    'fe14-prologue': [15, 15, 15],
    'fe14-1': [1, 1, 1],
    'fe14-2': [4, 6, 6],
    'fe14-3': [11, 11, 13],
    'fe14-4': [12, 14, 14],
    'fe14-5': [7, 9, 10],
    'fe14c-6': [5, 5, 5],
    'fe14c-7': [13, 16, 18],
    'fe14c-8': [12, 14, 14],
    'fe14c-9': [17, 19, 23],
    'fe14c-10': [19, 23, 27],
    'fe14c-11': [27, 31, 38],
    'fe14c-12': [31, 38, 42],
    'fe14c-13': [22, 26, 36],
    'fe14c-14': [25, 30, 35],
    'fe14c-15': [25, 25, 29],
    'fe14c-16': [25, 34, 41],
    'fe14c-17': [32, 39, 41],
    'fe14c-18': [27, 34, 39],
    'fe14c-19': [26, 28, 37],
    'fe14c-20': [30, 37, 45],
    'fe14c-21': [27, 31, 36],
    'fe14c-22': [23, 30, 33],
    'fe14c-23': [30, 42, 45],
    'fe14c-24': [25, 30, 40],
    'fe14c-25': [28, 38, 49],
    'fe14c-26': [35, 48, 50],
    'fe14c-27': [17, 21, 22],
    'fe14c-endgame': [22, 26, 37],
  }
  for (const map of ALL_MAPS) {
    it(map.id, () => {
      expect(expected, `no expected totals for ${map.id}`).toHaveProperty(map.id)
      DIFFICULTIES.forEach((d, i) => {
        const foes = map.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d)))
        expect(foes.reduce((n, u) => n + (u.paired ? 2 : 1), 0), d).toBe(expected[map.id][i])
        const tiles = foes.map((u) => tileKey(u.tile))
        expect(new Set(tiles).size, `${d}: two units on one tile`).toBe(tiles.length)
      })
    })
  }
})

describe('shared chapters', () => {
  it('Prologue: the vein dries exactly the river', () => {
    const patch = PROLOGUE.changes[0].patch!
    expect(patch.every((p) => terrainAt(PROLOGUE, p.tile) === 'w')).toBe(true)
    expect(terrainAt(applyChanges(PROLOGUE, new Set(['vein'])), [10, 10])).toBe('.')
    expect(PROLOGUE.grid.join('').split('').filter((c) => c === 'w')).toHaveLength(patch.length)
  })

  it('Chapter 4: seven veins, each melting one whole snow mountain, together melting all the snow', () => {
    expect(CHAPTER_4.changes).toHaveLength(7)
    const melted = applyChanges(CHAPTER_4, new Set(CHAPTER_4.changes.map((c) => c.id)))
    expect(melted.grid.join('')).not.toContain('n')
    for (const c of CHAPTER_4.changes) expect(c.patch!.every((p) => terrainAt(CHAPTER_4, p.tile) === 'n')).toBe(true)
  })

  it('Chapter 1: its healing tile heals 50%, not the usual 20%', () => {
    const healed = applyChanges(CHAPTER_1, new Set(['vein']))
    expect(terrainInfo(healed, terrainAt(healed, [7, 7])).heal).toBe(50)
  })
})

describe('tilesInRadius', () => {
  it('covers a 2-tile diamond (13 tiles) in open space and clips at the map edge', () => {
    expect(tilesInRadius(CONQUEST_12, [10, 20], 2)).toHaveLength(13)
    expect(tilesInRadius(CONQUEST_12, [1, 1], 2)).toHaveLength(6)
  })
})
