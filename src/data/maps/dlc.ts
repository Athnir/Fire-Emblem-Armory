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

/**
 * The Heirs of Fate finale's summons, read from its script as Revelation's Endgame's are (data-raw/fates/README.md, "Anankos's
 * summons"): its enemy-phase handler waits for turn 3 and keeps twelve on the field.
 */
const NOTES: Record<string, string[]> = {
  'fe14-dlc-8e': [
    "Anankos keeps summoning: from turn 3, each enemy phase he summons two units while fewer than eight of his army stand (the bosses aside), one while fewer than twelve do. Each of the seven summon points holds one unit at a time and calls it back once it's defeated; points 2, 3, 6 and 7 call other units once both claws fall or his head falls.",
    'Once both claws fall, Dragon Veins open at (4, 7) and (16, 7), and Groups A and B arrive on the next enemy phase.',
  ],
}

export const DLC_MAPS: ChapterMap[] = Object.keys(GAME_CHAPTERS)
  .filter((id) => GAME_CHAPTERS[id].route === 'DLC')
  .map((id) => gameMap(id, GAME_CHAPTERS[id].grind ? { notes: [GRIND_NOTE] } : NOTES[id] ? { notes: NOTES[id] } : {}))
