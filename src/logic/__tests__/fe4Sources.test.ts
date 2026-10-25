import { describe, expect, it } from 'vitest'
import { FE4_ITEM_SOURCES } from '../../data/fe4/fe4ItemSources'
import { FE4_STORY } from '../../data/fe4/fe4MapSet'

const at = (item: string, kind: string) =>
  (FE4_ITEM_SOURCES[item] ?? []).filter((s) => s.kind === kind).map((s) => `${FE4_STORY.short(FE4_STORY.maps.find((m) => m.id === s.mapId)!)} ${s.text}`)

describe("Genealogy of the Holy War's item sources, from its scripts, shop lists and foes' records", () => {
  it("sells what Serenes' item-locations page lists as each chapter's vendor (fan names in brackets)", () => {
    // Chapter 1: Slim Sword, Iron Lance, Javelin, Steel Axe. Chapter 3: the silver weapons and Elfire.
    for (const item of ['Slim Sword', 'Iron Lance', 'Javelin', 'Steel Axe']) expect(at(item, 'shop'), item).toContain('Ch.1 Sold at Evans')
    for (const item of ['Silver Sword', 'Silver Lance', 'Silver Axe', 'Silver Bow', 'Elfire']) expect(at(item, 'shop'), item).toContain('Ch.3 Sold at Agusti')
  })

  it("gives the drops Serenes lists for each boss (Return Ring: Philip; Thunder Sword: Jacoban; Tornado: Musar; Bolganone: Hilda)", () => {
    expect(at('Return Ring', 'drop')).toContain('Ch.2 Dropped by Philip')
    expect(at('Levin Sword', 'drop')).toContain('Ch.3 Dropped by Jacobi')
    expect(at('Bolganone', 'drop')).toContain('Ch.10 Dropped by Hilda')
    expect(at('Tornado', 'drop-later')).toContain('Ch.9 Dropped by Musar (Group 2)')
  })

  it('gives the talks, visits and hidden finds Serenes lists (Silver Sword: Alvis; Holsety: Silesia; Hero Axe: Lex)', () => {
    expect(at('Silver Sword', 'talk')).toEqual(['Prologue Sigurd talks to Arvis'])
    expect(at('Forseti', 'castle')).toEqual(['Ch.4 Entering Silesse (Lewyn)'])
    expect(at('Brave Axe', 'hidden')).toEqual(['Ch.1 Found by Lex at (29, 27)'])
    expect(at('Speed Ring', 'village')).toContain('Prologue Visiting the village at (29, 2)')
  })

  it("lists what a unit carries when it joins you (Sigurd's Steel Sword and Iron Lance, Seliph's Slim Sword)", () => {
    expect(at('Steel Sword', 'kit')).toContain('Prologue Carried by Sigurd on joining')
    expect(at('Iron Lance', 'kit')).toContain('Prologue Carried by Sigurd on joining')
    expect(at('Slim Sword', 'kit')).toContain('Ch.6 Carried by Seliph on joining')
  })
})
