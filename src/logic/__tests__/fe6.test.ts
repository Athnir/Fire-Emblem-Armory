import { describe, expect, it } from 'vitest'
import { FE6_ITEM_SOURCES } from '../../data/fe6/fe6ItemSources'
import { FE6_LISTED } from '../../data/fe6/fe6Listed'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE6_FORK, FE6_STORY } from '../../data/fe6/fe6MapSet'
import { FE6_MOVE_CLASSES, FE6_TERRAIN } from '../../data/fe6/fe6Terrain'
import { FE6_WEAPONS } from '../../data/fe6/fe6Weapons'
import type { ChapterMap, Difficulty, ReinforcementGroup } from '../../data/maps/types'
import { FE6_SUPPORTS } from '../../data/fe6/fe6Supports'
import { gbaSupportBonus } from '../gbaSupports'
import { rowCodes } from '../maps'
import { walkFork } from '../spoiler'

const map = (id: string) => FE6_MAPS.find((m) => m.id === id)!
const objects = (m: ChapterMap, type: string) => m.objects.filter((o) => o.type === type)
const chests = (id: string) => objects(map(id), 'chest').map((o) => (o.type === 'chest' ? o.contents : '')).sort()
const villages = (id: string) => objects(map(id), 'village').map((o) => (o.type === 'village' ? o.reward : '')).sort()
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const sources = (item: string, kind: string) => (FE6_ITEM_SOURCES[item] ?? []).filter((s) => s.kind === kind).map((s) => `${s.mapId} ${s.text}`)

describe("The Binding Blade's maps", () => {
  it('has every chapter of both routes, the gaiden chapters and the five trial maps, each grid its own size', () => {
    expect(FE6_MAPS.filter((m) => m.route === 'Story')).toHaveLength(38)
    expect(FE6_MAPS.filter((m) => m.route === 'Trial').map((m) => m.title)).toEqual([
      'Valley of Death', 'Rainy Island', 'Snowy Defensive', "Pirate's Challenge", "Roy's Trial",
    ])
    for (const m of FE6_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    expect([map('fe6-1').width, map('fe6-1').height]).toEqual([15, 21])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    for (const code of new Set(FE6_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE6_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE6_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
  })

  it("reads the terrain table's numbers: forts heal 20%, thrones give Res, peaks only brigands, berserkers and fliers climb", () => {
    expect(FE6_TERRAIN.bb).toMatchObject({ def: 2, avo: 20, heal: 20 })
    expect(FE6_TERRAIN.bc).toMatchObject({ def: 3, res: 5, avo: 30, heal: 10 })
    expect(FE6_TERRAIN.bq!.res).toBe(10)
    const peak = FE6_TERRAIN.bu!.move
    expect(Object.entries(peak).filter(([, c]) => c !== null).map(([k]) => k)).toEqual(['Brigands', 'Berserkers', 'Fliers'])
    expect(FE6_TERRAIN.tg!.move['Pirates']).toBe(2)
    expect(FE6_TERRAIN.tg!.move['Cavaliers']).toBeNull()
    // A tile only fliers enter gives no Def or Avoid: fliers' rows are all 0.
    expect(FE6_TERRAIN.wh).toMatchObject({ def: 0, avo: 0 })
  })

  it('places every unit inside its map, and never an icon on a tile nobody can stand on', () => {
    for (const m of FE6_MAPS) {
      for (const u of allUnits(m)) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
      }
      for (const [x, y] of m.starts) expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} start ${x},${y}`).toBe(true)
    }
    for (const [code, info] of Object.entries(FE6_TERRAIN)) {
      if (['bh', 'bu', 'om', 'on', 'oo'].includes(code)) expect(Object.values(info!.move).some((c) => c !== null), code).toBe(true)
    }
  })

  it("starts each chapter with the enemies the Fire Emblem Wiki counts (its chapter data, Normal)", () => {
    // From each chapter page's "enemy" figure, reinforcements and later recruits left out.
    const wiki: Record<string, number> = {
      'fe6-1': 14, 'fe6-2': 20, 'fe6-3': 18, 'fe6-4': 16, 'fe6-5': 23, 'fe6-6': 28, 'fe6-7': 22, 'fe6-8': 29, 'fe6-8x': 31, 'fe6-9': 29,
      'fe6-10a': 23, 'fe6-11a': 22, 'fe6-10b': 26, 'fe6-11b': 24, 'fe6-12': 28, 'fe6-12x': 26, 'fe6-13': 40, 'fe6-14': 31, 'fe6-14x': 32,
      'fe6-15': 35, 'fe6-16': 32, 'fe6-16x': 31, 'fe6-17a': 28, 'fe6-18a': 32, 'fe6-19a': 37, 'fe6-20a': 32, 'fe6-20ax': 40,
      'fe6-17b': 29, 'fe6-18b': 31, 'fe6-19b': 44, 'fe6-20b': 33, 'fe6-20bx': 34, 'fe6-21': 35, 'fe6-21x': 45, 'fe6-22': 39,
      'fe6-23': 41, 'fe6-24': 27, 'fe6-final': 3, 'fe6-trial-1': 26, 'fe6-trial-2': 21, 'fe6-trial-3': 25, 'fe6-trial-4': 26,
      'fe6-trial-5': 25,
    }
    for (const m of FE6_MAPS) {
      const red = m.units.filter((u) => u.type !== 'ally' && (!u.difficulties || u.difficulties.includes('Normal')))
      expect(red.length, m.id).toBe(wiki[m.id])
    }
    // Hard places more from the start where a Hard-only turn-1 event does (Chapters 7, 21 and 22).
    const hardOnly = FE6_MAPS.filter((m) => m.units.some((u) => u.difficulties?.join() === 'Hard')).map((m) => m.id)
    expect(hardOnly).toEqual(['fe6-7', 'fe6-21', 'fe6-22'])
  })

  it("plays each opening: Chapter 1's bandits round Damas, Roy and the five knights on their tiles", () => {
    const m = map('fe6-1')
    expect(m.units.find((u) => u.name === 'Damas')).toMatchObject({ type: 'boss', carries: ['Steel axe'] })
    expect(m.corrinStart).toEqual([3, 3])
    expect(m.forced!.map((f) => f.name)).toEqual(['Marcus', 'Alen', 'Bors', 'Wolt', 'Lance'])
    expect(m.objectives).toEqual([{ type: 'seize', tiles: [[6, 17]], label: 'Seize the gate with Roy' }])
    // Chapter 3's late arrival: Slater comes on turn 3, after Zephiel, Idunn and Narcian leave the scene.
    const slater = map('fe6-3').reinforcements![0]
    expect(slater.when).toBe('Turn 3, enemy phase')
    expect(slater.units[0]).toMatchObject({ name: 'Slater', type: 'boss', tile: [20, 18] })
    expect(slater.units.map((u) => u.name)).not.toContain('Zephiel')
  })


  it('keeps one group per arrival, and says who sets an area off and when', () => {
    // The same units on the same tiles are one group, its time per difficulty; two such groups only where both come at once on
    // one difficulty (two copies arriving).
    const key = (g: ReinforcementGroup) =>
      JSON.stringify(g.units.map((u) => [u.name, u.tile, u.from, u.type, u.carries, u.drops, u.talk, (u.note ?? '').replace(/^Lv \d+( \([^)]*\))?/, '')]).sort())
    const whenOn = (g: ReinforcementGroup, d: Difficulty) => (typeof g.when === 'string' ? g.when : g.when?.[d])
    for (const m of FE6_MAPS) {
      const groups = m.reinforcements ?? []
      groups.forEach((g, i) =>
        groups.slice(i + 1).forEach((o) => {
          if (key(g) === key(o)) expect((['Normal', 'Hard'] as Difficulty[]).some((d) => whenOn(g, d) && whenOn(g, d) === whenOn(o, d)), `${m.id} ${g.label} ${o.label}`).toBe(true)
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

  it("names the seize points, Chapter 24's stretches between them, and the areas a flag's group waits on", () => {
    const whens = (id: string) => (map(id).reinforcements ?? []).map((g) => g.when)
    expect(whens('fe6-20bx')).toContain('When Roy seizes the seize point at (4, 19)')
    expect(whens('fe6-24')).toContain('Enemy phase of every even turn, once Roy seizes the seize point at (6, 25), until Roy seizes the seize point at (17, 27)')
    expect(map('fe6-24').unconfirmed).toContain(
      "The groups that wait on flag 17 stop once it's set as well; no event in the chapter sets it, and what does wasn't traced.",
    )
    // Chapter 7's group waits on the flag two areas set as they fire: both are drawn.
    const seven = map('fe6-7').reinforcements!.find((g) => g.areas)!
    expect(seven.when).toBe('As soon as one of your units stops in a marked area, until Debias is defeated')
    expect(seven.areas).toHaveLength(2)
    // Chapter 5 lists one Hard event twice: two copies come each turn, so the two groups stay two.
    const twice = map('fe6-5').reinforcements!.filter((g) => JSON.stringify(g.when) === JSON.stringify({ Hard: 'Every turn from 15 to 20, enemy phase, until Dory is defeated' }))
    expect(twice).toHaveLength(2)
    expect(whens('fe6-trial-4')).toContain('Once no unit of another army is left')
  })

  it("marks Hard's extra groups (event type 3) as Hard only, and the coded area checks with their areas", () => {
    // A Hard-only turn event needs flag 2 clear, which the boss's death sets (its death quote's flag): Slater arrives with the throne
    // room. Its turns are the village's group's own on Hard: one group, whose time says each difficulty's.
    const village = (map('fe6-3').reinforcements ?? []).find((g) => typeof g.when === 'object')!
    expect(village.when).toEqual({
      Normal: 'When the village at (4, 19) is visited',
      Hard: 'When the village at (4, 19) is visited; turns 5, 10 and 15, enemy phase, until Slater is defeated',
    })
    for (const u of village.units) expect(u.difficulties).toBeUndefined()
    // Chapter 6's trap: once nobody is left in the starting area, foes appear behind you.
    const trap = map('fe6-6').reinforcements!.find((g) => g.areas)!
    expect(trap.when).toBe('Enemy phase, once none of your units is left in the marked area')
    expect(trap.areas).toEqual([{ who: 'player', rect: [1, 1, 26, 9] }])
    // Chapter 5's area event tests for Hard itself: two Mercenaries and two Nomads come in from the west on Hard only (the Fire
    // Emblem Wiki's Hard-exclusive group).
    const west = map('fe6-5').reinforcements!.find((g) => g.areas && g.units.length === 4)!
    // Its script skips the group once flag 2 is set, so it stops once Dory falls; the wall beside the area opens either way.
    // The area's script goes on only on your phase (0x0806C4D9), and otherwise waits again: one of your units stopping there.
    expect(west.when).toEqual({ Hard: 'As soon as one of your units stops in the marked area, until Dory is defeated' })
    expect(map('fe6-5').changes).toEqual([
      expect.objectContaining({ trigger: 'event', tile: { default: [7, 6] }, effect: 'As soon as one of your units stops in the area at (8, 5)–(8, 6): the wall opens.' }),
    ])
    expect(map('fe6-5').changes[0].patch).toEqual([{ tile: [7, 6], becomes: 'ta' }, { tile: [7, 5], becomes: 'ta' }])
    expect(west.units.map((u) => u.name).sort()).toEqual(['Mercenary', 'Mercenary', 'Nomad', 'Nomad'])
    for (const u of west.units) expect(u.difficulties).toEqual(['Hard'])
  })

  it("names who recruits whom, matching a talk's character to its enemy version by name (Gonzalez in 10B)", () => {
    const talk = (id: string, name: string) => allUnits(map(id)).find((u) => u.name === name)?.talk
    expect(talk('fe6-4', 'Rutger')).toBe('Recruit: talk with Clarine')
    expect(talk('fe6-10b', 'Gonzalez')).toBe('Recruit: talk with Lilina')
    expect(talk('fe6-16', 'Hugh')).toMatch(/^Recruit: talk with Roy \(for gold: 10,000/)
    expect(talk('fe6-12', 'Cath')).toBe('Recruit: talk with Roy (on the third talk, counting one per chapter)')
    // Recruiting a squad's leader turns the squad green (0x2B sends each of its characters to the other army).
    expect(talk('fe6-11a', 'Klein')).toBe('Recruit: talk with Roy or Clarine; the 4 Archers turn green with Klein')
    expect(talk('fe6-13', 'Perceval')).toBe('Recruit: talk with Elffin or Larum; the 2 Cavaliers and the Sniper turn green with Perceval')
    const archers = allUnits(map('fe6-11a')).filter((u) => u.name === 'Archer' && u.note?.endsWith('turns green with Klein (a talk)'))
    expect(archers).toHaveLength(4)
    // Shanna's three coded talks with Thea (0x0806BB35/69/9D): a talk while Klein is a foe; once Klein is yours, a recruit after
    // that talk, or only Thea turning green without it.
    for (const id of ['fe6-10b', 'fe6-11a'])
      expect(talk(id, 'Thea')).toBe(
        'Recruit: talk with Klein, or with Shanna once Klein is yours, after an earlier talk while Klein was still a foe; ' +
          "Shanna's talk once Klein is yours, without that earlier talk, turns Thea green instead; the 4 Peg Knights turn green with Thea",
      )
  })

  it("holds the chests, villages and buried items Serenes Forest's item-locations page lists (the patch's names)", () => {
    expect(chests('fe6-6')).toEqual(['2000 gold', '3000 gold', '5000 gold', 'Goddess icon', 'Killer axe', 'Short bow', 'Silver lance', 'Unlock'])
    expect(chests('fe6-8')).toEqual(['Elfire', 'Elysian whip', 'Guiding ring', 'Killer bow', 'Knight crest', 'Light Brand', 'Secret book', 'Silver axe'])
    expect(chests('fe6-12x')).toHaveLength(12)
    // Serenes: one 5000G village in Chapter 1 (the brigand's is closed in the opening), Knightslayer = the patch's Horseslayer.
    expect(villages('fe6-1')).toEqual(['5000 gold'])
    expect(villages('fe6-7')).toEqual(['Elixir', 'Hero crest', 'Horseslayer', 'Killing edge', 'Longbow', 'Physic', 'Red gem', 'Torch'])
    expect(villages('fe6-10b')).toContain('Speedwings if visited by Ward or Lot; anyone else: Elixir')
    expect(villages('fe6-11b')).toEqual(['Red gem'])
    const sand = objects(map('fe6-14'), 'hidden').map((o) => (o.type === 'hidden' ? o.contents : ''))
    expect(sand.sort()).toEqual(['Boots', 'Guiding ring', 'Silence', 'Silver blade', 'Silver card', 'Speedwings', 'Talisman', 'Warp'])
    const ring = objects(map('fe6-14'), 'hidden').find((o) => o.type === 'hidden' && o.contents === 'Guiding ring')
    expect(ring?.type === 'hidden' && ring.note).toBe('Found only by Sophia, by stopping in the area.')
  })

  it("previews each cracked wall broken, with the chapter record's wall HP", () => {
    const breaks = FE6_MAPS.flatMap((m) => m.changes.filter((c) => c.trigger === 'breakable').map((c) => ({ id: m.id, effect: c.effect })))
    expect(breaks).toHaveLength(45)
    expect(new Set(breaks.map((b) => b.effect))).toEqual(new Set(['A cracked wall with 40 HP: attack it down and it opens.', 'A cracked wall with 100 HP: attack it down and it opens.']))
  })

  it("keeps the skull for the chapter's own boss, and names an army's units by class", () => {
    const type = (id: string, name: string) => [...new Set(allUnits(map(id)).filter((u) => u.name === name).map((u) => u.type))]
    // Narcian and Zephiel leave Chapter 13 on turn 2; Narcian comes back to hold the gate, so Flaer isn't its boss either.
    expect(type('fe6-13', 'Zephiel')).toEqual(['named'])
    expect(type('fe6-13', 'Narcian').sort()).toEqual(['boss', 'named'])
    expect(type('fe6-13', 'Flaer')).toEqual(['named'])
    // Bosses whose death doesn't set the boss's flag: Rose and Maggie in Arcadia, the four clan chiefs of 20B, Peres in 21.
    for (const [id, name] of [['fe6-14', 'Rose'], ['fe6-14', 'Maggie'], ['fe6-20b', 'Thoril'], ['fe6-21', 'Peres'], ['fe6-12', 'Flaer']])
      expect(type(id, name), `${id} ${name}`).toEqual(['named'])
    // The trial maps' 'Bandit' is an army name: its boss goes by its class.
    expect(type('fe6-trial-1', 'Berserker')).toContain('boss')
    for (const m of FE6_MAPS) for (const u of allUnits(m)) expect(u.name, m.id).not.toBe('Bandit')
  })

  it("says Chapter 9's two north-eastern villages close each other (the route split)", () => {
    const notes = objects(map('fe6-9'), 'village').flatMap((o) => (o.type === 'village' && o.note ? [o.note] : []))
    expect(notes).toEqual(['Visiting it closes the village at (22, 24).', 'Visiting it closes the village at (19, 24).'])
  })

  it("starts Chapter 6's rooms under their roofs, closed until a door opens, and previews what each door opens", () => {
    const m = map('fe6-6')
    const at = (x: number, y: number) => rowCodes(m.grid[m.height - y])[x - 1]
    // Sue waits in a closed room; its chests stay under the roof until its door opens.
    expect(at(3, 15)).toBe('ws')
    expect(m.units.find((u) => u.name === 'Sue')!.tile).toEqual([3, 15])
    expect(FE6_TERRAIN.ws!.move).toEqual(Object.fromEntries(FE6_MOVE_CLASSES.map((c) => [c, null])))
    // Ten doors: six with their own event, four scripted in pairs (opening either opens the room and its other door).
    const doors = m.changes.filter((c) => c.id.startsWith('door-'))
    expect(doors).toHaveLength(10)
    expect(objects(m, 'door')).toHaveLength(10)
    const west = doors.find((c) => c.id === 'door-6-15')!
    expect(west.effect).toBe('A locked door: open it with a key or a thief, and the room behind it opens.')
    expect(west.patch).toContainEqual({ tile: [6, 15], becomes: 'ta' })
    expect(west.patch).toContainEqual({ tile: [3, 15], becomes: 'ta' })
    expect(doors.find((c) => c.id === 'door-9-20')!.effect).toMatch(/Its other door at \(7, 18\) opens too\.$/)
    // A change's 0 tiles leave the corridor beside a room as it is.
    for (const d of doors) for (const p of d.patch ?? []) expect(p.becomes, `${d.id} ${p.tile}`).not.toBe('wa')
    // Elsewhere a door only opens itself; Chapter 3's throne room and Chapter 22's temple open by their scripts.
    expect(FE6_MAPS.filter((x) => x.grid.some((row) => rowCodes(row).includes('ws'))).map((x) => x.id)).toEqual(['fe6-3', 'fe6-6', 'fe6-22'])
  })

  it("makes the chapters' scripted map changes: the opening's before the battle, the rest previewed with what sets them off", () => {
    // Chapter 1's opening raids the village: it starts as ruins.
    const ch1 = map('fe6-1')
    for (const [x, y] of [[4, 12], [5, 13], [6, 14]]) expect(rowCodes(ch1.grid[ch1.height - y])[x - 1], `${x},${y}`).toBe('tm')
    const words = (id: string) => map(id).changes.filter((c) => c.id.startsWith('event-')).map((c) => c.effect)
    expect(words('fe6-3')).toEqual(['Turn 3, enemy phase: the closed room opens and the door opens.'])
    expect(words('fe6-19b')).toEqual(['Turn 12, enemy phase: the door opens and the fence opens.'])
    expect(words('fe6-22')).toEqual(['As soon as one of your units stops in the area at (15, 12)–(17, 12): the closed room opens and the wall opens.'])
  })

  it("marks looters from the movement AI: what each goes for, and the exits a leaver heads for", () => {
    for (const m of FE6_MAPS) {
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

  it("reads Cath's AI: the chests, then out by the chapter's exit; a unit the script removes gets no exit of its own", () => {
    const cath = map('fe6-6').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Cath')!
    expect(cath).toMatchObject({ looter: true, goesTo: [[15, 24]] })
    expect(cath.note).toBe('Lv 5 Thief; goes for the chests, emptying what it reaches, then leaves the map by an exit')
    // Flaer flies off on turn 1 (the script): the AI's own exit isn't said as well.
    const flaer = map('fe6-12').units.find((u) => u.name === 'Flaer')!
    expect(flaer.note).toBe('Lv 1 Wyvern Lord; leaves the map: turn 1, enemy phase')
    expect(flaer.goesTo).toBeUndefined()
  })

  it("says on Hard what Hard gives foes that their shown level doesn't, and when Chapter 14's fog lifts", () => {
    const hard = (id: string) => (map(id).notesOn ?? []).filter((n) => n.difficulties.join() === 'Hard').map((n) => n.note)
    // The chapter record's +0x17 levels of the class's growths: 4 in Chapter 1 up to 16 in the Final Chapter, none on a trial map.
    expect(hard('fe6-1')).toEqual([
      "On Hard, foes gain 4 levels' worth of their class's growth in HP, Str, Skl, Spd, Def, Res and Lck; their shown level stays the same.",
    ])
    expect(hard('fe6-final')[0]).toMatch(/^On Hard, foes gain 16 levels' worth/)
    for (const m of FE6_MAPS.filter((m) => m.route === 'Trial')) expect(m.notesOn, m.id).toBeUndefined()
    // A foe the chapter starts with whom the game's list gives none (the ones you can recruit); one an event places gains it all
    // the same (Perceval arriving in Chapter 15).
    expect(hard('fe6-12')[0]).toMatch(/ Raigh gains none\.$/)
    expect(hard('fe6-16')[0]).toMatch(/ Douglas and Hugh gain none\.$/)
    expect(hard('fe6-15')[0]).not.toMatch(/Perceval/)
    // Chapter 14's turn-26 script lifts the fog.
    expect(map('fe6-14')).toMatchObject({ fog: true, notes: expect.arrayContaining(['The fog lifts on turn 26, your phase.']) })
  })
})

describe("The Binding Blade's item sources", () => {
  it('names only maps that exist', () => {
    const ids = new Set(FE6_MAPS.map((m) => m.id))
    for (const [item, list] of Object.entries(FE6_ITEM_SOURCES)) for (const s of list) expect(ids.has(s.mapId), `${item} ${s.mapId}`).toBe(true)
  })

  it("gives the chapter-end gifts Serenes lists (Durandal after 8x, the Binding Blade after 21 or 21x), each yours from the next chapter", () => {
    expect(sources('Durandal', 'event-later')).toEqual(['fe6-8x Given to Roy at the end of the chapter'])
    expect(sources('Binding Blade', 'event-later')).toEqual(['fe6-21 Given to Roy at the end of the chapter', 'fe6-21x Given to Roy at the end of the chapter'])
    // A talk mid-battle hands its gift over then: yours from the next chapter too.
    expect(sources('Thunder', 'talk-later')).toEqual(['fe6-8 Lilina talks to Roy'])
    // A foe a talk recruits joins mid-battle: Perceval's gear counts from the chapter after the one he's recruited in.
    expect(sources('Silver lance', 'kit-later')).toContain('fe6-13 Carried by Perceval on joining')
    for (const [name, list] of Object.entries(FE6_ITEM_SOURCES))
      for (const s of list) expect(['event', 'talk'].includes(s.kind), `${name} ${s.mapId} ${s.kind}`).toBe(false)
    // Fa joins at the end of Chapter 15, so her stone counts from Chapter 16.
    expect(sources('Divinestone', 'kit-later')).toEqual(['fe6-15 Carried by Fae, who joins at the end of the chapter'])
  })

  it('lists what anything gives or a unit carries, and marks what only foes carry', () => {
    const listed = new Set(FE6_LISTED.map((w) => w.name))
    for (const name of ['Poison lance', 'Poison bow', 'Fortify']) expect(listed.has(name), name).toBe(false)
    const foeOnly = FE6_LISTED.filter((w) => w.foeOnly).map((w) => w.name)
    expect(foeOnly).toEqual(expect.arrayContaining(['Eckesachs', 'Runesword', 'Spear', 'Dark breath', 'Fenrir']))
    expect(foeOnly).not.toContain('Iron sword')
    expect(FE6_LISTED.length).toBe(FE6_WEAPONS.length - 3)
  })
})

describe("The Binding Blade's story and supports", () => {
  it('splits twice: 10A or 10B after Chapter 9, Ilia or Sacae after 16x, every route ending at the Final Chapter', () => {
    expect(FE6_FORK.before.maps.at(-1)!.id).toBe('fe6-9')
    for (const a of ['a', 'b']) {
      expect(walkFork(FE6_FORK, a).pending).toBeDefined()
      expect(walkFork(FE6_FORK, a).story.maps.at(-1)!.id).toBe('fe6-16x')
      for (const b of ['ilia', 'sacae']) {
        const { story, pending, chosen } = walkFork(FE6_FORK, `${a}/${b}`)
        expect(pending).toBeUndefined()
        expect(chosen).toHaveLength(2)
        expect(story.maps.at(-1)!.id).toBe('fe6-final')
        expect(story.maps).toHaveLength(31)
        expect(story.opensAt!('fe6-trial-1')).toBe(30)
        // The other route's chapters never open.
        expect(story.opensAt!(b === 'ilia' ? 'fe6-17b' : 'fe6-17a')).toBe(Infinity)
      }
    }
    expect(walkFork(FE6_FORK, 'b/sacae').story.maps.map((m) => m.heading)).toContain('Ch.20Bx')
    // An unknown choice stops the walk where it is.
    expect(walkFork(FE6_FORK, 'x').story).toBe(FE6_FORK.before)
    expect(FE6_STORY.maps).toHaveLength(38)
  })

  it('works a support bonus out as the battle code does: both rows times the level, halved once, rounded down', () => {
    // Fire (Atk 1, Hit 5, Avo 5, Crit 5) with a Thunder partner (Def 1, Avo 5, Crit 5, Dodge 5) at C.
    expect(gbaSupportBonus(FE6_SUPPORTS, 'Fire', [{ affinity: 'Thunder', level: 1 }])).toEqual({ atk: 0, def: 0, hit: 2, avoid: 5, crit: 5, dodge: 2 })
    // Two half points from two partners add up to a whole one.
    expect(gbaSupportBonus(FE6_SUPPORTS, 'Fire', [{ affinity: 'Thunder', level: 1 }, { affinity: 'Thunder', level: 1 }]).atk).toBe(1)
  })
})
