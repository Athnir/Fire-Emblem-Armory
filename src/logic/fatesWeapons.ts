import { FATES_PROGRESS, LOTTERY_CHAPTERS, LOTTERY_RANK_LEVELS } from '../data/weapons/fatesCastle'
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

type StoryRoute = Exclude<Route, 'all'>
/** The routes whose allies give from each pool (Revelation's flip a coin between the two for each gift). */
const POOL_ROUTES: Record<'Hoshido' | 'Nohr', StoryRoute[]> = { Hoshido: ['Birthright', 'Revelation'], Nohr: ['Conquest', 'Revelation'] }
/** The lotteries each route's Lottery Shop offers. */
const LOTTERY_ROUTES: Record<'Dawn' | 'Dusk', StoryRoute[]> = { Dawn: ['Birthright', 'Revelation'], Dusk: ['Conquest', 'Revelation'] }

/**
 * The chapter that must be completed before My Castle's allies can give the weapon on this route: the first story chapter whose
 * progress number reaches the weapon's gate in a pool the route draws from, and never before the castle opens. Undefined when
 * no ally on the route gives it.
 */
export function giftAfter(w: Weapon, route: StoryRoute): number | undefined {
  const pools = w.game?.allyGift ?? {}
  const chapters = (Object.keys(pools) as ('Hoshido' | 'Nohr')[])
    .filter((pool) => POOL_ROUTES[pool].includes(route))
    .map((pool) => FATES_PROGRESS.findIndex((p) => p >= pools[pool]!))
    .filter((n) => n >= 0)
  return chapters.length ? Math.max(CASTLE_OPENS_AFTER, Math.min(...chapters)) : undefined
}

/** Each lottery on this route that gives the weapon, with the Lottery Shop levels whose draws can. */
export function lotteryLevels(w: Weapon, route: StoryRoute): { lottery: 'Dawn' | 'Dusk'; levels: number[] }[] {
  const ranks = w.game?.lottery ?? {}
  return (Object.keys(ranks) as ('Dawn' | 'Dusk')[])
    .filter((lottery) => LOTTERY_ROUTES[lottery].includes(route))
    .map((lottery) => ({ lottery, levels: LOTTERY_RANK_LEVELS[ranks[lottery]!] ?? [] }))
    .filter((l) => l.levels.length)
}

/** "level 2 or 3", "any level", "level 3". */
const levelText = (levels: number[]) =>
  levels.length === 3 ? 'any level' : `level ${levels.length === 1 ? levels[0] : `${levels.slice(0, -1).join(', ')} or ${levels[levels.length - 1]}`}`

/** What the weapon page says of My Castle's gifts and Lottery Shop for the whole game (without the spoiler block). */
export function castleLines(w: Weapon): string[] {
  const lines: string[] = []
  const routes: StoryRoute[] = ['Birthright', 'Conquest', 'Revelation']
  const gifts = routes.map((r) => [r, giftAfter(w, r)] as const).filter(([, n]) => n !== undefined)
  const from = new Set(gifts.map(([, n]) => n! + 1))
  if (gifts.length)
    lines.push(
      from.size === 1
        ? `Given by allies in My Castle from Chapter ${[...from][0]}.`
        : `Given by allies in My Castle from ${gifts.map(([r, n]) => `Chapter ${n! + 1} (${r})`).join(', ')}.`,
    )
  for (const lottery of ['Dawn', 'Dusk'] as const) {
    const rank = w.game?.lottery?.[lottery]
    const levels = rank ? LOTTERY_RANK_LEVELS[rank] ?? [] : []
    if (levels.length) lines.push(`A prize in the Lottery Shop's ${lottery} Lottery at ${levelText(levels)}.`)
  }
  return lines
}

/**
 * An amiibo item: static, any time the castle is open. A Battle Points or Visit Points rank reward counts as a way to collect it
 * only when `rewards` is on (the totals come from fighting and from visiting other players' castles). Allies' gifts and the
 * Lottery Shop's prizes open by chapter instead (`giftAfter`, `lotteryLevels`).
 */
export const isCastleItem = (w: Weapon, rewards = false) => !!(w.isAmiibo || (rewards && w.rankRewards?.length))

/**
 * A weapon whose only source is My Castle's Battle Points or Visit Points rewards: left off until those are shown. A weapon with
 * any other way to get it (a shop, the maps, the story, My Castle's own collection) is listed normally whatever rewards it also
 * has; its reward lines wait for the switch.
 */
export const isRewardItem = (w: Weapon) =>
  !!w.rankRewards?.length && !w.isMyCastle && !w.game?.allyGift && !w.game?.lottery && !w.isAmiibo && !w.isDlc && !w.purchase &&
  !w.mapSources?.length && !FATES_SHOPS[w.name] && !FATES_GIFTS[w.name]

/** A DLC weapon, or one only the DLC maps give (a foe carrying it there): left off until the DLC is shown. */
export const isDlcItem = (w: Weapon) => !!w.isDlc || (!!w.mapSources?.length && w.mapSources.every((s) => s.dlc) && !w.purchase && !FATES_SHOPS[w.name])

/** What the weapon list leaves out until the switches for them are ticked. */
export const hiddenByDefault = (w: Weapon) => isRewardItem(w) || isDlcItem(w)

/** The chapter number the story gives the weapon from, on this route. */
export const giftFrom = (w: Weapon, route: FatesChapter['route']): number | undefined =>
  FATES_GIFTS[w.name]?.all ?? (route ? FATES_GIFTS[w.name]?.[route] : undefined)

/**
 * Where in the story (an index) a weapon first turns up: a shop level that stocks it, My Castle opening, a chest or foe's drop
 * on a map of the route (a story map, or a paralogue or DLC map once it opens), what one of your own units starts a chapter
 * holding, the story handing it over, or the DLC maps opening. Infinity when nothing here gives it. A foe who arrives
 * mid-chapter counts from the chapter after.
 */
export function firstChapter(w: Weapon, c: FatesChapter, rewards = false): number {
  // What your own units hold when a chapter begins is yours from then on, whichever route the weapon is usually on.
  const held = (w.mapSources ?? []).filter((s) => s.how.startsWith('Starts with')).map((s) => turnsUpAt(c.story, s.mapId))
  if (!onRoute(w, c.route)) return Math.min(Infinity, ...held)
  const found: number[] = [...held]
  if (c.route) {
    for (const e of FATES_SHOPS[w.name] ?? []) {
      if (!SHOPS[c.route].includes(e.shop)) continue
      const level = e.stock.findIndex((s) => s !== 0)
      if (level >= 0) found.push(after(c.story, FATES_BUILDING_CHAPTERS[e.shop][level]))
    }
    if (isCastleItem(w, rewards)) found.push(after(c.story, CASTLE_OPENS_AFTER))
    // An ally can give it once the highest chapter cleared reaches its gate; the Lottery Shop once a level that draws it opens.
    const gift = giftAfter(w, c.route)
    if (gift !== undefined) found.push(after(c.story, gift))
    for (const l of lotteryLevels(w, c.route)) found.push(after(c.story, LOTTERY_CHAPTERS[l.levels[0] - 1]))
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
  // Nothing is said of a weapon no shop has now (never sold or not yet), so a blank can't hint at a later shop.
  if (sold) lines.push(`Bought at the ${sold.shop} (level ${sold.level}): ${sold.stock === null ? 'unlimited stock' : `${sold.stock} in stock`}.`)
  if (c.route) {
    // An ally with a "!" over their head can hand it over once the chapters cleared reach its gate.
    const after = giftAfter(w, c.route)
    if (after !== undefined && after <= completed(c)) lines.push('Given by allies in My Castle.')
    // Only the Lottery Shop levels open by now are named, so the line can't hint at a later one.
    const open = LOTTERY_CHAPTERS.filter((n) => n <= completed(c)).length
    for (const l of lotteryLevels(w, c.route)) {
      const now = l.levels.filter((lv) => lv <= open)
      if (now.length) lines.push(`A prize in the Lottery Shop's ${l.lottery} Lottery at ${levelText(now)}.`)
    }
  }
  const gift = giftFrom(w, c.route)
  if (gift !== undefined) lines.push(gift <= 1 ? 'Yours from the start.' : `Handed over by the story from Chapter ${gift}.`)
  return lines
}
