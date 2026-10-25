import type { Route } from '../types'

/**
 * Weapons the story hands over, by route: the chapter (number) you have it from. Yato's forms come from the Fire Emblem
 * Wiki's Yato page ("closing cutscene" of Birthright 19, Conquest 14 and Revelation 15, so you have it from the next
 * chapter; "prior to preparations" of Chapter 27, so from that chapter) and agree with the chapter titles in the game
 * files. A weapon only some character carries (Raijinto, Siegfried, Fujin Yumi, Brynhildr, Missiletainn) isn't here:
 * whose it is belongs to the Unit Planner.
 */
export const FATES_GIFTS: Record<string, Partial<Record<Route, number>>> = {
  Yato: { all: 1 },
  'Noble Yato': { Birthright: 20 },
  'Blazing Yato': { Birthright: 27 },
  'Grim Yato': { Conquest: 15 },
  'Shadow Yato': { Conquest: 27 },
  'Alpha Yato': { Revelation: 16 },
  'Omega Yato': { Revelation: 27 },
}
