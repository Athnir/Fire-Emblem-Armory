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
  'fe10-2-2': 25,
}

// The turns reinforcements arrive on Normal / Hard, from fireemblemwod.com's walkthrough of each chapter. Left out:
// 1-6 part 1 (WoD skips a turn-5 repeat the script has), 1-9 (WoD has its last waves a turn later: still to check
// in-game), 3-12 (WoD: turn 4; the script: turn 5), 3-Endgame (WoD stops at turn 7), 4-5 (Izuka's summons, not
// scripted), Endgame (1) (the script adds a turn-10 wave) and Endgame (4) and (5) (spirit waves up to turn 100).
const WOD_TURNS: Record<string, number[]> = {
  'fe10-1-2': [8, 10],
  'fe10-1-3': [2, 7, 9, 11, 12],
  'fe10-1-4': [5, 7],
  'fe10-1-5': [2, 3, 4, 5],
  'fe10-1-7': [2, 10, 12],
  'fe10-1-8': [2, 3, 4, 5, 6, 8],
  'fe10-1-endgame': [2, 3, 4, 6, 7, 10],
  'fe10-2-1': [8],
  'fe10-2-2': [6],
  'fe10-2-3': [4, 6, 7, 8, 12, 13],
  'fe10-2-endgame': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
  'fe10-3-1': [4, 5, 6],
  'fe10-3-2': [6, 7, 8, 9],
  'fe10-3-3': [1, 2, 3, 4, 9, 11, 14],
  'fe10-3-4': [7],
  'fe10-3-5': [3, 4, 5, 6, 7, 8, 9, 10],
  'fe10-3-6': [3, 4, 5, 6, 7, 8],
  'fe10-3-7': [4, 5, 6, 7, 9, 10],
  'fe10-3-8': [6, 7],
  'fe10-3-9': [2, 4, 6, 7, 8, 9, 10],
  'fe10-3-10': [3, 4],
  'fe10-3-13': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  'fe10-4-prologue': [2, 3, 4, 5, 6, 7, 8, 10, 11],
  'fe10-4-1': [2, 3, 4, 5, 6, 7, 8, 9, 12],
  'fe10-4-2': [2, 5, 6, 7, 8, 10, 12, 13],
  'fe10-4-3': [2, 5, 7, 8, 9, 10, 11, 14, 15, 16],
  'fe10-4-4': [5, 7, 8, 9, 11, 12, 14, 15],
  'fe10-4-endgame-2': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  'fe10-4-endgame-3': [3, 4, 7, 8, 9, 11, 12, 13],
}

/** The turns a map's reinforcements arrive on one difficulty ('Turns 8–9' is 8 and 9). */
function arrivalTurns(m: ChapterMap, d: Difficulty): number[] {
  const turns = new Set<number>()
  for (const g of m.reinforcements ?? []) {
    if (!g.units.some(on(d))) continue
    const when = typeof g.when === 'object' ? g.when[d] ?? '' : g.when ?? ''
    for (const [, list] of when.matchAll(/Turns? (\d+(?:(?:, | and |–)\d+)*)/g)) {
      for (const part of list.split(/, | and /)) {
        const [a, b = a] = part.split('–').map(Number)
        for (let t = a; t <= b; t++) turns.add(t)
      }
    }
  }
  return [...turns].sort((a, b) => a - b)
}

describe("Radiant Dawn's maps, from the game's own files", () => {
  it('lists every chapter in order, the Endgame as five maps, with Part 1 Ch.6 as its two maps', () => {
    expect(FE10_MAPS.map((m) => m.heading)).toEqual([
      '1-Prologue', '1-1', '1-2', '1-3', '1-4', '1-5', '1-6', '1-6', '1-7', '1-8', '1-9', '1-Endgame',
      '2-Prologue', '2-1', '2-2', '2-3', '2-Endgame', '3-Prologue', '3-1', '3-2', '3-3', '3-4', '3-5', '3-6', '3-7', '3-8',
      '3-9', '3-10', '3-11', '3-12', '3-13', '3-Endgame',
      '4-Prologue', '4-1', '4-2', '4-3', '4-4', '4-5',
      '4-Endgame (1)', '4-Endgame (2)', '4-Endgame (3)', '4-Endgame (4)', '4-Endgame (5)',
    ])
    expect(FE10_MAP_SET.chapterLabel(byId('fe10-1-1'))).toBe('Part 1, Chapter 1: Maiden of Miracles')
    expect(FE10_MAP_SET.chapterLabel(byId('fe10-1-prologue'))).toBe('Part 1, Prologue: Under Gray Skies')
  })

  it("matches fireemblemwod.com's starting foes", () => {
    for (const [id, n] of Object.entries(WOD)) expect(foes(byId(id), 'Hard'), id).toBe(n)
  })

  it("brings reinforcements on the turns fireemblemwod.com gives", () => {
    for (const [id, turns] of Object.entries(WOD_TURNS)) expect(arrivalTurns(byId(id), 'Hard'), id).toEqual(turns)
  })

  it('reads the rest of each win condition from the chapter data and script', () => {
    // A second way to win, stored beside the first ('Defeat boss').
    expect(byId('fe10-2-endgame').victory).toBe('Defend for 15 turns, or defeat the boss')
    expect(byId('fe10-3-5').victory).toBe('Defend for 10 turns, or defeat the boss')
    expect(byId('fe10-3-13').victory).toBe('Hold line for 12 turns, or defeat the boss')
    // 'Defeat enemies': the count the script checks, lower on Easy.
    expect(byId('fe10-3-6').victory).toBe('Defeat 46 enemies (36 on Easy)')
    expect(byId('fe10-3-12').victory).toBe('Defeat 40 enemies (30 on Easy)')
    // Part 3's Endgame also ends once 80 units have died, every side counted.
    expect(byId('fe10-3-endgame').victory).toMatch(/or until 80 units have died/)
    // The commander is your own: 3-12's setup hands the skill to Sigrun, the enemy's.
    expect(byId('fe10-3-12').lord).toBe('Micaiah')
    // 4-4's group comes whoever of Tormod, Muarim and Vika lives; Pelleas only on a later playthrough.
    expect(byId('fe10-4-4').joiners!.every((j) => !/still alive/.test(String(j.when)))).toBe(true)
    expect(byId('fe10-4-2').joiners!.find((j) => j.name === 'Pelleas')!.when).toMatch(/second or later playthrough/)
    expect(byId('fe10-4-5').unconfirmed!.some((u) => /Izuka is a Summoner/.test(u))).toBe(true)
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

  it("reads Part 2: each chapter's own commander, destroyable villages, fog and torches", () => {
    // The setup gives SID_HERO to the chapter's commander.
    expect(['fe10-2-prologue', 'fe10-2-1', 'fe10-2-2', 'fe10-2-3', 'fe10-2-endgame'].map((id) => byId(id).lord)).toEqual(
      ['Elincia', 'Nephenee', 'Lucia', 'Geoffrey', 'Elincia'])
    expect(byId('fe10-2-1').objects.filter((o) => o.type === 'village' && o.note?.match(/Bandits/))).toHaveLength(5)
    expect(byId('fe10-2-2').fog).toBe(true)
    // Torches are lit one at a time from the tile panel, like a Dragon Vein.
    const torches = byId('fe10-2-2').changes.filter((c) => c.trigger === 'torch')
    expect(torches.map((c) => [c.tile.default, c.radius])).toEqual([[[7, 13], 5], [[7, 4], 5], [[19, 13], 5], [[19, 5], 5]])
    // The Endgame's breakable wall has a ledge under it.
    expect(byId('fe10-2-endgame').changes.find((c) => c.trigger === 'breakable' && c.patch?.[0].becomes === 'E')).toBeTruthy()
    expect(byId('fe10-2-endgame').terrain!.E!.note).toMatch(/\+50 Hit/)
    // No preparations screen in Ch.2: everyone is placed by the game.
    expect(byId('fe10-2-2').forced).toHaveLength(7)
    // The prologue's exit is where an enemy carrying Leanne escapes.
    expect(byId('fe10-2-prologue').objectives[0].label).toMatch(/captive/)
    expect(byId('fe10-2-3').objects.filter((o) => o.type === 'ballista' && o.weapon === 'Onager')).toHaveLength(3)
    expect(byId('fe10-2-endgame').objectives.find((o) => o.type === 'defend')!.tiles).toEqual([byId('fe10-2-endgame').corrinStart])
  })

  it('reads roofs, healing jars, clouds and who uses each exit', () => {
    // Houses and the church are in the roof layer (Ch.1); the floor layer has paving under them.
    const ch1 = byId('fe10-1-1')
    const at = (m: ChapterMap, x: number, y: number) => m.grid[m.height - y][x - 1]
    for (const [x, y] of [[5, 3], [8, 4], [7, 2], [8, 2], [1, 14], [2, 14], [14, 14]]) expect(at(ch1, x, y), `(${x}, ${y})`).toBe('B')
    // Ch.7's cells: a plain roof that lifts when a cell is opened, flagged to check rather than called a building.
    expect(byId('fe10-1-7').roofed).toHaveLength(33)
    // Ch.4's jars heal the 4 tiles directly beside them.
    const ch4 = byId('fe10-1-4')
    const jars = ch4.grid.join('').split('I').length - 1
    expect(jars).toBe(4)
    expect(ch4.terrain!.N).toMatchObject({ heal: 20 })
    // Part 2's Prologue: the clouds' full pattern, and sky rather than chasm.
    const p2 = byId('fe10-2-prologue')
    expect(p2.clouds).toMatchObject({ left: 8, turns: 8 })
    expect(p2.clouds!.pattern).toHaveLength(p2.height)
    expect(p2.grid.join('')).not.toMatch(/x/)
    expect(byId('fe10-1-endgame').objectives.map((o) => o.label)).toContain("Where Bandit Thieves escape with what they've looted")
    expect(byId('fe10-2-1').objectives.map((o) => o.label)).toEqual(['Where Heather escapes'])
    expect([byId('fe10-1-prologue').height, byId('fe10-1-6-1').height]).toEqual([10, 18])
  })

  it("reads Part 3's start: torches lit from the outset, supplies to burn, fleeing horses, an arrive tile", () => {
    // Ch.1: fog, and its three torches already lit when the map loads.
    const ch1 = byId('fe10-3-1')
    expect(ch1.fog).toBe(true)
    expect(ch1.changes.filter((c) => c.trigger === 'torch').every((c) => c.lit)).toBe(true)
    // Ch.3: lighting every set of supplies wins (by turn 15, 18 on Easy); not a fog map.
    const ch3 = byId('fe10-3-3')
    expect(ch3.victory).toBe('All supplies burnt by turn 15 (18 on Easy)')
    expect(ch3.fog).toBeFalsy()
    // Six sets of supplies, each an objective of its own (no torches to toggle).
    const burn = ch3.objectives.filter((o) => o.type === 'burn')
    expect(burn).toHaveLength(6)
    expect(burn[0].tiles).toEqual([[2, 29], [2, 28], [1, 29]])
    expect(ch3.changes.some((c) => c.trigger === 'torch')).toBe(false)
    // Each horse runs for the exit its AI names (Cp/cp_data.cms), not the nearest: these two cross the map.
    expect(ch3.objectives.some((o) => o.label.startsWith('Where the Horses flee'))).toBe(true)
    const horse = (x: number, y: number) => ch3.units.find((u) => u.name === 'Horse' && u.tile[0] === x && u.tile[1] === y)!
    expect(horse(13, 18).goesTo).toEqual([[1, 22], [1, 21]])
    expect(horse(1, 18).goesTo).toEqual([[13, 30], [14, 30]])
    expect(ch3.units.filter((u) => u.name === 'Horse').every((u) => u.goesTo?.length === 2)).toBe(true)
    expect(byId('fe10-3-prologue').objectives).toEqual([expect.objectContaining({ type: 'arrive' })])
    expect(byId('fe10-3-prologue').lord).toBe('Ike')
  })

  it("reads the terrain table: fliers get no bonus, thickets give Avoid 10 and Def 1", () => {
    const t = byId('fe10-1-1').terrain!
    expect(t.f).toMatchObject({ avo: 10, def: 1 })
    expect(t.f!.move.Fliers).toBe(1)
    expect(t.k!.move.Infantry).toBeNull()
    expect(FE10_MAP_SET.moveClasses).toContain('Beast laguz')
  })

  it("reads Part 3 Ch.4-7: someone else stands in for a laguz who died earlier; armies' laguz are common foes", () => {
    const ch6 = byId('fe10-3-6')
    const lethe = ch6.units.find((u) => u.name === 'Lethe')!
    expect(lethe.note).toMatch(/If Lethe has died earlier, Kezhda \(Lv 17 Cat\) stands here instead/)
    // Kezhda isn't drawn on her tile as well.
    expect(ch6.units.some((u) => u.name === 'Kezhda')).toBe(false)
    expect(ch6.units.filter((u) => u.name === 'Cat' || u.name === 'Tiger').every((u) => u.type === 'enemy')).toBe(true)
    // Not fitted to fireemblemwod.com's grids yet: each says its edges are still to check.
    for (const id of ['fe10-3-4', 'fe10-3-5', 'fe10-3-6', 'fe10-3-7'])
      expect(byId(id).unconfirmed?.some((n) => /edges/.test(n)), id).toBe(true)
    expect(byId('fe10-3-4').victory).toBe('Ike and Ranulf arrive together')
  })

  it("reads Part 3 Ch.8-11: arsonists and the houses they burn, a non-fighter who walks off, Tibarn's late arrival", () => {
    // Ch.9: six houses the arsonists can set alight (not torches), the arsonists and the fire-fighting knights.
    const ch9 = byId('fe10-3-9')
    expect(ch9.objects.filter((o) => o.type === 'fire')).toHaveLength(6)
    expect(ch9.changes.some((c) => c.trigger === 'torch')).toBe(false)
    expect(ch9.units.some((u) => /sets it alight/.test(u.note ?? ''))).toBe(true)
    expect(ch9.units.filter((u) => u.type === 'ally').every((u) => /nearest fire to put it out/.test(u.note ?? '') || /Bishop/.test(u.note ?? ''))).toBe(true)
    // Ch.10: Valtome doesn't fight and leaves once 7 or fewer enemies are left; he isn't the boss.
    const valtome = byId('fe10-3-10').units.find((u) => u.name === 'Valtome')!
    expect(valtome.type).toBe('named')
    expect(valtome.note).toMatch(/walks off the map once 7 or fewer enemies are left/)
    // Ch.11: Tibarn's hawks come once a unit enters the marked area, carrying Leanne, and losing him then loses.
    const ch11 = byId('fe10-3-11')
    const tibarn = ch11.joiners!.find((j) => j.name === 'Tibarn')!
    expect(tibarn.when).toBe('After a unit enters the marked area')
    expect(tibarn.note).toBe('Carrying Leanne')
    expect(ch11.joiners!.some((j) => j.name === 'Leanne')).toBe(false)
    expect(ch11.defeat).toMatch(/Tibarn dies \(after arriving\)$/)
    // Lose conditions a section's own event adds stay in that section (Fiona joins in Part 1 Ch.6's second map).
    expect(byId('fe10-1-6-1').defeat).not.toMatch(/Fiona/)
    expect(byId('fe10-1-6-2').defeat).toMatch(/Fiona dies \(after arriving\)/)
  })

  it("reads Part 3's end: an army's hawks are common foes, and who comes instead of a companion who died", () => {
    // Phoenicis' hawks share their country's name and a portrait of their own, but come in numbers: soldiers.
    const ch13 = byId('fe10-3-13')
    expect(ch13.units.filter((u) => u.name === 'Hawk').every((u) => u.type === 'enemy')).toBe(true)
    expect(byId('fe10-3-endgame').units.filter((u) => u.name === 'Phoenicis').every((u) => u.generic)).toBe(true)
    // Ch.13: Ike's companions arrive on turns 11 and 12, each with a stand-in if they died; one group each.
    const titania = ch13.reinforcements!.find((g) => g.units.some((u) => u.name === 'Titania'))!
    expect(titania.units.map((u) => u.name)).toEqual(['Titania'])
    expect(titania.units[0].note).toMatch(/If Titania has died earlier, a Tiger comes instead\./)
    expect(ch13.reinforcements!.some((g) => g.units.every((u) => u.name === 'Tiger') && g.when === 'Turn 11, player phase')).toBe(false)
    expect(ch13.victory).toBe('Hold line for 12 turns, or defeat the boss')
  })

  it("reads Part 4 to Ch.5: warped-in reinforcements, fog from lit torches, arrivals and exits that depend on who lives", () => {
    // DisposWarp groups count: Ch.1 and Ch.2 bring in nine groups each; the Black Knight warps in to 3-6.
    expect(byId('fe10-4-1').reinforcements).toHaveLength(9)
    expect(byId('fe10-3-6').joiners!.map((j) => j.name)).toEqual(['Black Knight'])
    // Ch.1: torches lit as the map loads make it a fog map, flagged as inferred.
    const ch1 = byId('fe10-4-1')
    expect(ch1.fog).toBe(true)
    expect(ch1.unconfirmed!.some((n) => /inferred from the torches/.test(n))).toBe(true)
    // Ch.2: Pelleas comes only if he's alive.
    expect(byId('fe10-4-2').joiners!.find((j) => j.name === 'Pelleas')!.when).toBe('Turn 2, player phase, if Pelleas is still alive (only possible on a second or later playthrough)')
    // Ch.3: Lekain leaves on turn 6 and can't be killed, so he isn't a boss the rout needs.
    const lekain = byId('fe10-4-3').units.find((u) => u.name === 'Lekain')!
    expect(lekain.type).toBe('named')
    expect(lekain.note).toMatch(/Leaves the map on turn 6, enemy phase.*Can't be killed/)
    // A check inside a called handler doesn't gate the waves that follow it (3-6's laguz).
    expect(byId('fe10-3-6').reinforcements!.every((g) => !/if .* is still alive/.test(String(g.when)))).toBe(true)
  })

  it("reads the Endgame: the Tower's floors, the spirits that keep warping in, Ashera, and Lehran's condition", () => {
    expect(FE10_MAP_SET.chapterLabel(byId('fe10-4-endgame-1'))).toBe('Part 4, Endgame (1): Rebirth')
    // The Tower's floors, each with its own stats (Endgame (4)'s 防御床３ also gives Avo +15).
    const t = byId('fe10-4-endgame-4').terrain!
    expect(t.A).toMatchObject({ def: 10, avo: 0 })
    expect(t.y).toMatchObject({ def: 10, avo: 15 })
    expect(t.h).toMatchObject({ avo: 15, heal: 10 })
    expect(t.m!.note).toMatch(/Res \+10/)
    // Endgame (5): each turn's spirits come from the group the turn passes to the warp handler.
    const e5 = byId('fe10-4-endgame-5')
    expect(e5.reinforcements!.length).toBeGreaterThan(8)
    expect(e5.units.find((u) => u.name === 'Ashera')!.type).toBe('boss')
    expect(e5.joiners!.find((j) => j.name === 'Lehran')!.when).toMatch(/only on a second or later playthrough/)
    // Seven must go into the Tower, but only Ike (the lord) and Micaiah must be fielded on each floor.
    for (const n of [1, 2, 3, 4, 5]) {
      const m = byId(`fe10-4-endgame-${n}`)
      expect(m.forced!.map((f) => f.name)).toEqual(['Micaiah'])
      expect(m.notes.some((t) => /Only Ike and Micaiah must be fielded/.test(t))).toBe(true)
    }
    // 3-9's fires, confirmed in-game: they don't spread or hurt anyone.
    expect(byId('fe10-3-9').notes.some((n) => /doesn't spread or hurt/.test(n))).toBe(true)
  })
})
