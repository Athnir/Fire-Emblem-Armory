import { describe, expect, it } from 'vitest'
import { FE17_ITEM_SOURCES } from '../../data/fe17/fe17ItemSources'
import { FE17_LISTED } from '../../data/fe17/fe17Listed'
import { FE17_MAPS } from '../../data/fe17/fe17Maps'
import { FE17_MAP_SET, FE17_STORY } from '../../data/fe17/fe17MapSet'
import { FE17_REFINE, FE17_SMITHY_OPENS } from '../../data/fe17/fe17Refine'
import { FE17_SUPPORTS } from '../../data/fe17/fe17Supports'
import { FE17_MOVE_CLASSES, FE17_TERRAIN } from '../../data/fe17/fe17Terrain'
import type { ChapterMap, Difficulty, MapUnit } from '../../data/maps/types'
import { rowCodes, sameTile } from '../maps'
import { trueHit } from '../trueHit'

const map = (id: string) => FE17_MAPS.find((m) => m.id === id)!
const on = (u: MapUnit, d: Difficulty) => !u.difficulties || u.difficulties.includes(d)
const DIFFS: Difficulty[] = ['Normal', 'Hard', 'Maddening']
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && on(u, d))
const totals = (m: ChapterMap) => DIFFS.map((d) => foes(m, d).length)
const arriving = (m: ChapterMap) =>
  DIFFS.map((d) => (m.reinforcements ?? []).reduce((n, g) => n + g.units.filter((u) => on(u, d)).length, 0))
const whenOn = (g: { when?: string | Partial<Record<Difficulty, string>> }, d: Difficulty) =>
  typeof g.when === 'string' ? g.when : g.when?.[d]
/** How many times a group comes, read from its time: 'Turns 6, 12 and 13, player phase' 3, 'Every turn from 8 to 10' 3, once for a
 * time set off by an event; null for one that goes on. */
const comes = (when: string): number | null => {
  if (when.includes('; or ')) return null
  const span = (a: string, b: string, step = 1) => Math.floor((Number(b) - Number(a)) / step) + 1
  const steps: Record<string, number> = { turn: 1, 'other turn': 2, 'third turn': 3, 'fourth turn': 4 }
  let m = when.match(/^Turns? ([\d, and]+?)(?:, then every (turn|other turn|third turn|fourth turn) from (\d+) to (\d+))?, (?:player|enemy|ally|end)/)
  if (m) return m[1].match(/\d+/g)!.length + (m[2] ? span(m[3], m[4], steps[m[2]]) : 0)
  m = when.match(/^Every (turn|other turn|third turn|fourth turn) from (\d+) to (\d+), /)
  if (m) return span(m[2], m[3], steps[m[1]])
  if (/^When |^At the (start|end) of the \w+ (player|enemy|ally) phase (on an \w+ turn )?after /.test(when)) return 1
  return null
}
/** Every foe the groups bring, each group as many times as it comes. */
const arrivingAll = (m: ChapterMap) =>
  DIFFS.map((d) =>
    (m.reinforcements ?? []).reduce((n, g) => {
      const w = whenOn(g, d)
      return w ? n + g.units.filter((u) => on(u, d)).length * (comes(w) ?? NaN) : n
    }, 0),
  )

describe("Engage's story maps", () => {
  it('has the Prologue and Chapters 1 to 26, each grid its own size', () => {
    expect(FE17_MAPS.filter((m) => m.route === 'Story').map((m) => m.id)).toEqual(
      Array.from({ length: 27 }, (_, k) => `fe17-m${String(k).padStart(3, '0')}`),
    )
    for (const m of FE17_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The grid's own window (its MapTerrain object): Chapter 4 is 23 by 20.
    expect([map('fe17-m004').width, map('fe17-m004').height]).toEqual([23, 20])
    expect(FE17_STORY.maps.map((m) => FE17_STORY.short(m)).slice(0, 3)).toEqual(['Prologue', 'Ch.1', 'Ch.2'])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE17_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE17_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const c of FE17_MOVE_CLASSES) expect(info!.move[c], `${code} ${c}`).not.toBeUndefined()
    }
    // Woods and thickets: Avo +30, two moves on foot or horseback, one for fliers and dragons (terrain.xml).
    expect(FE17_TERRAIN.ba).toMatchObject({ avo: 30, move: { Infantry: 2, Cavalry: 2, Fliers: 1, Dragons: 1 } })
  })

  it("matches Fire Emblem Wiki's starting foes on every difficulty", () => {
    // [Normal, Hard, Maddening], each chapter page's enemy count (its Normal/Hard tab where it gives one for both).
    const wiki: Record<string, number[]> = {
      'fe17-m000': [1, 1, 1], 'fe17-m001': [3, 4, 5], 'fe17-m002': [3, 3, 3], 'fe17-m003': [12, 14, 14], 'fe17-m004': [14, 17, 18],
      'fe17-m005': [25, 25, 27], 'fe17-m006': [17, 19, 27], 'fe17-m007': [21, 21, 30], 'fe17-m008': [17, 19, 21],
      'fe17-m009': [27, 29, 30], 'fe17-m010': [21, 23, 27], 'fe17-m011': [22, 23, 28], 'fe17-m012': [12, 13, 13],
      'fe17-m013': [35, 36, 42], 'fe17-m014': [35, 35, 43], 'fe17-m015': [30, 35, 38], 'fe17-m016': [32, 34, 34],
      'fe17-m017': [35, 41, 45], 'fe17-m018': [32, 36, 41], 'fe17-m019': [28, 28, 36], 'fe17-m020': [28, 31, 39],
      'fe17-m021': [28, 28, 34], 'fe17-m022': [27, 32, 41], 'fe17-m023': [31, 36, 46], 'fe17-m024': [25, 25, 36],
      'fe17-m025': [48, 49, 53], 'fe17-m026': [11, 11, 11],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    // Chapter 4's reinforcements as the wiki counts them: the Ruffian on turn 2, two Corrupted on turn 4 and two on turn 5, and three
    // more on turn 7 on Maddening.
    expect(arriving(map('fe17-m004'))).toEqual([5, 5, 8])
  })

  it("comes on every turn its script places it, matching the wiki's reinforcement totals", () => {
    // Each group as many times as it comes (Chapter 25's waves come on every turn of a span; the wiki counts each).
    const wiki: Record<string, number[]> = {
      'fe17-m002': [6, 6, 6], 'fe17-m008': [4, 10, 12], 'fe17-m012': [11, 13, 13], 'fe17-m024': [26, 30, 33],
      'fe17-m025': [28, 83, 123], 'fe17-s010': [18, 18, 27], 'fe17-s011': [36, 104, 112], 'fe17-e002': [10, 26, 26],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(arrivingAll(map(id)), id).toEqual(counts)
    // Chapter 22's last wave comes every third turn from turn 13 until Alear has the rings back from all eleven emblems.
    expect(whenOn(map('fe17-m022').reinforcements!.at(-1)!, 'Normal')).toMatch(
      /^Every third turn from 13, player phase, until your units have talked to Sigurd, .* and Eirika$/,
    )
  })

  it('says what sets each group off: a defeat, a fight, a unit reaching a tile, an AI starting', () => {
    const groups = (id: string) => map(id).reinforcements!.map((g) => whenOn(g, 'Normal'))
    // Chapter 21: a Corrupted Wyrm after each of Zephia and Griss falls; Zephia's and Veyle's own calls once they start to move.
    expect(groups('fe17-m021')).toContain('At the start of the next player phase after Zephia is defeated')
    expect(groups('fe17-m021')).toContain('At the start of the next player phase after Veyle starts to move')
    // Chapter 9: Kagetsu's and Zelkov's men once each reaches his fort.
    expect(groups('fe17-m009')).toEqual([
      'At the start of the next player phase after Kagetsu reaches the fort at (16, 17)',
      'At the start of the next player phase after Zelkov reaches the fort at (16, 3)',
    ])
    // Chapter 5's countdown starts with a fight with the fourth platoon or the wall by the throne broken.
    expect(groups('fe17-m005')[0]).toMatch(/^At the start of the second player phase after one of your units fights .*, or the rickety wall at \(7, 21\) is broken$/)
    // Nothing is left as "After an event in the chapter".
    for (const m of FE17_MAPS)
      for (const g of [...(m.reinforcements ?? []), ...(m.joiners ?? [])])
        for (const d of DIFFS) expect(whenOn(g, d) ?? '', m.id).not.toMatch(/an event in the chapter/)
  })

  it('starts with its doors, breakable walls and roofs in place, each previewed open', () => {
    const at = (m: ChapterMap, [x, y]: [number, number]) => rowCodes(m.grid[m.height - y])[x - 1]
    // Chapter 5: a rickety wall (20 HP) over the stairs by the throne, a door (30 HP) on the treasury (the terrain's layers).
    const m5 = map('fe17-m005')
    expect(at(m5, [7, 21])).toBe('wz')
    expect(at(m5, [13, 12])).toBe('ob')
    const wall = m5.changes.find((c) => sameTile(c.tile.default!, [7, 21]))!
    expect(wall.effect).toBe('A rickety wall with 20 HP: attack it down and it opens.')
    expect(new Set(wall.patch!.map((p) => p.becomes))).toEqual(new Set(['tc']))
    expect(m5.changes.find((c) => sameTile(c.tile.default!, [13, 12]))!.effect).toMatch(/^A door with 30 HP: .*a Thief opens it/)
    // Chapter 15: rooms closed under roofs until their doors open, miasma inside.
    const m15 = map('fe17-m015')
    const door = m15.changes.find((c) => sameTile(c.tile.default!, [8, 10]))!
    expect(door.effect).toMatch(/and the room behind it opens\.$/)
    expect(door.patch!.length).toBeGreaterThan(40)
    expect(door.patch!.some((p) => at(m15, p.tile) === 'ws' && p.becomes === 'eg')).toBe(true)
  })

  it('previews what the scripts change on the map, and when', () => {
    const shifts = (id: string) => map(id).changes.filter((c) => c.trigger === 'event')
    // Chapter 16's tide, in on turn 1 and every fourth turn from 4, out every fourth turn from 2.
    expect(shifts('fe17-m016')[0].effect).toBe(
      'Turn 1, then every fourth turn from 4, player phase: 287 tiles become shoal; every fourth turn from 2, player phase, they become beach again.',
    )
    // Chapter 22's ring pedestals clear as each set of emblems appears; Fell Xenologue 6's later islands sink on Hard and Maddening only.
    expect(shifts('fe17-m022')).toHaveLength(4)
    expect(shifts('fe17-e006').find((c) => c.effect.startsWith('Turn 8'))?.difficulties).toEqual(['Hard', 'Maddening'])
  })

  it('lays the maps\' lasting effects over their tiles, their numbers added to the tile\'s', () => {
    const codes = (id: string) => map(id).grid.flatMap(rowCodes)
    // Chapter 19's miasma, Chapter 17's flames, Chapter 24's fog (the terrain's overlaps).
    expect(codes('fe17-m019').filter((c) => c === 'eg').length).toBeGreaterThan(90)
    expect(codes('fe17-m017').filter((c) => c === 'ef').length).toBeGreaterThan(70)
    expect(codes('fe17-m024').filter((c) => c === 'ea').length).toBe(98)
    // Fog over woods: Avo 30 + 30 (App.BattleDetail.CalcAvoid adds the overlap's to the tile's); flames hurt by 10 HP.
    expect(FE17_TERRAIN.eb).toMatchObject({ avo: 60, move: { Infantry: 3, Fliers: 1 } })
    expect(FE17_TERRAIN.ef?.note).toBe('Takes 10 HP at the start of each turn (not fliers).')
    expect(FE17_TERRAIN.eg?.note).toBe('Def -20 for your units, +20 for foes.')
    // Terrain heals by HP: the heal tile's 10 is 10 HP.
    expect(FE17_TERRAIN.ha?.heal).toBe(10)
    expect(FE17_MAP_SET.healInHp).toBe(true)
  })

  it('places what the openings bring: Chapter 10 opens with nineteen of its foes', () => {
    expect(totals(map('fe17-m010'))[0]).toBe(21)
  })
})

describe("Engage's paralogues", () => {
  it('lists the fifteen, each opening before the chapter after the one its world map spot names', () => {
    const side = FE17_MAPS.filter((m) => m.route === 'Paralogue' && m.id.startsWith('fe17-s'))
    expect(side.map((m) => m.id)).toEqual(Array.from({ length: 15 }, (_, k) => `fe17-s${String(k + 1).padStart(3, '0')}`))
    // Paralogue 1, Budding Talent, opens once Chapter 5 is cleared (chapter.xml): played before Chapter 6.
    expect(FE17_STORY.opensAt!('fe17-s001')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m006'))
    expect(map('fe17-s001').title).toBe('Budding Talent')
  })

  it("matches Fire Emblem Wiki's starting foes (The Radiant Hero's page gives no count)", () => {
    const wiki: Record<string, number[]> = {
      'fe17-s001': [13, 15, 16], 'fe17-s002': [20, 21, 22], 'fe17-s003': [9, 9, 9], 'fe17-s004': [22, 22, 33],
      'fe17-s006': [27, 27, 29], 'fe17-s007': [18, 18, 22], 'fe17-s008': [31, 38, 47], 'fe17-s009': [31, 31, 36],
      'fe17-s010': [32, 37, 38], 'fe17-s011': [18, 20, 30], 'fe17-s012': [26, 34, 40], 'fe17-s013': [6, 7, 7],
      'fe17-s014': [30, 34, 39], 'fe17-s015': [15, 15, 19],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    // Where the groups come once, their totals match too: The Crux of Fate's 4, 6 and 6, The Connector's 28, 28 and 37.
    expect(arriving(map('fe17-s007'))).toEqual([4, 6, 6])
    expect(arriving(map('fe17-s015'))).toEqual([28, 28, 37])
  })
})

describe("Engage's Divine Paralogues", () => {
  it("shows the lowest army level band, matching Fire Emblem Wiki's starting foes", () => {
    const wiki: Record<string, number[]> = {
      'fe17-g001': [34, 43, 38], 'fe17-g002': [31, 42, 36], 'fe17-g003': [24, 32, 27], 'fe17-g004': [29, 42, 37],
      'fe17-g005': [43, 57, 46], 'fe17-g006': [16, 22, 22],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    // The Ancestor's boss is Tiki, a person of her own (her asset is AID_Person_チキ, not a generic soldier's).
    expect(map('fe17-g001').units.find((u) => u.type === 'boss')?.name).toBe('Tiki')
    // Each opens once Chapter 6 is cleared (the first, Fire Emblem Wiki; the rest after it).
    expect(FE17_STORY.opensAt!('fe17-g003')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m007'))
  })
})

describe("Engage's Fell Xenologue", () => {
  it('is a story of its own, its six battles its chapters, opening with the Ancient Well (Chapter 6 cleared)', () => {
    expect(FE17_MAP_SET.routes!.list).toEqual(['Main story', 'Fell Xenologue'])
    expect(FE17_MAP_SET.routes!.maps('Fell Xenologue').map((m) => m.title)).toEqual([
      'Dragons from Afar', 'Seeds of Unrest', 'Path to War', 'Clash of Queens', 'The Fell Heir', 'Seven Bracelets',
    ])
    expect(FE17_MAP_SET.routes!.side('Fell Xenologue')).toEqual([])
    expect(FE17_STORY.opensAt!('fe17-e001')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m007'))
  })

  it("matches Fire Emblem Wiki's starting foes", () => {
    const wiki: Record<string, number[]> = {
      'fe17-e001': [11, 18, 25], 'fe17-e002': [23, 35, 43], 'fe17-e003': [23, 34, 53], 'fe17-e004': [18, 23, 24],
      'fe17-e005': [32, 39, 52], 'fe17-e006': [44, 55, 62],
    }
    for (const [id, counts] of Object.entries(wiki)) expect(totals(map(id)), id).toEqual(counts)
    expect(arriving(map('fe17-e001'))).toEqual([2, 5, 6])
  })
})

describe("Engage's skirmishes", () => {
  it("gives each location with foes its skirmish, in a list of its own, on the location's terrain", () => {
    const main = FE17_MAP_SET.routes!.fourth!.maps('Main story')
    expect(FE17_MAP_SET.routes!.fourth!.label).toBe('Skirmishes')
    expect(main.length).toBe(41)
    expect(FE17_MAP_SET.routes!.fourth!.maps('Fell Xenologue').map((m) => m.title)[0]).toBe('Bracelet Altar')
    const florra = map('fe17-m004-sk')
    expect(florra.title).toBe('Florra Mill Town')
    expect([florra.width, florra.height]).toEqual([map('fe17-m004').width, map('fe17-m004').height])
    // Twenty foe slots the game fills, one of them the leader; ten deployment tiles (dispos m004e).
    expect(totals(florra)).toEqual([20, 20, 20])
    expect(florra.units.filter((u) => u.name === 'Random foe (leader)')).toHaveLength(1)
    expect(florra.starts).toHaveLength(10)
    // It appears once Chapter 4 is cleared.
    expect(FE17_STORY.opensAt!('fe17-m004-sk')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m005'))
  })
})

describe("Engage's Tempest Trials", () => {
  it('gives each trial map a map per line-up, the six trials first and the shared final stage last', () => {
    const trials = FE17_MAP_SET.routes!.third!.maps('Main story')
    expect(FE17_MAP_SET.routes!.third!.label).toBe('Tempest Trials')
    expect(trials).toHaveLength(56)
    expect(trials[0].title).toBe('Verdant Plain, map 1, line-up 1')
    expect(trials.at(-1)!.title).toBe('Final stage, map 6, line-up 1')
    expect(FE17_MAP_SET.routes!.third!.maps('Fell Xenologue')).toEqual([])
    // The first four trials open once Chapter 11 is cleared (chapter.xml's やり込み UnlockCid), Vicious Volcano with Chapter 23.
    expect(FE17_STORY.opensAt!('fe17-c001-1-1')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m012'))
    expect(FE17_STORY.opensAt!('fe17-c006-1-1')).toBe(FE17_STORY.maps.findIndex((m) => m.id === 'fe17-m024'))
  })
})

describe("Engage's weapons", () => {
  it('sells from the chapter after the one whose clearing opens the armory (Chapter 4)', () => {
    const iron = FE17_ITEM_SOURCES['Iron Sword'].filter((s) => s.kind === 'shop')
    expect(iron[0].mapId).toBe('fe17-m005')
  })

  it('reads effectiveness and its multiplier from the skill table', () => {
    expect(FE17_LISTED.find((w) => w.name === 'Armorslayer')?.effective).toEqual(['armour'])
    expect(FE17_LISTED.find((w) => w.name === 'Levin Sword')?.magic).toBe(true)
  })

  it('refines each weapon five levels at the smithy, from the chapter after it opens', () => {
    // The Iron Sword as Fire Emblem Wiki gives it: +1 Mt 7, +2 Hit 95, +3 Mt 9; each step's ore and gold its own (item.xml's refine table).
    const iron = FE17_LISTED.find((w) => w.name === 'Iron Sword')!
    expect(FE17_REFINE[iron.id].slice(0, 3).map((l) => [l.mt, l.hit])).toEqual([[7, 90], [7, 95], [9, 95]])
    expect(FE17_REFINE[iron.id][4]).toMatchObject({ iron: 200, steel: 15, silver: 1, gold: 1400 })
    expect(FE17_SMITHY_OPENS).toBe('fe17-m006')
  })

  it("rolls hit as Fates does (App.BattleMath.GetHitRatio10000)", () => {
    expect(trueHit('hybrid-fates', 75).trueHitBasisPoints).toBe(8500)
    expect(trueHit('hybrid-fates', 50).trueHitBasisPoints).toBe(5000)
  })
})

describe("Engage's supports", () => {
  it('gives each type its four levels from the support table', () => {
    expect(FE17_SUPPORTS.map((t) => t.type)).toEqual(['Default', 'Balanced', 'Hit', 'Crit', 'Avoid', 'Dodge'])
    for (const t of FE17_SUPPORTS) expect(t.levels.map((l) => l.level)).toEqual(['C', 'B', 'A', 'Ring'])
    // The Hit type at the ring: Hit +30, Avoid +5 (reliance.xml).
    expect(FE17_SUPPORTS.find((t) => t.type === 'Hit')!.levels[3]).toEqual({ level: 'Ring', hit: 30, crit: 0, avoid: 5, dodge: 0 })
  })
})
