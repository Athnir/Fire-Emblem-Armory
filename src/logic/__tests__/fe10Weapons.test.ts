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
    // Ballistae and the Onager stay on their maps.
    for (const name of ['Ballista', 'Iron Ballista', 'Killer Ballista', 'Onager']) expect(FE10_WEAPONS.some((x) => x.name === name), name).toBe(false)
    // The other Judges are what the endgame bosses' AI makes on the spot for an attack, never in a unit's slots: Ashera's
    // map-wide attacks and silence and paralysis waves, Sephiran's and Dheginsea's map-wide attacks, Lekain's silence wave.
    expect(FE10_WEAPONS.filter((x) => x.name === 'Judge').map((x) => x.id)).toEqual(['judge'])
    // Judge, Creiddylad and the staves below are a foe's own, locked to them so Steal can't take them.
    for (const name of ['Judge', 'Creiddylad', 'Rewarp', 'Elsilence', 'Elsleep']) expect(FE10_WEAPONS.find((x) => x.name === name)?.foeOnly, name).toBe(true)
    // A foe's Venin weapons can be stolen, so they're the player's.
    for (const name of ['Venin Edge', 'Venin Lance', 'Venin Axe', 'Venin Bow', 'Silence']) expect(FE10_WEAPONS.find((x) => x.name === name)?.foeOnly, name).toBeUndefined()
  })

  it('names no strike plainly, and leaves out the spirits and placeholders', () => {
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

  it("lists each laguz strike family once, by race and whether it's the royals' Great form, with its higher forms", () => {
    const strikes = FE10_WEAPONS.filter((x) => x.ofClass)
    // Every strike comes with its class but Ashera's Judge, a weapon of the same type in her slots.
    expect(FE10_WEAPONS.filter((x) => x.category === 'Strike' && !x.ofClass).map((x) => x.name)).toEqual(['Judge'])
    // The black dragons' two families, both plain 'Breath', go by their classes.
    expect(strikes.map((x) => x.name).sort()).toEqual([
      'Beak (Raven)', 'Breath (Dragon King)', 'Breath (Dragon Prince)', 'Breath (Red Dragon)', 'Breath (White Dragon)', 'Claw (Cat)',
      'Fang (Lion)', 'Fang (Tiger)', 'Fang (Wolf)', 'Great Beak (Raven)', 'Great Fang (Lion)', 'Great Fang (Wolf)', 'Great Talon (Hawk)',
      'Talon (Hawk)',
    ])
    // No price, never breaks, never forged; the lowest form a class starts with, and the higher ones in its rules.
    for (const s of strikes) expect(s, s.name).toMatchObject({ worth: 0, uses: null, wt: 0 })
    expect(strikes.some((s) => s.forge)).toBe(false)
    expect(w('Claw (Cat)')).toMatchObject({ rank: 'A', mt: 8, hit: 90, range: '1' })
    expect(w('Claw (Cat)').rules).toEqual(expect.arrayContaining(['Rank S form: Mt 13, Hit 90', 'Rank SS form: Mt 18, Hit 90']))
    // Giffca's class starts at the Lion's Great Fang's S form, Caineghis's at its SS form: one entry.
    expect(w('Great Fang (Lion)')).toMatchObject({ rank: 'S', mt: 17, hit: 100, rules: expect.arrayContaining(['Rank SS form: Mt 22, Hit 100']) })
    expect(w('Great Talon (Hawk)')).toMatchObject({ rank: 'S', mt: 15, rules: expect.arrayContaining(['Rank SS form: Mt 20, Hit 100']) })
    expect(w('Breath (Red Dragon)').range).toBe('1-2')
    // The white dragons' Breath is magic (its second type, neutral: Mag against Res); the others are physical.
    expect(strikes.filter((s) => s.magic).map((s) => [s.name, s.magic])).toEqual([['Breath (White Dragon)', 'neutral']])
    // Yours from the chapter its first holder joins; the Dragon King only ever fights you.
    expect(w('Fang (Wolf)').kitAt).toEqual(['fe10-1-5'])
    expect(w('Great Beak (Raven)').kitAt).toEqual(['fe10-4-prologue'])
    expect(w('Breath (Dragon King)').foeOnly).toBe(true)
    // It's not an item: never stolen.
    for (const s of strikes) expect(fe10ItemSources(s.name).filter((x) => x.how.startsWith('Steal')), s.name).toEqual([])
  })

  it("lists Ashera's own Judge, a strike-type weapon in her slots in Endgame (5), as hers alone", () => {
    // Only a unit with SID_FINALBOSS (Ashera's) can use it; light magic in its damage and the triangle; never breaks, never sold.
    expect(w('Judge')).toMatchObject({ category: 'Strike', rank: 'SS', mt: 50, hit: 100, crit: 0, wt: 16, range: '1-2', uses: null, worth: 0 })
    expect(w('Judge')).toMatchObject({ magic: 'light', foeOnly: true, rules: ['Ashera only', "Can't be sold", "Can't land critical hits"] })
    expect(w('Judge').ofClass).toBeUndefined()
    expect(fe10ItemSources('Judge').map((s) => `${s.mapId}: ${s.how}`)).toEqual(['fe10-4-endgame-5: Carried by Ashera'])
  })
})
