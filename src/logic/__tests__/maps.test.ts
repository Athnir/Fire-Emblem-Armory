import { describe, expect, it } from 'vitest'
import { FE10_MAPS } from '../../data/fe10/fe10Maps'
import { FE9_MAPS } from '../../data/fe9/fe9Maps'
import { ALL_MAPS } from '../../data/maps'
import { CONQUEST_12 } from '../../data/maps/conquest12'
import { FATES_TERRAIN } from '../../data/maps/fatesTerrain'
import { GAME_CHAPTERS } from '../../data/maps/gameChapters'
import { TERRAIN_CODES } from '../../data/maps/terrainCodes'
import { DIFFICULTIES } from '../../data/maps/types'
import type { ChapterMap, Tile } from '../../data/maps/types'
import { applyChanges, atStart, digAt, resolveTile, rowCodes, terrainAt, terrainInfo, tileKey, tilesInRadius } from '../maps'
const byId = (id: string) => ALL_MAPS.find((m) => m.id === id)!
const CHAPTER_1 = byId('fe14-1')
const CHAPTER_4 = byId('fe14-4')
const CONQUEST_6 = byId('fe14c-6')

describe('every map', () => {
  for (const map of ALL_MAPS) {
    const onMap = ([x, y]: Tile) => x >= 1 && x <= map.width && y >= 1 && y <= map.height

    it(`${map.id}: grid matches its declared size and uses known terrain codes`, () => {
      expect(map.grid).toHaveLength(map.height)
      for (const row of map.grid) {
        expect(row).toHaveLength(2 * map.width)
        for (const code of rowCodes(row)) expect(FATES_TERRAIN).toHaveProperty(code)
      }
    })

    it(`${map.id}: every placed tile is on the map, and nothing shares a tile with another object`, () => {
      const seen = new Set<string>()
      for (const o of map.objects) {
        expect(onMap(o.tile), `${o.type} at ${o.tile}`).toBe(true)
        expect(seen.has(tileKey(o.tile)), `two objects at ${o.tile}`).toBe(false)
        seen.add(tileKey(o.tile))
      }
      for (const t of [...map.starts, ...map.units.map((u) => u.tile), ...map.objectives.flatMap((o) => o.tiles)]) {
        expect(onMap(t), `${t}`).toBe(true)
      }
      if (map.corrinStart) expect(map.starts.map(tileKey), "Corrin's start").toContain(tileKey(map.corrinStart))
      for (const f of map.forced ?? []) if (f.tile) expect(map.starts.map(tileKey), `forced ${f.name}`).toContain(tileKey(f.tile))
      // Reinforcements and joiners may enter from off the map, but always stop on it.
      for (const g of map.reinforcements ?? []) for (const u of g.units) expect(onMap(u.tile), `${g.label} ${u.name} ${u.tile}`).toBe(true)
      for (const j of map.joiners ?? []) expect(onMap(j.tile), `${j.name} ${j.tile}`).toBe(true)
    })

    it(`${map.id}: objects sit on matching terrain; units, starts and veins on walkable tiles`, () => {
      const expected = { chest: 'oa', door: 'ob', village: 'oc', pot: 'ta' } as const
      for (const o of map.objects) if (o.type in expected) expect(terrainAt(map, o.tile), `${o.type} at ${o.tile}`).toBe(expected[o.type as keyof typeof expected])
      // Something must be able to stand there (fliers start over open sky in Conquest 20; the Endgame's
      // invaders stand on Dark Waters, which only their own movement type can cross).
      const walkable = (t: Tile) =>
        terrainAt(map, t) === 'wm' || Object.values(terrainInfo(map, terrainAt(map, t)).move).some((m) => m !== null)
      const shiny = map.objects.filter((o) => o.type === 'shiny').map((o) => o.tile)
      // Revelation 10's foes under the snow stand on it until it's dug.
      for (const t of [...map.starts, ...map.units.filter((u) => !u.buried).map((u) => u.tile), ...shiny]) expect(walkable(t), `${t}`).toBe(true)
      for (const c of map.changes.filter((x) => x.trigger === 'dragonVein')) {
        for (const d of DIFFICULTIES) expect(walkable(resolveTile(c.tile, d)), `${c.id} on ${d}`).toBe(true)
      }
      // A breakable wall blocks the way until it's attacked down, then it's open ground.
      for (const c of map.changes.filter((x) => x.trigger === 'breakable')) {
        const t = c.tile.default
        expect(walkable(t) && terrainInfo(map, terrainAt(map, t)).move['Infantry A'] !== null, `${c.id} blocks`).toBe(false)
        const broken = applyChanges(map, new Set([c.id]))
        expect(terrainInfo(broken, terrainAt(broken, t)).move['Infantry A'], `${c.id} opens`).not.toBeNull()
      }
    })

    it(`${map.id}: every change patch is on the map and actually changes its tile`, () => {
      for (const c of map.changes) {
        for (const p of c.patch ?? []) {
          expect(onMap(p.tile), `${c.id} ${p.tile}`).toBe(true)
          expect(terrainAt(map, p.tile), `${c.id} ${p.tile}`).not.toBe(p.becomes)
        }
      }
    })
  }
})

describe('Conquest 12', () => {
  const pots = CONQUEST_12.objects.filter((o) => o.type === 'pot')

  it('has the 69 pots from the guide: 28 medicine, 41 poison', () => {
    expect(pots).toHaveLength(69)
    expect(pots.filter((p) => p.pot === 'medicine')).toHaveLength(28)
    expect(pots.filter((p) => p.pot === 'poison')).toHaveLength(41)
  })

  it('puts the Dragon Vein next to Saizo & Kagero on Normal/Hard and two tiles north on Lunatic', () => {
    const pair = CONQUEST_12.units.find((u) => u.name.startsWith('Saizo'))!.tile
    const vein = CONQUEST_12.changes[0].tile
    for (const d of ['Normal', 'Hard'] as const) {
      const [x, y] = resolveTile(vein, d)
      expect(Math.abs(x - pair[0]) + Math.abs(y - pair[1])).toBe(1)
    }
    expect(resolveTile(vein, 'Lunatic')).toEqual([pair[0], pair[1] + 2])
  })

  it("has the wiki's enemy totals on each difficulty (31 / 38 / 42, counting each pair as two)", () => {
    const expected: Record<string, number> = { Normal: 31, Hard: 38, Lunatic: 42 }
    for (const d of DIFFICULTIES) {
      const foes = CONQUEST_12.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d)))
      expect(foes.reduce((n, u) => n + (u.paired ? 2 : 1), 0), d).toBe(expected[d])
      const tiles = foes.map((u) => tileKey(u.tile))
      expect(new Set(tiles).size, `${d}: two units on one tile`).toBe(tiles.length)
    }
  })

  it('has no unit standing on a pot', () => {
    const potTiles = new Set(pots.map((p) => tileKey(p.tile)))
    for (const u of CONQUEST_12.units) expect(potTiles.has(tileKey(u.tile)), `${u.name} at ${u.tile}`).toBe(false)
  })

  it('deploys Corrin + 12', () => {
    expect(CONQUEST_12.starts).toHaveLength(13)
  })
})

describe("enemy totals match the wiki's enemy tables (pairs count as two)", () => {
  const expected: Record<string, [number, number, number]> = {
    'fe14-1': [1, 1, 1],
    'fe14-2': [4, 6, 6],
    'fe14-3': [11, 11, 13],
    'fe14-4': [12, 14, 14],
    'fe14-5': [7, 9, 10],
    'fe14c-6': [5, 5, 5],
    'fe14c-7': [13, 16, 18],
    'fe14c-8': [12, 14, 14],
    'fe14c-9': [17, 19, 23],
    'fe14c-10': [19, 23, 27],
    'fe14c-11': [27, 31, 38],
    'fe14c-12': [31, 38, 42],
    'fe14c-13': [22, 26, 36],
    'fe14c-14': [25, 30, 35],
    'fe14c-15': [25, 25, 29],
    'fe14c-16': [25, 34, 41],
    'fe14c-17': [32, 39, 41],
    'fe14c-18': [27, 34, 39],
    'fe14c-19': [26, 28, 37],
    'fe14c-20': [30, 37, 45],
    'fe14c-21': [27, 31, 36],
    'fe14c-22': [23, 30, 33],
    'fe14c-23': [30, 42, 45],
    'fe14c-24': [25, 30, 40],
    'fe14c-25': [28, 38, 49],
    'fe14c-26': [35, 48, 50],
    'fe14c-27': [17, 21, 22],
    'fe14c-endgame': [22, 26, 37],
    // Birthright, Revelation, the paralogues and the DLC: the wiki's chapter pages (2026-10-18). The DLC
    // grind maps have no fixed army (every enemy there is a spawn), so they aren't listed.
    'fe14b-6': [5, 6, 7],
    'fe14b-7': [11, 19, 27],
    'fe14b-8': [11, 21, 26],
    'fe14b-9': [17, 25, 37],
    'fe14b-10': [17, 28, 33],
    'fe14b-11': [17, 19, 19],
    'fe14b-12': [27, 34, 37],
    'fe14b-13': [24, 36, 38],
    'fe14b-14': [16, 33, 37],
    'fe14b-15': [15, 22, 25],
    'fe14b-16': [20, 40, 44],
    'fe14b-17': [1, 1, 1],
    'fe14b-18': [3, 3, 3],
    'fe14b-19': [22, 31, 31],
    'fe14b-20': [17, 23, 23],
    'fe14b-21': [27, 42, 42],
    'fe14b-22': [23, 28, 45],
    'fe14b-23': [25, 26, 42],
    'fe14b-24': [21, 34, 34],
    'fe14b-25': [28, 31, 48],
    'fe14b-26': [27, 33, 46],
    'fe14b-27': [26, 32, 49],
    'fe14b-endgame': [26, 30, 50],
    'fe14r-6': [14, 16, 18],
    'fe14r-7': [4, 4, 4],
    'fe14r-8': [19, 19, 19],
    'fe14r-9': [26, 26, 26],
    'fe14r-10': [4, 4, 4],
    'fe14r-11': [26, 26, 26],
    'fe14r-12': [27, 27, 27],
    'fe14r-13': [38, 40, 44],
    'fe14r-14': [35, 35, 35],
    'fe14r-15': [30, 30, 30],
    'fe14r-16': [31, 33, 35],
    'fe14r-17': [23, 23, 23],
    'fe14r-18': [30, 32, 34],
    'fe14r-19': [45, 45, 45],
    'fe14r-20': [42, 42, 42],
    'fe14r-21': [29, 32, 35],
    'fe14r-22': [29, 31, 34],
    'fe14r-23': [38, 38, 38],
    'fe14r-24': [1, 1, 1], // wiki 16/18/18: it counts the enemies behind the doors, which arrive when each opens
    'fe14r-25': [39, 39, 39],
    'fe14r-26': [34, 37, 41],
    'fe14r-27': [29, 29, 29],
    'fe14r-endgame': [2, 2, 2], // wiki 10: the other 8 are placed when the battle starts
    'fe14-x1': [19, 19, 19],
    'fe14-x2': [27, 27, 27],
    'fe14-x3': [20, 20, 20],
    'fe14-x4': [19, 19, 19],
    'fe14-x5': [27, 27, 27],
    'fe14-x6': [30, 30, 30],
    'fe14-x7': [33, 33, 33],
    'fe14-x8': [29, 29, 29],
    'fe14-x9': [32, 32, 35],
    'fe14-x10': [29, 29, 29],
    'fe14-x11': [29, 29, 29],
    'fe14-x12': [35, 35, 36],
    'fe14-x13': [27, 27, 28],
    'fe14-x14': [21, 21, 21],
    'fe14-x15': [25, 32, 35],
    'fe14-x16': [22, 31, 37],
    'fe14-x17': [20, 24, 32],
    'fe14-x18': [19, 23, 29],
    'fe14-x19': [31, 39, 46],
    'fe14-x20': [18, 24, 33],
    'fe14-x21': [17, 23, 29],
    'fe14-x22': [26, 33, 41],
    'fe14-dlc-40': [12, 12, 12],
    'fe14-dlc-6f': [18, 18, 18], // wiki 22: it also counts two groups the game places on turn 1 as reinforcements
    'fe14-dlc-70': [30, 30, 30],
    'fe14-dlc-72': [39, 44, 44],
    'fe14-dlc-74': [14, 14, 14],
    'fe14-dlc-76': [16, 21, 21],
    'fe14-dlc-79': [16, 16, 16],
    'fe14-dlc-7f': [30, 32, 32],
    'fe14-dlc-86': [39, 44, 44],
    'fe14-dlc-88': [16, 17, 17],
    'fe14-dlc-8a': [33, 33, 33],
    'fe14-dlc-8c': [20, 20, 20],
    'fe14-dlc-8e': [25, 25, 25],
    'fe14-hero1': [7, 7, 7],
    'fe14-hero2': [8, 8, 8],
    'fe14-hero3': [6, 6, 6],
    'fe14-hero4': [4, 4, 4],
  }
  // Challenge battles have no fixed army either: the game picks each battle's foes (they have their own tests).
  for (const map of ALL_MAPS.filter((m) => !GAME_CHAPTERS[m.id]?.grind && m.route !== 'Challenge')) {
    it(map.id, () => {
      expect(expected, `no expected totals for ${map.id}`).toHaveProperty(map.id)
      DIFFICULTIES.forEach((d, i) => {
        // Foes hidden under Revelation 10's snow aren't on the map until it's dug: the wiki counts them as reinforcements.
        const foes = map.units.filter((u) => u.type !== 'ally' && !u.buried && (!u.difficulties || u.difficulties.includes(d)))
        expect(foes.reduce((n, u) => n + (u.paired ? 2 : 1), 0), d).toBe(expected[map.id][i])
        const tiles = foes.map((u) => tileKey(u.tile))
        // Birthright 8's files put a third Lunatic foe on the pair at (7, 13); the game moves it to the
        // nearest free tile.
        const shared = map.id === 'fe14b-8' && d === 'Lunatic' ? 1 : 0
        expect(new Set(tiles).size, `${d}: two units on one tile`).toBe(tiles.length - shared)
      })
    })
  }
})

describe('shared chapters', () => {
  it('Conquest 6 (the Prologue battlefield): the vein dries exactly the river', () => {
    const patch = CONQUEST_6.changes[0].patch!
    expect(patch.every((p) => terrainAt(CONQUEST_6, p.tile) === 'tf')).toBe(true)
    expect(terrainAt(applyChanges(CONQUEST_6, new Set(['vein'])), [10, 10])).toBe('ta')
    expect(CONQUEST_6.grid.flatMap(rowCodes).filter((c) => c === 'tf')).toHaveLength(patch.length)
  })

  it('Chapter 4: seven veins, each melting one whole snow mountain, together melting all the snow', () => {
    expect(CHAPTER_4.changes).toHaveLength(7)
    const melted = applyChanges(CHAPTER_4, new Set(CHAPTER_4.changes.map((c) => c.id)))
    expect(melted.grid.flatMap(rowCodes)).not.toContain('bm')
    for (const c of CHAPTER_4.changes) expect(c.patch!.every((p) => terrainAt(CHAPTER_4, p.tile) === 'bm')).toBe(true)
  })

  it('Chapter 1: its healing tile heals 50%, not the usual 20%', () => {
    const healed = applyChanges(CHAPTER_1, new Set(['vein']))
    expect(terrainInfo(healed, terrainAt(healed, [7, 7])).heal).toBe(50)
  })
})

describe('tilesInRadius', () => {
  it('covers a 2-tile diamond (13 tiles) in open space and clips at the map edge', () => {
    expect(tilesInRadius(CONQUEST_12, [10, 20], 2)).toHaveLength(13)
    expect(tilesInRadius(CONQUEST_12, [1, 1], 2)).toHaveLength(6)
  })
})

describe('random spawns', () => {
  it('marks only the grinding maps as spawning at random; every other map has fixed reinforcements', () => {
    const random = ALL_MAPS.filter((m) => m.randomSpawns).map((m) => m.title)
    expect(random.sort()).toEqual(['Beach Brawl', 'Boo Camp', 'Ghostly Gold', 'Museum Melee', 'Royal Royale'])
    expect(ALL_MAPS.filter((m) => m.randomSpawns).every((m) => GAME_CHAPTERS[m.id]?.grind)).toBe(true)
  })
})

describe('terrain codes', () => {
  it('draws every tile of every game with a known two-character code', () => {
    for (const m of [...ALL_MAPS, ...FE9_MAPS, ...FE10_MAPS]) {
      for (const row of m.grid) {
        expect(row.length, m.id).toBe(2 * m.width)
        for (const code of rowCodes(row)) expect(TERRAIN_CODES, `${m.id} '${code}'`).toHaveProperty(code)
      }
    }
  })
})

describe('pillars', () => {
  it('shows the pillar icon only where a unit can stand: a pillar no one can enter is drawn as a wall', () => {
    const hasPillar = (m: ChapterMap) => m.grid.some((row) => rowCodes(row).includes('bh'))
    const withPillars = [...ALL_MAPS, ...FE9_MAPS, ...FE10_MAPS].filter(hasPillar)
    expect(withPillars.length).toBeGreaterThan(0)
    for (const m of withPillars) expect(Object.values(terrainInfo(m, 'bh').move).some((c) => c !== null), m.id).toBe(true)
    expect([...FE9_MAPS, ...FE10_MAPS].some(hasPillar)).toBe(false)
  })
})

describe('green units', () => {
  // The person icon is kept for named green units, to draw the eye; generic ones are a plain green dot.
  const greens = (maps: typeof ALL_MAPS) => maps.flatMap((m) => m.units.filter((u) => u.type === 'ally'))
  const isGeneric = (maps: typeof ALL_MAPS, name: string) => greens(maps).filter((u) => u.name === name).map((u) => Boolean(u.generic))

  it('Fates: villagers and other armies are generic; characters, even in their own paralogue, are named', () => {
    expect(new Set(isGeneric(ALL_MAPS, 'Villager'))).toEqual(new Set([true]))
    expect(new Set(isGeneric(ALL_MAPS, 'Sophie'))).toEqual(new Set([false]))
    expect(new Set(isGeneric(ALL_MAPS, 'Ryoma'))).toEqual(new Set([false]))
  })

  it("Tellius: horses, armies and townsfolk are generic; Aimee, Kurth and the named laguz aren't", () => {
    for (const name of ['Horse', 'Gallia', 'Crimea', 'Prisoner']) expect(new Set(isGeneric(FE10_MAPS, name)), name).toEqual(new Set([true]))
    for (const name of ['Aimee', 'Kurth', 'Ranulf', 'Tauroneo']) expect(new Set(isGeneric(FE10_MAPS, name)), name).toEqual(new Set([false]))
    expect(new Set(isGeneric(FE9_MAPS, 'Soldier'))).toEqual(new Set([true]))
    expect(new Set(isGeneric(FE9_MAPS, 'Tibarn'))).toEqual(new Set([false]))
  })
})

describe('terrain names', () => {
  it("are all English: a terrain the text has no line for gets one (Birthright 17's lake, a fort in Witches' Trial)", () => {
    for (const m of ALL_MAPS)
      for (const code of new Set(m.grid.flatMap(rowCodes))) expect(terrainInfo(m, code).name, `${m.id} ${code}`).not.toMatch(/[぀-ヿ一-鿿]/)
  })
})

describe("Revelation 10's snow", () => {
  const izumo = byId('fe14r-10')
  const snow = izumo.changes.find((c) => c.dig)!
  const covered = new Set((snow.patch ?? []).map((p) => tileKey(p.tile)))

  it('is ice to dig through, its own terrain, cleared to what lies under it', () => {
    expect(izumo.grid.flatMap(rowCodes).filter((c) => c === 'wr')).toHaveLength(covered.size)
    expect(new Set((snow.patch ?? []).map((p) => p.becomes))).toEqual(new Set(['ta', 'wa']))
  })

  it('hides its foes until dug: on the map from the start, under the snow, none of them a reinforcement', () => {
    const buried = izumo.units.filter((u) => u.buried)
    expect(buried.length).toBeGreaterThan(20)
    for (const u of buried) expect(covered.has(tileKey(u.tile)), u.name).toBe(true)
    expect((izumo.reinforcements ?? []).some((g) => g.units.every((u) => covered.has(tileKey(u.tile))))).toBe(false)
    expect(atStart(izumo).units.some((u) => u.buried)).toBe(false)
  })

  it('digs the tile and the four beside it, where the snow covers them', () => {
    expect(digAt(snow, [6, 15]).sort()).toEqual(['5,15', '6,14', '6,15', '6,16', '7,15'].filter((k) => covered.has(k)).sort())
  })
})

describe("the Rainbow Sage's stairs", () => {
  it('pair up every staircase on its three maps, each end on a stair tile (checked in the game)', () => {
    for (const id of ['fe14b-19', 'fe14c-11', 'fe14r-15']) {
      const m = byId(id)
      const stairs = m.grid.flatMap((row, r) => rowCodes(row).map((c, x) => [c, `${x + 1},${m.height - r}`])).filter(([c]) => c === 'tc')
      expect(new Set(m.links!.flat().map(tileKey)), id).toEqual(new Set(stairs.map(([, k]) => k)))
      expect(m.unconfirmed ?? [], id).toEqual([])
    }
  })
})

describe('named green units say what they do', () => {
  const green = (id: string, name: string) => byId(id).units.find((u) => u.type === 'ally' && u.name === name)!
  it('a talk that recruits, a join at the end, or that they stay green (read from the chapter scripts)', () => {
    expect(green('fe14b-8', 'Hinoka').talk).toBe('Recruit: talk with Corrin')
    expect(green('fe14b-8', 'Azama').note).toBe('Joins your army when Corrin talks to Hinoka, or at the end of the chapter')
    expect(green('fe14r-11', 'Saizo').talk).toBe('Recruit: talk with Corrin')
    expect(green('fe14-x2', 'Kana').note).toBe('Joins your army at the end of the chapter')
    expect(green('fe14c-18', 'Ryoma').note).toBe("Stays a green unit: doesn't join your army here")
    for (const m of ALL_MAPS.filter((x) => x.route !== 'Challenge' && !x.randomSpawns))
      for (const u of m.units.filter((x) => x.type === 'ally' && !x.generic)) expect(u.talk ?? u.note, `${m.id} ${u.name}`).toBeTruthy()
  })
})

describe('reinforcement arrivals read from the chapter scripts', () => {
  const group = (id: string, label: string) => byId(id).reinforcements!.find((g) => g.label === label)!
  const labels = (id: string) => byId(id).reinforcements!.map((g) => g.label)

  it("Anankos's summons go by his stage: his claws, his head, his core", () => {
    expect(group('fe14r-endgame', 'Group 1-1').when).toBe('Turn 1, player phase; summoned again while either claw stands')
    expect(group('fe14r-endgame', 'Group 2-8').when).toBe("Summoned once both claws fall, while Anankos's head stands")
    expect(group('fe14r-endgame', 'Group 3-4').when).toBe("Summoned once Anankos's head falls")
    expect(group('fe14r-endgame', 'Group A').when).toBe('As soon as both claws are defeated')
    expect(group('fe14r-endgame', 'Group B').when).toBe("As soon as Anankos's head is defeated")
    // 'Reinforce_01' to '_03' are in the file but nothing places them (only their '_1' to '_8' are).
    expect(labels('fe14r-endgame')).not.toContain('Group 1')
    expect(group('fe14-dlc-8e', 'Group 1-1').when).toBe('Summoned from turn 3, all through the battle')
    expect(group('fe14-dlc-8e', 'Group 6-3').when).toBe("Summoned once Anankos's head falls")
    // The notes that explain the summons give arrivals away, so the spoiler block drops them.
    for (const id of ['fe14r-endgame', 'fe14-dlc-8e']) {
      expect(byId(id).notes.length, id).toBeGreaterThan(0)
      expect(atStart(byId(id)).notes, id).toEqual([])
    }
  })

  it("Conquest's Endgame: the second set comes in a 48-turn cycle that never reaches half its groups", () => {
    expect(group('fe14c-endgame', 'Group 1').when).toBe('Enemy phase, every 12th turn from turn 4 (4, 16, 28…)')
    expect(group('fe14c-endgame', 'Group 46').when).toBe('Enemy phase, every 48th turn from turn 11 (11, 59…)')
    for (const n of [32, 34, 36, 41, 43, 45, 52, 54, 56, 61, 63, 65]) expect(labels('fe14c-endgame')).not.toContain(`Group ${n}`)
  })

  it('a group several handlers place says every turn, and only the difficulties the script brings it on', () => {
    const g = group('fe14b-10', 'Group 2')
    expect(g.when).toEqual({ Lunatic: 'Turns 6, 9, enemy phase' })
    expect(g.units.every((u) => u.difficulties?.join() === 'Lunatic')).toBe(true)
    for (const label of ['Group 4-2-1', 'Group 5-2-2', 'Group 6-2-1'])
      expect(group('fe14r-24', label).units.every((u) => !u.difficulties?.includes('Normal'))).toBe(true)
  })

  it("the doors, villages and Dragon Veins that bring groups in (Revelation 24's doors place theirs after opcode 0x4e)", () => {
    expect(group('fe14r-24', 'Group 1').when).toBe('When the door at (18, 8) or (21, 8) is opened')
    expect(group('fe14r-24', 'Group 3-1').when).toBe('When the door at (16, 27) is opened')
    expect(group('fe14r-13', 'Group 1-1').when).toBe(
      'Turn 15, enemy phase; turns 1–12, enemy phase, once the Dragon Vein at (4, 25) or (17, 25) is used',
    )
    expect(group('fe14r-18', 'Group 3').when).toBe('Turns 6, 12, 18, 24, 30, enemy phase, once the Dragon Vein at (4, 6) is used')
  })

  it("no arrival is put down to a unit merely moving: a check run after every action says when by its condition", () => {
    for (const m of ALL_MAPS)
      for (const g of m.reinforcements ?? [])
        for (const w of typeof g.when === 'string' ? [g.when] : Object.values(g.when ?? {}))
          expect(w, `${m.id} ${g.label}`).not.toMatch(/ moves\b/)
    expect(group('fe14-dlc-8c', 'Group K').when).toBe('As soon as Arete is defeated')
    expect(group('fe14-dlc-8c', 'Group H').units[0].name).toBe('Faceless')
  })
})
