import { describe, expect, it } from 'vitest'
import { ALL_WEAPONS } from '../../data/weapons'
import { itemSources } from '../itemSources'

const weapon = (name: string) => ALL_WEAPONS.find((w) => w.name === name)!

describe('item sources from the maps', () => {
  it("finds the Dual Club in Conquest 10's village, and nowhere in Conquest 19", () => {
    const sources = itemSources('Dual Club')
    expect(sources.map((s) => `${s.mapId} ${s.how}`)).toContain('fe14c-10 Village at (8, 13)')
    expect(sources.some((s) => s.mapId === 'fe14c-19')).toBe(false)
  })

  it('marks a Hoshido weapon found on a Conquest map as cross-route', () => {
    expect(weapon('Dual Club').availability.crossRoutes).toEqual(['Conquest'])
    expect(weapon('Dual Club').availability.routes).toContain('Conquest')
  })

  it('marks a Nohr weapon found on a Birthright map as cross-route', () => {
    // Birthright 7 has an Armorslayer in a chest.
    expect(weapon('Armorslayer').availability.crossRoutes).toContain('Birthright')
  })

  it('splits a chest that holds one of two items', () => {
    expect(itemSources("Spy's Yumi").some((s) => s.mapId === 'fe14c-26')).toBe(true)
    expect(itemSources("Spy's Shuriken").some((s) => s.mapId === 'fe14c-26')).toBe(true)
  })

  it('never marks a cross route from a DLC map alone', () => {
    for (const w of ALL_WEAPONS) {
      for (const r of w.availability.crossRoutes ?? []) {
        const story = (w.mapSources ?? []).filter((s) => !s.dlc && s.routes.includes(r as 'Birthright' | 'Conquest'))
        // Dual Club and the like keep any cross route written by hand only if the maps back it up.
        expect(story.length, `${w.name} on ${r}`).toBeGreaterThan(0)
      }
    }
  })
})
