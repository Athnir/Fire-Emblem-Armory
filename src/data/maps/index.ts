import type { ChapterMap } from './types'
import { SHARED_MAPS } from './shared'
import { CONQUEST_12 } from './conquest12'
import { CONQUEST_6_TO_11 } from './conquest'
import { CONQUEST_13_TO_ENDGAME } from './conquestLate'
import { BIRTHRIGHT_MAPS } from './birthright'
import { REVELATION_MAPS } from './revelation'
import { GAME_TERRAIN } from './gameTerrain'
import { GAME_UNITS } from './gameUnits'
import type { GameUnit } from './gameUnits'
import type { MapUnit, Tile } from './types'

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

const same = (a: readonly number[], b: readonly number[]) => a[0] === b[0] && a[1] === b[1]

/**
 * Units, starting tiles and Corrin's tile come from the game's own placement files where we have them.
 * What the map file adds by hand (notes, capture marks, a generic boss's class name, a pair-up the
 * game makes by script) carries over from the hand-written unit on the same tile.
 */
function withGameUnits(map: ChapterMap): ChapterMap {
  const game = GAME_UNITS[map.id]
  if (!game) return map
  const toUnit = (g: GameUnit): MapUnit & { from?: Tile } => ({
    type: g.type,
    name: g.name,
    tile: g.tile,
    ...(g.paired ? { paired: true } : {}),
    ...(g.partner && g.partner !== g.name ? { partner: g.partner } : {}),
    ...(g.drops ? { drops: g.drops } : {}),
    ...(g.difficulties && g.difficulties.length < 3 ? { difficulties: g.difficulties } : {}),
    ...(g.from ? { from: g.from } : {}),
  })
  const reinforcements = game.waves.map((w) => ({
    id: w.group,
    label: `Group ${Number(w.group.replace(/\D/g, ''))}`,
    units: w.units.map(toUnit),
    ...(w.when ? { when: w.when } : {}),
    ...(w.areas ? { areas: w.areas } : {}),
  }))
  const units = game.units.map((g): MapUnit => {
    const old = map.units.find((o) => same(o.tile, g.tile) && o.type !== 'enemy') ?? map.units.find((o) => same(o.tile, g.tile))
    const keepOld = old && old.type === g.type
    return {
      type: g.type,
      name: g.generic && keepOld ? old.name : g.name,
      tile: g.tile,
      ...(g.paired || (keepOld && old.paired && g.type === 'boss') ? { paired: true } : {}),
      ...(g.partner && g.partner !== g.name ? { partner: g.partner } : {}),
      ...(g.drops ? { drops: g.drops } : {}),
      ...(keepOld && old.capturable ? { capturable: true as const } : {}),
      ...(keepOld && old.note ? { note: old.note } : {}),
      ...(g.difficulties && g.difficulties.length < 3 ? { difficulties: g.difficulties } : {}),
    }
  })
  return {
    ...map,
    units,
    starts: game.starts,
    ...(game.corrin ? { corrinStart: game.corrin } : {}),
    ...(reinforcements.length ? { reinforcements } : {}),
    ...(game.joins.length ? { joiners: game.joins } : {}),
  }
}

/** Every transcribed map: the shared chapters first, then each route in chapter order. */
export const ALL_MAPS: ChapterMap[] = [
  ...SHARED_MAPS,
  ...BIRTHRIGHT_MAPS,
  ...CONQUEST_6_TO_11,
  CONQUEST_12,
  ...CONQUEST_13_TO_ENDGAME,
  ...REVELATION_MAPS,
].map(withGameVeins).map(withGameUnits)

export function mapLabel(map: ChapterMap): string {
  if (map.route === 'Shared') return `${map.chapter === 0 ? 'Prologue' : `Chapter ${map.chapter}`}: ${map.title}`
  return `${map.route} ${map.id.endsWith('-endgame') ? 'Endgame' : map.chapter}: ${map.title}`
}
