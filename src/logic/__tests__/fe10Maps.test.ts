import { describe, expect, it } from 'vitest'
import { FE10_MAPS } from '../../data/fe10/fe10Maps'
import { FE10_MAP_SET } from '../../data/fe10/fe10MapSet'
import { FE10_TERRAIN } from '../../data/fe10/fe10Terrain'
import type { ChapterMap, Difficulty, MapUnit, ReinforcementGroup } from '../../data/maps/types'
import { defaultDifficulty } from '../../games'
import { applyChanges, closedRooms, noteOn, rowCodes, terrainAt, terrainInfo, withStandIns } from '../maps'

const byId = (id: string) => FE10_MAPS.find((m) => m.id === id)!
const on = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally').filter(on(d)).length
const DIFFS = FE10_MAP_SET.difficulties.map((d) => d.value)

// Starting foes on Normal, counted from fireemblemwod.com's overview of each map (the red markers, plus the
// boss's own). Normal and Hard place the same units.
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

// The turns reinforcements arrive on Normal, from fireemblemwod.com's walkthrough of each chapter. Left out: 1-9 (WoD has
// its last waves a turn later: still to check in-game), 3-12 (WoD: turn 4; the script: turn 5), 3-Endgame (WoD stops at
// turn 7), 4-5 (Izuka's summons, not scripted), Endgame (1) (the script adds a turn-10 wave) and Endgame (4) and (5)
// (spirit waves up to turn 100). 1-6 part 1's turn-5 Pegasus wave, which WoD doesn't list, is Easy's own (its DisposSetMode
// flags are 1, 0, 0).
const WOD_TURNS: Record<string, number[]> = {
  'fe10-1-2': [8, 10],
  'fe10-1-3': [2, 7, 9, 11, 12],
  'fe10-1-4': [5, 7],
  'fe10-1-5': [2, 3, 4, 5],
  'fe10-1-6-1': [2, 3, 4, 7],
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
  it("says where a unit can cross but not stop (TerrainData's byte 7, bit 0x01)", () => {
    const note = (name: string) => Object.values(FE10_TERRAIN).find((t) => t!.name === name)!.note ?? ''
    for (const name of ['Building / object', 'Tree / forest', 'Fence / outer wall', 'Cliff', 'Abyss / waterfall', 'Chest'])
      expect(note(name), name).toMatch(/Fliers can fly over it, but no unit can stop on it/)
    // A flier lands on a rock or in a hole (unlike Path of Radiance's holes); a ledge stops no one but can't be stopped on.
    for (const name of ['Rock', 'Hole']) expect(note(name), name).not.toMatch(/stop/)
    expect(note('Ledge / low cliff')).toMatch(/^Units can cross it, but none can stop on it\. Height counts/)
    // Part 3 Ch.2's rocks and the Tower's abyss are tiles of their own.
    const codes = (id: string) => FE10_MAPS.find((m) => m.id === id)!.grid.join('')
    expect(codes('fe10-3-2')).toMatch(/(..)*wt/)
    expect(codes('fe10-4-endgame-1')).toMatch(/(..)*wv/)
  })

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
    for (const [id, n] of Object.entries(WOD)) expect(foes(byId(id), 'Normal'), id).toBe(n)
  })

  it("brings reinforcements on the turns fireemblemwod.com gives", () => {
    for (const [id, turns] of Object.entries(WOD_TURNS)) expect(arrivalTurns(byId(id), 'Normal'), id).toEqual(turns)
    // Normal and Hard always share their waves: the scripts never tell them apart.
    for (const m of FE10_MAPS) expect(arrivalTurns(m, 'Hard'), m.id).toEqual(arrivalTurns(m, 'Normal'))
  })

  it("says who a village gives nothing to (3-1's house and the three brothers)", () => {
    const house = byId('fe10-3-1').objects.find((o) => o.type === 'village' && o.reward === 'Seraph Robe')!
    expect(house.type === 'village' && house.note).toBe(
      'Visited by Oscar, Boyd or Rolf, it gives nothing: they get a talk of their own instead, which leads to a base conversation later.',
    )
  })

  it('gives each character who can be gone a stand-in, never a second unit on their tile', () => {
    for (const m of FE10_MAPS) {
      for (const d of DIFFS) {
        const tiles = m.units.filter(on(d)).filter((u) => !u.paired).map((u) => u.tile.join(','))
        expect(new Set(tiles).size, `${m.id} ${d}`).toBe(tiles.length)
      }
    }
    // 3-7: Jill and Zihark stay while they're in Micaiah's army; otherwise a Dragonmaster and a Swordmaster.
    const ch7 = byId('fe10-3-7')
    expect(ch7.units.find((u) => u.name === 'Jill')!.standIn).toMatchObject({ name: 'Dragonmaster', type: 'enemy' })
    expect(ch7.units.find((u) => u.name === 'Zihark')!.standIn!.when).toBe("Zihark is no longer in Micaiah's army (died, or joined Ike's side)")
    // Sothe can't die before 3-7 without losing, so 3-7's Lance General never comes; Ike's side can beat him there,
    // so the Endgame's can.
    expect(ch7.units.find((u) => u.name === 'Sothe')!.standIn).toBeUndefined()
    expect(byId('fe10-3-endgame').units.find((u) => u.name === 'Sothe')!.standIn!.when).toBe(
      'Sothe has died earlier (only possible by beating Sothe as a foe in 3-7)',
    )
    // Tauroneo could be fielded (and lost) in Part 1 Ch.7, though its placement file doesn't list him.
    expect(byId('fe10-3-endgame').units.find((u) => u.name === 'Tauroneo')!.standIn).toBeTruthy()
    // 3-6: Kezhda, a Cat who appears nowhere else, stands in for Lethe.
    expect(byId('fe10-3-6').units.find((u) => u.name === 'Lethe')!.standIn).toMatchObject({ name: 'Kezhda', when: 'Lethe has died earlier' })
    // A stand-in's level is Normal's with the others beside it, and the map reads the picked one's (Mordecai's Tiger).
    const mordecai = byId('fe10-3-6').units.find((u) => u.name === 'Mordecai')!
    expect(mordecai.note).toMatch(/a Tiger \(Lv 15 \(Easy 14, Hard 17\)\) stands here instead/)
    expect(DIFFS.map((d) => noteOn(mordecai.standIn!.note!, d))).toEqual([14, 15, 17].map((lv) => `Lv ${lv} Tiger: Fang (Tiger)`))
    // The toggle swaps everyone at once, reinforcements too (3-13's Titania becomes a Tiger).
    const swapped = withStandIns(byId('fe10-3-13'))
    expect(swapped.units.some((u) => u.name === 'Soren')).toBe(false)
    expect(swapped.reinforcements!.flatMap((g) => g.units).some((u) => u.name === 'Titania')).toBe(false)
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
      for (const row of m.grid) expect(row, m.id).toHaveLength(2 * m.width)
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
    expect(ch1.reinforcements!.every((g) => g.units.every((u) => u.difficulties && !u.difficulties.includes('Easy')))).toBe(true)
    expect(ch1.reinforcements!.map((g) => typeof g.when === 'object' && g.when.Normal)).toContain('Turns 9 and 10, player phase')
    // The prologue's Leonardo comes a turn sooner on Easy.
    expect(byId('fe10-1-prologue').joiners![0]).toMatchObject({
      name: 'Leonardo', when: { Easy: 'Turn 3, player phase', Normal: 'Turn 4, player phase', Hard: 'Turn 4, player phase' },
    })
    expect(foes(byId('fe10-1-prologue'), 'Easy')).toBe(4)
  })

  it('offers Easy, Normal and Hard as the game names them, and opens on Normal', () => {
    expect(FE10_MAP_SET.difficulties).toEqual([
      { value: 'Easy', label: 'Easy' }, { value: 'Normal', label: 'Normal' }, { value: 'Hard', label: 'Hard' },
    ])
    expect(defaultDifficulty(FE10_MAP_SET.difficulties)).toBe('Normal')
    expect(JSON.stringify(FE10_MAPS)).not.toMatch(/Normal \/ Hard|on Easy, \d+ on/)
  })

  it('brings each *SetMode wave on the difficulties its flags name (DisposSetMode(group, Easy, Normal, Hard))', () => {
    const group = (id: string, gid: string) => byId(id).reinforcements!.find((g) => g.id === gid)!
    const when = (g: ReinforcementGroup, d: Difficulty) => (g.units.some(on(d)) ? (typeof g.when === 'string' ? g.when : g.when?.[d]) : undefined)
    const timing = (g: ReinforcementGroup) => DIFFS.map((d) => when(g, d))
    // Flags 0, 1, 1: never on Easy.
    for (const [id, gid] of [['fe10-1-2', 'bmap0103_z02'], ['fe10-1-2', 'bmap0103_z03'], ['fe10-1-4', 'bmap0105_z01'],
      ['fe10-1-4', 'bmap0105_z02'], ['fe10-1-8', 'bmap0109_z01']]) {
      const g = group(id, gid)
      expect(when(g, 'Easy'), gid).toBeUndefined()
      expect(when(g, 'Normal'), gid).toBe(when(g, 'Hard'))
      expect(when(g, 'Normal'), gid).toMatch(/^Turn \d+, player phase$/)
    }
    // 1-6: the turn-3 call is Normal's and Hard's, the turn-5 one (flags 1, 0, 0) Easy's.
    expect(timing(group('fe10-1-6-1', 'bmap0107_z02a'))).toEqual(['Turn 5, player phase', 'Turn 3, player phase', 'Turn 3, player phase'])
    // Endgame (2): Easy's waves have calls of their own.
    expect(timing(group('fe10-4-endgame-2', 'bmap0407b_z02'))).toEqual(['Turns 4 and 6, player phase', 'Turns 3 and 6, player phase', 'Turns 3 and 6, player phase'])
    expect(timing(group('fe10-4-endgame-2', 'bmap0407b_z07'))).toEqual(['Turns 11 and 12, player phase', 'Turns 11, 13 and 15, player phase', 'Turns 11, 13 and 15, player phase'])
    for (const gid of ['bmap0407b_z08', 'bmap0407b_z09'])
      expect(timing(group('fe10-4-endgame-2', gid))).toEqual(['Turn 12, player phase', 'Turns 12, 14 and 15, player phase', 'Turns 12, 14 and 15, player phase'])
    // Endgame (3): its turn-3 call places the dragons on every difficulty, the later ones on Normal and Hard only.
    for (const gid of ['bmap0407c_z05', 'bmap0407c_z06']) {
      const [easy, normal, hard] = timing(group('fe10-4-endgame-3', gid))
      expect(easy).toBe('Turn 3, player phase')
      expect(normal).toBe('Turn 3, player phase or Turns 8–9, player phase or Turns 12–13, player phase')
      expect(hard).toBe(normal)
    }
  })

  it("adds the chapter record's 2 levels to Hard's auto-levelled foes, up to the class's highest level", () => {
    // Prologue: the bandits at Lv 1-3 in dispos_h read 2 higher on Hard; Pugo has no auto-level flag and stays Lv 5.
    const prologue = byId('fe10-1-prologue').units
    const bandits = prologue.filter((u) => u.name === 'Bandit' && u.difficulties?.join() !== 'Easy')
    expect(bandits).toHaveLength(7)
    for (const b of bandits) {
      const normal = Number(noteOn(b.note!, 'Normal').match(/^Lv (\d+)/)![1])
      expect([1, 2, 3]).toContain(normal)
      expect(noteOn(b.note!, 'Hard')).toBe(noteOn(b.note!, 'Normal').replace(/^Lv \d+/, `Lv ${normal + 2}`))
    }
    expect(prologue.find((u) => u.name === 'Pugo' && u.difficulties?.includes('Hard'))!.note).toBe('Lv 5 Fighter: Iron Axe, Vulnerary')
    // One entry, Normal's level first: a bandit placed alike on all three is Lv 2, Lv 1 on Easy and Lv 4 on Hard.
    expect(prologue.find((u) => u.name === 'Bandit' && u.tile[0] === 7 && u.tile[1] === 5)!).toMatchObject({ note: 'Lv 2 (Easy 1, Hard 4) Bandit: Bronze Axe, Herb' })
    // Never past the class's highest level (20, or 40 for laguz): Part 2's Endgame soldiers at Lv 20 stay at 20.
    const endgame = byId('fe10-2-endgame').units
    expect(endgame.find((u) => u.name === 'Soldier' && u.tile[0] === 2 && u.tile[1] === 3)!.note).toBe('Lv 20 Soldier: Steel Lance')
    expect(endgame.find((u) => u.name === 'Soldier' && u.tile[0] === 4 && u.tile[1] === 3)!.note).toMatch(/^Lv 19 \(Hard 20\) Soldier/)
    // Hard alone gains it, and only foes: Normal's level is the file's, and no green unit changes.
    const all = FE10_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
    for (const u of all.filter((x) => x.note?.includes('(') && on('Normal')(x) && on('Hard')(x))) {
      const [n, h] = (['Normal', 'Hard'] as Difficulty[]).map((d) => Number(noteOn(u.note!, d).match(/^Lv (\d+)/)![1]))
      expect(h === n || h === n + 2 || h === 20, `${u.name}: ${u.note}`).toBe(true)
      if (u.type === 'ally') expect(h, u.note).toBe(n)
    }
  })

  it("keeps Easy's own goals where its block in the chapter record differs (Normal's and Hard's are the same everywhere)", () => {
    expect(byId('fe10-1-1').victory).toBe('Escape within 10 turns (defeat the boss on Easy)')
    expect(byId('fe10-1-2').victory).toBe('Laura arrives (rout the enemy on Easy)')
    expect(byId('fe10-1-3').victory).toBe('Escape (defeat the boss on Easy)')
    expect(byId('fe10-1-5').victory).toBe('Defend for 6 turns (rout the enemy on Easy)')
    expect(byId('fe10-2-2').victory).toBe('Lucia arrives (defeat the boss on Easy)')
    expect(byId('fe10-3-3').victory).toBe('All supplies burnt by turn 15 (18 on Easy)')
    expect(byId('fe10-1-1').defeat).toBe('Any ally dies, or take more than 10 turns (Easy: Any ally dies)')
    // Only those six, and the two kill counts the scripts set lower on Easy.
    expect(FE10_MAPS.filter((m) => /Easy/.test(m.victory + m.defeat)).map((m) => m.id)).toEqual([
      'fe10-1-1', 'fe10-1-2', 'fe10-1-3', 'fe10-1-5', 'fe10-2-2', 'fe10-3-3', 'fe10-3-6', 'fe10-3-12',
    ])
    expect(FE10_MAPS.some((m) => /\((Normal|Hard)\)/.test(m.victory))).toBe(false)
  })

  it("keeps a unit's difficulties apart where the files tell them apart, not only by level", () => {
    // 3-13: Ike's Ragnell is locked to him on Easy only.
    const ike = byId('fe10-3-13').units.filter((u) => u.name === 'Ike')
    expect(ike.map((u) => [u.difficulties, u.locked, u.note])).toEqual([
      [['Normal', 'Hard'], undefined, 'Lv 20 Hero: Ragnell'],
      [['Easy'], ['Ragnell'], 'Lv 18 Hero: Ragnell'],
    ])
    // Endgame (1): Normal's and Hard's Generals march in from off the map; Easy's are set down where they stand.
    const gens = byId('fe10-4-endgame-1').reinforcements!.flatMap((g) => g.units).filter((u) => u.name === 'Axe Gen' && u.tile.join() === '1,7')
    expect(gens.map((u) => [u.difficulties, u.from])).toEqual([[['Normal', 'Hard'], [-3, 7]], [['Easy'], undefined]])
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
    expect(byId('fe10-2-endgame').changes.find((c) => c.trigger === 'breakable' && c.patch?.[0].becomes === 'bg')).toBeTruthy()
    expect(byId('fe10-2-endgame').terrain!.bg!.note).toMatch(/\+50 Hit/)
    // No preparations screen in Ch.2: everyone is placed by the game.
    expect(byId('fe10-2-2').forced).toHaveLength(7)
    // The prologue's exit is where an enemy carrying Leanne escapes.
    expect(byId('fe10-2-prologue').objectives[0].label).toMatch(/captive/)
    expect(byId('fe10-2-3').objects.filter((o) => o.type === 'ballista' && o.weapon === 'Onager')).toHaveLength(3)
    expect(byId('fe10-2-endgame').objectives.find((o) => o.type === 'defend')!.tiles).toEqual([byId('fe10-2-endgame').corrinStart])
  })

  it('reads roofs, healing jars, clouds and who uses each exit', () => {
    // Houses are in the roof layer (Ch.1); the floor layer has paving under them. Each is drawn as one town house over its tiles.
    const ch1 = byId('fe10-1-1')
    for (const [x, y] of [[5, 3], [8, 4], [7, 2], [8, 2], [1, 14], [2, 14], [14, 14]])
      expect(terrainAt(ch1, [x, y]), `(${x}, ${y})`).toMatch(/^r[a-i]$/)
    // Ch.7's cells and Part 4 Ch.4's treasure rooms: closed rooms under their roof models (as Path of Radiance's and the GBA
    // games'), what's in them unseen until a door beside them opens or breaks; a roof no model covers is a building's own.
    for (const [id, tiles, doors] of [['fe10-1-7', 33, 4], ['fe10-4-4', 63, 3]] as const) {
      const m = byId(id)
      const closed = closedRooms(m)
      expect(closed.size, id).toBe(tiles)
      const opens = m.changes.filter((c) => c.patch?.some((p) => closed.has(`${p.tile[0]},${p.tile[1]}`)))
      expect(opens, id).toHaveLength(doors)
      for (const c of opens) expect(c.effect, c.id).toMatch(/The room behind it opens/)
      const opened = applyChanges(m, new Set(opens.map((c) => c.id)))
      expect(opened.grid.flatMap(rowCodes), id).not.toContain('ws')
    }
    // The cells hold Ch.7's prisoners; the rooms' chests stay under the roof until a door opens.
    expect(byId('fe10-1-7').units.filter((u) => closedRooms(byId('fe10-1-7')).has(`${u.tile[0]},${u.tile[1]}`))).toHaveLength(5)
    const rooms = byId('fe10-4-4')
    expect(rooms.objects.filter((o) => o.type === 'chest' && closedRooms(rooms).has(`${o.tile[0]},${o.tile[1]}`))).toHaveLength(6)
    for (const m of FE10_MAPS) expect(m.roofed, m.id).toBeUndefined()
    expect(byId('fe10-3-prologue').grid.flatMap(rowCodes)).toContain('w7')
    // Ch.4's jars heal the 4 tiles directly beside them.
    const ch4 = byId('fe10-1-4')
    const jars = ch4.grid.flatMap(rowCodes).filter((c) => c === 'hd').length
    expect(jars).toBe(4)
    expect(ch4.terrain!.he).toMatchObject({ heal: 20 })
    // Part 2's Prologue: the clouds' full pattern, and sky rather than chasm.
    const p2 = byId('fe10-2-prologue')
    expect(p2.clouds).toMatchObject({ left: 8, turns: 8 })
    expect(p2.clouds!.pattern).toHaveLength(p2.height)
    expect(p2.grid.flatMap(rowCodes)).not.toContain('wd')
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
    expect(t.ba).toMatchObject({ avo: 10, def: 1 })
    expect(t.ba!.move.Fliers).toBe(1)
    expect(t.wh!.move.Infantry).toBeNull()
    expect(FE10_MAP_SET.moveClasses).toContain('Beast laguz')
  })

  it("reads Part 3 Ch.4-7: someone else stands in for a laguz who died earlier; armies' laguz are common foes", () => {
    const ch6 = byId('fe10-3-6')
    const lethe = ch6.units.find((u) => u.name === 'Lethe')!
    expect(lethe.note).toMatch(/If Lethe has died earlier, Kezhda \(Lv 17 Cat\) stands here instead/)
    // Kezhda isn't drawn on her tile as well.
    expect(ch6.units.some((u) => u.name === 'Kezhda')).toBe(false)
    expect(ch6.units.filter((u) => u.name === 'Cat' || u.name === 'Tiger').every((u) => u.type === 'enemy')).toBe(true)
    expect(byId('fe10-3-4').victory).toBe('Ike and Ranulf arrive together')
  })

  it('cuts each map to the playable grid its file stores (mapdata byte 17: the border, in from every edge)', () => {
    // No map's edges are a guess any more.
    for (const m of FE10_MAPS) expect(m.unconfirmed?.some((t) => /edges/.test(t)) ?? false, m.id).toBe(false)
    const size = (id: string) => [byId(id).width, byId(id).height]
    // Where the user's in-game counts (Part 3 Ch.4-13) and fireemblemwod.com's grids agree with the file, nothing changes.
    expect(size('fe10-3-13')).toEqual([23, 23])
    expect(size('fe10-1-prologue')).toEqual([12, 10])
    // Where they don't, the file wins: 3-4 is 2 rows shorter than counted, 3-6 a column wider; 1-3, 1-Endgame and
    // 2-Endgame are a column or row less than fireemblemwod.com's grid.
    expect(size('fe10-3-4')).toEqual([14, 34])
    expect(size('fe10-3-6')).toEqual([20, 18])
    expect([size('fe10-1-3'), size('fe10-1-endgame'), size('fe10-2-endgame')]).toEqual([[14, 16], [13, 26], [22, 21]])
    // The maps that had only a walk-reach crop: 3-Endgame, Part 4 and the Tower.
    expect([size('fe10-3-endgame'), size('fe10-4-1'), size('fe10-4-endgame-1'), size('fe10-4-endgame-5')]).toEqual([
      [31, 31], [20, 25], [15, 17], [19, 19],
    ])
    // Part 1 Ch.6's two maps share one file, so each keeps its own part.
    expect([size('fe10-1-6-1'), size('fe10-1-6-2')]).toEqual([[26, 18], [28, 22]])
  })

  it('draws the Partner army (army 3) in yellow: it fights beside you, takes the Direct command, and never joins', () => {
    const partners = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].filter((u) => u.yellow)
    const withPartners = FE10_MAPS.filter((m) => partners(m).length || m.joiners?.some((j) => j.yellow))
    expect(withPartners.map((m) => m.id)).toEqual(['fe10-1-3', 'fe10-2-3', 'fe10-2-endgame', 'fe10-3-1', 'fe10-3-6', 'fe10-3-9',
      'fe10-3-11', 'fe10-3-12', 'fe10-3-13'])
    // Each of those maps says what they are, and no other map does.
    expect(FE10_MAPS.filter((m) => m.notes.some((n) => /^Yellow units are partner units: .*Direct command.*None of them joins/.test(n)))).toEqual(withPartners)
    for (const m of withPartners) for (const u of partners(m)) expect(u.type, m.id).toBe('ally')
    // A named partner says it doesn't join; an army's soldiers are plain yellow dots that go by their class.
    expect(partners(byId('fe10-3-1')).map((u) => [u.name, u.note!.endsWith(". A partner unit; doesn't join your army here.")])).toEqual([
      ['Lethe', true], ['Lyre', true],
    ])
    const daein = partners(byId('fe10-3-13'))
    expect(daein.length).toBeGreaterThan(20)
    expect(daein.every((u) => u.generic && u.name !== 'Daein')).toBe(true)
    expect(byId('fe10-3-11').joiners!.filter((j) => j.yellow).map((j) => j.name)).toEqual(['Tibarn', 'Hawk', 'Hawk'])
  })

  it('marks looters with the torch badge: what they go for, and the exits they head for after', () => {
    const marked = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].filter((u) => u.looter)
    expect(FE10_MAPS.filter((m) => marked(m).length).map((m) => m.id)).toEqual(['fe10-1-endgame', 'fe10-2-1', 'fe10-3-9'])
    // Part 1's Endgame: the thieves go for the chests, then leave by the exits the escape objective outlines.
    const endgame = byId('fe10-1-endgame')
    const exits = endgame.objectives.find((o) => /escape/.test(o.label))!.tiles
    for (const u of marked(endgame)) {
      expect(u).toMatchObject({ looter: true, goesTo: exits })
      expect(u.note).toMatch(/\. Goes for the chests, then leaves the map by an exit\.$/)
    }
    // Part 2 Ch.1: the turn-8 bandits go for the villages, the only ones in the game a foe can destroy.
    const bandits = marked(byId('fe10-2-1'))
    expect(bandits.map((u) => [u.name, u.looter])).toEqual([['Bandit', true], ['Bandit', true]])
    expect(bandits.every((u) => u.note!.endsWith('. Goes for the villages, razing what it reaches.'))).toBe(true)
    // Part 3 Ch.9: the arsonists, which the legend names apart.
    const arsonists = marked(byId('fe10-3-9'))
    expect(arsonists).toHaveLength(6)
    expect(arsonists.every((u) => u.looter === 'fire' && /sets it alight\.$/.test(u.note!))).toBe(true)
  })

  it("draws the edge table's fences: sides a ground unit can't cross between two tiles it could walk, which fliers can", () => {
    const fenced = FE10_MAPS.filter((m) => m.walls?.length)
    expect(fenced.map((m) => m.id)).toEqual(['fe10-1-2', 'fe10-1-5', 'fe10-1-7', 'fe10-1-endgame', 'fe10-2-1', 'fe10-3-4', 'fe10-3-5',
      'fe10-3-9', 'fe10-3-12', 'fe10-3-13', 'fe10-4-4'])
    expect(fenced.reduce((n, m) => n + m.walls!.length, 0)).toBe(46)
    // Radiant Dawn's tables never shut a side to fliers.
    expect(fenced.some((m) => m.walls!.some((w) => w.all))).toBe(false)
    // Each lies between two tiles a ground unit can walk: two ledge tiles (no running along a ledge), or 2-1's fence on plain ground.
    const names = (m: ChapterMap) => m.walls!.map(({ tile: [x, y], side }) =>
      [[x, y], side === 'e' ? [x + 1, y] : [x, y - 1]].map((t) => terrainInfo(m, terrainAt(m, t as [number, number]))!.name).join(' | '))
    for (const m of fenced) {
      const expected = m.id === 'fe10-2-1' ? 'Plain | Plain' : 'Ledge / low cliff | Ledge / low cliff'
      expect(new Set(names(m)), m.id).toEqual(new Set([expected]))
    }
  })

  it("reads Part 3 Ch.8-11: arsonists and the houses they burn, a non-fighter who walks off, Tibarn's late arrival", () => {
    // Ch.9: six houses the arsonists can set alight (not torches), the arsonists and the fire-fighting knights.
    const ch9 = byId('fe10-3-9')
    expect(ch9.objects.filter((o) => o.type === 'fire')).toHaveLength(6)
    expect(ch9.changes.some((c) => c.trigger === 'torch')).toBe(false)
    expect(ch9.units.some((u) => /sets it alight/.test(u.note ?? ''))).toBe(true)
    expect(ch9.units.filter((u) => u.type === 'ally').every((u) => /nearest fire to put it out/.test(u.note ?? '') || /Bishop/.test(u.note ?? ''))).toBe(true)
    // Ch.10: Valtome and his guard stand off the playable grid (he walks away partway), so they're left out.
    expect(byId('fe10-3-10').units.some((u) => u.name === 'Valtome')).toBe(false)
    // Ch.8: the floor the script sets burning does 10 damage at the start of the turn.
    const ch8 = byId('fe10-3-8')
    expect(ch8.grid.flatMap(rowCodes).filter((c) => c === 'dd')).toHaveLength(62)
    expect(ch8.terrain!.dd!.note).toBe('A unit that starts its turn here takes 10 damage.')
    // Ch.11: Tibarn's hawks come once a unit enters the marked area, carrying Leanne, as partner units, and losing him then loses.
    const ch11 = byId('fe10-3-11')
    const tibarn = ch11.joiners!.find((j) => j.name === 'Tibarn')!
    expect(tibarn.when).toBe('After a unit enters the marked area')
    expect(tibarn).toMatchObject({ yellow: true, note: "Carrying Leanne. A partner unit; doesn't join your army here." })
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
    // They go by their class, as every army's soldiers do.
    const greenHawks = byId('fe10-3-endgame').units.filter((u) => u.name === 'Hawk' && u.type === 'ally')
    expect(greenHawks.length).toBeGreaterThan(0)
    expect(greenHawks.every((u) => u.generic)).toBe(true)
    expect(FE10_MAPS.some((m) => m.units.some((u) => u.name === 'Phoenicis'))).toBe(false)
    // Ch.13: Ike's companions arrive on turns 11 and 12, each with a stand-in if they died; one group each.
    const titania = ch13.reinforcements!.find((g) => g.units.some((u) => u.name === 'Titania'))!
    expect(titania.units.map((u) => u.name)).toEqual(['Titania'])
    expect(titania.units[0].note).toMatch(/If Titania has died earlier, a Tiger comes instead\./)
    expect(ch13.reinforcements!.some((g) => g.units.every((u) => u.name === 'Tiger') && g.when === 'Turn 11, player phase')).toBe(false)
    expect(ch13.victory).toBe('Hold line for 12 turns, or defeat the boss')
    // Nailah and Rafiel arrive just off the grid; turn 11's event carries Rafiel in, so they show where it leaves them.
    const nailah = ch13.joiners!.find((j) => j.name === 'Nailah')!
    expect(nailah.tile).toEqual([5, 6])
    expect(nailah.note).toBe('Arrives just off the map. On turn 11, Nailah carries Rafiel in to here, then heads for Micaiah.')
    expect(ch13.joiners!.some((j) => j.name === 'Rafiel')).toBe(false)
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
    expect(t.bo).toMatchObject({ def: 10, avo: 0 })
    expect(t.br).toMatchObject({ def: 10, avo: 15 })
    expect(t.hf).toMatchObject({ avo: 15, heal: 10 })
    expect(t.bq!.note).toMatch(/Res \+10/)
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

describe("Radiant Dawn's tiles each drawn as itself, by the game's own terrain names (the user's call)", () => {
  const codes = (id: string) => new Set(FE10_MAPS.find((m) => m.id === id)!.grid.flatMap(rowCodes))

  it('draws plain, floor, paving, snowfield, cave floor and lava each as itself: no plain catch-all is left', () => {
    for (const m of FE10_MAPS) expect(new Set(m.grid.flatMap(rowCodes)).has('ta'), m.id).toBe(false)
    expect(codes('fe10-1-1').has('t4')).toBe(true)
    expect(codes('fe10-4-1').has('t2')).toBe(true)
    expect(['t7', 'wp'].every((c) => codes('fe10-3-8').has(c as never))).toBe(true)
  })

  it("keeps the kinds working as the game has them: a house is one town house's pieces, a market its stalls, each its own stats", () => {
    expect(FE10_TERRAIN.t4!.move).toEqual(FE10_TERRAIN.t0!.move)
    expect(FE10_TERRAIN.ra!.move).toEqual(FE10_TERRAIN.w8!.move)
    expect([...codes('fe10-1-1')].some((c) => /^r[a-i]$/.test(c))).toBe(true)
    // Barrels, crates, odds and ends, and a market's stalls along their row (its ends, or one alone).
    const prologue = codes('fe10-1-prologue')
    for (const c of ['o1', 'o4', 'o5', 'o7', 'o8'] as const) expect(prologue.has(c), c).toBe(true)
    expect(FE10_MAPS.some((m) => m.grid.some((r) => rowCodes(r).includes('o3')))).toBe(true)
    for (const c of ['o3', 'o4', 'o5', 'o6', 'o7', 'o8'] as const) expect(FE10_TERRAIN[c]!.move, c).toEqual(FE10_TERRAIN.o1!.move)
  })

  it("draws a church, a prison camp's barracks and its watchtower as themselves, and a sandy ruin in sandstone", () => {
    // Part 1 Ch.1's church in the town's middle; Part 1 Ch.3's camp, barracks and watchtower.
    expect([...codes('fe10-1-1')].some((c) => /^k[a-i]$/.test(c))).toBe(true)
    expect([...codes('fe10-1-3')].some((c) => /^p[a-i]$/.test(c))).toBe(true)
    expect(codes('fe10-1-3').has('o9')).toBe(true)
    expect(FE10_TERRAIN.ka!.move).toEqual(FE10_TERRAIN.ke!.move)
    // Part 1 Ch.4 is more sand than grass: its castle walls sandstone, its floors sandy, its treasure under sand where it's dug.
    const ruin = byId('fe10-1-4')
    expect(codes('fe10-1-4').has('w5')).toBe(true)
    expect(codes('fe10-1-4').has('w0')).toBe(false)
    expect(ruin.fills?.t1).toBeDefined()
    for (const o of ruin.objects) if (o.type === 'hidden') expect(terrainAt(ruin, o.tile), String(o.tile)).toBe('t5')
    expect(FE10_TERRAIN.w5!.move).toEqual(FE10_TERRAIN.w0!.move)
    // A grassy map keeps its own.
    expect(byId('fe10-1-1').fills).toBeUndefined()
  })
})
