import { describe, expect, it } from 'vitest'
import { FE13_MAPS } from '../../data/fe13/fe13Maps'
import { ALL_MAPS } from '../../data/maps'
import { DARK_FILL, DARKEST_FILL, lightness, visibleFills } from '../mapFills'

const darkest = (fills: Record<string, string | undefined>) => Math.min(...Object.values(fills).map((h) => lightness(h!)))

describe("a map's own colours, as drawn", () => {
  it('lifts a palette too dark to see on the dark page to a dark brown or grey, never near black', () => {
    const ch1 = FE13_MAPS.find((m) => m.id === 'fe13-1')!
    expect(lightness(ch1.fills!.t0!)).toBeLessThan(0.1) // Awakening's Chapter 1, at night
    expect(lightness(visibleFills(ch1.fills).t0!)).toBeGreaterThan(DARKEST_FILL)
    expect(lightness(visibleFills(ch1.fills).t0!)).toBeLessThan(DARK_FILL)
    // Every colour but the void's: a wall all but black is the void beyond the map, drawn black (the user's call, Fates' Endgames).
    const shown = (fills: Record<string, string | undefined>) =>
      Object.fromEntries(Object.entries(visibleFills(fills)).filter(([code, h]) => !(code[0] === 'w' && lightness(h!) < 0.06)))
    for (const m of [...FE13_MAPS, ...ALL_MAPS].filter((m) => m.fills && Object.keys(m.fills).length))
      expect(darkest(shown(m.fills!)), m.id).toBeGreaterThanOrEqual(DARKEST_FILL - 0.005)
    const end = ALL_MAPS.find((m) => m.id === 'fe14r-endgame')!
    expect(lightness(visibleFills(end.fills).wa!)).toBeLessThan(0.06)
  })

  it('lifts its dark colours in order, so its walls stay darker than its floors, and leaves the light ones', () => {
    const r24 = ALL_MAPS.find((m) => m.id === 'fe14r-24')!
    const raw = r24.fills!
    const shown = visibleFills(raw)
    expect(lightness(raw.wa!)).toBeLessThan(lightness(raw.t1!))
    expect(lightness(shown.wa!)).toBeLessThan(lightness(shown.t1!))
    const ch2 = ALL_MAPS.find((m) => m.id === 'fe14b-6')!
    expect(visibleFills({ ...ch2.fills, wa: '#000000' }).ta).toBe(ch2.fills!.ta) // a black wall lifts no plain
  })

  it('leaves a palette light enough alone', () => {
    const fills = { t0: '#8aaa60', we: '#4a7ac0' }
    expect(visibleFills(fills)).toBe(fills)
  })
})
