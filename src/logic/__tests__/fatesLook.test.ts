import { describe, expect, it } from 'vitest'
import { ALL_MAPS } from '../../data/maps'
import { FATES_TERRAIN } from '../../data/maps/fatesTerrain'
import { rowCodes } from '../maps'

const map = (id: string) => ALL_MAPS.find((m) => m.id === id)!
const codes = (id: string) => map(id).grid.flatMap(rowCodes)

// scripts/fates_ground.py renders each field from above (scripts/fates_art.py) into data-raw/fates-ground.json, which
// scripts/build-fates-terrain.py applies.
describe("Fates' maps as its 3D fields draw them", () => {
  it('gives each map its own colours, its challenge too', () => {
    for (const m of ALL_MAPS) expect(m.fills, m.id).toBeDefined()
    expect(map('fe14b-6-challenge').fills).toEqual(map('fe14b-6').fills)
  })

  it("parts its plains' dirt from their grass, and floors from plains, all working alike", () => {
    expect(codes('fe14b-6').filter((c) => c === 'ga').length).toBeGreaterThan(50) // Birthright 6's paths
    expect(codes('fe14r-24').filter((c) => c === 't1').length).toBeGreaterThan(400) // the castle's floors (床)
    expect(codes('fe14r-24')).not.toContain('ta')
    for (const c of ['ga', 't1'] as const) expect(FATES_TERRAIN[c]!.move, c).toEqual(FATES_TERRAIN.ta!.move)
  })

  it("keeps the app's blue for water the render doesn't draw blue", () => {
    for (const m of ALL_MAPS)
      for (const c of ['tf', 'we', 'wm'] as const) {
        const hex = m.fills?.[c]
        if (!hex) continue
        const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
        expect(b, `${m.id} ${c}`).toBeGreaterThanOrEqual(Math.max(r, g))
      }
  })
})

// The review of every map (2026-11-14): Fates' houses, statues and challenge villages.
describe("Fates' buildings drawn as its art shows them", () => {
  const at = (id: string, x: number, y: number) => rowCodes(map(id).grid[map(id).height - y])[x - 1]
  it('draws a building block as a house over its tiles, the village before it its door mat, with the building numbers', () => {
    // Birthright 13's houses: three by two, each with its village below the middle of its front.
    expect([at('fe14b-13', 8, 11), at('fe14b-13', 9, 11), at('fe14b-13', 10, 11), at('fe14b-13', 8, 10), at('fe14b-13', 9, 10), at('fe14b-13', 10, 10)])
      .toEqual(['ra', 'rb', 'rc', 'rg', 'rh', 'ri'])
    expect(at('fe14b-13', 9, 9)).toBe('oc')
    expect(map('fe14b-13').terrainOverrides?.ra?.move).toEqual(map('fe14b-13').terrainOverrides?.wa?.move ?? FATES_TERRAIN.wa!.move)
  })

  it("draws Birthright 21's walls standing alone two by two as its statues", () => {
    expect(Object.values(map('fe14b-21').decor ?? {}).filter((d) => d === 'statue')).toHaveLength(12)
  })

  it("has a challenge's spent villages in ruins: the house and the village before it", () => {
    const ruins = map('fe14b-13-challenge').ruins ?? []
    expect(ruins).toContain('9,9')
    expect(ruins).toContain('9,10')
    expect(map('fe14b-13').ruins).toBeUndefined()
    // Revelation 10's houses under its snow, uncovered in its challenge, in ruins.
    const snow = map('fe14r-10-challenge')
    expect((snow.ruins ?? []).length).toBeGreaterThan(10)
    for (const k of snow.ruins ?? []) expect(snow.grid[snow.height - Number(k.split(',')[1])].slice(2 * (Number(k.split(',')[0]) - 1), 2 * Number(k.split(',')[0]))).toBe('wa')
  })

  it("draws Birthright 24's dragon statue, Birthright 25's pillars, x21's town of houses parted by their roofs, and Birthright 19's void", () => {
    expect(Object.values(map('fe14b-24').decor ?? {}).filter((d) => d === 'dragon')).toHaveLength(25)
    expect(Object.values(map('fe14b-25').decor ?? {}).filter((d) => d === 'pillar').length).toBeGreaterThanOrEqual(4)
    // Its houses and its town walls are all the game's Edifice: its houses drawn as their roofs from above, each in its render's colour
    // (the user: all roofs), the 26 its render shows.
    expect(Object.values(map('fe14-x21').decor ?? {}).filter((d) => /^roof-/.test(d))).toHaveLength(156)
    expect(map('fe14b-19').fills?.wa).toBe('#0b0b0e')
  })
})

// The user's notes on every Fates map, 2026-11-24.
describe("Fates' maps after the user's ninth look", () => {
  const decor = (id: string, kind: string | RegExp) =>
    Object.entries(map(id).decor ?? {}).filter(([, d]) => (typeof kind === 'string' ? d === kind : kind.test(d))).map(([k]) => k)

  it('reads every bridge off the whole bridge, a turning one tile by tile one way, stone ones as stone', () => {
    for (const m of ALL_MAPS) expect(m.wideBridges, m.id).toBe(true)
    // Chapter 3's bridge jogs at (12, 15)-(12, 16): every tile of it runs east to west.
    expect(map('fe14-3').bridgeSpans?.['12,15']).toBe('ew')
    expect(map('fe14-3').bridgeSpans?.['12,16']).toBe('ew')
    expect(map('fe14-x15').bridgeSpans?.['27,9']).toBe('ns')
    // Conquest 7's and Revelation 20's bridges are stone, the bridge's numbers kept.
    for (const id of ['fe14c-7', 'fe14r-20']) {
      expect(codes(id)).toContain('t8')
      expect(codes(id)).not.toContain('tb')
    }
  })

  it("draws ships' floors as decks and their walls as wood, boats' ends as bows over the water", () => {
    for (const id of ['fe14b-11', 'fe14c-16', 'fe14r-12', 'fe14-x3', 'fe14c-10', 'fe14r-14']) expect(codes(id), id).toContain('t3')
    // No stone on a ship: Paralogue 3's walls are all its wood.
    expect(Object.values(map('fe14-x3').wallLooks ?? {}).every((l) => l === 'wood' || l === 'ship')).toBe(true)
    expect(codes('fe14-x3')).toContain('bz')
    // Every partition on Birthright 12's boats is a boat's end.
    const b12 = map('fe14b-12')
    const partitions = b12.grid.flatMap((r, i) => rowCodes(r).flatMap((c, x) => (c === 'wg' ? [`${x + 1},${b12.height - i}`] : [])))
    expect(partitions.length).toBeGreaterThan(40)
    for (const k of partitions) expect(b12.boatEnds?.[k], k).toBeDefined()
    // Conquest 10's canal walls are a town's low stone walls.
    expect(Object.values(map('fe14c-10').wallLooks ?? {})).toContain('stone')
  })

  it('draws ice crystals and a frozen fountain, yurts, gardens, stalls, roofs and big trees as the art shows them', () => {
    expect(decor('fe14b-17', 'frozenFountain')).toHaveLength(9)
    expect(decor('fe14b-17', 'ice').length).toBeGreaterThan(20)
    expect(decor('fe14b-8', 'roundYurt')).toHaveLength(27)
    expect(decor('fe14b-9', 'zenGarden')).toHaveLength(36)
    expect(decor('fe14b-22', /^stall-/)).toHaveLength(160)
    expect(decor('fe14c-24', 'cherry').length).toBeGreaterThan(100)
    expect(decor('fe14-dlc-76', 'walledHouse')).toHaveLength(6)
    // The DLC's museum plaza has no villages: its buildings are crates and a pedestal.
    expect(codes('fe14-dlc-6b').filter((c) => /^r[a-r]$/.test(c))).toHaveLength(0)
  })

  it("marks the game's obstacles, warps, moving blocks and flame walls", () => {
    // Revelation 13's ten obstacles and Paralogue 21's two (障害物), each its own code, no unit entering.
    expect(codes('fe14r-13').filter((c) => c === 'xa')).toHaveLength(10)
    expect(codes('fe14-x21').filter((c) => c === 'xa')).toHaveLength(2)
    expect(FATES_TERRAIN.xa!.move.Fliers).toBeNull()
    // Revelation 18's eleven warps: (13, 21) is where the sigil at (13, 5) sends a unit.
    expect(map('fe14r-18').warps).toHaveLength(11)
    expect(map('fe14r-18').warps).toContainEqual([[13, 5], [13, 21]])
    expect(map('fe14r-18').decor?.['13,21']).toBe('warpPad')
    // The Rainbow Sage's stairs from its terrain script match the pairs the user checked in the game.
    expect(map('fe14b-19').links).toHaveLength(7)
    // Revelation 23's five blocks, and the floor paved beside their stops.
    expect(map('fe14r-23').notes.some((n) => /5 stone blocks/.test(n))).toBe(true)
    // Revelation 16's flame walls, down on its challenge.
    expect(map('fe14r-16').flameWalls?.length).toBe(178)
    expect(codes('fe14r-16-challenge')).not.toContain('wa')
  })

  it("starts Paralogue 2 with its inner and outer moats dry, as its opening drains them on every route", () => {
    const x2 = map('fe14-x2')
    const at = (x: number, y: number) => rowCodes(x2.grid[x2.height - y])[x - 1]
    expect(at(4, 17)).toBe('te') // the user's tiles, dry in the game
    expect(at(7, 17)).toBe('te')
    expect(codes('fe14-x2').filter((c) => c === 'te')).toHaveLength(82)
    expect(codes('fe14-x2').filter((c) => c === 'tf').length).toBeGreaterThan(0) // the bottom moat stays filled
  })

  it("gives Before Awakening Awakening Chapter 2's road, and Revelation 26's frozen pools their ice", () => {
    expect(codes('fe14-dlc-40').filter((c) => c === 'gb')).toHaveLength(35)
    expect(codes('fe14-dlc-40')).not.toContain('ga')
    expect(codes('fe14r-26-challenge').filter((c) => c === 'sa').length).toBeGreaterThan(0)
  })
})

// The user's tenth look, 2026-11-24.
describe("Fates' maps after the user's tenth look", () => {
  it("draws Revelation 13's docks as wood, Ghostly Gold's partitions as stone, and Birthright 22's top walkway as cobbles", () => {
    expect(codes('fe14r-13').filter((c) => c === 'gi')).toHaveLength(30)
    // Its five pale plank crossings are bridges (the user), the floor's numbers kept.
    expect(map('fe14r-13').bridgeFloors).toHaveLength(10)
    expect(map('fe14r-13').bridgeFloors).toContain('18,14')
    const at = (id: string, x: number, y: number) => rowCodes(map(id).grid[map(id).height - y])[x - 1]
    expect(at('fe14r-13', 3, 4)).toBe('gi')
    expect(at('fe14r-13', 11, 11)).toBe('gi')
    expect(map('fe14-dlc-6a').wallLooks?.['16,10']).toBe('stone')
    expect(at('fe14b-22', 8, 23)).toBe('gb')
    expect(at('fe14b-22', 18, 23)).toBe('gb')
  })

  it("keeps Birthright 9's walls a step darker than its floor", () => {
    const lum = (hex: string) => [1, 3, 5].reduce((s, i) => s + parseInt(hex.slice(i, i + 2), 16), 0)
    for (const id of ['fe14b-9', 'fe14c-18']) expect(lum(map(id).fills!.wa!), id).toBeLessThan(lum(map(id).fills!.t1!))
  })

  it("leaves a challenge's spent village with no house over it bare, and draws Revelation 18's middle sigil there", () => {
    expect(map('fe14r-14-challenge').bareTiles?.sort()).toEqual(['15,21', '2,21'])
    expect(map('fe14r-18-challenge').decor?.['13,5']).toBe('warpSigil')
  })
})
