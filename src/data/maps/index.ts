import type { ChapterMap } from './types'
import { SHARED_MAPS } from './shared'
import { CONQUEST_12 } from './conquest12'
import { CONQUEST_6_TO_11 } from './conquest'
import { CONQUEST_13_TO_ENDGAME } from './conquestLate'
import { BIRTHRIGHT_MAPS } from './birthright'
import { REVELATION_MAPS } from './revelation'
import { PARALOGUE_MAPS } from './paralogues'
import { DLC_MAPS } from './dlc'
import { GAME_TERRAIN } from './gameTerrain'
import { GAME_UNITS } from './gameUnits'
import { GAME_CHAPTERS } from './gameChapters'
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
 * Every chest and village from the game's terrain scripts. A hand-written one on the same tile wins,
 * since those add detail the files don't spell out (Conquest 8's event villages, Conquest 26's
 * Kaze-dependent chest).
 */
/** Each breakable wall or partition is a change of its own, previewed like a Dragon Vein. */
function withGameBreakables(map: ChapterMap): ChapterMap {
  const breakables = GAME_TERRAIN[map.id]?.breakables
  if (!breakables) return map
  const changes = breakables.map((b) => ({
    id: `break-${b.tile[0]}-${b.tile[1]}`,
    trigger: 'breakable' as const,
    tile: { default: b.tile },
    usableBy: 'Any unit that can attack it',
    effect: `${b.hp ? `${b.hp} HP. ` : ''}Attack it down and it becomes open ground.`,
    patch: [{ tile: b.tile, becomes: b.becomes }],
  }))
  return { ...map, changes: [...map.changes, ...changes] }
}

function withGameObjects(map: ChapterMap): ChapterMap {
  const game = GAME_CHAPTERS[map.id]
  if (!game) return map
  const extra = game.objects.filter((g) => !map.objects.some((o) => same(o.tile, g.tile)))
  return extra.length ? { ...map, objects: [...map.objects, ...extra] } : map
}

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
    label: w.label,
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
    ...(game.forced?.length ? { forced: game.forced } : {}),
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
  ...PARALOGUE_MAPS,
  ...DLC_MAPS,
].map(withGameVeins).map(withGameUnits).map(withGameObjects).map(withGameBreakables)

export function mapLabel(map: ChapterMap): string {
  if (map.route === 'Shared') return `${map.chapter === 0 ? 'Prologue' : `Chapter ${map.chapter}`}: ${map.title}`
  if (map.route === 'Paralogue') return `Paralogue ${map.chapter}: ${map.title}`
  if (map.route === 'DLC') {
    if (map.heading === 'Heirs of Fate') return `Heirs of Fate ${map.title}`
    return map.heading === 'Hero Battle' ? `Hero Battle: ${map.title}` : map.title
  }
  return `${map.route} ${map.id.endsWith('-endgame') ? 'Endgame' : map.chapter}: ${map.title}`
}

/** The route buttons on the map page: the chapters before the split, each route, and the DLC. */
export const MAP_ROUTES = ['Prologue', 'Birthright', 'Conquest', 'Revelation', 'DLC'] as const
export type MapRoute = (typeof MAP_ROUTES)[number]

/** A route's own maps (not its paralogues), in order. */
export function routeMaps(route: MapRoute): ChapterMap[] {
  return ALL_MAPS.filter((m) => m.route === (route === 'Prologue' ? 'Shared' : route))
}

/** The paralogues a route can reach. */
export function routeParalogues(route: MapRoute): ChapterMap[] {
  return ALL_MAPS.filter((m) => m.route === 'Paralogue' && m.availableIn?.some((r) => r === route))
}

/** A map's name within its own route's list ('Chapter 7: …' rather than 'Birthright 7: …'). */
export function chapterLabel(map: ChapterMap): string {
  if (map.route === 'Birthright' || map.route === 'Conquest' || map.route === 'Revelation') {
    return `${map.id.endsWith('-endgame') ? 'Endgame' : `Chapter ${map.chapter}`}: ${map.title}`
  }
  return mapLabel(map)
}

/** The route a map is listed under (a paralogue: the first route that can reach it). */
export function mapRoute(map: ChapterMap): MapRoute {
  if (map.route === 'Shared') return 'Prologue'
  if (map.route === 'Paralogue') return map.availableIn?.[0] ?? 'Revelation'
  return map.route
}
