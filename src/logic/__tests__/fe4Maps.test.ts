import { describe, expect, it } from 'vitest'
import { FE4_ITEM_SOURCES } from '../../data/fe4/fe4ItemSources'
import { FE4_LISTED } from '../../data/fe4/fe4Listed'
import { FE4_MAP_SET, FE4_STORY } from '../../data/fe4/fe4MapSet'
import { FE4_MAPS } from '../../data/fe4/fe4Maps'
import { FE4_MOVE_CLASSES, FE4_TERRAIN } from '../../data/fe4/fe4Terrain'
import type { ChapterMap } from '../../data/maps/types'
import { atStart, rowCodes, terrainInfo, terrainName } from '../maps'

const map = (heading: string) => FE4_MAPS.find((m) => m.heading === heading)!
const castles = (m: ChapterMap) => m.objects.filter((o) => o.type === 'castle')
const villages = (m: ChapterMap) => m.objects.filter((o) => o.type === 'village')

describe("Genealogy of the Holy War's maps", () => {
  it('has the twelve chapters in order, each the grid inside the border no unit enters: the Prologue 62 x 30, the rest 62 x 62', () => {
    expect(FE4_MAPS.map((m) => m.heading)).toEqual(['Prologue', 'Ch.1', 'Ch.2', 'Ch.3', 'Ch.4', 'Ch.5', 'Ch.6', 'Ch.7', 'Ch.8', 'Ch.9', 'Ch.10', 'Endgame'])
    for (const m of FE4_MAPS) {
      // $86:AE80 fills columns 0 and 63 and the top and bottom rows with 0xFF before every movement search.
      expect([m.width, m.height], m.id).toEqual([62, m.id === 'fe4-prologue' ? 30 : 62])
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it('gives every tile a terrain the table knows, with a cost for every movement type', () => {
    for (const code of new Set(FE4_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))) {
      const info = FE4_TERRAIN[code]
      expect(info, code).toBeDefined()
      for (const mc of FE4_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
    }
  })

  it("reads the terrain as the game does: villages, castles and Serenes' avoid values", () => {
    const prologue = FE4_MAPS[0]
    const codes = new Set(prologue.grid.flatMap((r) => rowCodes(r)))
    expect(codes.has('oc')).toBe(true)
    expect(codes.has('ol')).toBe(true)
    expect(FE4_TERRAIN.oc!.avo).toBe(20)
    expect(FE4_TERRAIN.ba!.avo).toBe(20)
    expect(FE4_TERRAIN.bt!.avo).toBe(40)
    expect(FE4_TERRAIN.bm!.avo).toBe(30)
    expect(FE4_TERRAIN.we!.avo).toBe(-30)
    // Only pirates wade the sea; fliers cross anything but walls.
    expect(FE4_TERRAIN.we!.move['Pirates']).toBe(5)
    expect(FE4_TERRAIN.we!.move['Knights']).toBeNull()
    expect(FE4_TERRAIN.wb!.move['Fliers']).toBe(1)
  })

  it("places the units from the game's lists: every one inside its map, on a tile someone can stand on", () => {
    for (const m of FE4_MAPS) {
      const all = [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
      expect(all.length, m.id).toBeGreaterThan(10)
      for (const u of all) {
        const [x, y] = u.tile
        expect(x >= 1 && x <= m.width && y >= 1 && y <= m.height, `${m.id} ${u.name} ${u.tile}`).toBe(true)
        const code = rowCodes(m.grid[m.height - y])[x - 1]
        const info = FE4_TERRAIN[code]!
        // Units stand where no movement cost reaches only inside a castle (a boss defending it) or as a ballista.
        const walkable = Object.values(info.move).some((c) => c !== null)
        if (!walkable) expect(code === 'ol' || u.type === 'boss' || u.type === 'named', `${m.id} ${u.name} on ${code}`).toBe(true)
      }
    }
  })

  it("names the Prologue's bosses as Lil' Nordion's dialogue does and gives a foe the weapons its record holds", () => {
    const prologue = FE4_MAPS[0]
    const dimaggio = prologue.units.find((u) => u.name === 'DiMaggio')!
    // The skull is a castle's holder's: Gerald holds Evans; DiMaggio stands below Yngvi, where Midir is.
    expect(dimaggio.type).toBe('named')
    expect(prologue.units.find((u) => u.name === 'Gerald')).toMatchObject({ type: 'boss', note: 'Axe Fighter, Lv 20. Holds Evans.' })
    expect(dimaggio.tile).toEqual([34, 5])
    expect(dimaggio.carries).toEqual(['Steel Axe'])
    expect(prologue.units.some((u) => u.name === 'Gerald')).toBe(true)
    expect(prologue.units.filter((u) => u.name === 'Barbarian').length).toBeGreaterThan(10)
  })

  it('wins each chapter by seizing the castle whose scene ends it, and loses it with the lord or the home castle', () => {
    const won = FE4_MAPS.map((m) => m.victory)
    expect(won).toEqual([
      'Seize Evans with Sigurd', 'Seize Verdane with Sigurd', 'Seize Agusti with Sigurd', 'Seize Orgahil with Sigurd',
      'Seize Zaxon with Sigurd', 'Seize Velthomer with Sigurd', 'Seize Ribaut with Seliph', 'Seize Ulster with Seliph',
      'Seize Meath with Seliph', 'Seize Thracia with Seliph', 'Seize Chalphy with Seliph', 'Seize Belhalla with Seliph',
    ])
    for (const m of FE4_MAPS) {
      const home = castles(m)[0]
      expect(m.defeat, m.id).toBe(`${m.lord} is defeated, or the enemy seizes ${home.type === 'castle' && home.name}`)
      // The lord starts where the opening puts them (Sigurd outside Chalphy), or in the home castle.
      expect(m.starts, m.id).toContainEqual(m.corrinStart)
      // Each castle is the castle tile on the map.
      for (const c of castles(m)) expect(rowCodes(m.grid[m.height - c.tile[1]])[c.tile[0] - 1], `${m.id} ${c.tile}`).toBe('ol')
    }
    expect(castles(map('Prologue')).map((c) => c.type === 'castle' && c.name)).toEqual(['Chalphy', 'Yngvi', 'Evans'])
  })

  it("gives each village 5000 gold, and the items Serenes' item-locations page lists for the villages", () => {
    for (const m of FE4_MAPS) for (const v of villages(m)) expect(v.type === 'village' && v.reward, m.id).toBe('5000 gold')
    // A village covers six tiles but is visited from its door alone (the location kind's entrance, $87:F453): one object each.
    // Each note ends with the raids (no raze toggle: the user's call); what comes before is the village's gift.
    const RAIDS = / ?A foe standing on its door raids it for 500 gold at a time; as its 5,000 gold runs out its houses fall to ruins\.$/
    const extra = (h: string) => [
      ...new Set(villages(map(h)).flatMap((v) => (v.type === 'village' && v.note?.replace(RAIDS, '') ? [v.note.replace(RAIDS, '')] : []))),
    ]
    expect(villages(map('Prologue')).length).toBe(5)
    // Serenes (fan names): Speed Ring (P), Bargain Ring and Armour Cutter (2), Wing Clipper and Rest staff (3), Defender (4, Sylvia).
    expect(extra('Prologue')).toEqual(['Also gives a Speed Ring.'])
    expect(extra('Ch.2')).toEqual(['Also gives a Bargain Bracelet.', 'Also gives an Ironbane Sword.'])
    expect(extra('Ch.3')).toEqual(['Also gives a Wing Clipper.', 'Also gives a Restore Staff.'])
    expect(extra('Ch.4')).toEqual(['Visited by Silvia: Safeguard as well.'])
  })

  it("says when each later group arrives, from the event table's turn and flag blocks", () => {
    expect(map('Prologue').reinforcements!.map((g) => g.when)).toEqual(['At the start of the enemy phase after you seize Yngvi.'])
    expect(map('Endgame').reinforcements!.at(-1)!.when).toBe('At the start of the enemy phase after Groups 4 and 5 arrive.')
    // Every group has a trigger read from the scripts (Chapter 5's ambush: a talk whose action sets the flag itself).
    const unread = FE4_MAPS.flatMap((m) => (m.reinforcements ?? []).filter((g) => /not been read/.test(String(g.when))).map((g) => `${m.id} ${g.label}`))
    expect(unread).toEqual([])
    // Sigurd's talk with Ida runs the scene that ends Chapter 5: Arvis and his men are that scene's cast, no group on the map.
    expect(map('Ch.5').reinforcements!.map((g) => g.label)).toEqual(['Group 1', 'Group 2'])
    expect(map('Ch.5').notes).toContain('The chapter also ends after Sigurd talks to Ida.')
  })

  it("draws each army as it stands toward yours when it comes, and says when that changes (event commands 4B and 4D)", () => {
    const joiners = (heading: string, when: string) => map(heading).joiners!.filter((j) => j.when === when)
    // Chapter 1: Elliot's army, made when Genoa or Marpha falls (4B 05 09), comes hostile; Eldigan's comes as your ally.
    expect(map('Ch.1').reinforcements!.find((g) => g.units.some((u) => u.name === 'Elliot'))).toMatchObject({
      label: 'Group 2', when: 'At the start of the enemy phase after you seize Genoa or you seize Marpha.',
    })
    const eldigan = joiners('Ch.1', 'At the start of the allied phase after Group 2 arrives.')
    expect(eldigan.length).toBe(9)
    expect(eldigan.every((j) => j.ally && !j.neutral)).toBe(true)
    // Chapter 2: the first Agustrian armies come neutral, and turn hostile as the next arrive hostile (4D 01 03 00).
    const neutral = joiners('Ch.2', "Turn 1, at the start of a neutral army's phase.")
    expect(neutral.length).toBe(9)
    expect(neutral.every((j) => j.neutral && /Turns hostile when Group [12] arrives\.$/.test(j.note ?? ''))).toBe(true)
    // Chapter 3: Eldigan's army turns hostile on arriving, so Papilio's wyverns, after him, come hostile too.
    expect(map('Ch.3').reinforcements!.map((g) => [g.label, g.when])).toContainEqual(['Group 2', 'At the start of the enemy phase after Lachesis talks to Eldigan or Eldigan is defeated.'])
    // Chapter 5: Travant's army is made neutral before his wyverns come, and turns hostile as the scripts say.
    const travant = map('Ch.5').joiners!.find((j) => j.name === 'Travant')!
    expect(travant).toMatchObject({ neutral: true, ally: true, when: "At the start of a neutral army's phase after you seize Lübeck." })
    expect(travant.note).toMatch(/Turns hostile after Quan is defeated and Ethlyn is defeated, or when you seize Fionnuala, or when Ethlyn is defeated\. Leaves the map /)
    // The Final Chapter makes army 1 anew for Arion's men: Altena's talk turns them, and no one of the army's earlier making.
    const turned = FE4_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)])
      .filter((u) => u.note?.includes('Turns friendly when Altena talks to Arion.'))
    expect(turned.length).toBe(6)
    // Units no one drew before: Chapter 8's Asaello / Febail on turn 3 (event command 4F loads his list) and Ishtar walking in on turn 5.
    expect(map('Ch.8').reinforcements!.map((g) => [g.when, g.units.map((u) => u.name)])).toEqual(expect.arrayContaining([
      ['Turn 3, at the start of the enemy phase.', ['Febail']],
      ['Turn 5, at the start of the enemy phase.', ['Ishtar']],
    ]))
    // The Final Chapter's Scorpio comes once your units reach one of three areas, drawn.
    expect(map('Endgame').reinforcements![1].areas).toHaveLength(3)
    // Joiners from the triggers too: Midir when Yngvi is seized, Deirdre when Sigurd reaches her.
    expect(map('Prologue').joiners!.find((j) => j.name === 'Midir')!.when).toBe('When you seize Yngvi.')
    expect(map('Ch.1').joiners!.find((j) => j.name === 'Deirdre')!.when).toBe('When Sigurd reaches the area (12, 20)-(17, 25).')
  })

  it("puts each talk on the unit you talk to, with everything it does (event triggers 0x04, 0x15 and 0x16)", () => {
    const unit = (heading: string, name: string) =>
      [...map(heading).units, ...(map(heading).reinforcements ?? []).flatMap((g) => g.units), ...(map(heading).joiners ?? [])].find((u) => u.name === name)!
    // Beowolf's talk takes 10,000 gold from the talker (0x55); Erinys's takes her four Pegasus Riders off the map.
    expect(unit('Ch.2', 'Beowolf').talk).toBe('Recruit: talk with any of your units for 10,000 gold')
    expect(unit('Ch.2', 'Erinys').talk).toBe('Recruit: talk with Lewyn; the 4 Pegasus Riders leave the map')
    expect(unit('Ch.3', 'Eldigan').talk).toBe('Talk with Lachesis: Lachesis receives a Lands Sword; Eldigan leaves the map')
    expect(unit('Ch.5', 'Byron').talk).toBe('Talk with Sigurd: Sigurd receives Tyrfing; Byron leaves the map')
    // 0x15 and 0x16 take a child and the substitute the game's table pairs them with ($86:9CA5) as one.
    expect(unit('Ch.6', 'Iuchar').talk).toBe('Recruit: talk with Larcei or Creidne; their army turns friendly')
    expect(unit('Ch.7', 'Tine').talk).toBe('Recruit: talk with Arthur or Amid')
    expect(unit('Endgame', 'Arion').talk).toBe('Talk with Altena: their army turns friendly')
    // A talk said on a unit isn't a note as well; one between two of your own units stays one.
    expect(FE4_MAPS.flatMap((m) => m.notes).filter((n) => /talks to (Beowolf|Erinys|Eldigan|Byron|Iuchar|Tine|Arion)\b/.test(n))).toEqual([])
    expect(map('Ch.3').notes).toContain('Ethlyn talks to Quan: Quan receives Gáe Bolg.')
  })

  it('gives every castle a foe holds a skull, names characters by what the game ties to them, and says who leaves the map', () => {
    const everyone = FE4_MAPS.flatMap((m) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)].map((u) => ({ m, u })))
    for (const { m, u } of everyone) {
      const castle = m.objects.find((o) => o.type === 'castle' && o.tile[0] === u.tile[0] && o.tile[1] === u.tile[1])
      if (u.type === 'boss') expect(u.note, `${m.id} ${u.name}`).toMatch(/Holds \S/)
      if (castle && u.type !== 'ally' && !(castle as { note?: string }).note?.startsWith('Your home castle')) expect(u.type, `${m.id} ${u.name}`).toBe('boss')
    }
    // Recruits are never skulls.
    for (const name of ['Jamke', 'Erinys', 'Altena', 'Hannibal', 'Julia']) expect(everyone.filter(({ u }) => u.name === name).every(({ u }) => u.type === 'named'), name).toBe(true)
    // The narration points at Kinbois (82 06 48 00); Elliot has his own battle quote; Eldigan's level isn't Serenes'.
    expect(map('Ch.1').units.find((u) => u.name === 'Cimbaeth')!.tile).toEqual([54, 25])
    expect(everyone.some(({ m, u }) => m.heading === 'Ch.2' && u.name === 'Elliot')).toBe(true)
    expect(everyone.find(({ m, u }) => m.heading === 'Ch.10' && u.name === 'Zaggam')!.u).toMatchObject({ type: 'boss', note: 'Dark Bishop, Lv 27. Holds Miletos.' })
    expect(map('Ch.10').joiners!.some((j) => j.name === 'Polemarch')).toBe(true)
    // Departures: the Prologue's Gandolf on turn 1; Chapter 8's Ishtar on turn 12, or after a battle (trigger 0x1A runs 0x74).
    expect(map('Prologue').units.filter((u) => u.note?.endsWith('Leaves the map on turn 1, at the start of the enemy phase.')).length).toBe(1)
    expect(everyone.find(({ m, u }) => m.heading === 'Ch.8' && u.name === 'Ishtar')!.u.note).toBe(
      'Sage, Lv 22 Leaves the map on turn 12, at the start of the enemy phase. Withdraws after a battle.')
    // A block's removal reaches only who is on the map by then: Eldigan's Cavaliers come after the Nordion messenger leaves.
    expect(map('Ch.1').joiners!.filter((j) => j.note?.includes('Leaves the map')).length).toBe(0)
  })

  it("draws the chapters' scripted map changes, and the opening's made before the battle (event command 0x5C)", () => {
    const code = (m: ChapterMap, [x, y]: [number, number]) => m.grid[m.height - y].slice(2 * (x - 1), 2 * x)
    const change = (heading: string, id: string) => map(heading).changes.find((c) => c.id === id)!
    expect(change('Prologue', 'change-17-12-15')).toMatchObject({ effect: 'On turn 1, at the start of the enemy phase: bridge becomes river.' })
    expect(change('Prologue', 'change-17-12-15').patch).toEqual([{ tile: [12, 16], becomes: 'tg' }])
    // Chapter 7's opening sets flag 0x2C and runs 0x5C: its six gates (a plain's numbers) are down from the start, the road under two
    // of them plain until flag 0x37 takes them away.
    expect(code(map('Ch.7'), [51, 11])).toBe('ta')
    expect(change('Ch.7', 'change-37-51-52').patch).toEqual([{ tile: [52, 11], becomes: 'tl' }])
    expect(map('Ch.7').changes.some((c) => c.id.startsWith('change-2c-'))).toBe(false)
  })

  it('has each castle seized from its gate, each village visited from its door, and says raided villages fall to ruins', () => {
    const code = (m: ChapterMap, [x, y]: [number, number]) => m.grid[m.height - y].slice(2 * (x - 1), 2 * x)
    for (const m of FE4_MAPS) {
      const seize = m.objectives[0].tiles[0]
      expect(code(m, seize), m.id).toBe('o0')
      expect(castles(m).some((c) => c.tile[0] === seize[0] && c.tile[1] === seize[1] + 2), m.id).toBe(true)
      // A raid is said in the village's note, never a change to preview (the user's call).
      for (const v of villages(m)) expect(v.note, m.id).toMatch(/raids it for 500 gold at a time; .* its houses fall to ruins/)
      expect(m.changes.some((c) => c.id.startsWith('raze')), m.id).toBe(false)
    }
    // Only fliers enter peaks, cliffs and Bragi Tower, and fliers get no Avoid from terrain ($83:9A3F).
    expect(FE4_TERRAIN.wb!.avo).toBe(0)
    expect(FE4_TERRAIN.wb!.name).toBe('Peak / Cliff / Bragi Tower')
  })

  it("names the terrain as Lil' Nordion's terrain window draws it, and costs and heals as the code does", () => {
    // fe4_names.terrain_names() checks each name against the patch's drawn letters.
    expect([FE4_TERRAIN.bt!.name, FE4_TERRAIN.wa!.name, FE4_TERRAIN.o0!.name, FE4_TERRAIN.ol!.name]).toEqual(['Thicket', 'Rampart', 'Gate', 'Castle'])
    // Where a code joins several names, each tile says its own: Chapter 3's two Bragi Tower tiles, Chapter 7's six gates.
    expect(terrainName(map('Ch.3'), map('Ch.3').terrainOverrides!.wb!.tileNames!['Bragi Tower'][0])).toBe('Bragi Tower')
    expect(map('Ch.7').terrainOverrides!.ta!.tileNames!.Gate).toHaveLength(6)
    expect(terrainInfo(map('Ch.1'), 'ta').name).toBe('Plain')
    // A table cost of 0 moves 0.7 ($86:A91A: [7, 10, 20, ...] tenths of a move); a Church heals in full.
    expect(FE4_TERRAIN.tl!.move.Knights).toBe(0.7)
    expect(FE4_TERRAIN.oj!.heal).toBe(100)
    expect(FE4_MAP_SET.terrainNote).toBe('Fliers get no Avoid from terrain.')
  })

  it("titles the chapters as Lil' Nordion's turn record does, the last one Endgame", () => {
    expect(FE4_MAPS.map((m) => m.title)).toEqual([
      'Birth of a Holy Knight', 'Lady of the Forest', 'Disturbance in Agustria', 'Eldigan, the Lionheart', 'Dance in the Skies',
      'Doorway to Destiny', 'Inheritors of Light', 'Beyond the Desert', 'Wyvern Knights of Thracia', 'For Whose Sake', 'Light and Dark',
      'End of the Holy War',
    ])
    expect(FE4_STORY.maps.map((m) => FE4_STORY.name(m))).toEqual(['Prologue', ...Array.from({ length: 10 }, (_, i) => `Chapter ${i + 1}`), 'Endgame'])
    expect(FE4_MAP_SET.mapLabel(map('Endgame'))).toBe('Endgame: End of the Holy War')
    // Every source is a chapter of the story.
    const ids = new Set(FE4_STORY.maps.map((m) => m.id))
    expect(Object.values(FE4_ITEM_SOURCES).flat().every((s) => ids.has(s.mapId))).toBe(true)
  })

  it('names no outside source in what the page shows', () => {
    const texts = JSON.stringify([FE4_MAPS, FE4_TERRAIN, FE4_ITEM_SOURCES, FE4_LISTED])
    expect(texts).not.toMatch(/Serenes|fireemblemwod|Fire Emblem Wiki/)
  })

  it('says nothing at the start about who comes later, under the spoiler block', () => {
    for (const m of FE4_MAPS) {
      const s = atStart(m)
      const texts = [...s.notes, ...(s.unconfirmed ?? []), ...s.units.map((u) => `${u.note ?? ''} ${u.talk ?? ''}`),
        ...s.objects.map((o) => ('note' in o ? (o.note ?? '') : ''))]
      expect(texts.filter((x) => /Group \d|arrives|appears on the map/i.test(x)), m.id).toEqual([])
    }
    // What stays is the start: a unit's own sentences, a village's gold and what anyone visiting finds.
    expect(atStart(map('Ch.2')).units.find((u) => u.name === 'Banneret')).toBeUndefined()
    expect(atStart(map('Ch.7')).objects.some((o) => 'note' in o && o.note?.includes('Laylea'))).toBe(false)
  })

  it("places the joins Serenes' recruitment page gives (turn 2: Azelle and Lex from the north; turn 3: Quan, Ethlyn and Finn from the east)", () => {
    const joins = map('Prologue').joiners!.map((j) => `${j.name} ${j.from} ${j.when}`)
    // They walk in from the border, so they're shown entering from its edge.
    expect(joins).toContain('Azelle 41,30 Turn 2, at the start of your phase.')
    expect(joins).toContain('Lex 41,30 Turn 2, at the start of your phase.')
    for (const n of ['Quan', 'Ethlyn', 'Finn']) expect(joins).toContain(`${n} 62,18 Turn 3, at the start of your phase.`)
    expect(map('Prologue').forced!.map((f) => f.name)).toEqual(['Naoise', 'Alec', 'Arden'])
    // Second generation: the child is drawn, and the substitute the game places when the child wasn't born is their stand-in
    // (the table at $86:9CA5), for joiners, the units the opening places and the units a 0x4F swap places alike.
    expect(map('Ch.6').joiners!.find((j) => j.name === 'Lester')!.standIn).toMatchObject({ name: 'Deimne', when: "Lester wasn't born" })
    expect(map('Ch.6').forced!.find((f) => f.name === 'Larcei')!.standIn).toEqual({ name: 'Creidne', when: "Larcei wasn't born" })
    const febail = map('Ch.8').reinforcements!.flatMap((g) => g.units).find((u) => u.name === 'Febail')!
    expect(febail.standIn).toMatchObject({ name: 'Asaello', note: 'Bow Fighter, Lv 9', talk: 'Recruit: talk with Patty or Daisy' })
    const notes = map('Prologue').notes
    expect(notes).toContain('Sigurd talks to Arvis (once Arvis appears on the map): Sigurd receives a Silver Sword; Arvis leaves the map.')
    expect(map('Ch.1').units.find((u) => u.name === 'Ayra')!.talk).toBe('Recruit: talk with Sigurd')
  })
})
