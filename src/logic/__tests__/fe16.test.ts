import { describe, expect, it } from 'vitest'
import { FE16_ITEM_SOURCES } from '../../data/fe16/fe16ItemSources'
import { FE16_SUPPORTS } from '../../data/fe16/fe16Supports'
import { FE16_LISTED } from '../../data/fe16/fe16Listed'
import { FE16_MAPS } from '../../data/fe16/fe16Maps'
import { FE16_FORK, FE16_MAP_SET } from '../../data/fe16/fe16MapSet'
import { FE16_MOVE_CLASSES, FE16_TERRAIN } from '../../data/fe16/fe16Terrain'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { covers, rowCodes, terrainAt, terrainInfo, tileKey } from '../maps'
import { walkFork } from '../spoiler'
import { trueHit } from '../trueHit'

const map = (id: string) => FE16_MAPS.find((m) => m.id === id)!
const on = (u: MapUnit, d: Difficulty) => !u.difficulties || u.difficulties.includes(d)
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && on(u, d))
const count = (m: ChapterMap, d: Difficulty, name: string) => foes(m, d).filter((u) => u.name === name).length
const weapon = (name: string) => FE16_LISTED.find((w) => w.name === name)
const DIFFS: Difficulty[] = ['Normal', 'Hard', 'Maddening']
const totals = (m: ChapterMap) => DIFFS.map((d) => foes(m, d).length)
/** The red army alone: Fire Emblem Wiki counts a third army (yellow) apart. */
const red = (m: ChapterMap) => DIFFS.map((d) => foes(m, d).filter((u) => !u.yellow).length)

describe("Three Houses' White Clouds maps", () => {
  it('has the Prologue and Chapters 1 to 11, Chapters 1, 4, 7 and 11 once per house, each grid its own size', () => {
    expect(FE16_MAPS.filter((m) => m.route === 'Story').map((m) => m.id)).toEqual([
      'fe16-0', 'fe16-1-be', 'fe16-1-bl', 'fe16-1-gd', 'fe16-2', 'fe16-3', 'fe16-4-be', 'fe16-4-bl', 'fe16-4-gd', 'fe16-5', 'fe16-6',
      'fe16-7-be', 'fe16-7-bl', 'fe16-7-gd', 'fe16-8', 'fe16-9', 'fe16-10', 'fe16-11-be', 'fe16-11-bl', 'fe16-11-gd',
    ])
    for (const m of FE16_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The grid stores the playable area's bounds in half tiles (archive file 365 + map): the Prologue's is 21 by 20.
    expect([map('fe16-0').width, map('fe16-0').height]).toEqual([21, 20])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE16_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE16_TERRAIN[code]
      expect(info, code).toBeDefined()
      expect(Object.keys(info!.move).sort(), code).toEqual([...FE16_MOVE_CLASSES].sort())
    }
    // Forest: Prt 1, Avoid 30 (fixed_stagedata.bin's terrain 3).
    expect(FE16_TERRAIN.ba).toMatchObject({ def: 1, avo: 30 })
  })

  it("draws your units' tiles: the slots, Byleth's own and every unit the game places", () => {
    // (An auxiliary battle's ten slots are all the game's 'Player' slots: no tile is Byleth's own.)
    for (const m of FE16_MAPS.filter((x) => x.route !== 'Auxiliary')) {
      const starts = new Set(m.starts.map(tileKey))
      expect(m.corrinStart, m.id).toBeDefined()
      expect(starts.has(tileKey(m.corrinStart!)), m.id).toBe(true)
      for (const f of m.forced ?? []) if (f.tile) expect(starts.has(tileKey(f.tile)), `${m.id} ${f.name}`).toBe(true)
    }
    // The Prologue places Byleth and the three lords; nothing is yours to place.
    expect(map('fe16-0').starts).toHaveLength(4)
    expect(map('fe16-0').forced?.map((f) => f.name)).toEqual(['Edelgard', 'Dimitri', 'Claude'])
    // The mock battle: Byleth, the house's leader and three slots (Fire Emblem Wiki: 2-5 units). The script's two Normal-only slots
    // more are a switched-off event's, and their records are of no army: the game never places them.
    for (const h of ['be', 'bl', 'gd']) {
      expect(map(`fe16-1-${h}`).starts, h).toHaveLength(5)
      expect(totals(map(`fe16-1-${h}`)), h).toEqual([10, 10, 10])
    }
    expect(map('fe16-1-be').forced).toEqual([{ name: 'Edelgard', tile: [16, 6] }])
  })

  it('names the leader beside Byleth in the battles every house plays alike, and says where nothing places them', () => {
    // Chapter 2's opening walks the house's leader onto (12, 27) of the grid; Chapters 3, 5 and 10 leave the leader to a slot.
    expect(map('fe16-2').forced).toEqual([{ name: 'Your house leader (Edelgard, Dimitri or Claude)', tile: [13, 3] }])
    for (const id of ['fe16-3', 'fe16-5', 'fe16-10']) {
      expect(map(id).forced, id).toEqual([{ name: 'Your house leader (Edelgard, Dimitri or Claude)' }])
      expect(map(id).defeat, id).toBe('Byleth or your house leader (Edelgard, Dimitri or Claude) falls in battle')
    }
    expect(map('fe16-8').defeat).toBe('Byleth, your house leader (Edelgard, Dimitri or Claude), or Jeralt falls in battle')
    // Chapter 6's lose condition names Byleth alone: no leader is needed.
    expect(map('fe16-6').forced).toBeUndefined()
    // The Holy Tomb: the Black Eagles' leader is the foe's commander; the others must bring theirs.
    expect(map('fe16-11-be').defeat).toBe('Byleth falls in battle')
    expect(map('fe16-11-be').units.find((u) => u.type === 'boss')?.name).toBe('Edelgard')
    expect(map('fe16-11-bl').units.find((u) => u.type === 'boss')?.name).toBe('Flame Emperor')
    expect(map('fe16-11-bl').forced).toEqual([{ name: 'Dimitri' }])
  })

  it("places the Prologue's foes per difficulty as Fire Emblem Wiki lists them", () => {
    const m = map('fe16-0')
    // Normal: Kostas and 6 Ruffians with Iron Swords (the default weapon a unit with empty slots is given, 0x19e41c).
    expect(count(m, 'Normal', 'Ruffian')).toBe(6)
    expect(foes(m, 'Normal').filter((u) => u.name === 'Ruffian').every((u) => u.carries?.[0] === 'Iron Sword')).toBe(true)
    // Hard: 4 Ruffians (one with an Iron Axe) and 2 Thieves with Iron Axes; Maddening: 4 Ruffians and 4 Thieves.
    expect([count(m, 'Hard', 'Ruffian'), count(m, 'Hard', 'Thief')]).toEqual([4, 2])
    expect([count(m, 'Maddening', 'Ruffian'), count(m, 'Maddening', 'Thief')]).toEqual([4, 4])
    const kostas = m.units.filter((u) => u.name === 'Kostas')
    expect(kostas[0]).toMatchObject({ type: 'boss', carries: ['Iron Axe'], drops: ['Iron Axe'] })
    // The commander is the scenario's level, 3 (Maddening 6); the rest two lower. (Maddening's own entry: its AI waits on other foes.)
    expect(kostas.map((u) => [u.note?.split('; ')[0], u.difficulties])).toEqual([
      ['Lv 3 Thief', ['Normal', 'Hard']],
      ['Lv 6 Thief', ['Maddening']],
    ])
  })

  it("places Chapter 2's foes as the files have them (one more Fighter than Fire Emblem Wiki counts on Normal and Hard)", () => {
    const m = map('fe16-2')
    expect(count(m, 'Normal', 'Thief')).toBe(5)
    expect(count(m, 'Normal', 'Archer')).toBe(3)
    expect(count(m, 'Hard', 'Archer')).toBe(6)
    expect(count(m, 'Maddening', 'Brigand')).toBe(1)
    // Fire Emblem Wiki: 5 Fighters on Normal and Hard, 8 on Maddening. The unit table places records 25-30 from the start on every
    // difficulty and Maddening alone takes record 30 off for a Brigand (event 7), so the files have 6 on Normal and Hard.
    expect(count(m, 'Normal', 'Fighter')).toBe(6)
    expect(count(m, 'Maddening', 'Fighter')).toBe(8)
    // The Fighter whose drop field is 1015 carries the Chest Key (item 1014) and drops it (0x1a0ef8).
    expect(foes(m, 'Normal').find((u) => u.drops?.includes('Chest Key'))?.carries).toEqual(['Iron Axe', 'Chest Key'])
  })

  it('fields the foes Fire Emblem Wiki counts once switched-off events and units of no army are left out', () => {
    // Chapter 9: 4, 5 and 7 Demonic Beasts. A switched-off opening event would place all nine on every difficulty.
    expect(totals(map('fe16-9'))).toEqual([4, 5, 7])
    // Chapter 6: 26, 28 and 32 foes at the start; its one Armored Knight of no army would make each one more.
    expect(totals(map('fe16-6'))).toEqual([26, 28, 32])
    // Chapter 11: 28, 35 and 40.
    for (const h of ['be', 'bl', 'gd']) expect(totals(map(`fe16-11-${h}`)), h).toEqual([28, 35, 40])
    // Chapter 8: Fire Emblem Wiki counts 20 (14 Rampaging Villagers, Commoners as a name no portrait carries goes by the class, and 6
    // soldiers). Records 42 and 47, of rank 6, are reinforcement points: two more villagers 'every third turn starting turn 1' (the
    // wiki), which stop on Normal and Hard after an event and keep coming on Maddening.
    expect(totals(map('fe16-8'))).toEqual([20, 20, 20])
    expect(count(map('fe16-8'), 'Normal', 'Commoner')).toBe(14)
    const villagers = map('fe16-8').reinforcements!.filter((g) => g.units.every((u) => u.name === 'Commoner'))
    const until = 'Turn 1 and every third turn after, until an event in the chapter stops them'
    expect(villagers.map((g) => g.when)).toEqual([{ Normal: until, Hard: until }, { Maddening: 'Turn 1 and every third turn after' }])
    // Their copies come in two levels under the battle's, as the wiki has them (Lv 15 of the battle's 17).
    expect(villagers[0].units[0].note).toBe('Lv 15 (Hard 16)')
  })

  it("swaps a recruited student for a soldier of their class on the same tile (Chapter 7's stand-ins)", () => {
    const felix = map('fe16-7-be').units.find((u) => u.name === 'Felix')!
    expect(felix.standIn).toMatchObject({ name: 'Mercenary', when: 'if you recruited Felix into your house' })
  })

  it("gives the Blue Lions' Rite of Rebirth its own two Myrmidons more (Hard and Maddening, without flag 61)", () => {
    const last = (h: string) => map(`fe16-4-${h}`).reinforcements!.at(-1)!
    expect(last('be').units).toHaveLength(2)
    expect(last('bl').units).toHaveLength(4)
    expect(last('bl').units.every((u) => u.difficulties?.join() === 'Hard,Maddening')).toBe(true)
  })

  it('says each arrival in one sentence, a chain of steps with its areas numbered (Chapter 8)', () => {
    const g = map('fe16-8').reinforcements!.find((x) => x.units.some((u) => u.name === 'Death Knight'))!
    expect(g.when).toBe(
      'At the start of the enemy phase with one of your units, or Jeralt, in area 2, once one of your units has been in area 1 at the ' +
        'start of your phase',
    )
    expect(new Set(g.areas!.map((a) => a.step))).toEqual(new Set([1, 2]))
    // No arrival says the same thing twice.
    for (const m of FE16_MAPS) {
      for (const r of m.reinforcements ?? []) {
        // (Times merged for the same units, said one after another with '; ', may share their words.)
        for (const w of (typeof r.when === 'string' ? [r.when] : Object.values(r.when ?? {})).flatMap((x) => x!.split('; '))) {
          const parts = w.toLowerCase().split(/, (?![^(]*\))/)
          expect(new Set(parts).size, `${m.id} ${w}`).toBe(parts.length)
        }
      }
    }
    expect(map('fe16-3').reinforcements![0].when).toBe('Once the foe Dark Mage at (12, 8) is defeated')
  })

  it("stretches a monster over its square: on the map, on ground units enter, and over no other unit's tiles", () => {
    const square = (u: MapUnit) => {
      const s = u.size ?? 1
      return Array.from({ length: s * s }, (_, k) => [u.tile[0] + (k % s), u.tile[1] - Math.floor(k / s)] as [number, number])
    }
    let monsters = 0
    for (const m of FE16_MAPS) {
      for (const d of DIFFS) {
        const units = m.units.filter((u) => on(u, d))
        for (const u of units.filter((x) => x.size)) {
          monsters++
          for (const t of square(u)) {
            expect(t[0] >= 1 && t[0] <= m.width && t[1] >= 1 && t[1] <= m.height, `${m.id} ${u.name} ${t}`).toBe(true)
            expect(Object.values(terrainInfo(m, terrainAt(m, t)).move).some((c) => c !== null), `${m.id} ${u.name} ${t}`).toBe(true)
            // (Chapter 8's script stacks two Armored Knights on one tile on Hard, so only a monster's square is checked for others.)
            for (const o of units) if (o !== u) expect(covers(o, t), `${m.id} ${d} ${u.name} ${t} ${o.name}`).toBe(false)
          }
        }
      }
    }
    expect(monsters).toBeGreaterThan(0)
    // Chapter 9's Experimental Demonic Beasts are 2 by 2 (the monster table's +56, plus one; Fire Emblem Wiki: size 2); tapping any
    // tile of the square finds the beast.
    const beast = map('fe16-9').units.find((u) => u.size)!
    expect(beast.size).toBe(2)
    expect(covers(beast, [beast.tile[0] + 1, beast.tile[1] - 1])).toBe(true)
    expect(covers(beast, [beast.tile[0] + 2, beast.tile[1]])).toBe(false)
    // Chapter 5: once Miklan falls, the Black Beast stands on his tile (the script walks it in): the battle ends with it.
    const black = map('fe16-5').reinforcements!.flatMap((g) => g.units.map((u) => ({ ...u, when: g.when }))).find((u) => u.name === 'Black Beast')
    expect(black).toMatchObject({ type: 'boss', size: 2, tile: map('fe16-5').units.find((u) => u.name === 'Miklan')!.tile, when: 'Once Miklan is defeated' })
  })

  it("gives each monster its health bars (the monster table's +52; Fire Emblem Wiki: Experimental Demonic Beasts two)", () => {
    for (const m of FE16_MAPS) for (const u of m.units) if (u.size) expect(u.bars, `${m.id} ${u.name}`).toBeGreaterThan(1)
    const beasts = map('fe16-9').units.filter((u) => u.name === 'Exp. Demonic Beast')
    expect(beasts.every((u) => u.bars === 2 && /; 2 health bars(;|$)/.test(u.note ?? ''))).toBe(true)
    // Miklan's Black Beast has three; no one else on the White Clouds maps has any.
    expect(map('fe16-5').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Black Beast')?.bars).toBe(3)
    expect(FE16_MAPS.filter((m) => m.route === 'Story').flatMap((m) => m.units).filter((u) => u.bars && !u.size)).toEqual([])
    // Part II: the Immaculate One is 3 by 3 with four bars (Fire Emblem Wiki), the Hegemon Husk one tile with four.
    expect(map('fe16-37-cf').units.find((u) => u.name === 'The Immaculate One')).toMatchObject({ size: 3, bars: 4 })
    // (Its commander, whose name no other record shows, goes by it: 'Hegemon Edelgard'.)
    const husk = map('fe16-30-am').units.find((u) => u.name === 'Hegemon Edelgard')!
    expect([husk.size, husk.bars]).toEqual([undefined, 4])
  })

  it("marks the Holy Tomb's looters: each takes its Crest Stones, then leaves the map at (11, 1)", () => {
    for (const h of ['be', 'bl', 'gd']) {
      const m = map(`fe16-11-${h}`)
      const stones = m.grid.flatMap((row, r) => rowCodes(row).flatMap((c, x) => (c === 'ow' ? [[x + 1, m.height - r]] : [])))
      expect(stones, h).toHaveLength(20)
      const looters = foes(m, 'Normal').filter((u) => u.looter)
      expect(looters.map((u) => u.name).sort(), h).toEqual([...Array(5).fill('Brigand'), ...Array(5).fill('Thief')])
      // Between them they go for every stone once, and each ends at the exit.
      const taken = looters.flatMap((u) => u.goesTo!.slice(0, -1))
      expect(taken.map(tileKey).sort(), h).toEqual(stones.map((t) => tileKey(t as [number, number])).sort())
      for (const u of looters) expect(u.goesTo!.at(-1), `${h} ${u.name}`).toEqual([11, 1])
      for (const t of taken) expect(terrainAt(m, t), h).toBe('ow')
    }
    expect(map('fe16-11-bl').notes[1]).toBe(
      'When the battle is won: if no Crest Stone is carried off the map, Rusted Bow (Silver Bow), Knowledge Gem and Advanced Seal; if ' +
        '1 to 10 Crest Stones are carried off the map, Advanced Seal; if 11 to 19 Crest Stones are carried off the map, Rusted Bow ' +
        '(Silver Bow); if all 20 Crest Stones are carried off the map, nothing.',
    )
  })
})

// Each route's chapters from 12 (fixed_flow.bin: chapter k's battle, a scenario): the same chapters, in the same order, as Fire Emblem
// Wiki's route pages (Crimson Flower 12-18, Silver Snow 13-21 after the shared 12, Azure Moon and Verdant Wind 13-22).
const PART_TWO: Record<string, string[]> = {
  'Crimson Flower': [31, 32, 33, 34, 35, 36, 37].map((s) => `fe16-${s}-cf`),
  'Silver Snow': [12, 13, 14, 15, 16, 20, 22, 24, 26, 28].map((s) => `fe16-${s}-ss`),
  'Azure Moon': [12, 13, 14, 15, 16, 17, 21, 23, 25, 27, 30].map((s) => `fe16-${s}-am`),
  'Verdant Wind': [12, 13, 14, 15, 16, 17, 20, 22, 24, 26, 29].map((s) => `fe16-${s}-vw`),
}

describe("Three Houses' Part II maps", () => {
  it("plays each route's own battles from Chapter 12, numbered as the game numbers its chapters", () => {
    for (const [route, ids] of Object.entries(PART_TWO)) {
      const maps = FE16_MAPS.filter((m) => m.route === route)
      expect(maps.map((m) => m.id), route).toEqual(ids)
      expect(maps.map((m) => m.chapter), route).toEqual(ids.map((_, k) => 12 + k))
    }
    expect(map('fe16-20-ss').title).toBe('Taking Fort Merceus')
    expect(map('fe16-20-ss').chapter).toBe(17)
  })

  it('fields the foes Fire Emblem Wiki counts at the start of every Part II battle, on each difficulty', () => {
    // Fire Emblem Wiki's map data (each battle page's ChapData 'enemy'): one total per difficulty (Hard's standing for Maddening where
    // a page gives two). Shambhala's is the number the game first shows; the rest wait behind doors.
    const WIKI: Record<string, number[]> = {
      'fe16-31-cf': [19, 22, 22], 'fe16-32-cf': [22, 25, 31], 'fe16-33-cf': [18, 19, 24], 'fe16-34-cf': [20, 20, 20],
      'fe16-35-cf': [30, 33, 42], 'fe16-36-cf': [15, 20, 22], 'fe16-37-cf': [38, 45, 49],
      'fe16-13': [31, 36, 39], 'fe16-14': [31, 35, 36], 'fe16-15': [29, 31, 31], 'fe16-16': [18, 25, 27],
      'fe16-17': [22, 22, 22], 'fe16-20': [30, 37, 37], 'fe16-21-am': [35, 40, 40], 'fe16-23-am': [30, 32, 35],
      'fe16-24': [36, 38, 46], 'fe16-25-am': [38, 41, 48], 'fe16-26': [23, 29, 37], 'fe16-27-am': [43, 46, 53],
      'fe16-28-ss': [33, 42, 42], 'fe16-30-am': [48, 52, 54],
      // Exceptions, each one less than the wiki. Chapter 12 (the other routes'): the wiki counts the repeating Armored Knight among
      // those at the start, though its own notes have it first come on turn 3 (the script places its point then). The Enbarr
      // Infiltration: its Death Knight comes in one of two versions by event flag 71, both shown as groups at the start. Verdant
      // Wind's last battle: an Agarthan Assassin withdraws in the opening scene (its RemoveFromMap), which the wiki still counts.
      'fe16-12': [32, 38, 38], 'fe16-22': [35, 39, 42], 'fe16-29-vw': [44, 47, 52],
    }
    // (The wiki counts the third army, To War at Gronder's yellow units, apart: 'other'.)
    for (const ids of Object.values(PART_TWO)) {
      for (const id of ids) expect(red(map(id)), id).toEqual(WIKI[id] ?? WIKI[id.replace(/-[a-z]{2}$/, '')])
    }
    // Saving Derdriu's green units: the wiki's 5, 5 and 6.
    expect(DIFFS.map((d) => map('fe16-23-am').units.filter((u) => u.type === 'ally' && on(u, d)).length)).toEqual([5, 5, 6])
  })

  it('sends repeating reinforcements from their points (rank 4, 5 or 6: every turn, every other turn, every third turn)', () => {
    // Protecting Garreg Mach: two Falcon Knights south of Randolph on odd-numbered turns (the wiki), a Paladin too on Maddening,
    // until the fire attack stops them; they aren't on the map at the start.
    const g = map('fe16-14-ss').reinforcements!.find((x) => x.units.some((u) => u.name === 'Falcon Knight'))!
    expect(g.when).toBe('Turn 1 and every other turn after, until an event in the chapter stops them')
    expect(g.units.map((u) => [u.name, u.difficulties])).toEqual([
      ['Falcon Knight', undefined],
      ['Falcon Knight', undefined],
      ['Paladin', ['Maddening']],
    ])
    // Chapter 12's Armored Knight from turn 3, every other turn, until the Death Knight falls; the Winged Demonic Beast from turn 9,
    // every third turn, until Hubert does (the wiki's notes).
    const whens = map('fe16-12-am').reinforcements!.map((x) => x.when)
    expect(whens).toContain('Turn 3, then every other turn after, until Death Knight is defeated')
    expect(whens).toContain('Turn 9, then every third turn after, until Hubert is defeated')
    // An area that stops a point isn't one of the group's outlines (those bring it in), so it's said by its corners.
    expect(map('fe16-p60').reinforcements!.map((x) => x.when)).toContain(
      'Every turn, until one of your units has entered the area from (21, 16) to (29, 21) or the foe Brigand at (25, 26) is defeated',
    )
    for (const m of FE16_MAPS)
      for (const x of m.reinforcements ?? []) expect(JSON.stringify(x.when), m.id).not.toMatch(/[{}]area/)
  })

  it('brings the students back for the reunion (Chapter 13): Byleth and the leader start, the rest arrive on turns 3 and 5', () => {
    expect(map('fe16-13-ss').forced).toEqual([{ name: 'Seteth', tile: [1, 9] }])
    expect(map('fe16-13-am').forced).toEqual([{ name: 'Dimitri', tile: [1, 9] }])
    const ss = map('fe16-13-ss').joiners!
    expect(ss.map((j) => j.name)).toEqual(['Dorothea', 'Caspar', 'Petra', 'Bernadetta', 'Linhardt', 'Ferdinand'])
    // The second three come from turn 5 on (TurnNumber's comparison 3, 'or later') with one of your units in the area the joiners show.
    const later = 'At the start of your phase with one of your units in the marked area, from turn 5'
    expect(new Set(ss.map((j) => j.when))).toEqual(new Set(['Turn 3, your phase', later]))
    expect(ss.filter((j) => j.when === later).every((j) => j.areas?.length === 1)).toBe(true)
    // Azure Moon's Gilbert comes only if he's in your army.
    expect(map('fe16-13-am').joiners!.find((j) => j.name === 'Gilbert')?.note).toBe('If Gilbert is in your army')
  })

  it("says each route's lose condition, its leader, and the locations it defends", () => {
    expect(map('fe16-13-ss').defeat).toBe('Byleth falls in battle')
    expect(map('fe16-13-am').defeat).toBe('Byleth or Dimitri falls in battle')
    expect(map('fe16-32-cf').defeat).toBe('Byleth or Edelgard falls in battle')
    // Protecting Garreg Mach: two defended locations at the map's top (the tiles the opening marks blue).
    expect(map('fe16-14-vw').objectives.map((o) => [o.type, o.tiles])).toEqual([
      ['defend', [[7, 26], [8, 26], [9, 26]]],
      ['defend', [[18, 26]]],
    ])
  })

  it("shows both versions of a unit an event flag decides (the Enbarr Infiltration's Death Knight, by The Face Beneath)", () => {
    const dk = map('fe16-22-ss').reinforcements!.filter((g) => g.units.some((u) => u.name === 'Death Knight'))
    expect(dk.map((g) => [g.when, g.units[0].carries?.[0]])).toEqual([
      ['At the start of the battle, if your army beat the Death Knight in battle in "The Face Beneath" (event flag 71)', 'Brave Lance'],
      ['At the start of the battle, unless your army beat the Death Knight in battle in "The Face Beneath" (event flag 71)', 'Scythe of Sariel'],
    ])
  })
})

describe("Three Houses' paralogues", () => {
  const para = (id: string) => map(id)
  it('fields the foes Fire Emblem Wiki counts at the start of every paralogue, on each difficulty', () => {
    // Each paralogue page's map data ('enemy'; Foreign Land and Sky's route pages, Retribution's '(paralogue)' page; The Face Beneath
    // and Death Toll give the number the battle starts with, not the one shown during preparations).
    const WIKI: Record<string, number[]> = {
      'fe16-p38': [26, 30, 42], 'fe16-p39': [30, 35, 40], 'fe16-p40': [26, 29, 32], 'fe16-p41': [19, 21, 24], 'fe16-p42': [6, 7, 7],
      'fe16-p43': [32, 33, 34], 'fe16-p44': [25, 29, 33], 'fe16-p45': [26, 21, 26], 'fe16-p46': [29, 32, 36], 'fe16-p47': [20, 26, 30],
      'fe16-p48': [33, 39, 44], 'fe16-p49': [19, 20, 26], 'fe16-p50': [6, 6, 6], 'fe16-p51': [41, 49, 57], 'fe16-p52': [18, 20, 25],
      'fe16-p53-cf': [20, 25, 28], 'fe16-p53-ss': [20, 25, 28], 'fe16-p54': [32, 39, 42], 'fe16-p55': [21, 27, 32],
      'fe16-p56': [14, 16, 19], 'fe16-p57': [19, 23, 28], 'fe16-p58': [17, 21, 28], 'fe16-p59': [22, 26, 30], 'fe16-p60': [22, 27, 31],
      // The DLC's: the wiki's DLC page (Black Market Scheme 20, then 26 on Hard and Maddening).
      'fe16-p93': [20, 26, 26], 'fe16-p94': [18, 21, 25], 'fe16-p97': [23, 23, 23],
    }
    expect(FE16_MAPS.filter((m) => m.route === 'Paralogue').map((m) => m.id).sort()).toEqual(Object.keys(WIKI).sort())
    for (const [id, n] of Object.entries(WIKI)) expect(red(para(id)), id).toEqual(n)
    // The green units the wiki lists apart ('other'): War for the Weak's 7, True Chivalry's 11, Death Toll's 5.
    expect(DIFFS.map((d) => para('fe16-p44').units.filter((u) => u.type === 'ally' && on(u, d)).length)).toEqual([11, 11, 11])
  })

  it("opens each one when the monastery's script does, on the routes it reaches, and says what else it needs", () => {
    expect(para('fe16-p42').notes[0]).toBe('Can be fought in the months of Chapters 8 to 10.')
    expect(para('fe16-p42').availableIn).toEqual(['Crimson Flower', 'Silver Snow', 'Azure Moon', 'Verdant Wind'])
    expect(para('fe16-p39')).toMatchObject({ availableIn: ['Azure Moon'], notes: ['Can be fought in the months of Chapters 19 to 22.'] })
    // Eternal Guardian: Rhea's, after she's back, with her support with Byleth at C.
    expect(para('fe16-p38').notes).toEqual([
      'Can be fought in the months of Chapters 16 to 18 on Silver Snow, Chapters 16 to 22 on Azure Moon and Chapters 16 to 19 on Verdant Wind.',
      'Needs Byleth and Rhea at support C or above.',
    ])
    expect(para('fe16-p48').notes[1]).toBe('Needs Gilbert in your army; Annette and Gilbert at support C or above.')
    // Dividing the World opens in White Clouds: for the Black Eagles only until the routes part, Crimson Flower's Hilda being a foe.
    expect(para('fe16-p57').notes[0]).toContain('Chapters 10 to 11 on Crimson Flower')
    expect(para('fe16-p52').notes[1]).toContain("unless Seteth and Flayn both fell in Protecting Garreg Mach (Crimson Flower's Chapter 15)")
  })

  it('plays one map for every route that fights a paralogue alike, the leader by house where it opens in White Clouds', () => {
    expect(para('fe16-p42').forced).toEqual([{ name: 'Your house leader (Edelgard, Dimitri or Claude)', tile: [14, 18] }])
    expect(para('fe16-p44').defeat).toBe('Byleth, your house leader (Edelgard, Dimitri or Claude), Felix, or Rodrigue falls in battle')
    // Foreign Land and Sky: Crimson Flower fights the Church from the battle's second unit table (scenario +36 bit 1), as the wiki's
    // Crimson Flower page lists it: Holy Knights and Warlocks for the Empire's Assassins and Dark Bishops.
    const names = (id: string) => new Set(foes(para(id), 'Normal').map((u) => u.name))
    expect(names('fe16-p53-cf').has('Holy Knight') && !names('fe16-p53-cf').has('Assassin')).toBe(true)
    expect(names('fe16-p53-ss').has('Assassin') && !names('fe16-p53-ss').has('Holy Knight')).toBe(true)
  })

  it('says what each reward waits on where the script counts something simple', () => {
    expect(para('fe16-p44').notes.at(-1)).toBe(
      'When the battle is won: if 3 or 4 of the 5 green Commoners fall, Bullion; if 1 or 2 of the 5 green Commoners fall, Wo Dao and ' +
        'Large Bullion; if none of the 5 green Commoners fall, Aegis Shield and Extra Large Bullion.',
    )
    expect(FE16_ITEM_SOURCES['Wo Dao']).toContainEqual({
      mapId: 'fe16-p44',
      kind: 'event-later',
      text: 'Given when the battle is won, if 1 or 2 of the 5 green Commoners fall',
    })
  })

  it('opens a paralogue in the spoiler walk at the chapter its month belongs to', () => {
    const bl = walkFork(FE16_FORK, 'bl').story
    expect(bl.opensAt!('fe16-p42')).toBe(bl.maps.findIndex((m) => m.id === 'fe16-8'))
    expect(bl.opensAt!('fe16-p40')).toBe(Infinity)
    const be = walkFork(FE16_FORK, 'be').story
    expect(be.opensAt!('fe16-p40')).toBe(Infinity)
    const cf = walkFork(FE16_FORK, 'be/cf').story
    expect(cf.opensAt!('fe16-p40')).toBe(cf.maps.findIndex((m) => m.id === 'fe16-34-cf'))
  })
})

describe("Three Houses' Cindered Shadows", () => {
  const cs = FE16_MAPS.filter((m) => m.route === 'Cindered Shadows')
  it("plays its seven battles as its route's chapters (fixed_flow.bin section 5: Chapter 5 has none), on Normal and Hard", () => {
    expect(cs.map((m) => [m.id, m.chapter])).toEqual([
      ['fe16-86-cs', 1], ['fe16-87-cs', 2], ['fe16-88-cs', 3], ['fe16-89-cs', 4], ['fe16-90-cs', 6], ['fe16-91-cs', 7], ['fe16-92-cs', 8],
    ])
    expect(FE16_MAP_SET.routes!.maps('Cindered Shadows')).toEqual(cs)
    for (const m of cs) expect(m.difficulties, m.id).toEqual(['Normal', 'Hard'])
    // Its maps' grids are the DLC's own (the base game's are placeholders): the Abyss is 25 by 29.
    expect([map('fe16-86-cs').width, map('fe16-86-cs').height]).toEqual([25, 29])
  })

  it('fields the foes Fire Emblem Wiki counts at the start of each battle, on Normal and Hard', () => {
    const WIKI: Record<string, number[]> = {
      'fe16-86-cs': [25, 27], 'fe16-87-cs': [10, 11], 'fe16-88-cs': [24, 30], 'fe16-89-cs': [0, 0], 'fe16-90-cs': [30, 35],
      'fe16-91-cs': [24, 32], 'fe16-92-cs': [1, 1],
    }
    for (const m of cs) expect(red(m).slice(0, 2), m.id).toEqual(WIKI[m.id])
    // Ambush in the Arena: the Ashen Wolves fight beside Byleth.
    expect(map('fe16-87-cs').forced?.map((f) => f.name)).toEqual(['Yuri', 'Balthus', 'Constance', 'Hapi'])
    expect(map('fe16-86-cs').units.find((u) => u.name === 'Yuri')?.note).toMatch(/^Lv \d+ \(Hard \d+\)/)
  })
})

describe("Three Houses' auxiliary battles", () => {
  const aux = FE16_MAPS.filter((m) => m.route === 'Auxiliary')
  it('lists the 25 auxiliary battles (scenarios 61-85) in a dropdown of their own on every route', () => {
    expect(aux.map((m) => m.id)).toEqual(Array.from({ length: 25 }, (_, k) => `fe16-a${61 + k}`))
    for (const r of ['Crimson Flower', 'Silver Snow', 'Azure Moon', 'Verdant Wind']) {
      expect(FE16_MAP_SET.routes!.third!.maps(r), r).toEqual(aux)
    }
    expect(map('fe16-a61').title).toBe('Battle in the Outskirts')
  })

  it("draws their foes where they stand, picked at random each time, with their slots and the part of the game that offers them", () => {
    for (const m of aux) {
      for (const u of m.units) {
        expect(['Random foe', 'Random monster'], `${m.id} ${u.name}`).toContain(u.name)
        expect(u.carries, m.id).toBeUndefined()
      }
    }
    // Ten slots of yours and fifteen foes (four monsters where monsters alone fight); the Expansion Pass's seven slots.
    expect([map('fe16-a61').starts.length, map('fe16-a61').units.length]).toEqual([10, 15])
    expect([map('fe16-a69').starts.length, map('fe16-a69').units.length]).toEqual([10, 4])
    expect(map('fe16-a81').starts).toHaveLength(7)
    // (Which part offers each is Fire Emblem Wiki's list of auxiliary battle maps: the README.)
    expect(map('fe16-a61').notes[0]).toBe('Offered on free days (the Battle menu) during Part I (White Clouds) only.')
    expect(map('fe16-a72').notes[0]).toBe('Offered on free days (the Battle menu) during Part II only.')
    expect(map('fe16-a81').notes[0]).toContain('with the Expansion Pass')
    // Their commander still drops its record's Bullion.
    expect(map('fe16-a61').units.find((u) => u.drops)?.drops).toEqual(['Bullion'])
  })

  it("gives the rare monsters' Rusted weapons as sources (Fire Emblem Wiki): the legendary ones once", () => {
    const lines = FE16_ITEM_SOURCES['Rusted Bow (Parthia)'].filter((x) => x.mapId.startsWith('fe16-a'))
    expect(lines.length).toBeGreaterThan(0)
    expect(lines[0].text).toBe('Dropped by a rare monster (King of Wings) at random, only once')
    expect(FE16_ITEM_SOURCES['Rusted Sword (Silver Sword)'].some((x) => x.text === 'Dropped by a rare monster (King of Fangs or Wings) at random')).toBe(true)
  })

  it('opens each in the spoiler walk with the free days of its part: Chapter 2, or Chapter 13 for Part II alone', () => {
    const am = walkFork(FE16_FORK, 'bl').story
    expect(am.opensAt!('fe16-a61')).toBe(am.maps.findIndex((m) => m.id === 'fe16-2'))
    expect(am.opensAt!('fe16-a72')).toBe(am.maps.findIndex((m) => m.id === 'fe16-13-am'))
  })
})

describe("Three Houses' White Clouds weapons", () => {
  it('lists only what something gives, a unit carries or a foe holds', () => {
    for (const w of FE16_LISTED) expect(FE16_ITEM_SOURCES[w.name]?.length, w.name).toBeGreaterThan(0)
  })

  it("gives the lords' and students' starting weapons and the Sword of the Creator after Chapter 4", () => {
    expect(FE16_ITEM_SOURCES['Iron Bow']).toContainEqual({ mapId: 'fe16-0', kind: 'kit', text: 'Carried by Claude from the start' })
    expect(FE16_ITEM_SOURCES['Sword of the Creator']).toEqual(
      ['be', 'bl', 'gd'].map((h) => ({ mapId: `fe16-4-${h}`, kind: 'event-later', text: 'Given when the battle is won' })),
    )
  })

  it("reads the record's stats and effectiveness", () => {
    expect(weapon('Iron Sword')).toMatchObject({ rank: 'E', mt: 5, hit: 90, crit: 0, wt: 5, uses: 40 })
    expect(weapon('Armorslayer')?.effective).toEqual(['armour'])
    expect(weapon('Iron Gauntlets')?.rules).toContain('Strikes twice when it attacks')
  })

  it("names each Rusted weapon for what the blacksmith forges it into (the Holy Tomb's reward)", () => {
    // fixed_shopdata.bin section 4: Rusted Bow record 111 is forged into a Silver Bow. The script gives it when no Crest Stone is
    // carried off, and again when 11 to 19 are.
    expect(weapon('Rusted Bow (Silver Bow)')).toMatchObject({ mt: 0, hit: 30, rules: ['The blacksmith forges it into a Silver Bow'] })
    expect(FE16_ITEM_SOURCES['Rusted Bow (Silver Bow)'].filter((s) => s.mapId === 'fe16-11-be').map((s) => s.text)).toEqual([
      'Given when the battle is won, if no Crest Stone is carried off the map',
      'Given when the battle is won, if 11 to 19 Crest Stones are carried off the map',
    ])
  })
})

describe("Three Houses' rare things to steal", () => {
  /** Every unit on every map with the group it arrives in: start units, reinforcements and stand-ins. */
  const everyUnit = FE16_MAPS.flatMap((m) =>
    [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].map((u) => ({ m, u })),
  )
  const marked = everyUnit.filter(({ u }) => u.steal)
  const steal = (id: string, name: string) =>
    everyUnit.filter(({ m, u }) => m.id === id && u.name === name && u.steal).map(({ u }) => u.steal)
  // What the shops keep in regular stock (availability 1, renewed at every shop update), as Fire Emblem Wiki's shop lists give them:
  // the monastery's armory and item shop, Anna's shop (her unlimited stock) and the Abyss's Pagan Altar.
  const REGULAR_STOCK = [
    'Leather Shield', 'Iron Shield', 'Steel Shield', 'Vulnerary', 'Concoction', 'Antitoxin', 'Pure Water', 'Torch', 'Door Key',
    'Chest Key', 'Beginner Seal', 'Intermediate Seal', 'Advanced Seal', 'Elixir', 'Master Seal', 'Silver Shield', 'Master Key',
    'Abyssian Exam Pass',
  ]

  it('lists only what the unit carries and does not drop, on foes alone, never on a random foe', () => {
    expect(marked.length).toBeGreaterThan(0)
    for (const { m, u } of marked) {
      const at = `${m.id} ${u.name} ${u.tile}`
      expect(u.steal!.length, at).toBeGreaterThan(0)
      for (const item of u.steal!) {
        expect(u.carries, at).toContain(item)
        expect(u.drops ?? [], at).not.toContain(item)
      }
      // A thief steals from the red and third armies (0xca560), never from a green unit or one that joins you.
      expect(u.type, at).not.toBe('ally')
      expect(u.talk?.startsWith('Recruit') ?? false, at).toBe(false)
    }
    for (const { m, u } of everyUnit) expect(u.standIn?.steal, `${m.id} ${u.name}`).toBeUndefined()
    expect(marked.filter(({ m }) => m.route === 'Auxiliary')).toEqual([])
  })

  it('never lists a weapon, a relic, something used up at once, or anything a shop keeps in regular stock', () => {
    const weapons = new Set(FE16_LISTED.map((w) => w.name))
    const items = new Set(marked.flatMap(({ u }) => u.steal!))
    for (const item of items) {
      // Steal's item check (0x40cb80) refuses a record of type below 8 (the weapons and spells) and the regalia (+22 bit 0x40).
      expect(weapons.has(item), item).toBe(false)
      expect(REGULAR_STOCK, item).not.toContain(item)
    }
    for (const relic of ['Aegis Shield', 'Ochain Shield', 'Seiros Shield', 'Caduceus Staff', 'Rafail Gem', 'Fetters of Dromi']) {
      expect(items.has(relic), relic).toBe(false)
    }
    // Only Anna's one-off stat boosters, rings and Hexlock Shields, the Pagan Altar's one-off staff, and what no shop sells.
    expect([...items].sort()).toEqual([
      'Accuracy Ring', 'Aurora Shield', 'Critical Ring', 'Dark Seal', 'Energy Drop', 'Evasion Ring', 'Goddess Icon', 'Goddess Ring',
      'Hexlock Shield', 'Lampos Shield', 'Magic Staff', 'Prayer Ring', 'Seraph Robe', 'Speed Ring',
    ])
    // (Among them The Great Bridge Coup's Acheron, once on each route that fights it: SpawnSpooky places him.)
    expect(marked).toHaveLength(52)
  })

  it("marks the foes Fire Emblem Wiki's item pages list as ones to steal from", () => {
    // Energy Drop, Goddess Icon and Seraph Robe: Insurmountable's Wyvern Lord, Bow Knight and other Wyvern Lord, The Silver Maiden's
    // Paladin, Fortress Knight and War Master, The Sleeping Sand Legend's Sniper and two Warlocks.
    expect(steal('fe16-p40', 'Wyvern Lord').sort()).toEqual([['Energy Drop'], ['Seraph Robe']])
    expect(steal('fe16-p40', 'Bow Knight')).toEqual([['Goddess Icon']])
    expect(steal('fe16-p39', 'Paladin')).toEqual([['Energy Drop']])
    expect(steal('fe16-p39', 'Fortress Knight')).toEqual([['Goddess Icon']])
    expect(steal('fe16-p39', 'War Master')).toEqual([['Seraph Robe']])
    expect(steal('fe16-p41', 'Sniper')).toEqual([['Energy Drop']])
    expect(steal('fe16-p41', 'Warlock').sort()).toEqual([['Goddess Icon'], ['Seraph Robe']])
    // The shields no shop sells: Nader's and Ladislava's Aurora Shield, Gwendal's Lampos Shield.
    expect(steal('fe16-p40', 'Nader')).toEqual([['Aurora Shield']])
    expect(steal('fe16-16-am', 'Ladislava')).toEqual([['Aurora Shield']])
    expect(steal('fe16-15-vw', 'Gwendal')).toEqual([['Lampos Shield']])
    // The mock battle's leaders: Edelgard's Accuracy Ring, Dimitri's and Claude's Evasion Rings.
    expect(steal('fe16-7-bl', 'Edelgard')).toEqual([['Accuracy Ring']])
    expect(steal('fe16-7-be', 'Claude')).toEqual([['Evasion Ring']])
    // The Face Beneath's Death Knight: the Accuracy Ring (the wiki's chapter page), not the Dark Seal he drops or his Elixir.
    expect(steal('fe16-p47', 'Death Knight')).toEqual([['Accuracy Ring']])
    // The Great Bridge Coup's arriving Acheron: 'Evasion Ring: Steal from Acheron (reinforcement)' on every route that fights it.
    for (const r of ['ss', 'am', 'vw']) expect(steal(`fe16-16-${r}`, 'Acheron'), r).toEqual([['Evasion Ring']])
    // Cindered Shadows' Ambush in the Arena: the arriving Death Knight's Dark Seal and Warlock's Goddess Ring.
    expect(steal('fe16-87-cs', 'Death Knight')).toEqual([['Dark Seal']])
    expect(steal('fe16-87-cs', 'Warlock')).toEqual([['Goddess Ring']])
    // Silver Snow's last battle: seven Hexlock Shields, three more on Hard and Maddening (the wiki's ten).
    const hexlocks = everyUnit.filter(({ m, u }) => m.id === 'fe16-28-ss' && u.steal?.includes('Hexlock Shield')).map(({ u }) => u)
    expect([hexlocks.length, hexlocks.filter((u) => !u.difficulties).length]).toEqual([10, 7])
    // A Master Seal isn't rare (Anna keeps them in stock): Crimson Flower's Lysithea holds one and isn't marked.
    const lysithea = map('fe16-33-cf').units.find((u) => u.name === 'Lysithea')!
    expect(lysithea.carries).toContain('Master Seal')
    expect(lysithea.steal).toBeUndefined()
  })
})

describe("Three Houses' SpawnSpooky arrivals (bsi action 620: the unit on the action's own tile)", () => {
  /** The units arriving on a difficulty, each with its group's time on that difficulty. */
  const arrivals = (m: ChapterMap, d: Difficulty) =>
    (m.reinforcements ?? []).flatMap((g) =>
      g.units.filter((u) => on(u, d)).map((u) => ({ ...u, when: typeof g.when === 'string' ? g.when : g.when?.[d], areas: g.areas })),
    )

  it("brings Acheron to The Great Bridge Coup where the script puts him, with Fire Emblem Wiki's group, levels and Evasion Ring", () => {
    for (const r of ['ss', 'am', 'vw']) {
      const m = map(`fe16-16-${r}`)
      // Not on the map at the start: he arrives (the spoiler block hides him until then).
      expect(m.units.some((u) => u.name === 'Acheron'), r).toBe(false)
      const g = m.reinforcements!.find((x) => x.units.some((u) => u.name === 'Acheron'))!
      // SpawnSpooky (21, 27, 10, 5, 1): grid (27, 10), the app's (28, 10); his record stands one tile east, (28, 10) of the grid.
      expect(g.units.find((u) => u.name === 'Acheron'), r).toMatchObject({
        type: 'boss', tile: [28, 10], note: 'Lv 33 (Hard 34, Maddening 40) Warlock', carries: ['Evasion Ring'], steal: ['Evasion Ring'],
      })
      // The wiki: 'Acheron ... 3 Armored Knights ... 2 Paladins', after a unit reaches column 17 or passes the L-shaped wall. The
      // script's other branch (after Ladislava's defeat or a battle with Ferdinand, as a unit's action ends) is a phase start's event
      // testing an action's end: left out (README).
      expect(g.units.map((u) => u.name).sort(), r).toEqual(['Acheron', 'Armored Knight', 'Armored Knight', 'Armored Knight', 'Paladin', 'Paladin'])
      expect(g.when, r).toBe('At the start of the enemy phase with one of your units in the marked areas')
      expect(g.areas?.map((a) => a.rect), r).toEqual([[1, 1, 17, 20], [18, 1, 22, 11]])
    }
  })

  it("adds Chapter 10's warped-in soldiers and beasts once Kronya falls: Fire Emblem Wiki's +10, +13 and +13", () => {
    const m = map('fe16-10')
    expect(DIFFS.map((d) => arrivals(m, d).length)).toEqual([10, 13, 13])
    expect(arrivals(m, 'Normal').every((u) => u.when === 'Once Kronya is defeated')).toBe(true)
    // The wiki's 'Steel Axe: Dropped by enemy Armored Knight (reinforcement)'.
    expect(FE16_ITEM_SOURCES['Steel Axe']).toContainEqual({
      mapId: 'fe16-10', kind: 'drop-later', text: 'Dropped by a foe Armored Knight, arriving mid-chapter',
    })
  })

  it("lands Nader and his Wyvern Lords with Capturing Derdriu's first wave, as Fire Emblem Wiki counts it", () => {
    const m = map('fe16-33-cf')
    const landing = (d: Difficulty) => arrivals(m, d).filter((u) => u.when === 'At the start of the enemy phase')
    // Nader, 4 (Normal), 5 (Hard) or 6 (Maddening) Bow Knights and 4 or 5 Wyvern Lords.
    expect(DIFFS.map((d) => landing(d).length)).toEqual([9, 10, 12])
    expect(landing('Normal').find((u) => u.name === 'Nader')).toMatchObject({ tile: [25, 19], drops: ['Aurora Shield'] })
  })

  it("sends Saving Derdriu's Imperial soldiers on the tiles the wiki gives once Hilda (or the green War Master standing in) falls", () => {
    const m = map('fe16-23-am')
    const g = m.reinforcements!.filter((x) => x.units.some((u) => u.name === 'Fortress Knight' || u.name === 'Falcon Knight'))
    const when = 'Once Hilda or the green War Master at (18, 24) is defeated'
    expect(g.map((x) => x.when)).toEqual([when, { Hard: when, Maddening: when }])
    // The wiki's (16, 4), (15, 4), (16, 8), (15, 8) in the grid's own coordinates; the Falcon Knights' (18, 2) and (19, 9) come on Hard
    // and Maddening by the script (the wiki: Maddening only).
    expect(g[0].units.map((u) => [u.name, u.tile])).toEqual([
      ['Fortress Knight', [17, 26]], ['Hero', [16, 26]], ['Fortress Knight', [17, 22]], ['Hero', [16, 22]],
    ])
    expect(g[1].units.map((u) => [u.name, u.tile, u.difficulties])).toEqual([
      ['Falcon Knight', [19, 28], ['Hard', 'Maddening']], ['Falcon Knight', [20, 21], ['Hard', 'Maddening']],
    ])
  })

  it("adds Crimson Flower's Golems to Rhea's soldiers: Fire Emblem Wiki's 12 (Normal and Hard) and 16 (Maddening)", () => {
    const m = map('fe16-31-cf')
    const soldiers = (d: Difficulty) =>
      arrivals(m, d).filter((u) => u.when === 'Once Flayn, Seteth and Gilbert are defeated; turn 11' && u.name !== 'Rhea')
    expect(DIFFS.map((d) => soldiers(d).length)).toEqual([12, 12, 16])
    expect(soldiers('Normal').filter((u) => u.name === 'Golem').map((u) => [u.tile, u.size])).toEqual([[[12, 25], 2], [[13, 22], 2]])
  })

  it("says what opens Search for the Chalice's groups: the Magic Seals (fixed_gimmick.bin), the area or the Golem, the Golem chain", () => {
    const m = map('fe16-88-cs')
    const whens = m.reinforcements!.map((g) => g.when)
    // The western and central Magic Seals (records 84 and 85: grid (0, 28) and (9, 29)).
    expect(whens).toContain('Once the Magic Seal at (1, 2) is used')
    expect(whens).toContain('Once the Magic Seal at (10, 1) is used')
    // The wiki's 'After defeating the southeastern Golem': the script's other way in, a unit in the area, is an 'or'.
    expect(whens).toContain('At the start of the enemy phase with one of your units in the marked area or once the foe Golem at (16, 15) is defeated')
    // A Golem from the southern border on turn 3, another each time the one before it there falls: twice on Normal, four times on Hard
    // (the wiki: every odd-numbered turn, endlessly).
    // Each also checks that Simone stands and that neither Magic Seal's event has run: what stops them, said once at the end.
    const unless = ', unless Simone is defeated or the Magic Seal at (10, 1) or (1, 2) is used first'
    expect(whens).toContainEqual({
      Normal: 'Turn 3, the enemy phase; at the start of the enemy phase, once the foe Golem at (6, 2) is defeated' + unless,
      Hard: 'Turn 3, the enemy phase; at the start of the enemy phase, once the foe Golem at (6, 2) is defeated (3 times)' + unless,
    })
    // The wiki's +12 that aren't the Golem chain.
    expect(arrivals(m, 'Normal').filter((u) => !(u.name === 'Golem' && u.tile[1] === 2))).toHaveLength(12)
  })

  it('places the Cindered Shadows arrivals the script warps in, and words the moment condition 400 tests as during a phase', () => {
    expect(arrivals(map('fe16-86-cs'), 'Normal').find((u) => u.name === 'Giant Crawler')).toMatchObject({
      tile: [18, 5], size: 2, when: 'As soon as one of your units enters the marked areas',
    })
    // A Beast in the Cathedral's Verrat beside the Umbral Beast (the wiki: at the start of enemy phase 1), after an event of trigger
    // 18000 whose condition 400 tests another moment than a phase's start.
    expect(arrivals(map('fe16-92-cs'), 'Normal').filter((u) => u.when === 'During your phase').map((u) => [u.name, u.tile])).toEqual([
      ['Verrat', [6, 11]],
    ])
    // (After the fourth wave, which comes like each before it at an enemy phase from turn 4 or once every foe is defeated.)
    expect(arrivals(map('fe16-87-cs'), 'Normal').find((u) => u.name === 'Death Knight')?.when).toBe(
      'During the enemy phase, once turn 4 has come or every foe is defeated',
    )
    // A Harrowing Escape: the Warlock and Assassin once all your units are past the first gate (the wiki: 'after all player units reach
    // the first checkpoint').
    expect(arrivals(map('fe16-89-cs'), 'Normal').filter((u) => u.name === 'Warlock' && u.tile.join() === '2,7').map((u) => u.when)).toContain(
      'Once none of your units is left in the marked areas, then every other turn after, until an event in the chapter stops them; once none of your units is left in the marked areas',
    )
  })

  it('never shows an end scene (what runs once the battle is won, DidCompleteMap) as an arrival, nor a unit off the grid', () => {
    // Ambush in the Arena's closing scene brings Aelfric; Besieged in the Chapel Ruins' its Dark Bishops: neither is a unit on the map.
    expect(arrivals(map('fe16-87-cs'), 'Normal').some((u) => u.name === 'Aelfric' || u.name === 'Yuri')).toBe(false)
    expect(arrivals(map('fe16-90-cs'), 'Normal').some((u) => u.name === 'Dark Bishop')).toBe(false)
    for (const m of FE16_MAPS) {
      for (const d of m.difficulties ?? DIFFS) {
        for (const u of arrivals(m, d)) {
          expect(u.tile[0] >= 1 && u.tile[0] <= m.width && u.tile[1] >= 1 && u.tile[1] <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
        }
      }
    }
  })
})

describe("Three Houses' arrival times, read from the script's condition trees", () => {
  /** Each group's time on a difficulty, by the names of its units. */
  const times = (id: string, d: Difficulty = 'Normal') =>
    (map(id).reinforcements ?? []).map((g) => ({
      names: g.units.map((u) => u.name).sort().join(),
      when: typeof g.when === 'string' ? g.when : g.when?.[d],
    }))
  const at = (id: string, names: string, d: Difficulty = 'Normal') => times(id, d).find((g) => g.names === names)?.when

  it("says an 'or' as 'or', with each way whole (Fire Emblem Wiki's chapter pages)", () => {
    // 'Upon entering the warp nexus ..., or upon opening the door to it'.
    expect(at('fe16-6', 'Archer,Archer,Cavalier,Cavalier,Cavalier,Cavalier')).toBe(
      'As soon as one of your units enters the marked area or once the door at (22, 13) is opened',
    )
    // Lorenz's group: event 14 (Ladislava's defeat, or a battle with Ferdinand or the Imperial General standing in for him). The
    // script's other way, after an event that is switched off, can't happen.
    expect(at('fe16-16-ss', 'Lorenz,Mage,Mage,Priest')).toBe(
      'Once Ferdinand or the foe Paladin at (5, 19) has fought, or once Ladislava is defeated',
    )
    // 'On turn 10, or after any player unit ... ending their turn within three tiles of Mercedes or Caspar'.
    expect(at('fe16-p47', 'Dark Knight,Dark Knight,Hero,Hero,Sniper,Sniper')).toBe(
      'Turn 10, the enemy phase, or once one of your units has come within 3 tiles of Mercedes or Caspar',
    )
    // 'After a player unit ends their turn within two spaces of Duke Gerth, or upon defeating Myson'.
    expect(times('fe16-p94').some((g) => g.when?.endsWith('within 2 tiles of Duke Gerth, or once Myson is defeated'))).toBe(true)
    // 'After reaching one of the shoals or bridges, or upon defeating Sylvain or his replacement'.
    expect(at('fe16-36-cf', 'Fortress Knight,Fortress Knight,Mercedes')).toBe(
      'At the start of the enemy phase, once one of your units has entered the marked areas, or once Sylvain or the foe Great Knight ' +
        'at (25, 11) is defeated',
    )
    // 'Turn 10 or upon any player unit entering the northwest regions'.
    expect(at('fe16-p48', 'Fortress Knight,Fortress Knight,Paladin,Paladin')).toBe(
      'Turn 10 or once one of your units has entered the marked areas',
    )
  })

  it('says what an arrival needs together as one, and a defeat that stands for every foe it names (Crimson Flower 12)', () => {
    // 'After Gilbert, Flayn, and Seteth are defeated, or ... of turn 11 if one of them has not been defeated yet'. What stops the turn-11
    // way (all three defeated) is, as a set, the other way in: not said again.
    expect(at('fe16-31-cf', 'Rhea')).toBe('Once Flayn, Seteth and Gilbert are defeated; turn 11')
    // 'Upon all the southeast Fortress Knights being defeated'.
    const all = 'Once the 4 foe Fortress Knights at (24, 5), (22, 5), (21, 4) and (21, 2) are defeated'
    expect(times('fe16-p48').some((g) => g.when?.startsWith(all))).toBe(true)
  })

  it('says what stops a one-off arrival where its event checks it: a unit standing, another event not yet run', () => {
    // 'All reinforcements are halted if the Thief Leader is defeated'.
    expect(at('fe16-90-cs', 'Sniper')).toBe('Turn 2, the enemy phase, unless the foe Warrior at (3, 20) is defeated first')
    // 'Fifteen turns after the first wave, or if a unit is in range ... Does not trigger if Dimitri has already been defeated'.
    expect(at('fe16-36-cf', 'Paladin,Paladin')).toBe(
      'Turn 15, the enemy phase, or once one of your units has been in the marked area at the start of the enemy phase, unless Dedue ' +
        'or Dimitri is defeated first',
    )
    // A unit a difficulty doesn't place stands for nothing: Reclaiming the Capital's westernmost Titanus is Hard and Maddening's.
    expect(at('fe16-21-am', 'Sniper')).toBe(
      'Once the foe Grappler at (4, 12), the foe Grappler at (2, 12) and the foe Warlock at (3, 14) are defeated, once one of your ' +
        'units has entered the marked area',
    )
    expect(at('fe16-21-am', 'Sniper', 'Hard')).toMatch(/^Once the foe Titanus at \(4, 16\), /)
    // Every stop reads 'unless ... first' (an event flag's 'unless' is a condition of its own).
    for (const m of FE16_MAPS) {
      for (const g of m.reinforcements ?? []) {
        for (const w of typeof g.when === 'string' ? [g.when] : Object.values(g.when ?? {})) {
          for (const part of w!.split('; ')) {
            if (part.includes(', unless ') && !part.includes('(event flag')) expect(part.endsWith(' first'), `${m.id} ${part}`).toBe(true)
          }
        }
      }
    }
  })

  /** A list of who falls as a set of names, its tiles kept whole: 'Gilbert, Flayn and Seteth are defeated'. */
  const fallen = (words: string) =>
    new Set(words.replace(/ (is|are) defeated$/, '').split(/, (?![^(]*\))| and (?![^(]*\))| or (?![^(]*\))/))
  const parts = (w: string) => w.split('; ')

  it("never says again, as what stops it, a group's other way in, whatever order it names the units in", () => {
    for (const m of FE16_MAPS) {
      for (const g of m.reinforcements ?? []) {
        for (const w of typeof g.when === 'string' ? [g.when] : Object.values(g.when ?? {})) {
          const ways = parts(w!).map((p) => /^Once (.*) (is|are) defeated$/.exec(p.split(', unless ')[0])?.[1]).filter(Boolean)
          for (const p of parts(w!)) {
            const unless = /, unless (.*) first$/.exec(p)?.[1]
            if (!unless || !/ (is|are) defeated$/.test(unless)) continue
            const stop = [...fallen(unless)].sort().join('|')
            for (const way of ways) expect([...fallen(way!)].sort().join('|'), `${m.id} ${w}`).not.toBe(stop)
          }
        }
      }
    }
    // Protecting Garreg Mach: the area way's stops are Flayn's later events, each after the group's other ways in (the defeats, turn
    // 12): not said, so no clause mixes the defeats' 'and' with their 'or'.
    expect(times('fe16-34-cf').filter((g) => g.when?.startsWith('At the start of the enemy phase')).map((g) => g.when)).toContain(
      'At the start of the enemy phase with one of your units in the marked area',
    )
  })

  it("says each 'unless' unambiguously: no clause mixes 'and' with 'or'", () => {
    for (const m of FE16_MAPS) {
      for (const g of m.reinforcements ?? []) {
        for (const w of typeof g.when === 'string' ? [g.when] : Object.values(g.when ?? {})) {
          for (const p of parts(w!)) {
            const unless = /, unless (.*) first$/.exec(p)?.[1]
            // (A list of names joined by 'and' is one clause: 'Gilbert, Flayn and Seteth are defeated'.)
            if (unless) expect(/ (is|are) defeated and | has come and /.test(unless) && / or /.test(unless), `${m.id} ${p}`).toBe(false)
          }
        }
      }
    }
  })

  it("says a unit out of an area as leaving it (MovedSpecificUnitInRectangle's seventh argument, 0x5451b8)", () => {
    // Black Market Scheme: 'Turn 6 (Normal/Hard) ..., or after the player unit southeast of the church leaves their starting area'.
    expect(at('fe16-p93', 'Assassin,Thief')).toBe('As soon as one of your units leaves the marked area; turn 6')
    // Weathervanes of Fódlan's Annette and Gilbert 'leave the southeast area'; Besieged in the Chapel Ruins' Giant Bird.
    const bird = map('fe16-90-cs').units.find((u) => u.name === 'Giant Bird')
    expect(bird?.note).toMatch(/; as soon as Balthus leaves the area from \(1, 1\) to \(4, 6\), goes for Balthus$/)
  })
})

describe("Three Houses' unit AI, read from the scripts and the program's AI kinds", () => {
  /** Every unit of a map, at the start and arriving, with its note. */
  const units = (id: string) => [...map(id).units, ...(map(id).reinforcements ?? []).flatMap((g) => g.units)]
  const notes = (id: string, name: string) => units(id).filter((u) => u.name === name).map((u) => u.note ?? '')
  const AI = /holds its ground|never moves or attacks|never attacks|goes for|heads for|moves with/

  it('says who a foe goes for, from when, as Fire Emblem Wiki has it', () => {
    // An Inevitable Encounter: 'He and his squad begin moving after the first four Ruffians are defeated' (Normal), 'or he or the
    // Thieves are provoked' (Hard): MoveToUnitAI2 sends them for Byleth, the first of their targets on the map.
    const area = 'at the start of the enemy phase, once one of your units has entered the area from (11, 15) to (21, 20) or '
    expect(notes('fe16-0', 'Kostas')).toEqual([
      `Lv 3 Thief; ${area}the 4 foe Ruffians at (11, 7), (8, 12), (9, 13) and (10, 13) are defeated, goes for Byleth`,
      `Lv 6 Thief; ${area}the 6 foes (4 Ruffians and 2 Thieves) are defeated, goes for Byleth`,
    ])
    // Jeralt: 'Immobile until all enemies but Kostas and his nearby Thieves are defeated'.
    expect(notes('fe16-0', 'Jeralt')[0]).toBe(
      'Lv 3 Paladin; holds its ground until the 4 foe Ruffians at (11, 7), (8, 12), (9, 13) and (10, 13) are defeated, once turn 2 has come',
    )
    // Saving Derdriu: the Heroes that go for Judith, and the soldiers that come once Hilda falls (Claude, then Byleth). Lord Arundel:
    // 'Immobile until any player unit enters the northern area; ignores combat and moves northeast for the first turn after becoming
    // mobile'.
    expect(units('fe16-23-am').filter((u) => u.note?.endsWith('; goes for Judith')).map((u) => u.tile)).toEqual([[9, 16], [12, 19], [13, 20]])
    expect(notes('fe16-23-am', 'Lord Arundel')[0]).toMatch(
      /; holds its ground; .*, heads for \(8, 28\), never attacking; as soon as Lord Arundel enters the area from \(7, 27\) to \(10, 29\), goes for Claude$/,
    )
    const once = (map('fe16-23-am').reinforcements ?? []).filter((g) => g.when === 'Once Hilda or the green War Master at (18, 24) is defeated')
    expect(once.flatMap((g) => g.units).every((u) => u.note?.endsWith('; goes for Claude, then Byleth'))).toBe(true)
    // Weathervanes of Fódlan: 'attacks only Annette once no longer immobile' (MoveToUnitAI2's last argument 0).
    const fk = notes('fe16-p48', 'Fortress Knight').filter((n) => n.includes('Annette'))
    expect(fk.length).toBeGreaterThan(4)
    expect(fk.every((n) => n.endsWith('goes for Annette, attacking no one else'))).toBe(true)
  })

  it('says where a foe heads, and that it holds its ground until then', () => {
    // The Forgotten: 'Immobile until turn 4 or any unit enters the seven-tile square centered on the Onager, at which point he
    // prioritizes escaping'.
    expect(notes('fe16-p46', 'Thief')).toContain(
      'Lv 13; holds its ground; on turn 4 or once one of your units has entered the area from (10, 8) to (16, 14), heads for (23, 1), ' +
        'never attacking',
    )
    // Land of the Golden Deer: 'Immobile until turn 3, at which point he prioritizes escaping via the south'.
    expect(notes('fe16-p54', 'Thief')).toContain(
      'Lv 13 (Hard 14, Maddening 21); holds its ground; on turn 3, heads for the area from (11, 1) to (12, 1), never attacking',
    )
    // Salvation at the Chapel's Nobles never move (their kind's +4 leaves them no Mov).
    expect(new Set(notes('fe16-9', 'Noble'))).toEqual(new Set(['Lv 15; never moves or attacks']))
  })

  it('says it per difficulty where the script does (Chapter 5: the Black Beast goes for Byleth on Maddening)', () => {
    const beast = (map('fe16-5').reinforcements ?? []).flatMap((g) => g.units).filter((u) => u.name === 'Black Beast')
    expect(beast.map((u) => [u.difficulties, u.note])).toEqual([
      [['Normal', 'Hard'], 'Lv 11 (Hard 12) Black Beast; 3 health bars'],
      [['Maddening'], 'Lv 17 Black Beast; 3 health bars; goes for Byleth'],
    ])
    // Gilbert, green: once Miklan falls, he goes for the beast.
    expect(notes('fe16-5', 'Gilbert')).toEqual(['Lv 10 (Hard 11, Maddening 16) Fortress Knight; once Miklan is defeated, goes for the Black Beast'])
  })

  it("leaves the plain ways unsaid, a looter's to its own words, and keeps every note short", () => {
    // A Ruffian that waits until one of your units is in its reach.
    expect(map('fe16-0').units.find((u) => u.name === 'Ruffian' && u.tile[0] === 11)?.note).toBe('Lv 1 (Maddening 4)')
    for (const m of FE16_MAPS) {
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]) {
        if (u.looter) expect(AI.test(u.note ?? ''), `${m.id} ${u.name}`).toBe(false)
        expect((u.note ?? '').length, `${m.id} ${u.name}`).toBeLessThanOrEqual(300)
      }
    }
    // A time that checks something the maps can't say is 'an event in the chapter' (True Chivalry's villagers, who stop while a foe
    // is near).
    expect(notes('fe16-p44', 'Mercenary')).toContain(
      'Lv 15 (Hard 16, Maddening 22); after an event in the chapter, moves with the green Commoner at (14, 10) until the green Commoner ' +
        'at (14, 10) is defeated',
    )
  })
})

describe("Three Houses' spoiler walk", () => {
  const WHITE_CLOUDS = (h: string) => [
    'fe16-0', `fe16-1-${h}`, 'fe16-2', 'fe16-3', `fe16-4-${h}`, 'fe16-5', 'fe16-6', `fe16-7-${h}`, 'fe16-8', 'fe16-9', 'fe16-10',
    `fe16-11-${h}`,
  ]
  it('asks for a house after the Prologue; the Blue Lions go on to Azure Moon and the Golden Deer to Verdant Wind', () => {
    expect(FE16_FORK.choices.map((c) => c.id)).toEqual(['be', 'bl', 'gd'])
    expect(walkFork(FE16_FORK, 'bl').story.maps.map((m) => m.id)).toEqual([...WHITE_CLOUDS('bl'), ...PART_TWO['Azure Moon']])
    expect(walkFork(FE16_FORK, 'gd').story.maps.map((m) => m.id)).toEqual([...WHITE_CLOUDS('gd'), ...PART_TWO['Verdant Wind']])
    expect(walkFork(FE16_FORK, 'bl').pending).toBeUndefined()
  })

  it('asks the Black Eagles again at Chapter 12: Crimson Flower or Silver Snow', () => {
    const be = walkFork(FE16_FORK, 'be')
    expect(be.story.maps.map((m) => m.id)).toEqual(WHITE_CLOUDS('be'))
    expect(be.pending?.choices.map((c) => [c.id, c.proceed])).toEqual([
      ['cf', 'Proceed to Chapter 12 (Crimson Flower)'],
      ['ss', 'Proceed to Chapter 12 (Silver Snow)'],
    ])
    expect(walkFork(FE16_FORK, 'be/cf').story.maps.map((m) => m.id)).toEqual([...WHITE_CLOUDS('be'), ...PART_TWO['Crimson Flower']])
    expect(walkFork(FE16_FORK, 'be/ss').story.maps.map((m) => m.id)).toEqual([...WHITE_CLOUDS('be'), ...PART_TWO['Silver Snow']])
  })
})

describe("Three Houses' supports", () => {
  it("gives Fire Emblem Wiki's Linked Attack and Gambit Boost bonuses by level, read from the support tables and the program", () => {
    // Fire Emblem Wiki: Linked Attack from one ally (None, C, B, A, S): hit and avoid +3, +5, +7, +10, +15; attack +0-+5 for certain
    // pairs (the support table's 23); Gambit Boost attack +1-+5, hit +5-+25.
    expect(FE16_SUPPORTS.linked).toEqual({ hit: [3, 5, 7, 10, 15], avoid: [3, 5, 7, 10, 15], pairAttack: [0, 1, 2, 3, 5], pairs: 23 })
    expect(FE16_SUPPORTS.gambit).toEqual({ attack: [1, 2, 3, 4, 5], hit: [5, 10, 15, 20, 25] })
    // The + ranks count as the rank below (the program's rank table, 0xcea420).
    expect(FE16_SUPPORTS.rankLevels['B+']).toBe('B')
  })
})

describe("Three Houses' hit roll", () => {
  it('rolls two numbers mod 100 and averages them (0x5bb8a0), counted over every state of its generator', () => {
    expect(trueHit('2rn-mod100', 0).trueHitBasisPoints).toBe(0)
    expect(trueHit('2rn-mod100', 50).trueHitBasisPoints).toBe(5054)
    expect(trueHit('2rn-mod100', 80).trueHitBasisPoints).toBe(9221)
    // The plain two-number model would give 44.68% at 47; the generator's own period gives 44.69%.
    expect(trueHit('2rn-mod100', 47).trueHitBasisPoints).toBe(4469)
    expect(trueHit('2rn-mod100', 100).trueHitBasisPoints).toBe(10000)
  })
})
