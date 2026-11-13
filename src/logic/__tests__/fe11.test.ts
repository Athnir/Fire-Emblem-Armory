import { describe, expect, it } from 'vitest'
import { FE11_ITEM_SOURCES } from '../../data/fe11/fe11ItemSources'
import { FE11_LISTED } from '../../data/fe11/fe11Listed'
import { FE11_MAPS } from '../../data/fe11/fe11Maps'
import { FE11_STORY } from '../../data/fe11/fe11MapSet'
import { FE11_MOVE_CLASSES, FE11_TERRAIN } from '../../data/fe11/fe11Terrain'
import { FE11_WEAPONS } from '../../data/fe11/fe11Weapons'
import { GAMES } from '../../games'
import type { Tile } from '../../data/maps/types'
import { fe11ForgeCost, fe11ForgeRange, fe11ForgeStatCost } from '../fe11Forge'
import { atStart } from '../maps'

const map = (id: string) => FE11_MAPS.find((m) => m.id === id)!
const weapon = (name: string) => FE11_WEAPONS.find((w) => w.name === name)!

/** Fire Emblem Wiki's Shadow Dragon chapter pages: [columns, rows, enemies at the start (Normal)]. */
const WIKI: Record<string, [number, number, number]> = {
  'fe11-p1': [14, 21, 0], 'fe11-p2': [17, 15, 6], 'fe11-p3': [26, 17, 10], 'fe11-p4': [19, 30, 9],
  'fe11-1': [30, 13, 14], 'fe11-2': [30, 13, 17], 'fe11-3': [30, 20, 15], 'fe11-4': [30, 20, 20], 'fe11-5': [30, 20, 18],
  'fe11-6': [30, 21, 25], 'fe11-6x': [30, 16, 18], 'fe11-7': [14, 28, 16], 'fe11-8': [30, 28, 20], 'fe11-9': [30, 28, 18],
  'fe11-10': [30, 28, 20], 'fe11-11': [30, 23, 20], 'fe11-12': [30, 28, 19], 'fe11-12x': [20, 30, 19], 'fe11-13': [30, 23, 17],
  'fe11-14': [30, 28, 22], 'fe11-15': [30, 28, 19], 'fe11-16': [30, 30, 20], 'fe11-17': [30, 30, 19], 'fe11-17x': [26, 26, 28],
  'fe11-18': [30, 28, 22], 'fe11-19': [14, 28, 20], 'fe11-20': [30, 28, 19], 'fe11-20x': [30, 30, 23], 'fe11-21': [30, 28, 20],
  'fe11-22': [30, 28, 20], 'fe11-23': [30, 28, 21], 'fe11-24': [30, 28, 20], 'fe11-24x': [22, 30, 31], 'fe11-final': [30, 28, 27],
}
/** Where the game's files and the wiki's infobox disagree: Chapter 8's infobox says 20 foes, but its own unit list has the 19 the
 * placement file places. */
const EXCEPTIONS: Record<string, number> = { 'fe11-8': 19 }

describe("Shadow Dragon's maps", () => {
  it('has the Prologue, Chapters 1-24 with each gaiden chapter where it comes, and the Endgame', () => {
    expect(FE11_STORY.maps.map((m) => m.id)).toEqual([
      'fe11-p1', 'fe11-p2', 'fe11-p3', 'fe11-p4', 'fe11-1', 'fe11-2', 'fe11-3', 'fe11-4', 'fe11-5', 'fe11-6', 'fe11-6x', 'fe11-7',
      'fe11-8', 'fe11-9', 'fe11-10', 'fe11-11', 'fe11-12', 'fe11-12x', 'fe11-13', 'fe11-14', 'fe11-15', 'fe11-16', 'fe11-17',
      'fe11-17x', 'fe11-18', 'fe11-19', 'fe11-20', 'fe11-20x', 'fe11-21', 'fe11-22', 'fe11-23', 'fe11-24', 'fe11-24x', 'fe11-final',
    ])
  })

  it("is each chapter's size on the wiki (the files' grids less their border) with the foes it lists", () => {
    for (const [id, [cols, rows, foes]] of Object.entries(WIKI)) {
      const m = map(id)
      expect([id, m.width, m.height]).toEqual([id, cols, rows])
      expect(m.grid).toHaveLength(rows)
      expect(m.grid.every((r) => r.length === cols * 2)).toBe(true)
      const normal = m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes('Normal')))
      expect([id, normal.length]).toEqual([id, EXCEPTIONS[id] ?? foes])
    }
  })

  it('places every unit inside its map', () => {
    for (const m of FE11_MAPS) {
      const all = [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
      for (const u of all) {
        expect(u.tile[0] >= 1 && u.tile[0] <= m.width && u.tile[1] >= 1 && u.tile[1] <= m.height, `${m.id} ${u.name}`).toBe(true)
      }
    }
  })

  it("reads the talks that recruit, the gaiden chapters' conditions and the reinforcements' turns", () => {
    expect(map('fe11-2').units.find((u) => u.name === 'Castor')?.talk).toBe('Recruit: talk with Caeda')
    expect(map('fe11-4').units.find((u) => u.name === 'Matthis')?.talk).toBe('Recruit: talk with Lena')
    expect(map('fe11-20').units.find((u) => u.name === 'Lorenz')?.talk).toBe('Recruit: talk with Caeda or Marth')
    expect(map('fe11-6x').notes).toContain('Opens if 15 or fewer of your units are alive at the end of Chapter 6.')
    expect(map('fe11-24x').notes.some((n) => /neither the Falchion nor Tiki/.test(n))).toBe(true)
    // Chapter 9's reinforcements come on turns 6, 8 and 10.
    expect(map('fe11-9').reinforcements![0].when).toMatch(/^Turns 6, 8 and 10/)
    // Wrys walks out of Chapter 1's village.
    expect(map('fe11-1').joiners?.map((j) => j.name)).toEqual(['Wrys'])
  })
})

describe("Shadow Dragon's openings and arrivals, as the scripts play them", () => {
  it('undoes what a scene moves inside UnitStackPush and UnitStackPop', () => {
    expect(map('fe11-22').units.find((u) => u.name === 'Michalis')?.tile).toEqual([20, 13])
    expect(map('fe11-11').corrinStart).toEqual([6, 4])
    expect(map('fe11-20').corrinStart).toEqual([30, 19])
  })

  it('reads every handler to its end, warps units in, and keeps scene actors off the map', () => {
    // Chapter 23's Bishops and Mage warp in from the border (UnitWarpAppearance) on turns 7 and 15.
    const warped = map('fe11-23').reinforcements!.find((g) => g.units.some((u) => u.tile[0] === 18 && u.tile[1] === 21))!
    expect(['18,21', '20,23', '11,23'].every((t) => warped.units.some((u) => u.tile.join() === t))).toBe(true)
    expect(warped.when).toMatch(/^Turns 7 and 15/)
    // Prologue IV: the ten Knights a type-0x03 turn handler brings; e02, an actor placed and taken off in one scene, is no group.
    const p4 = map('fe11-p4').reinforcements!
    expect(p4.every((g) => /^Group \d+$/.test(g.label))).toBe(true)
    expect(p4.flatMap((g) => g.units).filter((u) => u.name === 'Knight')).toHaveLength(10)
  })

  it("gives the skull to the chapter's own boss: whose death sets the boss flag, else the foe on the seize tile that stays", () => {
    const kinds = (id: string) => new Set(map(id).units.filter((u) => u.type === 'boss' || u.type === 'named').map((u) => `${u.name}:${u.type}`))
    expect(kinds('fe11-12')).toEqual(new Set(['Volzhin:boss', 'Heimler:named']))
    expect(kinds('fe11-p4').has('Captain:boss')).toBe(true)
    // Chapter 15's Gharnef warps away on turn 6: a named foe there.
    expect(kinds('fe11-15').has('Gharnef:named')).toBe(true)
    // Chapter 23: any of the three Gharnefs may be the real one, picked as the map loads.
    const gharnefs = map('fe11-23').units.filter((u) => u.name === 'Gharnef')
    expect(new Set(gharnefs.map((u) => u.tile.join())).size).toBe(3)
    expect(gharnefs.every((u) => u.type === 'boss' && /One of these 3, picked at random as the map loads, is the real Gharnef/.test(u.note!))).toBe(true)
    expect(FE11_ITEM_SOURCES['Steel Sword']).toContainEqual({ mapId: 'fe11-23', kind: 'drop', text: 'Dropped by a double of Gharnef' })
  })

  it('says when each arrival comes and what stops it, one group per arrival', () => {
    const when = (id: string) => map(id).reinforcements!.map((g) => g.when)
    expect(when('fe11-7')).toEqual([
      'The next 2 enemy phases after one of your units enters the area below, up to 3 times, until Harmein is defeated',
    ])
    // Chapter 8: two traps, each set off by its own two areas.
    expect(map('fe11-8').reinforcements!.map((g) => g.areas?.length)).toEqual([2, 2])
    expect(when('fe11-17')[0]).toBe('Every enemy phase once one of your units has entered the area below, at most 10 times, until Morzas is defeated')
    expect(when('fe11-17x')).toContain('Turn 2, enemy phase, unless one of your units has entered the area below by then')
    expect(when('fe11-p4')).toContain('The first player phase after Gordin joins your army')
    // The Endgame's turns 15 and 20 bring both pairs: each pair's turns say so.
    expect(when('fe11-final')).toEqual(['Turns 4, 6, 8, 10, 15 and 20, enemy phase', 'Turns 5, 8, 11, 15 and 20, enemy phase'])
    expect(map('fe11-9').reinforcements).toHaveLength(1)
  })

  it("reads each placement's AI and what the chapter's handlers do to its units", () => {
    const normal = (id: string) => map(id).units.filter((u) => !u.difficulties || u.difficulties.includes('Normal'))
    // Chapter 6's thieves (CP_SP_Treasure): a chest each, then the exit; torch badge, exit outlined.
    const thieves = normal('fe11-6').filter((u) => u.name === 'Thief')
    expect(thieves).toHaveLength(4)
    expect(thieves.every((u) => u.looter && JSON.stringify(u.goesTo) === '[[30,17]]')).toBe(true)
    expect(thieves[0].note).toContain('Goes for the chest at (4, 10), empties it, then makes for (30, 17) and leaves the map, never attacking.')
    // Chapter 4's (CP_SP_Village): their villages, which name them.
    expect(map('fe11-4').objects.filter((o) => o.type === 'village').every((o) => o.note?.includes('Thief can raze it before you visit.'))).toBe(true)
    expect(normal('fe11-12').filter((u) => u.name === 'Mage').every((u) => u.note!.endsWith('Targets Marth when it attacks.'))).toBe(true)
    expect(normal('fe11-12').find((u) => u.name === 'Heimler')!.note).toMatch(/Wakes when one of your units enters the area from/)
    expect(normal('fe11-1').find((u) => u.name === 'Gazzak')!.note).toContain("Moves to (5, 9) at the start of turn 2's player phase.")
    expect(normal('fe11-7').find((u) => u.name === 'Minerva')!.note).toContain("Leaves the map at the start of turn 6's enemy phase.")
    expect(normal('fe11-final').find((u) => u.name === 'Medeus')!.note).toContain("Turns into an E. Dragon at the start of turn 1's player phase.")
  })

  it('says everything a talk or the end does: recruits on any unit, their conditions, gifts, joins after the battle', () => {
    const anyone = (id: string, name: string) =>
      [...map(id).units, ...(map(id).reinforcements ?? []).flatMap((g) => g.units)].find((u) => u.name === name)!
    expect(anyone('fe11-10', 'Minerva').talk).toBe('Recruit: talk with Marth, once Maria has joined your army')
    expect(anyone('fe11-11', 'Jake').talk).toBe('Recruit: talk with Caeda, once the house at (22, 7) is visited')
    expect(anyone('fe11-14', 'Catria').talk).toBe('Recruit: talk with Marth')
    expect(anyone('fe11-12x', 'Horace').note).toMatch(/Joins your army after the battle if alive\.$/)
    expect(anyone('fe11-20x', 'Ymir').talk).toBe('Talk with Marth: leaves the map, and joins your army after the battle')
    expect(map('fe11-22').objects.find((o) => o.type === 'village')).toMatchObject({
      reward: 'Starlight, if Marth carries the Lightsphere and the Starsphere (both taken)',
    })
  })

  it('places one of two units by a story flag, saying which', () => {
    expect(map('fe11-final').forced).toEqual([{ name: 'Gotoh (Nagi if Chapter 24x was played)', tile: [15, 5] }])
  })
})

describe("Shadow Dragon's terrain", () => {
  const code = (id: string, c: string) => (map(id).grid.join('').match(/../g) ?? []).filter((x) => x === c).length
  it('reads movement costs from the terrain category, as the engine does', () => {
    // Plains cost 1 for every class (Terrain +0xc, read before, is a column no class can enter); a closed door bars everyone; the
    // lord can take the throne.
    expect(Object.values(FE11_TERRAIN.t0!.move).every((c) => c === 1)).toBe(true)
    expect(FE11_TERRAIN.t1!.move).toEqual(FE11_TERRAIN.t0!.move)
    expect(Object.values(FE11_TERRAIN.ob!.move).every((c) => c === null)).toBe(true)
    expect(FE11_TERRAIN.bc!.move.Lord).toBe(1)
  })

  it('draws its tiles as the game draws them: plains, floors, castle walls, the view beyond, each map its own colours', () => {
    // Plain and floor (MS_TER_PLAIN, MS_TER_FLOOR) their own codes; a wall a castle's, in its map's stone; a tile no one enters the
    // void beyond the map, sky or distant land (scripts/ds_art.py).
    const codes = new Set(FE11_MAPS.flatMap((m) => (m.grid.join('').match(/../g) ?? [])))
    for (const c of ['t0', 't1', 'w0', 'wy']) expect(codes.has(c), c).toBe(true)
    for (const c of ['ta', 'wa', 'wx', 'wg']) expect(codes.has(c), c).toBe(false)
    // The Fence over each village's entrance is its houses (fliers cross them, as the GBA games' village walls).
    expect(code('fe11-1', 'w8')).toBeGreaterThan(0)
    expect(FE11_TERRAIN.w8!.move).toEqual(FE11_TERRAIN.ca!.move)
    expect(code('fe11-24x', 'wy')).toBe(36)
    // The plains' dirt patches and paths, sorted from the art (scripts/ds_art.py's dirt): plain's stats, the map's own dirt colour.
    expect(code('fe11-24', 'ga')).toBeGreaterThan(100)
    expect(FE11_TERRAIN.ga!.move).toEqual(FE11_TERRAIN.t0!.move)
    expect(map('fe11-24').fills?.ga).toMatch(/^#[0-9a-f]{6}$/)
    expect(code('fe11-15', 'ga')).toBe(0) // a desert's sandy plains have no dirt look apart from them
    expect(map('fe11-6').fills?.w0).toMatch(/^#[0-9a-f]{6}$/)
    for (const m of FE11_MAPS) for (const c of ['t0', 't1', 'we', 'w0'] as const) if (code(m.id, c) >= 4) expect(m.fills?.[c], `${m.id} ${c}`).toBeDefined()
  })

  it('gives each kind of tile that works differently its own code', () => {
    // Houses: stood in for Avo 5, never razed. Ledges: climbed at a cost, barred to armour, cavalry, archers and soldiers. Castles:
    // fliers only. Chapter 9's reinforcement entry tiles: only the lord can't enter them.
    expect(FE11_TERRAIN.ot!.avo).toBe(5)
    expect(code('fe11-1', 'ot')).toBeGreaterThan(0)
    expect(FE11_TERRAIN.tt!.move).toMatchObject({ Lord: 4, Knight: null, Cavalier: null, Archer: null, 'Peg. Knight, Dracoknight': 1 })
    expect(code('fe11-13', 'tt')).toBe(148)
    expect(code('fe11-13', 'w0')).toBe(0)
    // A castle on open ground: fliers only, drawn whole, its pieces round its gate.
    for (const c of ['ca', 'cb', 'cc', 'ce', 'cg', 'ci'] as const)
      expect(Object.entries(FE11_TERRAIN[c]!.move).filter(([, n]) => n !== null).map(([g]) => g), c).toEqual(['Peg. Knight, Dracoknight'])
    expect(FE11_TERRAIN.tu!.move).toMatchObject({ Lord: null, Knight: 1 })
    expect(code('fe11-9', 'tu')).toBe(12)
  })

  it("names the classes plainly, and only those the game's maps use", () => {
    expect(FE11_MOVE_CLASSES).toContain('Hero, Swordmaster')
    expect(FE11_MOVE_CLASSES.some((c) => /KNIGHT|[⊂⊃]/.test(c))).toBe(false)
  })
})

describe("Shadow Dragon's map changes", () => {
  const at = (id: string, [x, y]: Tile) => {
    const m = map(id)
    return m.grid[m.height - y].slice((x - 1) * 2, x * 2)
  }
  const change = (id: string, cid: string) => map(id).changes.find((c) => c.id === cid)!

  it('starts the rooms of Chapters 17x and 19 closed, each opened by a door beside it or, for the throne room, a script', () => {
    // The map file's room grid (+0x14): every room closed as the map loads, fliers barred too, until a door into it opens.
    expect(Object.values(FE11_TERRAIN.ws!.move).every((c) => c === null)).toBe(true)
    expect(FE11_MAPS.filter((m) => m.grid.join('').match(/../g)!.includes('ws')).map((m) => m.id)).toEqual(['fe11-17x', 'fe11-19'])
    // Chapter 19's ten doors: the two nearest the start share its biggest room.
    expect(map('fe11-19').changes.map((c) => c.patch!.length)).toEqual([35, 35, 18, 18, 18, 18, 18, 18, 18, 18])
    for (const id of ['fe11-17x', 'fe11-19']) {
      const m = map(id)
      const opened = new Set(m.changes.flatMap((c) => c.patch!.map((p) => p.tile.join())))
      for (let y = 1; y <= m.height; y++) {
        for (let x = 1; x <= m.width; x++) if (at(id, [x, y]) === 'ws') expect(opened.has(`${x},${y}`), `${id} ${x},${y}`).toBe(true)
      }
      expect(m.changes.filter((c) => c.id.startsWith('door-')).every((c) => at(id, c.tile.default) === 'ob')).toBe(true)
    }
    expect(change('fe11-17x', 'room-20-6').effect).toBe('A closed room: it opens when one of your units enters the area from (13, 5) to (19, 6).')
  })

  it("makes the opening's changes before the battle and says what each script changes, and when", () => {
    // Chapter 1's opening razes the village at (22, 4): ruins, with no village left to visit.
    expect(at('fe11-1', [22, 4])).toBe('tm')
    expect(map('fe11-1').objects.some((o) => o.tile.join() === '22,4')).toBe(false)
    // The Endgame's five side doors start open and shut on turns 3, 3, 5, 6 and 7.
    const shuts = map('fe11-final').changes.filter((c) => c.effect.startsWith('Open as the battle starts'))
    expect(shuts.map((c) => c.effect.match(/turn (\d+)/)![1]).sort()).toEqual(['3', '3', '5', '6', '7'])
    expect(shuts.every((c) => at('fe11-final', c.tile.default) === 't1')).toBe(true)
    // Prologue I's door opens when your units come near; Prologue IV's by the decoy's fort, Gordin's death or Marth left alone
    // ("All but the prince have been slain?": ForceGetCount(0) == 1), said in notes the spoiler block leaves out.
    expect(change('fe11-p1', 'door-10-13').effect).toMatch(/ It also opens when one of your units enters the area from \(7, 1\) to \(14, 12\)\.$/)
    const p4 = map('fe11-p4').notes.filter((n) => n.startsWith("Gordin isn't on the map at the start: "))
    expect(p4).toHaveLength(2)
    expect(p4[1]).toMatch(/visits the fort at \(13, 1\), on the enemy phase after Gordin falls, or on the first enemy phase once Gordin has joined and only Marth is left in your army\.$/)
    expect(atStart(map('fe11-p4')).notes.some((n) => /Gordin/.test(n))).toBe(false)
    // Chapter 16's two villages: visiting one closes the other.
    expect(map('fe11-16').objects.filter((o) => o.type === 'village' && /^Visiting it closes the village at/.test(o.note ?? ''))).toHaveLength(2)
    // Drawbridges a Bridge Key or a Master Key lowers.
    expect(FE11_MAPS.flatMap((m) => m.changes.filter((c) => c.id.startsWith('bridge-')).map(() => m.id))).toEqual(['fe11-14', 'fe11-20'])
  })
})

describe("Shadow Dragon's Hard modes", () => {
  const HARD = ['Hard', 'Brutal', 'Savage', 'Fiendish', 'Merciless']
  it("gives each foe the weapons each mode gives it, one entry per set, as Fire Emblem Wiki's mode tabs list them", () => {
    // Chapter 10's boss, Zharov (tier 2): Merciless lifts Steel to Silver and forges the special weapons; a dropped item in the first
    // slot keeps a copy that still drops (Chapter 12's mage: Elfire, and the Thunder it drops).
    expect(map('fe11-10').units.filter((u) => u.name === 'Zharov').map((u) => [u.note, u.difficulties])).toEqual([
      ['Lv 3 General: Javelin, Steel Lance, Speedwing', ['Normal', 'Hard', 'Brutal', 'Savage', 'Fiendish']],
      ['Lv 3 General: Javelin (forged: Mt +4, Hit +20), Silv. Lance, Speedwing', ['Merciless']],
    ])
    expect(map('fe11-12').units.some((u) => u.note!.startsWith('Lv 5 Mage: Elfire, Thunder.') && u.difficulties?.join() === 'Savage,Fiendish')).toBe(true)
    // What only a mode's foes carry is theirs on that mode alone (the Brave weapons, from Merciless's Chapter 20).
    expect(FE11_ITEM_SOURCES['Brv. Sword'].every((s) => s.kind.startsWith('foe') && s.difficulties?.join() !== undefined)).toBe(true)
  })

  it('says what each mode adds on that mode, and that the prologue is Normal only', () => {
    const on = (id: string, mode: string) => map(id).notesOn?.find((n) => n.difficulties.join() === mode)?.note
    expect(on('fe11-1', 'Hard')).toMatch(/^Foes the game levels gain 3 levels' worth of growth.*at least C\.$/)
    expect(on('fe11-24', 'Merciless')).toMatch(/gain 20 levels' worth.*at least A\.$/)
    expect(map('fe11-p1').difficulties).toEqual(['Normal'])
    // The army joins in the prologue on Normal and in Chapter 1 on the Hard modes, which have none: each copy counted once a mode.
    expect(FE11_ITEM_SOURCES['Rapier']).toContainEqual({ mapId: 'fe11-p1', kind: 'kit', text: 'Carried by Marth on joining', difficulties: ['Normal'] })
    expect(FE11_ITEM_SOURCES['Rapier']).toContainEqual({ mapId: 'fe11-1', kind: 'kit', text: 'Carried by Marth on joining', difficulties: HARD })
    expect(FE11_ITEM_SOURCES['Javelin']).toContainEqual({ mapId: 'fe11-p2', kind: 'kit', text: 'Carried by Abel on joining', difficulties: ['Normal'] })
  })

  it("keeps Gharnef's doubles' false copies off the weapon page", () => {
    expect(map('fe11-23').units.filter((u) => u.name === 'Gharnef' && /doubles with false copies/.test(u.note!))).toHaveLength(3)
    expect(FE11_ITEM_SOURCES['Falchion (false)']).toBeUndefined()
  })
})

describe("Shadow Dragon's weapons", () => {
  it('reads the item table: prices are uses times the price per use, ranks from the weapon experience they need', () => {
    expect(weapon('Iron Sword')).toMatchObject({ mt: 5, hit: 100, crit: 0, wt: 4, uses: 40, worth: 400, rank: 'E' })
    expect(weapon('Silv. Sword')).toMatchObject({ mt: 12, rank: 'B', worth: 2000 })
    expect(weapon('Mercurius').rank).toBe('A')
    expect(weapon('Rapier')).toMatchObject({ effective: ['armour', 'horseback'], rules: ['Marth only'] })
    expect(weapon('Wyrmslayer').effective).toEqual(['fe11-dragons'])
    expect(weapon('Falchion').effective).toEqual(['fe11-dragons-all'])
    expect(weapon('Brv. Sword').rules).toContain('Strikes twice in a row')
  })

  it('says who may use each weapon as the equip check decides it (arm9 0x203c834), and what each one does', () => {
    // Each lock bit asks for an attribute of the person, the class or the placement: the Falchion's is on Marth's placements alone.
    expect(weapon('Falchion').rules).toContain('Marth only')
    expect(weapon('Aum').rules).toEqual(['Caeda, Maria, Minerva and Elice only'])
    expect(weapon('Hammerne').rules).toEqual(['Lena only'])
    expect(weapon('Divinestone').rules).toEqual(['Tiki and Nagi only'])
    expect(weapon('Longbow').rules).toEqual(['Archers and Snipers only'])
    expect(weapon('Aura').rules).toEqual(['Women only', 'Linde can use it from rank E'])
    expect(weapon('Excalibur').rules).toEqual(['Men only', 'Merric can use it from rank E'])
    // Magic weapons outside the tomes are fought against Resistance; the ballistae are a Ballistician's, Thunderbolt effective
    // against them.
    for (const name of ['Levin Sword', 'Magestone', 'Thunderbolt']) expect(weapon(name).magic, name).toBe(true)
    expect(weapon('Thunderbolt')).toMatchObject({ category: 'Ballista', range: '3–10', effective: ['fe11-ballistician'] })
    // Never wears out (+0x27 0x08), any distance (a max range of 255), the devil weapons' backfire, what a healing staff heals.
    for (const name of ['Falchion', 'Falchion (24x)', 'Imhullu', 'Earthstone']) expect(weapon(name).uses, name).toBeNull()
    expect(weapon('Physic').range).toBe('Any')
    expect(weapon('Devil Axe').rules).toEqual([expect.stringMatching(/under 21 minus half the wielder's Luck \(rounded down\)$/)])
    expect(weapon('Mend').rules).toEqual(["Heals 15 HP plus half the user's Magic (rounded down)"])
  })

  it("counts gifts and recruits' gear from the next chapter, and the 24x Falchion is its own", () => {
    // Gifts: the chapter's end (event-later), a talk (talk-later). Parthia has no other source.
    expect(FE11_ITEM_SOURCES['Parthia']).toEqual([{ mapId: 'fe11-12', kind: 'event-later', text: 'Given at the end of the chapter to Marth' }])
    expect(FE11_ITEM_SOURCES['Silv. Sword']).toContainEqual({ mapId: 'fe11-4', kind: 'event-later', text: 'Given at the end of the chapter to Marth' })
    expect(FE11_ITEM_SOURCES['Mercurius']).toEqual([{ mapId: 'fe11-18', kind: 'talk-later', text: 'Given to Marth when Est joins' }])
    // Recruits who join mid-battle (a talk, a village): from the next chapter.
    expect(FE11_ITEM_SOURCES['Killing Edge']).toContainEqual({ mapId: 'fe11-3', kind: 'kit-later', text: 'Carried by Navarre on joining' })
    expect(FE11_ITEM_SOURCES['Excalibur']).toContainEqual({ mapId: 'fe11-4', kind: 'kit-later', text: 'Carried by Merric on joining' })
    expect(weapon('Falchion (24x)')).toMatchObject({ mt: 7, hit: 90, wt: 9 })
    expect(FE11_ITEM_SOURCES['Falchion (24x)']).toEqual([{ mapId: 'fe11-24x', kind: 'event-later', text: 'Given at the end of the chapter to Marth' }])
  })

  it('lists where each weapon turns up', () => {
    expect(FE11_ITEM_SOURCES['Iron Sword']).toContainEqual({ mapId: 'fe11-1', kind: 'shop', text: 'Sold at the armory' })
    expect(FE11_LISTED.some((w) => w.name === 'Rapier')).toBe(true)
    // A limited stock (GoodsLimit) sells as many as the chapter's script sets (ValueRegistSet): one Rapier, three of the secret shops'.
    expect(FE11_ITEM_SOURCES['Rapier']).toContainEqual({ mapId: 'fe11-8', kind: 'shop', text: 'Sold at the armory (1 in stock)', limited: 1 })
    expect(FE11_ITEM_SOURCES['Killer Bow']).toContainEqual(
      { mapId: 'fe11-17', kind: 'shop', text: 'Sold at the secret shop, with a VIP Card (3 in stock)', limited: 3 },
    )
  })
})

describe("Shadow Dragon's battle numbers", () => {
  it('rolls hit with two numbers averaged (overlay 00 at 0x21c92c4: two 0-99 rolls, added and halved, below the hit lands)', () => {
    expect(GAMES.find((g) => g.id === 'fe11')?.hitSystem).toBe('2rn')
  })

  it("prices the forge as its menu does, matching Serenes Forest's worked example", () => {
    // A Silv. Sword (2,000G) with Mt +10, Crit +30 and Wt -4: (110,000 + 110,000 + 20,000 + 2,000) / 2.
    expect(weapon('Silv. Sword').worth).toBe(2000)
    expect(fe11ForgeCost(2000, { mt: 10, crit: 30, wt: -4 })).toBe(121000)
    // Nothing changed still costs half the price; a part step costs its share of the next (Hit +7: one step and 2/5 of the second).
    expect(fe11ForgeCost(400, {})).toBe(200)
    expect(fe11ForgeStatCost(400, 'hit', 7)).toBe(400 + Math.floor((2 * (1200 - 400)) / 5))
    // The limits, either way: Mt 10 (0 to 30), Hit 50 (0 to 200), Crit 30 (0 to 50), Wt 10 (1 to 30).
    expect(fe11ForgeRange('mt', 12)).toEqual([2, 22])
    expect(fe11ForgeRange('mt', 5)).toEqual([0, 15])
    expect(fe11ForgeRange('hit', 160)).toEqual([110, 200])
    expect(fe11ForgeRange('crit', 30)).toEqual([0, 50])
    expect(fe11ForgeRange('wt', 5)).toEqual([1, 15])
  })
})
