import { describe, expect, it } from 'vitest'
import { FE13_ITEM_SOURCES } from '../../data/fe13/fe13ItemSources'
import { FE13_LISTED } from '../../data/fe13/fe13Listed'
import { FE13_MAPS } from '../../data/fe13/fe13Maps'
import { FE13_BLOCK, FE13_MAP_SET, FE13_STORY } from '../../data/fe13/fe13MapSet'
import { FE13_OPENS } from '../../data/fe13/fe13Opens'
import { FE13_SUPPORTS } from '../../data/fe13/fe13Supports'
import { FE13_MOVE_CLASSES, FE13_TERRAIN } from '../../data/fe13/fe13Terrain'
import { FE13_TRIANGLE } from '../../data/fe13/fe13Triangle'
import { FE13_WEAPONS } from '../../data/fe13/fe13Weapons'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { GAMES } from '../../games'
import { fe13ForgeCost, fe13ForgeMax } from '../fe13Forge'
import { atStart, rowCodes, terrainInfo, terrainName } from '../maps'
import { reachOf, turnsUpAt } from '../spoiler'
import { trueHit } from '../trueHit'

const DIFFS: Difficulty[] = ['Normal', 'Hard', 'Lunatic']
const map = (id: string) => FE13_MAPS.find((m) => m.id === id)!
const on = (d: Difficulty, u: { difficulties?: Difficulty[] }) => !u.difficulties || u.difficulties.includes(d)
const weapon = (name: string) => FE13_WEAPONS.find((w) => w.name === name)!
/** The armies the game names its soldiers by (MPID_屍兵, MPID_ヴァルム兵...): never a unit's name in the app. */
const ARMIES = ['Risen', 'Valmese', 'Plegian', 'Ruffian', 'Grimleal', 'Feroxi', 'Outrealm', 'Unknown']

/** How many times a group arrives: "Turns 4, 7–8" is three; anything that isn't a list of turns counts once. */
function spawns(when: string): number {
  let n = 0
  for (const piece of when.split('; ')) {
    const turns = piece.match(/^[Tt]urns? ([0-9–, ]+)/)
    if (!turns) {
      n += 1
      continue
    }
    for (const part of turns[1].split(',').map((p) => p.trim()).filter(Boolean)) {
      const [a, b] = part.split('–').map(Number)
      n += b ? b - a + 1 : 1
    }
  }
  return n
}

/** The foes a map starts with on a difficulty, and how many arrive later (each arrival counted). */
function counts(m: ChapterMap, d: Difficulty): [number, number] {
  const start = m.units.filter((u) => u.type !== 'ally' && on(d, u)).length
  let later = 0
  for (const g of m.reinforcements ?? []) {
    const when = typeof g.when === 'string' ? g.when : g.when?.[d]
    if (!when) continue
    later += spawns(when) * g.units.filter((u) => on(d, u)).length
  }
  return [start, later]
}

// From each map's Fire Emblem Wiki page (its ChapData: starting foes, "+N" reinforcements, columns and rows), one row per difficulty
// where they differ (Normal, Hard, Lunatic); one row where all three are the same.
const WIKI: Record<string, [number, number, number, number][]> = {
  'fe13-premonition': [[1, 0, 25, 25]], 'fe13-prologue': [[5, 0, 15, 14], [8, 0, 15, 14], [11, 0, 15, 14]],
  'fe13-1': [[7, 0, 16, 16], [8, 0, 16, 16], [8, 0, 16, 16]], 'fe13-2': [[12, 0, 15, 20], [14, 0, 15, 20], [16, 0, 15, 20]],
  'fe13-3': [[13, 0, 21, 15], [17, 0, 21, 15], [18, 0, 21, 15]], 'fe13-4': [[9, 0, 14, 14]],
  'fe13-5': [[15, 5, 16, 20], [19, 8, 16, 20], [22, 10, 16, 20]], 'fe13-6': [[24, 0, 20, 20]], 'fe13-7': [[19, 3, 20, 16]],
  'fe13-8': [[20, 0, 16, 22], [23, 0, 16, 22], [23, 0, 16, 22]], 'fe13-9': [[17, 6, 20, 20], [19, 6, 20, 20], [21, 8, 20, 20]],
  'fe13-10': [[24, 7, 24, 16], [27, 7, 24, 16], [31, 12, 24, 16]], 'fe13-11': [[22, 18, 20, 26], [22, 20, 20, 26], [22, 25, 20, 26]],
  'fe13-12': [[40, 0, 20, 20], [43, 0, 20, 20], [43, 0, 20, 20]], 'fe13-13': [[26, 13, 16, 26], [29, 17, 16, 26], [29, 22, 16, 26]],
  'fe13-14': [[32, 6, 20, 20], [34, 9, 20, 20], [36, 9, 20, 20]], 'fe13-15': [[31, 0, 20, 16], [33, 0, 20, 16], [37, 0, 20, 16]],
  'fe13-16': [[24, 12, 20, 28], [31, 16, 20, 28], [31, 22, 20, 28]], 'fe13-17': [[30, 12, 25, 25], [37, 20, 25, 25], [37, 24, 25, 25]],
  'fe13-18': [[31, 0, 15, 30], [39, 0, 15, 30], [47, 0, 15, 30]], 'fe13-19': [[35, 20, 29, 20], [40, 24, 29, 20], [44, 48, 29, 20]],
  'fe13-20': [[40, 9, 21, 30], [44, 13, 21, 30], [50, 17, 21, 30]], 'fe13-21': [[29, 28, 21, 28], [33, 32, 21, 28], [37, 48, 21, 28]],
  'fe13-22': [[13, 0, 25, 23]], 'fe13-23': [[26, 12, 25, 25], [34, 12, 25, 25], [41, 15, 25, 25]],
  'fe13-24': [[18, 18, 26, 21], [25, 18, 26, 21], [30, 18, 26, 21]], 'fe13-25': [[39, 46, 29, 27]],
  'fe13-endgame': [[25, 0, 25, 26], [32, 0, 25, 26], [32, 0, 25, 26]],
  'fe13-par1': [[16, 0, 18, 16], [20, 0, 18, 16], [22, 0, 18, 16]], 'fe13-par2': [[18, 0, 22, 22], [21, 0, 22, 22], [23, 0, 22, 22]],
  'fe13-par3': [[17, 0, 22, 16], [20, 0, 22, 16], [22, 0, 22, 16]], 'fe13-par4': [[26, 0, 16, 20], [30, 0, 16, 20], [34, 0, 16, 20]],
  'fe13-par5': [[21, 0, 20, 22], [26, 0, 20, 22], [29, 0, 20, 22]], 'fe13-par6': [[27, 0, 30, 26], [32, 0, 30, 26], [38, 0, 30, 26]],
  'fe13-par7': [[30, 0, 22, 22], [33, 0, 22, 22], [36, 0, 22, 22]], 'fe13-par8': [[19, 17, 20, 22], [23, 21, 20, 22], [27, 25, 20, 22]],
  'fe13-par9': [[24, 0, 20, 24], [28, 0, 20, 24], [32, 0, 20, 24]], 'fe13-par10': [[24, 8, 24, 25], [30, 12, 24, 25], [35, 20, 24, 25]],
  'fe13-par11': [[30, 6, 30, 27], [33, 6, 30, 27], [39, 12, 30, 27]], 'fe13-par12': [[24, 7, 16, 24], [28, 7, 16, 24], [34, 11, 16, 24]],
  'fe13-par13': [[11, 0, 24, 20]], 'fe13-par14': [[17, 29, 20, 20], [23, 29, 20, 20], [29, 31, 20, 20]],
  'fe13-par15': [[27, 0, 25, 30], [32, 0, 25, 30], [36, 0, 25, 30]], 'fe13-par16': [[34, 0, 26, 25], [41, 0, 26, 25], [49, 0, 26, 25]],
  'fe13-par17': [[7, 30, 29, 21], [11, 30, 29, 21], [11, 44, 29, 21]], 'fe13-par18': [[31, 0, 30, 30], [34, 0, 30, 30], [40, 0, 30, 30]],
  'fe13-par19': [[29, 10, 30, 30], [29, 16, 30, 30], [29, 26, 30, 30]], 'fe13-par20': [[36, 0, 26, 26], [38, 0, 26, 26], [42, 0, 26, 26]],
  'fe13-par21': [[30, 0, 17, 28], [36, 0, 17, 28], [40, 0, 17, 28]], 'fe13-par22': [[16, 0, 18, 25]], 'fe13-par23': [[50, 0, 30, 30]],
  'fe13-dlc1': [[10, 0, 30, 13]], 'fe13-dlc2': [[10, 0, 30, 13]], 'fe13-dlc3': [[20, 0, 30, 13]], 'fe13-dlc4': [[18, 0, 22, 22]],
  'fe13-dlc5': [[17, 0, 23, 24]], 'fe13-dlc6': [[40, 0, 25, 29]], 'fe13-dlc7': [[24, 6, 30, 27]], 'fe13-dlc8': [[26, 4, 30, 27]],
  'fe13-dlc9': [[43, 7, 30, 27]], 'fe13-dlc10': [[20, 0, 19, 28]], 'fe13-dlc11': [[30, 0, 19, 28]], 'fe13-dlc12': [[50, 0, 19, 28]],
  'fe13-dlc13': [[30, 0, 24, 24]], 'fe13-dlc14': [[30, 0, 24, 24]], 'fe13-dlc15': [[50, 0, 24, 24]], 'fe13-dlc16': [[48, 26, 28, 30]],
  'fe13-dlc17': [[19, 38, 20, 20]], 'fe13-dlc18': [[37, 31, 25, 25]], 'fe13-dlc19': [[7, 0, 30, 30]], 'fe13-dlc22': [[27, 6, 20, 20]],
  'fe13-dlc23': [[26, 14, 21, 21], [36, 26, 21, 21], [36, 26, 21, 21]], 'fe13-dlc24': [[21, 8, 21, 21]],
  'fe13-dlc25': [[41, 22, 19, 19]], 'fe13-dlc26': [[31, 28, 20, 20], [37, 44, 20, 20], [37, 44, 20, 20]],
  'fe13-dlc27': [[48, 0, 19, 19], [49, 0, 19, 19], [49, 0, 19, 19]],
}

/**
 * Where the game's own scripts and the wiki's headline differ, and why (each checked in the map's files):
 * - Chapter 9: the wiki counts 17 / 19 / 21 after Gangrel and Aversa leave; so does the map (the opening takes them off).
 * - Chapter 19 (Normal): the wiki's turn 4 lists the Hard set; the script adds Reinforce03 and 04 on turn 4 only from Hard
 *   (DifficultyGet >= 1), so Normal has 16, not 20.
 * - Chapter 20 (Lunatic): the headline says +17; the wiki's own list adds up to 18, as the script does.
 * - Chapter 23: the wiki doesn't count Validar coming back once beaten (ReinforceBoss): one more each.
 * - Chapter 25: the wiki's turn 9 (Normal) lists only the four Dark Fliers; Reinforce05 also brings a Warrior and two Berserkers.
 * - Paralogue 9: the wiki's "+10" are villagers Ruger recruits to his side, not reinforcements.
 * - The Future Past 1: the headline says +22; the wiki's own list (turns 2-8) adds up to 24, as the script does.
 * - The Endgame: its reinforcements come every turn from turn 2 without end; the wiki gives no number.
 * - Apotheosis: its foes come in waves the wiki tables on their own; the starting 7 match.
 */
const REINFORCEMENT_EXCEPTIONS: Record<string, Partial<Record<Difficulty, number>>> = {
  'fe13-19': { Normal: 16 },
  'fe13-20': { Lunatic: 18 },
  'fe13-23': { Normal: 13, Hard: 13, Lunatic: 16 },
  'fe13-25': { Normal: 49, Hard: 49, Lunatic: 49 },
  'fe13-dlc25': { Normal: 24, Hard: 24, Lunatic: 24 },
}
const NO_WIKI_REINFORCEMENTS = new Set(['fe13-endgame', 'fe13-dlc19', 'fe13-par13', 'fe13-dlc27'])
/** Foes the wiki counts as reinforcements that the turn-1 opening places before you act (Lost Bloodlines' EnemyDelay groups, Death's
 * Embrace's one): here they stand from the start. */
const OPENING_PLACED: Record<string, number> = { 'fe13-dlc7': 6, 'fe13-dlc8': 4, 'fe13-dlc9': 7, 'fe13-dlc18': 1 }

describe("Awakening's maps", () => {
  it('has the story, the 23 paralogues and the DLC maps the user owns, each its playable size', () => {
    expect(FE13_MAPS.filter((m) => m.route === 'Story').map((m) => m.id)).toEqual([
      'fe13-premonition',
      'fe13-prologue',
      ...Array.from({ length: 25 }, (_, i) => `fe13-${i + 1}`),
      'fe13-endgame',
    ])
    expect(FE13_MAPS.filter((m) => m.route === 'Paralogue')).toHaveLength(23)
    // E020 and E021 were never released: the 25 maps are all of Awakening's DLC.
    expect(FE13_MAPS.filter((m) => m.route === 'DLC')).toHaveLength(25)
    for (const m of FE13_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
      // The stored grid keeps a one-tile border no unit can stop on; without it, every map is the wiki's size (a skirmish its
      // chapter's: it loads the chapter's own grid).
      const [, , cols, rows] = WIKI[m.skirmishOf ?? m.id][0]
      expect([m.width, m.height], m.id).toEqual([cols, rows])
    }
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE13_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE13_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE13_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
    // Forts and gates heal 20%; a fort is Def 2 / Avoid 20, woods Def 1 / Avoid 10 (TerrainCategoryData).
    expect(FE13_TERRAIN.bb).toMatchObject({ def: 2, avo: 20, heal: 20 })
    expect(FE13_TERRAIN.ba).toMatchObject({ def: 1, avo: 10, heal: 0 })
    // Cliffs and peaks are walls to all but fliers; walls stop everyone.
    expect(Object.entries(FE13_TERRAIN.wb!.move).filter(([, v]) => v !== null).map(([k]) => k)).toEqual(['Fliers'])
    expect(Object.values(FE13_TERRAIN.wa!.move).every((v) => v === null)).toBe(true)
    // An icon only on tiles a unit can stand on: no pillar, fort or tree on a tile nobody enters.
    for (const code of ['bh', 'bb', 'ba', 'bz'] as const) expect(Object.values(FE13_TERRAIN[code]!.move).some((v) => v !== null)).toBe(true)
  })

  it('keeps the stats of the tiles no unit can move onto but units are placed on, and says what damaging tiles do', () => {
    // The Endgame's 24 sigils, where foes appear, and Grima's Ire: every movement type's cost is 255, but the game places units there.
    const end = map('fe13-endgame')
    const codes = end.grid.flatMap(rowCodes)
    expect(codes.filter((c) => c === 'oi')).toHaveLength(24)
    expect(codes.filter((c) => c === 'ww')).toHaveLength(1)
    expect(terrainInfo(end, 'oi')).toMatchObject({ name: 'Sigil', def: 1, avo: 10 })
    expect(terrainInfo(end, 'ww')).toMatchObject({ name: 'Ire', def: 3, avo: 20 })
    for (const c of ['oi', 'ww'] as const) expect(Object.values(terrainInfo(end, c).move).every((v) => v === null), c).toBe(true)
    const grima = end.units.find((u) => u.name === 'Grima')!
    expect(end.grid[end.height - grima.tile[1]].slice((grima.tile[0] - 1) * 2, grima.tile[0] * 2)).toBe('ww')
    // map::ProcTerrainDamage (0x39789c): 10 HP at the start of the unit's army's phase, leaving at least 1, fliers too.
    const hazard = terrainInfo(map('fe13-18'), 'dd')
    expect(hazard.note).toBe("A unit on it at the start of its army's phase loses 10 HP, never dropping below 1; fliers too.")
    expect(terrainInfo(map('fe13-18'), 'wp').note).toBe(
      "Only fliers can cross it; a flier on it at the start of its army's phase loses 10 HP, never dropping below 1.",
    )
    // Each tile goes by the game's own name where its code joins several: Chapter 7's cliffs and peaks.
    expect(terrainInfo(map('fe13-7'), 'wb').name).toBe('Cliff / Peak')
    expect(terrainName(map('fe13-7'), [1, 16])).toBe('Peak')
  })

  it('places every unit inside its map', () => {
    for (const m of FE13_MAPS) {
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each map with the foes the Fire Emblem Wiki lists, and brings in as many later', () => {
    for (const m of FE13_MAPS.filter((x) => x.route !== 'Skirmish')) {
      DIFFS.forEach((d, i) => {
        const rows = WIKI[m.id]
        const [wikiStart, wikiLater] = rows[Math.min(i, rows.length - 1)]
        const moved = OPENING_PLACED[m.id] ?? 0
        const [start, later] = [wikiStart + moved, wikiLater - moved]
        const [ours, oursLater] = counts(m, d)
        expect(ours, `${m.id} ${d} start`).toBe(start)
        if (NO_WIKI_REINFORCEMENTS.has(m.id) || (m.id === 'fe13-par9')) return
        expect(oursLater, `${m.id} ${d} later`).toBe(REINFORCEMENT_EXCEPTIONS[m.id]?.[d] ?? later)
      })
    }
  })

  it("names a unit the game calls only by its army by its class, bosses too, and draws a DLC map's heroes as the people they are", () => {
    const all = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
    // An army's name is a label several of a file's characters share, at least one of them without a portrait.
    for (const m of FE13_MAPS) for (const u of all(m)) expect(ARMIES, `${m.id} ${u.name}`).not.toContain(u.name)
    expect(map('fe13-12').units.filter((u) => u.type === 'enemy').map((u) => u.name)).toContain('Cavalier')
    // A boss named by its army goes by its class: Roster Rescue's Risen.
    expect(map('fe13-dlc16').units.find((u) => u.type === 'boss')!.name).toBe('Swordmaster')
    // A DLC map's heroes have no label of their own: named foes and named green units, not plain markers.
    expect(map('fe13-dlc1').units.find((u) => u.name === 'Caeda')!.type).toBe('named')
    const heroes = map('fe13-dlc1').units.filter((u) => ['Marth', 'Alm', 'Ike'].includes(u.name))
    expect(heroes.map((u) => [u.type, u.generic ?? false])).toEqual([['ally', false], ['ally', false], ['ally', false]])
    // A role several characters share stays their name, on a plain marker (Paralogue 3's villagers all have portraits); the Risen
    // Chief's label is its own.
    expect(map('fe13-par3').units.filter((u) => u.name === 'Villager').map((u) => u.generic)).toEqual([true, true, true])
    expect(map('fe13-par3').units.find((u) => u.type === 'boss')!.name).toBe('Risen Chief')
    // Five-Anna Firefight's Annas all have a portrait and nobody carries their label without one: people, not a role.
    expect(map('fe13-dlc17').units.filter((u) => u.name === 'Anna').map((u) => u.generic ?? false)).toEqual(Array(5).fill(false))
  })

  it("gives each foe its gear on the picked difficulty: a slot's level leaves it off, steps it up its series, or forges it", () => {
    const at = (id: string, x: number, y: number) => map(id).units.filter((u) => u.tile[0] === x && u.tile[1] === y)
    const pick = (us: MapUnit[], d: Difficulty) => us.find((u) => on(d, u))!
    // Chapter 1's Fighter at (5, 4) carries a Bronze Axe on Normal and Hard, and a Hammer instead on Lunatic (each slot's level per
    // difficulty, 0x27cd00).
    expect(pick(at('fe13-1', 5, 4), 'Normal').note).toBe('Lv 1: Bronze Axe')
    expect(pick(at('fe13-1', 5, 4), 'Lunatic').note).toBe('Lv 1: Hammer')
    // Lunatic steps Chapter 2's Iron Lances up to Steel (0x27c4c0); one that drops its Iron Lance fights with the Steel one and still
    // drops the Iron one.
    expect(pick(at('fe13-2', 8, 9), 'Lunatic').note).toBe('Lv 2: Steel Lance')
    const dropper = pick(at('fe13-2', 5, 15), 'Lunatic')
    expect([dropper.carries, dropper.drops]).toEqual([['Steel Lance', 'Iron Lance'], ['Iron Lance']])
    // Past Silver a weapon is forged, Mt +4 and Hit +10 a step (0x27c47c), two in Chapter 25 on Lunatic; source lines name the
    // weapon itself.
    const forged = map('fe13-25').units.flatMap((u) => u.carries ?? []).filter((c) => c.includes('forged'))
    expect(forged).toContain('Silver Sword (forged: Mt +4, Hit +10)')
    expect(forged).toContain('Silver Sword (forged: Mt +8, Hit +20)')
    expect(Object.keys(FE13_ITEM_SOURCES).some((k) => k.includes('forged'))).toBe(false)
    // A placement's own level and class replace the person's: The Future Past's children start at level 1.
    expect(map('fe13-dlc25').units.find((u) => u.name === 'Cynthia')!.note).toMatch(/^Lv 1 Falcon Knight/)
  })

  it("says what Hard and Lunatic give units outside your army that their shown level doesn't count", () => {
    expect(map('fe13-1').notesOn!.map((n) => [n.difficulties.join(), n.note])).toEqual([
      ['Hard', "On Hard, units outside your army have 6 more levels' worth of growth than their shown level counts, and a weapon rank of " +
        'at least C in each type their class uses.'],
      ['Lunatic', "On Lunatic, units outside your army have 15 more levels' worth of growth than their shown level counts, every stat gain " +
        'rounded up, and a weapon rank of at least A in each type their class uses.'],
    ])
    // Promoted generic units level 19 more times on every difficulty (0x2ddc48).
    expect(map('fe13-12').notes).toContain("A promoted generic unit has 19 more levels' worth of growth than its shown level counts.")
    expect(map('fe13-1').notes).not.toContain("A promoted generic unit has 19 more levels' worth of growth than its shown level counts.")
    // Lunatic+ is Lunatic's data with foes' extra skills, which the maps don't show: one entry in the bar.
    expect(FE13_MAP_SET.difficulties.map((d) => d.label)).toEqual(['Normal', 'Hard', 'Lunatic / Lunatic+'])
  })

  it('starts each map as its load leaves it, and previews its doors opening', () => {
    const code = (m: ChapterMap, x: number, y: number) => rowCodes(m.grid[m.height - y])[x - 1]
    // Champions of Yore's load razes its third village (TrickSet(22, 11, 8, 4): TerrainData +13), so there's nothing to visit.
    for (const id of ['fe13-dlc1', 'fe13-dlc2', 'fe13-dlc3']) {
      expect(['t0', 'ga'], id).toContain(code(map(id), 22, 3)) // plain, or the dirt its art draws
      expect(map(id).objects.some((o) => o.tile[0] === 22 && o.tile[1] === 3), id).toBe(false)
    }
    // Roster Rescue opens 9 of its walls as it loads (kind 22: x and x+1); Smash Brethren 2 all 8 doors, Smash Brethren 1 two.
    const plain = (c: string) => (c === 'ga' ? 't0' : c)
    expect([code(map('fe13-dlc16'), 14, 26), code(map('fe13-dlc16'), 15, 26), code(map('fe13-dlc16'), 16, 26)].map(plain)).toEqual(['t0', 't0', 'w0'])
    expect(map('fe13-dlc11').objects.filter((o) => o.type === 'door')).toHaveLength(0)
    expect(map('fe13-dlc10').objects.filter((o) => o.type === 'door')).toHaveLength(6)
    // Paralogue 14's phantom villages start hidden.
    expect(map('fe13-par14').objects.filter((o) => o.type === 'village').map((o) => o.tile)).toEqual([[5, 3], [18, 16]])
    // Every door left previews opening, two tiles for models 9, 10, 11, 16 and 18 (0x2b9d4c).
    const doors = FE13_MAPS.flatMap((m) => m.changes.filter((c) => c.id.startsWith('door-')))
    expect(doors).toHaveLength(53)
    // (Paralogue 16's also patch the walls their flags bring down.)
    expect(doors.filter((c) => c.patch!.length >= 2)).toHaveLength(23)
    expect(doors[0].effect).toBe('A locked door: open it with a Door Key or Master Key, or a unit with Locktouch.')
  })

  it("previews what each chapter's script reshapes during the battle", () => {
    const changes = (id: string) => map(id).changes
    // Chapter 18: each islet covers its model's rectangle from its tile (0x2b8f30, the table at 0x460094): 200 of the 202 lava floor
    // tiles turn to hazard, and four chests in them burn to scrap.
    const islets = changes('fe13-18').filter((c) => c.trigger === 'eruption')
    expect(islets).toHaveLength(24)
    expect(islets.flatMap((c) => c.patch!).filter((p) => p.becomes === 'dd')).toHaveLength(200)
    expect(islets.filter((c) => c.effect.includes('burns to scrap'))).toHaveLength(4)
    expect(islets.find((c) => c.effect.includes('Bullion (M)'))!.effect).toContain('turn 7 (enemy phase)')
    // Doors a turn opens: Smash Brethren 1's on turns 3 and 5.
    const opens = changes('fe13-dlc10').filter((c) => c.effect.includes('opens by itself')).map((c) => c.effect.match(/turn (\d+)/)![1])
    expect(opens.sort()).toEqual(['3', '3', '5', '5'])
    // Roster Rescue's walls flip on turns 1-7.
    expect(changes('fe13-dlc16').filter((c) => c.id.includes('-walls-'))).toHaveLength(7)
    // Paralogue 13's turn-1 choice closes two villages by whose offer you take.
    expect(changes('fe13-par13').map((c) => c.effect).filter((e) => e.includes('offer'))).toEqual([
      "The villages at (5, 9) and (11, 9) close on turn 1 if you accept Gyral's offer.",
      "The villages at (5, 15) and (11, 15) close on turn 1 if you accept Dalen's offer.",
    ])
    // Paralogue 14's villages appear one by one, each once the last is visited.
    expect(changes('fe13-par14').filter((c) => c.effect.startsWith('A village appears')).map((c) => c.tile.default)).toEqual([[3, 14], [16, 5]])
    // Paralogue 16: the flag a door sets brings walls down.
    expect(changes('fe13-par16').find((c) => c.id === 'door-2-20')!.effect).toContain('brings down the walls at (8, 20) and (14, 20) for good')
  })

  it('says what sets each arrival off, read from the script, and makes what comes at one moment one group', () => {
    const when = (id: string) =>
      (map(id).reinforcements ?? []).map((g) => (typeof g.when === 'string' ? g.when : (g.when?.Normal ?? g.when?.Hard ?? '')))
    expect(when('fe13-23')).toContain('Once Validar is first defeated')
    expect(when('fe13-17')).toContain('Turn 8, unless your units stand on all of its arrival tiles')
    expect(when('fe13-par13')).toContain("Turn 1, if you accept Gyral's offer")
    expect(when('fe13-par14')).toContain('After the village at (18, 16) is visited, at the start of the next player phase')
    expect(when('fe13-par10')).toContain('After Severa turns against you or Severa talks to Holland, at the start of the next player phase')
    expect(when('fe13-dlc16')).toContain('From turn 7, once fewer than 49 foes are left, at the start of the player phase')
    expect(when('fe13-dlc27')).toContain('Turn 4, and every turn from turn 8')
    // Nothing is left saying only that a condition is met.
    for (const m of FE13_MAPS) for (const t of when(m.id)) expect(t, m.id).not.toMatch(/a condition in the chapter|story event/)
    // Paralogue 8's one handler places its groups at five moments: five groups.
    expect(map('fe13-par8').reinforcements).toHaveLength(5)
  })

  it("plays each opening: turn 1's placements stand from the start, a scripted battle's victim is gone, the gender's Morgan", () => {
    // The Prologue's party comes in the turn-1 opening: placed by the game, with Chrom's tile the lord's start.
    expect(map('fe13-prologue').corrinStart).toEqual([3, 2])
    expect(map('fe13-prologue').forced!.map((f) => f.name)).toEqual(['Chrom', 'Lissa', 'Frederick', 'Avatar'])
    expect(map('fe13-premonition').corrinStart).toBeDefined()
    expect(map('fe13-3').forced).toContainEqual({ name: 'Sumia', tile: [12, 1] })
    // Chapter 7's Hierarch falls in the opening's scripted battle (ev::Battle): not a unit on the map.
    expect(map('fe13-7').units.some((u) => u.type === 'ally')).toBe(false)
    // Paralogue 12 places one Morgan by the Avatar's gender: the other is its stand-in.
    const morgans = map('fe13-par12').units.filter((u) => u.name === 'Morgan')
    expect(morgans).toHaveLength(1)
    expect(morgans[0].standIn).toMatchObject({ name: 'Morgan', when: 'the Avatar is female' })
    // The Future Past 3's turn 1 gives the green Lucina the defeat condition (UnitSetSkill(SID_敗北条件)).
    expect(map('fe13-dlc27').defeat).toBe('Chrom, the Avatar or Lucina is defeated')
  })

  it('says what every talk does, and who joins without one', () => {
    const unit = (id: string, name: string) => [...map(id).units, ...(map(id).reinforcements ?? []).flatMap((g) => g.units)].find((u) => u.name === name)!
    const talks = (id: string, name: string) => map(id).units.filter((u) => u.name === name).map((u) => u.talk)
    expect(talks('fe13-par5', 'Villager')).toEqual([
      'Talk with anyone (gives an Elixir)',
      'Talk with anyone (gives a Spirit Dust)',
      'Talk with anyone (gives a Missiletainn if Owain talks, otherwise a Speed Tonic)',
    ])
    expect(unit('fe13-par9', 'Paladin').talk).toBe('If Ruger talks to it, it turns against you')
    expect(unit('fe13-par10', 'Severa').talk).toBe(
      'Recruit: joins on reaching Holland and talking (Holland then leaves the map); Talk with Chrom or Cordelia (a conversation)',
    )
    expect(unit('fe13-par10', 'Severa').note).toContain('Turns against you if Holland falls before Severa reaches Holland.')
    expect(unit('fe13-par18', 'Gangrel').talk).toBe('Recruit: talk with Chrom three times, one talk a turn')
    expect(unit('fe13-par15', 'Noire').note).toContain('Joins your army at the start of turn 2 (player phase), with a Steel Bow.')
    expect(unit('fe13-par17', 'Tiki').note).toContain('Joins your army after the battle if alive.')
    expect(map('fe13-par14').objects.find((o) => o.tile[0] === 5 && o.tile[1] === 3)).toMatchObject({
      note: 'Visited by Chrom or Miriel, Laurent joins your army. It turns to desert once visited.',
    })
    // A DLC map's reward join (ev::CompleteJoin), by the DLC's own name for it.
    expect(map('fe13-dlc1').notes).toContain('Clearing it adds Pr. Marth to your army.')
    expect(map('fe13-dlc16').notes).toContain('Clearing it adds Palla to your army.')
  })

  it("says what a choice of offers does to the armies, what it brings, and the gold the end gives by it", () => {
    // Paralogue 13's turn 1 (DialogYesNo, asked again until one is taken): ForceUnitTransferExchange(1, 2) trades the armies' sides,
    // ForceUnitTransfer(2, 1) turns the green army; each branch places its own groups, and the third sets the flag the end pays on.
    const par13 = map('fe13-par13')
    expect(par13.notes).toContain(
      "At the start of turn 1 (player phase), Gyral and Dalen each make an offer, asked again until you take one of the three choices: " +
        "accepting Gyral's offer turns Gyral's army green and Dalen's army against you; accepting Dalen's offer leaves the armies as they " +
        "are; turning both offers down turns Dalen's army against you.",
    )
    expect(par13.notes).toContain('Clearing it gives 10,000 gold if you turn both offers down; otherwise 500 gold for each green unit that survives.')
    expect(par13.reinforcements!.map((g) => g.when)).toEqual([
      "Turn 1, if you accept Gyral's offer",
      "Turn 1, if you accept Gyral's offer or turn both offers down",
      "Turn 1, if you accept Dalen's offer",
      "Turn 1, if you accept Dalen's offer or turn both offers down",
    ])
    const dalen = par13.units.find((u) => u.name === 'Dalen')!
    expect(dalen.note).toBe(
      "Lv 13 Paladin: Spear, Bullion (M). Turns against you if you accept Gyral's offer or turn both offers down. It then drops Bullion (M).",
    )
    expect(par13.units.find((u) => u.name === 'Gyral')!.note).toContain("Turns green if you accept Gyral's offer.")
    expect(FE13_ITEM_SOURCES['Bullion (M)']).toContainEqual({
      mapId: 'fe13-par13', kind: 'drop', text: "Dropped by Dalen, if you accept Gyral's offer or turn both offers down",
    })
    // A unit's gear is closed with a full stop before what's said after it.
    const notes = FE13_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].map((u) => u.note ?? ''))
    expect(notes.filter((n) => /[a-z)] (Joins|Turns|Leaves|It then) /.test(n))).toEqual([])
  })

  it("reads each unit's placement AI: thieves, leavers, village raiders and green units' goals", () => {
    const everyone = (id: string) => [...map(id).units, ...(map(id).reinforcements ?? []).flatMap((g) => g.units)]
    // Chapter 11's thief (AI_MV_TrasureToEscape: the chest in field 1, then AI_MI_Escape for the exit in field 3): the torch badge,
    // its exit outlined.
    const thief = map('fe13-11').units.find((u) => u.name === 'Thief')!
    expect(thief.note).toContain('Goes for the chest at (5, 10), empties it, then makes for (20, 6) and leaves the map, never attacking.')
    expect(thief.looter).toBe(true)
    expect(thief.goesTo).toEqual([[20, 6]])
    // Chapter 10's thieves only leave (AI_MV_EscapeSlow): no badge; one waits a turn (AI_AC_Turn 2).
    const leavers = map('fe13-10').units.filter((u) => u.name === 'Thief')
    expect(leavers.every((u) => !u.looter && JSON.stringify(u.goesTo) === '[[2,16]]')).toBe(true)
    expect(leavers.some((u) => u.note!.includes('From turn 2, makes for (2, 16) and leaves the map'))).toBe(true)
    // Paralogue 2's Barbarians (AI_MI_Village with AI_AT_Null), and the village they make for names them.
    const raiders = map('fe13-par2').units.filter((u) => u.looter)
    expect(raiders.length).toBeGreaterThan(0)
    for (const u of raiders) expect(u.note).toContain('Goes for the village at (18, 20) without attacking, razes it, then attacks.')
    expect(map('fe13-par2').objects.find((o) => o.type === 'village' && o.tile[0] === 18 && o.tile[1] === 20)).toMatchObject({
      note: 'Barbarian can raze it before you visit.',
    })
    // Green units' goals: a tile, a talk, a target (by its class where the game names it by its army; "the other" for one's own name).
    expect(everyone('fe13-par3').filter((u) => u.name === 'Villager').every((u) => JSON.stringify(u.goesTo) === '[[1,1]]')).toBe(true)
    expect(everyone('fe13-9').find((u) => u.name === 'Libra')!.note).toContain('Goes to Chrom to talk.')
    expect(everyone('fe13-par8').find((u) => u.name === 'Kjelle')!.note).toContain('Goes for the Archers.')
    expect(map('fe13-par22').units.find((u) => u.type === 'ally' && u.name === 'Aversa')!.note).toContain(
      'From turn 2, goes for the other Aversa.',
    )
    // Foes with a pattern of their own say it (the user's call): sent after one unit (AI_MV_Person), targeting one when they attack
    // (AI_AT_Person, Paralogue 17's AI_AT_X017Enemy), or leaving one out (AI_AT_ExcludePerson, AI_MV_NearestEnemyExcludePerson). What
    // the routines leave unread is said as not confirmed, with the routine's own target.
    expect(map('fe13-6').units.filter((u) => u.note?.includes('Goes for Emmeryn.')).length).toBeGreaterThan(5)
    expect(map('fe13-9').units.some((u) => u.name === 'Soldier' && u.note!.includes('Leaves Libra alone.'))).toBe(true)
    expect(map('fe13-15').units.some((u) => u.note?.includes("Never goes for Say'ri."))).toBe(true)
    expect(map('fe13-par10').units.find((u) => u.name === 'Holland')!.note).toContain('Never attacks Severa.')
    expect(everyone('fe13-par3').some((u) => u.note?.includes('Holds its ground and targets the Villagers when it attacks.'))).toBe(true)
    expect(everyone('fe13-par17').some((u) => u.note?.includes('Targets Tiki when it attacks.'))).toBe(true)
    expect(map('fe13-par17').unconfirmed!.some((n) => n.startsWith('When its foes stop targeting Tiki'))).toBe(true)
    expect(map('fe13-dlc17').unconfirmed!.some((n) => n.startsWith('When its foes stop targeting Anna'))).toBe(true)
    expect(map('fe13-6').unconfirmed!.some((n) => n.includes('AI_AT_Person'))).toBe(true)
    // Paralogue 9's boss heads for the tile its own routine names; whether it attacks there isn't said.
    const ruger = map('fe13-par9').units.find((u) => u.name === 'Ruger')!
    expect(ruger.note).toContain('Heads for (20, 24).')
    expect(ruger.goesTo).toEqual([[20, 24]])
    // The Golden Gaffe's random foes take their templates' escape, which names no exit: the wiki's south, said as not confirmed.
    expect(map('fe13-dlc4').units.every((u) => u.note!.endsWith('Makes for the south edge of the map and leaves it, never attacking.'))).toBe(true)
    expect(map('fe13-dlc4').unconfirmed!.some((n) => n.includes('AI_MI_Escape'))).toBe(true)
    // Every tile a unit heads for is on its map.
    for (const m of FE13_MAPS)
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
        for (const g of u.goesTo ?? []) expect(g[0] >= 1 && g[0] <= m.width && g[1] >= 1 && g[1] <= m.height, `${m.id} ${u.name}`).toBe(true)
  })

  it("names the boss to beat, and who else mustn't fall", () => {
    expect(map('fe13-3').victory).toBe('Defeat Raimi')
    expect(map('fe13-1').victory).toBe('Rout the enemy')
    // Chapter 23 sets no win rule: the game's default, rout.
    expect(map('fe13-23').victory).toBe('Rout the enemy')
    expect(map('fe13-6').defeat).toBe('Chrom, the Avatar or Emmeryn is defeated')
    expect(map('fe13-3').defeat).toContain('door keys')
    expect(map('fe13-5').defeat).toBe('Chrom or the Avatar is defeated')
  })

  it("times reinforcements from the chapter's script, by difficulty", () => {
    const g = map('fe13-5').reinforcements!
    // A reinforcement handler runs as the player phase starts on Normal and the enemy phase on Hard and Lunatic (0x3b7908).
    expect(g[0].when).toEqual({ Normal: 'Turn 3', Hard: 'Turn 3, enemy phase', Lunatic: 'Turn 3, enemy phase' })
    // Chapter 5's turn-4 Wyvern Riders come only from Hard (DifficultyGet >= 1).
    const wyverns = g.find((x) => x.units.some((u) => u.name.includes('Wyvern')))!
    expect(wyverns.when).toEqual({ Hard: 'Turn 4, enemy phase', Lunatic: 'Turn 4, enemy phase' })
    // One entry per difficulty where the gear differs: Lunatic steps their lances up.
    expect(wyverns.units.every((u) => u.difficulties?.length && !u.difficulties.includes('Normal'))).toBe(true)
    // Paralogue 22's shadows copy your units; the Endgame's sigils pick their foe at random.
    expect(map('fe13-par22').units.some((u) => u.note?.startsWith('Takes the form of one of your units'))).toBe(true)
    expect(map('fe13-endgame').reinforcements!.flatMap((x) => x.units).every((u) => u.name === 'Random foe')).toBe(true)
  })

  it('shows recruits by talk, joiners, villages, chests, event tiles and the lava islets', () => {
    const tharja = map('fe13-9').units.find((u) => u.name === 'Tharja')!
    expect(tharja.talk).toBe('Recruit: talk with Chrom')
    expect(map('fe13-1').joiners!.map((j) => j.name)).toEqual(['Sully', 'Virion'])
    expect(map('fe13-8').objects).toContainEqual(expect.objectContaining({ type: 'village', reward: 'Rescue' }))
    expect(map('fe13-6').objects).toContainEqual(expect.objectContaining({ type: 'chest', contents: 'Secret Book' }))
    // Every main chapter but the Endgame has two event tiles.
    for (const m of FE13_MAPS.filter((x) => x.route === 'Story' && x.id !== 'fe13-endgame' && x.id !== 'fe13-premonition'))
      expect(m.objects.filter((o) => o.type === 'event'), m.id).toHaveLength(2)
    expect(map('fe13-endgame').objects.filter((o) => o.type === 'event')).toHaveLength(0)
    // Chapter 18: 24 lava events (one per turn and phase for turns 1-12), on the islets its script names.
    expect(map('fe13-18').changes.filter((c) => c.trigger === 'eruption')).toHaveLength(24)
    expect(map('fe13-23').changes.find((c) => c.trigger === 'event')?.effect).toContain('Validar')
  })
})

describe("Awakening's weapons", () => {
  it("reads the item table's numbers", () => {
    expect(weapon('Iron Sword')).toMatchObject({ rank: 'D', mt: 5, hit: 95, crit: 0, uses: 40, worth: 520, range: '1' })
    expect(weapon('Levin Sword').rules).toContain("Deals magic damage: its attack uses the wielder's Mag and the foe's Res")
    // ISID_魔法武器 outside the tomes: marked as magic on the weapon page too.
    for (const name of ['Levin Sword', 'Shockstick', 'Bolt Axe']) expect(weapon(name).magic, name).toBe(true)
    expect(weapon('Fire').magic).toBeUndefined()
    // The brave bit is read for both sides' strikes (0x2f36a4).
    expect(weapon('Brave Sword').rules).toContain('Strikes twice in a row, attacking or defending')
    // The use check: the Falchions to SID_主人公 or SID_旧マルス, the Parallel Falchion to SID_マルス (Lucina) or SID_旧マルス.
    expect(weapon('Falchion').rules).toContain('Chrom and the Lodestar Marth only')
    expect(weapon('Exalted Falchion').rules).toContain('Chrom and the Lodestar Marth only')
    expect(weapon('Parallel Falchion').rules).toContain('Lucina and the Lodestar Marth only')
    // ISID_下剋上 (0x21a90c): +15 Hit and Avoid while the wielder's level is lower, a promoted class's counting 20 more.
    expect(weapon('Underdog Bow').rules).toContain(
      "Hit and Avoid +15 while its wielder's level is below the foe's (a promoted class's level counts 20 more)",
    )
    expect(weapon('Rapier').effective).toEqual(['fe13-beast', 'armour'])
    expect(weapon('Exalted Falchion').effective).toEqual(['wyvern', 'grima'])
    expect(weapon('Physic').range).toBe('1-Mag/2')
    expect(weapon('Dragonstone').stats).toEqual({ str: 8, mag: 5, skl: 3, spd: 2, def: 10, res: 7 })
    expect(weapon('Ragnell (enemy)').rules).toContain('Never breaks')
    // Forging: anything but a staff that isn't ISID_錬成不可 (the forge check, 0x263cbc): not Mire, the stones or the legendary weapons.
    expect(weapon('Iron Sword').forge).toBe(true)
    for (const name of ['Mire', 'Dragonstone', 'Beaststone+', 'Falchion']) expect(weapon(name).forge, name).toBeUndefined()
    // Weapons sold for a quarter of their worth (the event-tile pool) say so.
    expect(FE13_LISTED.find((w) => w.name === 'Glass Sword')!.sell).toBe(150)
  })

  it('lists where each weapon turns up, shops by location from the chapter after', () => {
    const iron = FE13_ITEM_SOURCES['Iron Sword']
    expect(iron).toContainEqual({ mapId: 'fe13-5', kind: 'town-shop-later', text: 'Sold at the shop in Border Pass' })
    expect(FE13_ITEM_SOURCES['Exalted Falchion']).toContainEqual(expect.objectContaining({ mapId: 'fe13-24' }))
    expect(FE13_ITEM_SOURCES['Glass Sword']).toContainEqual(expect.objectContaining({ kind: 'event-tile' }))
    expect(FE13_ITEM_SOURCES['Mercurius']).toContainEqual(expect.objectContaining({ kind: 'renown', text: 'Renown reward (3,000 renown)' }))
    // Foe-only: carried by foes, and nothing drops or gives them.
    const foeOnly = FE13_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toContain("Grima's Truth")
    expect(foeOnly).toContain('Ragnell (enemy)')
    expect(foeOnly).not.toContain('Ragnell')
  })

  it("says when each gift comes, on what condition and to whom, from the checks whose jump it sits inside", () => {
    const gift = (item: string, id: string) => FE13_ITEM_SOURCES[item].filter((s) => s.mapId === id && s.kind.includes('gift')).map((s) => s.text)
    expect(gift('Exalted Falchion', 'fe13-24')).toEqual(['Given at the end of the chapter'])
    expect(FE13_ITEM_SOURCES['Exalted Falchion']).toContainEqual(expect.objectContaining({ mapId: 'fe13-24', kind: 'gift-later' }))
    // A count at or above a number, each threshold its own check (the rewards stack); a unit's kills, and that it's alive.
    expect(gift('Ladle', 'fe13-par3')).toEqual(['Given at the end of the chapter, if 3 or more green units survive'])
    expect(gift('Fortify', 'fe13-par7')).toEqual(['Given at the end of the chapter, if 5 or more villagers survive'])
    expect(gift('Hammerne', 'fe13-par6')).toEqual(['Given at the end of the chapter, if Inigo defeats 5 or more foes and survives'])
    expect(gift('Fortify', 'fe13-par20')).toEqual(['Given at the end of the chapter, if Emmeryn is alive'])
    // A check that guards only a scene or a join before the gifts doesn't make them conditional.
    expect(gift('Bullion (L)', 'fe13-par22')).toEqual(['Given at the end of the chapter'])
    expect(gift("Naga's Tear", 'fe13-par12')).toEqual(['Given at the end of the chapter'])
    // To a unit the script names; a talk's gift by who talks (the branch after UnitIsPID is everyone else).
    expect(gift('Dragonstone+', 'fe13-par17')).toEqual(['Given at the end of the chapter, if Tiki is alive, to Tiki'])
    expect(gift('Steel Bow', 'fe13-par15')).toEqual(['Given at the start of turn 2 (player phase), if Noire is alive, to Noire'])
    expect(gift('Missiletainn', 'fe13-par5')).toEqual(['Given in a talk with a villager, if Owain talks'])
    expect(gift('Speed Tonic', 'fe13-par5')).toEqual(['Given in a talk with a villager, if anyone but Owain talks'])
    // A recruit who joins during the battle (a talk, a turn, the end) brings their gear from the next chapter; one placed on your side
    // from the start, from this one.
    expect(FE13_ITEM_SOURCES['Javelin'].filter((s) => s.kind.startsWith('kit')).map((s) => [s.mapId, s.kind, s.text])).toEqual([
      ['fe13-3', 'kit-later', 'Carried by Kellam when they join'],
      ['fe13-7', 'kit-later', 'Carried by Cordelia when they join'],
    ])
    expect(FE13_ITEM_SOURCES['Ruin']).toContainEqual({ mapId: 'fe13-13', kind: 'kit', text: 'Carried by Henry when they join' })
    // Paralogue 14's Goddess Staff: an area handler on one desert tile, once the third village that appears is visited.
    expect(map('fe13-par14').objects.find((o) => o.type === 'hidden')).toEqual({
      type: 'hidden', tile: [9, 18], area: [9, 18, 9, 18], contents: 'Goddess Staff',
      note: 'One of your units that enters this tile gets it, once the village at (16, 5) is visited.',
    })
    expect(FE13_ITEM_SOURCES['Goddess Staff']).toContainEqual({ mapId: 'fe13-par14', kind: 'hidden', text: 'Hidden on the map' })
    expect(FE13_ITEM_SOURCES['Goddess Staff'].filter((s) => s.mapId === 'fe13-par14')).toHaveLength(1)
  })

  it('prices and limits the forge as the program does', () => {
    // 0x26bce0: the worth times each stat's n(n+1)/2, added up, then halved: an odd worth loses at most 1 in all.
    expect(fe13ForgeCost(1175, { mt: 1, hit: 1, crit: 0 })).toBe(1175)
    expect(fe13ForgeCost(520, { mt: 5, hit: 3, crit: 0 })).toBe((520 * (15 + 6)) / 2)
    // 0x263cbc: 5 steps a stat, 8 in all, the forged Mt held at 30, Hit at 200, Crit at 50.
    const none = { mt: 0, hit: 0, crit: 0 }
    expect(fe13ForgeMax('mt', none, 5)).toBe(5)
    expect(fe13ForgeMax('mt', none, 27)).toBe(3)
    expect(fe13ForgeMax('crit', none, 45)).toBe(1)
    expect(fe13ForgeMax('hit', { mt: 5, hit: 0, crit: 0 }, 70)).toBe(3)
  })

  it("lists the DLC's random rewards with each item's chance, so no weapon a chest can give is foe-only", () => {
    // Infinite Regalia's chests give one of 31 (ItemGetRandomLimit, 0x3b4d00: +38 3 and the Bolt Axe), so every legendary weapon can be
    // had; the other DLC villages and chests one of 143 (ItemGetRandom, 0x3b31dc: +38 1 twice as likely as 2).
    const legendary = ['Luna', 'Vengeance', 'Astra', 'Nidhogg', 'Double Bow', 'Tyrfing', 'Mystletainn', 'Gáe Bolg', 'Hauteclere', 'Armads',
      'Mjölnir', 'Forseti', 'Excalibur', 'Book of Naga']
    for (const name of legendary) {
      const w = FE13_LISTED.find((x) => x.name === name)
      expect(w, name).toBeDefined()
      expect(w!.foeOnly, name).toBeUndefined()
      expect(FE13_ITEM_SOURCES[name], name).toContainEqual(expect.objectContaining({ mapId: 'fe13-dlc6', kind: 'dlc-chest', text: 'Sometimes in a chest (3.2%)' }))
    }
    expect(map('fe13-dlc6').objects.flatMap((o) => (o.type === 'chest' ? [o.contents] : []))).toEqual(Array(3).fill('Random item (the game picks one of 31)'))
    expect(map('fe13-dlc1').objects.filter((o) => o.type === 'village' && o.reward.startsWith('random item'))).toHaveLength(2)
    expect(FE13_ITEM_SOURCES['Silver Sword']).toContainEqual(
      expect.objectContaining({ mapId: 'fe13-dlc1', kind: 'dlc-village', text: 'Sometimes given at a village (0.7%)' }),
    )
    // SpotPass's gifts and teams stay out: nothing says SpotPass.
    expect(Object.values(FE13_ITEM_SOURCES).flat().some((x) => /SpotPass/i.test(x.text))).toBe(false)
  })

  it('names a foe in a source line by its class where the game names it only by its army', () => {
    const texts = Object.values(FE13_ITEM_SOURCES).flat().map((s) => s.text)
    for (const army of ARMIES) expect(texts.filter((t) => new RegExp(`by (a foe )?${army}$`).test(t)), army).toEqual([])
    expect(texts).toContain('Dropped by a foe Paladin')
    // A person's several records share a label, every one with a portrait: Chapter 23's two Validars stay a person.
    expect(texts).toContain('Dropped by Validar')
    expect(texts.some((t) => t.endsWith('a foe Validar'))).toBe(false)
  })

  it("says what a foe carries only where nothing else gives it, on the DLC maps too", () => {
    // Grima's Expiration and the Risen's Blighted weapons are carried in the main game, so they show without the DLC switch.
    for (const name of ['Expiration', 'Blighted Claws', 'Blighted Talons'])
      expect(FE13_ITEM_SOURCES[name].some((s) => s.kind === 'foe'), name).toBe(true)
    const foe = (s: { kind: string }) => s.kind.replace(/^dlc-/, '').startsWith('foe')
    const holds = (s: { difficulties?: string[] }, d: string) => !s.difficulties || s.difficulties.includes(d)
    for (const [name, list] of Object.entries(FE13_ITEM_SOURCES))
      for (const d of ['Normal', 'Hard', 'Lunatic'])
        if (list.some((s) => !foe(s) && holds(s, d))) expect(list.filter((s) => foe(s) && holds(s, d)), `${name} on ${d}`).toEqual([])
  })

  it('shows under the block what the side maps give from the chapter they open at, and no map says at its start who comes later', () => {
    const at = (id: string) => FE13_BLOCK.maps.findIndex((m) => m.id === id)
    const first = (name: string) =>
      Math.min(...FE13_ITEM_SOURCES[name].filter((s) => !s.kind.startsWith('dlc')).map((s) => turnsUpAt(FE13_BLOCK, s.mapId, s.kind.endsWith('-later'))))
    // Paralogues 18-23 open once Chapter 25 is cleared, at the Endgame, the story's last chapter: what their recruits bring (Priam's
    // Ragnell, Walhart's Wolf Berg) counts from there, not past the story's end.
    expect(FE13_BLOCK.opensAt!('fe13-par23')).toBe(at('fe13-endgame'))
    expect(first('Ragnell')).toBe(at('fe13-endgame'))
    expect(first('Wolf Berg')).toBe(at('fe13-endgame'))
    // A side map is played before the chapter it opens at, so what a talk on it gives is yours there (Paralogue 5, after Chapter 13);
    // a story chapter's end gives from the next (Chapter 24's Exalted Falchion).
    expect(first('Missiletainn')).toBe(at('fe13-14'))
    expect(first('Exalted Falchion')).toBe(at('fe13-25'))
    // At its start no map says who comes later: Chapter 23's barrier falls "once Validar is defeated", not "first". (A skirmish's
    // groups stand on the map from the start.)
    for (const m of FE13_MAPS.filter((x) => x.route !== 'Skirmish')) {
      const s = atStart(m)
      const texts = [...s.notes, ...(s.unconfirmed ?? []), ...s.changes.map((c) => c.effect), ...s.units.map((u) => `${u.note ?? ''} ${u.talk ?? ''}`)]
      expect(texts.filter((x) => /Group \d|first defeated|arrives|reinforce|foes come/i.test(x)), m.id).toEqual([])
    }
    expect(map('fe13-23').changes.find((c) => c.id === 'fe13-23-barrier')!.effect).toBe('The barrier of light falls once Validar is defeated.')
  })

  it("lists the world map's skirmishes in a dropdown of their own, each at its location", () => {
    // scripts/Encount.cmb: the chapter's own grid, its <key>E placement file's start tiles and two groups of Risen the game fills.
    const sk = FE13_MAPS.filter((m) => m.route === 'Skirmish')
    expect(sk).toHaveLength(49)
    expect(FE13_MAP_SET.third).toMatchObject({ label: 'Skirmishes' })
    expect(FE13_MAP_SET.third!.maps).toHaveLength(49)
    expect(FE13_MAP_SET.extras!.maps.some((m) => m.route === 'Skirmish')).toBe(false)
    const longfort = map('fe13-3-skirmish')
    expect(longfort).toMatchObject({ title: 'The Longfort', skirmishOf: 'fe13-3', victory: 'Rout the enemy' })
    expect(longfort.starts).toHaveLength(8)
    expect(longfort.foeGroups!.map((g) => [g.label, g.tiles.length])).toEqual([['Group 1', 14], ['Group 2', 14]])
    expect(longfort.units.filter((u) => u.name === 'Merchant')).toHaveLength(4)
    expect(longfort.grid).toEqual(map('fe13-3').grid)
    for (const m of sk) {
      expect(m.starts.length, m.id).toBeGreaterThan(0)
      expect(m.foeGroups!.every((g) => g.tiles.length > 0), m.id).toBe(true)
    }
    // A chapter's skirmish comes once the chapter is cleared; a paralogue's with the paralogue.
    const at = (id: string) => FE13_BLOCK.maps.findIndex((m) => m.id === id)
    expect(FE13_BLOCK.opensAt!('fe13-3-skirmish')).toBe(at('fe13-4'))
    expect(FE13_BLOCK.opensAt!('fe13-par1-skirmish')).toBe(FE13_BLOCK.opensAt!('fe13-par1'))
  })

  it('opens each side map once the chapter before it is cleared', () => {
    expect(FE13_OPENS['fe13-par1']).toBe('fe13-3')
    expect(FE13_OPENS['fe13-dlc1']).toBe('fe13-4')
    const at = (id: string) => FE13_BLOCK.maps.findIndex((m) => m.id === id)
    expect(FE13_BLOCK.opensAt!('fe13-par1')).toBe(at('fe13-4'))
    expect(turnsUpAt(FE13_BLOCK, 'fe13-par1')).toBe(at('fe13-4'))
    expect(reachOf(FE13_BLOCK, at('fe13-3')).has('fe13-par1')).toBe(false)
    expect(reachOf(FE13_BLOCK, at('fe13-4')).has('fe13-par1')).toBe(true)
    expect(FE13_STORY.short(map('fe13-par5'))).toBe('Par.5')
    expect(FE13_STORY.name(map('fe13-prologue'))).toBe('Prologue')
  })
})

describe("Awakening's battle numbers", () => {
  it('rolls hit with two numbers (the battle round, 0x268d8c)', () => {
    expect(GAMES.find((g) => g.id === 'fe13')!.hitSystem).toBe('2rn')
    expect(trueHit('2rn', 80).trueHitBasisPoints).toBe(9220)
  })

  it("reads the triangle and rank bonuses from GameData", () => {
    expect(FE13_TRIANGLE.beats).toEqual({ Sword: ['Axe'], Lance: ['Sword'], Axe: ['Lance'] })
    expect(FE13_TRIANGLE.advantage).toEqual({ E: [0, 5], D: [0, 5], C: [0, 10], B: [1, 10], A: [1, 15] })
    expect(FE13_TRIANGLE.rankBonus.Sword).toMatchObject({ C: [1, 0], B: [2, 0], A: [3, 0] })
    expect(FE13_TRIANGLE.rankBonus.Axe).toMatchObject({ C: [0, 5], B: [0, 10], A: [1, 10] })
  })

  it('reads dual support from PartnerEnhanceData', () => {
    expect(FE13_SUPPORTS.rows).toHaveLength(13)
    expect(FE13_SUPPORTS.rows[1]).toEqual([10, 0, 0, 0])
    expect(FE13_SUPPORTS.rows[12]).toEqual([20, 20, 20, 20])
    expect(FE13_SUPPORTS.perLevel).toEqual({ none: 1, C: 2, B: 3, A: 4, S: 5 })
    expect(FE13_SUPPORTS.max).toBe(12)
    // The four allies beside the unit and its pair-up partner (at most a tile away, 0x2aee64).
    expect(FE13_SUPPORTS.supporters).toBe(5)
  })

  it("reads dual strikes, dual guards and pair-up from the battle code", () => {
    // 0x3eeee0: the two units' stats added and divided by 4, a step by support level (the jump table at 0x3ef0cc), 10 for the skill.
    expect(FE13_SUPPORTS.dualStrike).toEqual({ perLevel: { none: 20, C: 30, B: 40, A: 50, S: 60 }, skill: 10 })
    expect(FE13_SUPPORTS.dualGuard).toEqual({ perLevel: { none: 0, C: 2, B: 5, A: 7, S: 10 }, skill: 10 })
    // 0x2b2c8c: the partner's stat / 10 (3 at most), the class's bonus and (support level + 1) / 2 where it gives one, Defender's 1.
    expect(FE13_SUPPORTS.pairUp).toEqual({ statStep: 10, statCap: 3, perLevel: { none: 0, C: 1, B: 1, A: 2, S: 2 }, defender: 1 })
  })
})

describe("Awakening's maps drawn as the game draws them (scripts/fe13_art.py, fe13_ground.py)", () => {
  const codes = (id: string) => map(id).grid.flatMap(rowCodes)
  const all = new Set(FE13_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
  it('keeps the kinds the game names apart (plain, waste, floor; wall, edifice, mast; ship, building, bones)', () => {
    for (const c of ['t0', 't1', 'w0', 'w9'] as const) expect(all.has(c), c).toBe(true)
    for (const c of ['ta'] as const) expect(all.has(c), c).toBe(false)
    for (const c of ['te', 't1', 'ga'] as const) if (FE13_TERRAIN[c]) expect(FE13_TERRAIN[c]!.move, c).toEqual(FE13_TERRAIN.t0!.move)
  })
  it("gives each map its own colours and its plains' dirt, but the two it can't draw yet", () => {
    for (const m of FE13_MAPS.filter((m) => !/^fe13-(endgame|18)(-skirmish)?$/.test(m.id))) expect(m.fills, m.id).toBeDefined()
    expect(map('fe13-endgame').fills).toBeUndefined()
    // Chapter 2's paler ground is its cobbled roads (the user's call: paving, with the plain's numbers).
    expect(codes('fe13-2').filter((c) => c === 'gb').length).toBeGreaterThan(50)
    expect(FE13_TERRAIN.gb!.move).toEqual(FE13_TERRAIN.t0!.move)
    // A building over a village is its house, drawn whole (Chapter 8's three), with the walls' numbers.
    expect(codes('fe13-8').filter((c) => c === 'rh')).toHaveLength(3)
    expect(FE13_TERRAIN.rh!.move).toEqual(FE13_TERRAIN.w0!.move)
    expect(map('fe13-2').fills?.tg).toBeUndefined() // its river, left to effects the render skips, keeps the app's blue
  })
})
