import { describe, expect, it } from 'vitest'
import { FE2_ITEM_SOURCES } from '../../data/fe2/fe2ItemSources'
import { FE2_LISTED } from '../../data/fe2/fe2Listed'
import { FE2_MAPS } from '../../data/fe2/fe2Maps'
import { FE2_BLOCK, FE2_MAP_SET } from '../../data/fe2/fe2MapSet'
import { FE2_TERRAIN } from '../../data/fe2/fe2Terrain'
import { FE2_WEAPONS } from '../../data/fe2/fe2Weapons'
import { GAMES, MISSING_GAMES } from '../../games'
import { trueHit } from '../trueHit'

const map = (id: string) => FE2_MAPS.find((m) => m.id === id)!
const weapon = (name: string) => FE2_WEAPONS.find((w) => w.name === name)!
const count = (id: string) =>
  map(id).units.reduce<Record<string, number>>((n, u) => ({ ...n, [u.name]: (n[u.name] ?? 0) + 1 }), {})

/**
 * Serenes Forest's Gaiden tables (inventory: swords, lances, bows, miscellaneous): [its name, Mt, Hit, Crit, range, Wt], each row
 * matched to the item by the Japanese name it gives (the app names them as Shadows of Valentia does). Where the cartridge differs, the
 * game wins: the Falchion's Hit is 100 in its table (Serenes: 80); the Lightning Sword's damage is its 15 less the foe's Res (9:$826C;
 * Serenes: "always does 15 damage", no Mt); the Tentacle is Mt 12, Hit 80 and reaches only the foe beside it (Serenes: 10, 90, 1-8).
 */
const SERENES: Record<string, [string, number | null, number, number, string, number]> = {
  'Steel Sword': ['Steel Sword', 4, 80, 0, '1', 1],
  'Silver Sword': ['Silver Sword', 8, 90, 0, '1', 1],
  'Brave Sword': ['Hero Sword', 5, 100, 30, '1', 0],
  'Shadow Sword': ['Darkness Sword', 13, 70, 0, '1', 5],
  'Lightning Sword': ['Thunder Sword', null, 80, 0, '1-2', 3],
  'Blessed Sword': ['Holy Sword', 3, 100, 15, '1', 0],
  'Royal Sword': ['Royal Sword', 7, 100, 20, '1', 0],
  Falchion: ['Falchion', 10, 80, 0, '1', 0],
  'Steel Lance': ['Steel Lance', 4, 80, 0, '1', 1],
  'Silver Lance': ['Silver Lance', 8, 90, 0, '1', 1],
  Javelin: ['Javelin', 3, 70, 0, '1-2', 2],
  Ridersbane: ['Knight Killer', 3, 85, 0, '1', 1],
  'Blessed Lance': ['Holy Lance', 3, 90, 10, '1', 0],
  Gradivus: ['Gradius', 15, 100, 0, '1-2', 0],
  Astra: ['Shooting Star', 10, 100, 50, '1', 0],
  Luna: ['Moonlight', 10, 100, 0, '1', 1],
  Sol: ['Sun', 20, 80, 0, '1', 2],
  'Steel Bow': ['Steel Bow', 3, 70, 0, '1-5', 1],
  'Silver Bow': ['Silver Bow', 7, 80, 0, '1-5', 2],
  'Blessed Bow': ['Holy Bow', 5, 100, 10, '1-5', 0],
  Tentacle: ['Tentacle', 10, 90, 0, '1-8', 0],
}

describe('Gaiden in the app', () => {
  it('is in the picker as the 2nd game, no longer a placeholder', () => {
    expect(GAMES.find((g) => g.id === 'fe2')).toMatchObject({ number: 2, hitSystem: '1rn-byte-below' })
    expect(MISSING_GAMES.some((g) => g.number === 2)).toBe(false)
  })

  it('rolls hit as its code does: (100 × a random byte) >> 8, a hit when below the displayed hit', () => {
    const at = (h: number) => trueHit('1rn-byte-below', h).trueHitBasisPoints
    // ceil(2.56 h) of 256.
    expect([0, 1, 50, 80, 99, 100].map(at)).toEqual([0, 117, 5000, 8008, 9922, 10000])
  })
})

describe("Gaiden's weapons against Serenes Forest's tables", () => {
  it('has every weapon of the tables, with their numbers but where the cartridge differs', () => {
    for (const [name, [, mt, hit, crit, range, wt]] of Object.entries(SERENES)) {
      const w = weapon(name)
      const want = { mt, hit, crit, range, wt }
      if (name === 'Falchion') want.hit = 100
      if (name === 'Lightning Sword') want.mt = 15
      if (name === 'Tentacle') Object.assign(want, { mt: 12, hit: 80, range: '1' })
      expect({ mt: w.mt, hit: w.hit, crit: w.crit, range: w.range, wt: w.wt }, name).toEqual(want)
    }
    // Serenes Forest's items: the shields' Def, the rings and shields that heal (the turn's start, 3:$9185: any item of special 10;
    // the Gradivus too, which Serenes leaves out).
    expect(weapon('Leather Shield').rules).toContain('Def +3 against weapons')
    expect(weapon('Steel Shield').rules).toContain('Def +5 against weapons')
    expect(weapon('Silver Shield').rules).toContain('Def +7 against weapons')
    expect(weapon('Dracoshield').rules).toContain('Def +13 against weapons, Res +13 against spells and the Lightning Sword')
    expect(weapon('Hexlock Shield').rules).toContain("A spell's hit against its holder is 10")
    const heals = FE2_WEAPONS.filter((w) => w.rules?.includes('Its holder recovers 5 HP at the start of each turn')).map((w) => w.name)
    expect(heals.sort()).toEqual(
      ['Blessed Lance', 'Gradivus', 'Astra', 'Sol', 'Luna', 'Blessed Sword', 'Falchion', 'Royal Sword', 'Blessed Bow', 'Blessed Shield',
        'Dracoshield', 'Blessed Ring', 'Angel Ring', 'Speed Ring', 'Mage Ring', 'Prayer Ring'].sort(),
    )
  })

  it('reads who may use them, and their effectiveness, from the code', () => {
    expect(weapon('Falchion').rules).toContain('Alm only')
    expect(weapon('Royal Sword').rules).toContain('Alm only')
    expect(weapon('Javelin').rules).toContain("Soldiers can't use it")
    expect(weapon('Ridersbane').effective).toEqual(['fe2-mounted'])
    expect(weapon('Steel Bow').effective).toEqual(['fe2-fliers'])
    expect(weapon('Blessed Bow').effective).toEqual(['fe2-monsters'])
  })

  it('lists what something gives: chests, drops, recruits; Duma\'s Tentacle as his alone', () => {
    const where = (name: string) => FE2_ITEM_SOURCES[name].map((s) => s.text)
    expect(where('Lightning Sword')).toContain('In a chest at S. Fort')
    expect(where('Royal Sword')).toContain("In a chest at Tozeh's Fort")
    expect(where('Dracoshield')).toContain('Dropped by Desaix')
    expect(where('Brave Sword')).toContain('Carried by Deen on joining')
    // Astra, Sol and Luna only drop at random from monsters holding nothing (15:$F225).
    for (const name of ['Astra', 'Sol', 'Luna']) expect(where(name).every((t) => t.startsWith('Sometimes dropped by')), name).toBe(true)
    expect(FE2_LISTED.find((w) => w.name === 'Tentacle')?.foeOnly).toBe(true)
    expect(FE2_LISTED.find((w) => w.name === 'Falchion')?.foeOnly).toBeUndefined()
  })
})

describe("Gaiden's battles", () => {
  it('has each chapter\'s battles by army, then the battle with Duma; the encounters a list of their own', () => {
    const story = FE2_BLOCK.maps.map((m) => m.id)
    expect(story.filter((id) => id.startsWith('fe2-1-'))).toHaveLength(7)
    expect(story.filter((id) => id.startsWith('fe2-3a-'))).toHaveLength(7)
    expect(story.filter((id) => id.startsWith('fe2-3c-'))).toHaveLength(8)
    expect(story.at(-1)).toBe('fe2-5-1')
    expect(FE2_MAP_SET.third!.maps.every((m) => m.heading === 'Dungeons' && m.id.startsWith('fe2-d'))).toBe(true)
  })

  it("places Sofia Gate's two armies as Fire Emblem Wiki lists them, and says who leaves when the other falls", () => {
    expect(count('fe2-1-7')).toEqual({ Slayde: 1, Desaix: 1, Arcanist: 1, Knight: 1, Archer: 5, Soldier: 2, Cavalier: 6 })
    expect(map('fe2-1-7').units.find((u) => u.name === 'Desaix')!.drops).toEqual(['Dracoshield'])
    expect(map('fe2-1-7').notes).toContain('When Slayde falls, Desaix leaves the battle (15:$F20C).')
    expect(map('fe2-2-4').notes).toContain('When Barth falls, the Brigands leave the battle (15:$F20C).')
    expect(map('fe2-4a-8').victory).toBe('Defeat Rudolf')
  })

  it("gives its forts and swamps the turn's healing and damage, in HP", () => {
    expect(FE2_TERRAIN.bb).toMatchObject({ name: 'Fort', avo: 40, heal: 5 })
    expect(FE2_TERRAIN.df).toMatchObject({ name: 'Swamp', heal: -5 })
    expect(FE2_TERRAIN.b2).toMatchObject({ name: 'Grave', avo: 60 })
  })
})

describe("Gaiden's maps drawn as the game draws them (scripts/fe2_art.py)", () => {
  const codes = (id: string) => FE2_MAPS.find((m) => m.id === id)!.grid.flatMap((r) => r.match(/../g) ?? [])
  const all = new Set(FE2_MAPS.flatMap((m) => m.grid.flatMap((r) => r.match(/../g) ?? [])))
  it("gives each map its own colours, its walls by what they are, a brown map's plains as dirt and its small castles whole", () => {
    for (const c of ['t0', 'ga', 'wt', 'wy', 'w9', 'qa', 'qh']) expect(all.has(c), c).toBe(true)
    for (const c of ['ta', 'wa']) expect(all.has(c), c).toBe(false)
    // The caves' plains are bare earth; the open fields' grass.
    expect(codes('fe2-d0').includes('ga')).toBe(true)
    expect(codes('fe2-d0').includes('t0')).toBe(false)
    expect(codes('fe2-1-2').includes('ga')).toBe(false)
    expect(FE2_TERRAIN.ga!.move).toEqual(FE2_TERRAIN.t0!.move)
    // Chapter 1's second battle: two forts in the open, each drawn whole round its fort and stairs (a stone fort's pieces, `q`).
    expect(codes('fe2-1-2').filter((c) => /^q[a-i]$/.test(c)).length).toBe(14)
    for (const m of FE2_MAPS) expect(m.fills, m.id).toBeDefined()
    expect(FE2_MAPS.find((m) => m.id === 'fe2-d20')!.fills!.t0).toBe('#7bbcff') // the Dragon Tower's plain is sky, as the game draws it
  })

  // The first three games' review (2026-11-13): tiles drawn as what they are though the game codes them as plain, floor or castle.
  const at = (id: string, x: number, y: number) => { const m = map(id); return m.grid[m.height - y].slice(2 * (x - 1), 2 * x) }
  it('draws its stone bridges, gangplanks, decks and masts as themselves, with the stats of what the game codes them as', () => {
    expect(at('fe2-1-6', 17, 15)).toBe('t8')
    for (const y of [11, 12, 13, 14, 15, 16]) expect(at('fe2-3c-1', 20, y)).toBe('t8')
    expect(at('fe2-3c-1', 11, 8)).toBe('t8') // a bridge two tiles tall: its deck, and its side under it (a wall: drawn as the side)
    expect(at('fe2-3c-1', 11, 7)).toBe('wx')
    expect(map('fe2-3c-1').decor?.['11,7']).toBe('bridge')
    expect(at('fe2-2-2', 12, 11)).toBe('tb') // the gangplank between two ships
    expect(at('fe2-2-2', 11, 8)).toBe('w4') // a mast's foot on a deck (the user: not a barrel)
    // A two-wide stone bridge's halves and its ends on the bank (the user's second look).
    for (const [x, y] of [[8, 7], [9, 7], [8, 18], [12, 12]] as const) expect(at(x === 12 ? 'fe2-4a-8' : 'fe2-3a-7', x, y)).toBe('t8')
    expect(codes('fe2-2-2').includes('t3')).toBe(true)
    // Plain and floor play alike, so a bridge over either is one terrain; a mast is a castle tile, which only fliers cross.
    expect(FE2_TERRAIN.t8!.move).toEqual(FE2_TERRAIN.t0!.move)
    expect(FE2_TERRAIN.t3!.move).toEqual(FE2_TERRAIN.t0!.move)
    expect(FE2_TERRAIN.w4!.move).toEqual(FE2_TERRAIN.wx!.move)
  })
  it("draws the mountains its art shows as a rocky shore or a ship's raised deck as those, with a mountain's numbers", () => {
    for (const x of [1, 4, 7, 10, 12]) expect(at('fe2-3a-7', x, 7)).toBe('na')
    expect(at('fe2-4c-4', 11, 8)).toBe('na')
    for (const [x, y] of [[19, 8], [21, 14], [21, 15]] as const) expect(at('fe2-2-2', x, y)).toBe('nb')
    for (const code of ['na', 'nb'] as const) {
      expect(FE2_TERRAIN[code]!.move).toEqual(FE2_TERRAIN.bm!.move)
      expect(FE2_TERRAIN[code]!.avo).toBe(FE2_TERRAIN.bm!.avo)
    }
  })
  it('puts your army on its second list of tiles only where the first is too short for it (8:$9E33)', () => {
    // Act 4's fortress: twenty tiles on the first list, so none on the second (the user: tiles on its walls).
    expect(map('fe2-4a-7').starts).toHaveLength(20)
    expect(map('fe2-4a-7').starts.some(([x]) => x >= 26)).toBe(false)
  })
  it("draws a door nothing opens on its wall, and a small castle whole only where it stands in the open", () => {
    expect(at('fe2-3c-8', 13, 21)).toBe('w0')
    expect(map('fe2-3c-8').decor?.['13,21']).toBe('door')
    expect(map('fe2-4c-4').decor?.['9,16']).toBe('door')
    // Walls inside a castle or a dungeon stay walls; the fort of four corner walls round a cross of floor (Act 4) is drawn whole.
    for (const id of ['fe2-1-7', 'fe2-d23', 'fe2-4a-8']) expect(codes(id).some((c) => /^[cq][a-i]$/.test(c)), id).toBe(false)
    expect([at('fe2-4a-3', 23, 12), at('fe2-4a-3', 25, 12), at('fe2-4a-3', 23, 10), at('fe2-4a-3', 25, 10)]).toEqual(['qa', 'qc', 'qg', 'qi'])
    expect(at('fe2-4a-3', 24, 11)).toBe('bb')
  })
})
