import type { TelliusWeapon } from '../data/fe9/types'
import type { StoryOrder } from '../data/maps/mapSet'
import type { Fe9ItemSource } from './fe9ItemSources'
import { turnsUpAt } from './spoiler'

/**
 * The chapters (map ids) a weapon can be had in at the time: what that chapter's base sells, bargains or forges, a base
 * conversation's gift, a script's gift, what a unit on your side starts the chapter holding, and what the map gives (chests, villages, buried items, and the drops of foes
 * standing on it at the start). What a foe who arrives mid-chapter carries counts from the chapter after, when `story` is
 * given. Left out: a foe's spare weapon, and the drops of anyone who isn't a unit you can see
 * (Petrine's Flame Lance is on the Great Bridge, not where she's only a cutscene).
 */
export function chaptersFor(w: TelliusWeapon, sources: (name: string) => Fe9ItemSource[], story?: StoryOrder): Set<string> {
  const ids = new Set<string>()
  for (const at of [w.shopAt, w.bargainAt, w.forgeAt]) for (const id of [...(at?.normal ?? []), ...(at?.hard ?? [])]) ids.add(id)
  for (const id of [...(w.baseAt ?? []), ...(w.giftAt ?? []), ...(w.kitAt ?? [])]) ids.add(id)
  for (const s of sources(w.name)) {
    if (!s.arrives) ids.add(s.mapId)
    else if (story) {
      const next = story.maps[turnsUpAt(story, s.mapId, true)]
      if (next) ids.add(next.id)
    }
  }
  return ids
}

/** Where in the story a weapon first turns up (its chapter's index), or Infinity if the story never gives it. */
export function firstChapter(w: TelliusWeapon, sources: (name: string) => Fe9ItemSource[], story: StoryOrder): number {
  const order = new Map(story.maps.map((m, i) => [m.id, i]))
  return Math.min(Infinity, ...[...chaptersFor(w, sources, story)].map((id) => order.get(id) ?? Infinity))
}

/**
 * The weapon as chapter `at` shows it. What its base sells, bargains or forges is only that chapter's (a stock changes
 * from base to base), while a base conversation's or script's gift is kept once you've reached it: you still have it.
 */
export function inChapter(w: TelliusWeapon, at: number, story: StoryOrder): TelliusWeapon {
  const { shop, bargain, forge, shopAt, bargainAt, forgeAt, baseAt, giftAt, kitAt, ...rest } = w
  void shop
  void bargain
  void forge
  const here = story.maps[at]
  const reached = new Set(story.maps.slice(0, at + 1).map((m) => m.id))
  const out: TelliusWeapon = { ...rest }
  const name = story.name(here)
  const words = (list: TelliusWeapon['shopAt']) => {
    const text = { normal: list?.normal.includes(here.id) ? name : '', hard: list?.hard.includes(here.id) ? name : '' }
    return text.normal || text.hard ? text : undefined
  }
  const s = words(shopAt)
  const b = words(bargainAt)
  const f = words(forgeAt)
  if (s) out.shop = s
  if (b) out.bargain = b
  if (f) out.forge = f
  const base = baseAt?.filter((id) => reached.has(id))
  const gift = giftAt?.filter((id) => reached.has(id))
  if (base?.length) out.baseAt = base
  if (gift?.length) out.giftAt = gift
  const kit = kitAt?.filter((id) => reached.has(id))
  if (kit?.length) out.kitAt = kit
  return out
}
