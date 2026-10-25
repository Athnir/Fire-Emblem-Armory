import { describe, expect, it } from 'vitest'
import { FE9_WEAPONS } from '../../data/fe9/fe9Weapons'
import { fe9ItemSources } from '../../data/fe9/fe9ItemSources'

const w = (name: string) => FE9_WEAPONS.find((x) => x.name === name)!

describe("Path of Radiance weapons from the game's item table", () => {
  it('reads stats, uses and worth', () => {
    expect(w('Iron Sword')).toMatchObject({ rank: 'E', mt: 5, hit: 90, crit: 0, wt: 7, range: '1', uses: 46, worth: 460, wex: 1 })
    expect(w('Killing Edge')).toMatchObject({ rank: 'C', mt: 9, hit: 75, crit: 30, wt: 9 })
  })

  it('reads effectiveness, rules and stat bonuses', () => {
    expect(w('Armorslayer').effective).toEqual(['armour'])
    expect(w('Brave Sword').flags).toContain('twice')
    expect(w('Ragnell')).toMatchObject({ rank: 'Prf', range: '1-2', uses: null, stats: { def: 5 } })
    expect(w('Double Bow').stats).toEqual({ str: 3 })
    expect(w('Physic').range).toBe('1-Mag/2')
  })

  it('tells horseback and beast laguz targets apart', () => {
    expect(w('Knight Killer').effective).toEqual(['horseback'])
    expect(w('Fire').effective).toEqual(['beast'])
    expect(w('Laguzslayer').effective).toEqual(['laguz'])
  })

  it("words Brave weapons as hitting twice every time, and marks weapons that can't be sold", () => {
    expect(w('Brave Sword').rules).toContain('Strikes twice in a row, when attacking and when countering')
    expect(w('Ragnell').rules).toContain("Can't be sold")
    expect(w('Iron Sword').rules).not.toContain("Can't be sold")
  })

  it('gives knives no rank rather than calling them personal weapons', () => {
    expect(w('Knife').rank).toBe('—')
  })

  it('leaves out cut and codes-only weapons', () => {
    for (const name of ['Warp', 'Berserk', 'Unlock', 'Devil Axe', 'Urvan', 'Bright Bow']) expect(FE9_WEAPONS.some((x) => x.name === name), name).toBe(false)
  })

  it('has unique ids', () => {
    expect(new Set(FE9_WEAPONS.map((x) => x.id)).size).toBe(FE9_WEAPONS.length)
  })

  it("lists the bases whose shops sell it, by difficulty", () => {
    expect(w('Iron Sword').shop).toEqual({ normal: 'Ch.8–11, 13, 15, 17, 19, 24, Endgame', hard: 'Ch.8–21, 23, 25, 27' })
    expect(w('Heal').shop).toEqual({ normal: 'Ch.8 onward', hard: 'Ch.8 onward' })
    // Sold on one difficulty only.
    expect(w('Armorslayer').shop).toEqual({ normal: 'Ch.21', hard: '' })
    expect(w('Ragnell').shop).toBeUndefined()
  })

  it('finds where the maps give it: chests, villages, drops and buried items', () => {
    expect(fe9ItemSources('Armorslayer')).toContainEqual(expect.objectContaining({ map: 'Chapter 7: Shades of Evil', how: expect.stringMatching(/^Chest at/) }))
    expect(fe9ItemSources('Steel Sword')).toContainEqual(expect.objectContaining({ how: expect.stringMatching(/^Village at/) }))
    expect(fe9ItemSources('Silver Blade')).toContainEqual(expect.objectContaining({ how: expect.stringMatching(/^Buried near/) }))
  })

  it("lists a foe's own weapons as foe-only, and leaves out the maps' siege machines", () => {
    const find = (name: string) => FE9_WEAPONS.find((x) => x.name === name)
    // The maps' own ballistae stay on their maps.
    for (const name of ['Ballista', 'Iron Ballista', 'Killer B', 'Onager']) expect(find(name), name).toBeUndefined()
    // Boss weapons; a lone Venin Edge or Lance is always equipped, so Steal can't take it: listed, marked as not available.
    for (const name of ['Alondite', 'Gurgurant', 'Venin Edge', 'Venin Lance', 'Practice Axe']) expect(find(name)?.foeOnly, name).toBe(true)
    // A foe carrying a second weapon unequips one to use the other, and a silenced bishop drops Rexaura for an Elixir.
    for (const name of ['Venin Axe', 'Venin Bow', 'Rexaura']) expect(find(name), name).toBeDefined()
    for (const name of ['Venin Axe', 'Venin Bow', 'Rexaura', 'Iron Sword']) expect(find(name)?.foeOnly, name).toBeUndefined()
  })

  it('says which foes carry a foe-only weapon when the chapter starts, not those who arrive later', () => {
    expect(fe9ItemSources('Gurgurant')).toContainEqual(expect.objectContaining({ mapId: 'fe9-endgame', how: 'Carried by Ashnard' }))
    // The Black Knight arrives in Chapter 11 and 24 as a reinforcement: only Chapter 27-2 has him on the map to see.
    expect(fe9ItemSources('Alondite').map((s) => s.mapId)).toEqual(['fe9-27-2'])
  })

  it('reads drops from the weapon slots too', () => {
    expect(fe9ItemSources('Longbow')).toContainEqual(expect.objectContaining({ how: expect.stringMatching(/Dropped/i) }))
  })
})
