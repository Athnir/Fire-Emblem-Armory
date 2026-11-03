import { describe, expect, it } from 'vitest'
import { FE16_ITEM_SOURCES } from '../../data/fe16/fe16ItemSources'
import { FE16_LISTED } from '../../data/fe16/fe16Listed'
import { FE16_MAPS } from '../../data/fe16/fe16Maps'
import { FE16_FORK } from '../../data/fe16/fe16MapSet'
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
    for (const m of FE16_MAPS) {
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
    const kostas = m.units.find((u) => u.name === 'Kostas')!
    expect(kostas).toMatchObject({ type: 'boss', carries: ['Iron Axe'], drops: ['Iron Axe'] })
    // The commander is the scenario's level, 3 (Maddening 6); the rest two lower.
    expect(kostas.note).toBe('Lv 3 (Maddening 6) Thief')
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
    expect(beasts.every((u) => u.bars === 2 && u.note?.endsWith('; 2 health bars'))).toBe(true)
    // Miklan's Black Beast has three; no one else on the White Clouds maps has any.
    expect(map('fe16-5').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Black Beast')?.bars).toBe(3)
    expect(FE16_MAPS.filter((m) => m.route === 'Story').flatMap((m) => m.units).filter((u) => u.bars && !u.size)).toEqual([])
    // Part II: the Immaculate One is 3 by 3 with four bars (Fire Emblem Wiki), the Hegemon Husk one tile with four.
    expect(map('fe16-37-cf').units.find((u) => u.name === 'The Immaculate One')).toMatchObject({ size: 3, bars: 4 })
    const husk = map('fe16-30-am').units.find((u) => u.name === 'Hegemon Husk')!
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
    const red = (m: ChapterMap) => DIFFS.map((d) => foes(m, d).filter((u) => !u.yellow).length)
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
  })

  it('brings the students back for the reunion (Chapter 13): Byleth and the leader start, the rest arrive on turns 3 and 5', () => {
    expect(map('fe16-13-ss').forced).toEqual([{ name: 'Seteth', tile: [1, 9] }])
    expect(map('fe16-13-am').forced).toEqual([{ name: 'Dimitri', tile: [1, 9] }])
    const ss = map('fe16-13-ss').joiners!
    expect(ss.map((j) => j.name)).toEqual(['Dorothea', 'Caspar', 'Petra', 'Bernadetta', 'Linhardt', 'Ferdinand'])
    expect(new Set(ss.map((j) => j.when))).toEqual(new Set(['Turn 3, your phase', 'Turn 5, your phase']))
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
