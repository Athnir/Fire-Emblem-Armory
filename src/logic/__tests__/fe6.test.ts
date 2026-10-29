import { describe, expect, it } from 'vitest'
import { FE6_ITEM_SOURCES } from '../../data/fe6/fe6ItemSources'
import { FE6_LISTED } from '../../data/fe6/fe6Listed'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE6_FORK, FE6_STORY } from '../../data/fe6/fe6MapSet'
import { FE6_MOVE_CLASSES, FE6_TERRAIN } from '../../data/fe6/fe6Terrain'
import { FE6_WEAPONS } from '../../data/fe6/fe6Weapons'
import type { ChapterMap } from '../../data/maps/types'
import { FE6_SUPPORTS } from '../../data/fe6/fe6Supports'
import { gbaSupportBonus } from '../gbaSupports'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE6_MAPS.find((m) => m.id === id)!
const objects = (m: ChapterMap, type: string) => m.objects.filter((o) => o.type === type)
const chests = (id: string) => objects(map(id), 'chest').map((o) => (o.type === 'chest' ? o.contents : '')).sort()
const villages = (id: string) => objects(map(id), 'village').map((o) => (o.type === 'village' ? o.reward : '')).sort()
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const sources = (item: string, kind: string) => (FE6_ITEM_SOURCES[item] ?? []).filter((s) => s.kind === kind).map((s) => `${s.mapId} ${s.text}`)

describe("The Binding Blade's maps", () => {
  it('has every chapter of both routes, the gaiden chapters and the five trial maps, each grid its own size', () => {
    expect(FE6_MAPS.filter((m) => m.route === 'Story')).toHaveLength(38)
    expect(FE6_MAPS.filter((m) => m.route === 'Trial').map((m) => m.title)).toEqual([
      'Valley of Death', 'Rainy Island', 'Snowy Defensive', "Pirate's Challenge", "Roy's Trial",
    ])
    for (const m of FE6_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    expect([map('fe6-1').width, map('fe6-1').height]).toEqual([15, 21])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const code of new Set(FE6_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE6_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE6_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
  })

  it("reads the terrain table's numbers: forts heal 20%, thrones give Res, peaks only brigands, berserkers and fliers climb", () => {
    expect(FE6_TERRAIN.bb).toMatchObject({ def: 2, avo: 20, heal: 20 })
    expect(FE6_TERRAIN.bc).toMatchObject({ def: 3, res: 5, avo: 30, heal: 10 })
    expect(FE6_TERRAIN.bq!.res).toBe(10)
    const peak = FE6_TERRAIN.bu!.move
    expect(Object.entries(peak).filter(([, c]) => c !== null).map(([k]) => k)).toEqual(['Brigands', 'Berserkers', 'Fliers'])
    expect(FE6_TERRAIN.tg!.move['Pirates']).toBe(2)
    expect(FE6_TERRAIN.tg!.move['Cavaliers']).toBeNull()
    // A tile only fliers enter gives no Def or Avoid: fliers' rows are all 0.
    expect(FE6_TERRAIN.wh).toMatchObject({ def: 0, avo: 0 })
  })

  it('places every unit inside its map, and never an icon on a tile nobody can stand on', () => {
    for (const m of FE6_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
      for (const [x, y] of m.starts) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} start ${x},${y}`).toBe(true)
    }
    for (const [code, info] of Object.entries(FE6_TERRAIN)) {
      if (['bh', 'bu', 'om', 'on', 'oo'].includes(code)) expect(Object.values(info!.move).some((c) => c !== null), code).toBe(true)
    }
  })

  it("starts each chapter with the enemies the Fire Emblem Wiki counts (its chapter data, Normal)", () => {
    // From each chapter page's "enemy" figure, reinforcements and later recruits left out.
    const wiki: Record<string, number> = {
      'fe6-1': 14, 'fe6-2': 20, 'fe6-3': 18, 'fe6-4': 16, 'fe6-5': 23, 'fe6-6': 28, 'fe6-7': 22, 'fe6-8': 29, 'fe6-8x': 31, 'fe6-9': 29,
      'fe6-10a': 23, 'fe6-11a': 22, 'fe6-10b': 26, 'fe6-11b': 24, 'fe6-12': 28, 'fe6-12x': 26, 'fe6-13': 40, 'fe6-14': 31, 'fe6-14x': 32,
      'fe6-15': 35, 'fe6-16': 32, 'fe6-16x': 31, 'fe6-17a': 28, 'fe6-18a': 32, 'fe6-19a': 37, 'fe6-20a': 32, 'fe6-20ax': 40,
      'fe6-17b': 29, 'fe6-18b': 31, 'fe6-19b': 44, 'fe6-20b': 33, 'fe6-20bx': 34, 'fe6-21': 35, 'fe6-21x': 45, 'fe6-22': 39,
      'fe6-23': 41, 'fe6-24': 27, 'fe6-final': 3, 'fe6-trial-1': 26, 'fe6-trial-2': 21, 'fe6-trial-3': 25, 'fe6-trial-4': 26,
      'fe6-trial-5': 25,
    }
    for (const m of FE6_MAPS) {
      const red = m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes('Normal')))
      expect(red.length, m.id).toBe(wiki[m.id])
    }
    // Hard places more from the start where a Hard-only turn-1 event does (Chapters 7, 21 and 22).
    const hardOnly = FE6_MAPS.filter((m) => m.units.some((u) => u.difficulties?.join() === 'Hard')).map((m) => m.id)
    expect(hardOnly).toEqual(['fe6-7', 'fe6-21', 'fe6-22'])
  })

  it("plays each opening: Chapter 1's bandits round Damas, Roy and the five knights on their tiles", () => {
    const m = map('fe6-1')
    expect(m.units.find((u) => u.name === 'Damas')).toMatchObject({ type: 'boss', carries: ['Steel axe'] })
    expect(m.corrinStart).toEqual([3, 3])
    expect(m.forced!.map((f) => f.name)).toEqual(['Marcus', 'Alen', 'Bors', 'Wolt', 'Lance'])
    expect(m.objectives).toEqual([{ type: 'seize', tiles: [[6, 17]], label: 'Seize the gate with Roy' }])
    // Chapter 3's late arrival: Slater comes on turn 3, after Zephiel, Idunn and Narcian leave the scene.
    const slater = map('fe6-3').reinforcements![0]
    expect(slater.when).toBe('Turn 3, enemy phase')
    expect(slater.units[0]).toMatchObject({ name: 'Slater', type: 'boss', tile: [20, 18] })
    expect(slater.units.map((u) => u.name)).not.toContain('Zephiel')
  })

  it("marks Hard's extra groups (event type 3) as Hard only, and the coded area checks with their areas", () => {
    const hard = (map('fe6-3').reinforcements ?? []).filter((g) => typeof g.when === 'object')
    expect(hard.map((g) => g.when)).toEqual([{ Hard: 'Turn 5, enemy phase' }, { Hard: 'Turn 10, enemy phase' }, { Hard: 'Turn 15, enemy phase' }])
    for (const g of hard) for (const u of g.units) expect(u.difficulties).toEqual(['Hard'])
    // Chapter 6's trap: once nobody is left in the starting area, foes appear behind you.
    const trap = map('fe6-6').reinforcements!.find((g) => g.areas)!
    expect(trap.when).toBe('Enemy phase, once none of your units is left in the marked area')
    expect(trap.areas).toEqual([{ who: 'player', rect: [1, 1, 26, 9] }])
  })

  it("names who recruits whom, matching a talk's character to its enemy version by name (Gonzalez in 10B)", () => {
    const talk = (id: string, name: string) => allUnits(map(id)).find((u) => u.name === name)?.talk
    expect(talk('fe6-4', 'Rutger')).toBe('Recruit: talk with Clarine')
    expect(talk('fe6-10b', 'Gonzalez')).toBe('Recruit: talk with Lilina')
    expect(talk('fe6-10b', 'Thea')).toBe('Recruit: talk with Shanna or Klein')
    expect(talk('fe6-16', 'Hugh')).toMatch(/^Recruit: talk with Roy \(for gold: 10,000/)
    expect(talk('fe6-12', 'Cath')).toBe('Recruit: talk with Roy (on the third talk, counting one per chapter)')
  })

  it("holds the chests, villages and buried items Serenes Forest's item-locations page lists (the patch's names)", () => {
    expect(chests('fe6-6')).toEqual(['2000 gold', '3000 gold', '5000 gold', 'Goddess icon', 'Killer axe', 'Short bow', 'Silver lance', 'Unlock'])
    expect(chests('fe6-8')).toEqual(['Elfire', 'Elysian whip', 'Guiding ring', 'Killer bow', 'Knight crest', 'Light Brand', 'Secret book', 'Silver axe'])
    expect(chests('fe6-12x')).toHaveLength(12)
    // Serenes: one 5000G village in Chapter 1 (the brigand's is closed in the opening), Knightslayer = the patch's Horseslayer.
    expect(villages('fe6-1')).toEqual(['5000 gold'])
    expect(villages('fe6-7')).toEqual(['Elixir', 'Hero crest', 'Horseslayer', 'Killing edge', 'Longbow', 'Physic', 'Red gem', 'Torch'])
    expect(villages('fe6-10b')).toContain('Speedwings if visited by Ward or Lot; anyone else: Elixir')
    expect(villages('fe6-11b')).toEqual(['Red gem'])
    const sand = objects(map('fe6-14'), 'hidden').map((o) => (o.type === 'hidden' ? o.contents : ''))
    expect(sand.sort()).toEqual(['Boots', 'Guiding ring', 'Silence', 'Silver blade', 'Silver card', 'Speedwings', 'Talisman', 'Warp'])
    const ring = objects(map('fe6-14'), 'hidden').find((o) => o.type === 'hidden' && o.contents === 'Guiding ring')
    expect(ring?.type === 'hidden' && ring.note).toBe('Found only by Sophia, by stopping in the area.')
  })

  it("says Chapter 9's two north-eastern villages close each other (the route split)", () => {
    const notes = objects(map('fe6-9'), 'village').flatMap((o) => (o.type === 'village' && o.note ? [o.note] : []))
    expect(notes).toEqual(['Visiting it closes the village at (22, 24).', 'Visiting it closes the village at (19, 24).'])
  })
})

describe("The Binding Blade's item sources", () => {
  it('names only maps that exist', () => {
    const ids = new Set(FE6_MAPS.map((m) => m.id))
    for (const [item, list] of Object.entries(FE6_ITEM_SOURCES)) for (const s of list) expect(ids.has(s.mapId), `${item} ${s.mapId}`).toBe(true)
  })

  it("gives the chapter-end gifts Serenes lists (Durandal after 8x, the Binding Blade after 21 or 21x)", () => {
    expect(sources('Durandal', 'event')).toEqual(['fe6-8x Given to Roy at the end of the chapter'])
    expect(sources('Binding Blade', 'event')).toEqual(['fe6-21 Given to Roy at the end of the chapter', 'fe6-21x Given to Roy at the end of the chapter'])
    expect(sources('Thunder', 'talk')).toEqual(['fe6-8 Lilina talks to Roy'])
    // Fa joins at the end of Chapter 15, so her stone counts from Chapter 16.
    expect(sources('Divinestone', 'kit-later')).toEqual(['fe6-15 Carried by Fae, who joins at the end of the chapter'])
  })

  it('lists what anything gives or a unit carries, and marks what only foes carry', () => {
    const listed = new Set(FE6_LISTED.map((w) => w.name))
    for (const name of ['Poison lance', 'Poison bow', 'Fortify']) expect(listed.has(name), name).toBe(false)
    const foeOnly = FE6_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toEqual(expect.arrayContaining(['Eckesachs', 'Runesword', 'Spear', 'Dark breath', 'Fenrir']))
    expect(foeOnly).not.toContain('Iron sword')
    expect(FE6_LISTED.length).toBe(FE6_WEAPONS.length - 3)
  })
})

describe("The Binding Blade's story and supports", () => {
  it('splits twice: 10A or 10B after Chapter 9, Ilia or Sacae after 16x, every route ending at the Final Chapter', () => {
    expect(FE6_FORK.before.maps.at(-1)!.id).toBe('fe6-9')
    for (const a of ['a', 'b']) {
      expect(walkFork(FE6_FORK, a).pending).toBeDefined()
      expect(walkFork(FE6_FORK, a).story.maps.at(-1)!.id).toBe('fe6-16x')
      for (const b of ['ilia', 'sacae']) {
        const { story, pending, chosen } = walkFork(FE6_FORK, `${a}/${b}`)
        expect(pending).toBeUndefined()
        expect(chosen).toHaveLength(2)
        expect(story.maps.at(-1)!.id).toBe('fe6-final')
        expect(story.maps).toHaveLength(31)
        expect(story.opensAt!('fe6-trial-1')).toBe(30)
        // The other route's chapters never open.
        expect(story.opensAt!(b === 'ilia' ? 'fe6-17b' : 'fe6-17a')).toBe(Infinity)
      }
    }
    expect(walkFork(FE6_FORK, 'b/sacae').story.maps.map((m) => m.heading)).toContain('Ch.20Bx')
    // An unknown choice stops the walk where it is.
    expect(walkFork(FE6_FORK, 'x').story).toBe(FE6_FORK.before)
    expect(FE6_STORY.maps).toHaveLength(38)
  })

  it('works a support bonus out as the battle code does: both rows times the level, halved once, rounded down', () => {
    // Fire (Atk 1, Hit 5, Avo 5, Crit 5) with a Thunder partner (Def 1, Avo 5, Crit 5, Dodge 5) at C.
    expect(gbaSupportBonus(FE6_SUPPORTS, 'Fire', [{ affinity: 'Thunder', level: 1 }])).toEqual({ atk: 0, def: 0, hit: 2, avoid: 5, crit: 5, dodge: 2 })
    // Two half points from two partners add up to a whole one.
    expect(gbaSupportBonus(FE6_SUPPORTS, 'Fire', [{ affinity: 'Thunder', level: 1 }, { affinity: 'Thunder', level: 1 }]).atk).toBe(1)
  })
})
