import { describe, expect, it } from 'vitest'
import { FE7_ITEM_SOURCES } from '../../data/fe7/fe7ItemSources'
import { FE7_LISTED } from '../../data/fe7/fe7Listed'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE7_FORK, FE7_STORY } from '../../data/fe7/fe7MapSet'
import { FE7_SUPPORTS } from '../../data/fe7/fe7Supports'
import { FE7_MOVE_CLASSES, FE7_TERRAIN } from '../../data/fe7/fe7Terrain'
import { FE7_TRIANGLE } from '../../data/fe7/fe7Triangle'
import { FE7_WEAPONS } from '../../data/fe7/fe7Weapons'
import type { ChapterMap, Difficulty } from '../../data/maps/types'
import { gbaSupportBonus } from '../gbaSupports'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE7_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const red = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d))).length

describe("The Blazing Blade's maps", () => {
  it("has Lyn's story, and Eliwood's and Hector's with both versions of the split chapters, each grid its own size", () => {
    expect(FE7_MAPS.filter((m) => m.route === 'Lyn')).toHaveLength(12)
    expect(FE7_MAPS.filter((m) => m.route === 'Eliwood')).toHaveLength(30)
    expect(FE7_MAPS.filter((m) => m.route === 'Hector')).toHaveLength(34)
    for (const m of FE7_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // Lyn's story is played on Normal only.
    for (const m of FE7_MAPS) expect(m.difficulties, m.id).toEqual(m.route === 'Lyn' ? ['Normal'] : undefined)
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const m of FE7_MAPS) {
      for (const row of m.grid) {
        for (const code of rowCodes(row)) {
          const info = FE7_TERRAIN[code]
          expect(info, `${m.id} ${code}`).toBeDefined()
          for (const mc of FE7_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
        }
      }
    }
    expect(FE7_TERRAIN.bb).toMatchObject({ def: 2, avo: 20, heal: 20 })
    expect(FE7_TERRAIN.bc).toMatchObject({ def: 2, res: 5, avo: 20, heal: 10 })
    const peak = FE7_TERRAIN.bu!.move
    expect(Object.entries(peak).filter(([, c]) => c !== null).map(([k]) => k)).toEqual(['Brigands', 'Berserkers', 'Fliers'])
    expect(FE7_TERRAIN.tm!.move['Infantry']).toBe(2)
  })

  it('places every unit inside its map', () => {
    for (const m of FE7_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it("starts each chapter with the enemies the Fire Emblem Wiki counts (its chapter data, per story and difficulty)", () => {
    // [Normal, Hard] from each chapter page's "enemy" figure, reinforcements left out; Lyn's story has Normal only.
    const wiki: Record<string, number[]> = {
      'fe7-lyn-prologue': [2], 'fe7-lyn-1': [5], 'fe7-lyn-2': [6], 'fe7-lyn-3': [9], 'fe7-lyn-4': [14], 'fe7-lyn-5': [7],
      'fe7-lyn-6': [7], 'fe7-lyn-7': [11], 'fe7-lyn-7x': [12], 'fe7-lyn-8': [14], 'fe7-lyn-9': [5], 'fe7-lyn-10': [11],
      'fe7-e-11': [10, 13], 'fe7-e-12': [15, 20], 'fe7-e-13': [12, 16], 'fe7-e-13x': [13, 17], 'fe7-e-14': [21, 22],
      'fe7-e-15': [19, 21], 'fe7-e-16': [25, 28], 'fe7-e-16x': [14, 21], 'fe7-e-17': [18, 20], 'fe7-e-18': [21, 29],
      'fe7-e-18x': [24, 27], 'fe7-e-19': [26, 33], 'fe7-e-20': [18, 26], 'fe7-e-21': [14, 22], 'fe7-e-22': [20, 27],
      'fe7-e-22x': [15, 19], 'fe7-e-23-lloyd': [18, 28], 'fe7-e-23-linus': [27, 37], 'fe7-e-24': [23, 34],
      'fe7-e-25-kenneth': [25, 34], 'fe7-e-25-jerme': [38, 46], 'fe7-e-26': [28, 35], 'fe7-e-26x': [28, 36], 'fe7-e-27': [43, 43],
      'fe7-e-28': [26, 32], 'fe7-e-29': [28, 35], 'fe7-e-29x': [0, 0], 'fe7-e-30': [25, 36], 'fe7-e-final': [17, 17],
      'fe7-e-final-2': [7, 7],
      'fe7-h-11': [9, 10], 'fe7-h-12': [12, 16], 'fe7-h-13': [14, 19], 'fe7-h-13x': [15, 21], 'fe7-h-14': [18, 30],
      'fe7-h-15': [10, 16], 'fe7-h-16': [18, 24], 'fe7-h-17': [25, 29], 'fe7-h-17x': [14, 21], 'fe7-h-18': [11, 24],
      'fe7-h-19': [21, 33], 'fe7-h-19x': [20, 30], 'fe7-h-19x-2': [23, 27], 'fe7-h-20': [25, 38], 'fe7-h-21': [16, 23],
      'fe7-h-22': [16, 36], 'fe7-h-23': [20, 31], 'fe7-h-23x': [15, 21], 'fe7-h-24-lloyd': [19, 28], 'fe7-h-24-linus': [25, 39],
      'fe7-h-25': [27, 27], 'fe7-h-26': [24, 34], 'fe7-h-27-kenneth': [24, 36],
      // The wiki gives Hector Hard 50; the event data's Hector Hard group (the fourth enemy group of Chapter 25b's event data,
      // read in scripts/build-fe7-maps.py) holds 54 units, all of them enemies on distinct tiles. The game wins.
      'fe7-h-27-jerme': [38, 54],
      'fe7-h-28': [34, 39], 'fe7-h-28x': [32, 50], 'fe7-h-29': [43, 45], 'fe7-h-30': [22, 22], 'fe7-h-31': [27, 37],
      'fe7-h-31x': [0, 0], 'fe7-h-32': [32, 39], 'fe7-h-32x': [17, 17], 'fe7-h-final': [17, 17], 'fe7-h-final-2': [7, 7],
    }
    for (const m of FE7_MAPS) {
      const [normal, hard] = wiki[m.id]
      expect(red(m, 'Normal'), `${m.id} Normal`).toBe(normal)
      if (hard !== undefined) expect(red(m, 'Hard'), `${m.id} Hard`).toBe(hard)
    }
  })

  it("plays each opening: Taking Leave's brigands round Groznyi, Eliwood with Marcus, Lowen and Rebecca beside him", () => {
    const m = map('fe7-e-11')
    expect(m.units.find((u) => u.name === 'Groznyi')).toMatchObject({ type: 'boss', carries: ['Iron axe'] })
    expect(m.forced!.map((f) => f.name)).toEqual(['Marcus', 'Lowen', 'Rebecca'])
    expect(m.lord).toBe('Eliwood')
    // A chapter with preparations starts with the event data's enemy group for the story and difficulty.
    expect(map('fe7-h-14').units.filter((u) => u.name === 'Erik')).toHaveLength(2)
  })

  it('reads who recruits whom, per story', () => {
    const talk = (id: string, name: string) =>
      [...allUnits(map(id)), ...(map(id).joiners ?? [])].find((u) => u.name === name && u.talk)?.talk
    expect(talk('fe7-lyn-5', 'Erk')).toBe('Recruit: talk with Lyn')
    expect(talk('fe7-e-13', 'Guy')).toBe('Recruit: talk with Matthew')
    expect(talk('fe7-e-22', 'Hawkeye')).toBe('Recruit: talk with Eliwood')
    expect(talk('fe7-h-22', 'Hawkeye')).toBeUndefined()
    expect(talk('fe7-h-23', 'Hawkeye')).toBe('Recruit: talk with Hector')
  })

  it('says when the gaiden chapters and the split chapters are played', () => {
    expect(map('fe7-lyn-7x').notes[0]).toMatch(/^Opens if Chapter 7 is cleared within 15 turns\./)
    expect(map('fe7-h-17x').notes[0]).toMatch(/^Opens if Chapter 17 is cleared/)
    expect(map('fe7-e-16x').notes[0]).toMatch(/^Opens if Chapter 16 is cleared/)
    expect(map('fe7-h-32x').notes[0]).toMatch(/within 20 turns/)
    expect(map('fe7-e-25-jerme').notes[0]).toMatch(/^Played when Guy, Dorcas, Bartre and Raven/)
  })
})

describe("The Blazing Blade's story under the spoiler block", () => {
  it("walks Lyn's story, then Eliwood's or Hector's, splitting at Lloyd or Linus and at Kenneth or Jerme", () => {
    expect(walkFork(FE7_FORK, '').story.maps).toHaveLength(12)
    const e = walkFork(FE7_FORK, 'eliwood/lloyd/kenneth').story.maps.map((m) => m.id)
    expect(e).toContain('fe7-e-23-lloyd')
    expect(e).toContain('fe7-e-25-kenneth')
    expect(e).not.toContain('fe7-e-23-linus')
    expect(e[e.length - 1]).toBe('fe7-e-final-2')
    const h = walkFork(FE7_FORK, 'hector/linus/jerme').story.maps.map((m) => m.id)
    expect(h.filter((id) => id.startsWith('fe7-h'))).toHaveLength(32)
    // Every map is in some story.
    const reached = new Set<string>()
    for (const r of ['eliwood/lloyd/kenneth', 'eliwood/linus/jerme', 'hector/lloyd/kenneth', 'hector/linus/jerme'])
      for (const m of walkFork(FE7_FORK, r).story.maps) reached.add(m.id)
    for (const m of FE7_MAPS) expect(reached.has(m.id), m.id).toBe(true)
  })

  it('names chapters by story without the block', () => {
    expect(FE7_STORY.name(map('fe7-h-13'))).toBe("Chapter 13, Hector's story")
    expect(FE7_STORY.name(map('fe7-lyn-prologue'))).toBe('Prologue')
  })
})

describe("The Blazing Blade's weapons, triangle and supports", () => {
  it("reads the item table: Durandal is Eliwood's, effective against dragons; Luna ignores defence", () => {
    const w = (name: string) => FE7_WEAPONS.find((x) => x.name === name)!
    expect(w('Durandal')).toMatchObject({ mt: 17, rank: 'Prf', effective: ['wyvern'], stats: { str: 5 } })
    expect(w('Durandal').rules).toContain('Eliwood only')
    expect(w('Luna').rules).toContain("The target's Def or Res counts as 0")
    expect(w('Eclipse').rules).toContain("Deals half the target's current HP, rounded up")
    expect(w('Lancereaver').rules).toContain('Reverses the weapon triangle and doubles it')
  })

  it("reads drops: a foe whose character or class has ability 0x08000000 drops its last item (the Final Chapter's ghosts)", () => {
    const final = map('fe7-e-final')
    expect(final.units.find((u) => u.name === 'Lloyd')!.drops).toEqual(['Regal blade'])
    expect(final.units.find((u) => u.name === 'Darin')!.drops).toEqual(['Rex Hasta'])
    expect(FE7_LISTED.find((x) => x.name === 'Regal blade')!.foeOnly).toBeUndefined()
  })

  it('lists only what turns up, marking what only foes carry', () => {
    for (const x of FE7_LISTED) expect(FE7_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
    expect(FE7_LISTED.find((x) => x.name === 'Iron sword')!.foeOnly).toBeUndefined()
  })

  it("counts a unit's starting items once per story, where it joins, not every chapter the opening reloads it", () => {
    const joins = new Map<string, Set<string>>()
    for (const list of Object.values(FE7_ITEM_SOURCES)) {
      for (const s of list.filter((x) => x.kind.startsWith('kit'))) {
        const key = `${s.text.match(/^Carried by (.+?)(,| on)/)![1]} in ${map(s.mapId).route}'s story`
        joins.set(key, new Set([...(joins.get(key) ?? []), s.mapId.replace(/-(kenneth|jerme|lloyd|linus)$/, '')]))
      }
    }
    // The two versions of a split chapter are one chapter (Karel joins in either version of Chapter 25).
    for (const [who, chapters] of joins) expect([...chapters], who).toHaveLength(1)
    const where = (name: string) => FE7_ITEM_SOURCES[name].map((s) => `${s.mapId}: ${s.text}`)
    expect(where('Mani Katti')).toEqual([
      'fe7-lyn-2: Given to Lyn at the end of the chapter',
      'fe7-e-15: Carried by Lyn on joining',
      'fe7-h-16: Carried by Lyn on joining',
    ])
    // Athos joins in the Final Chapter with the legendary weapons; a routine in the opening adds the Sol Katti (0x0807DBF5).
    for (const name of ['Durandal', 'Armads', 'Forblaze', 'Aureola', 'Sol Katti'])
      expect(where(name), name).toEqual(['fe7-e-final: Carried by Athos on joining', 'fe7-h-final: Carried by Athos on joining'])
    // What a foe holds is only said for a weapon nothing else gives.
    for (const [name, list] of Object.entries(FE7_ITEM_SOURCES))
      if (list.some((s) => !s.kind.startsWith('foe'))) expect(list.filter((s) => s.kind.startsWith('foe')), name).toEqual([])
  })

  it('gives the triangle 15 hit and 1 Mt, and supports at 81, 161 and 241 points', () => {
    expect([FE7_TRIANGLE.hit, FE7_TRIANGLE.mt]).toEqual([15, 1])
    expect(FE7_SUPPORTS.levels).toEqual({ C: 81, B: 161, A: 241 })
    expect(gbaSupportBonus(FE7_SUPPORTS, 'Fire', [{ affinity: 'Thunder', level: 1 }])).toEqual({ atk: 0, def: 0, hit: 2, avoid: 5, crit: 5, dodge: 2 })
  })
})
