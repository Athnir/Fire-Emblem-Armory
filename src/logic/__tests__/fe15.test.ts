import { describe, expect, it } from 'vitest'
import { FE15_ITEM_SOURCES } from '../../data/fe15/fe15ItemSources'
import { FE15_LISTED } from '../../data/fe15/fe15Listed'
import { FE15_MAPS } from '../../data/fe15/fe15Maps'
import { FE15_BLOCK, FE15_STORY } from '../../data/fe15/fe15MapSet'
import { FE15_OPENS } from '../../data/fe15/fe15Opens'
import { FE15_SUPPORT_POINTS } from '../../data/fe15/fe15Supports'
import { FE15_MOVE_CLASSES, FE15_TERRAIN } from '../../data/fe15/fe15Terrain'
import { FE15_WEAPONS } from '../../data/fe15/fe15Weapons'
import type { ChapterMap, Difficulty } from '../../data/maps/types'
import { GAMES } from '../../games'
import { rowCodes } from '../maps'
import { reachOf } from '../spoiler'
import { trueHit } from '../trueHit'

const DIFFS: Difficulty[] = ['Normal', 'Hard']
const map = (id: string) => FE15_MAPS.find((m) => m.id === id)!
const on = (d: Difficulty, u: { difficulties?: Difficulty[] }) => !u.difficulties || u.difficulties.includes(d)
const weapon = (name: string) => FE15_WEAPONS.find((w) => w.name === name)!
const foes = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && on(d, u)).length

// From each battle's Fire Emblem Wiki page (its Echoes ChapData): starting foes on Normal and Hard, columns, rows.
const WIKI: Record<string, [number, number, number, number]> = {
  'fe15-1-1': [5, 6, 14, 13], 'fe15-1-2': [7, 8, 22, 20], 'fe15-1-4': [10, 11, 22, 20], 'fe15-1-5': [7, 8, 14, 20],
  'fe15-1-6': [9, 10, 22, 20], 'fe15-1-7': [6, 8, 30, 28], 'fe15-1-9': [17, 19, 22, 28],
  'fe15-2-2': [7, 8, 22, 20], 'fe15-2-3': [10, 11, 30, 20], 'fe15-2-4': [13, 14, 14, 20], 'fe15-2-6': [1, 2, 14, 20],
  'fe15-2-8': [10, 10, 22, 20], 'fe15-2-9': [7, 7, 30, 20], 'fe15-2-10': [5, 5, 22, 28],
  'fe15-3a-1': [15, 15, 30, 28], 'fe15-3a-2': [7, 10, 22, 20], 'fe15-3a-3': [3, 3, 14, 20], 'fe15-3a-4': [10, 10, 30, 20],
  'fe15-3a-5': [20, 20, 30, 28], 'fe15-3a-7': [10, 10, 30, 28], 'fe15-3a-8': [10, 10, 22, 28],
  'fe15-3c-1': [18, 18, 22, 20], 'fe15-3c-3': [16, 16, 22, 20], 'fe15-3c-4': [10, 10, 14, 20], 'fe15-3c-5': [10, 10, 14, 20],
  'fe15-3c-6': [20, 20, 30, 28], 'fe15-3c-7': [5, 9, 22, 20], 'fe15-3c-9': [10, 10, 22, 28],
  'fe15-4a-1': [20, 20, 30, 28], 'fe15-4a-2': [10, 10, 30, 28], 'fe15-4a-3': [15, 15, 30, 28], 'fe15-4a-5': [10, 10, 30, 28],
  'fe15-4a-6': [20, 20, 30, 28], 'fe15-4a-8': [20, 20, 30, 28], 'fe15-4a-10': [20, 20, 30, 26], 'fe15-4a-11': [20, 20, 22, 24],
  'fe15-4c-1': [10, 10, 22, 20], 'fe15-4c-3': [10, 10, 14, 28], 'fe15-4c-5': [20, 20, 30, 28], 'fe15-4c-6': [5, 7, 22, 20],
  'fe15-5-2': [20, 20, 30, 28],
  // The dungeons' set battles: the Brigand Boss, Berkut, the three royal chambers.
  'fe15-1-3b': [7, 7, 12, 12], 'fe15-5-1b': [11, 11, 13, 17], 'fe15-5-1c': [9, 9, 11, 11], 'fe15-5-1d': [9, 9, 11, 11],
  'fe15-5-1e': [5, 5, 11, 11],
}

/**
 * Where the wiki's headline counts units the placement file gives no tile (each checked in the map's files): those foes join the
 * battle later, so the map starts with fewer and names them in its notes.
 * - Liberation of Zofia Castle: 10 placed, plus Slayde and 6 Cavaliers (Normal) or Slayde, 6 Cavaliers and 2 Archers (Hard).
 * - Rigel Plains: 10 placed, plus Zeke's company (Zeke, 6 Paladins and 3 Bow Knights), who leave with him.
 */
const WAITING: Record<string, [number, number]> = { 'fe15-1-9': [7, 9], 'fe15-4a-6': [10, 10] }

describe("Echoes' maps", () => {
  it('has the Prologue, Acts 1-5, and Act 6 and the amiibo dungeons on the side', () => {
    expect(FE15_MAPS.filter((m) => m.route !== 'Extra')).toHaveLength(65)
    expect(FE15_MAPS.filter((m) => m.route === 'Extra').map((m) => m.id)).toEqual([
      'fe15-6-1', 'fe15-6-2', 'fe15-6-3', 'fe15-6-4a', 'fe15-6-4b', 'fe15-6-4c', 'fe15-6-4d', 'fe15-x-1', 'fe15-x-2',
    ])
    for (const m of FE15_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it('starts each battle with the foes the Fire Emblem Wiki lists, on a map its size', () => {
    for (const [id, [n, h, cols, rows]] of Object.entries(WIKI)) {
      const m = map(id)
      expect([m.width, m.height], id).toEqual([cols, rows])
      const [wn, wh] = WAITING[id] ?? [0, 0]
      expect(foes(m, 'Normal') + wn, `${id} Normal`).toBe(n)
      expect(foes(m, 'Hard') + wh, `${id} Hard`).toBe(h)
    }
    expect(map('fe15-1-9').notes[0]).toBe(
      'More foes join the battle later, with no tile of their own in the placement file: Normal: Slayde, Cavalier ×6; Hard: Slayde, ' +
        'Cavalier ×6, Archer ×2.',
    )
    expect(map('fe15-4a-6').notes[0]).toContain('Zeke, Paladin ×6, Bow Knight ×3')
  })

  it("gives every tile a terrain from the game's table, Avoid and healing only", () => {
    const codes = new Set(FE15_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE15_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE15_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
      expect(info!.def, code).toBe(0)
    }
    // Forts (and supplies, orange trees) give 40 Avoid and heal 5 HP; graves 60; castle tiles 20; Thabes' ruin takes 20.
    expect(FE15_TERRAIN.bb).toMatchObject({ avo: 40, heal: 5 })
    expect(FE15_TERRAIN.b2).toMatchObject({ avo: 60 })
    expect(FE15_TERRAIN.b0).toMatchObject({ avo: 20 })
    expect(FE15_TERRAIN.tq).toMatchObject({ avo: -20 })
    // Lava and swamps take 5 HP; the bulwark stops every mounted class.
    expect(FE15_TERRAIN.dd).toMatchObject({ heal: -5 })
    expect(FE15_TERRAIN.b1!.move.Cavalier).toBeNull()
    expect(FE15_TERRAIN.b1!.move.Knight).toBe(2)
    // Peaks and ramparts are walls to all but fliers.
    expect(Object.entries(FE15_TERRAIN.wb!.move).filter(([, v]) => v !== null).map(([k]) => k)).toEqual(['Fliers'])
    // An icon only on tiles a unit can stand on.
    for (const code of ['bb', 'ba', 'b0', 'b1', 'b2', 'b3', 'by', 'tq'] as const) {
      if (FE15_TERRAIN[code]) expect(Object.values(FE15_TERRAIN[code]!.move).some((v) => v !== null), code).toBe(true)
    }
  })

  it('places every unit inside its map', () => {
    for (const m of FE15_MAPS) {
      for (const u of [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it("reads the win rule, the lord and the scripted reinforcements", () => {
    expect(map('fe15-4a-11').victory).toBe('Defeat Rudolf')
    expect(map('fe15-2-4').victory).toMatch(/^Defeat /)
    expect(map('fe15-1-1').victory).toBe('Rout the enemy')
    expect(map('fe15-1-1').defeat).toBe('Alm is defeated')
    expect(map('fe15-2-2').defeat).toBe('Celica is defeated')
    expect(map('fe15-6-3').reinforcements!.map((g) => g.when)).toEqual([
      'Turn 2, enemy phase',
      'Turn 3, enemy phase',
      'Turn 4, enemy phase',
    ])
    // Rigel Castle on Hard is a different map: Rudolf on his throne, a second army around him.
    const rudolf = map('fe15-4a-11').units.filter((u) => u.name === 'Rudolf')
    expect(rudolf.map((u) => u.difficulties)).toEqual([['Normal'], ['Hard']])
  })

  it("shows a dungeon's formations, fixed encounters and boss battles, and a cemetery's layouts", () => {
    const shrine = map('fe15-1-3a')
    expect(shrine.reinforcements!.map((g) => g.label)).toEqual([
      'Foes ahead',
      'Foes ahead and to the left',
      'Foes ahead and to the right',
      'Foes to the left',
      'Foes to the right',
    ])
    expect(shrine.notes).toContain('Encounter: Dracul, Revenant ×4 (rare monster, 30% once rare monsters appear)')
    // Duma Tower's gatekeepers: the Fiend (8), the Necrodragon (8), the Bow Knight (10) and the Mogall (15), as the wiki gives.
    const tower = map('fe15-4c-7').reinforcements!.filter((g) => g.label.startsWith('Fixed'))
    expect(tower.map((g) => g.units.filter((u) => on('Normal', u)).length)).toEqual([8, 8, 10, 15])
    expect(map('fe15-2-1').reinforcements!.map((g) => g.label)).toEqual(['Layout 1'])
    expect(map('fe15-3c-2').reinforcements).toHaveLength(5)
  })

  it("shows the amiibo ordeals' guards as the Fire Emblem Wiki lists them, with no wandering foes", () => {
    const guards = (id: string) => map(id).reinforcements!.map((g) => g.units.map((u) => `${u.name} ${u.note?.match(/Lv \d+/)?.[0]}`))
    // Mila's Ordeals: the Bonewalker's, Witch's, Deathgoyle's and Mogall's rooms, then Mila's Servant's (Normal levels).
    const mila = guards('fe15-x-2')
    expect(mila.map((g) => g.length)).toEqual([5, 6, 5, 9, 11])
    expect(mila[3]).toEqual([
      'Mogall Lv 3', 'Mogall Lv 1', 'Mogall Lv 1', 'Necrodragon Lv 1', 'Necrodragon Lv 1', 'Necrodragon Lv 1', 'Necrodragon Lv 1',
      'Revenant Lv 20', 'Revenant Lv 20',
    ])
    // Duma's Ordeals: the Knight, Paladin, Dread Fighter, Fiend and Duma's Apostle, each with the foes the wiki names.
    expect(guards('fe15-x-1').map((g) => g[0])).toEqual(['Knight Lv 1', 'Paladin Lv 1', 'Dread Fighter Lv 1', 'Fiend Lv 5', "Duma's Apostle Lv 10"])
    for (const id of ['fe15-x-1', 'fe15-x-2']) {
      expect(map(id).randomSpawns).toBe(false)
      expect(map(id).reinforcements!.every((g) => g.label.startsWith('Fixed'))).toBe(true)
      expect(map(id).notes!.some((n) => n.includes('only the first time'))).toBe(true)
    }
  })
})

describe("Echoes' weapons", () => {
  it("reads the item table, the forge and the arts", () => {
    expect(weapon('Iron Sword')).toMatchObject({ mt: 2, hit: 90, crit: 0, wt: 0, range: '1' })
    expect(weapon('Iron Sword').forge![4]).toEqual({ silver: 100, gold: 0, mt: 6, wt: 0, hit: 20, crit: 0 })
    expect(weapon('Iron Sword').evolve).toEqual([{ into: 'Steel Sword', silver: 50, gold: 0, stars: 1 }])
    expect(weapon('Iron Sword').arts!.map((a) => [a.name, a.mastery, a.hp, a.mt])).toEqual([
      ['Wrath Strike', 10, 1, 5],
      ['Windsweep', 25, 4, 3],
    ])
    expect(weapon('Royal Sword').rules).toContain('Alm only')
    expect(weapon('Beloved Zofia').rules).toContain('Celica only')
    expect(weapon('Blessed Sword').effective).toEqual(['terror'])
    expect(weapon('Rapier').effective).toEqual(['horseback', 'armour'])
    expect(weapon('Shadow Sword').stats).toEqual({ lck: -10 })
    // A Rusted Sword is one of six weapons, fixed when it's made.
    expect(weapon('Rusted Sword').evolve!.map((e) => e.into)).toEqual([
      'Iron Sword', 'Steel Sword', 'Shadow Sword', 'Brave Sword', 'Astra', 'Venin Sword',
    ])
    // The Sage's Shield's arts name skills the table doesn't have (the game's own typo, kept).
    expect(weapon("Sage's Shield").arts!.every((a) => a.name === null)).toBe(true)
  })

  it("adds the DLC's weapons from Fire Emblem Wiki, with the game's own numbers for the arts the base game also has", () => {
    const dlc = FE15_LISTED.filter((w) => w.dlc).map((w) => w.name)
    expect(dlc).toEqual([
      "Fernand's Lance", "Clair's Lance", "Clive's Lance", "Trainee's Lance", 'Wayward Lance', "Python's Bow", "Warrior's Sword",
      "Lukas's Shield",
    ])
    // The wiki's worth at a star is the mark value plus every star's cost so far; its stats are the totals.
    const clive = weapon("Clive's Lance")
    expect(clive.markValue).toEqual({ silver: 30, gold: 0 })
    expect(clive.forge![0]).toEqual({ silver: 50, gold: 0, mt: 1, wt: 0, hit: 0, crit: 0 })
    expect(clive.forge![5]).toEqual({ silver: 0, gold: 3, mt: 8, wt: 0, hit: 10, crit: 0 })
    // Armorcrush is the cartridge's (Skill.bin: effective against armour); Heaven or Hell is DLC-only (the wiki's).
    expect(clive.arts!.find((a) => a.name === 'Armorcrush')).toMatchObject({ mastery: 15, hp: 4, effective: ['armour'] })
    expect(weapon('Wayward Lance').arts).toEqual([expect.objectContaining({ name: 'Heaven or Hell', strikes: 2, hit: -30, crit: 30 })])
    expect(weapon("Clair's Lance")).toMatchObject({ effective: ['terror'], stats: { res: 5 } })
    // Each turns up only with the DLC switch, from Act 1 (the world map's Connect menu).
    for (const name of dlc) {
      expect(FE15_ITEM_SOURCES[name].every((s) => s.kind === 'dlc-reward' && s.mapId === 'fe15-1-1')).toBe(true)
    }
    // Held by Clair only during Flight from the Ruins: never the player's.
    expect(FE15_WEAPONS.some((w) => w.name === 'Ancient Ring')).toBe(false)
  })

  it('lists where each weapon turns up', () => {
    expect(FE15_ITEM_SOURCES['Iron Sword']).toContainEqual({ mapId: 'fe15-1-3a', kind: 'chest', text: "In a chest in Thieves' Shrine" })
    expect(FE15_ITEM_SOURCES['Golden Dagger']).toEqual([{ mapId: 'fe15-2-1', kind: 'kit', text: 'Carried by Celica when they join' }])
    expect(FE15_ITEM_SOURCES['Ridersbane']).toContainEqual({ mapId: 'fe15-1-9', kind: 'gift-later', text: 'Given in Zofia Castle' })
    expect(FE15_ITEM_SOURCES['Dracoshield']).toContainEqual({ mapId: 'fe15-1-9', kind: 'drop', text: 'Dropped by Desaix' })
    // The legendary weapons come from Rusted items, evolved at a blacksmith (the first: the Forest Village's, Act 3).
    expect(FE15_ITEM_SOURCES['Astra'].every((s) => s.kind === 'evolve-later')).toBe(true)
    expect(FE15_ITEM_SOURCES['Mila\'s Bow']).toEqual([{ mapId: 'fe15-x-2', kind: 'amiibo-gift', text: "Given in Mila's Ordeals" }])
    // A person's random drop rate is a percentage as stored (Fire Emblem Wiki: a Bonewalker's Rusted Sword 0.09%, a Witch's 0.01%
    // as a type-2 specter or 0.04%).
    const rusted = FE15_ITEM_SOURCES['Rusted Sword'].map((s) => s.text)
    expect(rusted).toContain("Sometimes dropped by Bonewalkers in Mila's Ordeals (0.09%)")
    expect(rusted).toContain("Sometimes dropped by Witches in Mila's Ordeals (0.01% or 0.04%)")
    // Foe-only: the monsters' own weapons and Berkut's Kriemhild.
    const foeOnly = FE15_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toContain('Claws')
    expect(foeOnly).toContain('Kriemhild')
    expect(foeOnly).not.toContain('Iron Sword')
    // The 7-Eleven quest's Seven Sword and Eleven Shield (a Japanese promotion) are left out.
    expect(FE15_ITEM_SOURCES['Seven Sword']).toBeUndefined()
  })

  it('opens Act 6 once the Final Battle is won', () => {
    expect(FE15_OPENS['fe15-6-1']).toBe('fe15-5-2')
    const at = (id: string) => FE15_BLOCK.maps.findIndex((m) => m.id === id)
    expect(reachOf(FE15_BLOCK, at('fe15-5-2')).has('fe15-6-1')).toBe(false)
    expect(FE15_STORY.short(map('fe15-3a-2'))).toBe('A3A-2')
    expect(FE15_STORY.name(map('fe15-0-1'))).toBe('Prologue')
  })
})

describe("Echoes' battle numbers", () => {
  it('rolls hit as Fates does (0x30c7d8: one 0-9999 number against the hit, curved from 50 up)', () => {
    expect(GAMES.find((g) => g.id === 'fe15')!.hitSystem).toBe('hybrid-fates')
    expect(trueHit('hybrid-fates', 30).trueHitBasisPoints).toBe(3000)
  })

  it("reads the support points from the game's tuning values", () => {
    expect(FE15_SUPPORT_POINTS).toEqual({ deployed: 1, distance: [1, 1, 0, 0], staff: 2, perBattle: 20 })
  })

  it('has no difficulty but Normal and Hard', () => {
    for (const m of FE15_MAPS)
      for (const u of m.units) for (const d of u.difficulties ?? []) expect(DIFFS.includes(d), `${m.id} ${u.name}`).toBe(true)
  })
})
