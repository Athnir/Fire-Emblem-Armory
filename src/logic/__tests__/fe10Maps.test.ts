import { describe, expect, it } from 'vitest'
import { FE10_MAPS } from '../../data/fe10/fe10Maps'
import { FE10_MAP_SET } from '../../data/fe10/fe10MapSet'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { terrainAt, terrainInfo } from '../maps'

const byId = (id: string) => FE10_MAPS.find((m) => m.id === id)!
const on = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally').filter(on(d)).length

// Starting foes on Normal, counted from fireemblemwod.com's overview of each map (the red markers, plus the
// boss's own). 'Hard' in the data is the game's Normal and Hard, which place the same units.
const WOD: Record<string, number> = {
  'fe10-1-prologue': 8,
  'fe10-1-1': 11,
  'fe10-1-3': 19,
  'fe10-1-4': 13,
  'fe10-1-5': 27,
  'fe10-1-6-1': 14,
  'fe10-1-7': 25,
}

describe("Radiant Dawn's Part 1 maps, from the game's own files", () => {
  it('lists Part 1 in order, with Ch.6 as its two maps', () => {
    expect(FE10_MAPS.map((m) => m.heading)).toEqual([
      '1-Prologue', '1-1', '1-2', '1-3', '1-4', '1-5', '1-6', '1-6', '1-7', '1-8', '1-9', '1-Endgame',
    ])
    expect(FE10_MAP_SET.chapterLabel(byId('fe10-1-1'))).toBe('Part 1, Chapter 1: Maiden of Miracles')
    expect(FE10_MAP_SET.chapterLabel(byId('fe10-1-prologue'))).toBe('Part 1, Prologue: Under Gray Skies')
  })

  it("matches fireemblemwod.com's starting foes", () => {
    for (const [id, n] of Object.entries(WOD)) expect(foes(byId(id), 'Hard'), id).toBe(n)
  })

  it('keeps every unit, starting tile and object on the map', () => {
    for (const m of FE10_MAPS) {
      expect(m.grid).toHaveLength(m.height)
      for (const row of m.grid) expect(row, m.id).toHaveLength(m.width)
      const tiles = [...m.units.map((u) => u.tile), ...m.starts, ...m.objects.map((o) => o.tile),
        ...(m.reinforcements ?? []).flatMap((g) => g.units.map((u) => u.tile))]
      for (const [x, y] of tiles) {
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} (${x}, ${y})`).toBe(true)
        expect(terrainInfo(m, terrainAt(m, [x, y])), `${m.id} (${x}, ${y})`).toBeTruthy()
      }
    }
  })

  it('tells Easy apart: its own goals, units and timings', () => {
    // Ch.1: escape within 10 turns, but on Easy beating the boss wins, and its reinforcements never come.
    const ch1 = byId('fe10-1-1')
    expect(ch1.victory).toBe('Escape within 10 turns (defeat the boss on Easy)')
    expect(ch1.reinforcements!.every((g) => g.units.every((u) => !u.difficulties || !u.difficulties.includes('Normal')))).toBe(true)
    expect(ch1.reinforcements!.map((g) => g.when)).toContain('Turns 9 and 10, player phase')
    // The prologue's Leonardo comes a turn sooner on Easy.
    expect(byId('fe10-1-prologue').joiners![0]).toMatchObject({ name: 'Leonardo', when: { Normal: 'Turn 3, player phase', Hard: 'Turn 4, player phase' } })
    expect(foes(byId('fe10-1-prologue'), 'Normal')).toBe(4)
  })

  it('places your units where the openings leave them, and who the game deploys', () => {
    // Before the base opens (Prologue to Ch.3) everyone is fixed; from Ch.4 on, only those the game names.
    expect(byId('fe10-1-1').forced!.map((f) => f.name)).toEqual(['Edward', 'Leonardo', 'Nolan'])
    expect(byId('fe10-1-4').forced!.map((f) => f.name)).toEqual(['Sothe'])
    // Ch.9: the Black Knight is set down outside the deployment slots.
    expect(byId('fe10-1-9').forced!.map((f) => f.name)).toEqual(['Black Knight'])
    expect(byId('fe10-1-1').lord).toBe('Micaiah')
  })

  it('reads chests, villages, buried treasure, doors and goals', () => {
    expect(byId('fe10-1-1').objects.filter((o) => o.type === 'village').map((o) => o.type === 'village' && o.reward)).toEqual(['Vulnerary', 'Hand Axe'])
    expect(byId('fe10-1-endgame').objects.filter((o) => o.type === 'chest')).toHaveLength(6)
    expect(byId('fe10-1-4').objects.filter((o) => o.type === 'hidden').map((o) => o.type === 'hidden' && o.contents).sort()).toEqual(['Beastfoe', 'Coin', 'Master Seal'])
    expect(byId('fe10-1-4').changes.filter((c) => c.trigger === 'breakable')).toHaveLength(2)
    // Ch.5: a defend tile the enemy wins by reaching, not used on Easy.
    expect(byId('fe10-1-5').objectives.find((o) => o.type === 'defend')!.label).toMatch(/not on Easy/)
    // Ch.9's boss only comes once the rest are beaten.
    expect(byId('fe10-1-9').reinforcements!.at(-1)!.when).toBe('Once every other enemy is defeated')
  })

  it("reads the terrain table: fliers get no bonus, thickets give Avoid 10 and Def 1", () => {
    const t = byId('fe10-1-1').terrain!
    expect(t.f).toMatchObject({ avo: 10, def: 1 })
    expect(t.f!.move.Fliers).toBe(1)
    expect(t.k!.move.Infantry).toBeNull()
    expect(FE10_MAP_SET.moveClasses).toContain('Beast laguz')
  })
})
