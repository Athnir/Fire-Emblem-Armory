import type { TelliusWeapon } from '../data/fe9/types'
import type { StoryOrder } from '../data/maps/mapSet'
import type { ChapterMap } from '../data/maps/types'
import type { Fe9ItemSource } from './fe9ItemSources'

/**
 * The chapters (map ids) a weapon can be had in at the time: what that chapter's base sells, bargains or forges, a base
 * conversation's gift, a script's gift, and what the map gives (chests, villages, buried items, and the drops of foes
 * standing on it at the start). Left out: a recruit's own weapon, a foe's spare weapon, and the drops of anyone who
 * arrives later or isn't a unit you can see (Petrine's Flame Lance is on the Great Bridge, not where she's only a cutscene).
 */
export function chaptersFor(w: TelliusWeapon, sources: (name: string) => Fe9ItemSource[]): Set<string> {
  const ids = new Set<string>()
  for (const at of [w.shopAt, w.bargainAt, w.forgeAt]) for (const id of [...(at?.normal ?? []), ...(at?.hard ?? [])]) ids.add(id)
  for (const id of [...(w.baseAt ?? []), ...(w.giftAt ?? [])]) ids.add(id)
  for (const s of sources(w.name)) if (!s.arrives) ids.add(s.mapId)
  return ids
}

/** The weapon as one chapter gives it: only that chapter's stock, gifts and map sources are kept. */
export function inChapter(w: TelliusWeapon, here: ChapterMap, story: StoryOrder): TelliusWeapon {
  const { shop, bargain, forge, shopAt, bargainAt, forgeAt, baseAt, giftAt, ...rest } = w
  void shop
  void bargain
  void forge
  const out: TelliusWeapon = { ...rest }
  const name = story.name(here)
  const words = (at: TelliusWeapon['shopAt']) => {
    const text = { normal: at?.normal.includes(here.id) ? name : '', hard: at?.hard.includes(here.id) ? name : '' }
    return text.normal || text.hard ? text : undefined
  }
  const s = words(shopAt)
  const b = words(bargainAt)
  const f = words(forgeAt)
  if (s) out.shop = s
  if (b) out.bargain = b
  if (f) out.forge = f
  if (baseAt?.includes(here.id)) out.baseAt = [here.id]
  if (giftAt?.includes(here.id)) out.giftAt = [here.id]
  return out
}
