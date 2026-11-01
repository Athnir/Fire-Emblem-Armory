import type { TelliusWeapon } from '../data/fe9/types'
import type { StoryOrder } from '../data/maps/mapSet'
import type { Difficulty } from '../data/maps/types'
import { firstChapter } from '../logic/spoilerWeapons'

/** How many weapons turn up for the first time in a chapter (a map id) on a difficulty. */
export const newWeaponsIn =
  (weapons: TelliusWeapon[], sources: Parameters<typeof firstChapter>[1], story: StoryOrder) =>
  (mapId: string, _route?: string, difficulty: Difficulty = 'Normal') =>
    weapons.filter((w) => story.maps[firstChapter(w, sources, story, difficulty)]?.id === mapId).length
