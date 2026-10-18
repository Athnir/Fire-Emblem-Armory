import type { ChapterMap } from './types'
import { SHARED_MAPS } from './shared'
import { CONQUEST_12 } from './conquest12'
import { CONQUEST_6_TO_11 } from './conquest'
import { CONQUEST_13_TO_ENDGAME } from './conquestLate'
import { GAME_TERRAIN } from './gameTerrain'

/** Veins whose effect isn't a terrain change of their own (they undo or reverse the others). */
const OWN_EFFECT = new Set(['vein-sakura', 'vein-hinoka'])

/** Each Dragon Vein takes the tiles it reshapes from the game's own data, where the game has them. */
function withGameVeins(map: ChapterMap): ChapterMap {
  const game = GAME_TERRAIN[map.id]
  if (!game) return map
  const changes = map.changes.map((c) => {
    if (OWN_EFFECT.has(c.id)) return c
    const tiles = [c.tile.default, c.tile.Normal, c.tile.Hard, c.tile.Lunatic].filter((t) => t !== undefined)
    const vein = game.veins.find((v) => tiles.some((t) => t[0] === v.tile[0] && t[1] === v.tile[1]))
    return vein && vein.patch.length ? { ...c, patch: vein.patch } : c
  })
  return { ...map, changes }
}

/** Every transcribed map: the shared chapters first, then each route in chapter order. */
export const ALL_MAPS: ChapterMap[] = [...SHARED_MAPS, ...CONQUEST_6_TO_11, CONQUEST_12, ...CONQUEST_13_TO_ENDGAME].map(withGameVeins)

export function mapLabel(map: ChapterMap): string {
  if (map.route === 'Shared') return `${map.chapter === 0 ? 'Prologue' : `Chapter ${map.chapter}`}: ${map.title}`
  return `${map.route} ${map.id.endsWith('-endgame') ? 'Endgame' : map.chapter}: ${map.title}`
}
