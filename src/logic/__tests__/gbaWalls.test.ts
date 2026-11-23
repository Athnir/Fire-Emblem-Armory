import { describe, expect, it } from 'vitest'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE6_TERRAIN } from '../../data/fe6/fe6Terrain'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE8_TERRAIN } from '../../data/fe8/fe8Terrain'
import type { ChapterMap } from '../../data/maps/types'
import type { TerrainCode } from '../../data/maps/terrainCodes'
import { rowCodes, sceneryHouse, tileKey, visitable } from '../maps'

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
    expect(['va', 'vb', 'vc', 'vd', 've', 'vf', 'vg', 'vi'].every((c) => codes(find(FE8_MAPS, 'fe8-2')).has(c as TerrainCode))).toBe(true)
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
    expect(FE8_TERRAIN.va!.move.Fliers).toBe(1)
    expect(Object.values(FE8_TERRAIN.ca!.move).every((v) => v === null)).toBe(true)
    expect(Object.values(FE8_TERRAIN.w0!.move).every((v) => v === null)).toBe(true)
    expect(Object.values(FE6_TERRAIN.w6!.move).every((v) => v === null)).toBe(true)
  })
})

describe("the GBA games' ground, as each map draws it (scripts/gba_ground.py)", () => {
  const all = [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS]
  const GROUND = ['t0', 'tl', 't1', 't3', 't6', 't7', 'tk', 'td', 'tg', 'we', 'wk', 'wm', 'tb'] as const
  const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))

  it('draws plains, roads, floors, decks, glaciers and flats each as itself: no plain catch-all is left', () => {
    for (const m of all) expect(codes(m).has('ta'), m.id).toBe(false)
  })

  it("gives every map its own colour for each of its ground and water codes, from its art", () => {
    for (const m of all) for (const c of GROUND) if (codes(m).has(c)) expect(m.fills?.[c], `${m.id} ${c}`).toMatch(/^#[0-9a-f]{6}$/)
  })

  it("colours each map's ground as the game does: Ilia's plains snow, a green chapter's plains green, Jehanna's desert sand", () => {
    const [r, g, b] = rgb(find(FE6_MAPS, 'fe6-20a').fills!.t0!)
    expect(Math.min(r, g, b)).toBeGreaterThan(150)
    expect(Math.max(r, g, b) - Math.min(r, g, b)).toBeLessThan(40)
    const [gr, gg, gb] = rgb(find(FE8_MAPS, 'fe8-2').fills!.t0!)
    expect(gg).toBeGreaterThan(gr)
    expect(gg).toBeGreaterThan(gb)
    const [sr, sg, sb] = rgb(find(FE8_MAPS, 'fe8-eirika-15').fills!.td!)
    expect(Math.min(sr, sg)).toBeGreaterThan(sb)
  })

  it('keeps the ground kinds working alike, as the game has them: only their look differs', () => {
    const plain = FE8_TERRAIN.t0!
    for (const c of ['tl', 't1', 't3', 't7'] as const) {
      expect(FE8_TERRAIN[c]!.move, c).toEqual(plain.move)
      expect([FE8_TERRAIN[c]!.def, FE8_TERRAIN[c]!.avo], c).toEqual([plain.def, plain.avo])
    }
  })
})

describe("a multi-tile building drawn whole, a piece for each place in it (scripts/gba_walls.py's place_pieces)", () => {
  const block = (m: ChapterMap, x0: number, y0: number, w: number, h: number) =>
    Array.from({ length: h }, (_, j) => Array.from({ length: w }, (_, i) => rowCodes(m.grid[m.height - (y0 - j)])[x0 - 1 + i]).join(' '))

  it('draws a 3 x 3 village as its nine places, its entrance at the front, and two side by side as two', () => {
    // The Sacred Stones' Chapter 2: two villages side by side, each with its own fence.
    expect(block(find(FE8_MAPS, 'fe8-2'), 4, 15, 6, 3)).toEqual(['va vb vc va vb vc', 'vd ve vf vd ve vf', 'vg oc vi vg oc vi'])
    expect(block(find(FE8_MAPS, 'fe8-2'), 1, 5, 3, 3)).toEqual(['va vb vc', 'vd ve vf', 'vg oc vi'])
  })

  it('draws a castle on open ground as its towers, walls and keep around its gate', () => {
    expect(block(find(FE6_MAPS, 'fe6-1'), 5, 19, 3, 3)).toEqual(['ca cb cc', 'cd ce cf', 'cg bd ci'])
  })

  it("keeps each piece working as the tile it replaces, and only buildings get them (a castle's halls keep their walls)", () => {
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS])
      for (const c of codes(m)) if (/^[vc][a-i]$/.test(c)) expect(m.terrain![c], `${m.id} ${c}`).toBeDefined()
    expect([...codes(find(FE8_MAPS, 'fe8-5x'))].some((c) => /^c[a-i]$/.test(c))).toBe(false)
  })
})

describe("houses with nothing to visit are drawn as the village scenery (the user's call)", () => {
  const houses = (m: ChapterMap) =>
    m.grid.flatMap((row, i) => rowCodes(row).flatMap((c, x) => (c === 'ot' ? [tileKey([x + 1, m.height - i])] : [])))

  it("draws Bulgar's 42 houses as scenery: only its villages can be visited", () => {
    const bulgar = find(FE6_MAPS, 'fe6-19b')
    const visits = visitable(bulgar)
    expect(houses(bulgar)).toHaveLength(42)
    expect(houses(bulgar).every((k) => sceneryHouse('ot', k, visits))).toBe(true)
    expect(bulgar.objects.filter((o) => o.type === 'village')).toHaveLength(5)
  })

  it('keeps a house with something to visit drawn as one', () => {
    const withVisit = FE8_MAPS.flatMap((m) => houses(m).filter((k) => visitable(m).has(k)))
    expect(withVisit).toHaveLength(2)
  })
})

describe("each map's water apart from its plains (the user's call)", () => {
  const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const apart = (a: string, b: string) => Math.hypot(...rgb(a).map((v, i) => v - rgb(b)[i]))

  it("draws no river, sea, lake or deeps within about 40 (RGB) of its map's plains", () => {
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS])
      for (const c of ['tg', 'we', 'wk', 'wm'] as const)
        if (m.fills?.[c] && m.fills.t0) expect(apart(m.fills[c]!, m.fills.t0), `${m.id} ${c}`).toBeGreaterThanOrEqual(39)
  })

  it("keeps River of Regrets' dry riverbed yellow and its grass green, and Bulgar's lake blue", () => {
    const e17 = find(FE8_MAPS, 'fe8-eirika-17').fills!
    expect(rgb(e17.tg!)[2]).toBeLessThan(rgb(e17.tg!)[1] - 60)
    expect(apart(e17.tg!, e17.t0!)).toBeGreaterThan(40)
    const lake = rgb(find(FE6_MAPS, 'fe6-19b').fills!.wk!)
    expect(lake[2]).toBeGreaterThan(Math.max(lake[0], lake[1]))
  })
})

describe('cliffs, barrels and bones each drawn as themselves (the user’s call)', () => {
  const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const apart = (a: string, b: string) => Math.hypot(...rgb(a).map((v, i) => v - rgb(b)[i]))

  it('gives barrels and bones codes of their own, working as cliffs do (fliers only)', () => {
    expect(codes(find(FE8_MAPS, 'fe8-3')).has('o1' as TerrainCode)).toBe(true)
    expect(codes(find(FE8_MAPS, 'fe8-eirika-15')).has('o2' as TerrainCode)).toBe(true)
    expect(FE8_TERRAIN.o1!.move).toEqual(FE8_TERRAIN.wb!.move)
    expect(FE8_TERRAIN.o2!.move).toEqual(FE8_TERRAIN.wb!.move)
  })

  it("draws every cliff in its map's own colour, never within about 40 (RGB) of ground units walk on", () => {
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS]) {
      if (!codes(m).has('wb')) continue
      expect(m.fills?.wb, m.id).toMatch(/^#[0-9a-f]{6}$/)
      for (const g of ['t0', 'tl', 't1', 't3', 't6', 't7', 'tk', 'td'] as const)
        if (m.fills?.[g]) expect(apart(m.fills.wb!, m.fills[g]!), `${m.id} ${g}`).toBeGreaterThanOrEqual(30)
    }
  })
})

describe("the GBA games' zoomed-in maps (the user's notes, 2026-11-22)", () => {
  const at = (m: ChapterMap, x: number, y: number) => rowCodes(m.grid[m.height - y])[x - 1]
  it('draws the stairwells as stairs going down, the stairs a hall climbs as stairs', () => {
    const e26x = find(FE7_MAPS, 'fe7-e-26x')
    for (const x of [24, 25, 26]) expect(at(e26x, x, 7)).toBe('tc')
    expect(count(e26x, 'gl')).toBeGreaterThan(10)
    expect(count(e26x, 'tc')).toBe(3)
    expect(at(find(FE8_MAPS, 'fe8-ruins-3'), 9, 27)).toBe('gl')
    expect(at(find(FE6_MAPS, 'fe6-8'), 16, 7)).toBe('gl')
    // The Binding Blade's Chapter 22's stairwells under its roofs: the map change that lifts them lays them.
    const roofs = find(FE6_MAPS, 'fe6-22').changes.flatMap((c) => c.patch ?? [])
    expect(roofs.filter((p) => p.becomes === 'gl').map((p) => tileKey(p.tile)).sort()).toEqual(['12,24', '13,16', '19,16', '20,24'])
    expect(FE6_TERRAIN.gl!.move).toEqual(FE6_TERRAIN.tc!.move)
  })

  it('draws the fences as low walls of tan stone, the ship\'s crates, coil and cabin wall as themselves', () => {
    expect(find(FE6_MAPS, 'fe6-11a').wallLooks?.['16,5']).toBe('stone')
    // Its walls beside them (Sacae's walled towns): tan stone too.
    expect(rowCodes(find(FE6_MAPS, 'fe6-11a').grid[find(FE6_MAPS, 'fe6-11a').height - 5])[14]).toBe('w5')
    expect(find(FE8_MAPS, 'fe8-eirika-10').wallLooks?.['9,10']).toBe('stone')
    const ship = find(FE7_MAPS, 'fe7-e-17')
    expect(ship.decor?.['12,11']).toBe('crates')
    expect(ship.decor?.['13,9']).toBe('barrel')
    expect(ship.wallLooks?.['13,16']).toBe('ship')
    expect(ship.wallLooks?.['13,17']).toBeUndefined()
    expect(find(FE8_MAPS, 'fe8-eirika-9').fills?.wg).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('marks the zoomed-out maps, whose villages stay fenced yards and whose buildings alone on a tile stay icons', () => {
    const all = [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS]
    // Every map is one or the other: a zoomed-in map's villages are drawn as their buildings.
    for (const m of all) expect(!!m.villageBuildings !== !!m.zoomedOut, m.id).toBe(true)
    // The user's (2026-11-23): The Sacred Stones' Chapter 2, and the maps they marked with it, are zoomed out; the towns zoomed in.
    for (const id of ['fe6-1', 'fe6-9', 'fe6-18a', 'fe6-18b', 'fe7-lyn-7', 'fe7-e-11', 'fe7-e-18x', 'fe8-2', 'fe8-eirika-15', 'fe8-ephraim-10'])
      expect(find(all, id).zoomedOut, id).toBe(true)
    for (const id of ['fe6-7', 'fe6-11a', 'fe7-lyn-3', 'fe7-e-20', 'fe8-5', 'fe8-eirika-9']) expect(find(all, id).villageBuildings, id).toBe(true)
  })

  it("draws Chapter 23's gatehouse a castle, the Dragon's Gate in tan bricks with no dirt, Chapter 21's courtyard cobbled", () => {
    const fort = find(FE6_MAPS, 'fe6-23')
    expect([at(fort, 5, 32), at(fort, 6, 32), at(fort, 7, 32), at(fort, 5, 31), at(fort, 6, 31), at(fort, 7, 31)])
      .toEqual(['ca', 'cb', 'cc', 'cg', 'bd', 'ci'])
    const gate = find(FE7_MAPS, 'fe7-e-19')
    expect(codes(gate).has('w3')).toBe(false)
    expect(count(gate, 'w5')).toBeGreaterThan(100)
    expect(count(gate, 'ga')).toBe(0)
    const yard = find(FE7_MAPS, 'fe7-e-21')
    expect(count(yard, 'gb')).toBeGreaterThan(40)
    expect([at(yard, 1, 2), at(yard, 2, 3)]).toEqual(['ga', 'ga'])
    expect(at(find(FE7_MAPS, 'fe7-lyn-2'), 1, 5)).toBe('t0')
  })

  it("keeps a carpet a floor, not boards, and a shore's sand its grains' colour", () => {
    expect(count(find(FE6_MAPS, 'fe6-6'), 'gi')).toBe(0)
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(find(FE8_MAPS, 'fe8-eirika-9').fills!.tk!.slice(i, i + 2), 16))
    expect(r).toBeGreaterThan(b)
    expect(g).toBeGreaterThan(b)
  })
})
