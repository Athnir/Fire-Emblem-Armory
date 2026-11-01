import { describe, expect, it } from 'vitest'
import { FE10_WEAPONS } from '../../data/fe10/fe10Weapons'
import { fe10ItemSources } from '../../data/fe10/fe10ItemSources'

const w = (name: string) => FE10_WEAPONS.find((x) => x.name === name)!

describe("Radiant Dawn weapons from the game's item table", () => {
  it('reads stats, uses and worth', () => {
    expect(w('Iron Sword')).toMatchObject({ rank: 'D', mt: 6, hit: 90, crit: 0, wt: 7, range: '1', uses: 50, worth: 500, wex: 2 })
    expect(w('Silver Sword')).toMatchObject({ rank: 'A', mt: 12, hit: 80, wt: 10, uses: 30 })
    expect(w('Tempest Blade')).toMatchObject({ rank: 'S', range: '1-2' })
    expect(w('Rexflame')).toMatchObject({ rank: 'SS', stats: { spd: 3 } })
  })

  it("reads personal weapons, stat bonuses and what can't break", () => {
    expect(w('Ragnell')).toMatchObject({ rank: 'Prf', uses: null, stats: { def: 5 } })
    expect(w('Ragnell').rules).toEqual(expect.arrayContaining(['Ike only', "Can't be sold", "Can't be stolen"]))
    expect(w('Amiti').rules).toEqual(expect.arrayContaining(['Elincia (and Renning) only', 'Strikes twice in a row, when attacking and when countering']))
    expect(w('Lughnasadh')).toMatchObject({ stats: { spd: 5 }, rules: expect.arrayContaining(['Leonardo only']) })
  })

  it("reads Radiant Dawn's own rules: crossbows, Marksman range and magic effectiveness", () => {
    expect(w('Bowgun')).toMatchObject({ category: 'Crossbow', rank: '—', mt: 24, effective: ['flying'] })
    expect(w('Bowgun').rules.join(' ')).toMatch(/Mt alone/)
    // A Marksman reaches one tile further with an ordinary bow, not a longbow.
    expect(w('Iron Bow').rules).toContain('A Marksman can fire it at 2-3 range')
    expect(w('Double Bow').rules).toContain('A Marksman can fire it at 1-3 range')
    expect(w('Iron Longbow').rules.join(' ')).not.toMatch(/Marksman/)
    // Fire against beasts, thunder against dragons, wind against fliers.
    expect([w('Fire').effective, w('Thunder').effective, w('Wind').effective]).toEqual([['beast'], ['dragon'], ['flying']])
    expect(w('Worm').category).toBe('Dark')
  })

  it('lists shops and one-off bargains, and keeps what staves do', () => {
    // Florete stays a physical sword: the game never flagged it as magic.
    expect(w('Florete').flags).not.toContain('magsw')
    expect(w('Heal').rules.join(' ')).toMatch(/HP/)
    expect(w('Bowgun').shop!.normal).toMatch(/^Part 3: Ch\.2/)
    // Serenes Forest's Part 3 bargains: Florete and Silencer in Ch.4, Wo Dao in Ch.5.
    expect(w('Florete').bargain).toEqual({ normal: 'Part 3: Ch.4', hard: 'Part 3: Ch.4' })
    expect(w('Silencer').bargain!.normal).toBe('Part 3: Ch.4')
    expect(w('Wo Dao').bargain!.normal).toBe('Part 3: Ch.5')
  })

  it("lists a foe's own weapons as foe-only, and leaves out the maps' siege machines", () => {
    // Ballistae, the Onager and Ashera's siege forms of Judge stay on their maps.
    for (const name of ['Ballista', 'Iron Ballista', 'Killer Ballista', 'Onager']) expect(FE10_WEAPONS.some((x) => x.name === name), name).toBe(false)
    expect(FE10_WEAPONS.filter((x) => x.name === 'Judge')).toHaveLength(1)
    // Judge, Creiddylad and the staves below are a foe's own, locked to them so Steal can't take them.
    for (const name of ['Judge', 'Creiddylad', 'Rewarp', 'Elsilence', 'Elsleep']) expect(FE10_WEAPONS.find((x) => x.name === name)?.foeOnly, name).toBe(true)
    // A foe's Venin weapons can be stolen, so they're the player's.
    for (const name of ['Venin Edge', 'Venin Lance', 'Venin Axe', 'Venin Bow', 'Silence']) expect(FE10_WEAPONS.find((x) => x.name === name)?.foeOnly, name).toBeUndefined()
  })

  it('leaves out laguz strikes, the spirits and placeholders', () => {
    for (const name of ['Fang', 'Talon', 'Beak', 'Breath', 'Fire Tail', 'dummy']) expect(FE10_WEAPONS.some((x) => x.name === name), name).toBe(false)
  })

  it("counts each unit's gear once, where it first joins: never a roster's preset gear or a cutscene's cast", () => {
    const w = (name: string) => FE10_WEAPONS.find((x) => x.name === name)!
    // Rolf brings his bow when the Greil Mercenaries join, in Part 3's Prologue; later rosters only place him.
    expect(w("Rolf's Bow").kitAt).toEqual(['fe10-3-prologue'])
    // Lehran joins in Endgame (5), placed on your side, with the Ashera Staff.
    expect(w('Ashera Staff').kitAt).toEqual(['fe10-4-endgame-5'])
    // Micaiah's rosters list a Thani from Part 1 Ch.3, but it's given in a base conversation before Part 1's Endgame.
    expect(w('Thani').kitAt).toBeUndefined()
    expect(w('Thani').baseAt).toEqual(['fe10-1-endgame'])
    // The endgame's rosters give Micaiah a Rexaura; in the game Lekain drops it.
    expect(w('Rexaura').kitAt).toBeUndefined()
    // Part 4 Ch.4's opening sends Tormod's items to the convoy and hands him three tomes.
    for (const name of ['Arcfire', 'Bolganone', 'Meteor']) expect(w(name).giftAt, name).toEqual(['fe10-4-4'])
    // Only cutscenes' casts carry a Slim Lance: no one can get or meet one, so it isn't listed.
    expect(FE10_WEAPONS.some((x) => x.name === 'Slim Lance')).toBe(false)
  })

  it('says which foes a weapon no base sells can be disarmed of, never a locked one', () => {
    const steal = (name: string) => fe10ItemSources(name).filter((s) => s.how.startsWith('Steal from'))
    expect(steal('Venin Edge').map((s) => `${s.mapId}: ${s.how}`)).toContain('fe10-2-1: Steal from Myrmidon')
    // The Black Knight's Alondite is locked to him.
    expect(steal('Alondite')).toEqual([])
    // Ike's Ragnell in Part 3 Ch.13 is locked on Easy only, as the files have it.
    expect(steal('Ragnell').map((s) => s.difficulties)).toEqual([['Normal', 'Hard']])
  })
})
