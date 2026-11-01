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
    // Mag/2 is held between 5 and 15 (main.dol 0x8001dd54).
    expect(w('Physic').range).toBe('1-Mag/2 (5-15)')
  })

  it("reads the rest of the record: magic from the second type, growth changes, doors and walls, who may use it", () => {
    // The second type decides the damage: the Flame Lance and Bolt Axe hit with Mag against Res.
    expect([w('Flame Lance').magic, w('Bolt Axe').magic, w('Sonic Sword').magic, w('Runesword').magic]).toEqual(['fire', 'thunder', 'wind', 'light'])
    expect(w('Iron Lance').magic).toBeUndefined()
    // Hidden growth changes a Fixed-mode level-up adds: iron weapons, Str -5, Skl +5, Spd +5, Res -5.
    expect(w('Iron Sword').growths).toEqual({ str: -5, skl: 5, spd: 5, res: -5 })
    // Axes also target breakable doors and walls.
    expect(w('Hand Axe').effective).toEqual(['doors and walls'])
    expect(w("Rolf's Bow").rules).toContain('Rolf only')
    expect(w('Amiti').rules).toContain('Elincia only')
    // The siege tomes stop counters both ways; the three blades and two magic swords lock attack skills at 2 range.
    expect(w('Meteor').rules).toContain("Can't be countered, and can't counter")
    for (const name of ['Ragnell', 'Alondite', 'Runesword', 'Sonic Sword']) expect(w(name).rules.join(' '), name).toMatch(/^.*At 2 range/)
    // The Torch staff is told apart from the Torch item; a laguz's own attack is listed by its class.
    expect(w('Torch (staff)').category).toBe('Staff')
    expect(FE9_WEAPONS.filter((x) => x.category === 'Strike').map((x) => x.name)).toEqual([
      'Claw (Lion)', 'Claw (Tiger)', 'Claw (Cat)', 'Breath (White Dragon)', 'Breath (Red Dragon)', 'Beak (Hawk)', 'Beak (Raven)',
      'Beak (Tibarn)', 'Beak (Naesala)',
    ])
    expect(w('Trainer').giftAt).toBeUndefined()
  })

  it('says which foes a weapon no base sells can be stolen from, and a foe placed on both difficulties once', () => {
    expect(fe9ItemSources('Venin Axe').map((s) => s.how)).toContain('Steal from Warrior')
    expect(fe9ItemSources('Rexaura').some((s) => s.how.startsWith('Steal from'))).toBe(true)
    // Gromell drops the Bolt Axe on every difficulty: one line, no difficulty named.
    expect(fe9ItemSources('Bolt Axe').filter((s) => s.how.startsWith('Dropped by Gromell')).map((s) => s.how)).toEqual(['Dropped by Gromell'])
    for (const x of FE9_WEAPONS)
      for (const s of fe9ItemSources(x.name)) {
        const base = s.how.replace(/ \(.*\)$/, '')
        const same = fe9ItemSources(x.name).filter((o) => o.mapId === s.mapId && o.how.replace(/ \(.*\)$/, '') === base && !!o.arrives === !!s.arrives)
        expect(same.length, `${x.name}: ${s.map} ${base}`).toBe(1)
      }
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
    // Boss weapons; a lone Venin Edge is always equipped, so Steal can't take it: listed, marked as not available.
    for (const name of ['Alondite', 'Gurgurant', 'Venin Edge', 'Practice Axe']) expect(find(name)?.foeOnly, name).toBe(true)
    // Held only on a leftover test map, or only by preset entries no script uses: left out as codes-only.
    for (const name of ['Rexflame', 'Venin Lance', 'Rexcalibur']) expect(find(name), name).toBeUndefined()
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
