import { describe, expect, it } from 'vitest'
import { FE15_ITEM_SOURCES } from '../../data/fe15/fe15ItemSources'
import { FE15_LISTED } from '../../data/fe15/fe15Listed'
import { FE15_MAPS } from '../../data/fe15/fe15Maps'
import { FE15_BLOCK, FE15_MAP_SET, FE15_STORY } from '../../data/fe15/fe15MapSet'
import { FE15_OPENS } from '../../data/fe15/fe15Opens'
import { FE15_SUPPORT_POINTS } from '../../data/fe15/fe15Supports'
import { FE15_MOVE_CLASSES, FE15_TERRAIN } from '../../data/fe15/fe15Terrain'
import { FE15_WEAPONS } from '../../data/fe15/fe15Weapons'
import type { ChapterMap, Difficulty } from '../../data/maps/types'
import { GAMES } from '../../games'
import { atStart, notesOn, rowCodes } from '../maps'
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


describe("Echoes' maps", () => {
  it('lists the story, the optional battles and the skirmishes, Act 4 in an order the game lets you play', () => {
    // The battles you can leave unfought, Act 6 and the amiibo ordeals; the dungeons' wandering foes' fields (the user's calls).
    expect(FE15_MAP_SET.extras!.maps.map((m) => m.id)).toEqual([
      'fe15-1-3b', 'fe15-2-6', 'fe15-3c-5', 'fe15-4a-3', 'fe15-4a-4d', 'fe15-4a-5', 'fe15-6-1', 'fe15-6-2', 'fe15-6-3', 'fe15-6-4c',
      'fe15-6-4d', 'fe15-x-1', 'fe15-x-2',
    ])
    expect(FE15_MAP_SET.third!.maps.every((m) => m.title.includes('skirmishes'))).toBe(true)
    expect(FE15_MAP_SET.third!.maps).toHaveLength(19)
    expect(FE15_BLOCK.maps).toHaveLength(FE15_MAPS.length - 32)
    // Alm reaching the Dragon's Maw before Duma Tower is cleared shuts the road on (GMAP's IsMoveAfterDra), so Celica's Act 4 comes
    // between his Dragon's Maw and Rigel Falls.
    const story = FE15_BLOCK.maps.map((m) => m.id)
    expect(story.slice(story.indexOf('fe15-4a-7'), story.indexOf('fe15-4a-8') + 1)).toEqual([
      'fe15-4a-7', 'fe15-4c-1', 'fe15-4c-2', 'fe15-4c-3', 'fe15-4c-5', 'fe15-4c-6', 'fe15-4a-8',
    ])
    // The two deserts: one is fought, the other army withdraws.
    expect(map('fe15-3c-5').notes[0]).toMatch(/^You fight this battle or the Northern Desert Battle, not both/)
    for (const m of FE15_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it('starts each battle with the foes the Fire Emblem Wiki lists, on a map its size', () => {
    for (const [id, [n, h, cols, rows]] of Object.entries(WIKI)) {
      const m = map(id)
      expect([m.width, m.height], id).toEqual([cols, rows])
      expect(foes(m, 'Normal'), `${id} Normal`).toBe(n)
      expect(foes(m, 'Hard'), `${id} Hard`).toBe(h)
    }
  })

  it("starts Zofia Castle and Rigel Plains with both of their armies, the second on the Enemy group's empty records", () => {
    // Data/Chapter.bin: each node holds an Enemy and a Reinforce army from the start; Rigel Plains' turn-1 handler reads Zeke's
    // company on those very tiles.
    const named = (id: string) => map(id).units.filter((u) => u.type !== 'enemy').map((u) => u.name)
    expect(named('fe15-1-9')).toEqual(expect.arrayContaining(['Desaix', 'Slayde']))
    // Both are the game's bosses here (the user's call): each withdraws when the other falls.
    expect([...new Set(map('fe15-1-9').units.filter((u) => u.type === 'boss').map((u) => u.name))]).toEqual(['Desaix', 'Slayde'])
    expect(map('fe15-1-9').notes[0]).toMatch(/^Once Desaix falls, Slayde withdraws/)
    expect(named('fe15-4a-6')).toContain('Zeke')
    expect(map('fe15-4a-6').notes[0]).toMatch(/Zeke and his company .* turn green at the start of turn 1/)
  })

  it('marks the units the game places itself, the lords, and no empty record as a unit', () => {
    for (const m of FE15_MAPS) expect(m.units.every((u) => u.name), m.id).toBe(true)
    expect(map('fe15-3a-4').units.filter((u) => u.type === 'ally').map((u) => u.name)).toEqual(['Mathilda'])
    expect(map('fe15-0-1').forced!.map((f) => f.name)).toEqual(['Alm', 'Celica', 'Gray', 'Tobin', 'Kliff', 'Faye', 'Mycen'])
    expect(map('fe15-2-10').forced).toEqual([{ name: 'Saber', tile: [17, 3] }])
    expect(map('fe15-5-2').forced).toEqual([{ name: 'Celica', tile: [27, 3] }])
    expect(map('fe15-5-1e').corrinStart).toEqual([6, 3])
    // Once the armies meet, losing either lord loses (both carry the protagonist's skill the defeat check reads).
    for (const m of FE15_MAPS.filter((x) => x.heading === 'Act 5' || x.heading === 'Act 6')) expect(m.defeat, m.id).toBe('Alm or Celica is defeated')
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
    expect(notesOn(shrine, 'Normal')).toContain('Encounter: Dracul, Revenant ×4 (rare monster, 30% once rare monsters appear)')
    // Duma Tower's gatekeepers: the Fiend (8), the Necrodragon (8), the Bow Knight (10) and the Mogall (15), as the wiki gives.
    const tower = map('fe15-4c-7').reinforcements!.filter((g) => g.label.startsWith('Fixed'))
    expect(tower.map((g) => g.units.filter((u) => on('Normal', u)).length)).toEqual([8, 8, 10, 15])
    expect(map('fe15-2-1r').reinforcements!.map((g) => g.label)).toEqual(['Layout 1'])
    expect(map('fe15-3c-2r').reinforcements).toHaveLength(7)
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
    // The game names six copies Rusted Sword, each evolving into its own weapon: an entry each, named by what it becomes.
    const rusted = FE15_WEAPONS.filter((w) => w.name.startsWith('Rusted Sword'))
    expect(rusted.map((w) => [w.name, w.evolve!.map((e) => e.into)])).toEqual(
      ['Iron Sword', 'Steel Sword', 'Shadow Sword', 'Brave Sword', 'Astra', 'Venin Sword'].map((into) => [`Rusted Sword (${into})`, [into]]),
    )
    // The Rusted Axe is the only copy of its name.
    expect(weapon('Rusted Axe').evolve!.map((e) => e.into)).toEqual(['Devil Axe'])
    // What a weapon's skills do is the program's, not the help text's (Echoes has no Magic stat).
    expect(weapon('Lightning Sword').rules).toEqual([
      "Transmute: Its attacks are against the foe's Resistance instead of Defense.",
      "Fixed Power: Its attack is its Mt alone, without the wielder's Strength.",
    ])
    expect(weapon('Ladyblade').rules).toEqual(['Lethal Lady: Its Mt counts twice when a woman wields it.'])
    expect(weapon('Grimoire Ring').rules).toEqual(['Magic +5: Mt +5 for black magic.'])
    expect(weapon('Devil Axe').rules![0]).toMatch(/^Hex: Each hit that lands has a \(41 - Luck\) ÷ 2 % chance to strike the wielder instead/)
    expect(weapon('Falchion').rules).toContain(
      "Deicide: Once Duma's HP is 52 or less, only a weapon with Deicide (or Nosferatu) damages him; above 52, no hit can take him below 1 HP.",
    )
    expect(weapon('Demon Ring').rules![0]).toMatch(/^Reconstruct: At each level-up, .* Resistance keeps its own\.$/)
    // The equip check's royal-blood flag with its gender flags.
    expect(weapon('Beloved Zofia').rules![0]).toBe('Celica only')
    // An art's nearest reach and its magic flag; a word broken at a line end is joined again.
    const art = (w: string, name: string) => weapon(w).arts!.find((a) => a.name === name)!
    expect(art('Lightning Sword', 'Thunderclap')).toMatchObject({ range: 1, minRange: 2 })
    expect(art('Ladyblade', 'Hexblade').magic).toBe(true)
    expect(art('Steel Sword', 'Crosswise Cut').effect).toBe('A highly accurate cross-strike.')
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
    expect(FE15_ITEM_SOURCES['Rusted Sword (Shadow Sword)'].map((s) => s.text)).toContain(
      "Sometimes dropped by Bonewalkers in Mila's Ordeals (0.09%)",
    )
    expect(FE15_ITEM_SOURCES['Rusted Sword (Brave Sword)'].map((s) => s.text)).toContain(
      "Sometimes dropped by Witches in Mila's Ordeals (0.01% or 0.04%)",
    )
    // A rate that differs by difficulty is a line per difficulty: Dragon Shrine's Revenants drop a Rusted Shield 0.25% of the time
    // on Normal and 0.5% on Hard.
    const shrine = FE15_ITEM_SOURCES['Rusted Shield (Steel Shield)'].filter((s) =>
      s.text.startsWith('Sometimes dropped by Revenants in Dragon Shrine'),
    )
    expect(shrine.map((s) => [s.text, s.difficulties])).toEqual([
      ['Sometimes dropped by Revenants in Dragon Shrine (0.25%)', ['Normal']],
      ['Sometimes dropped by Revenants in Dragon Shrine (0.5%)', ['Hard']],
    ])
    // Foe-only: the monsters' own weapons and Berkut's Kriemhild.
    const foeOnly = FE15_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toContain('Claws')
    expect(foeOnly).toContain('Kriemhild')
    expect(foeOnly).not.toContain('Iron Sword')
    // The 7-Eleven quest's Seven Sword and Eleven Shield (a Japanese promotion) are left out.
    expect(FE15_ITEM_SOURCES['Seven Sword']).toBeUndefined()
  })

  it('counts only what reaches your army, from the army that holds it', () => {
    // The Last Bastion's setting hands its foes Steel Lances (ItemGainSilent on units found by their tiles): not a gift of yours.
    expect(FE15_ITEM_SOURCES['Steel Lance'].some((s) => s.mapId === 'fe15-4a-10')).toBe(false)
    // Conrad joins in Dolth Keep's closing scene (JoinUnit), with his Blessed Lance from the next map.
    expect(FE15_ITEM_SOURCES['Blessed Lance']).toContainEqual({ mapId: 'fe15-4c-3', kind: 'kit-later', text: 'Carried by Conrad when they join' })
    // The Rusted Axe only foes carry (its record doesn't drop it), so nothing evolves into the Devil Axe: it's foe-only.
    const foeOnly = FE15_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toEqual(expect.arrayContaining(['Rusted Axe', 'Devil Axe']))
    expect(FE15_ITEM_SOURCES['Devil Axe'].some((s) => s.kind.startsWith('evolve'))).toBe(false)
    // The armies keep their own convoys until Act 5: Celica's Golden Dagger evolves at her first blacksmith (the Mountain Village).
    expect(FE15_ITEM_SOURCES['Beloved Zofia']).toEqual([expect.objectContaining({ mapId: 'fe15-3c-2', kind: 'evolve-later' })])
    // A request's gift says what it takes.
    const gift = (name: string) => FE15_ITEM_SOURCES[name].find((s) => s.kind.startsWith('gift'))!.text
    expect(gift('Coral Ring')).toBe("Given in Desaix's Fortress Interior for 30 silver marks")
    expect(gift('Grimoire Ring')).toBe("Given in Sage's Hamlet for 3 Gargoyle Ears")
    expect(gift('Dracoshield')).toBe("Given in Rigelian Village for 4 Dragon Scales, ready 4 world map turns after they're handed over")
  })

  it("puts a dungeon battle's foes and rewards on that battle's map", () => {
    // Fear Mountain Shrine's statue of Duma: its own battle, whose win gives Duma's Lance.
    expect(map('fe15-4a-4d').title).toBe('Fear Mountain Shrine: Statue of Duma')
    expect(map('fe15-4a-4d').units.some((u) => u.name === "Duma's Apostle")).toBe(true)
    expect(FE15_ITEM_SOURCES["Duma's Lance"]).toEqual([
      { mapId: 'fe15-4a-4d', kind: 'gift', text: "Given for winning the statue of Duma's battle in Fear Mountain Shrine" },
    ])
    expect(FE15_ITEM_SOURCES['Kriemhild'].map((s) => s.mapId)).toEqual(['fe15-5-1b'])
    expect(FE15_ITEM_SOURCES['Expiration'].map((s) => s.mapId)).toEqual(['fe15-6-4d'])
  })

  it('opens Act 6 with the Final Battle, and each other map with the first story map after it', () => {
    expect(FE15_OPENS['fe15-6-1']).toBe('fe15-5-2')
    const at = (id: string) => FE15_BLOCK.maps.findIndex((m) => m.id === id)
    // The Final Battle is the story's last chapter: there, the story is over and Act 6 is open (as other games' side maps are).
    expect(reachOf(FE15_BLOCK, at('fe15-5-2')).has('fe15-6-1')).toBe(true)
    expect(reachOf(FE15_BLOCK, at('fe15-5-1b')).has('fe15-6-1')).toBe(false)
    expect(map('fe15-6-1').notes[0]).toMatch(/foreign trading ship at Zofia Harbor/)
    // Thieves' Shrine, beside Fleecer's Forest: open from Ram Valley.
    expect(reachOf(FE15_BLOCK, at('fe15-1-2')).has('fe15-1-3a')).toBe(false)
    expect(reachOf(FE15_BLOCK, at('fe15-1-4')).has('fe15-1-3a')).toBe(true)
    expect(FE15_STORY.short(map('fe15-3a-2'))).toBe('A3A-2')
    expect(FE15_STORY.name(map('fe15-0-1'))).toBe('Prologue')
  })
})

describe("Echoes' skirmishes and cemeteries", () => {
  it('keeps the formations, fixed encounters and layouts under the spoiler block: they are how those battles start', () => {
    for (const id of ['fe15-1-3a', 'fe15-x-1', 'fe15-3c-2r']) expect(atStart(map(id)).reinforcements?.length, id).toBeGreaterThan(0)
    // An ordinary battle's arrivals still go.
    expect(atStart(map('fe15-6-3')).reinforcements).toBeUndefined()
  })

  it("puts a cemetery's first layout on its first battle and the layouts that gather again in the skirmishes", () => {
    // Novis Cemetery: Group1 fills the Enemy group's 9 empty records, 7 Revenants on Normal and 9 on Hard (Data/Chapter.bin's 配置).
    expect(foes(map('fe15-2-1'), 'Normal')).toBe(7)
    expect(foes(map('fe15-2-1'), 'Hard')).toBe(9)
    expect(map('fe15-2-1r').reinforcements!.map((g) => g.when)).toEqual(['Can gather here after a battle (the game gives it a figure of 100)'])
    // The mountain graveyard: five layouts by their figures, and two Revenants a villager's request can put there.
    expect(map('fe15-3c-2r').reinforcements!.map((g) => g.label)).toEqual([
      'Layout 1', 'Layout 2', 'Layout 3', 'Layout 4', 'Layout 5', 'Request foe 1', 'Request foe 2',
    ])
    // The swamp graveyard opens with Group5's Necrodragons.
    expect(map('fe15-4c-2').units.every((u) => u.name === 'Necrodragon')).toBe(true)
    // The Dragon's Maw: each win raises the army inside a level, and the next battle brings 7, 10, 13, 16 or 20 Necrodragons.
    expect(map('fe15-4a-7r').reinforcements!.map((g) => g.units.length)).toEqual([7, 10, 13, 16, 20])
  })

  it("says each encounter on the difficulties it holds on, from the act it turns up in", () => {
    for (const m of FE15_MAPS) expect([...m.notes, ...(m.notesOn ?? []).map((n) => n.note)].some((n) => /^Encounter: .*Normal: /.test(n)), m.id).toBe(false)
    const hideout = map('fe15-1-8')
    // A request's foes, and the shared group's pick (Skeleton 10 against an empty pick's 40: 20%).
    expect(notesOn(hideout, 'Normal')).toContain("Encounter: Entombed, Revenant ×3 (placed while a villager's request is open)")
    expect(notesOn(hideout, 'Normal')).toContain('Encounter: Bonewalker ×3, Revenant ×2 (20% chance to be there)')
    // The Titans come from Act 3: under the spoiler block their line waits for it.
    const titan = (has: (id: string) => boolean) => notesOn(hideout, 'Normal', has).some((n) => n.includes('Titan'))
    expect(titan(() => false)).toBe(false)
    expect(titan((id) => id === 'fe15-3a-1')).toBe(true)
  })
})

describe("Echoes' Hard levels", () => {
  it("adds each placement's Hard levels (0x42df34: the record's +8 on Hard)", () => {
    // Duma's two records (one per difficulty) differ only in level: one entry.
    const duma = map('fe15-5-2').units.filter((u) => u.name === 'Duma')
    expect(duma.map((u) => [u.note!.split('.')[0], u.difficulties])).toEqual([['Lv 30 (Hard 40) Fell God', undefined]])
    expect(map('fe15-1-2').units[0].note).toMatch(/^Lv 1 \(Hard 3\) Brigand\./)
    // Duma's Ordeals: +1 to +5, room by room, as Fire Emblem Wiki gives.
    const bonus = (g: { units: { note?: string }[] }) => {
      const [, n, h] = g.units[0].note!.match(/^Lv (\d+) \(Hard (\d+)\)/)!
      return Number(h) - Number(n)
    }
    expect(map('fe15-x-1').reinforcements!.map(bonus)).toEqual([1, 2, 3, 4, 5])
  })
})

describe("Echoes' foes' orders and the battles' events", () => {
  const unit = (id: string, name: string) => map(id).units.find((u) => u.name === name)!

  it("says what each placement's AI sends it to do (GameData/AIData.bin's routines)", () => {
    expect(unit('fe15-3a-3', 'Berkut').note).toMatch(
      /Waits until turn 5, or until one of your units is within its reach\. Goes for your lord\. Targets Alm when it attacks\./,
    )
    // AI_MV_Person on the unit's own leader is moving with them, not going for them.
    expect(unit('fe15-4a-1', 'Fernand').note).toMatch(/Moves with Berkut/)
    expect(unit('fe15-2-4', 'Kamui').note).toMatch(/Moves with Valbar/)
    expect(unit('fe15-3a-4', 'Mathilda')).toMatchObject({ goesTo: [[16, 20]] })
    expect(unit('fe15-3a-4', 'Mathilda').note).toMatch(/Heads for \(16, 20\)\. Never attacks\./)
    // A random drop is in the note (the person's 落下アイテム at its 落下率), with no badge.
    const guardian = unit('fe15-6-4d', 'Guardian')
    expect(guardian.note).toMatch(/Drops Rusted Bow \(Luna\) 1\.25% of the time\./)
    expect(guardian.drops).toBeUndefined()
  })

  it("reads what the battles' scripts do to their units, and who can be recruited after", () => {
    // Jedah warps out on turn 6's enemy phase, so he only passes through: a named foe, not the boss.
    expect(unit('fe15-4c-6', 'Jedah')).toMatchObject({ type: 'named' })
    expect(unit('fe15-4c-6', 'Jedah').note).toMatch(/Warps out at the start of turn 6's enemy phase, and every Mogall goes with him\./)
    expect(unit('fe15-3a-8', 'Delthea').note).toMatch(/Once Tatarrah falls, she turns green and warps out/)
    expect(unit('fe15-5-2', 'Duma').note).toMatch(/Once he's hurt, from the next enemy phase he goes for your nearest unit\./)
    // Data/Event's joins are a yes or no at the place the battle opens.
    for (const name of ['Valbar', 'Kamui', 'Leon']) expect(unit('fe15-2-4', name).note).toMatch(/Can be recruited inside the Pirate Fort/)
    expect(map('fe15-4c-3').notes).toContain('Conrad joins your army at the end of the battle.')
    expect(map('fe15-4a-6').notes[0]).toMatch(/if Zeke lives, he can then be recruited in a house in Rigel Village\.$/)
    for (const id of ['fe15-3c-4', 'fe15-3c-5']) expect(map(id).notes[0]).toMatch(/Deen, from the north; Sonya, from the south/)
    expect(map('fe15-4a-10').notes).toContain(
      "If the request for five Steel Lances made at Grieth's Citadel was fulfilled, Slayde and the Barons at (13, 22), (17, 22), " +
        '(21, 22), (25, 22) each get a Steel Lance.',
    )
    // Rigel Castle's script wakes every foe once Hard's Rudolf wakes; what wakes him is still to confirm.
    expect(map('fe15-4a-11').notes).toContain("On Hard, Rudolf and the six Bow Knights don't act until woken, and once Rudolf is, every foe is.")
    expect(map('fe15-4a-11').unconfirmed![0]).toMatch(/^What wakes Rudolf and the six Bow Knights on Hard/)
  })

  it("summons The Creation's foes as its script does, one group at a time", () => {
    const m = map('fe15-6-4d')
    // The setting places the first of each of six pairs; the others are the summons.
    expect(m.units.map((u) => u.name)).toEqual(['The Creation', 'Cantor', 'Dread Fighter', 'Deimos', 'Sage', 'Guardian', 'Priestess'])
    expect(m.reinforcements!).toHaveLength(18)
    expect(m.reinforcements!.every((g) => g.units.length === 1)).toBe(true)
    // Five of the script's checks name another person than the one it places, so nothing on the map holds those back.
    expect(m.reinforcements!.filter((g) => String(g.when).includes('even while')).map((g) => g.label).sort()).toEqual([
      'Fafnir', 'Garuda', 'Guardian', 'Titan', 'Vestal',
    ])
    expect(m.reinforcements!.filter((g) => g.label.endsWith('(every fifth turn)')).map((g) => g.label)).toEqual([
      'Dagon (every fifth turn)', 'Fire Dragon (every fifth turn)',
    ])
    // Random summons, not one of Fates' grinding maps.
    expect(m.randomSpawns).toBeFalsy()
    expect(m.groupsNote).toMatch(/^what The Creation's battle summons/)
  })

  it('gives a unit whose difficulties differ only in level one entry', () => {
    const lv = /^Lv \d+/
    for (const m of FE15_MAPS)
      for (const us of [m.units, ...(m.reinforcements ?? []).map((g) => g.units)])
        for (const h of us.filter((u) => u.difficulties?.join() === 'Hard'))
          expect(
            us.some(
              (n) =>
                n.difficulties?.join() === 'Normal' && n.name === h.name && n.tile.join() === h.tile.join() &&
                n.note?.replace(lv, '') === h.note?.replace(lv, '') && lv.test(n.note ?? ''),
            ),
            `${m.id} ${h.name}`,
          ).toBe(false)
  })
})

describe("Echoes' terrain", () => {
  it('shuts the doors the battle sets until a unit beside one uses the Door command', () => {
    const doors = (id: string) => map(id).changes.filter((c) => c.id.startsWith('door-'))
    expect(doors('fe15-1-9').map((c) => [c.tile.default, c.patch])).toEqual([
      [[4, 12], [{ tile: [4, 12], becomes: 'ta' }]],
      [[21, 26], [{ tile: [21, 26], becomes: 'b0' }]],
    ])
    for (const id of ['fe15-1-9', 'fe15-2-10', 'fe15-3c-9', 'fe15-4c-5'])
      for (const c of doors(id)) expect(rowCodes(map(id).grid[map(id).height - c.tile.default![1]])[c.tile.default![0] - 1]).toBe('ob')
    // Act 2's Zofia Castle reuses Act 1's grid but sets only one door: the other never opens.
    expect(doors('fe15-2-10')).toHaveLength(1)
    expect(map('fe15-2-10').notes).toContain(
      "The door at (21, 26) never opens: the battle sets no door on it, so the Door command can't be used there.",
    )
  })

  it("previews the royal chambers' floors as their scripts change them", () => {
    expect(map('fe15-5-1c').changes.map((c) => [c.id, c.patch!.length])).toEqual([['quake', 9]])
    expect(map('fe15-5-1d').changes.map((c) => [c.id, c.patch!.length])).toEqual([['supplies', 8]])
    expect(map('fe15-5-1e').changes.map((c) => [c.id, c.patch!.length])).toEqual([['quake', 13]])
  })

  it("says who a floor's damage spares and who a Bulwark stops, and names the tiles as the game does", () => {
    expect(FE15_TERRAIN.dd!.note).toMatch(/never leaving it below 1; Pegasus Knight, Falcon Knight, Saint, .* and every Terror take none\./)
    expect(FE15_TERRAIN.b1!.note).toBe("Cavalier, Paladin, Gold Knight and Bow Knight can't enter it; every other class, fliers too, can.")
    // Each movement group's label names classes of its own (the illusory heroes' Lord and Hero say so).
    const names = FE15_MOVE_CLASSES.flatMap((label) => label.replace(/ and others$/, '').split(', '))
    expect(new Set(names).size).toBe(names.length)
    // The Thieves' Shrine's floor is the game's Ground, its walls Rock.
    expect(map('fe15-1-3a').terrainOverrides).toMatchObject({ ta: { name: 'Ground' }, wa: { name: 'Rock' } })
  })
})

describe("Echoes' wording", () => {
  it('names no source in what the app shows: the READMEs keep them', () => {
    const shown = [
      ...FE15_MAPS.flatMap((m) => [...m.notes, ...(m.unconfirmed ?? []), ...(m.notesOn ?? []).map((n) => n.note)]),
      ...FE15_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].map((u) => u.note ?? '')),
      ...Object.values(FE15_ITEM_SOURCES).flatMap((lst) => lst.map((s) => s.text)),
    ]
    for (const text of shown) expect(text, text).not.toMatch(/Scripts\/|\.cmb|\.bin|Serenes|[Ww]iki|fireemblemwod/)
    // A place named with 'The' reads 'in the Lost Treescape' inside a line.
    expect(Object.values(FE15_ITEM_SOURCES).flat().some((s) => s.text.includes(' in The '))).toBe(false)
  })

  it('says the ordeals are amiibo dungeons, and which amiibo is still to confirm', () => {
    expect(map('fe15-x-1').notes[0]).toBe("An amiibo dungeon, on Alm's side of the world map from Act 3: it opens once an amiibo is scanned.")
    expect(map('fe15-x-2').unconfirmed![0]).toMatch(/^Which amiibo opens it \(Celica's/)
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
