import type { TelliusWeapon } from '../data/fe9/types'
import type { StoryOrder } from '../data/maps/mapSet'
import { firstChapter } from '../logic/spoilerWeapons'

/** How many weapons turn up for the first time in a chapter (a map id). */
export const newWeaponsIn =
  (weapons: TelliusWeapon[], sources: Parameters<typeof firstChapter>[1], story: StoryOrder) => (mapId: string) =>
    weapons.filter((w) => story.maps[firstChapter(w, sources, story)]?.id === mapId).length
