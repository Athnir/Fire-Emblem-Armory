import { describe, expect, it } from 'vitest'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE6_TERRAIN } from '../../data/fe6/fe6Terrain'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE8_TERRAIN } from '../../data/fe8/fe8Terrain'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes } from '../maps'

const codes = (m: ChapterMap) => new Set(m.grid.flatMap(rowCodes))
const count = (m: ChapterMap, code: string) => m.grid.flatMap(rowCodes).filter((c) => c === code).length
const find = (maps: ChapterMap[], id: string) => maps.find((m) => m.id === id)!

describe("the GBA games' walls, by what they are on the map (scripts/gba_walls.py)", () => {
  it('draws each kind of wall as itself: castle, ruins, temple, sandstone, snow, a village, a ship', () => {
    // The Sacred Stones: a fort's castle walls, Jehanna's sandstone hall, Lagdou's ruins, the final temple, a village's houses.
    expect(codes(find(FE8_MAPS, 'fe8-3')).has('w0')).toBe(true)
    expect(count(find(FE8_MAPS, 'fe8-eirika-14'), 'w5')).toBeGreaterThan(100)
    expect(codes(find(FE8_MAPS, 'fe8-eirika-14')).has('w0')).toBe(false)
    expect(count(find(FE8_MAPS, 'fe8-ruins-1'), 'w1')).toBeGreaterThan(50)
    expect(count(find(FE8_MAPS, 'fe8-eirika-final'), 'w3')).toBeGreaterThan(20)
    expect(count(find(FE8_MAPS, 'fe8-2'), 'w8')).toBeGreaterThan(10)
    // The Blazing Blade: the Dragon's Gate's temple, the pirate ship's sides; The Binding Blade: Ilia's snowy walls.
    expect(count(find(FE7_MAPS, 'fe7-e-final'), 'w3')).toBeGreaterThan(20)
    expect(FE7_MAPS.some((m) => codes(m).has('w9'))).toBe(true)
    expect(count(find(FE6_MAPS, 'fe6-20a'), 'w6')).toBeGreaterThan(100)
  })

  it('leaves no plain wall code where a kind is known: only snags, fallen trees until broken, stay plain walls', () => {
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS]) {
      const snags = m.changes.filter((c) => c.snag).length
      expect(count(m, 'wa'), m.id).toBe(snags)
    }
  })

  it("keeps each kind's movement as the game has it: fliers cross a village's houses and walls, no one a castle wall", () => {
    expect(FE8_TERRAIN.w8!.move.Fliers).toBe(1)
    expect(Object.values(FE8_TERRAIN.w0!.move).every((v) => v === null)).toBe(true)
    expect(Object.values(FE6_TERRAIN.w6!.move).every((v) => v === null)).toBe(true)
  })
})
