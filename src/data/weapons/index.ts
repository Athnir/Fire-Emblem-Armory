import type { Route, Weapon } from '../types'
import { itemSources } from '../../logic/itemSources'
import { SWORDS } from './swords'
import { SHURIKENS } from './shurikens'
import { KATANAS } from './katanas'
import { LANCES } from './lances'
import { NAGINATAS } from './naginatas'
import { AXES } from './axes'
import { CLUBS } from './clubs'
import { BOWS } from './bows'
import { YUMI } from './yumi'
import { TOMES } from './tomes'
import { SCROLLS } from './scrolls'
import { DAGGERS } from './daggers'
import { STAVES } from './staves'
import { RODS } from './rods'
import { OTHER } from './other'

/** The route a faction's weapons don't normally reach: finding one there is a cross-route exception. */
const OPPOSITE: Record<string, Route> = { Hoshido: 'Conquest', Nohr: 'Birthright' }
const ROUTE_ORDER: Route[] = ['Birthright', 'Conquest', 'Revelation', 'all']

/**
 * Adds where the maps give each weapon (chests, villages, enemy drops, from the game's own files) and
 * the routes that makes it reachable on. A Hoshido weapon found on a Conquest map (or a Nohr one on
 * Birthright) is a cross-route exception. DLC maps are listed but don't change the routes: they're
 * open on every route anyway.
 */
function withMapSources(w: Weapon): Weapon {
  const mapSources = itemSources(w.name)
  if (!mapSources.length) return w
  const routes = new Set(w.availability.routes)
  const cross = new Set(w.availability.crossRoutes ?? [])
  if (!routes.has('all')) {
    for (const r of mapSources.filter((s) => !s.dlc).flatMap((s) => s.routes)) {
      if (routes.has(r)) continue
      routes.add(r)
      if (r === OPPOSITE[w.faction]) cross.add(r)
    }
  }
  return {
    ...w,
    mapSources,
    availability: {
      ...w.availability,
      routes: ROUTE_ORDER.filter((r) => routes.has(r)),
      ...(cross.size ? { crossRoutes: ROUTE_ORDER.filter((r) => cross.has(r)) } : {}),
    },
  }
}

/** Every weapon category gets folded in here as its data file is added. */
export const ALL_WEAPONS: Weapon[] = [
  ...SWORDS,
  ...SHURIKENS,
  ...KATANAS,
  ...LANCES,
  ...NAGINATAS,
  ...AXES,
  ...CLUBS,
  ...BOWS,
  ...YUMI,
  ...TOMES,
  ...SCROLLS,
  ...DAGGERS,
  ...STAVES,
  ...RODS,
  ...OTHER,
].map(withMapSources)
