import { describe, expect, it } from 'vitest'
import { FE4_MAPS } from '../../data/fe4/fe4Maps'
import { FE4_MOVE_CLASSES, FE4_TERRAIN } from '../../data/fe4/fe4Terrain'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes } from '../maps'

const map = (heading: string) => FE4_MAPS.find((m) => m.heading === heading)!
const castles = (m: ChapterMap) => m.objects.filter((o) => o.type === 'castle')
const villages = (m: ChapterMap) => m.objects.filter((o) => o.type === 'village')

describe("Genealogy of the Holy War's maps", () => {
  it('has the twelve chapters in order, the Prologue 64 x 32 and the rest 64 x 64', () => {
    expect(FE4_MAPS.map((m) => m.heading)).toEqual(['Prologue', 'Ch.1', 'Ch.2', 'Ch.3', 'Ch.4', 'Ch.5', 'Ch.6', 'Ch.7', 'Ch.8', 'Ch.9', 'Ch.10', 'Final'])
    for (const m of FE4_MAPS) {
      expect([m.width, m.height], m.id).toEqual([64, m.id === 'fe4-prologue' ? 32 : 64])
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
  })

  it('gives every tile a terrain the table knows, with a cost for every movement type', () => {
    for (const m of FE4_MAPS) {
      for (const row of m.grid) {
        for (const code of rowCodes(row)) {
          const info = FE4_TERRAIN[code]
          expect(info, `${m.id} ${code}`).toBeDefined()
          for (const mc of FE4_MOVE_CLASSES) expect(mc in info!.move, `${code} ${mc}`).toBe(true)
        }
      }
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
    expect(dimaggio.type).toBe('boss')
    expect(dimaggio.tile).toEqual([35, 6])
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
    // Each village covers six tiles (the footprint the game checks), each carrying its contents.
    const extra = (h: string) => [...new Set(villages(map(h)).flatMap((v) => (v.type === 'village' && v.note ? [v.note] : [])))]
    expect(villages(map('Prologue')).length).toBe(5 * 6)
    // Serenes (fan names): Speed Ring (P), Bargain Ring and Armour Cutter (2), Wing Clipper and Rest staff (3), Defender (4, Sylvia).
    expect(extra('Prologue')).toEqual(['Also gives a Speed Ring.'])
    expect(extra('Ch.2')).toEqual(['Also gives a Bargain Bracelet.', 'Also gives an Ironbane Sword.'])
    expect(extra('Ch.3')).toEqual(['Also gives a Wing Clipper.', 'Also gives a Restore Staff.'])
    expect(extra('Ch.4')).toEqual(['Visited by Silvia: Safeguard as well.'])
  })

  it("says when each later group arrives, from the event table's turn and flag blocks", () => {
    expect(map('Prologue').reinforcements!.map((g) => g.when)).toEqual(['At the start of the enemy phase after you seize Yngvi.'])
    expect(map('Final').reinforcements!.at(-1)!.when).toBe('At the start of the enemy phase after Groups 3 and 4 arrive.')
    // Every group has a trigger read from the scripts (Chapter 5's ambush: a talk whose action sets the flag itself).
    const unread = FE4_MAPS.flatMap((m) => (m.reinforcements ?? []).filter((g) => /not been read/.test(String(g.when))).map((g) => `${m.id} ${g.label}`))
    expect(unread).toEqual([])
    expect(map('Ch.5').reinforcements!.find((g) => g.label === 'Group 4')!.when).toBe('After Sigurd talks to Ida.')
  })

  it("places the joins Serenes' recruitment page gives (turn 2: Azelle and Lex from the north; turn 3: Quan, Ethlyn and Finn from the east)", () => {
    const joins = map('Prologue').joiners!.map((j) => `${j.name} ${j.from} ${j.when}`)
    expect(joins).toContain('Azelle 42,32 Turn 2, at the start of your phase.')
    expect(joins).toContain('Lex 42,32 Turn 2, at the start of your phase.')
    for (const n of ['Quan', 'Ethlyn', 'Finn']) expect(joins).toContain(`${n} 64,19 Turn 3, at the start of your phase.`)
    expect(map('Prologue').forced!.map((f) => f.name)).toEqual(['Naoise', 'Alec', 'Arden'])
    // Second generation: a substitute and the child it stands in for share a tile and an entry.
    expect(map('Ch.6').joiners!.map((j) => j.name)).toContain('Deimne / Lester')
    const notes = map('Prologue').notes
    expect(notes).toContain('Sigurd talks to Arvis (once Arvis appears on the map): Sigurd receives a Silver Sword.')
    expect(map('Ch.1').notes).toContain('Sigurd talks to Ayra: Ayra joins your army.')
  })
})
