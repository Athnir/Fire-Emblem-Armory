import { describe, expect, it } from 'vitest'
import { FE4_ITEM_SOURCES } from '../../data/fe4/fe4ItemSources'
import { FE4_LISTED } from '../../data/fe4/fe4Listed'
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
    expect(at('Tornado', 'drop-later')).toContain('Ch.9 Dropped by Musar, arriving mid-chapter')
  })

  it('gives the talks, visits and hidden finds Serenes lists (Silver Sword: Alvis; Holsety: Silesia; Hero Axe: Lex)', () => {
    expect(at('Silver Sword', 'talk-later')).toEqual(['Prologue Sigurd talks to Arvis'])
    expect(at('Forseti', 'castle')).toEqual(['Ch.4 Entering Silesse (Lewyn)'])
    expect(at('Brave Axe', 'hidden')).toEqual(['Ch.1 Found by Lex at (29, 27)'])
    expect(at('Speed Ring', 'village')).toContain('Prologue Visiting the village at (29, 2)')
  })

  it("lists what a unit carries when it joins you (Sigurd's Steel Sword and Iron Lance, Seliph's Slim Sword)", () => {
    expect(at('Steel Sword', 'kit')).toContain('Prologue Carried by Sigurd on joining')
    expect(at('Iron Lance', 'kit')).toContain('Prologue Carried by Sigurd on joining')
    expect(at('Slim Sword', 'kit')).toContain('Ch.6 Carried by Seliph on joining')
    // Arden comes in the Prologue opening's unit list, on your side.
    expect(at('Iron Sword', 'kit')).toContain('Prologue Carried by Arden on joining')
  })

  it("counts a recruit's own items and a talk's or an event's gift from the next chapter", () => {
    // Deirdre joins when Sigurd reaches her in Chapter 1; Jamke when Deirdre talks to him; Quan, Ethlyn and Finn on the Prologue's turn 3.
    expect(at('Aura', 'kit-later')).toEqual(['Ch.1 Carried by Deirdre on joining'])
    expect(at('Killer Bow', 'kit-later')).toEqual(['Ch.1 Carried by Jamke on joining'])
    expect(at('Steel Lance', 'kit-later')).toEqual(['Prologue Carried by Quan on joining'])
    expect(Object.values(FE4_ITEM_SOURCES).flat().filter((x) => x.kind === 'talk' || x.kind === 'event' || x.kind === 'kit').every(
      (x) => x.kind === 'kit' || x.mapId === 'fe4-final')).toBe(true)
    // A block's gift: Chapter 9's Berserk Staff, once Galatia is seized and Charlot has spoken to Hannibal (trigger 0x0C: Charlot stops
    // next to him), and a gift that depends on a flag says which (Chapter 6's scene 0x1EA: Julia's Aura before Isaach falls, Nosferatu after).
    expect(at('Berserk Staff', 'event-later')).toEqual(['Ch.9 Given to Charlot after you seize Galatia and Charlot talks to Hannibal and Charlot stops next to Hannibal'])
    expect(at('Aura', 'talk-later')).toEqual(['Ch.6 Julia talks to Seliph, before you seize Isaach'])
    expect(at('Nosferatu', 'talk-later')).toEqual(['Ch.6 Julia talks to Seliph, after you seize Isaach'])
  })

  it('reads the drops of armies that arrive hostile or turn on you, and none from a foe that leaves before anyone can reach it', () => {
    expect(at('Sleep Staff', 'drop-later')).toEqual(['Ch.2 Dropped by Clement, arriving mid-chapter'])
    expect(at('Silver Blade', 'drop-later')).toEqual(['Ch.3 Dropped by Chagall, arriving mid-chapter'])
    expect(at('Ridersbane', 'drop-later')).toContain('Ch.7 Dropped by Bramsel, arriving mid-chapter')
    // The Prologue's Gandolf leaves on turn 1's enemy phase, some 40 tiles from your army: his Skill Ring is his Chapter 1 drop.
    expect([...at('Skill Ring', 'drop'), ...at('Skill Ring', 'drop-later')]).toEqual(['Ch.1 Dropped by Munnir, arriving mid-chapter', 'Ch.7 Dropped by Jabarro, arriving mid-chapter'])
  })

  it("marks the weapons no copy exists of as foe-only, with every foe carrying them, and says a foe's weapon nowhere else", () => {
    // The 140 copies the game tracks ($83:F489) cover every weapon type but these eleven; Steal takes only gold ($84:EAD9).
    expect(FE4_LISTED.filter((w) => w.foeOnly).map((w) => w.name)).toEqual([
      'Gungnir', 'Helswath', 'Valflame', 'Meteor', 'Mjölnir', 'Bolting', 'Blizzard', 'Jörmungandr', 'Fenrir', 'Hel', 'Loptous',
    ])
    expect(at('Gungnir', 'foe-later')).toEqual(['Ch.5 Carried by Travant, a foe, arriving mid-chapter', 'Ch.9 Carried by Arion, a foe, arriving mid-chapter'])
    expect(at('Blizzard', 'foe')).toEqual(['Ch.4 Carried by a foe Mage Fighter', 'Ch.4 Carried by a foe Wind Mage'])
    for (const [item, list] of Object.entries(FE4_ITEM_SOURCES)) {
      if (list.some((x) => !x.kind.startsWith('foe'))) expect(list.filter((x) => x.kind.startsWith('foe')), item).toEqual([])
    }
  })
})
