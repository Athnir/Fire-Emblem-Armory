import { describe, expect, it } from 'vitest'
import { FE1_ITEM_SOURCES } from '../../data/fe1/fe1ItemSources'
import { FE1_LISTED } from '../../data/fe1/fe1Listed'
import { FE1_MAPS } from '../../data/fe1/fe1Maps'
import { FE1_STORY } from '../../data/fe1/fe1MapSet'
import { FE1_MOVE_CLASSES, FE1_TERRAIN } from '../../data/fe1/fe1Terrain'
import { FE1_WEAPONS } from '../../data/fe1/fe1Weapons'
import type { ChapterMap } from '../../data/maps/types'
import { rowCodes } from '../maps'
import { trueHit } from '../trueHit'

const map = (id: string) => FE1_MAPS.find((m) => m.id === id)!
const allUnits = (m: ChapterMap) => [...m.units, ...(m.reinforcements ?? []).flatMap((g) => g.units)]
const weapon = (name: string) => FE1_LISTED.find((w) => w.name === name)

describe("Shadow Dragon and the Blade of Light's maps", () => {
  it('has its 25 chapters in order, each map its own size', () => {
    expect(FE1_MAPS.map((m) => m.id)).toEqual(Array.from({ length: 25 }, (_, i) => `fe1-${i + 1}`))
    expect(FE1_STORY.maps.map((m) => m.id)).toEqual(FE1_MAPS.map((m) => m.id))
    for (const m of FE1_MAPS) {
      expect(m.grid.length, m.id).toBe(m.height)
      for (const row of m.grid) expect(row.length, m.id).toBe(m.width * 2)
    }
    // The cursor never reaches the stored map's outer ring (6:$A97B): Chapter 1 is stored 32 x 15, played 30 x 13.
    expect([map('fe1-1').width, map('fe1-1').height]).toEqual([30, 13])
  })

  it("gives every tile a terrain from the game's table, with a cost for every movement type", () => {
    const codes = new Set(FE1_MAPS.flatMap((m) => m.grid.flatMap(rowCodes)))
    for (const code of codes) {
      const info = FE1_TERRAIN[code]
      expect(info, code).toBeDefined()
      expect(Object.keys(info!.move).sort(), code).toEqual([...FE1_MOVE_CLASSES].sort())
    }
    // Grassland gives 5 Avoid where floors give none (15:$EBD8), and a fortress, castle gate or throne heals.
    expect(FE1_TERRAIN.tv?.avo).toBe(5)
    expect(FE1_TERRAIN.ta?.avo).toBe(0)
    expect(FE1_TERRAIN.bb?.note).toMatch(/3 to 10 HP/)
  })

  it('makes Marth seize a castle or throne in every chapter', () => {
    for (const m of FE1_MAPS) {
      expect(m.objectives.filter((o) => o.type === 'seize').length, m.id).toBe(1)
      expect(m.victory, m.id).toMatch(/^Seize the (castle|throne) with Marth$/)
    }
  })

  it('marks the recruits each chapter has, with who talks to them (the talk table at 15:$EDB5)', () => {
    const talk = (id: string, name: string) => allUnits(map(id)).find((u) => u.name === name)?.talk
    expect(talk('fe1-3', 'Navarre')).toBe('Recruit: talk with Caeda')
    expect(talk('fe1-13', 'Astram')).toBe('Recruit: talk with Midia')
    expect(talk('fe1-14', 'Catria')).toBe('Recruit: talk with Marth (only with Minerva in your army)')
    expect(talk('fe1-19', 'Tiki')).toBe('Recruit: talk with Bantu')
  })
})

describe("Shadow Dragon and the Blade of Light's weapons", () => {
  it('lists only what something in the game gives or a unit carries', () => {
    for (const w of FE1_LISTED) expect(FE1_ITEM_SOURCES[w.name]?.length, w.name).toBeGreaterThan(0)
    // Hellarn: no shop, chest, village, unit or foe has it.
    expect(FE1_WEAPONS.some((w) => w.name === 'Hellarn')).toBe(true)
    expect(weapon('Hellarn')).toBeUndefined()
  })

  it("drops a foe's second item to the unit that beats it (6:$AD79, 6:$935E), never its first", () => {
    expect(FE1_ITEM_SOURCES.Gradivus).toEqual([{ mapId: 'fe1-20', kind: 'drop', text: 'Dropped by Camus' }])
    expect(weapon('Falchion')?.foeOnly).toBeUndefined()
    // Gazzak wields a Steel Axe and drops his Vulnerary (seen in Mesen).
    expect(map('fe1-1').units.find((u) => u.type === 'boss')).toMatchObject({ name: 'Gazzak', drops: ['Vulnerary'] })
  })

  it('gives what seizing a castle or throne gives', () => {
    expect(FE1_ITEM_SOURCES.Parthia).toEqual([{ mapId: 'fe1-12', kind: 'event', text: 'Given when Marth seizes the throne' }])
  })

  it("triples an effective weapon's Mt and names the classes its list does", () => {
    expect(weapon('Rapier')?.effective).toEqual(['cavalier', 'armour'])
    expect(weapon('Ridersbane')?.effective).toEqual(['cavaliers-only'])
    expect(weapon('Falchion')?.effective).toEqual(['fe1-medeus'])
  })
})

describe("Shadow Dragon and the Blade of Light's hit roll", () => {
  it('rolls a byte × 10 / 25, held at 100, and hits at or below the displayed hit (15:$CE7E, $CD70)', () => {
    expect(trueHit('1rn-byte-fifths', 0).trueHitBasisPoints).toBe(0)
    expect(trueHit('1rn-byte-fifths', 1).trueHitBasisPoints).toBe(195)
    expect(trueHit('1rn-byte-fifths', 50).trueHitBasisPoints).toBe(5000)
    expect(trueHit('1rn-byte-fifths', 99).trueHitBasisPoints).toBe(9766)
    expect(trueHit('1rn-byte-fifths', 100).trueHitBasisPoints).toBe(10000)
  })
})
