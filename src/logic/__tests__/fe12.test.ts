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
