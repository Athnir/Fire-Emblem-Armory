import { describe, expect, it } from 'vitest'
import { FE16_ITEM_SOURCES } from '../../data/fe16/fe16ItemSources'
import { FE16_LISTED } from '../../data/fe16/fe16Listed'
import { FE16_MAPS } from '../../data/fe16/fe16Maps'
import { FE16_FORK } from '../../data/fe16/fe16MapSet'
import { FE16_MOVE_CLASSES, FE16_TERRAIN } from '../../data/fe16/fe16Terrain'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'
import { trueHit } from '../trueHit'

const map = (id: string) => FE16_MAPS.find((m) => m.id === id)!
const on = (u: MapUnit, d: Difficulty) => !u.difficulties || u.difficulties.includes(d)
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && on(u, d))
const count = (m: ChapterMap, d: Difficulty, name: string) => foes(m, d).filter((u) => u.name === name).length
const weapon = (name: string) => FE16_LISTED.find((w) => w.name === name)

describe("Three Houses' White Clouds maps", () => {
  it('has the Prologue and Chapters 1 to 11, Chapters 1 and 7 once per house, each grid its own size', () => {
    expect(FE16_MAPS.map((m) => m.id)).toEqual([
      'fe16-0', 'fe16-1-be', 'fe16-1-bl', 'fe16-1-gd', 'fe16-2', 'fe16-3', 'fe16-4', 'fe16-5', 'fe16-6',
      'fe16-7-be', 'fe16-7-bl', 'fe16-7-gd', 'fe16-8', 'fe16-9', 'fe16-10', 'fe16-11',
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

  it("swaps a recruited student for a soldier of their class on the same tile (Chapter 7's stand-ins)", () => {
    const felix = map('fe16-7-be').units.find((u) => u.name === 'Felix')!
    expect(felix.standIn).toMatchObject({ name: 'Mercenary', when: 'if you recruited Felix into your house' })
  })
})

describe("Three Houses' White Clouds weapons", () => {
  it('lists only what something gives, a unit carries or a foe holds', () => {
    for (const w of FE16_LISTED) expect(FE16_ITEM_SOURCES[w.name]?.length, w.name).toBeGreaterThan(0)
  })

  it("gives the lords' and students' starting weapons and the Sword of the Creator after Chapter 4", () => {
    expect(FE16_ITEM_SOURCES['Iron Bow']).toContainEqual({ mapId: 'fe16-0', kind: 'kit', text: 'Carried by Claude from the start' })
    expect(FE16_ITEM_SOURCES['Sword of the Creator']).toEqual([{ mapId: 'fe16-4', kind: 'event-later', text: 'Given when the battle is won' }])
  })

  it("reads the record's stats and effectiveness", () => {
    expect(weapon('Iron Sword')).toMatchObject({ rank: 'E', mt: 5, hit: 90, crit: 0, wt: 5, uses: 40 })
    expect(weapon('Armorslayer')?.effective).toEqual(['armour'])
    expect(weapon('Iron Gauntlets')?.rules).toContain('Strikes twice when it attacks')
  })
})

describe("Three Houses' spoiler walk", () => {
  it('asks for a house after the Prologue, each house playing its own Chapters 1 and 7', () => {
    expect(FE16_FORK.choices.map((c) => c.id)).toEqual(['be', 'bl', 'gd'])
    expect(walkFork(FE16_FORK, 'bl').story.maps.map((m) => m.id)).toEqual([
      'fe16-0', 'fe16-1-bl', 'fe16-2', 'fe16-3', 'fe16-4', 'fe16-5', 'fe16-6', 'fe16-7-bl', 'fe16-8', 'fe16-9', 'fe16-10', 'fe16-11',
    ])
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
