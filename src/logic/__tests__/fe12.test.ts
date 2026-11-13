import { describe, expect, it } from 'vitest'
import { FE12_ITEM_SOURCES } from '../../data/fe12/fe12ItemSources'
import { FE12_LISTED } from '../../data/fe12/fe12Listed'
import { FE12_MAPS } from '../../data/fe12/fe12Maps'
import { FE12_FORK, FE12_MAP_SET, FE12_STORY } from '../../data/fe12/fe12MapSet'
import { FE12_SUPPORTS } from '../../data/fe12/fe12Supports'
import { FE12_TERRAIN } from '../../data/fe12/fe12Terrain'
import { FE12_TRIANGLE } from '../../data/fe12/fe12Triangle'
import { FE12_WEAPONS } from '../../data/fe12/fe12Weapons'
import { GAMES, MISSING_GAMES } from '../../games'
import { walkFork } from '../spoiler'

const map = (id: string) => FE12_MAPS.find((m) => m.id === id)!
const weapon = (name: string) => FE12_WEAPONS.find((w) => w.name === name)!
const MODES = ['Normal', 'Hard', 'Maniac', 'Lunatic', 'Reverse Lunatic']

describe("New Mystery of the Emblem's chapters", () => {
  it('is in the picker as the 12th game, no longer a placeholder', () => {
    expect(GAMES.find((g) => g.id === 'fe12')).toMatchObject({ number: 12, hitSystem: '2rn' })
    expect(MISSING_GAMES.some((g) => g.number === 12)).toBe(false)
  })

  it('has Prologue I-VIII (IV, VI and VII twice), Chapters 1-23 with each gaiden chapter where it comes, and the Endgame', () => {
    expect(FE12_STORY.maps.map((m) => m.id)).toEqual([
      'fe12-p1', 'fe12-p2', 'fe12-p3', 'fe12-p4', 'fe12-p4b', 'fe12-p5', 'fe12-p6', 'fe12-p6b', 'fe12-p7', 'fe12-p7b', 'fe12-p8',
      'fe12-1', 'fe12-2', 'fe12-3', 'fe12-3x', 'fe12-4', 'fe12-5', 'fe12-6', 'fe12-6x', 'fe12-7', 'fe12-8', 'fe12-9', 'fe12-10',
      'fe12-10x', 'fe12-11', 'fe12-12', 'fe12-13', 'fe12-13x', 'fe12-14', 'fe12-15', 'fe12-16', 'fe12-16x', 'fe12-17', 'fe12-18',
      'fe12-19', 'fe12-20', 'fe12-20x', 'fe12-21', 'fe12-22', 'fe12-23', 'fe12-final',
    ])
    // The Archanean Chronicles and the downloadable chapters are a list of their own.
    expect(FE12_MAP_SET.extras!.maps.map((m) => m.id)).toEqual([
      'fe12-ac1', 'fe12-ac2', 'fe12-ac3', 'fe12-ac4', 'fe12-dl1', 'fe12-dl2', 'fe12-dl3',
    ])
  })

  it("splits three times in the prologue: the answer at the end of III, V and VI picks the next chapter's version", () => {
    const ids = (route: string) => walkFork(FE12_FORK, route).story.maps.map((m) => m.id)
    expect(FE12_FORK.choices.map((c) => c.label)).toEqual(['Prologue IV (Yes)', 'Prologue IV (No)'])
    const yes = ids('yes/yes/yes')
    expect(yes.slice(0, 11)).toEqual(['fe12-p1', 'fe12-p2', 'fe12-p3', 'fe12-p4b', 'fe12-p5', 'fe12-p6b', 'fe12-p7b', 'fe12-p8', 'fe12-1', 'fe12-2', 'fe12-3'])
    const mixed = ids('no/yes/no')
    expect(mixed.slice(0, 8)).toEqual(['fe12-p1', 'fe12-p2', 'fe12-p3', 'fe12-p4', 'fe12-p5', 'fe12-p6b', 'fe12-p7', 'fe12-p8'])
    expect(mixed.at(-1)).toBe('fe12-final')
  })

  it('takes its names and titles from the translation patch, and its five modes from its menu', () => {
    expect(map('fe12-1').title).toBe('Grustian Expedition')
    expect(map('fe12-final').title).toBe('Light and Shadow')
    expect(map('fe12-ac1').title).toBe('Fall')
    expect(FE12_MAP_SET.difficulties.map((d) => d.value)).toEqual(MODES)
    expect(map('fe12-1').defeat).toBe('Marth or the Avatar is defeated')
    expect(map('fe12-p1').defeat).toBe('The Avatar is defeated')
  })

  it('opens each gaiden chapter by a turn limit the difficulty scales (GetNormalizeTurn), or another way', () => {
    const turns = (id: string) =>
      MODES.map((mode) => {
        const n = [...(map(id).notes ?? []), ...(map(id).notesOn ?? []).filter((x) => x.difficulties.includes(mode as never)).map((x) => x.note)]
        return Number(/by turn (\d+)/.exec(n.find((x) => x.startsWith('Opens if')) ?? '')?.[1])
      })
    // 24 turns x 100, 120, 140, 160 and 180%, rounded down.
    expect(turns('fe12-3x')).toEqual([24, 28, 33, 38, 43])
    expect(turns('fe12-10x')).toEqual([15, 18, 21, 24, 27])
    const say = (id: string) => (map(id).notesOn ?? []).find((n) => n.note.startsWith('Opens if'))!.note
    expect(say('fe12-6x')).toContain('or if Rickard is in your army when it ends')
    expect(say('fe12-13x')).toContain('or if no foe has escaped the map')
    expect(say('fe12-16x')).toContain('the Avatar is in a promoted class at level 5 or higher')
    expect(say('fe12-20x')).toContain('at least 3 of Roshea, Wolf, Sedgar, Vyland and Midia')
    // Prologue VIII's end sets 3x's flag too; Chapter 20 goes on only with the Binding Shield (its ChapterNext, else BadEnd).
    expect(say('fe12-3x')).toContain('or if no more than 1 of your units fell in the prologue')
    expect(say('fe12-20x')).toContain('and only once the Binding Shield is completed there')
    expect(map('fe12-20').notes).toContain(
      'The story goes on only if the Binding Shield is completed here, with all five orbs gathered; otherwise the game ends after this chapter.',
    )
  })
})

describe("New Mystery of the Emblem's maps", () => {
  it('keeps the units each mode places, its items gated and its weapons stepped up as the foe builder does', () => {
    // Chapter 15's Paladin: its Ridersbane (a 0x7d weapon) forged Mt +4 on Maniac, +8 on Lunatic (tier 3).
    const paladins = map('fe12-15').units.filter((u) => u.name === 'Paladin' && u.note?.includes('Ridersbane'))
    expect(paladins.map((u) => [u.difficulties, u.carries?.[0]])).toEqual([
      [['Normal', 'Hard'], 'Ridersbane'],
      [['Maniac'], 'Ridersbane (forged: Mt +4, Hit +20)'],
      [['Lunatic', 'Reverse Lunatic'], 'Ridersbane (forged: Mt +8, Hit +20)'],
    ])
    // Each mode's own levels and rank floor, Lunatic's +10 hit and Reverse Lunatic's order.
    const on = (mode: string) => map('fe12-15').notesOn!.filter((n) => n.difficulties.includes(mode as never)).map((n) => n.note)
    expect(on('Hard')[0]).toContain("gain 8 levels' worth of growth")
    expect(on('Lunatic')[0]).toContain('Foes get +10 hit.')
    expect(on('Reverse Lunatic')[0]).toContain('the foe strikes first')
  })

  it("starts Prologue I with the Avatar; on Normal Jagen and the soldier come back with the tutorial's steps", () => {
    expect(map('fe12-p1').forced).toEqual([{ name: 'Avatar', tile: [9, 1] }])
    expect(map('fe12-p1').units.map((u) => [u.name, u.difficulties])).toEqual([
      ['Jagen', ['Hard', 'Maniac', 'Lunatic', 'Reverse Lunatic']],
      ['Soldier', ['Hard', 'Maniac', 'Lunatic', 'Reverse Lunatic']],
    ])
  })

  it('has its secret shops (a VIP Card) with their limited stock, and its hidden treasures', () => {
    const shop = map('fe12-5').objects.find((o) => o.type === 'shop' && o.kind === 'Secret shop')
    expect(shop).toMatchObject({ stock: ['Master Seal (1 in stock)'] })
    expect(map('fe12-11').objects.filter((o) => o.type === 'hidden')).toHaveLength(10)
    expect(FE12_ITEM_SOURCES['Lady Sword']).toContainEqual(expect.objectContaining({ mapId: 'fe12-11', kind: 'hidden' }))
  })

  it("gives the Endgame's altars, where Medeus stands and the dragons appear, the summoning sigil's code", () => {
    expect(FE12_TERRAIN.oi).toMatchObject({ name: 'Altar', avo: 20, def: 2 })
    expect(Object.values(FE12_TERRAIN.oi!.move).every((c) => c === null)).toBe(true)
  })

  it('wins Archanean Chronicles 4 when Nyna reaches her tile', () => {
    expect(map('fe12-ac4').objectives).toEqual([{ type: 'arrive', tiles: [[23, 29]], label: 'Nyna arrives here' }])
  })

  it('sells the Iron weapons, Fire and Heal at the preparations, from Chapter 1', () => {
    const prep = (name: string) => FE12_ITEM_SOURCES[name].filter((s) => s.text === "Sold at the preparations' armory").map((s) => s.mapId)
    expect(prep('Iron Sword')[0]).toBe('fe12-1')
    expect(prep('Heal')).toContain('fe12-final')
    expect(prep('Iron Sword').some((id) => id.startsWith('fe12-p'))).toBe(false)
  })

  it("puts the downloadable chapters' items behind the DLC switch", () => {
    const dl = Object.values(FE12_ITEM_SOURCES).flat().filter((s) => s.mapId.startsWith('fe12-dl'))
    expect(dl.length).toBeGreaterThan(0)
    expect(dl.every((s) => s.kind.startsWith('dlc-'))).toBe(true)
  })
})

/** Fire Emblem Wiki's chapter boxes (New Mystery tab, Normal): the grid's columns and rows, the foes on the map at the start, and
 * the reinforcements over the chapter. 16x's size is fireemblemwod.com's (the wiki has none); 20x's box says 15x21, its whole map
 * image with the border, whose grid inside is 13x19. Where a named foe and their stand-in are both listed (Chapters 8, 9, 16, 19),
 * the box counts one of each pair, as does the map. */
const WIKI: Record<string, [number, number, number, number | null]> = {
  p1: [9, 6, 0, 2], p2: [9, 6, 1, 1], p3: [9, 6, 2, 1], p4: [9, 6, 4, 0], p4b: [9, 6, 5, 0], p5: [12, 10, 6, 0], p6: [9, 6, 5, 0],
  p6b: [9, 6, 5, 0], p7: [11, 8, 7, 2], p7b: [11, 8, 7, 2], p8: [9, 18, 11, 4], 1: [20, 20, 11, 1], 2: [30, 30, 14, 0],
  3: [30, 30, 14, 5], '3x': [30, 6, 9, 2], 4: [30, 30, 18, 4], 5: [30, 24, 24, 1], 6: [30, 30, 20, 12], '6x': [9, 10, 12, 0],
  7: [30, 30, 17, 15], 8: [30, 30, 19, 13], 9: [30, 30, 18, 6], 10: [30, 30, 20, 0], '10x': [9, 15, 7, null], 11: [30, 30, 29, 0],
  12: [30, 30, 19, 11], 13: [30, 30, 28, 6], '13x': [16, 11, 9, 0], 14: [30, 30, 24, 3], 15: [30, 30, 33, 14], 16: [30, 30, 26, 4],
  '16x': [12, 9, 9, 2], 17: [30, 28, 29, 6], 18: [30, 22, 24, 16], 19: [30, 23, 26, 10], 20: [30, 28, 28, 16], '20x': [13, 19, 13, 0],
  21: [30, 30, 29, 4], 22: [30, 30, 32, 30], 23: [30, 30, 28, 10], final: [30, 30, 23, null], ac1: [14, 22, 22, 0],
  ac2: [30, 22, 22, 12], ac3: [22, 22, 29, 0], ac4: [30, 30, 29, 40], dl1: [21, 23, 20, 7], dl2: [22, 21, 26, 14], dl3: [21, 14, 16, 10],
}
const ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']
/** How many times a group comes, read from its time on a difficulty: 'Turns 4-8, enemy phase' 5, 'The first and third enemy phases
 * after...' 2, once for one set off by an event or that comes the first of its turns; null for one that goes on. */
const comes = (when: string): number | null => {
  if (/^Every /.test(when)) return null
  if (/: the first of them/.test(when) || /^(As the tutorial|When a unit enters|The first player phase with no foe)/.test(when)) return 1
  let m = /^Turns? ([\d, and-]+?), (enemy|player) phase/.exec(when)
  if (m) return m[1].split(/, | and /).reduce((n, p) => n + (p.includes('-') ? Number(p.split('-')[1]) - Number(p.split('-')[0]) + 1 : 1), 0)
  m = /^Each of the first (\d+) /.exec(when)
  if (m) return Number(m[1])
  m = /^The ([a-z, ]+?) (enemy|player) phases? /.exec(when)
  if (m) return m[1].split(/, | and /).filter((w) => ORDINALS.includes(w)).length
  return NaN
}
const onNormal = (u: { difficulties?: string[] }) => !u.difficulties || u.difficulties.includes('Normal')
const whenOn = (g: { when?: string | Partial<Record<string, string>> }, d: string) => (typeof g.when === 'string' ? g.when : g.when?.[d])

describe("New Mystery of the Emblem's maps against Fire Emblem Wiki", () => {
  it('has each grid and each Normal start of the chapter boxes', () => {
    for (const m of FE12_MAPS) {
      const [cols, rows, foes] = WIKI[m.id.slice(5)]
      expect([m.width, m.height], m.id).toEqual([cols, rows])
      const start = m.units.filter((u) => ['enemy', 'named', 'boss'].includes(u.type) && onNormal(u)).length
      // Prologue VI: Ogma (Draug) walks off the map in the opening on Normal and comes back once the rest are beaten; the box counts
      // him among the five.
      expect(start, m.id).toBe(['fe12-p6', 'fe12-p6b'].includes(m.id) ? foes - 1 : foes)
    }
  })

  it("brings each chapter's reinforcements on Normal, as many as the boxes count", () => {
    for (const m of FE12_MAPS) {
      const want = WIKI[m.id.slice(5)][3]
      if (want === null) continue // 10x's copies and the Endgame's summons go on without end
      const got = (m.reinforcements ?? []).reduce((n, g) => {
        const w = whenOn(g, 'Normal')
        return w ? n + (comes(w) ?? NaN) * g.units.filter(onNormal).length : n
      }, 0)
      // Prologue VI: Ogma's (Draug's) return is the box's fifth foe at the start.
      expect(got, m.id).toBe(['fe12-p6', 'fe12-p6b'].includes(m.id) ? want + 1 : want)
    }
  })
})

describe("New Mystery of the Emblem's reinforcements, read path by path", () => {
  const group = (id: string, i: number) => map(id).reinforcements![i]

  it('gives each difficulty its own turns (a check of GetHard in an and-chain, or a turn apart)', () => {
    // Chapter 4's two groups: turn 6 on Normal, 6 and 8 on Hard, 5 and 7 on Maniac, 3 and 4 on Lunatic; the first alone a turn before.
    expect(MODES.map((d) => whenOn(group('fe12-4', 1), d))).toEqual([
      'Turn 6, enemy phase', 'Turns 6 and 8, enemy phase', 'Turns 5 and 7, enemy phase', 'Turns 3 and 4, enemy phase', 'Turns 3 and 4, enemy phase',
    ])
    expect(group('fe12-4', 0).units.every((u) => !u.difficulties?.includes('Normal'))).toBe(true)
    // Chapter 6's four groups come a turn sooner on Lunatic, every unit on every difficulty.
    expect(whenOn(group('fe12-6', 0), 'Normal')).toBe('Turn 4, enemy phase')
    expect(whenOn(group('fe12-6', 0), 'Lunatic')).toBe('Turn 3, enemy phase')
    // Chapter 18: z02 on turns 2, 4 and 6, z03 on the turns between (one handler's GetTurn() checks).
    expect(map('fe12-18').reinforcements!.map((g) => whenOn(g, 'Normal'))).toEqual([
      'Turn 2, enemy phase, while the village at (2, 7) is unvisited', 'Turns 2, 4 and 6, enemy phase', 'Turns 3 and 5, enemy phase',
    ])
  })

  it('times a counter by the phases since what starts it: an area, a chest, a door, or a turn on harder modes', () => {
    expect(whenOn(group('fe12-12', 1), 'Normal')).toBe('The third enemy phase after one of your units enters the area below')
    expect(whenOn(group('fe12-12', 0), 'Lunatic')).toBe(
      'The first enemy phase after one of your units enters the area below or turn 2 begins, whichever comes first',
    )
    expect(whenOn(group('fe12-22', 1), 'Normal')).toMatch(/^The first, third and fifth enemy phases after one of the chests at .* or turn 6 begins/)
    expect(whenOn(group('fe12-17', 1), 'Normal')).toBe('The first enemy phase after the door at (11, 8) is opened')
    expect(whenOn(group('fe12-20', 0), 'Lunatic')).toContain("(from turn 4, the script can also set them off by the foes' moves)")
    expect(whenOn(map('fe12-p6').reinforcements![0], 'Normal')).toBe('The first player phase with no foe left on the map')
  })

  it('stands a generic in for a person killed in an earlier chapter, at the start and among the reinforcements', () => {
    const standIns = (id: string) =>
      [...map(id).units, ...(map(id).reinforcements ?? []).flatMap((g) => g.units)].filter((u) => u.standIn).map((u) => [u.name, u.standIn!.name, u.standIn!.when])
    expect(standIns('fe12-8')).toContainEqual(['Jeorge', 'Sniper', 'Jeorge was killed in Chapter 5'])
    expect(standIns('fe12-9')).toContainEqual(['Astram', 'Hero', 'Astram was killed in Chapter 7 or 8'])
    expect(standIns('fe12-16')).toContainEqual(['Astram', 'Hero', 'Astram was killed in Chapter 7, 8 or 9'])
    expect(standIns('fe12-19').map((x) => x[0])).toEqual(expect.arrayContaining(['Sedgar', 'Wolf', 'Vyland']))
    // No group is left placed only for the stand-in.
    expect(map('fe12-9').reinforcements).toHaveLength(1)
    // Chapter 6's Rickard, placed only if Chapter 5 neither recruited nor killed him.
    expect(map('fe12-6').units.find((u) => u.name === 'Rickard')!.note).toContain("Placed only if Rickard wasn't recruited or killed in Chapter 5")
  })

  it("returns Chapter 10x's copies and summons the Endgame's dragons as their scripts do", () => {
    expect(whenOn(group('fe12-10x', 0), 'Normal')).toMatch(/second enemy phase after/)
    expect(whenOn(group('fe12-10x', 0), 'Hard')).toBe("Each of Roro's copies that falls comes back at its place on the next enemy phase")
    expect(whenOn(group('fe12-10x', 1), 'Normal')).toContain('come back 12 times in all')
    expect(whenOn(group('fe12-10x', 1), 'Hard')).toContain('come back 20 times in all')
    // Five summoning points; over each 20 turns, 9 summons in 4 turns on Normal and Hard (45), 12 on Maniac and up (60).
    const summons = (d: string) => map('fe12-final').reinforcements!.reduce((n, g) => n + /^Turns ([\d, and]+),/.exec(whenOn(g, d)!)![1].split(/, | and /).length, 0)
    expect(map('fe12-final').reinforcements).toHaveLength(5)
    expect(MODES.map(summons)).toEqual([45, 45, 60, 60, 60])
    expect(map('fe12-final').notes).toContain(
      "While any of Lena, Maria, Nyna or Elice is still on the enemy's side, Medeus comes back to life whenever defeated.",
    )
  })
})

describe("New Mystery of the Emblem's weapons", () => {
  it('reads who may use a weapon from the equip check', () => {
    expect(weapon('Rapier').rules).toContain('Marth only')
    expect(weapon('Wing Spear').rules).toContain('Caeda only')
    expect(weapon('Excalibur').rules).toEqual(expect.arrayContaining(['Men only', 'Merric can use it from rank E']))
    expect(weapon('Aura').rules).toEqual(expect.arrayContaining(['Women only', 'Linde can use it from rank E']))
    expect(weapon('Longbow').rules).toContain('Archers and Snipers only')
  })

  it('has no weight (nothing in battle reads it), never-wearing weapons, and its effectiveness bits', () => {
    expect(FE12_WEAPONS.every((w) => w.wt === undefined)).toBe(true)
    expect(weapon('Falchion')).toMatchObject({ uses: null, effective: ['fe12-dragons-all'] })
    expect(weapon('Wyrmslayer').effective).toEqual(['fe12-dragons'])
    expect(weapon('Swordslayer').effective).toEqual(['fe12-swordfighter'])
    expect(weapon('Swarm').rules).toContain("The foe can't counter it, it never counters, and its wielder never strikes twice with it")
    expect(weapon('Gradivus').rules).toContain("Can't be forged")
  })

  it('marks the weapons only foes carry, and lists only what something gives', () => {
    expect(FE12_LISTED.find((w) => w.name === 'Dark Breath')?.foeOnly).toBe(true)
    expect(FE12_LISTED.find((w) => w.name === 'Iron Sword')?.foeOnly).toBeUndefined()
  })
})

describe("New Mystery of the Emblem's triangle and supports", () => {
  it('reads the triangle and the rank bonuses from its database, a staff row included', () => {
    expect(FE12_TRIANGLE.beats).toEqual({ Sword: ['Axe'], Lance: ['Sword'], Axe: ['Lance'] })
    expect(FE12_TRIANGLE.advantage.A).toEqual([1, 10])
    expect(FE12_TRIANGLE.rankBonus.Staff.A).toEqual([3, 0])
  })

  it("reads the supports' numbers in the battle code", () => {
    expect(FE12_SUPPORTS).toEqual({
      reach: 3,
      slots: 5,
      levels: {
        C: { hit: 5, avoid: 5, crit: 0, critAvoid: 0 },
        B: { hit: 10, avoid: 10, crit: 0, critAvoid: 0 },
        A: { hit: 10, avoid: 10, crit: 5, critAvoid: 5 },
      },
      geosphere: 10,
    })
  })
})
