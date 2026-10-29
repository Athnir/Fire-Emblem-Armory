import { describe, expect, it } from 'vitest'
import { FE8_ITEM_SOURCES } from '../../data/fe8/fe8ItemSources'
import { FE8_LISTED } from '../../data/fe8/fe8Listed'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE8_FORK, FE8_STORY } from '../../data/fe8/fe8MapSet'
import { FE8_SUPPORTS } from '../../data/fe8/fe8Supports'
import { FE8_MOVE_CLASSES, FE8_TERRAIN } from '../../data/fe8/fe8Terrain'
import { FE8_TRIANGLE } from '../../data/fe8/fe8Triangle'
import { FE8_WEAPONS } from '../../data/fe8/fe8Weapons'
import type { ChapterMap, Difficulty } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE8_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const red = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d))).length

describe("The Sacred Stones' maps", () => {
  it('has the shared chapters, both routes to the end, the Tower of Valni and the Lagdou Ruins, each grid its own size', () => {
    expect(FE8_MAPS.filter((m) => m.route === 'Shared')).toHaveLength(10)
    expect(FE8_MAPS.filter((m) => m.route === 'Eirika')).toHaveLength(14)
    expect(FE8_MAPS.filter((m) => m.route === 'Ephraim')).toHaveLength(14)
    expect(FE8_MAPS.filter((m) => m.route === 'Extra')).toHaveLength(18)
    for (const m of FE8_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const code of new Set(FE8_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE8_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE8_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
    // Two kinds of gate: terrain 11 gives 20 Avoid, terrain 35 (its own code) 30.
    expect(FE8_TERRAIN.bd).toMatchObject({ avo: 20 })
    expect(FE8_TERRAIN.bv).toMatchObject({ avo: 30 })
  })

  it('places every unit inside its map', () => {
    for (const m of FE8_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each chapter with the enemies the Fire Emblem Wiki counts (its chapter data, per route and difficulty)', () => {
    // [Easy, Normal, Hard] from each chapter page's "Enemy" figure, reinforcements left out (one number: the same on all three).
    const wiki: Record<string, number | number[]> = {
      'fe8-prologue': [0, 3, 3], 'fe8-1': 7, 'fe8-2': 6, 'fe8-3': 10, 'fe8-4': 15,
      // The wiki's 16 leaves out Joshua, the Myrmidon Natasha recruits (it counts every other chapter's recruitable foes: Marisa,
      // Amelia, Rennac, Cormag); the opening loads him as an enemy.
      'fe8-5': 17,
      'fe8-5x': 31, 'fe8-6': 24, 'fe8-7': 19, 'fe8-8': [27, 27, 32],
      'fe8-eirika-9': [23, 23, 29], 'fe8-eirika-10': [34, 34, 40], 'fe8-eirika-11': 41, 'fe8-eirika-12': [32, 32, 38],
      'fe8-eirika-13': [22, 22, 28], 'fe8-eirika-14': 42, 'fe8-eirika-15': 46, 'fe8-eirika-16': [29, 29, 35], 'fe8-eirika-17': 25,
      'fe8-eirika-18': [28, 28, 34], 'fe8-eirika-19': 25, 'fe8-eirika-20': [47, 47, 50], 'fe8-eirika-final': 36, 'fe8-eirika-final-2': 1,
      'fe8-ephraim-9': 38, 'fe8-ephraim-10': [24, 24, 28], 'fe8-ephraim-11': 10, 'fe8-ephraim-12': 37, 'fe8-ephraim-13': 44,
      'fe8-ephraim-14': 42, 'fe8-ephraim-15': 45, 'fe8-ephraim-16': [37, 37, 42], 'fe8-ephraim-17': 25, 'fe8-ephraim-18': [28, 28, 34],
      'fe8-ephraim-19': 25, 'fe8-ephraim-20': [47, 47, 50], 'fe8-ephraim-final': 36, 'fe8-ephraim-final-2': 1,
    }
    for (const m of FE8_MAPS.filter((x) => x.route !== 'Extra')) {
      const w = wiki[m.id]
      const [easy, normal, hard] = typeof w === 'number' ? [w, w, w] : w
      expect(red(m, 'Easy'), `${m.id} Easy`).toBe(easy)
      expect(red(m, 'Normal'), `${m.id} Normal`).toBe(normal)
      expect(red(m, 'Hard'), `${m.id} Hard`).toBe(hard)
    }
  })

  it("plays each opening: Artur's scripted battle takes one Mogall off Chapter 4; the deploy tiles are the prep group's", () => {
    expect(map('fe8-4').units.filter((u) => u.name === 'Mogall')).toHaveLength(3)
    expect(map('fe8-prologue').units.find((u) => u.name === "O'Neill")).toMatchObject({ type: 'boss', carries: ['Iron Axe'] })
    expect(map('fe8-eirika-15').starts).toHaveLength(12)
    expect(map('fe8-5x').lord).toBe('Ephraim')
    expect(map('fe8-eirika-final-2').defeat).toBe('Eirika or Ephraim is defeated')
  })

  it("moves generic enemies' levels by difficulty, by the chapter's own figures (+0x14)", () => {
    // Chapter 5: Easy −4, Normal −2, Hard +3 for every enemy whose character id is above 0x3B.
    expect(map('fe8-5').units.find((u) => u.name === 'Saar')!.note).toBe('Lv 6 (Easy 4, Hard 11) Knight')
    // Named characters keep their level.
    expect(map('fe8-5').units.find((u) => u.name === 'Joshua')!.note).toBe('Lv 5 Myrmidon')
  })

  it('reads who recruits whom', () => {
    const talk = (id: string, name: string) => [...allUnits(map(id)), ...(map(id).joiners ?? [])].find((u) => u.name === name && u.talk)?.talk
    expect(talk('fe8-5', 'Joshua')).toBe('Recruit: talk with Natasha')
  })

  it('says what an end scene hands over only on a condition, from its own checks', () => {
    expect(map('fe8-6').notes).toContain("Orion's Bolt: given to Eirika at the end of the chapter if all three 'Renais Cit.' units survive.")
    expect(map('fe8-eirika-19').notes).toContain(
      "Light Brand: given to your army at the end of the chapter if at least 6 of the other army's units are left.",
    )
  })

  it('shows the Tower and the Ruins with their random monsters as spawn points, and nothing on tiles no one can enter', () => {
    const tower = map('fe8-tower-1')
    expect(tower.units.filter((u) => u.name === 'Random monster').length).toBeGreaterThan(10)
    expect(tower.units.find((u) => u.name === 'Random monster')!.carries).toBeUndefined()
    expect(tower.objects).toEqual([])
  })
})

describe("The Sacred Stones' story under the spoiler block", () => {
  it("walks the Prologue to Chapter 8, then Eirika's route or Ephraim's", () => {
    expect(walkFork(FE8_FORK, '').story.maps).toHaveLength(10)
    const e = walkFork(FE8_FORK, 'eirika').story.maps.map((m) => m.id)
    expect(e).toContain('fe8-eirika-11')
    expect(e).not.toContain('fe8-ephraim-9')
    expect(e[e.length - 1]).toBe('fe8-eirika-final-2')
    const reached = new Set<string>()
    for (const r of ['eirika', 'ephraim']) for (const m of walkFork(FE8_FORK, r).story.maps) reached.add(m.id)
    for (const m of FE8_MAPS.filter((x) => x.route !== 'Extra')) expect(reached.has(m.id), m.id).toBe(true)
  })

  it('names chapters by route without the block', () => {
    expect(FE8_STORY.name(map('fe8-ephraim-13'))).toBe("Chapter 13, Ephraim's route")
    expect(FE8_STORY.name(map('fe8-5x'))).toBe('Chapter 5x')
  })
})

describe("The Sacred Stones' weapons, triangle and supports", () => {
  it('reads the item table: the legendary weapons double Mt where the rest triple it', () => {
    const w = (name: string) => FE8_WEAPONS.find((x) => x.name === name)!
    expect(w('Sieglinde')).toMatchObject({ effectiveMultiplier: 2, effective: ['dragon', 'monster'] })
    expect(w('Rapier').effectiveMultiplier).toBeUndefined()
    expect(w('Rapier').rules).toContain('Eirika only')
  })

  it('lists only what turns up, marking what only foes carry', () => {
    for (const x of FE8_LISTED) expect(FE8_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
    expect(FE8_LISTED.find((x) => x.name === 'Iron Sword')!.foeOnly).toBeUndefined()
    expect(FE8_LISTED.find((x) => x.name === 'Wind Sword')!.foeOnly).toBe(true)
  })

  it('reads the world map towns\' shops, open from the chapter after the town\'s', () => {
    expect(FE8_ITEM_SOURCES['Iron Sword']).toContainEqual({ mapId: 'fe8-2', kind: 'town-shop-later', text: 'Sold at the armory in Ide (world map)' })
    expect(FE8_ITEM_SOURCES['Brave Sword']).toContainEqual({
      mapId: 'fe8-ephraim-14',
      kind: 'town-shop-later',
      text: 'Sold at the secret shop in Grado Keep (world map), with a Member Card',
    })
  })

  it("counts a unit's starting items once per route, where it joins", () => {
    const joins = new Map<string, Set<string>>()
    for (const list of Object.values(FE8_ITEM_SOURCES)) {
      for (const s of list.filter((x) => x.kind.startsWith('kit'))) {
        const who = s.text.match(/^Carried by (.+?)(,| on)/)![1]
        const route = map(s.mapId).route
        for (const r of route === 'Shared' ? ['Eirika', 'Ephraim'] : [route]) {
          const key = `${who} on ${r}'s route`
          joins.set(key, new Set([...(joins.get(key) ?? []), s.mapId]))
        }
      }
    }
    for (const [who, chapters] of joins) expect([...chapters], who).toHaveLength(1)
    expect(FE8_ITEM_SOURCES['Sieglinde'].map((s) => `${s.mapId}: ${s.text}`)).toEqual([
      'fe8-eirika-16: Given to Eirika at the end of the chapter',
      'fe8-ephraim-16: Given to Eirika at the end of the chapter',
    ])
  })

  it('gives the triangle 15 hit and 1 Mt, and supports at 81, 161 and 241 points', () => {
    expect([FE8_TRIANGLE.hit, FE8_TRIANGLE.mt]).toEqual([15, 1])
    expect(FE8_SUPPORTS.levels).toEqual({ C: 81, B: 161, A: 241 })
  })
})
