import type { Route } from '../types'

/**
 * Weapons the story hands over, by route: the chapter (number) you have it from. Yato's forms come from the Fire Emblem
 * Wiki's Yato page ("closing cutscene" of Birthright 19, Conquest 14 and Revelation 15, so you have it from the next
 * chapter; "prior to preparations" of Chapter 27, so from that chapter) and agree with the chapter titles in the game
 * files. What your own units start a chapter holding (Corrin's Yato, Felicia's dagger, Raijinto on Ryoma) comes from the
 * placement files instead (`kit` on each map), not from here.
 */
export const FATES_GIFTS: Record<string, Partial<Record<Route, number>>> = {
  'Noble Yato': { Birthright: 20 },
  'Blazing Yato': { Birthright: 27 },
  'Grim Yato': { Conquest: 15 },
  'Shadow Yato': { Conquest: 27 },
  'Alpha Yato': { Revelation: 16 },
  'Omega Yato': { Revelation: 27 },
}
