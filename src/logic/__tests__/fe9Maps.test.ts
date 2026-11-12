import { describe, expect, it } from 'vitest'
import { FE9_MAPS } from '../../data/fe9/fe9Maps'
import { FE9_MAP_SET } from '../../data/fe9/fe9MapSet'
import { FE9_TERRAIN } from '../../data/fe9/fe9Terrain'
import type { ChapterMap, Difficulty, MapUnit, Tile } from '../../data/maps/types'
import { rowCodes, terrainAt, terrainInfo, terrainName } from '../maps'

const byHeading = (h: string) => FE9_MAPS.find((m) => m.heading === h)!
const on = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const enemies = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally').filter(on(d)).length
const arrivals = (m: ChapterMap, d: Difficulty) =>
  (m.reinforcements ?? []).reduce((n, g) => n + g.units.filter(on(d)).length * (/each turn/.test(String(g.when)) ? 2 : 1), 0)

// The Fire Emblem Wiki's enemy counts (starting, reinforcements) on Easy/Normal and Hard ("Difficult").
const WIKI: Record<string, [[number, number], [number, number]]> = {
  'Ch.1': [[7, 0], [10, 0]],
  'Ch.2': [[9, 0], [13, 0]],
  'Ch.3': [[14, 0], [15, 0]],
  'Ch.4': [[16, 0], [22, 0]],
  'Ch.5': [[22, 10], [26, 10]],
  'Ch.6': [[18, 0], [24, 0]],
  'Ch.7': [[15, 13], [21, 13]],
  'Ch.8': [[29, 12], [30, 13]],
  'Ch.9': [[17, 7], [23, 11]],
  'Ch.10': [[6, 14], [6, 16]],
  'Ch.11': [[28, 4], [33, 4]],
  'Ch.12': [[6, 7], [6, 8]],
  'Ch.13': [[23, 8], [28, 8]],
  'Ch.14': [[19, 2], [23, 2]],
  'Ch.15': [[20, 0], [20, 0]],
  'Ch.16': [[28, 7], [32, 7]],
  'Ch.17-2': [[18, 4], [20, 4]],
  'Ch.17-3': [[25, 20], [25, 21]],
  'Ch.18': [[20, 10], [24, 12]],
  'Ch.19': [[27, 0], [32, 0]],
  'Ch.20': [[27, 15], [32, 15]],
  'Ch.21': [[36, 13], [43, 13]],
  'Ch.22': [[41, 11], [47, 11]],
  'Ch.23': [[29, 13], [37, 13]],
  'Ch.24': [[35, 13], [43, 18]],
  'Ch.25': [[24, 2], [29, 6]],
  'Ch.26': [[35, 18], [44, 28]],
  'Ch.27': [[39, 0], [50, 0]],
  'Ch.27-2': [[1, 3], [1, 3]],
  'Ch.28': [[29, 7], [42, 13]],
  Endgame: [[50, 0], [40, 5]],
}
/** Where the game's files and the wiki's count differ, and why. */
const EXCEPTIONS: Record<string, string> = {
  'Ch.22': "One Thief short on Easy/Normal: the script brings it only on Hard. Not yet checked in-game.",
  Endgame: "Ashnard's second form is listed as a group of its own.",
  'Ch.17-3': 'Two area groups bring the turn 2 and turn 3 groups in again (25 + 22 on both); the wiki counts each group once.',
}

describe("Path of Radiance's maps from the game files", () => {
  it('has every chapter, from the Prologue to the Endgame', () => {
    expect(FE9_MAPS.map((m) => m.heading)).toEqual([
      'Prologue', ...Array.from({ length: 16 }, (_, i) => `Ch.${i + 1}`), 'Ch.17-1', 'Ch.17-2', 'Ch.17-3', 'Ch.17-4',
      ...Array.from({ length: 10 }, (_, i) => `Ch.${i + 18}`), 'Ch.27-2', 'Ch.28', 'Endgame',
      ...Array.from({ length: 6 }, (_, i) => `Trial ${i + 1}`),
    ])
    expect(new Set(FE9_MAPS.map((m) => m.id)).size).toBe(FE9_MAPS.length)
  })

  it('keeps every grid, unit and tile on the map, with terrain the table knows', () => {
    for (const m of FE9_MAPS) {
      expect(m.grid).toHaveLength(m.height)
      for (const row of m.grid) {
        expect(row, m.heading).toHaveLength(2 * m.width)
        for (const c of rowCodes(row)) expect(FE9_TERRAIN, `${m.heading} '${c}'`).toHaveProperty(c)
      }
      const inside = ([x, y]: [number, number]) => x >= 1 && x <= m.width && y >= 1 && y <= m.height
      for (const u of m.units) expect(inside(u.tile), `${m.heading} ${u.name}`).toBe(true)
      for (const t of m.starts) expect(inside(t), m.heading).toBe(true)
      for (const g of m.reinforcements ?? []) for (const u of g.units) expect(inside(u.tile), `${m.heading} ${u.name}`).toBe(true)
      if (m.corrinStart) expect(m.starts).toContainEqual(m.corrinStart)
    }
  })

  it('never stacks two units on one tile on the same difficulty', () => {
    for (const m of FE9_MAPS)
      for (const d of ['Normal', 'Hard'] as Difficulty[]) {
        const tiles = m.units.filter(on(d)).map((u) => u.tile.join(','))
        expect(tiles.length - new Set(tiles).size, `${m.heading} ${d}`).toBe(0)
      }
  })

  it("matches fireemblemwod.com's trial map overviews: every starting enemy", () => {
    expect(FE9_MAP_SET.extras!.maps.map((m) => m.units.length)).toEqual([31, 22, 17, 47, 40, 36])
  })

  it("matches the wiki's enemy counts", () => {
    for (const [heading, [normal, hard]] of Object.entries(WIKI)) {
      if (EXCEPTIONS[heading]) continue
      const m = byHeading(heading)
      expect([enemies(m, 'Normal'), arrivals(m, 'Normal')], `${heading} Easy/Normal`).toEqual(normal)
      expect([enemies(m, 'Hard'), arrivals(m, 'Hard')], `${heading} Hard`).toEqual(hard)
    }
  })

  it('reads bosses, drops, chests and villages', () => {
    const ch2 = byHeading('Ch.2')
    expect(ch2.units.find((u) => u.type === 'boss')).toMatchObject({ name: 'Ikanau', drops: ['Speedwing'] })
    expect(byHeading('Ch.7').objects).toContainEqual(expect.objectContaining({ type: 'chest', contents: 'Miracle' }))
    expect(byHeading('Ch.1').objects).toContainEqual(expect.objectContaining({ type: 'village', reward: 'Seraph Robe' }))
  })

  it('times reinforcements from the script, by phase and difficulty', () => {
    const ch12 = byHeading('Ch.12')
    expect(ch12.reinforcements!.map((g) => g.when)).toContain('Turn 13, start of the enemy phase')
    const ch16 = byHeading('Ch.16')
    // Normal() is true on Easy too, so Easy keeps Normal's turns.
    expect(ch16.reinforcements![0].when).toEqual({
      Easy: 'Turn 9, start of the player phase', Normal: 'Turn 9, start of the player phase', Hard: 'Turn 6, start of the player phase',
    })
    // One group per arrival: Ch.7's thief comes on turn 3 on Easy and Normal and turn 2 on Hard.
    const ch7 = byHeading('Ch.7').reinforcements!
    expect(ch7.find((g) => g.units.some((u) => u.name === 'Thief'))!.when).toEqual({
      Easy: 'Turn 3, start of the player phase', Normal: 'Turn 3, start of the player phase', Hard: 'Turn 2, start of the player phase',
    })
    // Ch.13's first group: turn 5 on every difficulty ('Normal() || Hard()' is one test).
    expect(byHeading('Ch.13').reinforcements![0].when).toBe('Turn 5, start of the enemy phase')
  })

  it('gives Easy its own openings and two more levels for every generic foe of a story chapter', () => {
    // Easy opens with the '_m' records: Ch.1's raiding Bandit stands at (2, 14) there, and isn't a looter.
    const ch1 = byHeading('Ch.1').units
    const raider = ch1.find((u) => u.name === 'Bandit' && u.tile[0] === 3 && u.tile[1] === 14)!
    expect(raider.difficulties).toEqual(['Normal', 'Hard'])
    expect(raider.looter).toBe(true)
    const easy = ch1.find((u) => u.name === 'Bandit' && u.tile[0] === 2 && u.tile[1] === 14)!
    expect(easy.difficulties).toEqual(['Easy'])
    expect(easy.looter).toBeUndefined()
    // 40 units stand elsewhere or carry other gear on Easy (37 on Easy alone, 3 placed alike on Easy and Hard).
    const all = FE9_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
    expect(all.filter((u) => u.difficulties?.join() === 'Easy').length + all.filter((u) => u.difficulties?.join() === 'Easy,Hard').length).toBe(40)
    // A generic foe is 2 levels higher on Easy (one entry, its Normal level first); a boss isn't.
    expect(ch1.find((u) => u.name === 'Fighter' && u.tile[0] === 6 && u.tile[1] === 2)!.note).toMatch(/^Lv 1 \(Easy 3\) Fighter/)
    expect(ch1.find((u) => u.name === 'Zawana')!.note).toMatch(/^Lv 4 \(Hard 5\)/)
    // Never past level 20, and never in the trial maps.
    for (const u of all) for (const m of u.note?.matchAll(/(?:Easy|Hard) (\d+)/g) ?? []) expect(Number(m[1])).toBeLessThanOrEqual(20)
    for (const m of FE9_MAPS.filter((x) => x.route === 'Trial')) for (const u of m.units) expect(u.note ?? '', m.heading).not.toMatch(/Easy \d/)
  })

  it('says which items a unit holds only from a second playthrough (the bands)', () => {
    const havetti = byHeading('Ch.3').units.find((u) => u.name === 'Havetti')!
    expect(havetti.drops).toEqual(['Thief Band (from a second playthrough)'])
    expect(havetti.note).toContain('Thief Band (from a second playthrough)')
    // Only bands carry the flag.
    const all = FE9_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
    for (const u of all) for (const d of u.drops ?? []) if (d.includes('second playthrough')) expect(d).toMatch(/ Band \(/)
  })

  it('places a group the script names by one file on every difficulty that runs the call', () => {
    // Ch.22's turn-5 thief is named by its Hard group with no difficulty check: it comes on Normal too, at (17, 14) (the user, in
    // the game), and on Easy two levels up.
    const thief = byHeading('Ch.22').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Thief')!
    expect(thief.tile).toEqual([17, 14])
    expect(thief.difficulties).toBeUndefined()
    expect(thief.note).toMatch(/^Lv 12 \(Easy 14\) Thief/)
    // A *SetMode call takes its groups by place: Ch.28's turn-8 wave is z03 on Easy and Normal, z04 on Hard.
    const tigers = byHeading('Ch.28').reinforcements!.find((g) => g.when === 'Turn 8, start of the player phase')!.units
    expect(tigers.filter((u) => u.difficulties?.includes('Hard')).length).toBe(2)
    expect(tigers.filter((u) => u.difficulties?.includes('Normal')).length).toBe(2)
  })

  it("says where fliers can cross but no unit can stop (the terrain record's byte 7)", () => {
    // A village house is Building under its roof: a flier crosses it but can't land on it (the user, in the game).
    const crossOnly = Object.values(FE9_TERRAIN).filter((t) => t!.note === 'Fliers can fly over it, but no unit can stop on it.')
    // A house (drawn as one town house's pieces), a roof and odds and ends are kinds of the game's Building.
    expect([...new Set(crossOnly.map((t) => t!.name))].sort()).toEqual(['Fence', 'Hole', 'House / building', 'Odds and ends', 'Roof', 'Rubble', 'Tree'])
    for (const t of crossOnly) expect(t!.move['Fliers']).toBe(1)
    // A flier lands on a river, the sea or a cliff.
    for (const t of Object.values(FE9_TERRAIN)) if (/^(River|Sea|Cliff)/.test(t!.name)) expect(t!.note ?? '').not.toMatch(/stop/)
  })

  it("states each chapter's goals in the game's own terms", () => {
    expect(byHeading('Ch.5')).toMatchObject({ victory: 'Defend for 6 turns', defeat: 'Ike dies, or enemy seizes location' })
    // The record's second goal set is Hard's: 20 turns there.
    expect(byHeading('Ch.20').victory).toBe('Arrive within 15 turns (20 on Hard)')
    // Ch.27-2 ends three ways.
    expect(byHeading('Ch.27-2').victory).toMatch(/Defeat the Black Knight.*escape by the marked exit.*turn 5/)
    expect(byHeading('Ch.27-2').objectives.map((o) => o.type)).toEqual(['escape'])
  })

  it('places fences, arrivals, talks and conditions from the files', () => {
    // The edge table's blocked sides between walkable tiles: ground units only, fliers cross them.
    expect(byHeading('Ch.1').walls!.length).toBeGreaterThan(10)
    expect(byHeading('Ch.20').walls).toHaveLength(15) // its barricades
    expect(FE9_MAPS.flatMap((m) => m.walls ?? []).every((w) => !w.all)).toBe(true)
    expect(byHeading('Ch.3').joiners).toContainEqual(expect.objectContaining({ name: 'Marcia', talk: expect.stringMatching(/brings her back in Ch.9/), ally: true }))
    expect(byHeading('Ch.11').units.some((u) => u.name === 'Nasir')).toBe(false)
    const ch13 = byHeading('Ch.13').units.filter((u) => u.tile[0] === byHeading('Ch.13').units.find((g) => g.name === 'Gatrie')!.tile[0])
    // Placed only if Gatrie is alive; the soldier who stands there otherwise is his stand-in.
    expect(byHeading('Ch.13').units.find((u) => u.name === 'Gatrie')!.standIn).toMatchObject({ name: 'Soldier' })
    expect(ch13.filter((u) => u.tile[1] === byHeading('Ch.13').units.find((g) => g.name === 'Gatrie')!.tile[1])).toHaveLength(1)
    expect(byHeading('Ch.7').notes.join(' ')).toMatch(/Balmer isn't on the map at the start/)
    // Greil comes and goes in Ch.7; Gatrie and Shinon arrive with him and join you.
    const ch7 = byHeading('Ch.7').joiners!
    expect(ch7.some((j) => j.name === 'Greil')).toBe(false)
    expect(ch7.filter((j) => ['Gatrie', 'Shinon'].includes(j.name) && !j.ally)).toHaveLength(2)
    // Haar leaves at the start of Ch.23 and flies back in later, recruited by Jill.
    expect(byHeading('Ch.23').reinforcements!.flatMap((g) => g.units)).toContainEqual(expect.objectContaining({ name: 'Haar', talk: 'Recruit: talk with Jill' }))
  })

  it("crops each map to the playable grid of the game's overview", () => {
    const size = (h: string) => [byHeading(h).width, byHeading(h).height]
    expect(size('Ch.1')).toEqual([12, 16])
    expect(size('Ch.8')).toEqual([24, 24])
    expect(size('Ch.13')).toEqual([22, 19])
    expect(size('Ch.17-1')).toEqual([20, 28])
    expect(size('Endgame')).toEqual([33, 33])
    // Haar and his wyverns watch Ch.11 from off the grid; Tibarn's hawks fly into Ch.17's last section.
    expect(byHeading('Ch.11').units.some((u) => u.name === 'Haar')).toBe(false)
    expect(byHeading('Ch.17-4').joiners!.map((j) => j.name)).toContain('Tibarn')
    expect(byHeading('Ch.17-1').joiners ?? []).toHaveLength(0)
    // Edges checked against the game by hand.
    expect(size('Ch.10')).toEqual([20, 19])
    expect(size('Ch.15')).toEqual([28, 18])
    expect(size('Ch.23')).toEqual([50, 8])
    expect(size('Ch.27')).toEqual([27, 31])
  })

  it('sets Ike and Mist down for the duel in Ch.27-2, with no one from the cutscene', () => {
    const m = byHeading('Ch.27-2')
    expect(m.units.map((u) => u.name)).toEqual(['Black Knight'])
    expect(m.starts).toContainEqual(m.corrinStart)
    expect(m.forced).toEqual([{ name: 'Mist', tile: expect.anything() }])
    expect(m.starts).toContainEqual(m.forced![0].tile)
  })

  it("leaves Leanne off Ch.17's last two sections (Ike carries her) and shows its ruins as rubble", () => {
    for (const h of ['Ch.17-3', 'Ch.17-4']) {
      expect(byHeading(h).units.some((u) => u.name === 'Leanne'), h).toBe(false)
      expect(byHeading(h).notes.join(' '), h).toMatch(/Ike carries Leanne/)
    }
    for (const h of ['Ch.17-1', 'Ch.17-2', 'Ch.17-3', 'Ch.17-4']) expect(byHeading(h).grid.flatMap(rowCodes)).not.toContain('oe')
    // The ruins' tiles are what the game names them (Building), and fliers only.
    expect(terrainInfo(byHeading('Ch.17-3'), 'wj')).toMatchObject({ name: 'Building', move: { Infantry: null, Fliers: 1 } })
    expect(terrainAt(byHeading('Ch.17-3'), [20, 1])).toBe('wj')
  })

  it("splits Ch.17 into its four sections, each with its own goal", () => {
    expect(['Ch.17-1', 'Ch.17-2', 'Ch.17-3', 'Ch.17-4'].map((h) => byHeading(h).victory)).toEqual([
      'Rout the enemy', 'Arrive', 'Survive for 10 turns', 'Defeat boss',
    ])
  })

  it("marks Ch.25's eleven boulders with their paths", () => {
    const rocks = byHeading('Ch.25').changes.filter((c) => c.trigger === 'boulder')
    expect(rocks).toHaveLength(11)
    const m = byHeading('Ch.25')
    for (const r of rocks) {
      expect(r.path![0]).toEqual(r.tile.default)
      // The rock sits in front of the foe who pushes it, never on the foe, on Stone no unit enters until it rolls.
      expect(m.units.some((u) => u.tile[0] === r.tile.default[0] && u.tile[1] === r.tile.default[1]), r.id).toBe(false)
      expect(terrainAt(m, r.tile.default), r.id).toBe('wa')
      expect(r.patch, r.id).toEqual([{ tile: r.tile.default, becomes: expect.stringMatching(/^(t0|t1|bl)$/) }])
      // Each follows the path its script spells out and breaks on the last tile, on the map.
      const [x, y] = r.path!.at(-1)!
      expect(x >= 1 && y >= 1 && x <= m.width && y <= m.height, r.id).toBe(true)
    }
    expect(rocks.map((r) => r.tile.default)).toContainEqual([9, 20])
    // Rock 2 breaks a row above the bottom edge; the rest reach it (main.dol's rolling code, the scripts' TTPMEntry strings).
    expect(rocks.map((r) => r.path!.at(-1)![1])).toEqual([1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1])
  })

  it("places the ballistae beside their firing tiles, and the pits in Ch.23's bridge", () => {
    const ballistae = FE9_MAPS.flatMap((m) => m.objects.filter((o) => o.type === 'ballista').map((o) => [m, o] as const))
    expect(ballistae.map(([m]) => m.heading).sort()).toEqual(['Ch.19', 'Ch.19', 'Ch.19', 'Ch.23', 'Ch.23', 'Ch.23', 'Ch.23', 'Ch.23', 'Ch.24', 'Ch.24', 'Ch.24', 'Ch.25', 'Ch.25', 'Ch.25', 'Trial 2', 'Trial 2', 'Trial 2', 'Trial 2'])
    for (const [m, o] of ballistae) {
      if (o.type !== 'ballista') continue
      expect(terrainAt(m, o.machine), `${m.heading} ${o.machine}`).toBe('of')
      expect(Math.abs(o.machine[0] - o.tile[0]) + Math.abs(o.machine[1] - o.tile[1])).toBe(1)
      // Whoever starts on a firing tile is a bow user.
      for (const u of m.units.filter((u) => u.tile[0] === o.tile[0] && u.tile[1] === o.tile[1])) expect(u.note).toMatch(/Archer|Sniper/)
    }
    expect(ballistae.map(([, o]) => o.type === 'ballista' && o.weapon)).toEqual(expect.arrayContaining(['Ballista', 'Iron Ballista', 'Killer B', 'Onager']))
    const ch23 = byHeading('Ch.23')
    const pits = ch23.changes.filter((c) => c.trigger === 'trap')
    expect(pits).toHaveLength(12)
    // A hidden trap: the lid is bridge a ground unit can step onto, and once sprung it stays a hole. Previewed one by one or all.
    for (const p of pits) {
      expect(terrainAt(ch23, p.tile.default)).toBe('tb')
      expect(p.patch).toEqual([{ tile: p.tile.default, becomes: 'wd' }])
      expect(p.group).toBe('pits')
    }
  })

  it('keeps Mist off the Prologue: she watches from beside it', () => {
    const m = byHeading('Prologue')
    // The game's own border (mapextra byte 5).
    expect([m.width, m.height]).toEqual([10, 8])
    expect(m.units.some((u) => u.name === 'Mist')).toBe(false)
    expect(m.notes.join(' ')).toMatch(/Mist watches from just off the map/)
  })

  it("finds Ch.15's buried items and Stefan's hiding spot", () => {
    const hidden = byHeading('Ch.15').objects.filter((o) => o.type === 'hidden')
    expect(hidden.map((o) => o.type === 'hidden' && o.contents).sort()).toEqual(
      ['Boots', 'Coin', 'Coin', 'Guard', 'Physic', 'Shine', 'Silver Blade', 'Statue Frag', 'Stefan (with the Vague Katti)', 'White Gem'],
    )
    expect(hidden.find((o) => o.type === 'hidden' && o.contents.startsWith('Stefan'))).toMatchObject({ note: expect.stringMatching(/Lethe or Mordecai/) })
    // Each sparkle sits in its dig zone, and the zone stays on the (cropped) map.
    const m = byHeading('Ch.15')
    for (const o of hidden) {
      if (o.type !== 'hidden') continue
      const [l, b, r, t] = o.area
      expect(l <= o.tile[0] && o.tile[0] <= r && b <= o.tile[1] && o.tile[1] <= t, o.contents).toBe(true)
      expect(l >= 1 && b >= 1 && r <= m.width && t <= m.height, o.contents).toBe(true)
    }
  })

  it("uses the game's terrain: a thicket gives Avoid +10 and Def +1 and slows horses", () => {
    const thicket = terrainInfo(byHeading('Ch.2'), 'ba')
    expect(thicket).toMatchObject({ name: 'Thicket', def: 1, avo: 10 })
    expect(thicket.move).toMatchObject({ Infantry: 2, 'Horse knights': 3, 'Beast laguz': 1, Fliers: 1 })
  })

  it('has the six trial maps, in their own dropdown, with their goals and descriptions', () => {
    const trials = FE9_MAP_SET.extras!.maps
    expect(trials.map((m) => `${m.heading}: ${m.title}`)).toEqual([
      'Trial 1: Hillside Battle', 'Trial 2: Lonely Isle', 'Trial 3: Strange Turn', 'Trial 4: Desperation', 'Trial 5: Escape', 'Trial 6: Trapped',
    ])
    expect(trials.map((m) => m.victory)).toEqual([
      'Rout the enemy', 'Defend for 8 turns', 'Rout the enemy', 'Arrive within 15 turns', 'Escape', 'Defend for 10 turns',
    ])
    for (const m of trials) {
      expect(m.route).toBe('Trial')
      // No story text from the trial's menu.
      expect(m.notes.join(' '), m.heading).not.toMatch(/Ike's party|marching/)
      expect(m.starts.length, m.heading).toBeGreaterThan(0)
    }
    // Trial 4 is lost after turn 15, so the groups timed later never come.
    expect(byHeading('Trial 4').reinforcements!.map((g) => g.when).at(-1)).toBe('Turn 15, start of the player phase')
    // Trial 5's groups each come through their own door.
    expect(new Set(byHeading('Trial 5').reinforcements!.map((g) => g.when))).toEqual(
      new Set(['After the bottom-left door is opened', 'After the bottom-right door is opened', 'After the top-left door is opened']),
    )
    // Trial 1's rocks roll 6 to 12 tiles down the paths its script spells out, over the cliffs.
    const rocks = byHeading('Trial 1').changes.filter((c) => c.trigger === 'boulder')
    expect(rocks).toHaveLength(11)
    for (const r of rocks) {
      expect(terrainAt(byHeading('Trial 1'), r.tile.default)).toBe('wa')
      expect(r.path!.length, r.id).toBeGreaterThanOrEqual(7)
    }
  })

  it("starts each map as the game lays it out: rooms under roofs, village houses, goal tiles; opening them shows what's under", () => {
    // Ch.16, Ch.21 and Ch.27's rooms are closed to everyone, fliers included, until a door into them opens.
    const count = (h: string, code: string) => byHeading(h).grid.flatMap(rowCodes).filter((c) => c === code).length
    expect([count('Ch.16', 'ws'), count('Ch.21', 'ws'), count('Ch.27', 'ws')]).toEqual([50, 74, 240])
    expect(terrainInfo(byHeading('Ch.16'), 'ws').move).toMatchObject({ Infantry: null, Fliers: null })
    const doors = byHeading('Ch.16').changes.filter((c) => c.trigger === 'breakable' && (c.patch ?? []).length > 1)
    expect(doors).toHaveLength(2)
    for (const d of doors) expect(d.effect).toMatch(/room behind it opens/)
    // A village bandits can raze says so in its note: no change to preview (the user's call).
    for (const m of FE9_MAPS) expect(m.changes.some((c) => c.id.startsWith('raze-')), m.id).toBe(false)
    const razeable = byHeading('Ch.1').objects.filter((o) => o.type === 'village' && /Bandits can raze it/.test(o.note ?? ''))
    expect(razeable.length).toBeGreaterThan(0)
    // Seize, arrive, escape and defend tiles are the game's goal terrain (heals 10%), named as the game names them.
    const ch1Seize = byHeading('Ch.1').objectives.find((o) => o.type === 'seize')!.tiles[0]
    expect(terrainAt(byHeading('Ch.1'), ch1Seize)).toBe('bc')
    expect(terrainName(byHeading('Ch.1'), ch1Seize)).toBe('Objective')
    // Ch.17's ruins are what the game lays there, rubble to everyone but fliers.
    expect(terrainAt(byHeading('Ch.17-4'), [8, 3])).toBe('wj')
  })

  it("keeps a village on the ground it stands on, names tiles as the game does, and has Ch.5's fog on Hard", () => {
    // Ch.9's two villages on the coast keep its Def +1 and Avo +10.
    const ch9 = byHeading('Ch.9')
    for (const t of [[2, 19], [1, 23]] as Tile[]) expect(terrainInfo(ch9, terrainAt(ch9, t)).def, String(t)).toBe(1)
    expect(terrainName(ch9, [2, 19])).toBe('Coast')
    // Trail and coast work alike but each has its own colour and icon.
    expect(new Set(ch9.grid.flatMap(rowCodes))).toContain('b4')
    expect(byHeading('Ch.5').fogOn).toEqual(['Hard'])
    expect(FE9_MAPS.filter((m) => m.fog || m.fogOn).map((m) => m.heading)).toEqual(['Ch.5'])
    expect(FE9_MAP_SET.terrainNote).toMatch(/Fliers get no Def\/Avo/)
  })

  it("reads what the scripts' handlers hand to each other: the alarm, the prisoners, the looters, partners and bosses", () => {
    // Ch.10: the three Watches raise one alarm that brings all three groups at once.
    const ch10 = byHeading('Ch.10')
    expect(ch10.reinforcements!.map((g) => g.when)).toEqual([expect.stringMatching(/^When a Watch raises the alarm/)])
    expect(ch10.units.filter((u) => u.name === 'Watch')).toHaveLength(3)
    // Its prisoners' talks make them partner units; they head for the exit once their door is open.
    const brom = ch10.units.find((u) => u.name === 'Brom')!
    expect(brom.talk).toMatch(/becomes a partner unit/)
    expect(brom.goesTo).toEqual(ch10.objectives.find((o) => o.type === 'escape')!.tiles)
    // Looters carry the torch badge; those that leave head for the map's exits.
    const looters = FE9_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].filter((u) => u.looter))
    expect(looters.length).toBeGreaterThan(10)
    expect(byHeading('Ch.7').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Thief')!.goesTo!.length).toBeGreaterThan(0)
    // Where a unit heads is cropped with the map, arriving ones too: on the grid, and the same exits whoever's going there.
    for (const m of FE9_MAPS)
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
        for (const [x, y] of u.goesTo ?? []) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name}`).toBe(true)
    const ch22 = byHeading('Ch.22')
    const exitsOf = (us: MapUnit[]) => us.filter((u) => u.looter && u.goesTo).map((u) => u.goesTo)
    expect(exitsOf(ch22.reinforcements!.flatMap((g) => g.units))[0]).toEqual(exitsOf(ch22.units)[0])
    // Partner units (army 3) are yellow: Lethe and Mordecai in Ch.9, Tibarn in Ch.28.
    expect(byHeading('Ch.9').units.filter((u) => u.yellow).map((u) => u.name).sort()).toEqual(['Lethe', 'Mordecai'])
    expect(byHeading('Ch.28').units.find((u) => u.name === 'Tibarn')!.yellow).toBe(true)
    // The chapter's own boss gets the skull: Muarim in Ch.15; the Black Knight passing through Ch.11 and Ch.24 doesn't.
    expect(byHeading('Ch.15').units.find((u) => u.name === 'Muarim')!.type).toBe('boss')
    for (const h of ['Ch.11', 'Ch.24'])
      expect(byHeading(h).reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Black Knight')!.type, h).toBe('named')
    // Shinon comes back with a Brave Bow he drops; he joins only through Rolf's talk and Ike's win.
    const shinon = byHeading('Ch.18').units.find((u) => u.name === 'Shinon')!
    expect(shinon.drops).toEqual(['Brave Bow'])
    expect(shinon.talk).toMatch(/Rolf talks to him, then Ike defeats him/)
    // Ch.17's later sections set your whole army down.
    expect(byHeading('Ch.17-2').starts).toHaveLength(10)
    // A unit that differs between difficulties only by level is one entry.
    expect(byHeading('Ch.1').units.filter((u) => u.name === 'Zawana')).toHaveLength(1)
    expect(byHeading('Ch.1').units.find((u) => u.name === 'Zawana')!.note).toMatch(/^Lv 4 \(Hard 5\)/)
  })

  it("plays out the Prologue in the script's order: Boyd first, then Greil", () => {
    const m = byHeading('Prologue')
    expect(m.units.map((u) => [u.name, u.type])).toEqual([['Boyd', 'named']])
    expect(m.units[0].note).toMatch(/Once beaten, Boyd turns green/)
    const greil = m.reinforcements!.flatMap((g) => g.units)
    expect(greil).toEqual([expect.objectContaining({ name: 'Greil', type: 'boss' })])
    expect(m.reinforcements![0].when).toBe('Once Boyd is beaten')
  })
})

describe("Path of Radiance's tiles each drawn as itself, by the game's own terrain names (the user's call)", () => {
  it('draws plain, floor, snowfield and deck each as itself, castle walls and ruins as theirs, houses as town houses', () => {
    for (const m of FE9_MAPS) expect(new Set(m.grid.flatMap(rowCodes)).has('ta'), m.id).toBe(false)
    const all = new Set(FE9_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const c of ['t0', 't1', 't2', 't3', 'w0', 'w1', 'o4', 'ra'] as const) expect(all.has(c), c).toBe(true)
    expect(FE9_TERRAIN.t1!.move).toEqual(FE9_TERRAIN.t0!.move)
  })

  it("draws a town's paved plain as paving where its minimap shows a town's ground (Port Toha, Pirates Aground's port)", () => {
    for (const id of ['fe9-3', 'fe9-11']) {
      const codes = new Set(FE9_MAPS.find((m) => m.id === id)!.grid.flatMap(rowCodes))
      expect(codes.has('t8'), id).toBe(true)
      expect(codes.has('t0'), id).toBe(false)
    }
    expect(new Set(FE9_MAPS.find((m) => m.id === 'fe9-1')!.grid.flatMap(rowCodes)).has('t0')).toBe(true)
    expect(FE9_TERRAIN.t8!.move).toEqual(FE9_TERRAIN.t0!.move)
    expect(FE9_TERRAIN.t8!.name).toBe("Plain (a town's paving)")
  })

  it('draws a sandy map (more sand than grass) in sandstone: the desert of Ch.15', () => {
    const desert = FE9_MAPS.find((m) => m.id === 'fe9-15')!
    const codes = new Set(desert.grid.flatMap(rowCodes))
    expect(codes.has('w5')).toBe(true)
    expect(codes.has('w0')).toBe(false)
    expect(desert.fills?.t1).toBeDefined()
    expect(FE9_TERRAIN.w5!.move).toEqual(FE9_TERRAIN.w0!.move)
  })
})
