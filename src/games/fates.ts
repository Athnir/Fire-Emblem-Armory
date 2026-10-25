import { FatesMaps } from '../components/FatesMaps'
import { FatesSupports } from '../components/FatesSupports'
import { FatesWeapons } from '../components/FatesWeapons'
import { FATES_FORK } from '../data/maps/fatesStory'
import { ALL_WEAPONS } from '../data/weapons'
import { firstChapter } from '../logic/fatesWeapons'
import type { GameParts } from '.'

/** Fates' screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: FatesWeapons,
  maps: FatesMaps,
  supports: FatesSupports,
  fork: FATES_FORK,
  newWeapons: (mapId, route) => {
    const story = FATES_FORK.choices.find((c) => c.id === route)?.story ?? FATES_FORK.before
    const at = story.maps.findIndex((m) => m.id === mapId)
    if (at < 0) return 0
    const chapter = { story, at, route: route as 'Birthright' | 'Conquest' | 'Revelation' | undefined }
    return ALL_WEAPONS.filter((w) => story.maps[firstChapter(w, chapter)]?.id === mapId).length
  },
}

export default parts
