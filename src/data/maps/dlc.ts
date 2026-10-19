import type { ChapterMap } from './types'
import { gameMap } from './fromGame'
import { GAME_CHAPTERS } from './gameChapters'

/*
 * The DLC maps from the user's own downloads (xenologues and Heirs of Fate; Infinite Regalia isn't among
 * them), then the four amiibo Hero Battles. All are open on every route. Built wholly from the game's
 * own files (see fromGame.ts).
 */
const GRIND_NOTE =
  'A grind map: the more enemies you defeat in a run, the more spawn and the stronger they get, so nothing here is on a set turn. The marked groups show only where each spawns and where it heads.'

export const DLC_MAPS: ChapterMap[] = Object.keys(GAME_CHAPTERS)
  .filter((id) => GAME_CHAPTERS[id].route === 'DLC')
  .map((id) => gameMap(id, GAME_CHAPTERS[id].grind ? { notes: [GRIND_NOTE] } : {}))
