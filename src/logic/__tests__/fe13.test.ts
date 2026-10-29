import { describe, expect, it } from 'vitest'
import { FE13_ITEM_SOURCES } from '../../data/fe13/fe13ItemSources'
import { FE13_LISTED } from '../../data/fe13/fe13Listed'
import { FE13_MAPS } from '../../data/fe13/fe13Maps'
import { FE13_BLOCK, FE13_STORY } from '../../data/fe13/fe13MapSet'
import { FE13_OPENS } from '../../data/fe13/fe13Opens'
import { FE13_SUPPORTS } from '../../data/fe13/fe13Supports'
import { FE13_MOVE_CLASSES, FE13_TERRAIN } from '../../data/fe13/fe13Terrain'
import { FE13_TRIANGLE } from '../../data/fe13/fe13Triangle'
import { FE13_WEAPONS } from '../../data/fe13/fe13Weapons'
import type { ChapterMap, Difficulty } from '../../data/maps/types'
import { GAMES } from '../../games'
import { rowCodes } from '../maps'
import { reachOf, turnsUpAt } from '../spoiler'
import { trueHit } from '../trueHit'

const DIFFS: Difficulty[] = ['Normal', 'Hard', 'Lunatic']
const map = (id: string) => FE13_MAPS.find((m) => m.id === id)!
const on = (d: Difficulty, u: { difficulties?: Difficulty[] }) => !u.difficulties || u.difficulties.includes(d)
const weapon = (name: string) => FE13_WEAPONS.find((w) => w.name === name)!

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

describe("Awakening's maps", () => {
  it('has the story, the 23 paralogues and the DLC maps the user owns, each its playable size', () => {
    expect(FE13_MAPS.filter((m) => m.route === 'Story').map((m) => m.id)).toEqual([
      'fe13-premonition',
      'fe13-prologue',
      ...Array.from({ length: 25 }, (_, i) => `fe13-${i + 1}`),
      'fe13-endgame',
    ])
    expect(FE13_MAPS.filter((m) => m.route === 'Paralogue')).toHaveLength(23)
    // E020 and E021 aren't in the user's DLC.
    expect(FE13_MAPS.filter((m) => m.route === 'DLC')).toHaveLength(25)
    for (const m of FE13_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
      // The stored grid keeps a one-tile border no unit can stop on; without it, every map is the wiki's size.
      const [, , cols, rows] = WIKI[m.id][0]
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

  it('places every unit inside its map', () => {
    for (const m of FE13_MAPS) {
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each map with the foes the Fire Emblem Wiki lists, and brings in as many later', () => {
    for (const m of FE13_MAPS) {
      DIFFS.forEach((d, i) => {
        const rows = WIKI[m.id]
        const [start, later] = rows[Math.min(i, rows.length - 1)]
        const [ours, oursLater] = counts(m, d)
        expect(ours, `${m.id} ${d} start`).toBe(start)
        if (NO_WIKI_REINFORCEMENTS.has(m.id) || (m.id === 'fe13-par9')) return
        expect(oursLater, `${m.id} ${d} later`).toBe(REINFORCEMENT_EXCEPTIONS[m.id]?.[d] ?? later)
      })
    }
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
    expect(g[0].when).toBe('Turn 3')
    // Chapter 5's turn-4 Wyvern Riders come only from Hard (DifficultyGet >= 1).
    const wyverns = g.find((x) => x.units.some((u) => u.note?.includes('Wyvern')))!
    expect(wyverns.when).toEqual({ Hard: 'Turn 4', Lunatic: 'Turn 4' })
    expect(wyverns.units.every((u) => u.difficulties?.join() === 'Hard,Lunatic')).toBe(true)
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
    expect(weapon('Brave Sword').rules).toContain('Strikes twice in a row')
    expect(weapon('Rapier').effective).toEqual(['fe13-beast', 'armour'])
    expect(weapon('Exalted Falchion').effective).toEqual(['wyvern', 'grima'])
    expect(weapon('Physic').range).toBe('1-Mag/2')
    expect(weapon('Dragonstone').stats).toEqual({ str: 8, mag: 5, skl: 3, spd: 2, def: 10, res: 7 })
    expect(weapon('Ragnell (enemy)').rules).toContain('Never breaks')
    // Forging: any weapon with a worth, but not Mire (its +0 0x08) or a staff.
    expect(weapon('Iron Sword').forge).toBe(true)
    expect(weapon('Mire').forge).toBeUndefined()
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
  })
})
