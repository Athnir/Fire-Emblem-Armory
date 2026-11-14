import { describe, expect, it } from 'vitest'
import { FE8_ITEM_SOURCES } from '../../data/fe8/fe8ItemSources'
import { FE8_LISTED } from '../../data/fe8/fe8Listed'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE8_FORK, FE8_MAP_SET, FE8_STORY } from '../../data/fe8/fe8MapSet'
import { FE8_SUPPORTS } from '../../data/fe8/fe8Supports'
import { FE8_MOVE_CLASSES, FE8_TERRAIN } from '../../data/fe8/fe8Terrain'
import { FE8_TRIANGLE } from '../../data/fe8/fe8Triangle'
import { FE8_WEAPONS } from '../../data/fe8/fe8Weapons'
import type { ChapterMap, ReinforcementGroup, Difficulty } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE8_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const red = (m: ChapterMap, d: Difficulty) => m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes(d))).length

describe("The Sacred Stones' maps", () => {
  it('has the shared chapters, both routes to the end, the Tower of Valni and the Lagdou Ruins, each grid its own size', () => {
    expect(FE8_MAPS.filter((m) => m.route === 'Shared')).toHaveLength(10)
    expect(FE8_MAPS.filter((m) => m.route === 'Eirika')).toHaveLength(14)
    expect(FE8_MAPS.filter((m) => m.route === 'Ephraim')).toHaveLength(14)
    expect(FE8_MAPS.filter((m) => m.route === 'Extra')).toHaveLength(18)
    for (const m of FE8_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const code of new Set(FE8_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE8_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE8_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
    // Two kinds of gate: terrain 11 gives 20 Avoid, terrain 35 (its own code) 30.
    expect(FE8_TERRAIN.bd).toMatchObject({ avo: 20 })
    expect(FE8_TERRAIN.bv).toMatchObject({ avo: 30 })
  })

  it('places every unit inside its map', () => {
    for (const m of FE8_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
    }
  })

  it('starts each chapter with the enemies the Fire Emblem Wiki counts (its chapter data, per route and difficulty)', () => {
    // [Easy, Normal, Hard] from each chapter page's "Enemy" figure, reinforcements left out (one number: the same on all three).
    const wiki: Record<string, number | number[]> = {
      'fe8-prologue': [0, 3, 3], 'fe8-1': 7, 'fe8-2': 6, 'fe8-3': 10, 'fe8-4': 15,
      // The wiki's 16 leaves out Joshua, the Myrmidon Natasha recruits (it counts every other chapter's recruitable foes: Marisa,
      // Amelia, Rennac, Cormag); the opening loads Joshua as an enemy.
      'fe8-5': 17,
      'fe8-5x': 31, 'fe8-6': 24, 'fe8-7': 19, 'fe8-8': [27, 27, 32],
      'fe8-eirika-9': [23, 23, 29], 'fe8-eirika-10': [34, 34, 40], 'fe8-eirika-11': 41, 'fe8-eirika-12': [32, 32, 38],
      'fe8-eirika-13': [22, 22, 28], 'fe8-eirika-14': 42, 'fe8-eirika-15': 46, 'fe8-eirika-16': [29, 29, 35], 'fe8-eirika-17': 25,
      'fe8-eirika-18': [28, 28, 34], 'fe8-eirika-19': 25, 'fe8-eirika-20': [47, 47, 50], 'fe8-eirika-final': 36, 'fe8-eirika-final-2': 1,
      'fe8-ephraim-9': 38, 'fe8-ephraim-10': [24, 24, 28], 'fe8-ephraim-11': 10, 'fe8-ephraim-12': 37, 'fe8-ephraim-13': 44,
      'fe8-ephraim-14': 42, 'fe8-ephraim-15': 45, 'fe8-ephraim-16': [37, 37, 42], 'fe8-ephraim-17': 25, 'fe8-ephraim-18': [28, 28, 34],
      'fe8-ephraim-19': 25, 'fe8-ephraim-20': [47, 47, 50], 'fe8-ephraim-final': 36, 'fe8-ephraim-final-2': 1,
    }
    for (const m of FE8_MAPS.filter((x) => x.route !== 'Extra' && x.route !== 'Skirmish')) {
      const w = wiki[m.id]
      const [easy, normal, hard] = typeof w === 'number' ? [w, w, w] : w
      expect(red(m, 'Easy'), `${m.id} Easy`).toBe(easy)
      expect(red(m, 'Normal'), `${m.id} Normal`).toBe(normal)
      expect(red(m, 'Hard'), `${m.id} Hard`).toBe(hard)
    }
  })

  it("plays each opening: Artur's scripted battle takes one Mogall off Chapter 4; the deploy tiles are the prep group's", () => {
    expect(map('fe8-4').units.filter((u) => u.name === 'Mogall')).toHaveLength(3)
    expect(map('fe8-prologue').units.find((u) => u.name === "O'Neill")).toMatchObject({ type: 'boss', carries: ['Iron Axe'] })
    expect(map('fe8-eirika-15').starts).toHaveLength(12)
    expect(map('fe8-5x').lord).toBe('Ephraim')
    expect(map('fe8-eirika-final-2').defeat).toBe('Eirika or Ephraim is defeated')
  })

  it("moves generic enemies' levels by difficulty, by the chapter's own figures (+0x14)", () => {
    // Chapter 5: Easy −4, Normal −2, Hard +3 for every enemy whose character id is above 0x3B.
    expect(map('fe8-5').units.find((u) => u.name === 'Saar')!.note).toBe('Lv 6 (Easy 4, Hard 11) Knight')
    // Named characters keep their level.
    expect(map('fe8-5').units.find((u) => u.name === 'Joshua')!.note).toBe('Lv 5 Myrmidon')
  })

  it("marks looters from the movement AI: what each goes for, and the exits a leaver heads for", () => {
    for (const m of FE8_MAPS) {
      const units = [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units), ...(m.joiners ?? [])]
      const has = (t: string) => m.objects.some((o) => o.type === t)
      for (const u of units) {
        // A looter only where there's something to loot, and its note says what.
        if (u.looter) {
          expect(has('village') || has('chest'), `${m.id} ${u.name}`).toBe(true)
          expect(u.note, `${m.id} ${u.name}`).toMatch(/[Gg]oes for the (villages|chests|villages and chests), (razing|emptying|razing or emptying) what it reaches/)
        }
        // Exits only for a unit whose note says it leaves, each on the map.
        if (u.goesTo) {
          expect(u.note, `${m.id} ${u.name}`).toMatch(/leaves the map/)
          for (const [x, y] of u.goesTo) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name}`).toBe(true)
        }
      }
    }
  })

  it("reads the looters: Chapter 2's brigands wait a turn, Colm goes for the chests, Rennac only leaves", () => {
    expect(map('fe8-2').units.filter((u) => u.note?.endsWith('after a turn, goes for the villages, razing what it reaches'))).toHaveLength(2)
    expect(map('fe8-3').joiners!.find((j) => j.name === 'Colm')).toMatchObject({ looter: true, note: 'Goes for the chests, emptying what it reaches' })
    // No chest on Rennac's map: the thief's AI finds nothing and makes for the exit.
    expect(map('fe8-eirika-14').units.find((u) => u.name === 'Rennac')).toMatchObject({
      note: 'Lv 1 Rogue; makes for an exit and leaves the map',
      goesTo: [[1, 14]],
    })
  })


  it('keeps one group per arrival, and says who sets an area off and when', () => {
    // The same units on the same tiles are one group, its time per difficulty; two such groups only where both come at once on
    // one difficulty (two copies arriving).
    const key = (g: ReinforcementGroup) =>
      JSON.stringify(g.units.map((u) => [u.name, u.tile, u.from, u.type, u.carries, u.drops, u.talk, (u.note ?? '').replace(/^Lv \d+( \([^)]*\))?/, '')]).sort())
    const whenOn = (g: ReinforcementGroup, d: Difficulty) => (typeof g.when === 'string' ? g.when : g.when?.[d])
    for (const m of FE8_MAPS) {
      const groups = m.reinforcements ?? []
      groups.forEach((g, i) =>
        groups.slice(i + 1).forEach((o) => {
          if (key(g) === key(o)) expect((['Easy', 'Normal', 'Hard'] as Difficulty[]).some((d) => whenOn(g, d) && whenOn(g, d) === whenOn(o, d)), `${m.id} ${g.label} ${o.label}`).toBe(true)
        }),
      )
      // An area's group says who stops there and that it comes at once; none just "enters".
      for (const g of groups) {
        const whens = typeof g.when === 'string' ? [g.when] : Object.values(g.when ?? {})
        for (const w of whens) expect(w, `${m.id} ${g.label}`).not.toMatch(/enters the (marked )?area/)
        if (g.areas) for (const w of whens) expect(w, `${m.id} ${g.label}`).toMatch(/stops in|stands on|is in the marked area|is left in the marked area/)
      }
    }
  })

  it('reads who may set an area off, groups by arrival, and the Tower 7 spawns each foe unlocks', () => {
    // Chapter 1's area calls the shared character check with Eirika's id: only Eirika sets it off.
    expect(map('fe8-1').reinforcements![0].when).toBe('As soon as Eirika stops in the marked area')
    // One handler's placement, with the extra Gargoyles Hard adds marked Hard.
    const gargoyles = map('fe8-eirika-12').reinforcements![0]
    expect(gargoyles.when).toBe('As soon as one of your units stops in the marked area')
    expect(gargoyles.units.some((u) => u.difficulties?.join() === 'Hard')).toBe(true)
    // Chapter 17's groups that come on the same turns are one arrival.
    expect(map('fe8-eirika-17').reinforcements!.find((g) => g.when === 'Turns 4, 6 and 8, your phase')!.units).toHaveLength(5)
    expect(map('fe8-tower-7').reinforcements!.map((g) => g.when)).toEqual([
      'Every turn, your phase, once the Elder Bael and 3 random monsters are defeated',
      'Every turn, your phase, once the Gwyllgi and 6 random monsters are defeated',
      'Every turn, your phase, once the Arch Mogall and 4 random monsters are defeated',
    ])
  })

  it('times gifts and gear: the Prologue opening\'s Rapier from the Prologue, end gifts and talk recruits from the next chapter', () => {
    // The Prologue's opening gives Eirika the Rapier (0x37); Easy's hands the rest to the tutorial, which gives the same one.
    expect(FE8_ITEM_SOURCES['Rapier'][0]).toEqual({ mapId: 'fe8-prologue', kind: 'gift', text: 'Given to Eirika at the start of the chapter' })
    for (const [name, list] of Object.entries(FE8_ITEM_SOURCES))
      for (const s of list) {
        expect(['event', 'talk'].includes(s.kind), `${name} ${s.mapId} ${s.kind}`).toBe(false)
        if (s.text.endsWith('at the end of the chapter') || s.text.includes('at the end of the chapter if')) expect(s.kind, `${name} ${s.mapId}`).toBe('event-later')
      }
    // Joshua joins by a talk in Chapter 5: the Killing Edge Joshua brings counts from Chapter 6.
    expect(FE8_ITEM_SOURCES['Killing Edge'].find((s) => s.text === 'Carried by Joshua on joining')).toMatchObject({ mapId: 'fe8-5', kind: 'kit-later' })
  })

  it("says on Hard what it gives a promoted generic foe that its shown level doesn't", () => {
    expect(map('fe8-eirika-9').notesOn).toEqual([
      {
        note:
          "On Hard, a promoted generic foe the game levels gets 19 extra levels' worth of its class's growth in HP, Str, Skl, Spd, Def, " +
          "Res and Lck rather than Easy's and Normal's 9; its shown level doesn't count them.",
        difficulties: ['Hard'],
      },
    ])
    // No promoted generic the game levels in the Prologue; a Tower floor of random monsters says nothing of what they are.
    expect(map('fe8-prologue').notesOn).toBeUndefined()
    expect(map('fe8-tower-5').notesOn).toBeUndefined()
  })

  it('reads a recruit a talk offers for gold (the shared script at 0x089EEAAC: Rennac)', () => {
    for (const [id, lord] of [['fe8-eirika-14', 'Eirika'], ['fe8-ephraim-14', 'Ephraim']])
      expect(allUnits(map(id)).find((u) => u.name === 'Rennac')!.talk).toBe(`Recruit: talk with L'Arachel, or with ${lord} for 9,980 gold`)
  })

  it('reads who recruits whom', () => {
    const talk = (id: string, name: string) => [...allUnits(map(id)), ...(map(id).joiners ?? [])].find((u) => u.name === name && u.talk)?.talk
    expect(talk('fe8-5', 'Joshua')).toBe('Recruit: talk with Natasha')
  })

  it('says what an end scene hands over only on a condition, from its own checks', () => {
    expect(map('fe8-6').notes).toContain("Orion's Bolt: given to Eirika at the end of the chapter if all three 'Renais Cit.' units survive.")
    expect(map('fe8-eirika-19').notes).toContain(
      "Light Brand: given to your army at the end of the chapter if at least 6 of the other army's units are left.",
    )
  })

  it("starts each map as the opening leaves it, and previews its doors, rooms, walls and snags", () => {
    const at = (m: ChapterMap, x: number, y: number) => rowCodes(m.grid[m.height - y])[x - 1]
    const codes = (m: ChapterMap) => m.grid.flatMap((row) => rowCodes(row))
    // Chapter 2's opening razes a village; Ephraim's Chapter 11 puts the phantom ship on the sea, so only fliers stand on water.
    expect(codes(map('fe8-2')).filter((c) => c === 'tm')).toHaveLength(9)
    const ship = map('fe8-ephraim-11')
    for (const u of ship.units) if (['we', 'wm'].includes(at(ship, ...u.tile))) expect(['Mogall', 'Gargoyle', 'Deathgoyle'], u.name).toContain(u.name)
    // A change made while a scene has another map loaded doesn't count: Eirika's Chapter 9 keeps its Dragonshield village.
    expect(map('fe8-eirika-9').objects.filter((o) => o.type === 'village').map((o) => (o.type === 'village' ? o.reward : ''))).toEqual(['Dragonshield', 'Rapier'])
    // Eirika's Chapter 14: rooms under their roofs, closed until one of its nine doors opens.
    const ch14 = map('fe8-eirika-14')
    expect(codes(ch14).filter((c) => c === 'ws')).toHaveLength(97)
    expect(ch14.changes.filter((c) => c.id.startsWith('door-'))).toHaveLength(9)
    expect(FE8_TERRAIN.ws!.move).toEqual(Object.fromEntries(FE8_MOVE_CLASSES.map((c) => [c, null])))
    // Cracked walls take the chapter's wall HP; snags have 20.
    const breaks = FE8_MAPS.flatMap((m) => m.changes.filter((c) => c.trigger === 'breakable'))
    expect(breaks.filter((c) => c.effect.startsWith('A snag')).every((c) => c.effect === 'A snag with 20 HP: attack it down and it opens.')).toBe(true)
    // Snags are drawn as snags, walls as cracks.
    for (const c of breaks) expect(c.snag === true, c.effect).toBe(c.effect.startsWith('A snag'))
    expect(breaks.filter((c) => c.snag)).toHaveLength(6)
    expect(breaks.length).toBeGreaterThan(50)
  })

  it("draws houses and inns as tiles of their own (Avo 10 like a village, but no looter goes for them)", () => {
    const at = (m: ChapterMap, t: [number, number]) => rowCodes(m.grid[m.height - t[1]])[t[0] - 1]
    // Every village stands on a village tile and every house on a house tile.
    for (const m of FE8_MAPS)
      for (const o of m.objects)
        if (o.type === 'village') expect(at(m, o.tile), `${m.id} (${o.tile.join(', ')})`).toBe(o.note?.includes('(A house.)') ? 'ot' : 'oc')
    expect(FE8_TERRAIN.ot).toMatchObject({ name: 'House / inn', avo: 10 })
    expect(FE8_MAPS.some((m) => m.grid.some((row) => rowCodes(row).includes('oe')))).toBe(false)
  })

  it('shows each trap list: ballistae, fire tiles, gas vents, arrow launchers, and the extra ones on Hard', () => {
    const traps = (id: string, kind: string) => map(id).objects.filter((o) => o.type === 'trap' && o.kind === kind)
    expect(traps('fe8-ruins-5', 'gas')).toHaveLength(21)
    expect(traps('fe8-tower-8', 'arrow').map((o) => (o.type === 'trap' ? o.note : ''))).toEqual([
      'It fires arrows down column 4 every 2 turns, the first time after 3 turns.',
      'It fires arrows down column 20 every 2 turns, the first time after 2 turns.',
    ])
    // Ruins 9's list on Hard adds twenty fire tiles to its thirty.
    const fire = traps('fe8-ruins-9', 'fire')
    expect(fire.filter((o) => o.type === 'trap' && o.difficulties?.join() === 'Hard')).toHaveLength(20)
    expect(fire[0].type === 'trap' && fire[0].note).toBe('Fire bursts from it every turn, the first time after 1 turn: 10 damage to a unit standing on it.')
    // An Archer or Sniper fires a ballista standing on it.
    const ballistae = FE8_MAPS.flatMap((m) => m.objects.filter((o) => o.type === 'ballista'))
    expect(ballistae).toHaveLength(8)
    for (const b of ballistae) expect(b.type === 'ballista' && b.mounted).toBe(true)
  })

  it("never takes an end scene's cast for the battle's units", () => {
    // Chapter 4's end scene casts Eirika, Seth, L'Arachel, Dozla and Rennac; only Lute joins during the battle.
    expect((map('fe8-4').joiners ?? []).map((j) => j.name)).toEqual(['Lute'])
    // Lyon only speaks in Chapter 18's and the Final's end scenes.
    for (const id of ['fe8-eirika-18', 'fe8-ephraim-18', 'fe8-eirika-final', 'fe8-ephraim-final'])
      expect((map(id).reinforcements ?? []).flatMap((g) => g.units).some((u) => u.name === 'Lyon'), id).toBe(false)
  })

  it("keeps the skull for the chapter's own boss, and names an army's units by class", () => {
    const type = (id: string, name: string) => [...new Set(allUnits(map(id)).filter((u) => u.name === name).map((u) => u.type))]
    // The defeat quote that sets flag 2 names each chapter's boss: Beran, not Selena, in Ephraim's Chapter 10; Aias, not the Pablo
    // who arrives, in Eirika's Chapter 13; the Cyclops whose fall ends Ephraim's Chapter 12, not Caellach.
    expect(type('fe8-ephraim-10', 'Selena')).toEqual(['named'])
    expect(type('fe8-ephraim-10', 'Beran')).toEqual(['boss'])
    expect(type('fe8-eirika-13', 'Pablo')).toEqual(['named'])
    expect(type('fe8-ephraim-12', 'Caellach')).toEqual(['named'])
    expect(type('fe8-ephraim-12', 'Cyclops')).toContain('boss')
    // A seize map's tie goes to the unit on the seize tile: Morva, not Riev.
    expect(type('fe8-eirika-20', 'Riev')).toEqual(['named'])
    expect(type('fe8-eirika-20', 'Morva')).toEqual(['boss'])
    // 'Monster' and Chapter 5's 'Bandit' are army names: those units go by their class.
    for (const m of FE8_MAPS) for (const u of allUnits(m)) expect(['Monster', 'Bandit', 'Enemy'], `${m.id}`).not.toContain(u.name)
    expect(type('fe8-tower-1', 'Entombed')).toEqual(['boss'])
    expect(Object.values(FE8_ITEM_SOURCES).flat().some((s) => s.text.includes('Monster'))).toBe(false)
  })

  it('shows the Tower and the Ruins with their random monsters as spawn points, and nothing on tiles no one can enter', () => {
    const tower = map('fe8-tower-1')
    expect(tower.units.filter((u) => u.name === 'Random monster').length).toBeGreaterThan(10)
    expect(tower.units.find((u) => u.name === 'Random monster')!.carries).toBeUndefined()
    expect(tower.objects).toEqual([])
  })
})

describe("The Sacred Stones' story under the spoiler block", () => {
  it("walks the Prologue to Chapter 8, then Eirika's route or Ephraim's", () => {
    expect(walkFork(FE8_FORK, '').story.maps).toHaveLength(10)
    const e = walkFork(FE8_FORK, 'eirika').story.maps.map((m) => m.id)
    expect(e).toContain('fe8-eirika-11')
    expect(e).not.toContain('fe8-ephraim-9')
    expect(e[e.length - 1]).toBe('fe8-eirika-final-2')
    const reached = new Set<string>()
    for (const r of ['eirika', 'ephraim']) for (const m of walkFork(FE8_FORK, r).story.maps) reached.add(m.id)
    for (const m of FE8_MAPS.filter((x) => x.route !== 'Extra' && x.route !== 'Skirmish')) expect(reached.has(m.id), m.id).toBe(true)
  })

  it("lists the shared chapters under a button of their own leading into each route, as Fates does (the user's call)", () => {
    const routes = FE8_MAP_SET.routes!
    expect(routes.list).toEqual(['Prologue', 'Eirika', 'Ephraim'])
    const shared = routes.maps('Prologue').map((m) => m.id)
    expect(shared[0]).toBe('fe8-prologue')
    expect(shared.at(-1)).toBe('fe8-8')
    expect(shared).toHaveLength(10)
    for (const r of ['Eirika', 'Ephraim']) {
      expect(routes.maps(r)[0].id).toBe(`fe8-${r.toLowerCase()}-9`)
      expect(routes.maps(r).some((m) => m.route === 'Shared')).toBe(false)
    }
    expect(routes.of(map('fe8-4'))).toBe('Prologue')
    expect(routes.of(map('fe8-ephraim-14'))).toBe('Ephraim')
    // The skirmishes fought on a shared chapter's map go with the shared chapters as well.
    expect(routes.side('Prologue').map((m) => m.skirmishOf)).toEqual(['fe8-4', 'fe8-4', 'fe8-4', 'fe8-6', 'fe8-6', 'fe8-6'])
  })

  it("lists the world map's skirmishes with the Tower and the Ruins: each location's three line-ups on its chapter's map, destroyed", () => {
    // The event data's +0x30-+0x38 (your deploy tiles) and +0x3C-+0x44 (the monsters), picked by one index (0x08083348, 0x080833B0).
    const sk = FE8_MAPS.filter((m) => m.route === 'Skirmish')
    expect(sk).toHaveLength(33)
    // Optional maps to fight again, so side maps (the user's call): no dropdown of their own.
    expect(FE8_MAP_SET.routes!.third).toBeUndefined()
    const side = FE8_MAP_SET.routes!.side
    const tower = FE8_MAPS.filter((m) => m.route === 'Extra')
    for (const r of ['Eirika', 'Ephraim']) {
      expect(side(r).slice(0, tower.length)).toEqual(tower)
      expect(side(r).filter((m) => m.route === 'Skirmish')).toHaveLength(27)
      expect(FE8_MAP_SET.routes!.maps(r).some((m) => m.route === 'Skirmish')).toBe(false)
    }
    expect(side('Eirika').some((m) => m.id.includes('ephraim'))).toBe(false)
    const zaha = map('fe8-skirmish-zaha-woods-1')
    expect(zaha).toMatchObject({ title: "Za'ha Woods, line-up 1", skirmishOf: 'fe8-4', victory: 'Rout the enemy', objects: [] })
    expect(FE8_MAP_SET.chapterLabel(zaha)).toBe("Skirmish: Za'ha Woods, line-up 1")
    expect([zaha.width, zaha.height]).toEqual([map('fe8-4').width, map('fe8-4').height])
    expect(zaha.starts).toHaveLength(8)
    expect(zaha.units.length).toBeGreaterThan(10)
    expect(zaha.units.every((u) => u.type !== 'boss')).toBe(true)
    // Destroyed, as the game has it (the user, in the game: like Fates' scout maps): every change of the chapter made at once, so no
    // village, house, shop, arena or door is left; Za'ha Woods' villages lie in ruins (tm). A chapter with no changes keeps its map.
    const codes = (m: ChapterMap) => m.grid.join('').match(/../g)!
    const story4 = codes(map('fe8-4'))
    const ruined = codes(zaha)
    expect(story4.filter((c) => c === 'oc')).toHaveLength(2)
    story4.forEach((c, i) => c === 'oc' && expect(ruined[i]).toBe('tm'))
    for (const m of sk) expect(codes(m).filter((c) => ['oc', 'od', 'ot', 'om', 'on', 'oo', 'ob'].includes(c)), m.id).toEqual([])
    expect(map('fe8-skirmish-hamill-canyon-1').grid).toEqual(map('fe8-eirika-13').grid)
    expect(zaha.notes[1]).toMatch(/villages lie in ruins and its snags are cleared to bridges/)
    // The skirmish's opening (0x089FFC30) places a share of a line-up's bit-14 monsters (0x0800F914): Za'ha Woods' three Bonewalkers
    // always come, its 18 random monsters by the share; Neleras Peak's first line-up has none to leave out, and its opening turns
    // the fog off (0x29 with 0).
    const maybe = (m: ChapterMap) => m.units.filter((u) => u.note?.includes('may not appear at all')).length
    expect([maybe(zaha), zaha.units.length]).toEqual([18, 21])
    expect(zaha.notes).toContain(
      'Of the monsters that may not appear, the game places a share it picks as the map loads: none (50% of the time), 40% of them ' +
        '(25%), 60% of them (15%), 80% of them (5%) or all of them (5%), which ones at random.',
    )
    expect(zaha.notes).toContain('Fog of war comes half the time (vision 3).')
    const neleras = map('fe8-skirmish-neleras-peak-eirika-1')
    expect(maybe(neleras)).toBe(0)
    expect(neleras.notes.some((n) => n.includes('may not appear'))).toBe(false)
    expect(neleras.notes).toContain("No fog of war: the skirmish's opening turns it off.")
    expect(maybe(map('fe8-skirmish-neleras-peak-eirika-2'))).toBe(22)
    // The story's chapter says its map is fought on again.
    expect(map('fe8-4').notes).toContain(
      "Its destroyed map is fought on again when the world map's monsters reach Za'ha Woods: a side map, in three line-ups.",
    )
    // Melkaen Coast's map (chapter 57) is a skirmish's alone.
    expect(map('fe8-skirmish-melkaen-coast-1').skirmishOf).toBeUndefined()
    // Under the block a skirmish opens once its location's chapter is cleared, at the story's end where the route plays no chapter
    // there (Melkaen Coast; Bethroen on Eirika's route), and never on a route that doesn't have it.
    const before = walkFork(FE8_FORK, '').story
    expect(before.opensAt!('fe8-skirmish-zaha-woods-1')).toBe(before.maps.findIndex((m) => m.id === 'fe8-4') + 1)
    const eirika = walkFork(FE8_FORK, 'eirika').story
    expect(eirika.opensAt!('fe8-skirmish-narube-river-ephraim-1')).toBe(Infinity)
    expect(eirika.opensAt!('fe8-skirmish-narube-river-eirika-1')).toBe(eirika.maps.findIndex((m) => m.id === 'fe8-eirika-17') + 1)
    expect(eirika.opensAt!('fe8-skirmish-melkaen-coast-1')).toBe(eirika.maps.length - 1)
    expect(eirika.opensAt!('fe8-skirmish-bethroen-1')).toBe(eirika.maps.length - 1)
    expect(before.opensAt!('fe8-skirmish-bethroen-1')).toBe(Infinity)
  })

  it('names chapters by route without the block', () => {
    expect(FE8_STORY.name(map('fe8-ephraim-13'))).toBe("Chapter 13, Ephraim's route")
    expect(FE8_STORY.name(map('fe8-5x'))).toBe('Chapter 5x')
  })
})

describe("The Sacred Stones' weapons, triangle and supports", () => {
  it('reads the item table: the legendary weapons double Mt where the rest triple it', () => {
    const w = (name: string) => FE8_WEAPONS.find((x) => x.name === name)!
    expect(w('Sieglinde')).toMatchObject({ effectiveMultiplier: 2, effective: ['dragon', 'monster'] })
    expect(w('Rapier').effectiveMultiplier).toBeUndefined()
    expect(w('Rapier').rules).toContain('Eirika only')
  })

  it("reads the magic swords as The Blazing Blade's: the Wind Sword (0xA1) anima from 2 tiles away, the Runesword dark at any range", () => {
    const w = (name: string) => FE8_WEAPONS.find((x) => x.name === name)!
    expect(w('Wind Sword').rules).toEqual([
      "Strikes with anima magic from 2 tiles away (Anima in the weapon triangle): half the wielder's Str adds to its Mt, rounded up, " +
        "and it can't land critical hits",
      'The target defends with its Res at either range',
    ])
    expect(w('Light Brand').rules?.[1]).toBe('The target defends with its Res at either range')
    expect(w('Runesword').rules?.[0]).toMatch(/^Strikes with dark magic \(Dark in the weapon triangle\)/)
  })

  it('lists only what turns up, marking what only foes carry', () => {
    for (const x of FE8_LISTED) expect(FE8_ITEM_SOURCES[x.name]?.length, x.name).toBeGreaterThan(0)
    expect(FE8_LISTED.find((x) => x.name === 'Iron Sword')!.foeOnly).toBeUndefined()
    expect(FE8_LISTED.find((x) => x.name === 'Wind Sword')!.foeOnly).toBe(true)
  })

  it('reads the world map towns\' shops, open from the chapter after the town\'s', () => {
    expect(FE8_ITEM_SOURCES['Iron Sword']).toContainEqual({ mapId: 'fe8-2', kind: 'town-shop-later', text: 'Sold at the armory in Ide (world map)' })
    expect(FE8_ITEM_SOURCES['Brave Sword']).toContainEqual({
      mapId: 'fe8-ephraim-14',
      kind: 'town-shop-later',
      text: 'Sold at the secret shop in Grado Keep (world map), with a Member Card',
    })
  })

  it("counts a unit's starting items once per route, where it joins", () => {
    const joins = new Map<string, Set<string>>()
    for (const list of Object.values(FE8_ITEM_SOURCES)) {
      for (const s of list.filter((x) => x.kind.startsWith('kit'))) {
        const who = s.text.match(/^Carried by (.+?)(,| on)/)![1]
        const route = map(s.mapId).route
        for (const r of route === 'Shared' ? ['Eirika', 'Ephraim'] : [route]) {
          const key = `${who} on ${r}'s route`
          joins.set(key, new Set([...(joins.get(key) ?? []), s.mapId]))
        }
      }
    }
    for (const [who, chapters] of joins) expect([...chapters], who).toHaveLength(1)
    expect(FE8_ITEM_SOURCES['Sieglinde'].map((s) => `${s.mapId}: ${s.text}`)).toEqual([
      'fe8-eirika-16: Given to Eirika at the end of the chapter',
      'fe8-ephraim-16: Given to Eirika at the end of the chapter',
    ])
  })

  it('gives the triangle 15 hit and 1 Mt, and supports at 81, 161 and 241 points', () => {
    expect([FE8_TRIANGLE.hit, FE8_TRIANGLE.mt]).toEqual([15, 1])
    expect(FE8_SUPPORTS.levels).toEqual({ C: 81, B: 161, A: 241 })
  })
})

// The review of every map (2026-11-13): the ground drawn tile by tile as its art shows it (scripts/gba_ground.py's looks).
describe("The Sacred Stones' ground as its art draws it", () => {
  const codes = (id: string) => map(id).grid.flatMap(rowCodes)
  it("draws its towns' roads as cobbles, its dirt paths as dirt and its docks' planks as boards, each with its terrain's numbers", () => {
    expect(codes('fe8-5').filter((c) => c === 'gf')).toHaveLength(167) // Serafew's paved streets: every road tile
    expect(codes('fe8-5').includes('tl')).toBe(false)
    expect(codes('fe8-1').filter((c) => c === 'ga').length).toBeGreaterThan(5) // the yellow ground by the shore
    expect(codes('fe8-3').filter((c) => c === 'gi').length).toBeGreaterThan(40) // Borgo's fort, floored in planks
    expect(FE8_TERRAIN.gf!.move).toEqual(FE8_TERRAIN.tl!.move)
    expect(FE8_TERRAIN.ga!.move).toEqual(FE8_TERRAIN.t0!.move)
    expect(FE8_TERRAIN.gi!.move).toEqual(FE8_TERRAIN.t1!.move)
    // The grass keeps its own colour: Serafew's no longer the cobbles' tan blended in.
    const [r, g] = [1, 3].map((i) => parseInt(map('fe8-5').fills!.t0!.slice(i, i + 2), 16))
    expect(g).toBeGreaterThan(r)
  })
})
