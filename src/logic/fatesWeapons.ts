import { FATES_GIFTS } from '../data/weapons/fatesGifts'
import { FATES_BUILDING_CHAPTERS, FATES_SHOPS } from '../data/weapons/fatesShops'
import type { StoryOrder } from '../data/maps/mapSet'
import type { Route, Weapon } from '../data/types'
import { maxForgeRank } from './forge'
import { turnsUpAt } from './spoiler'

/** Where a Fates weapon stands at a chapter, with the block on: the chapters of the route chosen so far, and where you are in them. */
export interface FatesChapter {
  story: StoryOrder
  at: number
  /** Chosen at the split after Chapter 5; none before. */
  route?: Exclude<Route, 'all'>
}

/** The shops each route builds: the Hoshidan pair, the Nohrian pair, or (Revelation) both. */
const SHOPS: Record<Exclude<Route, 'all'>, string[]> = {
  Birthright: ['Dawn Armoury', 'Rod Store'],
  Conquest: ['Dusk Armoury', 'Staff Store'],
  Revelation: ['Dawn Armoury', 'Rod Store', 'Dusk Armoury', 'Staff Store'],
}
/** The chapter whose completion opens My Castle's first shop level: from then on its allies' items are yours to collect. */
const CASTLE_OPENS_AFTER = FATES_BUILDING_CHAPTERS['Dawn Armoury'][0]
/** The chapter whose completion opens the Dragon's Gate, which holds the DLC maps (Serenes Forest). */
const DLC_OPENS_AFTER = 6

/** Chapters completed when you're on the chapter at `at` (the one you're on isn't). */
export const completed = (c: FatesChapter) => c.story.maps[c.at].chapter - 1

/** How many levels of a building are open: each opens once its chapter is completed. */
export function buildingLevel(building: string, c: FatesChapter): number {
  return FATES_BUILDING_CHAPTERS[building].filter((n) => n <= completed(c)).length
}

export const smithyLevel = (c: FatesChapter) => buildingLevel('Smithy', c)
export const maxForge = (c: FatesChapter) => maxForgeRank(smithyLevel(c))

/** The index of the first chapter of the story after `chapter` is completed, or Infinity if the story ends first. */
const after = (story: StoryOrder, chapter: number) => {
  const i = story.maps.findIndex((m) => m.chapter > chapter)
  return i < 0 ? Infinity : i
}

/** Whether the weapon belongs to the route chosen (before the choice: only what the shared chapters hold). */
export function onRoute(w: Weapon, route: FatesChapter['route']): boolean {
  if (!route) return true
  const routes = w.availability.routes
  return routes.includes(route) || routes.includes('all') || (routes.length === 0 && !!(w.isAmiibo || w.isDlc))
}

/** What a shop stocks of this weapon at its current level on this route: undefined when it isn't sold there now. */
export interface Stocked {
  shop: string
  level: number
  /** null: unlimited. */
  stock: number | null
}

export function stockedNow(w: Weapon, c: FatesChapter): Stocked | undefined {
  if (!c.route) return undefined
  let best: Stocked | undefined
  for (const e of FATES_SHOPS[w.name] ?? []) {
    if (!SHOPS[c.route].includes(e.shop)) continue
    const level = buildingLevel(e.shop, c)
    const stock = level ? e.stock[level - 1] : 0
    if (stock === 0) continue
    // The same weapon in two shops (Revelation): the roomier stock wins.
    if (!best || stock === null || (best.stock !== null && stock > best.stock)) best = { shop: e.shop, level, stock }
  }
  return best
}

/** A My Castle item collected from allies, a rank reward or an amiibo item: static, any time the castle is open. */
export const isCastleItem = (w: Weapon) => !!(w.isMyCastle || w.isAmiibo || w.rankRewards?.length)

/** A My Castle reward for a Visit Points total, which comes from visiting other players' castles. */
export const isVisitItem = (w: Weapon) => !!w.rankRewards?.some((r) => r.track === 'Visit Points')

/** The chapter number the story gives the weapon from, on this route. */
export const giftFrom = (w: Weapon, route: FatesChapter['route']): number | undefined =>
  FATES_GIFTS[w.name]?.all ?? (route ? FATES_GIFTS[w.name]?.[route] : undefined)

/**
 * Where in the story (an index) a weapon first turns up: a shop level that stocks it, My Castle opening, a chest or foe's drop
 * on a map of the route (a story map, or a paralogue or DLC map once it opens), the story handing it over, or the DLC maps opening. Infinity when nothing here gives it (a
 * character's own weapon, say). The drops of foes who arrive mid-chapter don't count.
 */
export function firstChapter(w: Weapon, c: FatesChapter): number {
  if (!onRoute(w, c.route)) return Infinity
  const found: number[] = []
  if (c.route) {
    for (const e of FATES_SHOPS[w.name] ?? []) {
      if (!SHOPS[c.route].includes(e.shop)) continue
      const level = e.stock.findIndex((s) => s !== 0)
      if (level >= 0) found.push(after(c.story, FATES_BUILDING_CHAPTERS[e.shop][level]))
    }
    if (isCastleItem(w)) found.push(after(c.story, CASTLE_OPENS_AFTER))
    if (w.isDlc) found.push(after(c.story, DLC_OPENS_AFTER))
  }
  // A chest, village or foe's gear on a story map counts from that chapter; on a paralogue or DLC map, from the chapter that opens it.
  // A foe who arrives mid-chapter counts from the chapter after.
  for (const s of w.mapSources ?? []) found.push(turnsUpAt(c.story, s.mapId, s.arrives))
  const gift = giftFrom(w, c.route)
  if (gift !== undefined) found.push(c.story.maps.findIndex((m) => m.chapter >= gift))
  return Math.min(Infinity, ...found.filter((i) => i >= 0))
}

/** What the detail panel says about where to get a weapon, as far as this chapter goes: a shop that stocks it now, or the story's gift. */
export function whereLines(w: Weapon, c: FatesChapter): string[] {
  const lines: string[] = []
  const sold = stockedNow(w, c)
  // Nothing is said of a weapon no shop has now (never sold or not yet), or of My Castle's static items, so a blank can't hint at a later shop.
  if (sold) lines.push(`Bought at the ${sold.shop} (level ${sold.level}): ${sold.stock === null ? 'unlimited stock' : `${sold.stock} in stock`}.`)
  const gift = giftFrom(w, c.route)
  if (gift !== undefined) lines.push(gift <= 1 ? 'Yours from the start.' : `Handed over by the story from Chapter ${gift}.`)
  return lines
}
