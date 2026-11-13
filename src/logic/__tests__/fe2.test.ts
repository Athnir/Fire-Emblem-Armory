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
